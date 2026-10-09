# HackEval — PRD Gap Analysis

**Document Version:** 1.0
**Status:** Analysis only — nothing in this document is implemented yet
**Compared against:** `HackEval_PRD_Updated.md` (v1.1) vs. the codebase as of Phase 10
**Method:** Every claim below was checked directly against the current code (grep/read, not memory) — file paths and specific confirmations are given throughout so this stays verifiable rather than assumed.

---

## 0. Most important finding: nothing is deployed anywhere

The PRD's entire §16 ("Zero-Cost Development & Deployment Strategy") assumes the platform is actually live on Vercel (frontend), Render/Railway/Fly.io (backend), and Supabase/Neon (database). As it stands, **the project only runs via local `docker compose up` on a developer's machine** — there is no public URL. For a hackathon submission specifically, this is the single highest-impact gap: a judge cannot open a link and try it.

This is also the one item in this document that is **not purely an engineering task** — it requires actually creating accounts on free-tier providers and wiring secrets, which only you can do (API keys, custom domains, etc.). Flagging it first because it's easy to deprioritize behind code changes and is arguably the most consequential one for a demo.

---

## 1. Fully missing modules

### 1.1 Module 7 — AI-Generated Code Detection

**Status: not started.** Verified via project-wide grep for `ai_generated`, `ai-generated`, `AIGeneratedDetection`, and related terms across every `.py` file — zero matches. This isn't a partial implementation folded into something else; no phase of this project ever built it.

**What the PRD wants:** analyze coding-style consistency, repetitive patterns, project structure, and documentation consistency to produce an estimated "AI usage %" with a confidence score and risk assessment.

**Suggested approach, scoped to fit the existing pipeline:**
- New service: `backend/app/services/ai_code_detection.py`
- Deterministic signal gathering (cheap, no LLM): comment-density ratio, variable-naming entropy (real human code has more inconsistent naming than LLM output), commit-message patterns if `source_fetch.clone_repo_with_history` from the agents plan is built (a suspiciously small number of commits each perfectly-formatted is itself a signal), and boilerplate-pattern matching (common LLM scaffolding phrases, e.g. excessive try/except with generic messages, repetitive docstring templates).
- Qualitative signal: fold one more question into the existing single Gemini call in `gemini_client.py` (cheapest integration point — no new agent needed for an MVP version) asking it to rate "does this code's style look LLM-generated" given a sample of the actual source, output a `0-100` confidence + `risk_level`.
- New field: `ai_scores_json["ai_generated_code_assessment"]` (nested JSON, same pattern as `whisper_transcript`/`ppt_analysis` today — no migration needed).
- **Framing matters as much as the number itself:** the PRD's own Limitations section (§14) already says this "provides an estimated confidence score rather than legal proof" — the UI must present it exactly that way, never as a verdict.
- Effort: **M** — one new service file, one schema field, one UI panel. No DB migration if nested into existing JSON.

### 1.2 Forgot Password / Email Verification (Module 1)

**Status: not started.** `auth_router.py` has exactly 5 endpoints: `/register`, `/login`, `/me`, `/invite/{token}`, `/invite/{token}/accept`. No password-reset flow, no email-verification step.

