"""Stage 8 - Write cover letter."""


def node(state: dict) -> dict:
    """Input: `current_offer`, `profile`.
    Output: `cover_letters[offer_id]` (resume facts only).
    Will: call the LLM (stage 'cover_letter') with the offer fenced as untrusted data.
    Stub: placeholder text."""
    offer = state["current_offer"]
    letters = dict(state.get("cover_letters", {}))
    letters[offer.id] = f"Dear {offer.company}, (stub cover letter for {offer.title})"
    return {"cover_letters": letters, "tokens_used": state.get("tokens_used", 0) + 100}
