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
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hackguard.db")
    
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

settings = Settings()
