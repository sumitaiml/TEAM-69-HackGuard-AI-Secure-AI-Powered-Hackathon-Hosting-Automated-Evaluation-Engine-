import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Type, TypeVar

from groq import Groq
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.services.gemini_client import GeminiScoreResponse, _build_prompt

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_MODE_INSTRUCTION = (
    "You must respond with ONLY valid JSON matching this schema (no markdown "
    "code fences, no commentary before or after it): {schema}"
)


def _model_candidates() -> List[str]:
    """Mirrors gemini_client._model_candidates() exactly - [primary] +
    fallbacks, de-duped, in order."""
    candidates = [settings.GROQ_MODEL] + [
        m.strip() for m in settings.GROQ_MODEL_FALLBACKS.split(",") if m.strip()
    ]
    seen = set()
    ordered = []
    for m in candidates:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def _is_retryable(exc: BaseException) -> bool:
    """Groq's SDK exposes a consistent .status_code across its error
    hierarchy (RateLimitError pins it to 429, APIStatusError is the general
    base) - checked by duck-typing rather than importing exact exception
    class names, which aren't guaranteed stable across SDK versions."""
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    if isinstance(status_code, int) and status_code >= 500:
        return True
    return False


def _is_phantom_tool_call_error(exc: BaseException) -> bool:
    """Detects Groq gpt-oss's tendency to keep trying to call a tool once a
    conversation has included tool use, even on a request where it
    shouldn't - seen live in two distinct shapes, both 400s:
    1. Given `tools` plus any hint of the eventual answer's shape, it tries
       to "call" a synthetic tool named after that shape (e.g. "json" or
       the response schema's class name) instead of using a real tool or
       replying in plain text - rejected with a tool "was not in
       request.tools".
    2. On the separate final call where `tools` is withheld entirely, it
       still tries to call a REAL tool from earlier in the conversation
       (e.g. "search_code") - rejected with "Tool choice is none, but
       model called a tool".
    Narrowly matched on these specific error shapes so an unrelated 400 (a
    genuinely malformed request) still surfaces as a real failure instead
    of being silently swallowed."""
    status_code = getattr(exc, "status_code", None)
    if status_code != 400:
        return False
    message = str(exc).lower()
    if "tool call validation failed" in message and "not in request.tools" in message:
        return True
    if "tool choice is none" in message and "called a tool" in message:
        return True
    return False


def _function_to_tool_schema(func: Callable) -> Dict[str, Any]:
    """Builds an OpenAI-style tool schema from a plain Python function's
    signature/docstring - Groq has no equivalent of Gemini's Automatic
    Function Calling, which introspects functions for you. Kept simple
    (every parameter typed as a string) since the only tools this is used
    for today (list_directory/read_file/search_code in
    repo_verification_agent.py) each take exactly one string argument."""
    sig = inspect.signature(func)
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for name, param in sig.parameters.items():
        properties[name] = {"type": "string", "description": f"The {name} argument."}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": (func.__doc__ or "").strip(),
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _chat(client: "Groq", model_name: str, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None, force_json: bool = False):
    kwargs: Dict[str, Any] = {"model": model_name, "messages": messages, "temperature": 0.1}
    if tools:
        kwargs["tools"] = tools
    if force_json:
        kwargs["response_format"] = {"type": "json_object"}
    return client.chat.completions.create(**kwargs)


