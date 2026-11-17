"""Build the chat model for a stage, from config/models.yaml + keys in .env."""
from langchain.chat_models import init_chat_model

from core.config import PROVIDER_KEYS, ConfigError, Settings, get_model_spec


def get_chat_model(stage: str, settings: Settings, provider: str):
    """`provider` is the one chosen for the run (state["llm_provider"])."""
    spec = get_model_spec(stage, provider)
    key = getattr(settings, PROVIDER_KEYS[provider])
    if not key:
        raise ConfigError(f"{PROVIDER_KEYS[provider].upper()} is missing in .env "
                          f"(needed by stage '{stage}').")
    extra = {} if spec.temperature is None else {"temperature": spec.temperature}
    return init_chat_model(spec.model, model_provider=provider, api_key=key,
                           timeout=settings.llm_timeout, max_retries=settings.llm_max_retries,
                           **extra)
