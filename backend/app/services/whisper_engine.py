import os
import subprocess
import tempfile
from typing import Any, Dict, Optional

from app.config import settings

_model = None  # lazy-loaded singleton - loading the model is slow (disk + init)


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(settings.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def _extract_audio_wav(video_path: str) -> str:
    """ffmpeg: isolate audio, downmix to mono, resample to 16kHz - the input
    format faster-whisper/Whisper models expect (PRD Section 10.3)."""
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-ar", "16000", "-ac", "1", "-vn", wav_path],
        check=True, capture_output=True, timeout=120,
    )
    return wav_path


def generate_whisper_transcript(video_path: Optional[str]) -> Dict[str, Any]:
    """Module 11: Demo Video Analysis - real speech-to-text via ffmpeg audio
    extraction + faster-whisper. Deterministic extraction only; qualitative
    judgment (communication quality, feature-claim coverage) moves into the
    Gemini prompt in Phase 7 rather than being faked locally a second time."""
    if not video_path or not os.path.exists(video_path):
        return {"status": "skipped", "reason": "No video provided", "transcript": "", "audio_processed": False}

    wav_path = None
    try:
        wav_path = _extract_audio_wav(video_path)
        model = _get_model()
        segments, info = model.transcribe(wav_path, beam_size=1)
        transcript = " ".join(seg.text.strip() for seg in segments).strip()
        return {
            "status": "completed",
            "transcript": transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "duration_seconds": round(info.duration, 2),
            "audio_processed": True,
        }
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")[-500:] if e.stderr else str(e)
        return {"status": "error", "reason": f"ffmpeg failed: {stderr}", "transcript": "", "audio_processed": False}
    except Exception as e:
        return {"status": "error", "reason": str(e), "transcript": "", "audio_processed": False}
    finally:
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