def call_structured_groq(prompt: str, response_schema: Type[T]) -> T:
    """Text-only structured-output call: one prompt in, one Pydantic-
    validated response out - with the same model-fallback and one-time
    repair-retry contract as gemini_client.call_structured_gemini(), so
    callers migrated from Gemini don't need to change their own error
    handling. Groq's chat-completions API has no native field-level schema
    enforcement (unlike Gemini's response_schema), so the schema is spelled
    out in a system message and response_format={"type":"json_object"} only
    guarantees syntactically valid JSON - model_validate_json() below plus
    the repair pass is what actually enforces the schema."""
    schema_json = json.dumps(response_schema.model_json_schema())
    system_message = {"role": "system", "content": _JSON_MODE_INSTRUCTION.format(schema=schema_json)}
    messages = [system_message, {"role": "user", "content": prompt}]

    client = Groq(api_key=settings.GROQ_API_KEY)
    last_error: Exception = RuntimeError("No Groq model candidates configured")

    for model_name in _model_candidates():
        try:
            response = _chat(client, model_name, messages, force_json=True)
            raw = response.choices[0].message.content
        except Exception as e:
            logger.warning("Groq model %s failed: %s", model_name, e)
            last_error = e
            continue

        try:
            return response_schema.model_validate_json(raw)
        except Exception as validation_error:
            # One repair retry, same rationale as the Gemini version: fix
            # the formatting of an answer the model already reasoned its
            # way to, not another exploration pass.
            logger.warning("Groq model %s returned invalid schema, attempting repair: %s", model_name, validation_error)
            try:
                repair_messages = messages + [
                    {"role": "assistant", "content": raw},
                    {"role": "user", "content": "That was not valid JSON matching the required schema. Return ONLY the corrected JSON."},
                ]
                repaired_response = _chat(client, model_name, repair_messages, force_json=True)
                repaired = repaired_response.choices[0].message.content
                return response_schema.model_validate_json(repaired)
            except Exception as e:
                logger.warning("Groq model %s repair attempt also failed: %s", model_name, e)
                last_error = e
                continue

    raise RuntimeError(f"All Groq model candidates failed: {last_error}") from last_error


