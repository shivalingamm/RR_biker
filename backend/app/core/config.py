"""Application configuration.

All secrets come from environment variables. Safe development defaults are
provided so a student can run the project locally without credentials, but any
value that would create a false sense of a "live" integration is explicitly
flagged through the ``is_*_configured`` helpers.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE = f"sqlite:///{(BACKEND_DIR / 'biker_dev.db').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App -------------------------------------------------------------
    app_name: str = "BIKER API"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # --- Database --------------------------------------------------------
    # Portable: point at PostgreSQL in production, SQLite locally.
    database_url: str = DEFAULT_SQLITE

    # --- Auth ------------------------------------------------------------
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # --- File storage ----------------------------------------------------
    # Local disk for development. Never served as public static files.
    storage_dir: str = str(BACKEND_DIR / "storage")
    max_upload_mb: int = 10
    allowed_document_types: str = "application/pdf,image/jpeg,image/png"

    # --- AI --------------------------------------------------------------
    # When empty, the AI endpoints return a clearly labelled deterministic
    # fallback and never claim a live model was used.
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ai_enabled_fallback: bool = True

    # --- Maps ------------------------------------------------------------
    google_maps_api_key: str = ""

    # --- CORS ------------------------------------------------------------
    cors_origins: str = "*"

    # --- convenience -----------------------------------------------------
    @property
    def allowed_document_type_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_document_types.split(",") if t.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def is_maps_configured(self) -> bool:
        return bool(self.google_maps_api_key.strip())

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
