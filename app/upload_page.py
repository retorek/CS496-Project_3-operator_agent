"""Page 1-3: upload a resume, give locations, build the profile and find offers."""
import logging
import uuid

import streamlit as st

from app import offers_view
from app.uploads import UploadError, save_upload
from core.config import ConfigError, get_settings
from core.state import initial_state
from graph.graph import build_graph

log = logging.getLogger(__name__)


# search_mode (stage 3) -> label shown to the user
SEARCH_MODES = {"stub": "Sample offers", "scrape": "Job sites",
                "agent": "Job sites, searches chosen by the AI"}


def run_profile(resume_path: str, locations: list[str], use_llm: bool, provider: str,
                search_mode: str) -> dict:
    """Run the graph until its first pause (stage 7) and return the state:
    profile (stage 2) and offers (stage 3). Stages 4-6 are still stubs."""
    settings = get_settings(dry=True)  # API keys are checked by core/llm.py when needed
    graph = build_graph(settings)
    config = {"configurable": {"thread_id": str(uuid.uuid4())},
              "recursion_limit": settings.max_steps + 20}
    graph.invoke(initial_state(resume_path=resume_path, location_preferences=locations,
                               use_llm=use_llm, llm_provider=provider,
                               search_mode=search_mode), config)
    return graph.get_state(config).values


def handle_submit(file, locations_text: str, use_llm: bool, provider: str,
                  search_mode: str) -> None:
    """Save the file, run stages 1-6, store the result. Shows one clear error on failure."""
    if file is None:
        st.warning("Choose a resume file first.")
        return
    locations = [loc.strip() for loc in locations_text.split(",") if loc.strip()]
    wait = "" if search_mode == "stub" else " Searching job sites takes one to two minutes."
    try:
        path = save_upload(file.name, file.getvalue())
        with st.spinner(f"Building your profile and finding offers...{wait}"):
            st.session_state["profile_run"] = run_profile(str(path), locations, use_llm,
                                                          provider, search_mode)
    except UploadError as e:  # refused file (type, size, content)
        st.error(str(e))
    except ConfigError as e:  # e.g. API key missing
        st.error(f"Configuration problem: {e}")
    except (OSError, ValueError) as e:  # unreadable, damaged or scanned PDF
        st.error(f"Could not read the resume: {e}")
    except Exception:  # anything else: full details in the terminal only
        log.exception("Profile run failed")
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
    st.success("Profile ready.")
    st.subheader(f"{profile.name} - {profile.email}")
    for label, items in [("Target roles", profile.target_roles), ("Skills", profile.skills),
                         ("Education", profile.education), ("Experience", profile.experience),
                         ("Languages", profile.languages),
                         ("Locations", profile.location_preferences)]:
        st.markdown(f"**{label}**")
        st.markdown("\n".join(f"- {item}" for item in items) or "_none_")
    with st.expander("Text read from the resume"):
        st.text(state["resume_text"])
    offers_view.render(state)


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
        st.session_state.pop("profile_run", None)
        handle_submit(file, locations_text, use_llm, provider, search_mode)
        if "profile_run" in st.session_state:
            st.rerun()  # redraw the page so the provider picker shows as locked
    if "profile_run" in st.session_state:
        show_result(st.session_state["profile_run"])
