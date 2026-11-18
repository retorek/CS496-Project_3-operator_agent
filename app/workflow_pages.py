"""Pages 7, 9 and 10: choose offers, review each cover letter, follow the applications."""
import logging

import streamlit as st

from app import workflow
from app.offers_view import offer_box, plain
from core import log
from core.config import ConfigError, get_settings

logger = logging.getLogger(__name__)  # full error details for the terminal

DECISIONS = {"Apply": "selected", "Decline": "declined", "Dismiss": "dismissed"}
ACTIONS = {"next": "Show next offers", "find_others": "Find other offers", "done": "Done"}


def submit(answer: dict) -> None:
    """Send the user's answer to the paused run, then redraw on the page of the next pause."""
    log.user(describe(answer))
    try:
        with st.spinner("Working... (letters and fact checks can take a minute)"):
            workflow.resume(answer)
    except ConfigError as e:  # e.g. API key missing
        st.error(f"Configuration problem: {e}")
        return
    except Exception:  # details in the terminal only
        logger.exception("Workflow step failed")
        st.error("Unexpected error. The details are in the terminal running Streamlit.")
        return
    st.rerun()


def describe(answer: dict) -> str:
    """One log line for an answer: counts and choices, no offer text."""
    if "decision" in answer:
        offer = st.session_state["profile_run"]["current_offer"]
        return f"review: {answer['decision']} the letter for '{offer.title}'"
    counts = ", ".join(f"{label.lower()} {len(answer[key])}" for label, key in DECISIONS.items())
    return f"decisions: {counts}, then {ACTIONS[answer['action']].lower()}"


def not_here(state: dict | None) -> None:
    """Shown when this page has nothing to do right now."""
    stage = workflow.pending_stage()
    if stage:
        st.info(f"The workflow is waiting on the **{workflow.PAGES[stage]}** page.")
    elif state:
        st.info("The workflow has finished. See the **Tracker** page.")
    else:
        st.info("Build your profile first.")


def decisions(state: dict | None) -> None:
    """Stage 7: one decision per offer of the batch, then what to do next."""
    if workflow.pending_stage() != "user_decides":
        return not_here(state)
    batch = state.get("current_batch", [])
    if not batch:
        st.info("No more offers in this list. Find other offers or finish.")
    with st.form("decisions"):
        choices = {}
        for position, item in enumerate(batch, start=1):
            with offer_box(item.offer, item, position):
                choices[item.offer.id] = st.radio("Your decision", list(DECISIONS), index=None,
                                                  horizontal=True, key=f"decision_{item.offer.id}")
        columns = st.columns(len(ACTIONS))
        clicked = [a for a, col in zip(ACTIONS, columns) if col.form_submit_button(ACTIONS[a])]
    if clicked:
        answer = {key: [oid for oid, choice in choices.items() if DECISIONS.get(choice) == key]
                  for key in DECISIONS.values()}
        submit(answer | {"action": clicked[0]})


def review(state: dict | None) -> None:
    """Stage 9: read the letter and its fact check, then confirm, rewrite or cancel."""
    if workflow.pending_stage() != "review":
        return not_here(state)
    offer = state["current_offer"]
    report = state.get("cover_letter_reports", {}).get(offer.id, {})
    st.subheader(f"{plain(offer.title)} · {plain(offer.company)}")
    with st.container(border=True):  # escaped: the letter may quote the untrusted offer
        st.markdown(plain(st.session_state["pending"]["letter"]).replace("\n", "  \n"))
    if report.get("passed"):
        st.success("Fact check passed: every claim is backed by your resume.")
    else:
        st.error("Fact check failed: this letter cannot be sent. Write it again or cancel.")
        st.text("\n".join(f"- {claim}" for claim in report.get("unsupported", [])) or report.get("error", ""))
    confirm, rewrite, cancel = st.columns(3)
    if confirm.button("Confirm and send to the test inbox", type="primary",
                      disabled=not report.get("passed")):
        submit({"decision": "confirm"})
    if rewrite.button("Write it again"):
        submit({"decision": "edit"})
    if cancel.button("Cancel this offer"):
        submit({"decision": "cancel"})


def tracker(state: dict | None) -> None:
    """Stage 10: what this session found, blocked and applied to."""
    if not state:
        return not_here(state)
    test_mode = state.get("send_dry_run", True)
    counts = {"Offers found": len(state.get("offers", [])),
              "Blocked": len(state.get("quarantined", [])),
              "Ranked": len(state.get("ranked", [])),
              "Applications prepared" if test_mode else "Applications sent":
                  state.get("applications_sent", 0)}
    for column, (label, value) in zip(st.columns(len(counts)), counts.items()):
        column.metric(label, value)
    if test_mode:
        st.caption("Test mode: emails are prepared but not sent. Set SEND_EMAILS=true in .env "
                   "to send them to the test inbox.")
    else:
        st.caption(f"Emails go only to the test inbox ({get_settings(dry=True).test_inbox}), "
                   "never to the employer.")
    offers = {o.id: o for o in state.get("offers", [])}
    sent_label = "prepared" if test_mode else "sent"
    rows = [{"Offer": offers[a.offer_id].title if a.offer_id in offers else a.offer_id,
             "Company": offers[a.offer_id].company if a.offer_id in offers else "",
             "Status": sent_label if a.status.value == "applied" else a.status.value,
             "Date": a.sent_at.strftime("%Y-%m-%d %H:%M") if a.sent_at else ""}
            for a in state.get("applications", [])]
    if rows:
        st.dataframe(rows, hide_index=True)  # shown as data: nothing in it is rendered
    else:
        st.info("No applications yet.")
    if not workflow.pending_stage():
        st.caption(f"Run finished. Stop reason: {state.get('stop_reason')}")
    if state.get("errors"):
        with st.expander(f"Errors: {len(state['errors'])}"):
            for error in state["errors"]:
                st.code(error)
