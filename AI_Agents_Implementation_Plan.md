# HackGuard AI — Agentic Evaluation Modules: Implementation Plan

**Document Version:** 2.1 — corrected per-agent timeout mechanism and closed the task-status/frontend stage-reporting gap
**Status:** Design proposal — nothing in this document is implemented yet
**Scope:** 4 of the 5 agents discussed are covered here. The **Judge Q&A / Score-Explanation Agent** is explicitly excluded per direction and should be scoped as its own follow-up document.
**Agents covered:** Repo Verification Agent · Plagiarism Explainer Agent · Pitch-Deck Reasoning Agent · Anti-Cheating / Timeline Agent

---

## 1. Why these are "agents" and not just bigger prompts

The platform's existing AI step (`backend/app/services/gemini_client.py::score_submission`) is a **single-shot structured-output call**: one prompt in, one `GeminiScoreResponse` JSON out, with model-fallback and a one-time repair retry. It cannot look at anything it wasn't handed up front.

All four modules below are different in kind: each one is given a small set of **callable tools** and decides, turn by turn, what to inspect before producing a final answer. That loop — "look, then decide what to look at next" — is what makes something an agent rather than a prompt.

Mechanically, this is built on a capability the project's existing `google-genai` SDK already has and is already paying the setup cost for: **Automatic Function Calling (AFC)**. (The "AFC is enabled with max remote calls: 10" line already visible in worker logs today is this exact feature — it's on by default, just unused because no `tools` are currently passed to `generate_content`.) Passing plain Python functions as `tools` lets the SDK run the look→decide→look-again loop itself, up to a configurable call cap, with no new dependency.

---

## 2. Shared agent runtime (build once, reuse four times)

New file: **`backend/app/services/agent_runtime.py`**

```python
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Callable, List, Type, TypeVar

T = TypeVar("T", bound=BaseModel)

def run_tool_agent(
    system_prompt: str,
    user_prompt: str,
    tools: List[Callable],
    response_schema: Type[T],
    max_tool_calls: int = 10,
    model_candidates: List[str] = None,
) -> T:
    """Shared tool-calling loop for every agent in this document. Reuses the
    same model-fallback + retry scaffolding as gemini_client.py's
    score_submission(), just generalized to accept arbitrary tools and an
    arbitrary Pydantic response_schema instead of being hardcoded to
    GeminiScoreResponse."""
```

### This is a refactor of `gemini_client.py`, not just new code alongside it

`_model_candidates()` (line 25-36), `_is_retryable()` (line 39-47), and `_call_model()` + its `@retry` decorator (line 79-95) already exist in `gemini_client.py` today. Moving them into `agent_runtime.py` means **`gemini_client.py` itself must be rewritten to import and call into `agent_runtime.py`** for its own `score_submission()` call — otherwise the retry/fallback logic ends up duplicated in two places and drifts out of sync the first time either one is touched. This needs to be an explicit step in Phase 13 (where the harness is first built), not an afterthought.

What's new on top of what's being moved:
- `tools=[...]` passed into `types.GenerateContentConfig`, each a plain Python function with a docstring and type hints (the SDK auto-generates the function-calling schema from these — no manual JSON schema authoring needed).
- `automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=max_tool_calls)` — this is the cost/runaway-loop guardrail. Every agent below gets a hard cap on how many tool calls it can make before being forced to answer with whatever it's learned so far.
- Each agent still ends with `response_mime_type="application/json", response_schema=<AgentSpecificPydanticModel>` — same structured-output discipline as the existing `GeminiScoreResponse`, so output is always parseable, never free text.

### Config additions (`backend/app/config.py` / `.env`)

```
ENABLE_REPO_VERIFICATION_AGENT=true
ENABLE_PLAGIARISM_EXPLAINER_AGENT=true
ENABLE_PITCH_DECK_AGENT=true
ENABLE_TIMELINE_AGENT=true
AGENT_MAX_TOOL_CALLS=10
AGENT_TIMEOUT_SECONDS=45
```

