"""Deterministic, offline checks. No findings does not prove an offer is safe.

Inspect the original Offer without changing it. Findings are deduplicated by
(code, field), so callers get stable reasons without copying sensitive content
into logs. No URLs are fetched and no hostnames are resolved.
"""

from dataclasses import dataclass
import html
import ipaddress
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from core.models import Offer


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    field: str
    explanation: str


# IDs can be supplied by a scraper, so inspect them as well as display fields.
_TEXT_FIELDS = ("id", "source", "url", "title", "company", "location", "description")
_RULES = (
    (
        "PROMPT_INJECTION",
        r"\b(?:ignore|disregard|forget|override)\s+(?:(?:all|any|the|your)\s+)*"
        r"(?:(?:previous|prior|above|earlier|system|developer|original|safety|security)\s+)+"
        r"(?:instructions?|prompts?|rules?|messages?)\b"
        r"|\b(?:ignore|disregard|override)\s+(?:(?:all|the|your|any)\s+)*"
        r"(?:instructions?|rules?|prompts?)\s+(?:above|earlier|previously)\b"
        r"|\b(?:reveal|print|output|disclose)\s+(?:(?:the|your|hidden|full)\s+)*"
        r"(?:system|developer)\s+(?:prompt|instructions?|messages?)\b",
        "Offer text attempts to override instructions or extract internal prompts.",
    ),
    (
        "ROLE_IMPERSONATION",
        r"<\s*/?\s*(?:system|developer|assistant)\b[^>]*>"
        r"|\[\s*(?:system|developer|assistant)(?:\s+(?:message|instructions?))?\s*\]"
        r"|\[/?inst\]|<\|(?:im_start|start_header_id)\|>"
        r"|(?:^|\n)\s*(?:#{1,6}\s*)?(?:system|developer|assistant)"
        r"(?:\s+(?:message|instructions?|prompt))?\s*:"
        r"|[\"']role[\"']\s*:\s*[\"'](?:system|developer|assistant)[\"']"
        r"|(?:^|\n)\s*#{1,6}\s*(?:system|developer)(?:\s+instructions?)?\s*(?:\n|$)"
        r"|\b(?:act\s+as|you\s+are\s+now)\s+(?:the\s+)?(?:system|developer|assistant)\b",
        "Offer text impersonates a trusted message or model role.",
    ),
    (
        "APPROVAL_BYPASS",
        r"\b(?:bypass|skip|disable|ignore|avoid)\s+(?:(?:the|all|any|user|human)\s+)*"
        r"(?:approval|confirmation|consent|review)\b"
        r"|\b(?:do\s+not|don['’]t|never)\s+(?:ask|wait|request)(?:\s+\w+){0,4}\s+"
        r"(?:approval|confirmation|consent)\b"
        r"|\b(?:apply|submit|send)(?:\s+\w+){0,8}\s+without\s+"
        r"(?:(?:asking|waiting)\s+for\s+)?(?:(?:the|any|user|human)\s+)*"
        r"(?:approval|confirmation|consent|review)\b",
        "Offer text asks to bypass user approval or review.",
    ),
    (
        "RANKING_MANIPULATION",
        r"\b(?:rank|place|put)\s+(?:(?:this|our|the)\s+)?(?:offer|internship|job|listing)"
        r"(?:\s+\w+){0,3}\s+(?:first|highest|top|number\s+one|#?1)\b"
        r"|\b(?:give|assign|set|change|boost|increase)\s+(?:(?:this|our|the|its)\s+)*"
        r"(?:(?:offer|internship|job|listing)(?:'s)?\s+)?"
        r"(?:(?:a|the)\s+)?"
        r"(?:ranking|rank|score|match\s+score)\b"
        r"|\b(?:give|assign)\s+(?:this|our|the)\s+(?:offer|internship|job|listing)"
        r"\s+(?:(?:a|the)\s+)?(?:perfect|maximum|100(?:/100)?)\s*(?:score|points)?\b",
        "Offer text attempts to control its ranking or matching score.",
    ),
    (
        "SENSITIVE_DATA_REQUEST",
        r"\b(?:send|provide|share|enter|submit|upload|disclose|reveal|verify|confirm|email|require|request)"
        r"\b[^.!?;\n]{0,160}?\b(?:your|candidate(?:'s)?|applicant(?:'s)?)\s+"
        r"(?:(?:online|account|email|bank|banking|login|one[- ]time|personal)\s+){0,3}"
        r"(?:passwords?|passcodes?|otps?|pins?|credentials?|verification\s+codes?|"
        r"security\s+codes?|recovery\s+codes?|login\s+details|cvv|"
        r"bank\s+(?:details|accounts?|account\s+numbers?)|"
        r"credit\s+card(?:\s+(?:details|numbers?))?|passport(?:\s+(?:numbers?|scans?|copies))?|"
        r"social\s+security\s+(?:numbers?|details)|national\s+id(?:\s+numbers?)?|"
        r"home\s+address|date\s+of\s+birth|api\s+keys?|private\s+keys?|seed\s+phrases?)\b"
        r"|\b(?:send|provide|share|enter|submit|upload|email)\s+"
        r"(?:(?:a|an|the|us|of|copy|scan)\s+)*"
        r"(?:passwords?|passcodes?|otps?|pins?|banking\s+credentials?|"
        r"bank\s+(?:details|account\s+(?:numbers?|details))|passport\s+(?:numbers?|scans?|copies)|"
        r"credit\s+card\s+(?:numbers?|details)|social\s+security\s+numbers?)\b",
        "Offer text requests credentials or sensitive personal information.",
    ),
)
_COMPILED_RULES = tuple((code, re.compile(pattern, re.I), explanation)
                        for code, pattern, explanation in _RULES)