**Suggested approach:**
- Reuses machinery already built for judge invites almost exactly: `JudgeInvite` already has `token` (unique, indexed) + `expires_at` + `email_service.py`'s "send if SMTP configured, else return link directly" pattern (`dev_invite_link`). A password-reset token can be the same shape.
- New table: `PasswordResetToken` (id, user_id, token, expires_at, used_at) — same structure as `JudgeInvite`, different purpose.
- New endpoints: `POST /api/auth/forgot-password` (always returns 200 regardless of whether the email exists, to avoid leaking which emails are registered — a real security requirement, not just nice-to-have), `POST /api/auth/reset-password/{token}`.
- Email verification: add `is_verified: bool` to `User` (default `False`), a `POST /api/auth/verify/{token}` endpoint mirroring the judge-invite-accept pattern, sent automatically at registration via the existing `email_service.py`. Whether unverified users should be blocked from logging in or just flagged is a product decision — recommend **not blocking** for a hackathon-scale MVP (matches the PRD's own tone of reducing friction), just surfacing verification status.
- Effort: **M** — one new table + migration, ~4 new endpoints, reuses all existing email-delivery and token-pattern infrastructure from Phase 8.

---

## 2. Partially implemented — real gaps against the spec

### 2.1 Docker sandbox resource metrics (Module 9)

**Confirmed:** `sandbox_runner.py`'s return value is `{exit_code, logs, elapsed_seconds, timed_out, error}` — no CPU or memory figures, even though the PRD explicitly lists "CPU Usage, Memory Usage" as required output metrics.

**Fix:** the Docker SDK already exposes `container.stats(stream=False)` while the container is running — this needs to be polled once (or averaged over a couple of samples) during the test-execution phase and the peak/average `cpu_percent` and `memory_usage_mb` added to the returned dict. Low effort since the container object is already held in `sandbox_runner.py`'s execution phase — this is adding a stats call, not new infrastructure.

Effort: **S**.

### 2.2 Leaderboard per-parameter scores (Module 12)

**Confirmed:** `GET /api/evaluation/leaderboard/{hackathon_id}` in `evaluation_router.py` returns one aggregate `score` field per entry. The PRD wants "Technical Score, Innovation Score, UI Score, Impact Score" shown per team on the leaderboard itself, not just buried in the individual report.

**Fix:** the data already exists (`EvaluationReport.ai_scores_json.parameter_scores`) — this is purely a matter of adding `parameter_scores: dict` to each leaderboard entry in the existing endpoint, then rendering it as extra columns in `OrganizerDashboard.tsx`'s and `ParticipantDashboard.tsx`'s leaderboard tables. No new computation, no migration.

Effort: **S**.

### 2.3 Team invites are code-based, not targeted (Module 3)

**Confirmed:** `team_router.py` only has `/create`, `/join` (by shared invite code), `/my-team` — no per-email invite + pending/accept state for teammates, unlike the targeted flow already built for judges (`JudgeInvite`).

**Fix:** this could reuse the exact same `JudgeInvite`-style pattern (token + expiry + accept-at-signup), but it's worth asking whether it's actually worth doing — a shared join code is simpler for participants and is a very common, accepted pattern in real hackathon platforms (Devpost, MLH, etc. mostly use exactly this). Recommend treating this as a **low-priority, PRD-literal-compliance-only** item rather than a real product gap.

Effort: **M**, but **low priority** — flagging the trade-off explicitly rather than just listing it as a todo.

### 2.4 No PDF documentation upload (Module 4)

**Confirmed:** no "pdf" reference anywhere in `submission_router.py`, `schemas.py`, or `models.py`. Only ZIP/PPT/video are accepted as file uploads.

**Fix:** mechanically identical to the existing PPT upload path — add `pdf_file: Optional[UploadFile] = File(None)` to `submit_project()`, save under a fixed name (`docs.pdf`) in the submission's upload directory following the existing fixed-filename pattern (`source.zip`/`deck.pptx`/`demo.mp4`), add `MAX_PDF_SIZE_MB` to config. Whether its content should also be extracted and fed into the Gemini scoring prompt (like PPT text is) or just stored/linked is worth deciding — recommend starting with storage + link only, since most hackathons' required PDF (if any) duplicates the README/PPT content rather than adding new signal.

Effort: **S** (store-only) to **M** (if text extraction + scoring integration is wanted).

### 2.5 Plagiarism detection doesn't check README similarity or folder structure (Module 6)

**Confirmed:** `plagiarism_engine.py`'s MinHash signature is computed only from files inside the extracted repo/zip (`_iter_source_files` walks `source_dir`). The submission's actual `readme_text` field (what the participant typed into the submission form, separate from any `README.md` file that may or may not exist in their repo) is never included in any similarity check at all. There's also no distinct folder-structure comparison — only token-content similarity.

**Fix:** two independent, smaller additions rather than a redesign:
- Compute a second, lightweight MinHash signature over `submission.readme_text` alone and compare it the same way (GIN-shortlisted) against other submissions' readme text — catches copy-pasted project descriptions distinctly from copied code.
- Folder-structure similarity: hash the sorted list of relative file paths (extension + depth, not full names) per submission and compare via simple set overlap — cheap, catches "literally the same scaffolding/boilerplate generator output" patterns that pure token-content MinHash can miss when variable names differ but structure doesn't.

Effort: **S** for README-similarity (reuses the exact same `compute_minhash_signature` function on different input text), **M** for folder-structure (new, small comparison function + one more field on the existing report).

### 2.6 Demo video "Feature Coverage" cross-check (Module 11)

**Confirmed:** the Whisper transcript is passed into the single Gemini scoring call purely as narrative context — nothing cross-references claims made in the video against what's actually in the repository.

**Fix:** this is the same shape of problem the agents implementation plan's **Repo Verification Agent** already solves for README claims (see `AI_Agents_Implementation_Plan.md` §3) — extending that agent's `claims_checked` list to also take claims extracted from the video transcript (not just the README) is a natural, low-incremental-cost addition once that agent exists, rather than a separate thing to build from scratch.

Effort: **S**, but only after Phase 13 (Repo Verification Agent) ships — otherwise **M** standalone.

### 2.7 Organizer dashboard has no total-participant count (Module 13)

**Confirmed:** `OrganizerDashboard.tsx` derives `registeredTeams` from unique `team_id`s in the leaderboard — there's no distinct headcount of individual participants anywhere in the UI or API.

**Fix:** needs a small new query — `Team` → `TeamMember` → count distinct `user_id` scoped to teams that have a submission in the given hackathon (or, more simply, all teams ever created, if "participants" should mean "everyone registered" rather than "everyone who submitted"). Worth deciding which definition the organizer actually wants before building it. Could be its own small endpoint (`GET /api/hackathons/{id}/stats`) or folded into the existing leaderboard response.

Effort: **S**.

### 2.8 No result caching for repeated evaluations (§10.2)

**Confirmed:** no caching layer exists anywhere in the pipeline — re-running evaluation on an unmodified submission recomputes static analysis, plagiarism fingerprinting, and the Gemini call from scratch every time.

**Fix:** the natural cache key already exists implicitly — the plagiarism engine already computes a MinHash signature of the submission's full content, and `static_analysis.py` could hash the extracted source tree (e.g. a simple concatenated-file-hash) before running Semgrep/Pylint/ESLint. If that hash matches the hash stored on the submission's most recent prior report, skip straight to reusing the stored `static_analysis_json`/`plagiarism_json` instead of recomputing. The Gemini call is the most expensive step and the easiest to skip redundantly — cache on `(readme_text, ppt text, transcript, tech_stack)` hash.

Effort: **M** — needs a stored content-hash column on `EvaluationReport` or `Submission`, plus a short-circuit check at the top of `run_full_evaluation_task`.

### 2.9 Pipeline is sequential, not parallel (§10.3)

**Confirmed, and a deliberate choice, not an oversight:** `run_full_evaluation_task` (Phase 7) is one flat function running static analysis → plagiarism → sandbox → media analysis → AI scoring in sequence, explicitly chosen over Celery `chain`/`chord` for simplicity, since the sandbox step (up to 60s) dominates total time regardless.

**Assessment:** probably still meets the PRD's "<5 minutes" SLA in practice given typical per-stage timings observed during Phase 7-9 verification (full pipeline completed in 6-16 seconds against small test fixtures; real submissions with a full 60s sandbox timeout would still land well under 5 minutes total). Recommend **leaving this as-is** rather than re-architecting into parallel Celery tasks purely for PRD-literal-compliance when the actual success metric (sub-5-minute SLA) is already met by the simpler design. Documenting this as a conscious deviation rather than a gap to close.

---

## 3. Already-known, deliberately-flagged deviations (not new findings — listed for completeness)

- **Frontend styling:** hand-written CSS/JSX instead of the PRD's named Tailwind/Shadcn/Framer Motion stack. Flagged during the original Phase 9 scoping as a cosmetic, deliberate trade-off — swapping the styling system is high-risk-of-visual-regression and orthogonal to making the product's actual AI/security behavior real.
- **"Publish Winner Ranks"** is an honest disabled stub (no backing endpoint for locking/publishing results) rather than a faked success — consistent with this project's "make it real, not simulated" approach throughout.

---

## 4. Recommended order of work

Given limited time before a hackathon deadline, roughly in order of impact-per-hour-of-work:

1. **Deploy it somewhere** (§0) — highest impact, not an engineering task, do this first regardless of what else gets built.
2. **Leaderboard per-parameter scores** (§2.2) and **sandbox CPU/memory metrics** (§2.1) — both **S**-effort, both directly visible in a demo, both literally just surfacing data that already exists.
3. **AI-Generated Code Detection** (§1.1) — the only *entire module* missing from the PRD; worth having at least a minimal version given it's named as its own numbered module, not a sub-feature.
4. **Forgot Password / Email Verification** (§1.2) — matters more for a real deployment (§0) than for a local demo; prioritize after something is actually publicly reachable.
5. Everything in §2.3–§2.9 — genuine gaps, but each is either low-priority-by-design (§2.3), dependent on the separate agents plan (§2.6), or a reasonable-to-defer polish item (§2.4, §2.5, §2.7, §2.8) that doesn't change what a judge sees in a 5-minute demo.
