"""Job offer sources. Stage 3 only uses `search()` and `SOURCES` from here.

Every source has the same function:
    search(query, location, page, max_offers, seen_ids) -> list[Offer]
Offer text is untrusted data: it is extracted, never followed or executed.
"""
from core.models import Offer
from services.scraping import arbeitnow, jobijoba, keejob
from services.scraping.fetch import ScrapeError

# name -> (module, what it covers). The description is shown to the stage 3 agent.
SOURCES = {
    "jobijoba": (jobijoba, "France: jobs and internships from many French job boards"),
    "keejob": (keejob, "Tunisia: jobs and internships"),
    "arbeitnow": (arbeitnow, "Europe (mostly Germany) and remote jobs, English titles"),
}

__all__ = ["SOURCES", "ScrapeError", "search"]


def search(source: str, query: str, location: str, page: int = 1, max_offers: int = 5,
           seen: set[str] | None = None) -> list[Offer]:
    """New offers from one source. Raises ScrapeError if the search page cannot be read."""
    if source not in SOURCES:
        raise ScrapeError(f"unknown source: {source}")
    module = SOURCES[source][0]
    return module.search(query, location, page, max_offers, seen or set())
