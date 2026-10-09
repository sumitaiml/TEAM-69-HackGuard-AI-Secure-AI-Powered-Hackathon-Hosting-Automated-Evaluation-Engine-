import os
import subprocess
import uuid
from datetime import datetime, timedelta

import pytest

from app.services import timeline_agent
from app.services.timeline_agent import TimelineRiskAssessment, get_commit_log, run_timeline_risk_check


def _run_git(repo_dir, *args):
    subprocess.run(["git", *args], cwd=repo_dir, check=True, capture_output=True, text=True)


def _commit(repo_dir, filename, content, when: datetime, lines_of_padding=0):
    with open(os.path.join(repo_dir, filename), "w") as f:
        f.write(content)
        f.write("\n".join(f"line {i}" for i in range(lines_of_padding)))
    _run_git(repo_dir, "add", ".")
    env_date = when.strftime("%Y-%m-%dT%H:%M:%S")
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": env_date,
        "GIT_COMMITTER_DATE": env_date,
        "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@test.com",
        "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@test.com",
    }
    subprocess.run(["git", "commit", "-m", f"commit at {env_date}"], cwd=repo_dir, check=True, capture_output=True, text=True, env=env)


@pytest.fixture
def git_repo(tmp_path):
    repo_dir = str(tmp_path / "repo")
    os.makedirs(repo_dir)
    _run_git(repo_dir, "init", "-q")
    return repo_dir


class FakeSubmission:
    def __init__(self, github_url=None, readme_text="", submission_id=None):
        self.id = submission_id or f"test-{uuid.uuid4()}"
        self.github_url = github_url
        self.readme_text = readme_text


def test_get_commit_log_parses_timestamps_and_line_counts(git_repo):
    first = datetime(2026, 1, 1, 10, 0, 0)
    second = datetime(2026, 1, 2, 10, 0, 0)
    _commit(git_repo, "a.txt", "hello", first, lines_of_padding=5)
    _commit(git_repo, "b.txt", "world", second, lines_of_padding=2)

    commits = get_commit_log(git_repo)

    assert len(commits) == 2
    assert commits[0]["insertions"] > 0  # earliest-first
    assert "2026-01-01" in commits[0]["timestamp"]
    assert "2026-01-02" in commits[1]["timestamp"]


def test_get_commit_log_returns_empty_for_non_git_dir(tmp_path):
    assert get_commit_log(str(tmp_path)) == []


def test_not_applicable_when_no_github_url():
    result = run_timeline_risk_check(FakeSubmission(github_url=None), datetime(2026, 1, 1))
    assert result["status"] == "not_applicable"


def test_not_applicable_when_agent_disabled(monkeypatch):
    monkeypatch.setattr(timeline_agent.settings, "ENABLE_TIMELINE_AGENT", False)
    result = run_timeline_risk_check(FakeSubmission(github_url="https://example.com/repo.git"), datetime(2026, 1, 1))
    assert result["status"] == "not_applicable"


def test_clean_when_commits_are_within_hackathon_window(monkeypatch, git_repo):
    hackathon_start = datetime(2026, 1, 1, 0, 0, 0)
    _commit(git_repo, "a.txt", "hello", hackathon_start + timedelta(hours=2), lines_of_padding=5)

    monkeypatch.setattr(timeline_agent, "clone_repo_with_history", lambda url, dest, timeout=60: _copy_repo(git_repo, dest))
    called = {"gemini": False}
    def _fail_if_called(*a, **k):
        called["gemini"] = True
        raise AssertionError("Gemini should not be called for a clean timeline")
    monkeypatch.setattr(timeline_agent, "call_structured_gemini", _fail_if_called)

    result = run_timeline_risk_check(FakeSubmission(github_url="https://example.com/repo.git"), hackathon_start)

    assert result["status"] == "clean"
    assert result["risk_level"] == "LOW"
    assert called["gemini"] is False


def test_flagged_when_commits_predate_hackathon_start(monkeypatch, git_repo):
    hackathon_start = datetime(2026, 1, 10, 0, 0, 0)
    _commit(git_repo, "a.txt", "hello", hackathon_start - timedelta(days=5), lines_of_padding=5)

    monkeypatch.setattr(timeline_agent, "clone_repo_with_history", lambda url, dest, timeout=60: _copy_repo(git_repo, dest))
    fake_assessment = TimelineRiskAssessment(
        status="flagged", risk_level="HIGH",
        reasoning="Commit history predates the hackathon with no disclosed starter template.",
        suspicious_commits=["abc1234"],
    )
    monkeypatch.setattr(timeline_agent, "call_structured_gemini", lambda prompt, schema: fake_assessment)

    result = run_timeline_risk_check(FakeSubmission(github_url="https://example.com/repo.git"), hackathon_start)

    assert result["status"] == "flagged"
    assert result["risk_level"] == "HIGH"


def test_flagged_by_large_initial_commit_even_within_window(monkeypatch, git_repo):
    hackathon_start = datetime(2026, 1, 1, 0, 0, 0)
    # First commit has far more than the suspicious-initial-commit threshold
    _commit(git_repo, "a.txt", "hello", hackathon_start + timedelta(hours=1), lines_of_padding=1000)

    monkeypatch.setattr(timeline_agent, "clone_repo_with_history", lambda url, dest, timeout=60: _copy_repo(git_repo, dest))
    fake_assessment = TimelineRiskAssessment(
        status="flagged", risk_level="MEDIUM", reasoning="Unusually large initial commit.", suspicious_commits=[],
    )
    monkeypatch.setattr(timeline_agent, "call_structured_gemini", lambda prompt, schema: fake_assessment)

    result = run_timeline_risk_check(FakeSubmission(github_url="https://example.com/repo.git"), hackathon_start)

    assert result["status"] == "flagged"


def test_degrades_to_deterministic_flag_when_llm_fails(monkeypatch, git_repo):
    hackathon_start = datetime(2026, 1, 10, 0, 0, 0)
    _commit(git_repo, "a.txt", "hello", hackathon_start - timedelta(days=5), lines_of_padding=5)

    monkeypatch.setattr(timeline_agent, "clone_repo_with_history", lambda url, dest, timeout=60: _copy_repo(git_repo, dest))
    def _raise(*a, **k):
        raise RuntimeError("All Gemini model candidates failed")
    monkeypatch.setattr(timeline_agent, "call_structured_gemini", _raise)

    result = run_timeline_risk_check(FakeSubmission(github_url="https://example.com/repo.git"), hackathon_start)

    assert result["status"] == "flagged"
    assert result["risk_level"] == "MEDIUM"
    assert len(result["suspicious_commits"]) == 1


def _copy_repo(src_dir, dest_dir):
    import shutil
    shutil.copytree(src_dir, dest_dir)
    return dest_dir
