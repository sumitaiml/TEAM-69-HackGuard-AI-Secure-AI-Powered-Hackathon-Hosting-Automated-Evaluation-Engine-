import os
from typing import Any, Dict, List, Optional

from tree_sitter_languages import get_parser

# Reuses the same extension->language map pattern as plagiarism_engine.py.
_EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
}

_COMMENT_NODE_TYPES = {"comment", "line_comment", "block_comment"}
_IDENTIFIER_NODE_TYPES = {"identifier"}
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}

# Common scaffolding phrases that show up disproportionately often in
# LLM-authored code comments/docstrings - a real human hackathon team under
# time pressure rarely writes comments this way. This is a correlational
# signal, not proof - framed that way everywhere it's surfaced.
_BOILERPLATE_PHRASES = [
    "this function is responsible for", "this function does", "in this code",
    "here is the implementation", "here's how", "as an ai", "i cannot",
    "certainly!", "note: this", "this script", "the following code",
    "this class is used to", "this method", "below is",
]

# Generic placeholder-style identifier names - overreliance on these across
# many different functions (rather than domain-specific naming) is a weak
# but real signal of templated/generated code.
_GENERIC_IDENTIFIERS = {
    "data", "result", "response", "item", "value", "temp", "output", "input",
    "res", "obj", "arr", "val", "item1", "item2", "foo", "bar", "baz",
}


def _iter_source_files(source_dir: str) -> List[str]:
    paths = []
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in _EXTENSION_LANGUAGE_MAP:
                paths.append(os.path.join(root, fname))
    return paths


def _walk_nodes(node, callback) -> None:
    callback(node)
    for child in node.children:
        _walk_nodes(child, callback)


def _analyze_file(path: str) -> Optional[Dict[str, Any]]:
    ext = os.path.splitext(path)[1].lower()
    lang = _EXTENSION_LANGUAGE_MAP.get(ext)
    if not lang:
        return None

    try:
        with open(path, "rb") as f:
            source_bytes = f.read()
        parser = get_parser(lang)
        tree = parser.parse(source_bytes)
    except Exception:
        return None

    comment_chars = 0
    identifiers: List[str] = []

    def visit(node):
        nonlocal comment_chars
        if node.type in _COMMENT_NODE_TYPES:
            comment_chars += node.end_byte - node.start_byte
        elif node.type in _IDENTIFIER_NODE_TYPES and node.child_count == 0:
            identifiers.append(source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore").lower())

    _walk_nodes(tree.root_node, visit)

    text = source_bytes.decode("utf-8", errors="ignore")
    boilerplate_hits = sum(text.lower().count(phrase) for phrase in _BOILERPLATE_PHRASES)

    return {
        "total_chars": len(source_bytes),
        "comment_chars": comment_chars,
        "identifiers": identifiers,
        "boilerplate_hits": boilerplate_hits,
    }


def run_ai_code_detection_check(source_dir: Optional[str]) -> Dict[str, Any]:
    """Module 7: AI-Generated Code Detection.

    Entirely deterministic (no LLM call), mirroring how Module 6 (plagiarism)
    and Module 8 (static analysis) are also deterministic peer modules, not
    sub-steps of the single Gemini scoring call. Produces a correlational
    risk signal, not a verdict - the PRD's own Limitations section (14)
    explicitly calls for "an estimated confidence score rather than legal
    proof," and every surface showing this must frame it that way.
    """
    if not source_dir or not os.path.isdir(source_dir):
        return {
            "status": "skipped",
            "reason": "No source code available to analyze",
            "estimated_ai_usage_percentage": None,
            "confidence": 0.0,
            "risk_level": "UNKNOWN",
            "signals": {},
        }

    files = _iter_source_files(source_dir)
    if not files:
        return {
            "status": "skipped",
            "reason": "No recognized source files to analyze",
            "estimated_ai_usage_percentage": None,
            "confidence": 0.0,
            "risk_level": "UNKNOWN",
            "signals": {},
        }

    total_chars = 0
    total_comment_chars = 0
    total_boilerplate_hits = 0
    all_identifiers: List[str] = []

    for path in files:
        result = _analyze_file(path)
        if not result:
            continue
        total_chars += result["total_chars"]
        total_comment_chars += result["comment_chars"]
        total_boilerplate_hits += result["boilerplate_hits"]
        all_identifiers.extend(result["identifiers"])

    if total_chars == 0 or not all_identifiers:
        return {
            "status": "skipped",
            "reason": "Source files could not be parsed",
            "estimated_ai_usage_percentage": None,
            "confidence": 0.0,
            "risk_level": "UNKNOWN",
            "signals": {},
        }

    comment_density = round(total_comment_chars / total_chars, 4)
    generic_identifier_ratio = round(
        sum(1 for ident in all_identifiers if ident in _GENERIC_IDENTIFIERS) / len(all_identifiers), 4
    )
    identifier_diversity = round(len(set(all_identifiers)) / len(all_identifiers), 4)
    boilerplate_density = round(total_boilerplate_hits / max(len(files), 1), 4)

    # Each signal contributes points toward a 0-100 likelihood estimate.
    # Weights are a documented heuristic, not a trained/calibrated model -
    # this is explicitly an estimate (see docstring), not a certainty.
    score = 0.0
    score += min(comment_density * 150, 30)              # heavy over-commenting
    score += min(generic_identifier_ratio * 100, 25)      # generic naming overuse
    score += min((1 - identifier_diversity) * 40, 25)     # low naming diversity/repetition
    score += min(boilerplate_density * 20, 20)            # scaffolding phrases
    score = round(min(score, 100.0), 2)

    confidence = round(min(len(files) / 10.0, 1.0), 2)  # more files analyzed = more confidence in the estimate

    risk_level = "LOW"
    if score > 65:
        risk_level = "HIGH"
    elif score > 35:
        risk_level = "MEDIUM"

    return {
        "status": "completed",
        "estimated_ai_usage_percentage": score,
        "confidence": confidence,
        "risk_level": risk_level,
        "signals": {
            "comment_density": comment_density,
            "generic_identifier_ratio": generic_identifier_ratio,
            "identifier_diversity": identifier_diversity,
            "boilerplate_phrase_hits": total_boilerplate_hits,
            "files_analyzed": len(files),
        },
    }
