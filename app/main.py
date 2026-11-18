"""Streamlit entry point. Run: streamlit run app/main.py"""
import sys
from pathlib import Path

# `streamlit run` only puts app/ on the import path; add the project root for core/, graph/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app import offers_view, provider_picker, upload_page, workflow_pages  # noqa: E402
from core import log  # noqa: E402

PAGES = ["Resume & profile", "Offers", "Decisions", "Review", "Tracker"]

st.set_page_config(page_title="Internship assistant", layout="wide")
title_col, provider_col = st.columns([3, 1])
title_col.title("Internship application assistant")
with provider_col:  # locked once a run exists, so one provider is used from start to end
    provider = provider_picker.render(locked="profile_run" in st.session_state)
if "goto" in st.session_state:  # set by the workflow: open the page of the next pause
    st.session_state["page"] = st.session_state.pop("goto")
page = st.sidebar.radio("Page", PAGES, key="page",
                        on_change=lambda: log.user(f"opened page {st.session_state['page']}"))
st.header(page)
state = st.session_state.get("profile_run")
if page == "Offers" and state:
    offers_view.render(state)
elif page == "Offers":
    st.info("Build your profile first.")
elif page == "Decisions":
    workflow_pages.decisions(state)
elif page == "Review":
    workflow_pages.review(state)
elif page == "Tracker":
    workflow_pages.tracker(state)
else:
    upload_page.render(provider)
