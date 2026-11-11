"""Stage 5 - Rank offers."""
from core.models import RankedOffer


def node(state: dict) -> dict:
    """Input: `profile`, `offers`, `quarantined`.
    Output: `ranked` (safe offers only, best first, score 0-100 + short reason).
    Will: score each safe offer against the profile with the LLM (stage 'rank').
    Stub: descending dummy scores in list order."""
    bad = {v.offer_id for v in state.get("quarantined", [])}
    safe = [o for o in state.get("offers", []) if o.id not in bad]
    ranked = [RankedOffer(offer=o, score=max(0, 90 - 5 * i), reason="dummy score (stub)")
              for i, o in enumerate(safe)]
    return {"ranked": ranked, "tokens_used": state.get("tokens_used", 0) + 100}
