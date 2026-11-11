"""Stage 2 - Build profile."""
from core.models import Profile


def node(state: dict) -> dict:
    """Input: `resume_text`.
    Output: `profile` (skills, experience, education, inferred target roles).
    Will: call the LLM (model from config/models.yaml, stage 'profile') to structure the resume.
    Stub: returns a fixed Profile."""
    profile = Profile(
        name="Alice Martin", email="alice.martin@example.com",
        education=["MSc Computer Science, INSA Lyon"],
        experience=["Data Science Intern, Acme Analytics"],
        skills=["Python", "SQL", "scikit-learn"], languages=["French", "English"],
        target_roles=["Data Scientist Intern"], location_preferences=["Lyon", "Remote"],
    )
    return {"profile": profile, "tokens_used": state.get("tokens_used", 0) + 100}
