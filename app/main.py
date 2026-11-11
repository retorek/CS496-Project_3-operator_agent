"""Streamlit entry point (placeholder pages only). Run: streamlit run app/main.py"""
import streamlit as st

PAGES = {
    "1. Upload resume": "Upload your resume here.",
    "2. Profile": "Your structured profile will appear here.",
    "6. Offers": "A batch of ranked offers will appear here.",
    "7. Decisions": "Apply / decline / dismiss, then Next, Find others or Done.",
    "9. Review": "Review the cover letter before it is sent to the test inbox.",
    "10. Tracker": "Applications and their status will appear here.",
}

st.set_page_config(page_title="Internship assistant", layout="wide")
st.title("Internship application assistant")
st.caption("Placeholder UI - nothing is wired to the graph yet.")
page = st.sidebar.radio("Page", list(PAGES))
st.header(page)
st.info(PAGES[page])
