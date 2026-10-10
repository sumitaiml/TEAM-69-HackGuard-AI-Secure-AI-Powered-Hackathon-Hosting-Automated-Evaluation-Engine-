import logging
import os
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.services.groq_client import call_structured_groq
from app.services.plagiarism_engine import _jaccard_from_signatures

logger = logging.getLogger(__name__)

_CANDIDATE_SIMILARITY_THRESHOLD = 0.5
_MAX_FILE_PAIRS_IN_PROMPT = 5
_MAX_FILE_CONTENT_CHARS = 3000


class PlagiarismExplanation(BaseModel):
    verdict: Literal["likely_shared_boilerplate", "probable_copying", "inconclusive"]
    explanation: str
    cited_file_pairs: List[str]


def get_candidate_file_pairs(db: Session, submission_a_id: str, submission_b_id: str) -> List[Dict[str, Any]]:
    """Deterministic Python query, not a model tool-call - the per-file
    signatures already tell us exactly which file pairs are worth showing
    the explainer agent, so there's no reason to make the model discover
    this via trial and error."""
    rows_a = db.query(models.PlagiarismFileFingerprint).filter(
        models.PlagiarismFileFingerprint.submission_id == submission_a_id
    ).all()
    rows_b = db.query(models.PlagiarismFileFingerprint).filter(
        models.PlagiarismFileFingerprint.submission_id == submission_b_id
    ).all()

    pairs = []
    for row_a in rows_a:
        for row_b in rows_b:
            similarity = _jaccard_from_signatures(row_a.minhash_signature, row_b.minhash_signature)
            if similarity >= _CANDIDATE_SIMILARITY_THRESHOLD:
                pairs.append({
                    "file_a": row_a.file_path,
                    "file_b": row_b.file_path,
                    "similarity": round(similarity, 4),
                })
    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs


def get_file_content(source_dir: str, file_path: str, max_bytes: int = 6000) -> str:
    """Scoped to a single submission's already-extracted source directory -
    re-validates path containment (the same zip-slip-style guard used
    elsewhere in this codebase) since file_path ultimately traces back to
    data stored from a submission's own extracted archive."""
    dest_real = os.path.realpath(source_dir)
    target_real = os.path.realpath(os.path.join(source_dir, file_path))
    if target_real != dest_real and not target_real.startswith(dest_real + os.sep):
        return "(file path outside the submission's source directory - skipped)"
    try:
        with open(target_real, "rb") as f:
            return f.read(max_bytes).decode("utf-8", errors="ignore")
    except OSError as e:
        return f"(could not read file: {e})"


def _build_prompt(pairs: List[Dict[str, Any]], contents: Dict[str, str]) -> str:
    sections = []
    for pair in pairs:
        key_a = f"A:{pair['file_a']}"
        key_b = f"B:{pair['file_b']}"
        sections.append(
            f"### File pair (similarity {pair['similarity']:.0%}): {pair['file_a']} <-> {pair['file_b']}\n\n"
            f"--- Submission A: {pair['file_a']} ---\n{contents.get(key_a, '(not available)')}\n\n"
            f"--- Submission B: {pair['file_b']} ---\n{contents.get(key_b, '(not available)')}"
        )
    pairs_text = "\n\n".join(sections)

    return f"""You are reviewing why two hackathon submissions were flagged as similar by \
automated plagiarism detection. Below are the specific file pairs that matched, with their \
actual content.

{pairs_text}

Determine whether this is:
- likely_shared_boilerplate: common scaffolding, generated starter-template code, or
  trivial/generic code any team could independently produce (e.g. default config files,
  framework boilerplate, auto-generated code)
- probable_copying: substantive, non-generic logic that appears copied between the two
  submissions
- inconclusive: not enough evidence either way

Respond with:
- verdict: one of the three options above
- explanation: 2-4 sentences for an organizer reviewing this, in plain language, citing what
  specifically drove your verdict
- cited_file_pairs: which file pairs above you actually based your verdict on (e.g. "{pairs[0]['file_a']} <-> {pairs[0]['file_b']}")"""


def run_plagiarism_explainer_agent(db: Session, submission_id: str, matched_submission_id: str, source_dir: Optional[str]) -> Dict[str, Any]:
    """Module 6 add-on: today's MinHash check produces one number ("CRITICAL,
    82%") - an organizer still has to manually diff two codebases to tell
    real theft from two teams using the same boilerplate starter. This
    explains the match using the actual overlapping code, scoped to only
    the two already-flagged submissions (never the whole hackathon)."""
    pairs = get_candidate_file_pairs(db, submission_id, matched_submission_id)
    if not pairs:
        return {
            "verdict": "inconclusive",
            "explanation": "No per-file match was found above the similarity threshold to explain, despite the whole-submission signature being flagged.",
            "cited_file_pairs": [],
        }

    top_pairs = pairs[:_MAX_FILE_PAIRS_IN_PROMPT]

    matched_submission = db.query(models.Submission).filter(models.Submission.id == matched_submission_id).first()
    matched_source_dir = None
    if matched_submission:
        from app.services.source_fetch import extract_submission_source
        matched_source_dir = extract_submission_source(matched_submission)

    contents: Dict[str, str] = {}
    for pair in top_pairs:
        if source_dir:
            contents[f"A:{pair['file_a']}"] = get_file_content(source_dir, pair["file_a"], _MAX_FILE_CONTENT_CHARS)
        if matched_source_dir:
            contents[f"B:{pair['file_b']}"] = get_file_content(matched_source_dir, pair["file_b"], _MAX_FILE_CONTENT_CHARS)

    try:
        prompt = _build_prompt(top_pairs, contents)
        result = call_structured_groq(prompt, PlagiarismExplanation)
        return result.model_dump()
    except Exception as e:
        logger.warning("Plagiarism explainer LLM call failed: %s", e)
        return {
            "verdict": "inconclusive",
            "explanation": f"AI explanation was unavailable ({e}) - organizer should review the matched file pairs directly.",
            "cited_file_pairs": [f"{p['file_a']} <-> {p['file_b']}" for p in top_pairs],
        }
