"""Agent 5: cover letter writing + fact checking.

`write_verified_letter` runs the write -> check -> retry loop and returns a letter
plus a FactCheckReport. A letter that never passes is returned with passed=False,
so Agent 6 (stage 10) refuses to send it.
"""
from core.models import Offer, Profile

from .factcheck import (FactCheckReport, fact_check, number_check, number_only_report,
                        route_after_check)
from .writer import fence_offer, stub_letter, write_letter

MAX_RETRIES = 2

__all__ = ["FactCheckReport", "fact_check", "number_check", "number_only_report",
           "route_after_check", "fence_offer", "stub_letter", "write_letter",
           "write_verified_letter", "MAX_RETRIES"]


def write_verified_letter(profile: Profile, offer: Offer, use_llm: bool = False,
                          provider: str | None = None, max_retries: int = MAX_RETRIES,
                          model=None, checker=None) -> tuple[str, FactCheckReport, int]:
    """Write a letter and fact-check it. Returns (letter, report, tokens).

    Dry mode (use_llm=False): one deterministic draft, number check only, no model.
    LLM mode: write -> check -> rewrite with the unsupported claims, up to max_retries.
    """
    if type(max_retries) is not int or max_retries < 0:
        raise ValueError("max_retries must be a non-negative integer")
    if not use_llm:
        letter = stub_letter(profile, offer)
        return letter, number_only_report(letter, profile, offer), 100

    feedback, tokens, attempts = None, 0, 0
    while True:
        letter, used = write_letter(profile, offer, provider, feedback, model=model)
        tokens, attempts = tokens + used, attempts + 1
        report, used = fact_check(letter, profile, offer, provider, checker=checker)
        tokens += used
        if route_after_check(report.passed, attempts, max_retries) != "retry":
            return letter, report, tokens
        feedback = report.unsupported or [report.error]
