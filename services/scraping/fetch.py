"""Polite HTTP fetching for the scrapers: allowed hosts only, delay per host, timeout, size cap."""
import time
from urllib.parse import urlparse

import requests

from core.config import get_settings

# Only these hosts can be fetched. A link inside a page cannot send the scraper anywhere else.
ALLOWED_HOSTS = {"www.jobijoba.com", "www.keejob.com", "www.arbeitnow.com"}
USER_AGENT = "Mozilla/5.0 (compatible; InternshipAssistant/0.1; student project)"
MAX_BYTES = 5_000_000

_last_request: dict[str, float] = {}  # host -> time of the last request


class ScrapeError(RuntimeError):
    """A page could not be fetched or read."""


class PageNotFound(ScrapeError):
    """HTTP 404, e.g. asking for a results page after the last one."""


def _check_host(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ScrapeError(f"host not allowed: {host or url}")
    return host


def _wait_turn(host: str, delay: float) -> None:
    """Sleep so that two requests to the same host are at least `delay` seconds apart."""
    wait = _last_request.get(host, 0.0) + delay - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_request[host] = time.monotonic()


def _get(url: str) -> requests.Response:
    settings = get_settings(dry=True)
    _wait_turn(_check_host(url), settings.scrape_delay)
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT},
                            timeout=settings.scrape_timeout)
    except requests.RequestException as e:
        raise ScrapeError(f"{type(e).__name__} on {url}") from e
    _check_host(resp.url)  # after redirects
    if resp.status_code == 404:
        raise PageNotFound(f"HTTP 404 on {url}")
    if resp.status_code != 200:
        raise ScrapeError(f"HTTP {resp.status_code} on {url}")
    if len(resp.content) > MAX_BYTES:
        raise ScrapeError(f"page too large: {url}")
    return resp


def fetch_html(url: str) -> str:
    return _get(url).content.decode("utf-8", errors="replace")


def fetch_json(url: str) -> dict:
    try:
        return _get(url).json()
    except ValueError as e:
        raise ScrapeError(f"not JSON: {url}") from e
