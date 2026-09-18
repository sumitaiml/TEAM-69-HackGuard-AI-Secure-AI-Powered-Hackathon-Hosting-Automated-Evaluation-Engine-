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
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
