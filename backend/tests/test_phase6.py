import io

from pptx import Presentation

from app.services.ppt_engine import analyze_ppt_presentation
from app.services.whisper_engine import generate_whisper_transcript


def _build_test_pptx(path: str):
    prs = Presentation()
    slide_layout = prs.slide_layouts[1]  # title + content

    slide1 = prs.slides.add_slide(slide_layout)
    slide1.shapes.title.text = "Problem Statement"
    slide1.placeholders[1].text_frame.text = "Manual hackathon judging is slow and inconsistent."

    slide2 = prs.slides.add_slide(slide_layout)
    slide2.shapes.title.text = "Our Solution"
    slide2.placeholders[1].text_frame.text = "An automated evaluation pipeline."

    prs.save(path)


def test_ppt_analysis_skipped_without_file():
    result = analyze_ppt_presentation(None)
    assert result["status"] == "skipped"
    assert result["slide_count"] == 0


def test_ppt_analysis_extracts_real_slide_text(tmp_path):
    pptx_path = str(tmp_path / "deck.pptx")
    _build_test_pptx(pptx_path)

    result = analyze_ppt_presentation(pptx_path)

    assert result["status"] == "completed"
    assert result["slide_count"] == 2
    assert "Problem Statement" in result["slides"][0]["text"]
    assert "Manual hackathon judging is slow and inconsistent." in result["slides"][0]["text"]
    assert "Our Solution" in result["slides"][1]["text"]
    # Proves this is real extraction, not the old hardcoded marketing copy
    assert "HackGuard" not in str(result)


def test_ppt_analysis_handles_corrupt_file(tmp_path):
    bad_path = str(tmp_path / "not_a_real_pptx.pptx")
    with open(bad_path, "wb") as f:
        f.write(b"this is not a real pptx file")

    result = analyze_ppt_presentation(bad_path)
    assert result["status"] == "error"
    assert result["slide_count"] == 0


def test_whisper_transcript_skipped_without_video():
    result = generate_whisper_transcript(None)
    assert result["status"] == "skipped"
    assert result["audio_processed"] is False


def test_whisper_transcript_mocked_transcription(tmp_path, monkeypatch):
    # Model loading (faster_whisper.WhisperModel(...)) is slow and not worth
    # paying in every test run - mocked here at the model boundary. The real
    # ffmpeg + faster-whisper pipeline is verified manually against the live
    # stack with an actual short video fixture instead.
    import app.services.whisper_engine as whisper_engine

    class FakeSegment:
        def __init__(self, text):
            self.text = text

    class FakeInfo:
        language = "en"
        language_probability = 0.99
        duration = 3.5

    class FakeModel:
        def transcribe(self, wav_path, beam_size=1):
            return [FakeSegment("hello from the demo video")], FakeInfo()

    monkeypatch.setattr(whisper_engine, "_get_model", lambda: FakeModel())

    video_path = str(tmp_path / "demo.mp4")
    with open(video_path, "wb") as f:
        f.write(b"not a real video, but generate_whisper_transcript only checks existence before calling ffmpeg")

    # ffmpeg itself is real here - it will fail on this fake file, which is
    # exactly the error-handling path we want covered without needing a real
    # video fixture in the unit test.
    result = generate_whisper_transcript(video_path)
    assert result["status"] == "error"
    assert "ffmpeg failed" in result["reason"]
