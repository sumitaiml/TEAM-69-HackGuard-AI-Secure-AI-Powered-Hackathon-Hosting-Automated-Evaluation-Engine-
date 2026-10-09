# HackEval

An automated hackathon evaluation platform: participants submit a project (GitHub repo, ZIP, slide deck, demo video), and the platform runs it through a real pipeline — static analysis (Semgrep/Pylint/ESLint), AST-based plagiarism detection, sandboxed Docker execution, Whisper transcription of the demo video, PPT slide extraction, and Gemini-based AI scoring — before organizers and judges review the results on a live leaderboard.

See [`HackEval_PRD_Updated.md`](HackEval_PRD_Updated.md) for the full product spec.

## Architecture

| Service | What it does |
|---|---|
| `postgres` | Primary datastore |
| `redis` | Celery broker + result backend |
| `migrate` | One-shot Alembic migration runner (runs once on `up`, then exits) |
| `api` | FastAPI backend (`:8000`) |
| `worker` | Celery worker — runs the evaluation pipeline, including spawning sandbox containers via Docker-outside-of-Docker |
| `frontend` | React + Vite dev server (`:5173`) |

The worker mounts the host's `/var/run/docker.sock` to launch sandbox containers as siblings (not nested/privileged) — untrusted submission code only ever runs inside a hardened, network-isolated sandbox container, never near the socket itself.

## Prerequisites

- Docker and Docker Compose
- A [Gemini API key](https://aistudio.google.com/apikey) (required for AI scoring — everything else in the pipeline runs without it, but evaluations will fall back to a degraded/deterministic-only score if it's missing)

## Quickstart

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set GEMINI_API_KEY at minimum

docker compose up --build
```

Then open:
- Frontend: http://localhost:5173
- API docs (Swagger UI): http://localhost:8000/docs

Register an **organizer** account, create a hackathon, and register a **participant** account (in a separate browser/incognito session) to submit a project. Judges aren't self-registered — an organizer invites them by email from the dashboard; if no SMTP server is configured (see below), the invite link is returned directly in the UI (`dev_invite_link`) so the flow works end-to-end without a real mail provider.

To reset to a completely clean state (wipes the database and all volumes):

```bash
docker compose down -v
docker compose up --build
```

## Configuration

Backend config lives in `backend/.env` (copy from `backend/.env.example`). Key variables:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Required for real AI scoring. Without it, evaluations still run (static analysis, plagiarism, sandbox, transcription) but AI-judged rubric fields fall back to a degraded score (`ai_evaluation_degraded: true` in the report). |
| `GEMINI_MODEL` / `GEMINI_MODEL_FALLBACKS` | Model + comma-separated fallback list, tried in order if a model is unavailable. |
| `DOCKER_SANDBOX_ENABLED` | Disable to skip sandboxed code execution (e.g. if the host can't do Docker-outside-of-Docker). |
| `SMTP_HOST` (+ `SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD`) | If unset, judge invite emails aren't actually sent — the invite link comes back directly in the API response instead. Set these to wire in real email delivery; no code changes needed. |
| `CORS_ORIGINS` | Comma-separated allow-list of frontend origins. |
| `MAX_ZIP_SIZE_MB` / `MAX_PPT_SIZE_MB` / `MAX_VIDEO_SIZE_MB`, `VIDEO_MIN_DURATION_SECONDS` / `VIDEO_MAX_DURATION_SECONDS` | Upload validation limits (PRD: demo video 3–5 minutes, ≤50MB). |

Frontend config is `frontend/.env` (copy from `frontend/.env.example`) — `VITE_API_BASE_URL` must stay host-reachable (`http://localhost:8000`), since it's shipped to the browser rather than resolved inside the Docker network.

Full list of variables and their defaults: `backend/app/config.py`.

## Running tests

```bash
docker compose exec api pytest -q
```

Tests run against a real Postgres database (`hackeval_test`, created alongside the main `hackeval_db`) with Celery in eager mode — no separate test infrastructure needed beyond the compose stack already being up. Gemini/Docker-sandbox/Whisper calls are mocked at the service boundary in the automated suite; the real integrations are verified manually (see below).

## Manual / end-to-end verification

The automated suite mocks the slow, external-service-dependent parts of the pipeline (Gemini, Docker sandbox execution, Whisper). To verify the real integrations end-to-end:

1. `docker compose up --build` from a clean state.
2. Register an organizer, create a hackathon.
3. Register a participant (separate session), create a team, submit a project with a GitHub URL or ZIP.
4. Watch the submission move through evaluation on the **AI Evaluation** tab — this is polling the real Celery task, which runs real static analysis, plagiarism fingerprinting, sandboxed execution, and a real Gemini API call.
5. From the organizer dashboard, invite a judge; accept the invite link and submit a score override.
6. Confirm the leaderboard reflects the override.

## Known scope decisions

- **Styling**: the frontend keeps its original hand-written CSS/JSX rather than adopting the PRD's named Tailwind/Shadcn/Framer Motion stack. This was a deliberate, flagged trade-off — swapping the styling system is cosmetic and orthogonal to making the platform's actual AI/security behavior real, which is where the original gap against the PRD mattered.
- **"Publish Winner Ranks"** (organizer leaderboard tab) is an intentionally disabled stub with an explanatory tooltip — there's no backing endpoint for locking/publishing results, and the button was left honest rather than wired to a fake success.
- **Judges are invite-only**: public signup only accepts `participant`/`organizer`; `judge` accounts are created at invite-accept time.

## Project structure

```
backend/
  app/
    routers/       FastAPI route handlers
    services/       static analysis, plagiarism, sandbox, whisper/ppt, gemini client
    tasks/          Celery task definitions
    models.py, schemas.py, config.py, auth.py
  alembic/          database migrations
  tests/            pytest suite (phase-numbered, matching the build history)
frontend/
  src/
    components/     dashboards (Organizer/Participant/Judge), auth pages
    context/        AuthContext (JWT session state)
    hooks/          useAsyncAction, useTaskPolling
    lib/            apiClient, shared types
docker-compose.yml
```
