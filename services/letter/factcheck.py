"""Fact-check a cover letter against the profile (Agent 5, checking half).

Two checks, both must pass:
1. An LLM splits the letter into claims and judges each against the profile JSON
   (catches invented employers, certifications, tools, ...). Fails closed: an
   unreadable checker reply means the letter did not pass.
2. A deterministic number check: every number in the letter must appear in the
   profile or the offer (catches "team of 10", "50,000 users", ...). The LLM
   cannot override this check.
"""
import re
from dataclasses import asdict, dataclass, field

from pydantic import BaseModel

from core.models import Offer, Profile

CHECKER_SYSTEM = """You are a strict fact checker for a cover letter.
Split the letter into individual factual claims about the candidate: education,
experience, projects, skills, tools, numbers, certifications, languages,
achievements. Ignore greetings, motivation, opinions and statements about the
company. For each claim decide whether the candidate profile JSON supports it
(states it or directly implies it). Anything else is unsupported."""


class _Claim(BaseModel):
    claim: str
    supported: bool = False
    evidence: str = ""


class _ClaimList(BaseModel):
    claims: list[_Claim]


@dataclass
class FactCheckReport:
    claims: list = field(default_factory=list)       # [{claim, supported, evidence}]
    unsupported: list = field(default_factory=list)   # claim texts / number problems
    passed: bool = False
    error: str = ""

    def to_dict(self):
        return asdict(self)


_DATE = re.compile(r"\b(\d{4})-\d{2}(?:-\d{2})?\b")      # 2026-07 -> 2026
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def _numbers(text: str) -> set:
    text = _DATE.sub(r"\1", text)
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def number_check(letter: str, profile: Profile, offer: Offer | None = None) -> list[str]:
    """One message per sentence with a number found in neither profile nor offer."""
    allowed = _numbers(profile.model_dump_json())
    if offer is not None:
        allowed |= _numbers(offer.model_dump_json())
    problems = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", letter):
        bad = sorted(_numbers(sentence) - allowed)
        if bad:
            problems.append(f"Number(s) {', '.join(bad)} not in the profile: {sentence.strip()}")
    return problems


def route_after_check(passed: bool, attempts: int, max_retries: int) -> str:
    """accept -> go to submission; retry -> rewrite; reject -> stop, never submit."""
    if passed:
        return "accept"
    if attempts <= max_retries:     # attempts counts drafts written so far
        return "retry"
    return "reject"


def number_only_report(letter: str, profile: Profile, offer: Offer | None = None) -> FactCheckReport:
    """Dry-mode report: no LLM, deterministic number check only."""
    problems = number_check(letter, profile, offer)
    return FactCheckReport(claims=[], unsupported=problems, passed=not problems, error="")


def fact_check(letter: str, profile: Profile, offer: Offer | None = None,
               provider: str | None = None, checker=None) -> tuple[FactCheckReport, int]:
    """LLM claim check + deterministic number check. Returns (report, tokens).

    `checker` lets tests inject a fake returning {raw, parsed, parsing_error}; in
    production it is the 'cover_letter' model with structured output.
    """
    if checker is None:
        from core.config import get_settings
        from core.llm import get_chat_model
        settings = get_settings(dry=True)
        checker = get_chat_model("cover_letter", settings, provider or settings.llm_provider
                                 ).with_structured_output(_ClaimList, include_raw=True)
    out = checker.invoke([
        ("system", CHECKER_SYSTEM),
        ("human", "Candidate profile:\n" + profile.model_dump_json(indent=2)
         + "\n\nCover letter:\n<letter>\n" + letter + "\n</letter>"),
    ])

    raw = out.get("raw") if isinstance(out, dict) else None
    tokens = int((getattr(raw, "usage_metadata", None) or {}).get("total_tokens", 0) or 0)
    claims, error = [], ""
    try:
        if not isinstance(out, dict):
            raise ValueError("checker did not return a structured result")
        if out.get("parsing_error") is not None:
            raise ValueError(str(out["parsing_error"]))
        parsed = out.get("parsed")
        if parsed is None:
            raise ValueError("no structured output")
        items = parsed.claims if isinstance(parsed, _ClaimList) else _ClaimList.model_validate(parsed).claims
        if not items:
            raise ValueError("no claims extracted")
        claims = [{"claim": c.claim, "supported": c.supported is True, "evidence": c.evidence}
                  for c in items]
    except Exception as exc:
        error = f"Fact checker reply unusable: {exc}"

    unsupported = [c["claim"] for c in claims if not c["supported"]]
    for problem in number_check(letter, profile, offer):
        if problem not in unsupported:
            unsupported.append(problem)
    passed = not error and not unsupported
    return FactCheckReport(claims, unsupported, passed, error), tokens