Each agent is **independently feature-flagged**. This matters because these four are being proposed as incremental phases (see §10) — a flag lets any one of them be disabled instantly (cost spike, bad output in the field) without touching the other three or the core deterministic pipeline, which must never be allowed to regress.

### Per-agent timeouts — Celery's `soft_time_limit` is the wrong tool for this

Earlier drafts of this document said to "wrap each agent call with Celery's `soft_time_limit`." That's not just under-specified, it's **mechanically the wrong mechanism** for what's needed here, and worth correcting properly rather than just adding detail:

Celery's `soft_time_limit` (set via `task_soft_time_limit` in app config, the `@task(soft_time_limit=...)` decorator, or per-call in `apply_async()`) always bounds **the entire task invocation**, timed from when the worker starts executing the task function to when it raises `SoftTimeLimitExceeded`. It cannot be scoped to one internal section of a single task's code. `run_full_evaluation_task` is deliberately one flat function covering the whole pipeline (source fetch → static analysis → plagiarism → sandbox → media analysis → AI scoring) — so setting *any* `task_soft_time_limit` on it, global or per-task, would bound the **whole pipeline's total runtime**, not just a new agent step. Given the sandbox step alone already runs up to `DOCKER_TIMEOUT_SECONDS=60`, a blanket limit tight enough to bound one agent call (`AGENT_TIMEOUT_SECONDS=45`) would risk killing the entire evaluation, static analysis and all, for reasons unrelated to any agent.

**What actually gives per-agent-step granularity:** a Python-level timeout around just that call, inside the task function, independent of Celery's own time-limit machinery:

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

