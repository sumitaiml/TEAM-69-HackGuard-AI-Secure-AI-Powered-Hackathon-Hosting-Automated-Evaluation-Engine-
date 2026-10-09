import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "HackGuard AI Engine"
    VERSION: str = "1.0.0"
    
    # 1. Auth & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "hackguard_super_secret_jwt_key_2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    
    # 2. Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hackguard_db")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/hackguard_test")
    
    # 3. AI Services (Gemini API)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # gemini-1.5-flash and gemini-2.5-flash have both since been retired for
    # new callers (confirmed directly against the live API while building
    # this) - gemini-3.6-flash is what the API itself now recommends.
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_MODEL_FALLBACKS: str = os.getenv("GEMINI_MODEL_FALLBACKS", "gemini-3.5-flash,gemini-flash-latest")
    
    # 4. Whisper STT Model
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base")
    
    # 5. Storage
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # 6. Sandbox
    DOCKER_SANDBOX_ENABLED: bool = os.getenv("DOCKER_SANDBOX_ENABLED", "true").lower() == "true"
    DOCKER_MEMORY_LIMIT: str = os.getenv("DOCKER_MEMORY_LIMIT", "512m")
    DOCKER_CPU_CAP: float = float(os.getenv("DOCKER_CPU_CAP", 1.0))
    DOCKER_TIMEOUT_SECONDS: int = int(os.getenv("DOCKER_TIMEOUT_SECONDS", 60))
    DOCKER_PIDS_LIMIT: int = int(os.getenv("DOCKER_PIDS_LIMIT", 64))
    # Fixed Docker volume name (see docker-compose.yml's `name:` override) -
    # sibling sandbox containers mount this by name via the host daemon
    # (DooD), so it must match exactly regardless of compose project name.
    SANDBOX_VOLUME_NAME: str = os.getenv("SANDBOX_VOLUME_NAME", "hackguard_sandbox_workspace")
    # Dedicated bridge network for sandbox containers, created idempotently
    # by the worker on first use - deliberately NOT the compose-managed
    # internal network, so sandboxed code can never reach postgres/redis/
    # api/worker even during the network-on install phase.
    SANDBOX_NETWORK_NAME: str = os.getenv("SANDBOX_NETWORK_NAME", "hackguard-sandbox-net")

    # 7. CORS
    # Comma-separated list of allowed origins for the frontend SPA.
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:5173")

    # 8. Upload limits (PRD: video 3-5 min, max 50MB)
    MAX_ZIP_SIZE_MB: int = int(os.getenv("MAX_ZIP_SIZE_MB", 100))
    MAX_PPT_SIZE_MB: int = int(os.getenv("MAX_PPT_SIZE_MB", 25))
    MAX_VIDEO_SIZE_MB: int = int(os.getenv("MAX_VIDEO_SIZE_MB", 50))
    VIDEO_MIN_DURATION_SECONDS: int = int(os.getenv("VIDEO_MIN_DURATION_SECONDS", 180))
    VIDEO_MAX_DURATION_SECONDS: int = int(os.getenv("VIDEO_MAX_DURATION_SECONDS", 300))

    # 9. Async task queue (Celery + Redis)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Runs Celery tasks synchronously in-process (no worker/broker needed) -
    # used for tests; real dev/prod always goes through the real worker.
    CELERY_TASK_ALWAYS_EAGER: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"

    # 10. Shared workspace for extracted submission source (and, from Phase 5,
    # sandbox execution) - the api and worker containers mount the same
    # named Docker volume here so work done by one is visible to the other.
    WORKSPACE_ROOT: str = os.getenv("WORKSPACE_ROOT", "./workspace")

    # 11. Judge invites & email delivery
    # Used to build the accept-invite link sent to invited judges.
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    JUDGE_INVITE_EXPIRY_DAYS: int = int(os.getenv("JUDGE_INVITE_EXPIRY_DAYS", 7))
    PASSWORD_RESET_EXPIRY_HOURS: int = int(os.getenv("PASSWORD_RESET_EXPIRY_HOURS", 2))

    # 12. Agentic evaluation modules (see AI_Agents_Implementation_Plan.md) -
    # each independently feature-flagged so one can be disabled without
    # touching the others or the core deterministic pipeline.
    ENABLE_TIMELINE_AGENT: bool = os.getenv("ENABLE_TIMELINE_AGENT", "true").lower() == "true"
    ENABLE_PLAGIARISM_EXPLAINER_AGENT: bool = os.getenv("ENABLE_PLAGIARISM_EXPLAINER_AGENT", "true").lower() == "true"
    ENABLE_REPO_VERIFICATION_AGENT: bool = os.getenv("ENABLE_REPO_VERIFICATION_AGENT", "true").lower() == "true"
    # Hard cap on tool calls per agentic Gemini call - bounds cost/latency
    # for any agent using call_structured_gemini(tools=...).
    AGENT_MAX_TOOL_CALLS: int = int(os.getenv("AGENT_MAX_TOOL_CALLS", 10))
    # If SMTP_HOST is unset, invite emails aren't actually sent - the invite
    # link is returned directly in the API response instead (dev_invite_link)
    # so the feature works end-to-end without a real mail provider. Wiring in
    # real SMTP later is just setting these env vars, not a code change.
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_ADDRESS: str = os.getenv("SMTP_FROM_ADDRESS", "no-reply@hackguard.ai")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
