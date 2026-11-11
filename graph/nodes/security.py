"""Stage 4 - Security check."""
import re

from core.models import SecurityVerdict

# Stub heuristic only. The real stage must treat offer text as untrusted data.
_SUSPICIOUS = re.compile(r"ignore (all )?previous instructions|passport|bank details|password", re.I)


def node(state: dict) -> dict:
    """Input: `offers`.
    Output: `quarantined` (verdicts for flagged offers). Safe offers stay in `offers`.
    Will: detect prompt injection, suspicious links and personal-data requests.
    Stub: keyword match on the description."""
    flagged = [
        SecurityVerdict(offer_id=o.id, safe=False, reasons=["suspicious keyword (stub)"])
        for o in state.get("offers", []) if _SUSPICIOUS.search(o.description)
    ]
    return {"quarantined": flagged}
