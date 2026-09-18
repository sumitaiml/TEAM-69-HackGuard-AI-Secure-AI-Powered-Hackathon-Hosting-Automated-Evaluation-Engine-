# Product Requirements Document (PRD) - HackGuard AI
**Version:** 1.1 (Updated with Technical Implementation & Security Recommendations)  
**Project Type:** AI + Full Stack + DevOps + Cybersecurity  
**Domain:** General  
**Target Users:** Universities, Enterprises, Developer Communities, Hackathon Organizers  

---

## 1. Product Overview

HackGuard AI is an AI-powered hackathon management platform designed to automate the complete lifecycle of a hackathon—from participant registration to project evaluation and winner announcement.

The platform combines secure code execution, AI-powered project analysis, plagiarism detection, automated scoring, and real-time leaderboards into one unified system.

Its primary objective is to reduce manual judging effort, eliminate submission fraud, and provide transparent, scalable, and fair project evaluation.

---

## 2. Problem Statement

Current hackathon platforms face several challenges:
* Manual evaluation consumes significant time and is prone to bias.
* Organizers use multiple disconnected tools for registration, submissions, communication, and judging.
* Code plagiarism and copied GitHub repositories are difficult to detect.
* AI-generated projects are often submitted without genuine implementation effort.
* Lack of secure environments to execute participant code.
* Delayed result announcements due to manual review.

---

## 3. Vision

To create an intelligent, secure, and scalable hackathon platform capable of evaluating projects automatically while maintaining fairness, transparency, and security.

---

## 4. Objectives

* Automate project evaluation.
* Detect plagiarism across submissions.
* Analyze project documentation using AI.
* Execute submitted projects securely.
* Generate transparent scores.
* Reduce judging time by more than 90%.
* Provide real-time rankings.
* Simplify hackathon management.

---

## 5. Target Users & User Roles

### Target Users
* **Participants:** Students, Developers, Startup Teams, Professionals
* **Organizers:** Universities, Colleges, Tech Communities, Enterprises
* **Judges:** Faculty Members, Industry Experts, Mentors

### User Capabilities
* **Participant:** Register, Login, Create/Join Team, Submit Project (Repo link, ZIP, PPT, Video, README, Tech stack, Live URL), View Scores & Leaderboard.
* **Organizer:** Create Hackathon, Manage Participants/Teams, Configure Evaluation Rubric, Monitor Submissions, View Analytics, Publish Results.
* **Judge:** View AI Reports, Review Projects, Override Scores (Optional), Add Feedback, Finalize Results.

---

## 6. Functional Requirements & Modules

### Module 1 – Authentication
Features: User Registration, Login, JWT Authentication, Password Encryption (bcrypt), Forgot Password, Email Verification.

### Module 2 – Participant Dashboard
Features: Join Hackathon, Team Management, Submission Status, Notifications, Profile Management.

### Module 3 – Team Management
Features: Create Team, Invite Members, Accept Invitations, Team Dashboard, Team Progress.

### Module 4 – Project Submission
Participants can upload: GitHub Repository Link, ZIP File, PPT, PDF Documentation, Demo Video, README, Tech Stack, Live Deployment URL.

### Module 5 – AI Project Evaluation
Analyzes: Source Code, README, Project Description, Documentation, PPT, Demo Video.  
Parameters: Innovation, Technical Complexity, Feature Completeness, UI/UX, Business Impact, Scalability, Documentation, Code Quality, Architecture, Presentation Quality.  
Output: Overall Score, Individual Parameter Scores, AI Feedback, Improvement Suggestions.

### Module 6 – Plagiarism Detection
System compares: Folder Structure, Source Files, Function Similarity, README Similarity, Class Structure, Project Architecture.  
Outputs: Similarity Percentage, Duplicate Files, Matching Code Sections, Risk Level.

### Module 7 – AI Generated Code Detection
Analyzes: Coding Style Consistency, Repetitive Patterns, Project Structure, Documentation Consistency.  
Outputs: Estimated AI Usage Percentage, Confidence Score, Risk Assessment.

### Module 8 – Static Code Analysis
Checks include: Bugs, Security Issues, Complexity, Code Smells, Dead Code, Maintainability.  
Tools: Semgrep, ESLint, Pylint.  
Reports: Static Analysis Report, Security Report, Code Quality Score.

### Module 9 – Secure Docker Sandbox
Executes each project inside an isolated Docker container.  
Workflow: Clone Repo -> Build Project -> Install Dependencies -> Execute Application -> Run Test Cases -> Capture Logs -> Measure Performance -> Destroy Container.  
Metrics: Build Status, Execution Time, CPU Usage, Memory Usage, Runtime Errors.

