import os
import re
from typing import Any, Dict, List, Optional, Tuple

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}
_MAX_SEARCH_DEPTH = 2  # allow one level of "project inside a wrapper folder"


def _parse_pytest_output(logs: str) -> Dict[str, int]:
    match = re.search(r"(\d+) passed(?:, (\d+) failed)?", logs)
    if match:
        return {"passed": int(match.group(1)), "failed": int(match.group(2) or 0)}
    match = re.search(r"(\d+) failed", logs)
    if match:
        return {"passed": 0, "failed": int(match.group(1))}
    return {"passed": 0, "failed": 0}


def _parse_npm_test_output(logs: str) -> Dict[str, int]:
    # Jest-style summary line: "Tests:       1 failed, 4 passed, 5 total"
    match = re.search(r"Tests:\s+(?:(\d+) failed,\s*)?(\d+) passed", logs)
    if match:
        return {"passed": int(match.group(2)), "failed": int(match.group(1) or 0)}
    # Node's built-in test runner (`node --test`) TAP summary: "# pass 3" / "# fail 0"
    pass_match = re.search(r"# pass (\d+)", logs)
    if pass_match:
        fail_match = re.search(r"# fail (\d+)", logs)
        return {"passed": int(pass_match.group(1)), "failed": int(fail_match.group(1) if fail_match else 0)}
    # npm's own pass/fail summary as a fallback
    match = re.search(r"(\d+) passing", logs)
    if match:
        failed_match = re.search(r"(\d+) failing", logs)
        return {"passed": int(match.group(1)), "failed": int(failed_match.group(1) if failed_match else 0)}
    return {"passed": 0, "failed": 0}


PROFILES: List[Dict[str, Any]] = [
    {
        "name": "node",
        "marker": "package.json",
        "image": "node:20-slim",
        "install_cmd": ["sh", "-c", "npm install"],
        "run_cmd": ["sh", "-c", "npm test --if-present"],
        "parse_output": _parse_npm_test_output,
    },
    {
        "name": "python",
        "marker": "requirements.txt",
        "image": "python:3.11-slim",
        "install_cmd": ["sh", "-c", "pip install --no-cache-dir -r requirements.txt"],
        "run_cmd": ["sh", "-c", "pip install --no-cache-dir pytest -q >/dev/null 2>&1; pytest -q || true"],
        "parse_output": _parse_pytest_output,
    },
    {
        "name": "python-pyproject",
        "marker": "pyproject.toml",
        "image": "python:3.11-slim",
        "install_cmd": ["sh", "-c", "pip install --no-cache-dir ."],
        "run_cmd": ["sh", "-c", "pip install --no-cache-dir pytest -q >/dev/null 2>&1; pytest -q || true"],
        "parse_output": _parse_pytest_output,
    },
]


def _find_marker_dir(source_dir: str, marker: str) -> Optional[str]:
    source_dir = os.path.abspath(source_dir)
    for root, dirs, files in os.walk(source_dir):
        depth = root[len(source_dir):].count(os.sep)
        if depth > _MAX_SEARCH_DEPTH:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        if marker in files:
            return root
    return None


def detect_profile(source_dir: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Returns (profile, project_root) for the first recognized build system
    found under source_dir (searched up to 2 levels deep, to tolerate a zip
    with a single wrapper folder), or (None, None) if nothing recognized."""
    for profile in PROFILES:
        project_root = _find_marker_dir(source_dir, profile["marker"])
        if project_root:
            return profile, project_root
    return None, None