def run_agent_with_timeout(fn, *args, timeout=settings.AGENT_TIMEOUT_SECONDS, **kwargs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            raise AgentTimeoutError(f"{fn.__name__} exceeded {timeout}s")
```

Each agent call in `evaluation_tasks.py` goes through this wrapper, with a `try/except AgentTimeoutError` applying the same degrade-don't-fail handling the pipeline already applies to a Gemini outage today — extended to per-agent granularity (`repo_verification_degraded`, `timeline_check_degraded`, etc.) rather than one blanket `ai_evaluation_degraded` flag. (Celery's own `time_limit`/`soft_time_limit` is still worth setting on `run_full_evaluation_task` separately, as a coarse whole-pipeline safety net — but generously, e.g. 300s covering every stage combined, not as the per-agent control.)

---

## 3. Agent 1 — Repo Verification Agent

**Feasibility: HIGH** — no hard prerequisites. It reads the already-extracted `source_dir` from `extract_submission_source()`, which already runs before it in the pipeline today. This is the agent with the shortest path to a working prototype and a reasonable candidate to build `agent_runtime.py` against first, even if Phase 11 (Timeline) is what ships to production first (see §10).

**Purpose:** The README says "built with FastAPI, PostgreSQL, and a microservices architecture." Is that true? Static analysis today runs Semgrep/Pylint/ESLint against whatever's there, but nothing checks whether the project *is what it claims to be*. This agent reads the claim, then goes and checks.

**New file:** `backend/app/services/repo_verification_agent.py`

### Tools (scoped to the already-extracted source directory)

Reuses `extract_submission_source()` from `source_fetch.py` — no new fetching logic. All three tools below take paths **relative to** that submission's `src/` directory and must re-validate with the same realpath-containment check already used in `source_fetch.safe_extract_zip` (zip-slip-style guard) before touching disk, so a hostile submission can't get the agent to read files outside its own sandboxed source tree:

```python
def list_directory(relative_path: str = ".") -> list[str]: ...
def read_file(relative_path: str, max_bytes: int = 8000) -> str: ...
def search_code(pattern: str) -> list[dict]: ...  # grep-style, returns {file, line, text}
```

`read_file`'s `max_bytes` cap and `search_code`'s match-count cap (propose: 30 matches) exist for the same reason `AGENT_MAX_TOOL_CALLS` exists — bound the worst case before it becomes a cost or latency problem.

### Output schema

```python
class RepoVerificationResult(BaseModel):
    claims_checked: list[ClaimCheck]   # {claim, verdict: "confirmed"|"unconfirmed"|"contradicted", evidence}
    architecture_summary: str          # one paragraph, grounded only in files actually read
    red_flags: list[str]               # e.g. "README claims tests exist; no test files found"
    confidence: float                  # 0-1, how much of the README's claims it could actually check
```

### Touchpoints in existing code

| File | Change |
|---|---|
| `tasks/evaluation_tasks.py` | New stage after `static_analysis` (line 37-38), guarded by `settings.ENABLE_REPO_VERIFICATION_AGENT` |
| `models.py` | + `EvaluationReport.repo_verification_json` (JSON, nullable) — line 83-96 |
| `schemas.py` | + `repo_verification_json: Optional[Dict[str, Any]]` on `EvaluationReportOut` (line 120) |
| `config.py` | + `ENABLE_REPO_VERIFICATION_AGENT` flag |
| *(new)* `services/repo_verification_agent.py` | The agent itself |

```python
self.update_state(state="PROGRESS", meta={"stage": "repo_verification"})
if settings.ENABLE_REPO_VERIFICATION_AGENT:
    repo_verification = run_repo_verification_agent(source_dir, sub.readme_text)
```

**API note:** `evaluation_router.py`'s existing `/report/{submission_id}` endpoint returns `EvaluationReportOut` as-is — once `repo_verification_json` is added to that schema, the endpoint itself needs **no route changes**, only the schema addition above.

### Surfacing

OrganizerDashboard's existing "Fraud & Plagiarism" tab gains a second table/section: "Claim Verification" with the claim/verdict/evidence rows. Judge's "AI Report Reader" tab gains a matching panel.

### Risk & mitigation

The main failure mode is a **confident wrong answer** — claiming to have checked something it didn't actually call a tool for. Mitigation: the system prompt must explicitly instruct "only report a verdict for claims you called `read_file` or `search_code` to check; otherwise mark `unconfirmed`", and `confidence` should be computed server-side (not trusted from the model) as `claims_with_a_tool_call_backing / total_claims`, cross-referenced against the tool-call transcript the SDK returns.

---

## 4. Agent 2 — Plagiarism Explainer Agent

**Feasibility: MEDIUM** — gated on one schema migration before any agent code can run.

**Purpose:** Today, `plagiarism_engine.py` produces one number: a Jaccard similarity estimate between two submissions' *whole-codebase* MinHash signatures. An organizer sees "CRITICAL, 82%" and has to manually diff two codebases to find out if that's real theft or just two teams using the same boilerplate starter. This agent does that diffing and writes the explanation.

### Required prerequisite: per-file fingerprints, not just one aggregate

This is the one agent that **cannot be built on top of the current data model as-is**. `compute_minhash_signature()` concatenates every file in the submission into one token stream and produces a single signature for the whole codebase (`plagiarism_engine.py:72-89`). There is no record of *which files* contributed to a match — so there is nothing concrete for an explainer agent to point at.

**Required change:** compute and store a MinHash signature **per source file**, not just one per submission.

New table (Alembic migration required — see §8):

```python
class PlagiarismFileFingerprint(Base):
    __tablename__ = "plagiarism_file_fingerprints"
    id = Column(String, primary_key=True, default=generate_uuid)
    submission_id = Column(String, ForeignKey("submissions.id"), nullable=False)
    file_path = Column(String, nullable=False)       # relative path within the submission
    minhash_signature = Column(ARRAY(Integer), nullable=False)
    __table_args__ = (
        Index("ix_plagiarism_file_fingerprints_gin", "minhash_signature", postgresql_using="gin"),
    )
```

> **PostgreSQL dependency note:** this adds a *second* `ARRAY(Integer) + GIN index` construct to the schema (the first being the existing `PlagiarismFingerprint` table). SQLite was already incompatible with this project because of that first table — the stray `hackguard.db`/`test_hackguard.db` files at the repo root predate the Postgres migration and don't work with the current schema regardless. This change doesn't newly break SQLite; it just makes the existing hard Postgres dependency more explicit. No action needed beyond knowing there is no path back to SQLite for local dev or tests.

`run_plagiarism_check` keeps computing the existing whole-submission signature (that's what drives the fast GIN-shortlisted candidate search and the headline risk level — no change to that cost-performance characteristic) but *additionally* writes one row per file here. Only once a pair of submissions is already flagged MEDIUM/CRITICAL by the existing whole-submission check does anything touch this per-file table — so the extra storage/compute only happens for the submissions that already warranted a closer look.

### Tools

```python
def get_candidate_file_pairs(submission_a: str, submission_b: str) -> list[dict]:
    # server-side, NOT a model tool-call: queries PlagiarismFileFingerprint
    # for the two submissions, returns file-pairs whose per-file Jaccard
    # similarity exceeds a threshold (propose 0.5), pre-sorted by similarity.
    ...

def get_file_content(submission_id: str, file_path: str, max_bytes: int = 6000) -> str: ...
```

`get_candidate_file_pairs` is a deterministic pre-filter run in Python *before* the agent starts (not a tool the model calls) — it would be wasteful to let the model discover via trial-and-error which files to compare when the per-file signatures already tell us exactly which pairs are worth showing it. The agent's only real tool is `get_file_content`, scoped to **only the two already-flagged submissions** (never the whole hackathon) — pass both submission IDs in as fixed context, not agent-discoverable.

### Output schema

```python
class PlagiarismExplanation(BaseModel):
    verdict: Literal["likely_shared_boilerplate", "probable_copying", "inconclusive"]
    explanation: str                 # for the organizer, plain language
    cited_file_pairs: list[str]      # which files it actually compared
```

### Trigger & storage

```python
# In evaluation_tasks.py, after run_plagiarism_check():
if (plagiarism_report.get("risk_level") in ("MEDIUM", "CRITICAL")
        and settings.ENABLE_PLAGIARISM_EXPLAINER_AGENT):
    plagiarism_report["explanation"] = run_plagiarism_explainer_agent(sub.id, plagiarism_report)
```

Only runs when `plagiarism_json.risk_level` is `MEDIUM` or `CRITICAL` (cost gating — most submissions never reach this). Output stored as `plagiarism_json["explanation"]` (nested into the existing field, since it's additive context for an existing result, not a new concern).

### Risk & mitigation

This is the most **legally/socially sensitive** agent — it is one step from "accusing a team of cheating." Mitigations:
- `verdict` is always framed as input *to an organizer's own judgment*, never auto-published to the public leaderboard or to the accused team directly.
- System prompt must require every claim in `explanation` to cite a specific file in `cited_file_pairs` — no vague "this looks copied."
- The frontend must visibly label this "AI-flagged for organizer review" wherever it's shown — never present it as a finding of fact.

---

## 5. Agent 3 — Pitch-Deck Reasoning Agent

**Feasibility: MEDIUM** — gated on a prerequisite change plus real cost discipline (multimodal tokens run 5-10× more expensive than text).

**Purpose:** Today's presentation score is one number, built from `ppt_engine.py`'s slide **text** fed into the same single Gemini call as everything else. It never looks at the deck's actual visual design, diagrams, or screenshots — `ppt_engine.py` already detects `has_image: bool` per slide (`ppt_engine.py:30-31`) but discards the image itself. A deck that's all polished screenshots and almost no text currently reads as "thin content" to the pipeline, when it may actually be the strongest deck in the batch.

### Required prerequisite: extract slide images, not just a boolean

**Change to `ppt_engine.py`:** for any slide where `has_image` is true, also extract and save the image bytes (python-pptx exposes `shape.image.blob` for picture shapes).

```python
# Current (line 30-31):
if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
    has_image = True

# Needs to become:
if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
    has_image = True
    image_path = os.path.join(slides_dir, f"slide_{index}_{shape.shape_id}.png")
    with open(image_path, "wb") as f:
        f.write(shape.image.blob)
    image_paths.append(image_path)
```

> **Signature blocker:** `analyze_ppt_presentation(ppt_path)` currently has no knowledge of `submission_id` or `WORKSPACE_ROOT` — it only takes a file path. To write images to `{WORKSPACE_ROOT}/{submission_id}/slides/...` it needs `submission_id` and the workspace root passed in (changing the function's signature and its one caller in `evaluation_tasks.py`), **or** image extraction needs to move to its own step in `evaluation_tasks.py` that already has both of those in scope. This is a real, non-trivial change to an existing function signature, not a drop-in addition — plan for it explicitly in Phase 14, including updating the one existing call site and the existing `test_phase6.py` tests that exercise this function today.

### Tools

```python
def get_slide_text(slide_number: int) -> str: ...
def get_slide_image(slide_number: int) -> bytes:
    # returned as an inline multimodal Part, not plain text — the SDK
    # supports mixing a Part.from_bytes(mime_type="image/png", ...) into
    # the function-response turn.
    ...
```

The agent decides **which slides are worth the extra multimodal call** — this is the actual agentic judgment here, not "look at every slide's image unconditionally" (that would be a fixed, non-agentic policy, and multimodal tokens are materially more expensive than text). Guidance in the system prompt: request an image only for slides whose extracted text is short (hints at a mostly-visual slide: an architecture diagram, a screenshot, a demo frame) or where text alone can't establish the slide's role in the pitch narrative.

### Output schema

```python
class SlideCritique(BaseModel):
    slide_number: int
    narrative_role: Literal["problem", "solution", "demo", "market_impact", "team", "other", "unclear"]
    clarity_score: float  # 0-100
    notes: str

class PitchDeckAnalysis(BaseModel):
    slides: list[SlideCritique]
    missing_narrative_elements: list[str]   # e.g. "no results/impact slide found"
    overall_narrative_score: float          # 0-100
```

### Pipeline integration & scoring interaction

Runs alongside the existing `media_analysis` stage (`tasks/evaluation_tasks.py:47-49`), after `ppt_report` is available. `ai_evaluation.py::_deterministic_presentation_score` stays exactly as it is today (structural completeness, unchanged) — `overall_narrative_score` from this agent becomes a **third** input into the existing presentation-score blend:

```python
# Current (ai_evaluation.py:128):
pres_score = round(pres_structural_score * 0.5 + pres_gemini_score * 0.5, 2)

# Proposed, with this agent's weight deliberately kept low until validated (see §11):
pres_score = round(
    pres_structural_score * 0.4 + pres_gemini_score * 0.4 + pitch_deck_narrative_score * 0.2, 2
)
```

> **This is a breaking change to existing scores.** Any submission re-evaluated after this ships gets a different `presentation` score than it did before — not just an additive feature, an actual change in output for existing data. Flag this to organizers before re-running evaluations on an already-judged hackathon.

### Storage & surfacing

`ai_scores_json["pitch_deck_analysis"]` (nested, same pattern as `whisper_transcript`/`ppt_analysis` today). ParticipantDashboard's AI Evaluation tab and JudgeDashboard's report reader both gain a per-slide breakdown table instead of (or alongside) the single presentation score.

### Risk & mitigation

Cost is the dominant risk — uncapped image fetching on a 20-slide deck would be expensive. Mitigation is the heuristic gate described above *plus* a hard cap passed into the tool itself (propose: no more than 6 image fetches per deck, enforced in `get_slide_image`'s Python implementation, not just requested via `max_tool_calls`).

---

## 6. Agent 4 — Anti-Cheating / Timeline Agent

**Feasibility: MEDIUM** — gated on a second git-fetch path, but this is the strongest cost design of the four: the common (honest) case costs zero LLM calls.

**Purpose:** MinHash plagiarism detection only catches copying *between* submissions in the same hackathon. It has no way to catch a team submitting a project they built weeks before the hackathon started — there's nothing to compare it against. This is a real, currently-unaddressed gap, not a nicer version of something that already exists.

### Required prerequisite: full commit history, not a shallow clone

**Blocking issue:** `source_fetch.clone_repo()` does `git clone --depth 1` (`source_fetch.py:38`) specifically to keep static-analysis/sandbox cloning fast — but a depth-1 clone **discards all commit history**, which is exactly what this agent needs to read. It cannot reuse the existing clone.

**Required change:** a second fetch path, `clone_repo_with_history(url, dest_dir, timeout=60)`, using `--depth 200` (full history is unnecessary and unbounded — 200 commits comfortably covers any realistic hackathon project's history while still bounding clone time) rather than `--depth 1`. This only runs for submissions with a `github_url` — **ZIP uploads have no git history at all and this agent must report `status: "not_applicable"` for them**, not attempt to fabricate a verdict from nothing.

### Deterministic pre-check (the actual cost gate — this is the strongest design decision across all four agents)

```python
# Before ANY LLM call:
commits = get_commit_log(repo_dir)   # git log --format=... --numstat
earliest = min(c["timestamp"] for c in commits)
first_commit_lines = commits[0]["insertions"]

suspicious = (earliest < hackathon.start_date) or (first_commit_lines > THRESHOLD)

if suspicious and settings.ENABLE_TIMELINE_AGENT:
    result = run_timeline_agent(commits, source_dir)   # LLM only ever called here
else:
    result = TimelineRiskAssessment(status="clean", risk_level="LOW", reasoning="", suspicious_commits=[])
```

For the large majority of honest submissions, this costs **zero LLM calls** — the agent only runs for submissions the deterministic check has already flagged as worth a closer look.

### Tools (only called when the pre-check escalates)

```python
def get_commit_log(repo_dir: str) -> list[dict]: ...          # already computed above, passed as context
def read_file(relative_path: str) -> str: ...                  # e.g. to check README for "built on top of X starter template"
```

The agent's actual job, once invoked, is to look for a **legitimate explanation** before concluding anything — a starter template, a previous personal project explicitly disclosed in the README, a team importing boilerplate they're honest about. This framing (look for innocent explanations first) is deliberate: the deterministic check alone is prone to false positives (any legitimate use of a starter kit or template trips it), and the LLM's job is specifically to reduce those false positives with judgment, not to pile on more suspicion.

### Output schema

```python
class TimelineRiskAssessment(BaseModel):
    status: Literal["not_applicable", "clean", "flagged"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    reasoning: str
    suspicious_commits: list[str]   # commit SHAs, if any
```

### Storage & surfacing

New column on `Submission` (not `EvaluationReport` — this is a property of the submission's provenance, checked once, not re-derived per evaluation run): `timeline_risk_json`. This requires matching additions in:
- `models.py` — `Submission.timeline_risk_json` (line 62-82)
- `schemas.py` — `SubmissionOut.timeline_risk_json` (line 102-118)
- `frontend/src/lib/types.ts` — `Submission.timeline_risk_json` (line 52-66)

Surfaced in OrganizerDashboard's Fraud & Plagiarism tab, next to (not merged with) the existing MinHash plagiarism risk — these are two different kinds of fraud signal and should stay visually distinct.

### Risk & mitigation

Same "never auto-reject" principle as the Plagiarism Explainer: `risk_level: HIGH` must read as "an organizer should take a look," never as an automatic disqualification. Legitimate starter-template use is common in real hackathons and must not be penalized by default — hence the "look for an innocent explanation first" framing above.

---

## 7. Consolidated impact on existing files

### Backend files that need changes

| File | Change | Agent(s) |
|---|---|---|
| `services/gemini_client.py` | Refactor — extract retry/fallback logic into `agent_runtime.py` | All |
| `models.py` | + `EvaluationReport.repo_verification_json` | Agent 1 |
| `models.py` | + `Submission.timeline_risk_json` | Agent 4 |
| `models.py` | + new `PlagiarismFileFingerprint` table | Agent 2 |
| `schemas.py` | + `repo_verification_json` on `EvaluationReportOut` | Agent 1 |
| `schemas.py` | + `timeline_risk_json` on `SubmissionOut` | Agent 4 |
| `services/ppt_engine.py` | Signature change + image-blob extraction | Agent 3 |
| `services/plagiarism_engine.py` | Per-file fingerprint computation + storage | Agent 2 |
| `services/source_fetch.py` | + `clone_repo_with_history()` (`--depth 200` path) | Agent 4 |
| `tasks/evaluation_tasks.py` | New stages, feature-flag gating, per-agent `ThreadPoolExecutor` timeout wrapper (§2) | All |
| `celery_app.py` | Generous whole-pipeline `task_soft_time_limit` as a coarse safety net only (currently absent) | All |
| `config.py` | 6 new env vars (§2) | All |

### New backend files

| File | Purpose |
|---|---|
| `services/agent_runtime.py` | Shared tool-calling loop (all four agents use this) |
| `services/repo_verification_agent.py` | Agent 1 |
| `services/plagiarism_explainer_agent.py` | Agent 2 |
| `services/pitch_deck_agent.py` | Agent 3 |
| `services/timeline_agent.py` | Agent 4 |

### Frontend files that need changes

| File | Change |
|---|---|
| `lib/types.ts` | + `repo_verification_json`, `timeline_risk_json`, `pitch_deck_analysis` fields |
| `components/OrganizerDashboard.tsx` | Fraud tab: + claim-verification table, + timeline-risk section |
| `components/JudgeDashboard.tsx` | Report reader: + repo-verification panel, + per-slide deck breakdown |
| `components/ParticipantDashboard.tsx` | AI Evaluation tab: + per-slide deck breakdown |
`backend/app/routers/tasks_router.py` | **Pre-existing gap, independent of these agents:** `get_task_status()` only ever returns `task_id`/`status`/`result`/`error` — it never reads `AsyncResult.info`, which is where `meta={"stage": ...}` from `update_state()` actually lands. The 6 `update_state(..., meta={"stage": ...})` calls already in `evaluation_tasks.py` today are write-only; nothing has ever surfaced them. `ParticipantDashboard.tsx:194` only ever displays `evalTaskStatus.status` (PENDING/PROGRESS/SUCCESS/FAILURE), never a stage name. Before any new agent's stage name can be shown to a user, this endpoint needs `response["stage"] = result.info.get("stage") if isinstance(result.info, dict) else None` added — this is a small, one-line fix, but it has to happen regardless of these agents, not an incidental side effect of adding them. |
| `frontend/src/lib/types.ts` (`TaskStatus`) | + optional `stage?: string` field, once the backend above exposes it |
| `components/ParticipantDashboard.tsx:194` | Render `evalTaskStatus.stage` alongside/instead of `.status` once available, and recognize the new stage names (`repo_verification`, `timeline_check`, etc.) alongside the five that exist today |

### Dead-code note — `analysis_router.py` / `tasks/analysis_tasks.py`

These exist as a standalone set of per-feature trigger endpoints (`POST /api/analysis/run-static/{id}`, `/plagiarism/{id}`, `/sandbox/{id}`) left over from Phases 4-5, before Phase 7 consolidated everything into the single `run_full_evaluation_task`. **Verified: the frontend calls none of these endpoints today.** They're orphaned, not an alternate integration point to design around — all four agents belong in `evaluation_tasks.py`, matching where every other analysis step already lives. Worth a separate, unrelated cleanup pass to decide whether to delete them outright, but out of scope for this document.

---

## 8. Consolidated schema changes (one Alembic migration)

| Table | Change |
|---|---|
| `evaluation_reports` | + `repo_verification_json` (JSON, nullable) |
| `submissions` | + `timeline_risk_json` (JSON, nullable) |
| *(new)* `plagiarism_file_fingerprints` | per-file MinHash signatures, GIN-indexed (see §4) |
| `ai_scores_json` (existing JSON column, no migration needed) | gains a nested `pitch_deck_analysis` key, written by the pipeline, not a schema change |

```python
# Migration: add_agent_columns
def upgrade():
    op.add_column("evaluation_reports",
        sa.Column("repo_verification_json", sa.JSON(), nullable=True))

    op.add_column("submissions",
        sa.Column("timeline_risk_json", sa.JSON(), nullable=True))

    op.create_table("plagiarism_file_fingerprints",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("submission_id", sa.String(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("minhash_signature", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_plagiarism_file_fingerprints_gin",
        "plagiarism_file_fingerprints", ["minhash_signature"],
        postgresql_using="gin")
```

As with every migration so far in this project, prefer generating this via `alembic revision --autogenerate` once the model changes above are in place, and review the generated diff rather than hand-writing it — the sketch above is for review purposes, not meant to be pasted verbatim.

---

## 9. Testing strategy

Matches the existing pattern in `backend/tests/` — Gemini/tool-calls mocked at the service boundary, real Postgres test DB, no live API calls in the automated suite:

| Agent | What the automated test needs |
|---|---|
| Repo Verification | A fixture source directory (small, checked-in under `tests/fixtures/`) with a README making a checkable claim and code that either confirms or contradicts it; mock `agent_runtime.run_tool_agent` to return a canned `RepoVerificationResult`. |
| Plagiarism Explainer | Two fixture submissions with overlapping and non-overlapping files, to exercise `get_candidate_file_pairs` against a real (test) Postgres `plagiarism_file_fingerprints` table — this part is NOT mocked, it's real SQL, matching how `test_phase4.py` already tests MinHash for real rather than mocking it. |
| Pitch-Deck | A fixture `.pptx` with at least one image-bearing, text-sparse slide, to verify the image-extraction change in `ppt_engine.py` for real (deterministic, no model needed) and the slide-selection heuristic with the agent mocked. |
| Timeline | A fixture git repo (a tiny local repo created in the test via `git init` + scripted commits with controlled timestamps) covering: commits after hackathon start (clean), commits before hackathon start (flagged), and a ZIP-only submission (`not_applicable`). |

One manual real-API run per agent against its fixture, same as the existing verification pattern for `score_submission()`, before each phase is considered checkpointed.

---

## 10. Proposed phased rollout

Consistent with how this project has shipped every prior feature — one phase, one checkpoint, independently verifiable before the next starts:

- **Phase 11 — Anti-Cheating / Timeline Agent.** Recommended first: it's the one covering a genuine current gap, has the cheapest common-case cost (zero LLM calls for the honest majority), and needs no changes to existing scoring math.
- **Phase 12 — Plagiarism Explainer Agent.** Second: builds on the existing, already-battle-tested plagiarism pipeline; main work is the per-file fingerprint migration.
- **Phase 13 — Repo Verification Agent.** Third: introduces the shared `agent_runtime.py` tool-calling harness (including the `gemini_client.py` refactor from §2) that Phase 14 then reuses. Note: this is also the lowest-friction agent to prototype in isolation first if you want to validate the harness design before committing to the production rollout order above — it has zero schema prerequisites.
- **Phase 14 — Pitch-Deck Reasoning Agent.** Last: highest cost (multimodal), touches the existing presentation-score blend, requires the `ppt_engine.py` signature change, benefits from the harness already being proven out by Phase 13.

Each phase: implement → automated tests (per §9) → one manual real-API run against a crafted fixture → checkpoint before starting the next phase.

---

## 11. Open decisions — status

| # | Decision | Resolution adopted in this document | Still needs your sign-off? |
|---|---|---|---|
| 1 | Cost budget per submission | `AGENT_MAX_TOOL_CALLS=10` caps runaway loops, but no dollar ceiling is set. Multimodal tokens (Agent 3) run 5-10× more expensive than text — budget that one separately from the other three. | **Yes** — need an actual number before Phase 14. |
| 2 | Pitch-deck score blend weighting | Adopted default: `pitch_deck_narrative_score` at 0.2, not an even three-way split, so the new agent has less influence while unvalidated (§5). | No, unless you want it higher/lower. |
| 3 | HIGH timeline-risk / probable-plagiarism → block or annotate? | Adopted default throughout this document: **annotate only**, surfaced to organizers, never auto-blocks a leaderboard entry. Auto-blocking would need a human-review SLA the system doesn't have. | No, unless you want auto-blocking. |
| 4 | Per-file fingerprint retention | Recommended default: keep for the duration of the hackathon, purge 30 days after it ends — this data is more granular (and more sensitive, since it could be used to reconstruct which specific files are similar) than the existing whole-submission signature. | **Yes** — no retention/deletion job exists yet; needs to be built if adopted. |
