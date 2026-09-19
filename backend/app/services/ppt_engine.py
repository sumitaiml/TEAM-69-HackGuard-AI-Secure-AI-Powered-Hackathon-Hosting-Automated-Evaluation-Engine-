import os
from typing import Any, Dict, List, Optional

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


def analyze_ppt_presentation(ppt_path: Optional[str]) -> Dict[str, Any]:
    """Module 10: PPT Analysis - real per-slide text extraction via
    python-pptx. Deterministic extraction only; qualitative judgment
    (missing sections, presentation quality, improvement suggestions) moves
    into the Gemini prompt in Phase 7 rather than being faked locally here."""
    if not ppt_path or not os.path.exists(ppt_path):
        return {"status": "skipped", "reason": "No presentation provided", "slide_count": 0, "slides": []}

    try:
        presentation = Presentation(ppt_path)
    except Exception as e:
        return {"status": "error", "reason": f"Could not open presentation: {e}", "slide_count": 0, "slides": []}

    slides: List[Dict[str, Any]] = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts = []
        has_image = False
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    texts.append(text)
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                has_image = True
        slides.append({
            "slide_number": index,
            "text": "\n".join(texts),
            "has_image": has_image,
        })

    return {
        "status": "completed",
        "slide_count": len(slides),
        "slides": slides,
    }
