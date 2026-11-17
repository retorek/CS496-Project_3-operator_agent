"""Small text helpers shared by the sources: location match, keyword match, French query."""
import re
import unicodedata

# Words the user may type -> how they appear in offer locations (country codes, "remote").
ALIASES = {"tunisia": "tn", "tunisie": "tn", "france": "fr", "germany": "de",
           "allemagne": "de", "teletravail": "remote", "remote": "remote"}


def normalize(text: str) -> str:
    """Lowercase, no accents."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9+#]+", normalize(text)) if w]


def matches_location(offer_location: str, wanted: str) -> bool:
    """True if the offer is in the wanted place. Empty `wanted` matches everything."""
    wanted = normalize(wanted)
    if not wanted:
        return True
    text = normalize(offer_location)
    return wanted in text or ALIASES.get(wanted, "") in words(offer_location)


def matches_keywords(text: str, query: str) -> bool:
    """True if at least half of the query's words appear in `text`."""
    wanted, have = set(words(query)), set(words(text))
    return bool(wanted) and len(wanted & have) * 2 >= len(wanted)


def same_offer_key(offer) -> str:
    """Offers with the same title words and location are treated as one offer. The company
    is left out: aggregators relist one job under different board names."""
    return " ".join(words(offer.title)) + "|" + " ".join(words(offer.location))


def shorter_query(query: str) -> str:
    """Fallback when a long query finds nothing: first word, plus 'stage' if it was there.
    'Backend Software Engineer stage' -> 'Backend stage'."""
    first = query.split()[0] if query.split() else ""
    return f"{first} stage" if "stage" in words(query) and first.lower() != "stage" else first


def french_query(query: str) -> str:
    """French job sites list internships as 'stage': 'Data Analyst Intern' -> 'Data Analyst stage'."""
    return re.sub(r"\b(intern|internship|interns)\b", "stage", query, flags=re.I)
