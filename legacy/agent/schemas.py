"""Strict input schemas for the 4 tools (shared contract with P2)."""
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class SearchJobsInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(5, ge=1, le=10)


class ReadOfferInput(BaseModel):
    offer_id: str = Field(min_length=1)


class UpdateTrackerInput(BaseModel):
    offer_id: str = Field(min_length=1)
    status: Literal["interested", "skip", "applied"]
    match_score: int = Field(ge=0, le=100)
    notes: str = ""


class SubmitApplicationInput(BaseModel):
    offer_id: str = Field(min_length=1)
    letter: str = Field(min_length=20)


class ToolError(Exception):
    """Error message meant to be read by the model (no stack trace)."""


def readable(err: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in err.errors()
    )
