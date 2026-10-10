import pytest
from pydantic import BaseModel

import app.services.groq_client as groq_client_module
from app.services.groq_client import (
    _function_to_tool_schema,
    _is_phantom_tool_call_error,
    _is_retryable,
    _model_candidates,
    call_agentic_groq,
    call_structured_groq,
)


class _DummySchema(BaseModel):
    value: str


class _FakeAPIError(Exception):
    """Mimics Groq SDK errors closely enough for _is_retryable's duck-typed
    status_code check - a real RateLimitError/APIStatusError isn't needed."""

    def __init__(self, status_code, message="error"):
        super().__init__(message)
        self.status_code = status_code


class _FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = _FakeFunction(name, arguments)


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeResponse:
    def __init__(self, message):
        self.choices = [type("Choice", (), {"message": message})()]


class _FakeCompletions:
    """Each entry in `behaviors` is either an Exception instance (raised) or
    a _FakeResponse (returned) - consumed in order, one per .create() call."""

    def __init__(self, behaviors):
        self.behaviors = list(behaviors)
        self.calls = []

    def create(self, **kwargs):
        # groq_client.py mutates its `messages` list in place across the
        # retry/tool-calling loop - snapshot it (shallow copy is enough,
        # individual message dicts aren't mutated after being appended) so a
        # later `calls[i]` inspection shows what was actually sent at call i,
        # not the list's final state after the whole function has returned.
        snapshot = dict(kwargs)
        if "messages" in snapshot:
            snapshot["messages"] = list(snapshot["messages"])
        self.calls.append(snapshot)
        behavior = self.behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


class _FakeGroqClient:
    def __init__(self, behaviors):
        completions = _FakeCompletions(behaviors)
        self.chat = type("Chat", (), {"completions": completions})()


def _patch_client(monkeypatch, behaviors):
    fake_client = _FakeGroqClient(behaviors)
    monkeypatch.setattr(groq_client_module, "Groq", lambda api_key: fake_client)
    return fake_client


# --- Pure unit tests (no API calls, no sleeping) ---

def test_model_candidates_dedupes_and_preserves_order(monkeypatch):
    monkeypatch.setattr(groq_client_module.settings, "GROQ_MODEL", "model-a")
    monkeypatch.setattr(groq_client_module.settings, "GROQ_MODEL_FALLBACKS", "model-b, model-a, model-c")
    assert _model_candidates() == ["model-a", "model-b", "model-c"]


def test_is_retryable_on_429_and_5xx_not_on_other_codes():
    assert _is_retryable(_FakeAPIError(429)) is True
    assert _is_retryable(_FakeAPIError(500)) is True
    assert _is_retryable(_FakeAPIError(503)) is True
    assert _is_retryable(_FakeAPIError(400)) is False
    assert _is_retryable(_FakeAPIError(404)) is False
    assert _is_retryable(ValueError("no status_code at all")) is False


def test_is_phantom_tool_call_error_matches_only_the_known_pattern():
    phantom = _FakeAPIError(400, "Tool call validation failed: tool call validation failed: attempted to call tool 'json' which was not in request.tools")
    assert _is_phantom_tool_call_error(phantom) is True
    # A different 400 (genuinely malformed request) must NOT be swallowed by this check.
    assert _is_phantom_tool_call_error(_FakeAPIError(400, "invalid_request_error: messages must not be empty")) is False
    assert _is_phantom_tool_call_error(_FakeAPIError(429, "rate limited")) is False


def test_function_to_tool_schema_describes_required_string_params():
    def read_file(relative_path: str) -> str:
        """Reads a file."""
        return ""

    schema = _function_to_tool_schema(read_file)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "read_file"
    assert schema["function"]["description"] == "Reads a file."
    assert schema["function"]["parameters"]["properties"]["relative_path"]["type"] == "string"
    assert schema["function"]["parameters"]["required"] == ["relative_path"]


# --- call_structured_groq ---

