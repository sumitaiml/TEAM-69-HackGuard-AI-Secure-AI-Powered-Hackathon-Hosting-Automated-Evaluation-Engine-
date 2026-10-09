# HackEval — Build Documentation

_As of 2026-10-09_

A record of everything built so far: what the platform does, how it's architected, the AI pipeline and agents that power evaluation, the security hardening in place, and what's been tested.

---

## 1. Overview

HackEval is an automated hackathon evaluation platform. Participants submit a project (GitHub repo, ZIP, slide deck, demo video); the platform runs it through a real pipeline — static analysis, AST-based plagiarism detection, sandboxed Docker execution, Whisper transcription, PPT extraction, and Gemini-based AI scoring — before organizers and judges review the results on a live leaderboard.

It started as a PRD/spec with a UI/API skeleton where almost none of the "AI-powered" behavior actually existed (static analysis, plagiarism, sandboxing, transcription, and scoring were all hardcoded or simulated). Every one of those has since been replaced with a real implementation, phase by phase, verified against the live stack rather than just unit-tested in isolation.

Three roles: **Organizer** (creates hackathons, configures the scoring rubric, invites judges, monitors fraud signals), **Participant** (forms a team, submits a project, watches it evaluate, views the leaderboard), **Judge** (invite-only, reviews AI reports, can override scores with justification).

---

## 2. Architecture & Tech Stack

Everything runs via Docker Compose — six services:

| Service | Role |
|---|---|
| `postgres` | Primary datastore |
| `redis` | Celery broker + result backend |
| `migrate` | One-shot Alembic migration runner (runs once on `up`, then exits) |
| `api` | FastAPI backend (`:8090` on the host → `:8000` in-container) |
| `worker` | Celery worker — runs the evaluation pipeline, spawns sandbox containers via Docker-outside-of-Docker |
| `frontend` | React + Vite dev server (`:5173`) |

**Backend:** Python 3.10, FastAPI, SQLAlchemy + Alembic (Postgres), Celery + Redis for async work, `google-genai` SDK for Gemini.

**Frontend:** React 19 + Vite, TypeScript, `react-router-dom` for routing, hand-written CSS (not Tailwind — see §10), JWT in `localStorage` with a bearer-token `apiClient`.

**Sandbox isolation:** the `worker` container mounts the host's `/var/run/docker.sock` to spawn sandbox containers as siblings (Docker-outside-of-Docker), not nested — untrusted submission code never runs anywhere near the socket itself, only inside a hardened, network-isolated sandbox container spawned for that purpose.

**Database tables:** `users`, `teams`, `team_members`, `hackathons`, `submissions`, `evaluation_reports`, `plagiarism_fingerprints`, `plagiarism_file_fingerprints`, `judge_invites`, `audit_logs`, `password_reset_tokens`.

---

## 3. Core Platform

- **Auth:** JWT-based, email verification, password reset flow, role-locked registration (public signup only allows `participant`/`organizer` — `judge` and `admin` are rejected at the schema level).
- **Hackathons:** organizers create events with a configurable rubric (six weighted categories, must sum to 100%): technical complexity, innovation, UI/UX, business impact, documentation, presentation.
- **Teams:** participants create or join via a 6-character invite code; a team is independent of any specific hackathon until a submission ties it to one.
- **Submissions:** GitHub URL and/or ZIP + PPTX + demo video upload, all streamed to disk under a fixed server-chosen filename (never the client-supplied name — kills path traversal by construction) with per-type size caps and structural validation (zip-slip guard, real zip/Office-archive check, video duration probe via `ffprobe`).
- **Leaderboard:** `GET /api/evaluation/leaderboard/{hackathon_id}` returns every submission's score, per-parameter breakdown, and every fraud/relevance signal below, sorted and ranked live.

---

## 4. The Evaluation Pipeline

One Celery task (`run_full_evaluation_task`) runs the whole sequence per submission, in order, with progress updates polled by the frontend via a generic `GET /api/tasks/{task_id}` endpoint:

