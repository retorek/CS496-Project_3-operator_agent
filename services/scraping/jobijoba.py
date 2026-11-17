"""Jobijoba (France): search page -> offer links -> JobPosting on each offer page."""
from urllib.parse import quote_plus

from scrapling.parser import Selector

from core.models import Offer
from services.scraping.fetch import fetch_html
from services.scraping.filters import french_query, normalize
from services.scraping.jsonld import read_offer_pages

BASE = "https://www.jobijoba.com"
SOURCE = "jobijoba"


def search_url(query: str, location: str, page: int) -> str:
    """e.g. /fr/emploi/Data+Analyst+stage/Lyon?page=2 (robots.txt allows this form)."""
    where = "" if normalize(location) in ("", "remote") else quote_plus(location)
    url = f"{BASE}/fr/emploi/{quote_plus(french_query(query))}"
    url += f"/{where}" if where else ""
    return url + (f"?page={page}" if page > 1 else "")


def offer_links(html: str) -> list[str]:
    links = Selector(html, url=BASE).css('a[href*="/fr/annonce/"]::attr(href)').getall()
    return [link if link.startswith("http") else BASE + link for link in links]


def search(query: str, location: str, page: int, max_offers: int, seen: set[str]) -> list[Offer]:
    links = offer_links(fetch_html(search_url(query, location, page)))
    return read_offer_pages(links, SOURCE, location, max_offers, seen)
