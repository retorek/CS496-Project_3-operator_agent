"""Workflow state shared by all graph nodes.

Nodes return partial updates (dicts). `errors` is append-only (reducer);
every other key is overwritten by the node that returns it.
"""
import operator
from typing import Annotated, TypedDict

from core.models import Application, Offer, Profile, RankedOffer, SecurityVerdict


class WorkflowState(TypedDict, total=False):
    resume_path: str                      # stage 1 input: .pdf or .txt file ("" = mock sample)
    resume_text: str                      # stage 1 output
    location_preferences: list[str]       # stage 1 output (user input at upload)
    use_llm: bool                         # stage 2 calls its real model (else stub)
    llm_provider: str                     # "openai" | "google_genai": chosen once, used by every LLM stage
    profile: Profile | None               # stage 2
    offers: list[Offer]                   # stage 3: all offers scraped so far
    quarantined: list[SecurityVerdict]    # stage 4: flagged offers
    ranked: list[RankedOffer]             # stage 5
    batch_cursor: int                     # stage 6: next index in `ranked`
    current_batch: list[RankedOffer]      # stage 6
    selected_offer_ids: list[str]         # stage 7: queue of offers to apply to
    next_action: str                      # stage 7: "next" | "find_others" | "done" (after queue)
    route: str                            # stage 7: where the graph goes next
    current_offer: Offer | None           # offer being processed in 8-10
    cover_letters: dict[str, str]         # stage 8: offer_id -> letter
    review_enabled: bool                  # stage 9 on/off
    review_decision: str                  # stage 9: "confirm" | "edit" | "cancel"
    applications: list[Application]       # stage 10
    applications_sent: int
    steps: int                            # global limit counters
    tokens_used: int
    stop_reason: str | None               # set when the run ends
    errors: Annotated[list[str], operator.add]


def initial_state(review_enabled: bool = True, resume_path: str = "",
                  location_preferences: list[str] | None = None,
                  use_llm: bool = False, llm_provider: str = "openai") -> WorkflowState:
    return WorkflowState(
        resume_path=resume_path, resume_text="",
        location_preferences=location_preferences or [], use_llm=use_llm,
        llm_provider=llm_provider, profile=None, offers=[], quarantined=[], ranked=[],
        batch_cursor=0, current_batch=[], selected_offer_ids=[], next_action="", route="",
        current_offer=None, cover_letters={}, review_enabled=review_enabled,
        review_decision="", applications=[], applications_sent=0, steps=0,
        tokens_used=0, stop_reason=None, errors=[],
    )
