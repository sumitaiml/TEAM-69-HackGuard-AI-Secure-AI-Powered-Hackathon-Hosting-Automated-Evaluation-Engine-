import os
from typing import Any, Dict, List, Optional

from datasketch import MinHash
from sqlalchemy.orm import Session
from tree_sitter_languages import get_parser

from app import models

_EXTENSION_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".c": "c",
    ".cpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
}

_SHINGLE_SIZE = 5
_NUM_PERM = 128
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def _tokenize_file(path: str) -> List[str]:
    ext = os.path.splitext(path)[1].lower()
    lang = _EXTENSION_LANGUAGE_MAP.get(ext)

    try:
        with open(path, "rb") as f:
            source_bytes = f.read()
    except OSError:
        return []

    if lang:
        try:
            parser = get_parser(lang)
            tree = parser.parse(source_bytes)
            tokens: List[str] = []

            def walk(node):
                if node.child_count == 0:
                    tokens.append(node.type)
                for child in node.children:
                    walk(child)

            walk(tree.root_node)
            return tokens
        except Exception:
            pass  # fall through to the generic text tokenizer below

    # Unrecognized language (or parse failure): a normalized whitespace
    # token stream is a weaker signal than an AST but still catches
    # near-verbatim copies, which covers the PRD's inter-submission MVP scope.
    text = source_bytes.decode("utf-8", errors="ignore")
    return text.split()


def _iter_source_files(source_dir: str) -> List[str]:
    paths = []
    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for fname in files:
            paths.append(os.path.join(root, fname))
    return paths


def compute_minhash_signature(source_dir: str) -> Optional[List[int]]:
    all_tokens: List[str] = []
    for path in _iter_source_files(source_dir):
        all_tokens.extend(_tokenize_file(path))

    if len(all_tokens) < _SHINGLE_SIZE:
        return None

    m = MinHash(num_perm=_NUM_PERM)
    for i in range(len(all_tokens) - _SHINGLE_SIZE + 1):
        shingle = " ".join(all_tokens[i:i + _SHINGLE_SIZE])
        m.update(shingle.encode("utf-8"))

    # Postgres INTEGER is 32-bit; datasketch's hash values are 64-bit, so mask
    # down for storage. The GIN index is only used to cheaply shortlist
    # candidates (array overlap) - the real Jaccard estimate below is
    # recomputed from the full signatures, so this loses no accuracy there.
    return [int(v) & 0x7FFFFFFF for v in m.hashvalues]


def _jaccard_from_signatures(sig_a: List[int], sig_b: List[int]) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return matches / len(sig_a)


def run_plagiarism_check(db: Session, submission: "models.Submission", source_dir: Optional[str]) -> Dict[str, Any]:
    """Module 6 & 7: Inter-submission plagiarism detection via AST-tokenized
    MinHash fingerprints, shortlisted through a Postgres GIN index instead of
    comparing against every other submission in the hackathon."""
    if not source_dir or not os.path.isdir(source_dir):
        return {
            "status": "skipped",
            "reason": "No source code available to fingerprint",
            "similarity_percentage": 0.0,
            "risk_level": "UNKNOWN",
            "flagged_matching_submission_id": None,
            "matched_sections": [],
        }

    signature = compute_minhash_signature(source_dir)
    if signature is None:
        return {
            "status": "skipped",
            "reason": "Not enough source content to fingerprint",
            "similarity_percentage": 0.0,
            "risk_level": "UNKNOWN",
            "flagged_matching_submission_id": None,
            "matched_sections": [],
        }

    file_count = len(_iter_source_files(source_dir))

    existing = db.query(models.PlagiarismFingerprint).filter(
        models.PlagiarismFingerprint.submission_id == submission.id
    ).first()
    if existing:
        existing.minhash_signature = signature
        existing.file_count = file_count
    else:
        db.add(models.PlagiarismFingerprint(
            submission_id=submission.id,
            hackathon_id=submission.hackathon_id,
            minhash_signature=signature,
            file_count=file_count,
        ))
    db.commit()

    # GIN-indexed array overlap (&&) shortlists candidates in roughly O(N)
    # instead of an O(N^2) pairwise scan across the whole hackathon.
    candidates = db.query(models.PlagiarismFingerprint).filter(
        models.PlagiarismFingerprint.hackathon_id == submission.hackathon_id,
        models.PlagiarismFingerprint.submission_id != submission.id,
        models.PlagiarismFingerprint.minhash_signature.overlap(signature),
    ).all()

    best_similarity = 0.0
    best_match_submission_id = None
    matched_sections = []
    for candidate in candidates:
        similarity = round(_jaccard_from_signatures(signature, candidate.minhash_signature) * 100, 2)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match_submission_id = candidate.submission_id
        if similarity > 40.0:
            matched_sections.append({
                "matched_submission_id": candidate.submission_id,
                "similarity_percentage": similarity,
            })

    risk_level = "LOW"
    if best_similarity > 70.0:
        risk_level = "CRITICAL"
    elif best_similarity > 40.0:
        risk_level = "MEDIUM"

    return {
        "status": "completed",
        "similarity_percentage": best_similarity,
        "risk_level": risk_level,
        "flagged_matching_submission_id": best_match_submission_id,
        "matched_sections": matched_sections,
        "file_count": file_count,
    }
