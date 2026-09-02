from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[4]
CONFIG_DIR = ROOT_DIR / "config"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./data/accountflow.db", alias="DATABASE_URL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

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

    stt_provider: str = Field(default="deepgram", alias="STT_PROVIDER")
    deepgram_api_key: str = Field(default="", alias="DEEPGRAM_API_KEY")

    integrations_mock: bool = Field(default=True, alias="INTEGRATIONS_MOCK")
    hubspot_client_id: str = Field(default="", alias="HUBSPOT_CLIENT_ID")
    hubspot_client_secret: str = Field(default="", alias="HUBSPOT_CLIENT_SECRET")
    hubspot_redirect_uri: str = Field(
        default="http://localhost:8000/auth/hubspot/callback",
        alias="HUBSPOT_REDIRECT_URI",
    )
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        alias="GOOGLE_REDIRECT_URI",
    )
    jira_base_url: str = Field(default="", alias="JIRA_BASE_URL")
    jira_email: str = Field(default="", alias="JIRA_EMAIL")
    jira_api_token: str = Field(default="", alias="JIRA_API_TOKEN")
    jira_project_key: str = Field(default="", alias="JIRA_PROJECT_KEY")

    confidence_threshold: float = 0.7

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


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
