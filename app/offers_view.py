"""Offers after stages 3-4: safe offers in boxes, blocked offers apart with the reasons.
Shown under the profile and on the Offers page."""
import re

import streamlit as st


def plain(text: str) -> str:
    """Escape Markdown so text copied from job sites cannot add links or formatting."""
    return re.sub(r"([\\`*_\[\]()#<>|~!])", r"\\\1", text or "")


def offer_box(offer) -> None:
    """One offer in a bordered box; the description stays hidden until clicked."""
    with st.container(border=True):
        st.markdown(f"#### {plain(offer.title)}")
        st.markdown(f"{plain(offer.company) or 'Company not given'} · "
                    f"{plain(offer.location) or 'Location not given'}")
        st.caption(f"Source: {offer.source} · `{offer.url}`")  # code text: not a clickable link
        if offer.description:
            with st.expander("Description"):
                st.text(offer.description)  # plain text: nothing in it is rendered


def blocked_section(state: dict) -> None:
    """Offers stopped by the security check (stage 4), with the reasons."""
    verdicts = state.get("quarantined", [])
    if not verdicts:
        return
    by_id = {o.id: o for o in state.get("offers", [])}
    if any(r.startswith("CLASSIFICATION_ERROR") for v in verdicts for r in v.reasons):
        st.warning("Some offers could not be checked (missing API key or busy model), "
                   "so they were blocked to be safe.")
    with st.expander(f"Blocked by the security check: {len(verdicts)}"):
        for verdict in verdicts:
            offer = by_id.get(verdict.offer_id)
            with st.container(border=True):
                st.markdown(f"**{plain(offer.title) if offer else verdict.offer_id}**")
                st.text("\n".join(f"- {reason}" for reason in verdict.reasons))


def render(state: dict) -> None:
    safe = state.get("safe_offers", [])
    st.subheader(f"Offers: {len(safe)}")
    if not safe:
        st.info("No safe offers found. Try other locations or another way to find offers.")
    for offer in safe:
        offer_box(offer)
    blocked_section(state)
    site_errors = [e for e in state.get("errors", []) if e.startswith("find_offers")]
    if site_errors:
        with st.expander(f"Searches that failed: {len(site_errors)}"):
            for error in site_errors:
                st.code(error)
