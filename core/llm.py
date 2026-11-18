"""Build the chat model for a stage, from config/models.yaml + keys in .env."""
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.rate_limiters import InMemoryRateLimiter

from core import log
from core.config import PROVIDER_KEYS, ConfigError, Settings, get_model_spec

# Shared by every model: all stages together send at most LLM_REQUESTS_PER_MINUTE requests.
RATE_LIMITER = InMemoryRateLimiter(requests_per_second=Settings().llm_requests_per_minute / 60)


class LogCalls(BaseCallbackHandler):
    """Prints one SYSTEM line per model request, reply and failure (never the content)."""

    def __init__(self, stage: str, model: str):
        self.what = f"{stage} model ({model})"

    def on_chat_model_start(self, serialized, messages, **kwargs):
        log.system(f"{self.what}: request sent")

    def on_llm_end(self, response, **kwargs):
        message = getattr(response.generations[0][0], "message", None)
        tokens = (getattr(message, "usage_metadata", None) or {}).get("total_tokens", "?")
        log.system(f"{self.what}: reply received ({tokens} tokens)")

    def on_llm_error(self, error, **kwargs):
        log.system(f"{self.what}: failed ({type(error).__name__})")


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
                           rate_limiter=RATE_LIMITER, callbacks=[LogCalls(stage, spec.model)],
                           **extra)