### Module 10 – PPT Analysis
AI extracts: Problem Statement, Solution, Architecture, Innovation, Market Potential, Business Model.  
Outputs: Presentation Score, Missing Sections, Improvement Suggestions.

### Module 11 – Demo Video Analysis
System performs: Speech-to-Text via Whisper, Transcript Generation, Feature Extraction, Presentation Analysis.  
Outputs: Transcript, Communication Score, Feature Coverage, Confidence Score.

### Module 12 – Leaderboard
Displays: Team Rank, Overall Score, Technical Score, Innovation Score, UI Score, Impact Score.  
Updates automatically post-evaluation.

### Module 13 – Organizer Dashboard
Features: Total Participants, Total Teams, Submission Statistics, Fraud Alerts, Evaluation Progress, Leaderboard, Reports, Export Results.

### Module 14 – Judge Dashboard
Features: AI Evaluation Report, Manual Review, Score Override, Comments, Final Decision.

---

## 7. Evaluation Rubric

| Parameter | Weight |
| :--- | :--- |
| **Technical Complexity** | 30% |
| **Innovation** | 20% |
| **UI/UX** | 15% |
| **Business Impact** | 15% |
| **Documentation** | 10% |
| **Presentation** | 10% |

---

## 8. Technology Stack

* **Frontend:** React, TypeScript, Vite, Tailwind CSS, Shadcn UI, Framer Motion
* **Backend:** Python, FastAPI
* **Database:** PostgreSQL
* **Authentication:** JWT
* **AI Services:** Gemini API (Free Tier), Whisper (Speech-to-Text)
* **Static Analysis:** Semgrep, ESLint, Pylint
* **Sandbox:** Docker Isolation
* **Storage:** Local Storage, MinIO (Optional), AWS S3 (Optional)
* **Deployment:** Vercel (Frontend), Render (Backend), Docker

---

## 9. Non-Functional Requirements

* Responsive UI & Accessible UX
* Secure Authentication & Role-Based Access Control (RBAC)
* Fast API Response Times
* Container Isolation & Strict Resource Scoping
* Data Encryption (at rest & in transit)
* Audit Logging for score overrides & system events
* High Availability & Modular Backend Architecture

---

## 10. Technical Implementation & Risk Mitigation Recommendations (UPDATED)

To address potential security vulnerabilities, rate limits, and processing bottlenecks during production execution, the following technical specifications are integrated:

### 10.1 Docker Sandbox Security & Hardening
* **Container Hardening:** Run sandbox execution under non-root unprivileged users (`nobody:nogroup`) with read-only root filesystems (`--read-only`).
* **Resource Controls:** Enforce strict resource caps per submission container (`--memory=512m`, `--cpus=1.0`, `--pids-limit=64`, `--storage-opt size=2G`).
* **Network Isolation:** Allow outbound network access *only* during the dependency installation phase, then disable networking (`--network none`) prior to building and running participant code.
* **Execution Timeouts:** Impose a hard 60-second execution cap to prevent infinite loops, blocking calls, or resource exhaustion attacks (e.g., fork bombs).

### 10.2 AI Rate Limiting & Queue Orchestration
* **Asynchronous Task Queue:** Implement Celery with Redis (or RabbitMQ / Temporal) to handle heavy AI evaluation jobs asynchronously instead of blocking HTTP request threads.
* **Rate-Limit Backoff:** Build exponential backoff and retry middleware around the Gemini API free-tier calls to prevent 429 Too Many Requests errors during peak submission spikes.
* **Deterministic Scoring:** Set Gemini temperature parameter low ($0.0 - 0.2$) and mandate JSON schema constraints (via Pydantic / Function Calling) to ensure reproducible and parseable evaluation responses.
* **Result Caching:** Cache identical code snippet analyses and static analysis AST hashes to minimize redundant LLM calls.

### 10.3 Video Processing & Speech-to-Text Pipeline
* **Audio Pre-processing:** Use `ffmpeg` to isolate and convert the video audio track to low-bitrate mono WAV/MP3 before passing it to the Whisper Speech-to-Text engine, reducing memory and bandwidth footprint.
* **Upload Constraints:** Enforce pre-upload rules: max video duration of 3–5 minutes and max file size of 50 MB.
* **Parallel Processing Pipeline:** Dispatch static analysis (Module 8), sandbox execution (Module 9), and video processing (Module 11) in parallel worker threads to achieve sub-5-minute evaluation SLAs.

