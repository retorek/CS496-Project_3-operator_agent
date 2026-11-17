"""Keejob (Tunisia): keyword search -> offer links -> JobPosting on each offer page.
Its city filter is set by JavaScript, so the location is checked on each offer instead."""
from urllib.parse import urlencode

from scrapling.parser import Selector

from core.models import Offer
from services.scraping.fetch import PageNotFound, fetch_html
from services.scraping.filters import french_query, shorter_query
from services.scraping.jsonld import read_offer_pages

BASE = "https://www.keejob.com"
SOURCE = "keejob"


def search_url(query: str, page: int) -> str:
    params = {"keywords": query} | ({"page": page} if page > 1 else {})
    return f"{BASE}/offres-emploi/?{urlencode(params)}"


def offer_links(html: str) -> list[str]:
    """Offer URLs without the tracking part (?source=search), so the offer id stays stable."""
    links = Selector(html, url=BASE).css('a[href^="/offres-emploi/"]::attr(href)').getall()
    return [BASE + link.split("?")[0] for link in links
            if link.split("/")[2].isdigit()]  # /offres-emploi/<number>/<slug>/


def result_links(query: str, page: int) -> list[str]:
    """Offer links on one results page. Keejob answers 404 after the last page: no results."""
    try:
        return offer_links(fetch_html(search_url(query, page)))
    except PageNotFound:
        return []


def search(query: str, location: str, page: int, max_offers: int, seen: set[str]) -> list[Offer]:
    query = french_query(query)
    links = result_links(query, page)
    if not links and shorter_query(query) != query:  # Keejob needs every word to match
        links = result_links(shorter_query(query), page)
    return read_offer_pages(links, SOURCE, location, max_offers, seen)
