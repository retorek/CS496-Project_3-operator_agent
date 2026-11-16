"""Stage 1 - Upload resume."""
from core.resume_reader import read_resume
from core.samples import load_resume


def node(state: dict) -> dict:
    """Input: `resume_path` (.pdf or .txt; set by the CLI now, by Streamlit later).
    Output: `resume_text` (raw text).
    `location_preferences` is already in the state from the same upload; nothing to do here.
    If no path is given, falls back to the mock sample in data/samples/."""
    path = state.get("resume_path", "")
    text = read_resume(path) if path else load_resume()
    return {"resume_text": text}