def test_call_structured_groq_succeeds_on_first_try(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(_FakeMessage(content='{"value": "ok"}'))])
    result = call_structured_groq("some prompt", _DummySchema)
    assert result == _DummySchema(value="ok")


def test_call_structured_groq_repairs_invalid_json_before_falling_back(monkeypatch):
    fake_client = _patch_client(monkeypatch, [
        _FakeResponse(_FakeMessage(content="not valid json at all")),
        _FakeResponse(_FakeMessage(content='{"value": "repaired"}')),
    ])
    result = call_structured_groq("some prompt", _DummySchema)
    assert result == _DummySchema(value="repaired")
    assert len(fake_client.chat.completions.calls) == 2


def test_call_structured_groq_falls_back_to_next_model_on_non_retryable_error(monkeypatch):
    monkeypatch.setattr(groq_client_module.settings, "GROQ_MODEL", "model-a")
    monkeypatch.setattr(groq_client_module.settings, "GROQ_MODEL_FALLBACKS", "model-b")
    fake_client = _patch_client(monkeypatch, [
        _FakeAPIError(400, "bad request on model-a"),  # non-retryable - no sleep, moves straight to next model
        _FakeResponse(_FakeMessage(content='{"value": "from model b"}')),
    ])
    result = call_structured_groq("some prompt", _DummySchema)
    assert result == _DummySchema(value="from model b")
    assert fake_client.chat.completions.calls[0]["model"] == "model-a"
    assert fake_client.chat.completions.calls[1]["model"] == "model-b"


def test_call_structured_groq_raises_after_all_candidates_exhausted(monkeypatch):
    monkeypatch.setattr(groq_client_module.settings, "GROQ_MODEL", "model-a")
    monkeypatch.setattr(groq_client_module.settings, "GROQ_MODEL_FALLBACKS", "model-b")
    _patch_client(monkeypatch, [
        _FakeAPIError(400, "bad on a"),
        _FakeAPIError(400, "bad on b"),
    ])
    with pytest.raises(RuntimeError, match="All Groq model candidates failed"):
        call_structured_groq("some prompt", _DummySchema)


def test_call_structured_groq_retries_on_429_then_succeeds(monkeypatch):
    """The one test that exercises the real tenacity retry wrapper (not just
    the model-fallback loop) - genuinely sleeps a couple of seconds via the
    real wait_exponential backoff, which is the point: proving a transient
    429 gets retried on the SAME model rather than immediately falling back."""
    fake_client = _patch_client(monkeypatch, [
        _FakeAPIError(429, "rate limited"),
        _FakeResponse(_FakeMessage(content='{"value": "retried ok"}')),
    ])
    result = call_structured_groq("some prompt", _DummySchema)
    assert result == _DummySchema(value="retried ok")
    # Both calls went to the same (only) model candidate - this was a retry, not a fallback.
    assert len(fake_client.chat.completions.calls) == 2
    assert fake_client.chat.completions.calls[0]["model"] == fake_client.chat.completions.calls[1]["model"]


# --- call_agentic_groq ---

def test_call_agentic_groq_executes_tools_then_returns_final_answer(monkeypatch):
    calls_to_list_directory = []

    def list_directory(path: str):
        """Lists a directory."""
        calls_to_list_directory.append(path)
        return ["main.py", "requirements.txt"]

    tool_call_message = _FakeMessage(
        content="",
        tool_calls=[_FakeToolCall("call_1", "list_directory", '{"path": "."}')],
    )
    stop_message = _FakeMessage(content="I've seen enough.", tool_calls=None)
    final_message = _FakeMessage(content='{"value": "done"}', tool_calls=None)
    fake_client = _patch_client(monkeypatch, [
        _FakeResponse(tool_call_message),  # investigation: requests a tool call
        _FakeResponse(stop_message),       # investigation: stops calling tools
        _FakeResponse(final_message),      # separate, tools-free call for the real structured answer
    ])

    result = call_agentic_groq("investigate the repo", _DummySchema, tools=[list_directory], max_tool_calls=10)

    assert result == _DummySchema(value="done")
    assert calls_to_list_directory == ["."]  # the real tool function was actually invoked
    # Second call's messages must include the tool's result for the model to see.
    second_call_messages = fake_client.chat.completions.calls[1]["messages"]
    assert any(m.get("role") == "tool" and m.get("tool_call_id") == "call_1" for m in second_call_messages)
    # The final call must be tools-free - confirmed live against Groq's
    # gpt-oss models that mentioning the output schema while tools are also
    # present makes the model try to "call" a synthetic tool named after the
    # schema, which the API then rejects outright.
    assert not fake_client.chat.completions.calls[2].get("tools")


