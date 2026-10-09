import app.services.repo_verification_agent as repo_verification_agent_module
from app.services.repo_verification_agent import (
    ClaimCheck,
    RepoVerificationResult,
    run_repo_verification_agent,
)


def test_skipped_when_no_source_dir():
    result = run_repo_verification_agent(None, "# My Project\nBuilt with FastAPI.")
    assert result["status"] == "skipped"


def test_skipped_when_no_readme(tmp_path):
    (tmp_path / "main.py").write_text("print('hi')")
    result = run_repo_verification_agent(str(tmp_path), "")
    assert result["status"] == "skipped"


def test_skipped_when_agent_disabled(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("print('hi')")
    monkeypatch.setattr(repo_verification_agent_module.settings, "ENABLE_REPO_VERIFICATION_AGENT", False)
    result = run_repo_verification_agent(str(tmp_path), "# README")
    assert result["status"] == "skipped"


def test_tools_can_actually_read_the_fixture_tree(tmp_path, monkeypatch):
    """Doesn't mock the tool functions themselves - only the Gemini call -
    so this proves list_directory/read_file/search_code genuinely work
    against a real directory, independent of whether Gemini is involved."""
    (tmp_path / "requirements.txt").write_text("fastapi>=0.100.0\nuvicorn\n")
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")

    captured_tools = {}

    def fake_call_structured_gemini(prompt, schema, tools=None):
        captured_tools["tools"] = tools
        # Exercise the tools exactly like the real model would, to prove
        # they work end-to-end against the real fixture directory.
        list_directory, read_file, search_code = tools
        assert "requirements.txt" in list_directory(".")
        assert "fastapi" in read_file("requirements.txt").lower()
        matches = search_code("FastAPI")
        assert any(m["file"] == "main.py" for m in matches)
        return RepoVerificationResult(
            claims_checked=[ClaimCheck(claim="Uses FastAPI", verdict="confirmed", evidence="requirements.txt lists fastapi; main.py imports FastAPI")],
            architecture_summary="A minimal FastAPI app.",
            red_flags=[],
            confidence=1.0,
        )

    monkeypatch.setattr(repo_verification_agent_module, "call_structured_gemini", fake_call_structured_gemini)

    result = run_repo_verification_agent(str(tmp_path), "# My Project\nBuilt with FastAPI.")

    assert result["status"] == "completed"
    assert result["claims_checked"][0]["verdict"] == "confirmed"
    assert result["confidence"] == 1.0
    assert len(captured_tools["tools"]) == 3


def test_confidence_forced_to_zero_when_model_never_calls_a_tool(tmp_path, monkeypatch):
    """The real guardrail against a confident-wrong-answer: if the model
    never actually calls list_directory/read_file/search_code, nothing was
    verified, so confidence is forced to 0 server-side regardless of what
    the model itself reports."""
    (tmp_path / "main.py").write_text("print('hi')")

    def fake_call_structured_gemini(prompt, schema, tools=None):
        # Deliberately never calls any of the tools.
        return RepoVerificationResult(
            claims_checked=[ClaimCheck(claim="Uses FastAPI", verdict="confirmed", evidence="made up")],
            architecture_summary="Guessed.",
            red_flags=[],
            confidence=0.95,  # the model claims high confidence despite never checking anything
        )

    monkeypatch.setattr(repo_verification_agent_module, "call_structured_gemini", fake_call_structured_gemini)

    result = run_repo_verification_agent(str(tmp_path), "# My Project\nBuilt with FastAPI.")

    assert result["confidence"] == 0.0


def test_path_traversal_blocked_in_tools(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("print('hi')")
    captured = {}

    def fake_call_structured_gemini(prompt, schema, tools=None):
        list_directory, read_file, search_code = tools
        captured["escape_attempt"] = read_file("../../../etc/passwd")
        captured["escape_listing"] = list_directory("../../")
        return RepoVerificationResult(claims_checked=[], architecture_summary="", red_flags=[], confidence=0.5)

    monkeypatch.setattr(repo_verification_agent_module, "call_structured_gemini", fake_call_structured_gemini)
    run_repo_verification_agent(str(tmp_path), "# README")

    assert captured["escape_attempt"] == "(file not found)"
    assert captured["escape_listing"] == []


def test_degrades_gracefully_on_llm_failure(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("print('hi')")

    def _raise(*a, **k):
        raise RuntimeError("All Gemini model candidates failed")

    monkeypatch.setattr(repo_verification_agent_module, "call_structured_gemini", _raise)

    result = run_repo_verification_agent(str(tmp_path), "# README")

    assert result["status"] == "error"
    assert result["confidence"] == 0.0
