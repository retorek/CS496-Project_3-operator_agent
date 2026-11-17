"""Streamlit entry point. Run: streamlit run app/main.py"""
import sys
from pathlib import Path

# `streamlit run` only puts app/ on the import path; add the project root for core/, graph/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app import offers_view, provider_picker, upload_page  # noqa: E402

PLACEHOLDERS = {
    "7. Decisions":"Apply / decline / dismiss, then Next, Find others or Done.",
    "9. Review": "Review the cover letter before it is sent to the test inbox.",
    "10. Tracker": "Applications and their status will appear here.",
}

st.set_page_config(page_title="Internship assistant", layout="wide")
title_col, provider_col = st.columns([3, 1])
title_col.title("Internship application assistant")
with provider_col:  # locked once a run exists, so one provider is used from start to end
    provider = provider_picker.render(locked="profile_run" in st.session_state)
page = st.sidebar.radio("Page", ["1-3. Resume & profile", "Offers", *PLACEHOLDERS])
st.header(page)
if page in PLACEHOLDERS:
    st.info(PLACEHOLDERS[page])
elif page == "Offers":
    if "profile_run" in st.session_state:
        offers_view.render(st.session_state["profile_run"])
    else:
        st.info("Build your profile first: offers are searched at the same time.")
else:
    upload_page.render(provider)
