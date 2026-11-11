"""Stage 1 - Upload resume."""
from core.samples import load_resume


def node(state: dict) -> dict:
    """Input: nothing (the Streamlit page will provide the file in the real version).
    Output: `resume_text` (raw text).
    Will: read the uploaded resume file and extract its text.
    Stub: returns a sample resume from data/samples/."""
    return {"resume_text": load_resume()}