### 10.4 Scalable AST Plagiarism Fingerprinting
* **Locality-Sensitive Hashing (LSH):** Use MinHash / LSH on Abstract Syntax Trees (ASTs) for $O(N)$ submission indexing and fast similarity matching across large hackathons, avoiding $O(N^2)$ pairwise comparison bottlenecks.
* **Cross-Submission Indexing:** Store code token hashes in PostgreSQL with GIN/GiST indexes to instantly identify plagiarized components across teams.

---

## 11. System Workflow

1. Organizer creates hackathon and configures evaluation rubrics.
2. Participants register, create teams, and manage invitations.
3. Teams submit project repository links and multi-format assets.
4. Platform initiates plagiarism detection across submissions.
5. Static code analysis (`Semgrep`, `ESLint`, `Pylint`) runs on repository code.
6. Project executes inside hardened Docker sandbox.
7. AI models evaluate repository, documentation, PPT, and demo video transcript.
8. Individual parameter scores are generated.
9. Final weighted score is computed automatically.
10. Live Leaderboard updates immediately.
11. Judges review AI reports and optionally log overrides/comments.
12. Winners are published and announced.

---

## 12. Success Metrics

* **90% Reduction** in judging time.
* **< 5 Minutes** average automated evaluation duration per submission.
* 100% automated baseline scoring across all valid projects.
* Real-time leaderboard updates post-evaluation.
* Instant detection of duplicate or suspicious code submissions.
* Improved fairness, transparency, and consistency in evaluation.

---

## 13. Future Enhancements

* Multi-language runtime code support.
* Fully custom, dynamic evaluation rubrics builder.
* AI mentor recommendations during hackathon build phase.
* Integrated live coding challenges & speed programming modes.
* Automated certificate generation (PDF / NFT).
* Dedicated Sponsor dashboard & prize tracking.
* Blockchain-based immutable submission verification.
* Advanced Git commit timeline & developer contribution analytics.
* Public API for third-party hackathon integrations.

---

## 14. Assumptions & Limitations

### Assumptions
* Submissions are delivered via GitHub repository links or ZIP archives.
* Docker runtime environment is accessible on the evaluation host.
* AI APIs operate within free-tier rate limits during development.

### Limitations
* Public GitHub-wide plagiarism detection is outside the scope of MVP (inter-submission plagiarism only).
* AI-generated code detection provides an estimated confidence score rather than legal proof.
* Large-scale concurrent container executions require horizontal scaling infrastructure (e.g., Kubernetes / AWS ECS).

---

## 15. Minimum Viable Product (MVP) Scope

The initial MVP release includes:
* User Authentication & RBAC
* Team Management & Invitations
* Hackathon Creation & Rubric Config
* Multi-Asset Project Submission
* AI Repository Evaluation & README Analysis
* Static Code Analysis Integration
* Docker Sandbox Execution
* Inter-Submission Plagiarism Detection
* AI Feedback Report Generation
* Organizer Dashboard & Live Leaderboard

---

## 16. Zero-Cost Development & Deployment Strategy ($0 Budget Stack)

HackGuard AI can be built, hosted, and operated entirely with **$0 capital expenditure** using open-source tools, self-hosted services, and cloud free tiers.

### 16.1 Free Stack Architecture
* **Frontend Hosting:** Vercel (Hobby Tier: 100% free hosting with custom domains & automated HTTPS).
* **Backend Hosting:** Render / Railway / Fly.io (Free Web Service tier for FastAPI).
* **Database Hosting:** Supabase / Neon.tech (Free managed PostgreSQL tier with 500 MB storage).
* **AI Model API:** Google AI Studio (Gemini 1.5 Flash / 2.0 Flash with 15 RPM / 1M TPM free tier).
* **Local Speech-to-Text:** `faster-whisper` or `whisper.cpp` running open-source Whisper models locally on CPU/GPU ($0 API cost).
* **Local Object Storage:** MinIO running in Docker or local filesystem storage during development ($0 cloud storage fees).
* **Static Analysis & Security:** Semgrep, ESLint, Pylint CLI packages (100% open-source & free).

### 16.2 Strategic Cost Optimization Tips
1. **Zero-Cost Object Storage:** Utilize a self-hosted MinIO container or local disk mount for uploaded videos, PPTs, and code archives during development and MVP staging instead of AWS S3.
2. **Local Whisper Inference:** Convert video audio via `ffmpeg` and process it using the lightweight `faster-whisper` Python package locally on host CPU/GPU to eliminate third-party Speech-to-Text API costs.
3. **Queue Throttling for Free AI Tier:** Enforce Celery + Redis task throttling to keep Gemini API requests strictly within the 15 Requests-Per-Minute (RPM) free tier boundary during peak submission windows.
4. **AST Fingerprint Caching:** Cache AST hashes and static analysis outputs in local PostgreSQL to prevent duplicate LLM calls on unmodified submission re-runs.

