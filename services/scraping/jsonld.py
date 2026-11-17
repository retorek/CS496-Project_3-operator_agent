"""Read schema.org JobPosting blocks (JSON-LD) from an offer page and turn them into Offers."""
import json

from scrapling.parser import Selector

from core.models import Offer, make_offer_id
from services.scraping.fetch import ScrapeError, fetch_html
from services.scraping.filters import matches_location, same_offer_key

MAX_DESCRIPTION = 5000  # characters kept from the description


def job_postings(html: str) -> list[dict]:
    """All JobPosting objects in the page's <script type="application/ld+json"> blocks."""
    found = []
    for raw in Selector(html).css('script[type="application/ld+json"]::text').getall():
        try:
            data = json.loads(raw)
        except ValueError:
            continue  # broken block: skip it
        items = data if isinstance(data, list) else data.get("@graph", [data])
        found += [i for i in items if isinstance(i, dict) and i.get("@type") == "JobPosting"]
    return found


def html_to_text(html: str) -> str:
    """Plain text of an HTML fragment, capped at MAX_DESCRIPTION characters."""
    return Selector(f"<div>{html}</div>").get_all_text(separator="\n", strip=True)[:MAX_DESCRIPTION]


def _location(posting: dict) -> str:
    """'City, Region, Country', plus 'Remote' if the posting says so."""
    places = posting.get("jobLocation") or []
    place = (places[0] if isinstance(places, list) and places else places) or {}
    address = (place.get("address") or {}) if isinstance(place, dict) else {}
    if isinstance(address, str):
        parts = [address]
    else:
        parts = [address.get(k) for k in ("addressLocality", "addressRegion", "addressCountry")]
    if posting.get("jobLocationType") == "TELECOMMUTE":
        parts.append("Remote")
    return ", ".join(p for p in parts if isinstance(p, str) and p)


def to_offer(posting: dict, source: str, url: str) -> Offer:
    org = posting.get("hiringOrganization") or {}
    return Offer(
        source=source, url=url,
        title=str(posting.get("title", "")).strip(),
        company=str(org.get("name", "") if isinstance(org, dict) else org).strip(),
        location=_location(posting),
        description=html_to_text(str(posting.get("description", ""))),
    )


def read_offer_pages(urls: list[str], source: str, location: str, max_offers: int,
                     seen: set[str]) -> list[Offer]:
    """Open offer pages one by one and keep the ones with a JobPosting in `location`.
    Skips offers already seen (no request) and repeats of the same offer under another URL
    (aggregators list one job several times). Reads at most 2 * max_offers pages."""
    offers: list[Offer] = []
    kept: set[str] = set()  # same_offer_key of kept offers
    new_urls = [u for u in dict.fromkeys(urls) if make_offer_id(source, u) not in seen]
    for url in new_urls[:2 * max_offers]:
        try:
            postings = job_postings(fetch_html(url))
        except ScrapeError:
            continue  # one broken page does not stop the search
        if not postings:
            continue
        offer = to_offer(postings[0], source, url)
        key = same_offer_key(offer)
        if offer.title and key not in kept and matches_location(offer.location, location):
            offers.append(offer)
            kept.add(key)
        if len(offers) >= max_offers:
            break
    return offers
