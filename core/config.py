"""Typed settings loaded from .env, plus per-stage model config (config/models.yaml)."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MODELS_YAML = Path(__file__).resolve().parent.parent / "config" / "models.yaml"

# LangChain provider name -> label shown to the user, and the Settings field holding its key.
PROVIDERS = {"openai": "OpenAI", "google_genai": "Gemini"}
PROVIDER_KEYS = {"openai": "openai_api_key", "google_genai": "google_api_key"}


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    google_api_key: str | None = None
    langsmith_api_key: str | None = None
    langsmith_tracing: bool = True
    langsmith_project: str = "internship-agent"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str | None = None
    smtp_password: str | None = None
    test_inbox: str = "test-inbox@example.com"
    batch_size: int = 3
    max_applications: int = 3
    max_steps: int = 50
    max_tokens: int = 200_000
    llm_timeout: int = 60       # seconds per model call
    llm_max_retries: int = 2    # retries on overload/timeout, then the stage fails
    llm_provider: Literal["openai", "google_genai"] = "openai"  # default choice for a new run
    # Stage 3 (find offers)
    scrape_delay: float = 1.0       # seconds between two requests to the same site
    scrape_timeout: int = 15        # seconds per request
    max_offers_per_search: int = 5  # new offers kept per (source, query, location)
    max_queries: int = 4            # (role, location) pairs searched in "scrape" mode
    find_max_tool_calls: int = 6    # searches the "agent" mode may run

    @field_validator("openai_api_key", "google_api_key", "langsmith_api_key", "smtp_user", "smtp_password")
    @classmethod
    def _empty_is_none(cls, v):
        return v or None


def key_status(settings: Settings) -> dict[str, bool]:
    """Provider -> is its API key set in .env. No network call."""
    return {p: bool(getattr(settings, field)) for p, field in PROVIDER_KEYS.items()}


def get_settings(dry: bool = False, provider: str | None = None) -> Settings:
    """Load settings. The chosen provider's key (default LLM_PROVIDER) is required unless dry=True."""
    settings = Settings()
    provider = provider or settings.llm_provider
    if not dry and not key_status(settings)[provider]:
        raise ConfigError(
            f"{PROVIDER_KEYS[provider].upper()} is missing. Copy .env.example to .env and set it, "
            "or run with --dry (no keys needed)."
        )
    return settings


class ModelSpec(BaseModel):
    model: str
    temperature: float | None = None  # None: the provider's default


def load_model_config(path: Path = MODELS_YAML) -> dict[str, dict[str, ModelSpec]]:
    """Stage -> provider -> ModelSpec. The only place model names are read."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {stage: {provider: ModelSpec(**spec) for provider, spec in by_provider.items()}
            for stage, by_provider in raw.items()}


def get_model_spec(stage: str, provider: str) -> ModelSpec:
    return load_model_config()[stage][provider]
