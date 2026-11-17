"""Page 1-2: upload a resume, give locations, build and show the profile."""
import logging
import uuid

import streamlit as st

from app.uploads import UploadError, save_upload
from core.config import ConfigError, get_settings
from core.state import initial_state
from graph.graph import build_graph

log = logging.getLogger(__name__)


def run_profile(resume_path: str, locations: list[str], use_llm: bool) -> dict:
    """Run the graph until its first pause (stage 7) and return the state.
    Stages 3-6 are still stubs, so in practice this builds the profile."""
    settings = get_settings(dry=True)  # API keys are checked by core/llm.py when needed
    graph = build_graph(settings)
    config = {"configurable": {"thread_id": str(uuid.uuid4())},
              "recursion_limit": settings.max_steps + 20}
    graph.invoke(initial_state(resume_path=resume_path, location_preferences=locations,
                               use_llm=use_llm), config)
    return graph.get_state(config).values


def handle_submit(file, locations_text: str, use_llm: bool) -> None:
    """Save the file, run the profile stage, store the result. Shows one clear error on failure."""
    if file is None:
        st.warning("Choose a resume file first.")
        return
    locations = [loc.strip() for loc in locations_text.split(",") if loc.strip()]
    try:
        path = save_upload(file.name, file.getvalue())
        with st.spinner("Reading your resume and building the profile..."):
            st.session_state["profile_run"] = run_profile(str(path), locations, use_llm)
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
        st.error("The model could not build your profile (it may be busy). Try again in a minute.")
        with st.expander("Details"):
            for error in state["errors"]:
                st.code(error)
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


def render() -> None:
    with st.form("upload"):
        file = st.file_uploader("Resume (PDF or TXT, max 5 MB)", type=["pdf", "txt"])
        locations_text = st.text_input("Where do you want to work?", placeholder="Lyon, Remote")
        use_llm = st.checkbox("Use the real model to build the profile", value=True,
                              help="Unchecked: a fixed sample profile, no API call.")
        submitted = st.form_submit_button("Build my profile")
    if submitted:
        st.session_state.pop("profile_run", None)
        handle_submit(file, locations_text, use_llm)
    if "profile_run" in st.session_state:
        show_result(st.session_state["profile_run"])
