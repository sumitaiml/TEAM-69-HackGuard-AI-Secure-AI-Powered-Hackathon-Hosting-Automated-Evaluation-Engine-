import logging
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiScoreResponse(BaseModel):
    innovation_score: float = Field(ge=0, le=100)
    ui_ux_score: float = Field(ge=0, le=100)
    business_impact_score: float = Field(ge=0, le=100)
    documentation_quality_score: float = Field(ge=0, le=100)
    presentation_quality_score: float = Field(ge=0, le=100)
    feedback: List[str]
    improvement_suggestions: List[str]


def _model_candidates() -> List[str]:
    candidates = [settings.GEMINI_MODEL] + [
        m.strip() for m in settings.GEMINI_MODEL_FALLBACKS.split(",") if m.strip()
    ]
    # de-dupe while preserving order
    seen = set()
    ordered = []
    for m in candidates:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def _is_retryable(exc: BaseException) -> bool:
    """Retry on transient server errors and rate limits (429) - a 404
    (model retired/unavailable) should instead advance to the next model
    candidate, not retry the same one, since retrying won't fix that."""
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, genai_errors.ClientError) and getattr(exc, "code", None) == 429:
        return True
    return False


def _build_prompt(readme_text: str, ppt_slides_text: str, transcript: str, tech_stack: str) -> str:
    return f"""You are an expert, discerning hackathon judge evaluating a project submission. \
Score fairly based only on the evidence given - do not invent details that aren't present, \
and do not default to the same score for every category.

## README
{readme_text or "(no README provided)"}

## Presentation slides (extracted text)
{ppt_slides_text or "(no presentation slides provided)"}

## Demo video transcript
{transcript or "(no demo video provided)"}

## Claimed tech stack
{tech_stack or "(not specified)"}

Score this submission from 0-100 on each dimension:
- innovation_score: originality and creativity of the idea
- ui_ux_score: quality of the user experience, as described or shown
- business_impact_score: real-world value and market potential
- documentation_quality_score: clarity and completeness of the README
- presentation_quality_score: how well the slides/demo communicate the project

Also provide:
- feedback: 2-4 short, specific strengths you noticed
- improvement_suggestions: 1-3 short, specific, actionable suggestions"""


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _call_model(
    client: "genai.Client",
    model_name: str,
    prompt: Union[str, List[Any]],
    response_schema: Type[BaseModel],
    tools: Optional[List[Callable]] = None,
) -> str:
    config_kwargs = dict(
        temperature=0.1,
        response_mime_type="application/json",
        response_schema=response_schema,
    )
    if tools:
        # Automatic Function Calling: passing plain Python functions (not
        # types.Tool objects) lets the SDK run the whole look-then-decide
        # tool-calling loop itself within this one generate_content() call -
        # it introspects each function's signature/docstring for the
        # function-declaration schema, executes it when the model requests
        # it, and feeds the result back in, up to maximum_remote_calls.
        config_kwargs["tools"] = tools
        config_kwargs["automatic_function_calling"] = types.AutomaticFunctionCallingConfig(
            maximum_remote_calls=settings.AGENT_MAX_TOOL_CALLS,
        )
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    return response.text


def call_structured_gemini(prompt: Union[str, List[Any]], response_schema: Type[T], tools: Optional[List[Callable]] = None) -> T:
    """Generic structured-output call: one prompt in, one Pydantic-validated
    response out, with model-fallback and a one-time repair retry on
    schema-invalid output. `prompt` can be a plain string or a list mixing
    text and types.Part.from_bytes(...) image parts for multimodal input
    (pitch_deck_agent.py) - google-genai's generate_content() `contents`
    argument accepts either natively. This is the shared scaffolding behind
    score_submission() below and every agent built on top of it - raises on
    total failure across every model candidate, so callers are responsible
    for their own degraded-mode fallback rather than this function silently
    swallowing errors.

    `tools`, if given, turns this into a genuine agentic tool-calling call
    (see _call_model) rather than a single-shot one - used by agents that
    need to decide what to look at (repo_verification_agent.py) rather than
    being handed everything relevant up front."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    last_error: Exception = RuntimeError("No Gemini model candidates configured")
    for model_name in _model_candidates():
        try:
            raw = _call_model(client, model_name, prompt, response_schema, tools)
        except Exception as e:
            logger.warning("Gemini model %s failed: %s", model_name, e)
            last_error = e
            continue

        try:
            return response_schema.model_validate_json(raw)
        except Exception as validation_error:
            # One repair retry: ask the same model to fix its own output
            # before giving up on it and moving to the next candidate. No
            # tools here - this is just a formatting fix of an answer the
            # model already reasoned its way to, not another exploration pass.
            logger.warning("Gemini model %s returned invalid schema, attempting repair: %s", model_name, validation_error)
            try:
                repair_prompt = (
                    "Your previous response was not valid JSON matching the required schema. "
                    f"Fix it and return ONLY the corrected JSON.\n\nPrevious response:\n{raw}"
                )
                repaired = _call_model(client, model_name, repair_prompt, response_schema)
                return response_schema.model_validate_json(repaired)
            except Exception as e:
                logger.warning("Gemini model %s repair attempt also failed: %s", model_name, e)
                last_error = e
                continue

    raise RuntimeError(f"All Gemini model candidates failed: {last_error}") from last_error


def score_submission(readme_text: str, ppt_slides_text: str, transcript: str, tech_stack: str) -> GeminiScoreResponse:
    """Raises on total failure across every model candidate - the caller
    (ai_evaluation.py) is responsible for the degraded-mode fallback so a
    Gemini outage doesn't fail the whole evaluation."""
    prompt = _build_prompt(readme_text, ppt_slides_text, transcript, tech_stack)
    return call_structured_gemini(prompt, GeminiScoreResponse)
