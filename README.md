# HackEval

> **Secure, AI-Powered Hackathon Hosting & Automated Evaluation Engine**

HackEval is an automated hackathon evaluation platform. Participants submit projects (GitHub repository, source ZIP, pitch deck, and demo video), and the platform runs them through a rigorous, multi-stage evaluation pipeline:
- **Deterministic Static Analysis**: Real `semgrep`, `pylint`, and `eslint` scans with heuristic AI-generated code detection.
- **AST-Based Plagiarism Detection**: MinHash tree-sitter fingerprinting against existing submissions.
- **Isolated Docker Sandboxing**: Secure execution and dependency testing inside resource-capped, network-isolated containers.
- **Media Processing**: Local Whisper transcription (`faster-whisper`, int8) and slide deck extraction (`python-pptx`).
- **Four Specialized AI Agents**: Dual-provider LLM pipeline (Groq for high-throughput reasoning + Gemini for multimodal vision).
- **Live Leaderboard & Judge Review**: Role-based portals for Organizers, Participants, and Judges with live fraud signals and score override workflows.

---

## Architecture

HackEval runs as a multi-container stack orchestrated via Docker Compose:

```
                          ┌───────────────────────┐
                          │   Frontend (React 19) │  :5173
                          └───────────┬───────────┘
                                      │ HTTP / REST
                                      ▼
┌──────────────────┐      ┌───────────────────────┐      ┌───────────────────────┐
│ Postgres 16 DB   │◄────►│  FastAPI Backend API  │◄────►│ Redis 7 Broker/Cache  │
│ (Port 5432)      │      │  (Port 8090 -> 8000)  │      │ (Port 6379)           │
└──────────────────┘      └───────────────────────┘      └───────────┬───────────┘
                                                                     │ Celery Tasks
                                                                     ▼
                                                         ┌───────────────────────┐
                                                         │ Celery Worker Engine  │
                                                         └───────────┬───────────┘
                                                                     │ Docker-out-of-Docker
                                                                     ▼
                                                         ┌───────────────────────┐
                                                         │ Isolated Sandboxes    │
                                                         └───────────────────────┘
```

| Service | Container / Port | Description |
|---|---|---|
| **`postgres`** | `postgres:16-alpine` (`:5432`) | Primary datastore for users, submissions, reports, and fingerprints. |
| **`redis`** | `redis:7-alpine` (`:6379`) | Celery message broker and task result cache. |
| **`migrate`** | `hackeval-backend:local` | One-shot Alembic migration runner; executes on startup and exits cleanly. |
| **`api`** | `hackeval-backend:local` (`:8090` -> `:8000`) | FastAPI application serving REST endpoints and OpenAPI documentation. |
| **`worker`** | `hackeval-backend:local` | Celery worker executing the evaluation pipeline and managing sibling Docker sandboxes. |
| **`frontend`** | Node 20 / Vite (`:5173`) | React 19 single-page application with role-based dashboards. |

---

## The AI Pipeline & Agent Architecture

The evaluation engine uses a hybrid deterministic/AI split to guarantee fair, reproducible scoring:

