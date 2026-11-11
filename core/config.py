"""Typed settings loaded from .env (and the environment)."""
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(RuntimeError):
    """Raised when a required setting is missing."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
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

    @field_validator("openai_api_key", "langsmith_api_key", "smtp_user", "smtp_password")
    @classmethod
    def _empty_is_none(cls, v):
        return v or None


def get_settings(dry: bool = False) -> Settings:
    """Load settings. A missing OpenAI key is an error unless dry=True."""
    settings = Settings()
    if not dry and not settings.openai_api_key:
        raise ConfigError(
            "OPENAI_API_KEY is missing. Copy .env.example to .env and set it, "
            "or run with --dry (no keys needed)."
        )
    return settings


# --- Per-stage model configuration (config/models.yaml) ---
from pathlib import Path  # noqa: E402

import yaml  # noqa: E402
from pydantic import BaseModel  # noqa: E402

MODELS_YAML = Path(__file__).resolve().parent.parent / "config" / "models.yaml"


class ModelSpec(BaseModel):
    model: str
    temperature: float = 0.0


def load_model_config(path: Path = MODELS_YAML) -> dict[str, ModelSpec]:
    """Stage name -> ModelSpec. The only place model names are read."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {stage: ModelSpec(**spec) for stage, spec in raw.items()}


def get_model_spec(stage: str) -> ModelSpec:
    return load_model_config()[stage]
