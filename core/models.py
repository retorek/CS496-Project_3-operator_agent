"""Shared data models (Pydantic v2). Keep minimal; extend as needed."""
import hashlib
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, model_validator


def make_offer_id(source: str, url: str) -> str:
    """Stable id: hash of source + url."""
    return hashlib.sha256(f"{source}|{url}".encode()).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Profile(BaseModel):
    name: str
    email: str
    education: list[str] = []
    experience: list[str] = []
    skills: list[str] = []
    languages: list[str] = []
    target_roles: list[str] = []
    location_preferences: list[str] = []


class Offer(BaseModel):
    id: str = ""  # computed from source + url if left empty
    source: str
    url: str
    title: str
    company: str
    location: str = ""
    description: str = ""
    scraped_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _set_id(self):
        if not self.id:
            self.id = make_offer_id(self.source, self.url)
        return self


class SecurityVerdict(BaseModel):
    offer_id: str
    safe: bool
    reasons: list[str] = []


class RankedOffer(BaseModel):
    offer: Offer
    score: int = Field(ge=0, le=100)
    reason: str = ""


class OfferStatus(str, Enum):
    shown = "shown"
    applied = "applied"
    declined = "declined"
    dismissed = "dismissed"
    failed = "failed"
    quarantined = "quarantined"


class Application(BaseModel):
    offer_id: str
    cover_letter: str
    status: OfferStatus = OfferStatus.applied
    sent_at: datetime | None = None


class TrackerEntry(BaseModel):
    offer_id: str
    status: OfferStatus
    updated_at: datetime = Field(default_factory=_now)
    note: str = ""
