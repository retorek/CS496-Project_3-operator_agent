"""Resume & profile page: upload a resume, give locations, build the profile and find offers."""
import logging

import streamlit as st

from app import offers_view, workflow
from app.uploads import UploadError, save_upload
from core import log
from core.config import ConfigError, get_settings
from core.state import initial_state

logger = logging.getLogger(__name__)  # full error details for the terminal


# search_mode (stage 3) -> label shown to the user
SEARCH_MODES = {"stub": "Sample offers", "scrape": "Job sites",
                "agent": "Job sites, searches chosen by the AI"}


def handle_submit(file, locations_text: str, use_llm: bool, provider: str,
                  search_mode: str) -> None:
    """Save the file, run stages 1-6 (up to the first pause). Shows one clear error on failure."""
    if file is None:
        st.warning("Choose a resume file first.")
        return
    locations = [loc.strip() for loc in locations_text.split(",") if loc.strip()]
    log.user(f"submitted resume '{file.name}', locations={locations}, real model={use_llm}, "
             f"find offers={SEARCH_MODES[search_mode]}")
    wait = "" if search_mode == "stub" else " Searching job sites takes one to two minutes."
    try:
        path = save_upload(file.name, file.getvalue())
        with st.spinner(f"Building your profile and finding offers...{wait}"):
            workflow.start(initial_state(
                resume_path=str(path), location_preferences=locations, use_llm=use_llm,
                llm_provider=provider, search_mode=search_mode,
                send_dry_run=not get_settings(dry=True).send_emails))
    except UploadError as e:  # refused file (type, size, content)
        st.error(str(e))
    except ConfigError as e:  # e.g. API key missing
        st.error(f"Configuration problem: {e}")
    except (OSError, ValueError) as e:  # unreadable, damaged or scanned PDF
        st.error(f"Could not read the resume: {e}")
    except Exception:  # anything else: full details in the terminal only
        logger.exception("Profile run failed")
        st.error("Unexpected error. The details are in the terminal running Streamlit.")


def show_result(state: dict) -> None:
    if state["stop_reason"] == "llm_error":
        st.error("The model stopped (it may be busy). Try again in a minute.")
        with st.expander("Details"):
            for error in state["errors"]:
                st.code(error)
        if not state.get("profile"):
            return
    profile = state["profile"]
    st.success("Profile ready. Click below to see it.")
    with st.expander(f"Your profile: {profile.name} - {profile.email}"):  # closed by default
        for label, items in [("Target roles", profile.target_roles), ("Skills", profile.skills),
                             ("Education", profile.education), ("Experience", profile.experience),
                             ("Languages", profile.languages),
                             ("Locations", profile.location_preferences)]:
            st.markdown(f"**{label}**")
            st.markdown("\n".join(f"- {item}" for item in items) or "_none_")
    with st.expander("Text read from the resume"):
        st.text(state["resume_text"])
    offers_view.render(state)
    if workflow.pending_stage() == "user_decides":
        st.info("Next: open **Decisions** in the sidebar to choose the offers to apply to.")


def render(provider: str) -> None:
    """`provider` is the model provider chosen in the top-right picker."""
    with st.form("upload"):
        file = st.file_uploader("Resume (PDF or TXT, max 5 MB)", type=["pdf", "txt"])
        locations_text = st.text_input("Where do you want to work?", placeholder="Lyon, Remote")
        use_llm = st.checkbox("Use the real model to build the profile", value=True,
                              help="Unchecked: a fixed sample profile, no API call.")
        search_mode = st.radio("How to find offers", list(SEARCH_MODES),
                               format_func=SEARCH_MODES.get, horizontal=True)
        submitted = st.form_submit_button("Build my profile and find offers")
    if submitted:
        workflow.reset()
        handle_submit(file, locations_text, use_llm, provider, search_mode)
        if "profile_run" in st.session_state:
            st.rerun()  # redraw the page so the provider picker shows as locked
    if "profile_run" in st.session_state:
        show_result(st.session_state["profile_run"])
