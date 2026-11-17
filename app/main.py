"""Streamlit entry point. Run: streamlit run app/main.py"""
import sys
from pathlib import Path

# `streamlit run` only puts app/ on the import path; add the project root for core/, graph/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from app import provider_picker, upload_page  # noqa: E402

PLACEHOLDERS = {
    "6. Offers": "A batch of ranked offers will appear here.",
    "7. Decisions": "Apply / decline / dismiss, then Next, Find others or Done.",
    "9. Review": "Review the cover letter before it is sent to the test inbox.",
    "10. Tracker": "Applications and their status will appear here.",
}

st.set_page_config(page_title="Internship assistant", layout="wide")
title_col, provider_col = st.columns([3, 1])
title_col.title("Internship application assistant")
with provider_col:  # locked once a run exists, so one provider is used from start to end
    provider = provider_picker.render(locked="profile_run" in st.session_state)
page = st.sidebar.radio("Page", ["1-2. Resume & profile", *PLACEHOLDERS])
st.header(page)
if page in PLACEHOLDERS:
    st.info(PLACEHOLDERS[page])
else:
    upload_page.render(provider)
