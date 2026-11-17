"""Top-right model provider picker: chosen once per run, then locked until "Start over"."""
import streamlit as st

from core.config import PROVIDER_KEYS, PROVIDERS, get_settings, key_status


def render(locked: bool) -> str:
    """Show the OpenAI / Gemini choice and whether its key is set. Returns the provider."""
    settings = get_settings(dry=True)
    st.session_state.setdefault("llm_provider", settings.llm_provider)  # default: LLM_PROVIDER
    provider = st.radio("Model provider", list(PROVIDERS), format_func=PROVIDERS.get,
                        horizontal=True, key="llm_provider", disabled=locked)
    if key_status(settings)[provider]:
        st.caption("✓ API key set")
    else:
        st.caption(f"✗ {PROVIDER_KEYS[provider].upper()} missing in .env")
    if locked:
        st.caption("Locked for this run.")
        if st.button("Start over"):
            st.session_state.pop("profile_run", None)
            st.rerun()
    return provider
