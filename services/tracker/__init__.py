"""Track each offer's status and block duplicate submissions (Agent 6 helper).

In-memory for now: it reads the applications already in the workflow state. A
persistent (SQLite) tracker can replace these helpers later without changing the
stage-10 node, which only needs "has this offer been applied to?" and an entry.
"""
from core.models import Application, OfferStatus, TrackerEntry


def already_applied(offer_id: str, applications: list[Application]) -> bool:
    """True if this offer already has a successful application (no resubmission)."""
    return any(a.offer_id == offer_id and a.status == OfferStatus.applied
               for a in applications)


def make_entry(offer_id: str, status: OfferStatus, note: str = "") -> TrackerEntry:
    """Build a tracker entry for the offer's new status."""
    return TrackerEntry(offer_id=offer_id, status=status, note=note)