| Agent / Stage | Provider | Responsibility |
|---|---|---|
| **Repo Verification Agent** | **Groq** (`gpt-oss-120b`) | Autonomous tool-calling agent with `list_directory`, `read_file`, and `search_code` capabilities. Verifies README claims directly against the source code. |
| **Timeline Agent** | **Groq** (`gpt-oss-120b`) | Analyzes Git commit history and first-commit size to detect pre-built projects submitted as new work. |
| **Plagiarism Explainer** | **Groq** (`gpt-oss-120b`) | Receives AST MinHash overlapping code segments (Jaccard similarity ≥ 0.5) and classifies code as boilerplate vs. direct plagiarism. |
| **Pitch Deck Agent** | **Gemini** (`gemini-3.6-flash`) | Multimodal slide-by-slide narrative evaluation with visual screenshot inspection. Enforces automatic zero-override if deck is irrelevant to the submitted project. |
| **Technical Complexity** | **Deterministic** | 60% static analysis code quality + 40% sandbox test pass rate. Never delegated to an LLM. |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+ with Compose v2+)
- [Node.js](https://nodejs.org/) (v20+ recommended for host frontend development)
- [Groq API Key](https://console.groq.com/keys) (Free tier supported)
- [Google AI Studio Gemini API Key](https://aistudio.google.com/apikey) (Free tier supported)

---

## Quickstart

### 1. Configure Environment Variables

Create your `.env` files from the provided templates:

```bash
# Backend configuration
cp backend/.env.example backend/.env

# Frontend configuration
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and insert your API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 2. Install Local Frontend Dependencies (Optional for host tooling)

```bash
cd frontend
npm install
cd ..
```

### 3. Build & Start with Docker Compose

```bash
docker compose up --build -d
```

### 4. Access the Application

- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **API Swagger Documentation**: [http://localhost:8090/docs](http://localhost:8090/docs)
- **API ReDoc**: [http://localhost:8090/redoc](http://localhost:8090/redoc)

---

## User Roles & Workflows

1. **Organizer**:
   - Register an organizer account at `/register`.
   - Create a hackathon with custom rubric weights (Technical, Innovation, UI/UX, Business Impact, Documentation, Presentation).
   - Invite judges individually or in bulk via CSV upload (`/invite-judges-csv`).
   - Monitor live leaderboard, plagiarism flags, and pitch deck relevance reports.

2. **Participant**:
   - Register a participant account.
   - Create or join a team via a 6-character team invite code.
   - Submit a GitHub repository link or upload a ZIP archive, PPTX slide deck, and demo video.
   - Track evaluation progress in real time through Celery task polling.

3. **Judge**:
   - Joined via secure one-time invite token (judges cannot sign up publicly).
   - Review comprehensive AI evaluation reports with code citations.
   - Submit manual score overrides with mandatory justification logs.

---

## Configuration Reference

Key settings in `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | JWT signing key. |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/hackeval_db` | Postgres connection string. |
| `GROQ_API_KEY` | — | API key for timeline, plagiarism, and repo verification agents. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Primary Groq model (`openai/gpt-oss-20b` as fallback). |
| `GEMINI_API_KEY` | — | API key for multimodal pitch deck analysis. |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model for vision inspection. |
| `DOCKER_SANDBOX_ENABLED` | `true` | Enables/disables sibling container code execution. |
| `DOCKER_MEMORY_LIMIT` | `512m` | Memory ceiling per submission sandbox. |
| `DOCKER_TIMEOUT_SECONDS`| `60` | Execution timeout for sandbox test suites. |
| `MAX_ZIP_SIZE_MB` | `100` | Maximum source code ZIP upload size. |
| `MAX_PPT_SIZE_MB` | `25` | Maximum presentation slide upload size. |
| `MAX_VIDEO_SIZE_MB` | `50` | Maximum demo video upload size. |
| `VIDEO_MIN_DURATION_SECONDS` | `180` (3m) | Minimum demo video length enforced via `ffprobe`. |
| `VIDEO_MAX_DURATION_SECONDS` | `300` (5m) | Maximum demo video length enforced via `ffprobe`. |
| `SMTP_HOST` | *(empty)* | SMTP server for judge invites. When blank, invites output `dev_invite_link` directly. |

---

## Testing & Quality Assurance

### Run Backend Test Suite

The test suite runs against an isolated PostgreSQL database (`hackeval_test`) inside the Docker container:

```bash
docker compose exec api pytest -q
```

All 98 tests cover:
- Authentication, RBAC, and Token handling
- File validation (zip-slip guards, MIME verification, ffprobe duration checks)
- Static analysis & AI-generated code detection heuristics
- AST-based plagiarism MinHash fingerprinting
- The 4 AI evaluation agents with mock and degraded-mode resilience
- Celery task pipeline and score aggregation logic

### Frontend Linting & Type Checking

```bash
cd frontend
npm run lint
npm run build
```

---

## Resetting the Environment

To stop all services and wipe the database and named volumes for a fresh start:

```bash
docker compose down -v
docker compose up --build -d
```
