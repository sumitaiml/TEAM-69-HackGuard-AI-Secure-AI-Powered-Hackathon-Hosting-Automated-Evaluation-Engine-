import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.services.groq_client import call_agentic_groq

_MAX_READ_BYTES = 8000
_MAX_SEARCH_MATCHES = 30
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


class ClaimCheck(BaseModel):
    claim: str
    verdict: Literal["confirmed", "unconfirmed", "contradicted"]
    evidence: str


class RepoVerificationResult(BaseModel):
    claims_checked: List[ClaimCheck]
    architecture_summary: str
    red_flags: List[str]
    confidence: float = Field(ge=0, le=1)


def _safe_path(source_dir: str, relative_path: str) -> Optional[str]:
    """Same realpath-containment guard used by source_fetch.safe_extract_zip
    and plagiarism_explainer_agent.get_file_content - the model chooses
    relative_path itself, so it must be re-validated as untrusted input,
    not assumed safe just because it came from a tool-call argument."""
    dest_real = os.path.realpath(source_dir)
    target_real = os.path.realpath(os.path.join(source_dir, relative_path))
    if target_real != dest_real and not target_real.startswith(dest_real + os.sep):
        return None
    return target_real


def _build_prompt(readme_text: str) -> str:
    return f"""You are verifying whether a hackathon project's README claims match its \
actual codebase. You have tools to list directories, read files, and search code in the \
project's source tree - use them to check claims before reporting a verdict.

README:
{readme_text}

For each checkable claim in the README (technology stack, architecture, features, testing, \
etc.):
- Only report "confirmed" or "contradicted" for a claim you actually used a tool to check.
- Mark anything you didn't verify as "unconfirmed" - do not guess, and do not report a claim
  as confirmed just because it sounds plausible.

Respond with:
- claims_checked: list of {{claim, verdict, evidence}} - evidence must reference specific
  files or content you actually read via a tool
- architecture_summary: one paragraph, grounded only in files you actually read
- red_flags: e.g. "README claims tests exist; no test files found" - only things you checked
- confidence: 0-1, how much of the README's claims you were actually able to check"""


def run_repo_verification_agent(source_dir: Optional[str], readme_text: str) -> Dict[str, Any]:
    """Module 8 add-on: static analysis runs real tools against whatever
    code is there, but nothing checks whether the project IS what it claims
    to be. This agent reads the README's claims, then goes and checks them
    against the actual extracted source - the first agent in this codebase
    that needs genuine tool-calling, since (unlike the timeline or
    plagiarism-explainer agents) there's no deterministic pre-filter that
    can tell it in advance which files are worth looking at."""
    if not source_dir or not os.path.isdir(source_dir) or not readme_text.strip():
        return {
            "status": "skipped", "reason": "No source code or README to verify claims against.",
            "claims_checked": [], "architecture_summary": "", "red_flags": [], "confidence": 0.0,
        }
    if not settings.ENABLE_REPO_VERIFICATION_AGENT:
        return {
            "status": "skipped", "reason": "Repo verification agent is disabled.",
            "claims_checked": [], "architecture_summary": "", "red_flags": [], "confidence": 0.0,
        }

    tool_call_count = 0

    def list_directory(relative_path: str = ".") -> List[str]:
        """Lists file and subdirectory names at the given path, relative to the project root."""
        nonlocal tool_call_count
        target = _safe_path(source_dir, relative_path)
        if target is None or not os.path.isdir(target):
            return []
        tool_call_count += 1
        try:
            return sorted(
                name for name in os.listdir(target) if name not in _SKIP_DIRS
            )[:200]
        except OSError:
            return []

    def read_file(relative_path: str) -> str:
        """Reads the content of a single file, relative to the project root (truncated if large)."""
        nonlocal tool_call_count
        target = _safe_path(source_dir, relative_path)
        if target is None or not os.path.isfile(target):
            return "(file not found)"
        tool_call_count += 1
        try:
            with open(target, "rb") as f:
                return f.read(_MAX_READ_BYTES).decode("utf-8", errors="ignore")
        except OSError as e:
            return f"(could not read file: {e})"

    def search_code(pattern: str) -> List[Dict[str, Any]]:
        """Case-insensitive substring search across all source files. Returns up to 30 matches as {file, line, text}."""
        nonlocal tool_call_count
        matches: List[Dict[str, Any]] = []
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    with open(path, "r", errors="ignore") as f:
                        for line_no, line in enumerate(f, start=1):
                            if pattern.lower() in line.lower():
                                matches.append({
                                    "file": os.path.relpath(path, source_dir),
                                    "line": line_no,
                                    "text": line.strip()[:200],
                                })
                                if len(matches) >= _MAX_SEARCH_MATCHES:
                                    tool_call_count += 1
                                    return matches
                except OSError:
                    continue
        tool_call_count += 1
        return matches

    try:
        prompt = _build_prompt(readme_text)
        result = call_agentic_groq(
            prompt, RepoVerificationResult,
            tools=[list_directory, read_file, search_code],
            max_tool_calls=settings.AGENT_MAX_TOOL_CALLS,
        )
        data = result.model_dump()
        data["status"] = "completed"
        # Server-side override, not trusted from the model: if no tool was
        # ever actually called, nothing could have been verified regardless
        # of what confidence value the model reports - this is exactly the
        # "confident wrong answer" failure mode this agent is most at risk of.
        if tool_call_count == 0:
            data["confidence"] = 0.0
        return data
    except Exception as e:
        return {
            "status": "error", "reason": str(e),
            "claims_checked": [], "architecture_summary": "", "red_flags": [], "confidence": 0.0,
        }