def test_call_agentic_groq_recovers_from_phantom_tool_call_error(monkeypatch):
    """A second, deeper instance of the same live quirk (found after the
    fix above): even with no schema in the system message, the task
    prompt's own description of the expected fields was enough to trigger
    it - the model attempted a phantom tool call on the very FIRST
    investigation request, before any real tool was ever used. The
    _is_phantom_tool_call_error() catch must recover from this instead of
    burning the whole model candidate (and, with only one candidate
    configured here, the whole call)."""
    def list_directory(path: str):
        """Lists a directory."""
        return []

    phantom_error = _FakeAPIError(400, "Tool call validation failed: tool call validation failed: attempted to call tool 'json' which was not in request.tools")
    final_message = _FakeMessage(content='{"value": "recovered"}', tool_calls=None)
    _patch_client(monkeypatch, [phantom_error, _FakeResponse(final_message)])

    result = call_agentic_groq("investigate", _DummySchema, tools=[list_directory], max_tool_calls=10)

    assert result == _DummySchema(value="recovered")


def test_call_agentic_groq_never_mentions_schema_while_tools_are_in_play(monkeypatch):
    """Regression test for a real failure seen live: Groq's gpt-oss models,
    when given both `tools` and a system prompt describing a JSON schema,
    try to "call" a synthetic tool named after the schema (e.g. a tool
    literally named "Result") instead of either using a real tool or
    answering normally - which the API then rejects with a 400. The fix is
    to never mention the output schema in any call that also has `tools`
    set, only in the separate final call."""
    def list_directory(path: str):
        """Lists a directory."""
        return []

    stop_message = _FakeMessage(content="done investigating", tool_calls=None)
    final_message = _FakeMessage(content='{"value": "ok"}', tool_calls=None)
    fake_client = _patch_client(monkeypatch, [_FakeResponse(stop_message), _FakeResponse(final_message)])

    call_agentic_groq("investigate", _DummySchema, tools=[list_directory], max_tool_calls=10)

    investigation_call = fake_client.chat.completions.calls[0]
    assert investigation_call.get("tools")  # tools were offered...
    investigation_text = " ".join(m.get("content") or "" for m in investigation_call["messages"])
    assert "schema" not in investigation_text.lower()  # ...but the schema was never mentioned alongside them

    final_call = fake_client.chat.completions.calls[1]
    assert not final_call.get("tools")  # the final call is the only one that may mention the schema


def test_call_agentic_groq_forces_final_answer_at_max_tool_calls(monkeypatch):
    def list_directory(path: str):
        """Lists a directory."""
        return []

    # The model keeps requesting tool calls forever - capped at max_tool_calls=1,
    # then one more call is forced with tools withheld to get the final JSON.
    always_tool_call = _FakeMessage(content="", tool_calls=[_FakeToolCall("call_1", "list_directory", '{"path": "."}')])
    forced_final = _FakeMessage(content='{"value": "forced"}', tool_calls=None)
    fake_client = _patch_client(monkeypatch, [
        _FakeResponse(always_tool_call),
        _FakeResponse(forced_final),
    ])

    result = call_agentic_groq("investigate", _DummySchema, tools=[list_directory], max_tool_calls=1)

    assert result == _DummySchema(value="forced")
    # The final forced call must NOT pass tools (mixing live tool-calling with forced JSON isn't reliable).
    assert "tools" not in fake_client.chat.completions.calls[-1] or not fake_client.chat.completions.calls[-1].get("tools")
