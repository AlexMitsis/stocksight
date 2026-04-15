"""
Application configuration using pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # API Keys
    OPENAI_API_KEY: str  # For LLM (custom endpoint)
    OPENAI_EMBEDDINGS_API_KEY: Optional[str] = None  # For embeddings (standard OpenAI)

    # Model Configuration
    MODEL_NAME: str = "c1/openai/gpt-5/v-20250930"
    MODEL_BASE_URL: str = "https://api.thesys.dev/v1/embed/"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8888

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./stockanalysis.db"  # Default to SQLite for development

    # Redis Configuration (for caching)
    REDIS_URL: Optional[str] = None  # Set via environment or docker-compose

    # JWT Authentication Configuration
    SECRET_KEY: str  # Required: generate with: openssl rand -hex 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/google/callback"

    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"

    FRONTEND_URL: str = "http://localhost:3000"

    # Logging Configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "text"  # text or json (json for production)

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Global settings instance
settings = Settings()  # type: ignore[call-arg]