1. **Extract source** — clone the repo or unpack the ZIP into a shared workspace volume.
2. **Static analysis** — real `semgrep`, `pylint`, `eslint` subprocess runs against the actual extracted code, plus a heuristic AI-generated-code detector (comment density, naming patterns, boilerplate phrasing).
3. **Repo verification** — an AI agent checks README claims against the real codebase (§5).
4. **Plagiarism check** — AST-tokenized, MinHash-fingerprinted comparison against every other submission in the hackathon, Postgres-indexed for fast shortlisting; flagged matches get an AI explanation (§5).
5. **Timeline check** — flags a repo whose commit history predates the hackathon start, or an unusually large first commit (§5).
6. **Sandbox execution** — the submission's code actually runs: stack auto-detected (Node/Python), two isolated Docker phases (network-on install, then `network_mode=none` test run), resource-capped (512MB, 1 CPU, 64 pids), 60s hard timeout, guaranteed cleanup.
7. **Media analysis** — Whisper transcribes the demo video (`faster-whisper`, CPU int8); `python-pptx` extracts per-slide text from the deck.
8. **AI scoring** — Gemini scores the submission against the rubric; a dedicated pitch-deck agent additionally critiques the deck slide-by-slide, including visual inspection of image-heavy slides (§5).

**Scoring split** (in `ai_evaluation.py`):
- `technical_complexity` — **fully deterministic**: 60% real static-analysis code-quality score + 40% real sandbox test pass rate. Never judged by an LLM.
- `innovation`, `ui_ux`, `business_impact` — fully Gemini-judged from the README/tech stack/transcript.
- `documentation`, `presentation` — hybrid: 50/50 (documentation) or blended (presentation) between deterministic structural checks and Gemini's qualitative read.

**Degraded mode:** if Gemini fails after every model-fallback and retry, the pipeline doesn't fail the whole evaluation — it keeps every real deterministic result and flags `ai_evaluation_degraded: true` on the report.

---

## 5. The Four AI Agents

All four sit on one shared scaffold, `call_structured_gemini()` in `gemini_client.py`: forces JSON output matching a Pydantic schema, retries with exponential backoff on 429/5xx, does one self-repair pass on invalid JSON, and falls back across a configured model list (`gemini-3.6-flash` → `gemini-3.5-flash` → `gemini-flash-latest`). Passing `tools=[...]` turns it into genuine agentic tool-calling via Gemini's Automatic Function Calling.

| Agent | What it checks | How |
|---|---|---|
| **Timeline Agent** | A pre-built project submitted as "new" | Deterministic pre-filter first (commit history predates hackathon start, or an oversized first commit) — only calls Gemini when that trips, to rule out an innocent explanation (disclosed starter template, etc.) before raising risk |
| **Plagiarism Explainer** | Turns a MinHash similarity % into a real verdict | Deterministic pre-filter shortlists the actual matching file pairs (≥0.5 Jaccard); Gemini reads the real overlapping code and judges `likely_shared_boilerplate` vs `probable_copying` vs `inconclusive` |
| **Repo Verification Agent** | Does the README's claims match the actual code? | The only agent with genuine tool-calling — Gemini is handed `list_directory`/`read_file`/`search_code` (path-traversal-guarded) and decides what to inspect itself. If it never actually calls a tool, confidence is server-side forced to 0 regardless of what it reports — a model can't "confidently" verify claims it never checked |
| **Pitch Deck Agent** | Slide-by-slide critique + **deck-relevance check** | Multimodal: text-sparse slides (<50 chars, likely a diagram/screenshot) get their actual image attached via `types.Part.from_bytes`. Also compares the deck's actual content against the README and judges `is_relevant_to_project`. If a deck is flagged irrelevant (e.g. an unrelated or placeholder file was uploaded), the narrative score is forced to 0 server-side regardless of what the model scored it, **and** the entire presentation parameter score is zeroed — technical/innovation/documentation scores are untouched since those are judged independently from the README/code. Surfaced to organizers as a dedicated "Pitch Deck Relevance Check" table and to judges as a red warning banner on the report |

---

## 6. Security Hardening

- **Uploads:** fixed server-chosen filenames (zero path-traversal surface), streamed size caps enforced mid-transfer (not after), zip-slip-guarded extraction, real archive/video-duration validation before acceptance.
- **Sandbox:** untrusted code only ever executes inside a resource-capped, network-isolated, non-root, all-capabilities-dropped container on a dedicated bridge network — never the app's internal Docker network, so it can't reach Postgres/Redis/the API even during the (network-on) install phase.
- **RBAC:** `require_role()` dependency on every privileged endpoint; ownership checks on submission/team access; judges must have an **accepted** invite for that specific hackathon to see its submissions.
- **CORS:** explicit origin allow-list, no wildcard + credentials combination.
- **Judge accounts:** invite-only — public registration rejects `judge`/`admin` roles outright; a judge account is created only at invite-accept time.
- **Secrets:** `.env` files are gitignored; nothing committed includes real credentials.

---

## 7. Judge Invite System

