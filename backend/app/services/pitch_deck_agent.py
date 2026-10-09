import logging
import mimetypes
import os
from typing import Any, Dict, List, Literal, Optional

from google.genai import types
from pydantic import BaseModel, Field

from app.config import settings
from app.services.gemini_client import call_structured_gemini

logger = logging.getLogger(__name__)

# Slides with less text than this are "text-sparse" - likely a mostly-visual
# slide (architecture diagram, screenshot, demo frame) that extracted text
# alone can't meaningfully judge. This, not a model tool-call, is what
# decides which slides get the extra multimodal look - the deterministic
# pre-filter approach used throughout this plan (same shape as the timeline
# agent's commit-history check and the plagiarism explainer's file-pair
# shortlist), since multimodal tokens run materially more expensive than
# text and there's no reason to make the model discover this via trial and
# error when a cheap heuristic already tells us which slides are worth it.
_SPARSE_TEXT_THRESHOLD_CHARS = 50
_MAX_IMAGE_FETCHES = 6


class SlideCritique(BaseModel):
    slide_number: int
    narrative_role: Literal["problem", "solution", "demo", "market_impact", "team", "other", "unclear"]
    clarity_score: float = Field(ge=0, le=100)
    notes: str


class PitchDeckAnalysis(BaseModel):
    slides: List[SlideCritique]
    missing_narrative_elements: List[str]
    overall_narrative_score: float = Field(ge=0, le=100)


def _select_slides_for_image_inspection(slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates = [
        s for s in slides
        if s.get("has_image") and s.get("image_paths") and len((s.get("text") or "")) < _SPARSE_TEXT_THRESHOLD_CHARS
    ]
    return candidates[:_MAX_IMAGE_FETCHES]


def _build_contents(slides: List[Dict[str, Any]], image_slide_numbers: set) -> List[Any]:
    parts: List[Any] = [
        "You are critiquing a hackathon pitch deck slide by slide. For each slide below, "
        "determine its narrative role in the pitch and how clearly it communicates that role. "
        "Some slides include their actual image since their extracted text alone is too sparse "
        "to judge (e.g. a diagram, screenshot, or demo frame) - look at those images directly.\n\n"
        "Respond with:\n"
        "- slides: one entry per slide below, with slide_number, narrative_role "
        "(problem/solution/demo/market_impact/team/other/unclear), clarity_score (0-100), "
        "and brief notes\n"
        "- missing_narrative_elements: e.g. \"no results/impact slide found\" - only real gaps\n"
        "- overall_narrative_score: 0-100, how well the deck as a whole tells a coherent pitch story"
    ]
    for slide in slides:
        slide_number = slide["slide_number"]
        text = slide.get("text") or "(no extracted text)"
        parts.append(f"\n### Slide {slide_number}\nText: {text}")
        if slide_number in image_slide_numbers:
            image_path = slide["image_paths"][0]
            try:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
                mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
                parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            except OSError as e:
                logger.warning("Could not read slide image %s: %s", image_path, e)
    return parts


def run_pitch_deck_agent(ppt_report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Module 10 add-on: the existing presentation score is built only from
    slide text fed into the main scoring call - it never looks at the
    deck's actual visual design. A deck that's mostly polished screenshots
    and diagrams with little text currently reads as "thin content," when
    it may be the strongest deck in the batch."""
    if not ppt_report or ppt_report.get("status") != "completed" or not ppt_report.get("slides"):
        return {"status": "skipped", "reason": "No presentation to analyze.", "slides": [], "missing_narrative_elements": [], "overall_narrative_score": 0.0}
    if not settings.ENABLE_PITCH_DECK_AGENT:
        return {"status": "skipped", "reason": "Pitch deck agent is disabled.", "slides": [], "missing_narrative_elements": [], "overall_narrative_score": 0.0}

    slides = ppt_report["slides"]
    image_slides = _select_slides_for_image_inspection(slides)
    image_slide_numbers = {s["slide_number"] for s in image_slides}

    try:
        contents = _build_contents(slides, image_slide_numbers)
        result = call_structured_gemini(contents, PitchDeckAnalysis)
        data = result.model_dump()
        data["status"] = "completed"
        data["slides_inspected_visually"] = sorted(image_slide_numbers)
        return data
    except Exception as e:
        logger.warning("Pitch deck agent LLM call failed: %s", e)
        return {
            "status": "error", "reason": str(e),
            "slides": [], "missing_narrative_elements": [], "overall_narrative_score": 0.0,
        }