def call_agentic_groq(prompt: str, response_schema: Type[T], tools: List[Callable], max_tool_calls: int) -> T:
    """The tool-calling counterpart to call_structured_groq(), for agents
    that need to decide what to look at (repo_verification_agent.py)
    instead of being handed everything up front. Groq has no equivalent of
    Gemini's Automatic Function Calling (which runs the whole call-execute-
    feed-back loop inside the SDK) - only the lower-level OpenAI-compatible
    protocol where the caller drives that loop itself, which is what this
    function does. Same model-fallback and repair-retry contract as the
    text-only version above."""
    tool_map = {fn.__name__: fn for fn in tools}
    tool_schemas = [_function_to_tool_schema(fn) for fn in tools]
    tool_names = ", ".join(sorted(tool_map))
    schema_json = json.dumps(response_schema.model_json_schema())
    # Deliberately says NOTHING about the eventual output schema - confirmed
    # live against Groq's gpt-oss models that mentioning a JSON schema while
    # `tools` is also set makes the model try to "call" a synthetic tool
    # named after the schema (e.g. a tool literally named "Result" or
    # "json"), which the API then rejects outright since no such tool was
    # registered. The schema is only introduced in the separate, tools-free
    # final call below, once investigation is done. Even with no schema
    # mentioned here, the task prompt itself (built by the caller, e.g.
    # repo_verification_agent's _build_prompt) often still describes the
    # eventual answer's fields in plain English - enough on its own to
    # trigger the same quirk - hence the explicit tool allow-list below
    # AND the _is_phantom_tool_call_error() catch further down as a second
    # line of defense that doesn't depend on prompt wording holding up
    # across model versions.
    investigate_system_message = {
        "role": "system",
        "content": (
            f"You may ONLY call these exact tools: {tool_names}. Use them to investigate "
            "thoroughly before answering. The task below may describe what your eventual "
            "final answer should contain once you're done investigating - do NOT try to "
            "produce that answer as a tool call now, and do not invent or call any tool "
            "other than the ones listed above. When ready to answer, make a normal "
            "plain-text reply with no tool call at all; a later step will ask you to "
            "format it."
        ),
    }

    client = Groq(api_key=settings.GROQ_API_KEY)
    last_error: Exception = RuntimeError("No Groq model candidates configured")

    for model_name in _model_candidates():
        try:
            messages: List[Dict[str, Any]] = [investigate_system_message, {"role": "user", "content": prompt}]
            calls_made = 0

            while calls_made < max_tool_calls:
                try:
                    response = _chat(client, model_name, messages, tools=tool_schemas)
                except Exception as e:
                    if _is_phantom_tool_call_error(e):
                        # The model tried to "call" a synthetic tool to
                        # deliver its answer instead of either using a real
                        # tool or replying in plain text - treat this as "the
                        # model is done investigating" rather than a hard
                        # failure, and fall through to the final answer call
                        # below with whatever was actually learned so far.
                        logger.warning("Groq model %s attempted a phantom tool call, treating as done investigating: %s", model_name, e)
                        break
                    raise
                msg = response.choices[0].message
                if not msg.tool_calls:
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in msg.tool_calls
                    ],
                })
                for tc in msg.tool_calls:
                    fn = tool_map.get(tc.function.name)
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                        result = fn(**args) if fn else f"(unknown tool: {tc.function.name})"
                    except Exception as e:
                        result = f"(tool error: {e})"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": json.dumps(result),
                    })
                    calls_made += 1
                    if calls_made >= max_tool_calls:
                        break

            # Separate, tools-free call to get the actual structured answer -
            # always done (whether the loop stopped naturally or hit
            # max_tool_calls), since the model was never asked for JSON
            # during the investigation phase above.
            messages.append({
                "role": "user",
                "content": (
                    "Based on everything above, respond with ONLY valid JSON matching "
                    f"this schema (no markdown fences, no commentary): {schema_json}"
                ),
            })
            try:
                response = _chat(client, model_name, messages, force_json=True)
                final_text = response.choices[0].message.content
            except Exception as e:
                if not _is_phantom_tool_call_error(e):
                    raise
                # Seen live: even with no `tools` offered on this call, the
                # model sometimes still tries to call a real tool from
                # earlier in the conversation (e.g. "search_code"). One
                # retry with an explicit "you have no tools right now"
                # instruction, rather than burning the whole model
                # candidate over it.
                logger.warning("Groq model %s attempted a phantom tool call on the final answer, retrying with an explicit no-tools instruction: %s", model_name, e)
                messages.append({
                    "role": "user",
                    "content": "You have no tools available in this message - do not attempt to call any tool. Just write the JSON answer directly.",
                })
                response = _chat(client, model_name, messages, force_json=True)
                final_text = response.choices[0].message.content
        except Exception as e:
            logger.warning("Groq model %s failed: %s", model_name, e)
            last_error = e
            continue

        try:
            return response_schema.model_validate_json(final_text)
        except Exception as validation_error:
            logger.warning("Groq model %s returned invalid schema, attempting repair: %s", model_name, validation_error)
            try:
                repair_messages = [
                    {"role": "system", "content": _JSON_MODE_INSTRUCTION.format(schema=schema_json)},
                    {"role": "assistant", "content": final_text},
                    {"role": "user", "content": "That was not valid JSON matching the required schema. Return ONLY the corrected JSON."},
                ]
                repaired_response = _chat(client, model_name, repair_messages, force_json=True)
                repaired = repaired_response.choices[0].message.content
                return response_schema.model_validate_json(repaired)
            except Exception as e:
                logger.warning("Groq model %s repair attempt also failed: %s", model_name, e)
                last_error = e
                continue

    raise RuntimeError(f"All Groq model candidates failed: {last_error}") from last_error


def score_submission(readme_text: str, ppt_slides_text: str, transcript: str, tech_stack: str) -> GeminiScoreResponse:
    """Raises on total failure across every model candidate - the caller
    (ai_evaluation.py) is responsible for the degraded-mode fallback so a
    Groq outage doesn't fail the whole evaluation. Reuses gemini_client's
    prompt builder and response schema directly rather than duplicating
    them - the shape is provider-agnostic, only the transport changed."""
    prompt = _build_prompt(readme_text, ppt_slides_text, transcript, tech_stack)
    return call_structured_groq(prompt, GeminiScoreResponse)
