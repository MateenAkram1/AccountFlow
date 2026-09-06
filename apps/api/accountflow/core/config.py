import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[2]
_REPO_CANDIDATE = Path(__file__).resolve().parents[4]
# Monorepo root locally; apps/api root when Vercel Root Directory is apps/api.
ROOT_DIR = (
    _REPO_CANDIDATE
    if (_REPO_CANDIDATE / "samples").is_dir() or (_REPO_CANDIDATE / "config").is_dir()
    else _API_ROOT
)
CONFIG_DIR = ROOT_DIR / "config"


def data_dir() -> Path:
    """Writable data directory (Vercel serverless only allows /tmp writes)."""
    base = Path("/tmp/accountflow") if os.getenv("VERCEL") else ROOT_DIR / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base


def resolve_sqlite_file(database_url: str, default_name: str = "accountflow.db") -> Path:
    if database_url.startswith("sqlite:///"):
        rel = database_url.removeprefix("sqlite:///")
        path = Path(rel)
        if path.is_absolute():
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        # On Vercel map relative sqlite paths into /tmp.
        if os.getenv("VERCEL"):
            target = data_dir() / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            return target
        target = ROOT_DIR / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    target = data_dir() / default_name
    return target


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            str(ROOT_DIR / ".env"),
            str(_API_ROOT / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./data/accountflow.db", alias="DATABASE_URL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    web_app_url: str = Field(default="http://localhost:3000", alias="WEB_APP_URL")

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    ollama_cloud_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OLLAMA_CLOUD_API_KEY", "OLLAMA_API_KEY"),
    )
    ollama_cloud_base_url: str = Field(
        default="https://ollama.com",
        validation_alias=AliasChoices("OLLAMA_CLOUD_BASE_URL", "OLLAMA_BASE_URL"),
    )
    ollama_cloud_model: str = Field(
        default="llama3.2",
        validation_alias=AliasChoices("OLLAMA_CLOUD_MODEL", "OLLAMA_MODEL"),
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        alias="ANTHROPIC_MODEL",
    )
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    stt_provider: str = Field(default="deepgram", alias="STT_PROVIDER")
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")

    integrations_mock: bool = Field(default=True, alias="INTEGRATIONS_MOCK")

    hubspot_access_token: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HUBSPOT_ACCESS_TOKEN",
            "HUBSPOT_API_TOKEN",
            "HUBSPOT_SERVICE_KEY",
        ),
    )
    hubspot_client_id: str = Field(default="", alias="HUBSPOT_CLIENT_ID")
    hubspot_client_secret: str = Field(default="", alias="HUBSPOT_CLIENT_SECRET")
    hubspot_redirect_uri: str = Field(
        default="http://localhost:8000/auth/hubspot/callback",
        alias="HUBSPOT_REDIRECT_URI",
    )

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    # Single redirect URI registered in Google Cloud Console (login + Gmail share it via state)
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        validation_alias=AliasChoices(
            "GOOGLE_REDIRECT_URI",
            "GOOGLE_LOGIN_REDIRECT_URI",
            "GOOGLE_GMAIL_REDIRECT_URI",
        ),
    )
    gmail_access_token: str = Field(
        default="",
        validation_alias=AliasChoices("GMAIL_ACCESS_TOKEN", "GOOGLE_ACCESS_TOKEN"),
    )

    jira_base_url: str = Field(
        default="",
        validation_alias=AliasChoices("JIRA_BASE_URL", "JIRA_SITE_URL"),
    )
    jira_email: str = Field(default="", alias="JIRA_EMAIL")
    jira_api_token: str = Field(default="", alias="JIRA_API_TOKEN")
    jira_project_key: str = Field(default="", alias="JIRA_PROJECT_KEY")

    # Auth + encrypted vault (operator-only; never user-facing)
    auth_allowlist: str = Field(default="", alias="AUTH_ALLOWLIST")
    jwt_secret: str = Field(default="", alias="JWT_SECRET")
    jwt_expiry_hours: int = Field(default=8, alias="JWT_EXPIRY_HOURS")
    credentials_fernet_key: str = Field(default="", alias="CREDENTIALS_FERNET_KEY")
    confidence_threshold: float = 0.7

    # Durable SQLite via Turso (preferred on Vercel). When both are set, stores use Turso.
    turso_database_url: str = Field(default="", alias="TURSO_DATABASE_URL")
    turso_auth_token: str = Field(default="", alias="TURSO_AUTH_TOKEN")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowlist_emails(self) -> list[str]:
        return [e.strip().lower() for e in self.auth_allowlist.split(",") if e.strip()]

    @property
    def hubspot_configured(self) -> bool:
        return bool(self.hubspot_access_token.strip())

    @property
    def jira_configured(self) -> bool:
        return bool(self.jira_base_url and self.jira_email and self.jira_api_token)

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    def require_auth_secrets(self) -> None:
        """Fail fast when operator crypto secrets are missing outside tests."""
        if self.app_env.lower() in {"test"}:
            return
        missing: list[str] = []
        if not self.jwt_secret.strip():
            missing.append("JWT_SECRET")
        if not self.credentials_fernet_key.strip():
            missing.append("CREDENTIALS_FERNET_KEY")
        if missing and self.app_env.lower() not in {"development", "dev"}:
            raise RuntimeError(
                f"Missing required auth secrets: {', '.join(missing)}. "
                "Generate JWT_SECRET and CREDENTIALS_FERNET_KEY before starting."
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Safe local defaults so auth crypto works without operator keys in development/tests.
    # Production (non-dev) still requires explicit JWT_SECRET + CREDENTIALS_FERNET_KEY.
    if settings.app_env.lower() in {"development", "dev", "test"}:
        updates: dict[str, Any] = {}
        if not settings.jwt_secret.strip():
            updates["jwt_secret"] = "dev-only-jwt-secret-not-for-production"
        if not settings.credentials_fernet_key.strip():
            updates["credentials_fernet_key"] = "h0Wi6NpZKs9zZeEbdl26EtoVziQR6Iq4DDCCwv2VA9c="
        if updates:
            settings = settings.model_copy(update=updates)
    return settings


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def load_yaml_config(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    example = CONFIG_DIR / name.replace(".yaml", ".example.yaml")
    target = path if path.exists() else example
    if not target.exists():
        return {}
    with open(target, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
