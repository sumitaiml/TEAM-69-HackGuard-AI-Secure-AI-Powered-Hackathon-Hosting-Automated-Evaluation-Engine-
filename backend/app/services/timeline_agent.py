import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

from app import models
from app.config import settings
from app.services.gemini_client import call_structured_gemini
from app.services.source_fetch import SourceFetchError, clone_repo_with_history

logger = logging.getLogger(__name__)

# A single from-scratch "hello world" commit is normally small. A first
# commit well beyond that is a classic signature of an already-built
# project being dumped into a fresh repo right as a hackathon starts -
# this is a documented heuristic threshold, not a calibrated model.
_SUSPICIOUS_INITIAL_COMMIT_LINES = 300

# Three independent patterns rather than one fully-optional combined regex -
# a regex where every group is optional can match a zero-length empty string
# at the very start of the line (before real content even begins), which
# `re.search` happily returns instead of ever reaching the real numbers.
_FILES_CHANGED_RE = re.compile(r"(\d+) files? changed")
_INSERTIONS_RE = re.compile(r"(\d+) insertions?\(\+\)")
_DELETIONS_RE = re.compile(r"(\d+) deletions?\(-\)")


class TimelineRiskAssessment(BaseModel):
    status: Literal["not_applicable", "clean", "flagged"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    reasoning: str
    suspicious_commits: List[str]


def _parse_git_timestamp(value: str) -> datetime:
    """git's %aI format is strict ISO-8601 - usually a +HH:MM offset, but a
    commit made in UTC renders as a bare 'Z' suffix instead, which Python's
    fromisoformat() only accepts from 3.11 onward (this runs on 3.10)."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_commit_log(repo_dir: str) -> List[Dict[str, Any]]:
    """Earliest-first commit log with per-commit insertion/deletion counts,
    parsed from `git log --shortstat` output (interleaved commit headers and
    stat lines, not structured data - this is the standard way to get both
    in one process invocation instead of two)."""
    try:
        result = subprocess.run(
            ["git", "log", "--reverse", "--pretty=format:COMMIT %H|%aI|%s", "--shortstat"],
            cwd=repo_dir, capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    commits: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for line in result.stdout.splitlines():
        if line.startswith("COMMIT "):
            if current:
                commits.append(current)
            sha, timestamp, message = line[len("COMMIT "):].split("|", 2)
            current = {"sha": sha, "timestamp": timestamp, "message": message, "insertions": 0, "deletions": 0, "files_changed": 0}
        elif current is not None and ("changed" in line or "insertion" in line or "deletion" in line):
            files_m = _FILES_CHANGED_RE.search(line)
            ins_m = _INSERTIONS_RE.search(line)
            del_m = _DELETIONS_RE.search(line)
            current["files_changed"] = int(files_m.group(1)) if files_m else 0
            current["insertions"] = int(ins_m.group(1)) if ins_m else 0
            current["deletions"] = int(del_m.group(1)) if del_m else 0
    if current:
        commits.append(current)
    return commits


def _build_prompt(commits: List[Dict[str, Any]], readme_text: str, hackathon_start: datetime) -> str:
    commit_lines = "\n".join(
        f"- {c['sha'][:8]} ({c['timestamp']}): {c['message']} "
        f"[+{c['insertions']}/-{c['deletions']}, {c['files_changed']} files]"
        for c in commits[:30]  # cap prompt size for unusually long histories
    )
    return f"""You are investigating whether a hackathon submission's codebase was built \
before the hackathon started, rather than during it.

Hackathon start date: {hackathon_start.isoformat()}

Commit history (earliest first):
{commit_lines}

README (check for any disclosed starter template, prior project, or boilerplate origin):
{readme_text or "(no README provided)"}

A deterministic check already flagged this submission as suspicious (commits predating \
the hackathon start, and/or an unusually large initial commit). Your job is to look for \
a LEGITIMATE explanation before concluding anything - a disclosed starter template, an \
explicitly mentioned prior personal project, or imported boilerplate the team is honest \
about. Only raise risk_level if no such explanation is evident in the README.

Respond with:
- status: always "flagged" (a deterministic pre-check already triggered this call)
- risk_level: LOW if there's a plausible innocent explanation, MEDIUM if uncertain, \
HIGH if the evidence strongly suggests a pre-built project was submitted as new
- reasoning: 2-3 sentences explaining your assessment
- suspicious_commits: short-form SHAs of commits that support your assessment, if any"""


def _clean_result(status: str, risk_level: str, reasoning: str, suspicious_commits: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"status": status, "risk_level": risk_level, "reasoning": reasoning, "suspicious_commits": suspicious_commits or []}


def run_timeline_risk_check(submission: "models.Submission", hackathon_start_date: Optional[datetime]) -> Dict[str, Any]:
    """Module 7-adjacent anti-cheating check: MinHash plagiarism (Module 6)
    only catches copying between submissions in the same hackathon - it has
    no way to catch a team submitting a project built before the hackathon
    even started, since there's nothing to compare a solo pre-built project
    against. This closes that gap via commit timestamps instead.

    Only ever invokes the LLM for submissions a deterministic pre-check has
    already flagged - the common (honest) case costs zero Gemini calls.
    """
    if not submission.github_url:
        return _clean_result("not_applicable", "LOW", "No GitHub URL on this submission - the timeline check only applies to repo-linked submissions, not ZIP uploads (which have no commit history at all).")

    if not settings.ENABLE_TIMELINE_AGENT:
        return _clean_result("not_applicable", "LOW", "Timeline agent is disabled.")

    history_dir = os.path.join(settings.WORKSPACE_ROOT, submission.id, "history")
    try:
        clone_repo_with_history(submission.github_url, history_dir)
    except SourceFetchError as e:
        return _clean_result("not_applicable", "LOW", f"Could not fetch commit history to check: {e}")

    try:
        commits = get_commit_log(history_dir)
    finally:
        shutil.rmtree(history_dir, ignore_errors=True)

    if not commits:
        return _clean_result("clean", "LOW", "No commit history was found to check.")

    earliest_dt = _parse_git_timestamp(commits[0]["timestamp"])
    first_commit_lines = commits[0]["insertions"]

    suspicious = bool(hackathon_start_date and earliest_dt < hackathon_start_date)
    suspicious = suspicious or first_commit_lines > _SUSPICIOUS_INITIAL_COMMIT_LINES

    if not suspicious:
        return _clean_result("clean", "LOW", "Commit history is consistent with work done during the hackathon window.")

    try:
        prompt = _build_prompt(commits, submission.readme_text or "", hackathon_start_date or earliest_dt)
        result = call_structured_gemini(prompt, TimelineRiskAssessment)
        return result.model_dump()
    except Exception as e:
        logger.warning("Timeline agent LLM call failed, falling back to the deterministic flag alone: %s", e)
        return _clean_result(
            "flagged", "MEDIUM",
            f"Deterministic check flagged this submission (commit history predates the hackathon start and/or an "
            f"unusually large initial commit), but AI reasoning to rule out an innocent explanation was unavailable: {e}",
            [commits[0]["sha"][:8]],
        )
