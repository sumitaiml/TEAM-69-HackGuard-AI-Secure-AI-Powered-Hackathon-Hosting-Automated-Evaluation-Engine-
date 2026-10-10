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
    is_relevant_to_project: bool
    relevance_explanation: str


def _select_slides_for_image_inspection(slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    candidates = [
        s for s in slides
        if s.get("has_image") and s.get("image_paths") and len((s.get("text") or "")) < _SPARSE_TEXT_THRESHOLD_CHARS
    ]
    return candidates[:_MAX_IMAGE_FETCHES]


def _build_contents(slides: List[Dict[str, Any]], image_slide_numbers: set, readme_text: str) -> List[Any]:
    parts: List[Any] = [
        "You are critiquing a hackathon pitch deck slide by slide. First, check whether this "
        "deck is actually about the project described in the README below - teams sometimes "
        "upload an unrelated or placeholder file by mistake, and that should be caught rather "
        "than quietly scored as if it were a real (if weak) pitch for this project.\n\n"
        f"## Project README\n{readme_text or '(no README provided)'}\n\n"
        "Then, for each slide below, determine its narrative role in the pitch and how clearly "
        "it communicates that role. Some slides include their actual image since their "
        "extracted text alone is too sparse to judge (e.g. a diagram, screenshot, or demo "
        "frame) - look at those images directly.\n\n"
        "Respond with:\n"
        "- is_relevant_to_project: false ONLY if the deck's actual subject matter clearly does "
        "not match the README (e.g. a different project entirely, generic template content "
        "with no connection, or non-pitch content). If the README is missing or the deck is "
        "merely weak/incomplete, this should still be true - weakness is not irrelevance.\n"
        "- relevance_explanation: 1-2 sentences grounding your relevance verdict in what the "
        "deck actually contains vs. what the README describes\n"
        "- slides: one entry per slide below, with slide_number, narrative_role "
        "(problem/solution/demo/market_impact/team/other/unclear), clarity_score (0-100), "
        "and brief notes\n"
        "- missing_narrative_elements: e.g. \"no results/impact slide found\" - only real gaps\n"
        "- overall_narrative_score: 0-100, how well the deck as a whole tells a coherent pitch "
        "story for THIS project - score this 0 if is_relevant_to_project is false"
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


def run_pitch_deck_agent(ppt_report: Optional[Dict[str, Any]], readme_text: str = "") -> Dict[str, Any]:
    """Module 10 add-on: the existing presentation score is built only from
    slide text fed into the main scoring call - it never looks at the
    deck's actual visual design. A deck that's mostly polished screenshots
    and diagrams with little text currently reads as "thin content," when
    it may be the strongest deck in the batch.

    Also the only thing in the pipeline that checks whether the uploaded
    deck is even ABOUT the submitted project - everything else (innovation,
    business impact, documentation) is judged from the README/code alone,
    so an unrelated or placeholder deck would otherwise only cost a small
    slice of the 10%-weighted presentation score instead of being flagged.
    `is_relevant_to_project: True` is the safe default everywhere below
    (skipped/disabled/error) - absence of a check is not evidence of a
    mismatch, so it must never read as a red flag."""
    if not ppt_report or ppt_report.get("status") != "completed" or not ppt_report.get("slides"):
        return {
            "status": "skipped", "reason": "No presentation to analyze.", "slides": [],
            "missing_narrative_elements": [], "overall_narrative_score": 0.0,
            "is_relevant_to_project": True, "relevance_explanation": "",
        }
    if not settings.ENABLE_PITCH_DECK_AGENT:
        return {
            "status": "skipped", "reason": "Pitch deck agent is disabled.", "slides": [],
            "missing_narrative_elements": [], "overall_narrative_score": 0.0,
            "is_relevant_to_project": True, "relevance_explanation": "",
        }

    slides = ppt_report["slides"]
    image_slides = _select_slides_for_image_inspection(slides)
    image_slide_numbers = {s["slide_number"] for s in image_slides}

    try:
        contents = _build_contents(slides, image_slide_numbers, readme_text)
        result = call_structured_gemini(contents, PitchDeckAnalysis)
        data = result.model_dump()
        # Server-side override, not trusted from the model alone: if it
        # flagged the deck as irrelevant, force the narrative score to 0
        # regardless of what number it reported - the prompt asks for this,
        # but a model that praises an off-topic deck's "clarity" while also
        # marking it irrelevant should not get credit for either half.
        if not data["is_relevant_to_project"]:
            data["overall_narrative_score"] = 0.0
        data["status"] = "completed"
        data["slides_inspected_visually"] = sorted(image_slide_numbers)
        return data
    except Exception as e:
        logger.warning("Pitch deck agent LLM call failed: %s", e)
        return {
            "status": "error", "reason": str(e),
            "slides": [], "missing_narrative_elements": [], "overall_narrative_score": 0.0,
            "is_relevant_to_project": True,
            "relevance_explanation": "Relevance could not be checked - AI evaluation was unavailable.",
        }
