"""Build the chat model for a stage, from config/models.yaml + keys in .env."""
from langchain.chat_models import init_chat_model

from core.config import ConfigError, Settings, get_model_spec

# Which .env key each provider needs.
_KEYS = {"openai": "openai_api_key", "google_genai": "google_api_key"}


def get_chat_model(stage: str, settings: Settings):
    spec = get_model_spec(stage)
    key = getattr(settings, _KEYS[spec.provider])
    if not key:
        raise ConfigError(f"{_KEYS[spec.provider].upper()} is missing in .env "
                          f"(needed by stage '{stage}').")
    return init_chat_model(spec.model, model_provider=spec.provider,
                           temperature=spec.temperature, api_key=key,
                           timeout=settings.llm_timeout, max_retries=settings.llm_max_retries)
