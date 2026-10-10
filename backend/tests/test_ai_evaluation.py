from app.services.gemini_client import GeminiScoreResponse
import app.services.ai_evaluation as ai_evaluation_module
from app.services.ai_evaluation import evaluate_project_with_ai

_FAKE_GEMINI_RESULT = GeminiScoreResponse(
    innovation_score=85.0,
    ui_ux_score=80.0,
    business_impact_score=75.0,
    documentation_quality_score=90.0,
    presentation_quality_score=88.0,  # deliberately high - should be overridden when the deck is irrelevant
    feedback=["Clear problem framing."],
    improvement_suggestions=["Add tests."],
)


def _run(monkeypatch, pitch_deck_result):
    monkeypatch.setattr(ai_evaluation_module.groq_client, "score_submission", lambda **kwargs: _FAKE_GEMINI_RESULT)
    monkeypatch.setattr(ai_evaluation_module, "run_pitch_deck_agent", lambda ppt_report, readme_text: pitch_deck_result)
    return evaluate_project_with_ai(
        readme_text="# AutoJudge\nAutomates hackathon judging.",
        tech_stack="FastAPI, React",
        static_report={"code_quality_score": 80.0, "sandbox_execution": {"unit_tests_passed": 4, "unit_tests_failed": 0}},
        plagiarism_report={"risk_level": "LOW"},
        whisper_report=None,
        ppt_report={"status": "completed", "slides": [{"slide_number": 1, "text": "x"}]},
    )


def test_relevant_pitch_deck_blends_normally(monkeypatch):
    result = _run(monkeypatch, {
        "status": "completed", "overall_narrative_score": 70.0,
        "is_relevant_to_project": True, "relevance_explanation": "Matches the README.",
    })

    # presentation = structural*0.4 + gemini*0.4 + narrative*0.2, not zeroed
    assert result["parameter_scores"]["presentation"] > 0
    assert result["pitch_deck_analysis"]["is_relevant_to_project"] is True


def test_irrelevant_pitch_deck_zeroes_presentation_score(monkeypatch):
    result = _run(monkeypatch, {
        "status": "completed", "overall_narrative_score": 0.0,
        "is_relevant_to_project": False, "relevance_explanation": "Deck is about something else entirely.",
    })

    # A high Gemini presentation_quality_score (88.0, judging the deck in
    # isolation) must NOT leak through once the deck is flagged irrelevant.
    assert result["parameter_scores"]["presentation"] == 0.0
    assert result["pitch_deck_analysis"]["is_relevant_to_project"] is False
    # Other dimensions, judged independently from the deck, are unaffected.
    assert result["parameter_scores"]["innovation"] == 85.0
    assert result["parameter_scores"]["technical_complexity"] > 0


def test_skipped_pitch_deck_result_does_not_zero_presentation(monkeypatch):
    # "skipped" (no presentation uploaded at all) must never be treated as
    # a relevance red flag - absence of a check is not evidence of a mismatch.
    result = _run(monkeypatch, {
        "status": "skipped", "overall_narrative_score": 0.0,
        "is_relevant_to_project": True, "relevance_explanation": "",
    })

    assert result["parameter_scores"]["presentation"] > 0
