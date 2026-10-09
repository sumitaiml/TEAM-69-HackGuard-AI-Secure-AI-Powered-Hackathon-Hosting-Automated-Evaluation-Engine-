import logging
import re
from typing import Any, Dict, Optional

from app.services import gemini_client
from app.services.pitch_deck_agent import run_pitch_deck_agent

logger = logging.getLogger(__name__)

_DEFAULT_RUBRIC_WEIGHTS = {
    "technical_complexity": 30.0,
    "innovation": 20.0,
    "ui_ux": 15.0,
    "business_impact": 15.0,
    "documentation": 10.0,
    "presentation": 10.0,
}

_NEUTRAL_SCORE = 70.0  # documented placeholder used when a signal is simply absent, not judged

_README_SECTION_PATTERNS = {
    "installation": r"##?\s*(installation|getting started|setup)",
    "usage": r"##?\s*usage",
    "architecture": r"##?\s*(architecture|design|how it works)",
}


def _deterministic_technical_score(static_report: Optional[Dict[str, Any]]) -> float:
    """60% real static-analysis code quality + 40% real sandbox test pass
    rate - both already computed by real tooling (Phases 4-5), so this
    parameter needs no LLM judgment at all."""
    code_quality = static_report.get("code_quality_score") if static_report else None
    code_quality = float(code_quality) if code_quality is not None else _NEUTRAL_SCORE

    sandbox_report = (static_report or {}).get("sandbox_execution") or {}
    passed = sandbox_report.get("unit_tests_passed", 0)
    failed = sandbox_report.get("unit_tests_failed", 0)
    total = passed + failed
    pass_rate = (passed / total * 100) if total > 0 else _NEUTRAL_SCORE

    return round(code_quality * 0.6 + pass_rate * 0.4, 2)


def _deterministic_documentation_score(readme_text: str) -> float:
    """Structural completeness only (length + presence of key sections) -
    the qualitative half (clarity, does it actually explain the project
    well) comes from Gemini's documentation_quality_score."""
    if not readme_text:
        return 10.0
    lower = readme_text.lower()
    sections_found = sum(1 for pattern in _README_SECTION_PATTERNS.values() if re.search(pattern, lower))
    length_score = min(len(readme_text) / 500.0, 1.0) * 40
    section_score = (sections_found / len(_README_SECTION_PATTERNS)) * 60
    return round(length_score + section_score, 2)


def _deterministic_presentation_score(ppt_report: Optional[Dict[str, Any]]) -> float:
    """Structural completeness only (do the slides actually have content) -
    the qualitative half comes from Gemini's presentation_quality_score."""
    if not ppt_report or ppt_report.get("status") != "completed":
        return _NEUTRAL_SCORE
    slides = ppt_report.get("slides", [])
    if not slides:
        return 20.0
    slides_with_text = sum(1 for s in slides if s.get("text"))
    return round((slides_with_text / len(slides)) * 100, 2)


def _ppt_slides_as_text(ppt_report: Optional[Dict[str, Any]]) -> str:
    if not ppt_report or ppt_report.get("status") != "completed":
        return ""
    return "\n".join(f"Slide {s['slide_number']}: {s['text']}" for s in ppt_report.get("slides", []) if s.get("text"))


def evaluate_project_with_ai(
    readme_text: str = "",
    tech_stack: str = "",
    static_report: Dict[str, Any] = None,
    plagiarism_report: Dict[str, Any] = None,
    whisper_report: Dict[str, Any] = None,
    ppt_report: Dict[str, Any] = None,
    rubric_weights: Dict[str, float] = None,
) -> Dict[str, Any]:
    """Module 5 & 12: AI Project Evaluation & Weighted Score Engine.

    Rubric split:
    - technical_complexity: fully deterministic (real static analysis +
      real sandbox pass rate) - never sent to Gemini to judge from scratch,
      since we already have real tooling for this signal.
    - innovation / ui_ux / business_impact: fully Gemini-judged.
    - documentation / presentation: hybrid - 50% deterministic structural
      completeness + 50% Gemini's qualitative read.
    """
    if rubric_weights is None:
        rubric_weights = dict(_DEFAULT_RUBRIC_WEIGHTS)

    tech_score = _deterministic_technical_score(static_report)
    doc_structural_score = _deterministic_documentation_score(readme_text)
    pres_structural_score = _deterministic_presentation_score(ppt_report)

    pitch_deck_result = run_pitch_deck_agent(ppt_report)
    pitch_deck_narrative_score = (
        pitch_deck_result["overall_narrative_score"] if pitch_deck_result.get("status") == "completed" else _NEUTRAL_SCORE
    )

    transcript = (whisper_report or {}).get("transcript", "")
    ppt_slides_text = _ppt_slides_as_text(ppt_report)

    degraded = False
    degraded_reason = None
    try:
        gemini_result = gemini_client.score_submission(
            readme_text=readme_text,
            ppt_slides_text=ppt_slides_text,
            transcript=transcript,
            tech_stack=tech_stack,
        )
        innov_score = gemini_result.innovation_score
        ui_score = gemini_result.ui_ux_score
        impact_score = gemini_result.business_impact_score
        doc_gemini_score = gemini_result.documentation_quality_score
        pres_gemini_score = gemini_result.presentation_quality_score
        ai_feedback = gemini_result.feedback
        improvement_suggestions = gemini_result.improvement_suggestions
    except Exception as e:
        logger.error("Gemini scoring failed after all retries/fallbacks: %s", e)
        degraded = True
        degraded_reason = str(e)
        innov_score = ui_score = impact_score = doc_gemini_score = pres_gemini_score = _NEUTRAL_SCORE
        ai_feedback = ["AI evaluation was unavailable for this submission - manual judge review is recommended."]
        improvement_suggestions = []

    doc_score = round(doc_structural_score * 0.5 + doc_gemini_score * 0.5, 2)
    # Pitch-deck agent weighted deliberately low (0.2) relative to the two
    # existing signals until it's validated against more real decks - see
    # AI_Agents_Implementation_Plan.md section 11.
    pres_score = round(pres_structural_score * 0.4 + pres_gemini_score * 0.4 + pitch_deck_narrative_score * 0.2, 2)

    parameter_scores = {
        "technical_complexity": tech_score,
        "innovation": innov_score,
        "ui_ux": ui_score,
        "business_impact": impact_score,
        "documentation": doc_score,
        "presentation": pres_score,
    }

    final_weighted_score = round(sum(
        parameter_scores[param] * (weight / 100.0)
        for param, weight in rubric_weights.items()
        if param in parameter_scores
    ), 2)

    result = {
        "overall_score": final_weighted_score,
        "parameter_scores": parameter_scores,
        "ai_feedback": ai_feedback,
        "improvement_suggestions": improvement_suggestions,
        "pitch_deck_analysis": pitch_deck_result,
        "ai_evaluation_degraded": degraded,
    }
    if degraded:
        result["degraded_reason"] = degraded_reason
    return result
