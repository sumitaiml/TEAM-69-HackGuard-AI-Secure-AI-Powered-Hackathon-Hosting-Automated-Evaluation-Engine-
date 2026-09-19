import logging
from typing import List

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiScoreResponse(BaseModel):
    innovation_score: float = Field(ge=0, le=100)
    ui_ux_score: float = Field(ge=0, le=100)
    business_impact_score: float = Field(ge=0, le=100)
    documentation_quality_score: float = Field(ge=0, le=100)
    presentation_quality_score: float = Field(ge=0, le=100)
    feedback: List[str]
    improvement_suggestions: List[str]


def _model_candidates() -> List[str]:
    candidates = [settings.GEMINI_MODEL] + [
        m.strip() for m in settings.GEMINI_MODEL_FALLBACKS.split(",") if m.strip()
    ]
    # de-dupe while preserving order
    seen = set()
    ordered = []
    for m in candidates:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered


def _is_retryable(exc: BaseException) -> bool:
    """Retry on transient server errors and rate limits (429) - a 404
    (model retired/unavailable) should instead advance to the next model
    candidate, not retry the same one, since retrying won't fix that."""
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, genai_errors.ClientError) and getattr(exc, "code", None) == 429:
        return True
    return False


def _build_prompt(readme_text: str, ppt_slides_text: str, transcript: str, tech_stack: str) -> str:
    return f"""You are an expert, discerning hackathon judge evaluating a project submission. \
Score fairly based only on the evidence given - do not invent details that aren't present, \
and do not default to the same score for every category.

## README
{readme_text or "(no README provided)"}

## Presentation slides (extracted text)
{ppt_slides_text or "(no presentation slides provided)"}

## Demo video transcript
{transcript or "(no demo video provided)"}

## Claimed tech stack
{tech_stack or "(not specified)"}

Score this submission from 0-100 on each dimension:
- innovation_score: originality and creativity of the idea
- ui_ux_score: quality of the user experience, as described or shown
- business_impact_score: real-world value and market potential
- documentation_quality_score: clarity and completeness of the README
- presentation_quality_score: how well the slides/demo communicate the project

Also provide:
- feedback: 2-4 short, specific strengths you noticed
- improvement_suggestions: 1-3 short, specific, actionable suggestions"""


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=2, max=30),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _call_model(client: "genai.Client", model_name: str, prompt: str) -> str:
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=GeminiScoreResponse,
        ),
    )
    return response.text


def score_submission(readme_text: str, ppt_slides_text: str, transcript: str, tech_stack: str) -> GeminiScoreResponse:
    """Raises on total failure across every model candidate - the caller
    (ai_evaluation.py) is responsible for the degraded-mode fallback so a
    Gemini outage doesn't fail the whole evaluation."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = _build_prompt(readme_text, ppt_slides_text, transcript, tech_stack)

    last_error: Exception = RuntimeError("No Gemini model candidates configured")
    for model_name in _model_candidates():
        try:
            raw = _call_model(client, model_name, prompt)
        except Exception as e:
            logger.warning("Gemini model %s failed: %s", model_name, e)
            last_error = e
            continue

        try:
            return GeminiScoreResponse.model_validate_json(raw)
        except Exception as validation_error:
            # One repair retry: ask the same model to fix its own output
            # before giving up on it and moving to the next candidate.
            logger.warning("Gemini model %s returned invalid schema, attempting repair: %s", model_name, validation_error)
            try:
                repair_prompt = (
                    "Your previous response was not valid JSON matching the required schema. "
                    f"Fix it and return ONLY the corrected JSON.\n\nPrevious response:\n{raw}"
                )
                repaired = _call_model(client, model_name, repair_prompt)
                return GeminiScoreResponse.model_validate_json(repaired)
            except Exception as e:
                logger.warning("Gemini model %s repair attempt also failed: %s", model_name, e)
                last_error = e
                continue

    raise RuntimeError(f"All Gemini model candidates failed: {last_error}") from last_error
