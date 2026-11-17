"""Arbeitnow (Europe, remote): free public JSON API, 300 newest jobs per page, no search
parameter, so keywords and location are filtered here."""
from core.models import Offer, make_offer_id
from services.scraping.fetch import fetch_json
from services.scraping.filters import matches_keywords, matches_location
from services.scraping.jsonld import html_to_text

API = "https://www.arbeitnow.com/api/job-board-api"
SOURCE = "arbeitnow"


def to_offer(job: dict) -> Offer:
    location = job.get("location") or ""
    if job.get("remote"):
        location = f"{location}, Remote" if location else "Remote"
    return Offer(source=SOURCE, url=job["url"], title=job.get("title", ""),
                 company=job.get("company_name", ""), location=location,
                 description=html_to_text(job.get("description", "")))


def search(query: str, location: str, page: int, max_offers: int, seen: set[str]) -> list[Offer]:
    jobs = fetch_json(f"{API}?page={page}").get("data", [])
    offers = []
    for job in jobs:
        searchable = " ".join([job.get("title", ""), *job.get("tags", []), *job.get("job_types", [])])
        if make_offer_id(SOURCE, job.get("url", "")) in seen or not matches_keywords(searchable, query):
            continue
        offer = to_offer(job)
        if matches_location(offer.location, location):
            offers.append(offer)
        if len(offers) >= max_offers:
            break
    return offers
