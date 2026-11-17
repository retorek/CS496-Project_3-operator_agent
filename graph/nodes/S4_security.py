"""Stage 4 - Screen offers while preserving discovery history."""
from core.models import SecurityVerdict
from services.security.guardian import analyze_offer


def node(state: dict) -> dict:
    safe_offers, quarantined = [], []
    tokens_used = state.get("tokens_used", 0)

    def add_tokens(count: int) -> None:
        nonlocal tokens_used
        tokens_used += count

    for offer in state.get("offers", []):
        try:
            verdict = analyze_offer(offer, dry_run=state.get("security_dry_run", False),
                                    on_tokens=add_tokens, provider=state.get("llm_provider"))
            if not isinstance(verdict, SecurityVerdict) or verdict.offer_id != offer.id:
                raise ValueError("Invalid security verdict")
            if verdict.safe is True and not verdict.reasons:
                safe_offers.append(offer)
                continue
            verdict = SecurityVerdict(offer_id=offer.id, safe=False,
                                      reasons=verdict.reasons or ["Security rejected this offer."])
        except Exception:
            verdict = SecurityVerdict(offer_id=offer.id, safe=False,
                                      reasons=["CLASSIFICATION_ERROR: Security classification failed."])
        quarantined.append(verdict)
    blocked = {verdict.offer_id for verdict in quarantined}
    return {"safe_offers": [offer for offer in safe_offers if offer.id not in blocked],
            "quarantined": quarantined, "tokens_used": tokens_used}
