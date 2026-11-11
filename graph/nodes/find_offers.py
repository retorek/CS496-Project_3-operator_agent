"""Stage 3 - Find offers (the only real agent loop)."""
from core.samples import load_offers


def node(state: dict) -> dict:
    """Input: `profile`, `offers` (already seen).
    Output: `offers` = previous offers + new ones; already-seen ones are skipped (by id).
    Will: run an agent loop (LLM + scraping tools from services/scraping/) over job sites.
    Stub: returns the sample offers not already in state."""
    seen = {o.id for o in state.get("offers", [])}
    new = [o for o in load_offers() if o.id not in seen]
    return {"offers": list(state.get("offers", [])) + new,
            "tokens_used": state.get("tokens_used", 0) + 100}
