"""List of the offers found by stage 3, shown under the profile and on the Offers page."""
import re

import streamlit as st


def plain(text: str) -> str:
    """Escape Markdown so text copied from job sites cannot add links or formatting."""
    return re.sub(r"([\\`*_\[\]()#<>|~!])", r"\\\1", text or "")


def render(state: dict) -> None:
    offers = state.get("offers", [])
    st.subheader(f"Offers found: {len(offers)}")
    for offer in offers:
        st.markdown(f"**{plain(offer.title)}**  \n"
                    f"{plain(offer.company)} · {plain(offer.location) or 'location not given'}"
                    f" · _{offer.source}_")
        st.caption(offer.url)  # shown as text, not a clickable link
    site_errors = [e for e in state.get("errors", []) if e.startswith("find_offers")]
    if site_errors:
        with st.expander(f"Searches that failed: {len(site_errors)}"):
            for error in site_errors:
                st.code(error)
