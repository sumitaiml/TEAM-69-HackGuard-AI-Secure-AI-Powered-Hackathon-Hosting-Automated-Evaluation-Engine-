from google.genai import types

import app.services.pitch_deck_agent as pitch_deck_agent_module
from app.services.pitch_deck_agent import (
    PitchDeckAnalysis,
    SlideCritique,
    _select_slides_for_image_inspection,
    run_pitch_deck_agent,
)


def _slide(number, text="", has_image=False, image_paths=None):
    return {"slide_number": number, "text": text, "has_image": has_image, "image_paths": image_paths or []}


def test_skipped_when_no_ppt_report():
    result = run_pitch_deck_agent(None)
    assert result["status"] == "skipped"


def test_skipped_when_ppt_status_not_completed():
    result = run_pitch_deck_agent({"status": "skipped", "slides": []})
    assert result["status"] == "skipped"


def test_skipped_when_agent_disabled(monkeypatch):
    monkeypatch.setattr(pitch_deck_agent_module.settings, "ENABLE_PITCH_DECK_AGENT", False)
    result = run_pitch_deck_agent({"status": "completed", "slides": [_slide(1, text="Problem statement here")]})
    assert result["status"] == "skipped"


def test_slide_selection_only_picks_text_sparse_image_slides(tmp_path):
    img = tmp_path / "fake.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)  # not a real PNG, just needs to exist for open()

    slides = [
        _slide(1, text="A" * 200, has_image=True, image_paths=[str(img)]),  # text-heavy - should NOT be selected
        _slide(2, text="short", has_image=True, image_paths=[str(img)]),     # sparse + image - SHOULD be selected
        _slide(3, text="also short but no image", has_image=False),          # sparse but no image - not selected
        _slide(4, text="", has_image=True, image_paths=[str(img)]),          # empty text + image - selected
    ]

    selected = _select_slides_for_image_inspection(slides)

    assert {s["slide_number"] for s in selected} == {2, 4}


def test_slide_selection_caps_at_max_image_fetches(tmp_path):
    img = tmp_path / "fake.png"
    img.write_bytes(b"fake")
    slides = [_slide(i, text="", has_image=True, image_paths=[str(img)]) for i in range(1, 11)]

    selected = _select_slides_for_image_inspection(slides)

    assert len(selected) == 6


def test_run_pitch_deck_agent_builds_multimodal_contents_for_image_slides(tmp_path, monkeypatch):
    img = tmp_path / "slide2.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fakeimagebytes")

    ppt_report = {
        "status": "completed",
        "slides": [
            _slide(1, text="Problem: hackathon judging takes too long and is inconsistent."),
            _slide(2, text="", has_image=True, image_paths=[str(img)]),
        ],
    }

    captured = {}

    def fake_call_structured_gemini(contents, schema):
        captured["contents"] = contents
        return PitchDeckAnalysis(
            slides=[
                SlideCritique(slide_number=1, narrative_role="problem", clarity_score=80.0, notes="Clear problem statement."),
                SlideCritique(slide_number=2, narrative_role="demo", clarity_score=70.0, notes="Screenshot of the dashboard."),
            ],
            missing_narrative_elements=["no team slide"],
            overall_narrative_score=75.0,
        )

    monkeypatch.setattr(pitch_deck_agent_module, "call_structured_gemini", fake_call_structured_gemini)

    result = run_pitch_deck_agent(ppt_report)

    assert result["status"] == "completed"
    assert result["overall_narrative_score"] == 75.0
    assert result["slides_inspected_visually"] == [2]
    # The multimodal contents list should contain an actual image Part for
    # slide 2 (it was selected) and only plain text for slide 1.
    image_parts = [p for p in captured["contents"] if isinstance(p, types.Part)]
    assert len(image_parts) == 1


def test_degrades_gracefully_on_llm_failure(monkeypatch):
    ppt_report = {"status": "completed", "slides": [_slide(1, text="Some slide text")]}

    def _raise(*a, **k):
        raise RuntimeError("All Gemini model candidates failed")

    monkeypatch.setattr(pitch_deck_agent_module, "call_structured_gemini", _raise)

    result = run_pitch_deck_agent(ppt_report)

    assert result["status"] == "error"
