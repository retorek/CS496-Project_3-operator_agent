"""Stage 10 - Apply."""
from datetime import datetime, timezone

from core.models import Application, OfferStatus


def node(state: dict) -> dict:
    """Input: `current_offer`, `cover_letters`.
    Output: `applications` + 1, `applications_sent` + 1, `current_offer` cleared.
    Will: email the application + letter to TEST_INBOX (never the employer) via
    services/mailer/, then update the tracker in services/tracker/.
    Stub: records an Application without sending anything."""
    offer = state["current_offer"]
    app = Application(offer_id=offer.id, cover_letter=state["cover_letters"][offer.id],
                      status=OfferStatus.applied, sent_at=datetime.now(timezone.utc))
    return {"applications": list(state.get("applications", [])) + [app],
            "applications_sent": state.get("applications_sent", 0) + 1,
            "current_offer": None}
