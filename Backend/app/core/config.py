"""
Central configuration for the Cross-Border Workforce OS backend.

All configuration MUST come from environment variables.
Never hard-code secrets, connection strings, or credentials here.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Cross-Border Workforce OS"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str

    # --- Redis ---
    REDIS_URL: str

    # --- Auth / JWT ---
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Object Storage (S3-compatible) ---
    STORAGE_ENDPOINT: str | None = None
    STORAGE_ACCESS_KEY: str | None = None
    STORAGE_SECRET_KEY: str | None = None
    STORAGE_BUCKET: str | None = None

    # --- AI Gateway ---
    AI_PROVIDER_API_KEY: str | None = None
    AI_MODEL_DEFAULT: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance. Import and call get_settings() everywhere
    instead of instantiating Settings() directly, so the environment is
    only parsed once per process.
    """
    return Settings()