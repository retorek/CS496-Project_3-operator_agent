"""Offers after stages 3-5: ranked offers in cards with their match score, blocked offers
apart with the reasons. Shown under the profile and on the Offers page."""
import re

import streamlit as st


def plain(text: str) -> str:
    """Escape Markdown so text copied from job sites cannot add links or formatting."""
    return re.sub(r"([\\`*_\[\]()#<>|~!])", r"\\\1", text or "")


def score_color(score: int) -> str:
    """Streamlit text color for a match score."""
    return "green" if score >= 70 else "orange" if score >= 40 else "red"


def offer_box(offer, ranked=None, position: int = 0) -> None:
    """One offer in a bordered card. With `ranked`: position, score, bar and reason.
    The description stays hidden until clicked."""
    with st.container(border=True):
        info, score_col = st.columns([5, 1])
        with info:
            prefix = f"{position}. " if position else ""
            st.markdown(f"#### {prefix}{plain(offer.title)}")
            st.markdown(f"🏢 {plain(offer.company) or 'Company not given'}  ·  "
                        f"📍 {plain(offer.location) or 'Location not given'}")
        if ranked is not None:
            with score_col:
                st.markdown(f"### :{score_color(ranked.score)}[{ranked.score}]")
                st.caption("match / 100")
            st.progress(ranked.score)
            st.markdown(f"**Why:** {plain(ranked.reason)}")
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
    ranked = state.get("ranked", [])
    safe = state.get("safe_offers", [])
    if ranked:  # stage 5 done: best match first
        st.subheader(f"Offers ranked for you: {len(ranked)}")
        st.caption("Sorted by how well each offer matches your profile.")
        for position, item in enumerate(ranked, start=1):
            offer_box(item.offer, item, position)
    elif safe:  # ranking failed or not run: offers in the order found
        st.subheader(f"Offers: {len(safe)}")
        st.warning("These offers could not be ranked, so they are shown in the order found.")
        for offer in safe:
            offer_box(offer)
    else:
        st.subheader("Offers: 0")
        st.info("No safe offers found. Try other locations or another way to find offers.")
    blocked_section(state)
    site_errors = [e for e in state.get("errors", []) if e.startswith("find_offers")]
    if site_errors:
        with st.expander(f"Searches that failed: {len(site_errors)}"):
            for error in site_errors:
                st.code(error)
