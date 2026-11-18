"""Stage 10 - Apply (Agent 6)."""
from datetime import datetime, timezone

from core.models import Application, OfferStatus
from services.mailer import MailerError, send_application
from services.tracker import already_applied


def node(state: dict) -> dict:
    """Input: `current_offer`, `cover_letters`, `cover_letter_reports`, `profile`,
    `send_dry_run` (default True).
    Output: `applications` + the new Application, `applications_sent` (+1 only on a
    real/dry delivery), `current_offer` cleared.
    Refuses any letter that did not pass the fact check and any offer already applied
    to; otherwise emails the application + letter to the TEST inbox (never the
    employer) via services/mailer. `send_dry_run=True` builds the mail without sending.
    Every return includes `applications_sent` (the graph's limit guard reads it)."""
    offer = state["current_offer"]
    profile = state.get("profile")
    letter = state.get("cover_letters", {}).get(offer.id, "")
    report = state.get("cover_letter_reports", {}).get(offer.id)
    applications = list(state.get("applications", []))
    sent = state.get("applications_sent", 0)

    # Duplicate protection: the same internship is never submitted twice.
    if already_applied(offer.id, applications):
        return {"applications": applications, "applications_sent": sent, "current_offer": None}

    # Agent 6 refuses any letter that did not pass the fact check.
    if not report or not report.get("passed"):
        failed = Application(offer_id=offer.id, cover_letter=letter, status=OfferStatus.failed)
        return {"applications": applications + [failed], "applications_sent": sent,
                "current_offer": None,
                "errors": [f"apply: {offer.id} not sent (cover letter failed the fact check)."]}

    dry_run = state.get("send_dry_run", True)
    try:
        send_application(profile, offer, letter, dry_run=dry_run)
    except MailerError as exc:
        failed = Application(offer_id=offer.id, cover_letter=letter, status=OfferStatus.failed)
        return {"applications": applications + [failed], "applications_sent": sent,
                "current_offer": None, "errors": [f"apply: sending failed ({exc})."]}

    app = Application(offer_id=offer.id, cover_letter=letter, status=OfferStatus.applied,
                      sent_at=datetime.now(timezone.utc))
    return {"applications": applications + [app], "applications_sent": sent + 1,
            "current_offer": None}