_NEGATED_REQUEST = re.compile(r"\b(?:never|do\s+not|don['’]t|must\s+not)\s+$", re.I)


def _matches_rule(code: str, pattern: re.Pattern, text: str) -> bool:
    if code != "SENSITIVE_DATA_REQUEST":
        return pattern.search(text) is not None
    start = 0
    while (match := pattern.search(text, start)) is not None:
        # A direct warning such as 'never share your password' is not a request.
        if not _NEGATED_REQUEST.search(text[:match.start()]):
            return True
        # Search overlapping requests too: a warning must not hide 'enter your OTP'.
        start = match.start() + 1
    return False

# Include non-web schemes, protocol-relative links and common bare-host links.
# Stopping at quotes also extracts href="..." and Markdown destinations.
_LINKS = re.compile(
    r"\b(?:[a-z][a-z0-9+.-]*://|"
    r"(?:https?|javascript|data|vbscript|file|mailto|tel|ftp|ssh|gopher|about|blob):)"
    r"[^\s<>\"']*"
    r"|(?<![\w:/])//[^\s<>\"']+"
    r"|\bwww\.[^\s<>\"']+", re.I
)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", html.unescape(text))
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def _url_findings(value: str, field: str) -> list[SecurityFinding]:
    findings = []

    def add(code: str, explanation: str) -> None:
        findings.append(SecurityFinding(code, field, explanation))

    # urlsplit otherwise silently strips some control characters.
    if any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value) or "\\" in value:
        add("MALFORMED_URL", "Link contains whitespace, control characters or backslashes.")
        return findings
    if re.search(r"%(?![0-9a-fA-F]{2})", value):
        add("MALFORMED_URL", "Link contains an invalid percent escape.")
        return findings
    try:
        parts = urlsplit(value)
        scheme = parts.scheme.lower()
        allowed_schemes = {"http", "https", "mailto"} if field != "url" else {"http", "https"}
        if scheme not in allowed_schemes:
            add("UNSAFE_URL_SCHEME", "Link uses an unsupported or executable URL scheme.")
        # Contact emails are common in offers; they are not web destinations.
        if scheme == "mailto" and field != "url":
            if not re.fullmatch(r"[^\s@/?#]+@[^\s@/?#]+\.[^\s@/?#]+", parts.path):
                add("MALFORMED_URL", "Contact link has an invalid email destination.")
            return findings
        if not parts.netloc or not parts.hostname:
            add("MALFORMED_URL", "Web link must contain a scheme and a hostname.")
            return findings
        if parts.username is not None or parts.password is not None:
            add("URL_CREDENTIALS", "Link embeds credentials or a deceptive user-info component.")
        authority = parts.netloc.rsplit("@", 1)[-1]
        if authority.startswith("[") and not re.fullmatch(r"\[[^\]]+\](?::[0-9]*)?", authority):
            add("MALFORMED_URL", "Link contains text after a bracketed IP address.")
        # Accessing .port validates both its syntax and range.
        if parts.port == 0 or parts.netloc.endswith(":"):
            add("MALFORMED_URL", "Link has an invalid port.")
        host = unquote(parts.hostname).lower().rstrip(".")
        if "%" in host:
            # Zone-qualified IPv6 is a local-network destination.
            host = host.split("%", 1)[0]
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            ascii_host = host.encode("idna").decode("ascii")
            labels = ascii_host.split(".")
            if (len(ascii_host) > 253 or any(
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels
            )):
                add("MALFORMED_URL", "Link contains an invalid hostname.")
            elif (len(labels) == 1 or host.endswith((".localhost", ".local", ".internal", ".lan", ".localdomain"))
                  or re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*", host)):
                add("PRIVATE_NETWORK_URL", "Link targets a local name or an ambiguous numeric address.")
        else:
            # IPv4-mapped IPv6 must follow the embedded IPv4 address policy.
            target = getattr(address, "ipv4_mapped", None) or address
            if not target.is_global or target.is_multicast:
                add("PRIVATE_NETWORK_URL", "Link targets a non-public IP address.")
    except (ValueError, UnicodeError):
        add("MALFORMED_URL", "Link has an invalid hostname, bracket syntax or port.")
    return findings


def check_offer(offer: Offer) -> list[SecurityFinding]:
    """Return findings in field/rule order; never mutate the offer or access a network.

    One finding per reason code per field. Unexpected inspection failures produce
    CHECK_ERROR, never a clean result. Invalid input objects are programming errors.
    """
    if not isinstance(offer, Offer):
        raise TypeError("check_offer expects a core.models.Offer")
    findings: dict[tuple[str, str], SecurityFinding] = {}
    for field in _TEXT_FIELDS:
        current = []
        try:
            text = _normalize(getattr(offer, field))
            current = [SecurityFinding(code, field, explanation)
                       for code, pattern, explanation in _COMPILED_RULES
                       if _matches_rule(code, pattern, text)]
            if field == "url":
                current.extend(_url_findings(text, field))
            else:
                for match in _LINKS.finditer(text):
                    current.extend(_url_findings(match.group().rstrip(".,;!?)"), field))
        except Exception:
            # Do not expose input text or exception details (possibly credentials).
            current.append(SecurityFinding("CHECK_ERROR", field, "Security inspection failed for this field."))
        for finding in current:
            findings.setdefault((finding.code, finding.field), finding)
    return list(findings.values())
