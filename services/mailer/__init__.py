"""Send the application + cover letter to the TEST inbox (Agent 6, sending half).

The message always goes to `settings.test_inbox`, never to the employer. Header
fields reject line breaks (offer text is untrusted third-party data). `dry_run`
builds the message without opening an SMTP connection, so demos and tests never
send anything; real delivery (to the test inbox) needs dry_run=False and a server.
"""
import smtplib
from email.message import EmailMessage

from core import log
from core.models import Offer, Profile


class MailerError(Exception):
    """The application could not be composed or sent (readable message)."""


def _header(value, name: str) -> str:
    value = str(value or "").strip()
    if "\r" in value or "\n" in value:
        raise MailerError(f"{name} must not contain line breaks.")
    return value


def build_message(profile: Profile | None, offer: Offer, letter: str, settings) -> EmailMessage:
    """Build the exact email: to the test inbox, subject and body from the facts."""
    if not letter or len(letter.strip()) < 20:
        raise MailerError("The cover letter is empty or too short.")
    name = _header(getattr(profile, "name", "") if profile else "", "name")
    title = _header(offer.title, "title")
    company = _header(offer.company, "company")
    to = _header(settings.test_inbox, "test_inbox")
    sender = _header(settings.smtp_user or "operator-agent@localhost", "sender")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = _header(f"Application - {title} - {name}", "subject")[:200]
    body = (f"Candidate: {name}\n"
            f"Offer: {title} at {company} (id {offer.id})\n"
            f"Note: test delivery to {to}; the employer is never contacted.\n\n"
            f"{letter.strip()}\n")
    msg.set_content(body)
    return msg


def send_application(profile: Profile | None, offer: Offer, letter: str, dry_run: bool = True,
                     settings=None, smtp=None) -> dict:
    """Compose and (unless dry_run) send the application. Returns a record dict.

    `smtp` lets tests inject a fake transport with send_message(msg).
    """
    if settings is None:
        from core.config import get_settings
        settings = get_settings(dry=True)
    msg = build_message(profile, offer, letter, settings)
    record = {"to": msg["To"], "subject": msg["Subject"], "offer_id": offer.id,
              "dry_run": bool(dry_run), "sent": False}
    if dry_run:
        log.system(f"email prepared for {msg['To']} (test mode: not sent)")
        return record
    try:
        if smtp is not None:
            smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port,
                              timeout=settings.llm_timeout) as server:
                server.ehlo()
                if server.has_extn("starttls"):  # Gmail (port 587) requires encryption
                    server.starttls()
                    server.ehlo()
                if settings.smtp_user and settings.smtp_password:
                    server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        log.system(f"email to {msg['To']} failed ({type(exc).__name__})")
        raise MailerError(f"SMTP send failed: {exc}") from exc
    log.system(f"email sent to {msg['To']} through {settings.smtp_host}")
    record["sent"] = True
    return record