- **Single invite:** `POST /{hackathon_id}/invite-judge` — generates a 7-day-expiry token, emails it (or returns `dev_invite_link` directly in the API response if no SMTP is configured, so the flow works end-to-end without a real mail provider).
- **CSV bulk invite:** `POST /{hackathon_id}/invite-judges-csv` — upload a `.csv` with an `email` column to invite many judges in one request. Per-row validation (format, in-file duplicates, existing accounts, already-pending invites), capped at 1MB/500 rows, returns an invited/skipped summary with a reason per skip. The Organizer dashboard has a matching upload UI with a downloadable template.

---

## 8. Frontend / UX

- **Three dashboards** (Organizer/Participant/Judge), each with role-specific tabs, driven by one `DashboardShell` keyed on role (not tab — deliberately, so tab switches don't wipe in-flight evaluation-polling state).
- **Auth pages** (Login/Register, Accept Invite, Reset Password, Verify Email) are full-screen, not card-in-page layouts.
- **Fixed sidebar:** the dashboard shell has its own scroll region for the content column; the sidebar never scrolls with it.
- **Tab-switch transitions:** every dashboard view (and judge's AI-report sub-tabs) is keyed on its active tab, forcing a clean remount on every switch so the existing `fadeInUp` CSS animation actually replays each time, instead of only on first mount.
- Branded throughout as **HackEval** (renamed from an earlier "HackGuard AI" working name — code, config, docs, and the live Postgres database/Docker image/volume names were all migrated).

---

## 9. Testing & Verification

**Automated suite:** 84 passing tests (`docker compose exec api pytest -q`) across phase-numbered files plus dedicated files per agent (`test_timeline_agent.py`, `test_repo_verification_agent.py`, `test_pitch_deck_agent.py`, `test_plagiarism_explainer.py`, `test_ai_evaluation.py`, `test_ai_code_detection.py`). Gemini/Docker-sandbox/Whisper are mocked at the service boundary for speed and determinism; the real integrations are verified manually.

**Manually verified live**, not just unit-tested:
- Full register → create hackathon → submit → evaluate → leaderboard → judge-override flow, multiple times, via both the UI and direct API calls.
- Real Gemini scoring against the live API key (including watching it work through free-tier rate-limit retries in production logs).
- Real Docker sandbox execution (pass/fail counts, timeout-and-cleanup on a hung process).
- CSV bulk judge invite, end-to-end, via Playwright browser automation.
- Tab-switch animation replay, via Playwright `animationstart` event capture.
- The pitch-deck relevance check's UI wiring (organizer table + judge banner).
- Live Postgres database rename with zero data loss (row-count verified before/after).

---

## 10. Known Scope Decisions & Limitations

- **Styling:** the frontend keeps hand-written CSS/JSX rather than the PRD's named Tailwind/Shadcn/Framer Motion stack — a deliberate, flagged trade-off; cosmetic and orthogonal to making the AI/security behavior real.
- **"Publish Winner Ranks"** is an intentionally disabled stub (no backing endpoint) rather than wired to a fake success.
- **Gemini free tier:** the current API key is on the free tier (5 requests/minute per model). A single evaluation can burn through that quickly — the repo-verification agent alone can fire 10 tool-calling requests in a burst — so evaluations sometimes take several minutes while the model-fallback/retry logic cycles through `429`/`503` errors before succeeding. Not a bug; the fix (not yet implemented) would be either enabling billing (same code, ~1000+ RPM) or adding client-side request pacing to stay under the free-tier ceiling.
- **Pitch-deck agent weighting:** deliberately low (0.2 of the presentation sub-score) relative to the two older signals, pending validation against more real decks — except when flagged irrelevant, where it now overrides to zero outright (§5).

---

## 11. Project Structure

```
backend/
  app/
    routers/        auth, hackathons, teams, submissions, evaluation, tasks
    services/        static analysis, plagiarism, sandbox, whisper/ppt, gemini client,
                     the four AI agents, upload validation, audit log, email
    tasks/           Celery task definitions (full evaluation pipeline)
    models.py, schemas.py, config.py, auth.py
  alembic/           database migrations
  tests/             pytest suite (84 tests, phase-numbered + per-agent)
frontend/
  src/
    components/      OrganizerDashboard, ParticipantDashboard, JudgeDashboard,
                     Sidebar, Header, auth pages
    context/         AuthContext (JWT session state)
    hooks/           useAsyncAction, useTaskPolling
    lib/             apiClient, shared types
docker-compose.yml   postgres, redis, migrate, api, worker, frontend
```
