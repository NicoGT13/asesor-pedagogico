"""Configuración centralizada (12-Factor App): todo se lee de variables de entorno / .env."""
from __future__ import annotations

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Asesor Pedagógico Inteligente"
    APP_VERSION: str = "3.0.0"
    ENVIRONMENT: str = "development"  # development | production

    # --- Persistencia ---
    DATABASE_URL: str = "sqlite:///./asesor.db"

    # --- Seguridad / JWT ---
    SECRET_KEY: str = "dev-insecure-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "*"

    # --- Motor de IA ---
    AI_PROVIDER: str = "mock"  # mock | openai
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AI_TIMEOUT_SECONDS: float = 90.0
    AI_FALLBACK_TO_MOCK: bool = True

    # --- Archivos ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 10
    MAX_ZIP_UNCOMPRESSED_MB: int = 50

    # --- Arranque ---
    INIT_DB_ON_STARTUP: bool = True
    SEED_DEMO_DATA: bool = True
    DEMO_PASSWORD: str = "Demo2026*"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def async_database_url(self) -> str:
        """Normaliza la URL para drivers asíncronos.

        Render entrega `postgres://` o `postgresql://`; SQLAlchemy async necesita
        `postgresql+asyncpg://`. asyncpg no entiende `sslmode`, así que se elimina
        de la query y se traduce a `connect_args` (ver `database_connect_args`).
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        if url.startswith("sqlite:///"):
            url = "sqlite+aiosqlite:///" + url[len("sqlite:///"):]
        if url.startswith("postgresql+asyncpg://"):
            parts = urlsplit(url)
            query = [(k, v) for k, v in parse_qsl(parts.query) if k != "sslmode"]
            url = urlunsplit(parts._replace(query=urlencode(query)))
        return url

    @property
    def database_connect_args(self) -> dict:
        url = self.DATABASE_URL
        if url.startswith(("postgres://", "postgresql")):
            sslmode = dict(parse_qsl(urlsplit(url).query)).get("sslmode")
            if sslmode in {"require", "verify-ca", "verify-full"}:
                return {"ssl": "require"}
            return {}
        return {"check_same_thread": False} if "sqlite" in url else {}

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
