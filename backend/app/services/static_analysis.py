import json
import os
import subprocess
from typing import Any, Dict, List, Optional

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_SEMGREP_RULES = os.path.join(_BACKEND_ROOT, "tooling", "semgrep-rules.yml")
_ESLINT_CONFIG = os.path.join(_BACKEND_ROOT, "tooling", "eslint.default.json")

# TypeScript/JSX-with-types syntax isn't parseable by plain eslint:recommended
# without @typescript-eslint - .ts/.tsx are covered by Semgrep instead, and
# scanning only .js/.jsx here is a documented scope decision, not an oversight.
_JS_EXTENSIONS = {".js", ".jsx"}


def _walk_files(source_dir: str) -> List[str]:
    paths = []
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv")]
        for fname in files:
            paths.append(os.path.join(root, fname))
    return paths


def _run_semgrep(source_dir: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["semgrep", "--config", _SEMGREP_RULES, "--json", "--quiet", "--timeout", "60", source_dir],
            capture_output=True,
            text=True,
            timeout=90,
        )
        data = json.loads(result.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        return {"findings": [], "error": str(e)}

    findings = []
    for r in data.get("results", []):
        findings.append({
            "tool": "Semgrep",
            "rule_id": r.get("check_id"),
            "severity": r.get("extra", {}).get("severity", "WARNING"),
            "message": r.get("extra", {}).get("message", "").strip(),
            "path": os.path.relpath(r.get("path", ""), source_dir),
            "line": r.get("start", {}).get("line"),
        })
    return {"findings": findings, "error": None}


def _run_pylint(source_dir: str, python_files: List[str]) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["pylint", "--output-format=json", "--disable=C0114,C0115,C0116", *python_files],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=source_dir,
        )
        data = json.loads(result.stdout or "[]")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        return {"smells": [], "error": str(e)}

    smells = []
    for item in data:
        smells.append({
            "tool": "Pylint",
            "rule_id": item.get("symbol") or item.get("message-id"),
            "severity": item.get("type", "convention").upper(),
            "message": item.get("message", ""),
            "path": item.get("path"),
            "line": item.get("line"),
        })
    return {"smells": smells, "error": None}


def _run_eslint(source_dir: str, js_files: List[str]) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["eslint", "--no-eslintrc", "-c", _ESLINT_CONFIG, "--format", "json", *js_files],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=source_dir,
        )
        data = json.loads(result.stdout or "[]")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        return {"findings": [], "error": str(e)}

    findings = []
    for file_result in data:
        for msg in file_result.get("messages", []):
            findings.append({
                "tool": "ESLint",
                "rule_id": msg.get("ruleId") or "parse-error",
                "severity": "ERROR" if msg.get("severity") == 2 else "WARNING",
                "message": msg.get("message", ""),
                "path": os.path.relpath(file_result.get("filePath", ""), source_dir),
                "line": msg.get("line"),
            })
    return {"findings": findings, "error": None}


def run_static_code_analysis(source_dir: Optional[str]) -> Dict[str, Any]:
    """Module 8: Static Code Analysis - runs real Semgrep (custom security
    ruleset), Pylint (Python files), and ESLint (JS/JSX files) against the
    submission's actual extracted source code."""
    if not source_dir or not os.path.isdir(source_dir):
        return {
            "status": "skipped",
            "reason": "No source code available to analyze (no zip upload or repo URL)",
            "code_quality_score": None,
            "security_vulnerabilities": [],
            "code_smells": [],
            "tools_executed": [],
            "metrics": {},
        }

    all_files = _walk_files(source_dir)
    python_files = [f for f in all_files if f.endswith(".py")]
    js_files = [f for f in all_files if os.path.splitext(f)[1] in _JS_EXTENSIONS]

    tools_executed = []
    vulnerabilities: List[Dict[str, Any]] = []
    code_smells: List[Dict[str, Any]] = []

    if all_files:
        semgrep_result = _run_semgrep(source_dir)
        tools_executed.append("Semgrep")
        vulnerabilities.extend(semgrep_result["findings"])

    if python_files:
        pylint_result = _run_pylint(source_dir, python_files)
        tools_executed.append("Pylint")
        code_smells.extend(pylint_result["smells"])

    if js_files:
        eslint_result = _run_eslint(source_dir, js_files)
        tools_executed.append("ESLint")
        vulnerabilities.extend(eslint_result["findings"])

    critical_count = sum(1 for v in vulnerabilities if v.get("severity") in ("ERROR", "CRITICAL"))
    warning_count = len(vulnerabilities) - critical_count
    score = 100 - (critical_count * 20) - (warning_count * 5) - (len(code_smells) * 1)
    score = max(score, 0)

    return {
        "status": "completed",
        "code_quality_score": score,
        "security_vulnerabilities": vulnerabilities,
        "code_smells": code_smells,
        "tools_executed": tools_executed,
        "metrics": {
            "total_files_analyzed": len(all_files),
            "python_files": len(python_files),
            "js_files": len(js_files),
        },
    }
