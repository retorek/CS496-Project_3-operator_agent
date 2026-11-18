"""Agent 6: mail to the test inbox, fact-check gate, duplicates, dry run (no server)."""
import pytest

from core.config import Settings
from core.models import Application, Offer, OfferStatus, Profile
from graph.nodes import S10_apply
from services.mailer import MailerError, build_message, send_application
from services.tracker import already_applied, make_entry

PROFILE = Profile(name="Alice Martin", email="alice@example.com", skills=["Python"])
OFFER = Offer(source="samplejobs", url="https://jobs.example.com/1",
              title="Data Science Intern", company="Nimbus AI", location="Lyon, FR")
LETTER = "Dear Nimbus AI Hiring Team, I would be glad to apply. Best regards, Alice Martin"


def settings(**kw):
    base = dict(_env_file=None, test_inbox="test-inbox@example.com", smtp_user=None,
                smtp_host="localhost", smtp_port=1025)
    return Settings(**{**base, **kw})


class FakeSMTP:
    def __init__(self):
        self.messages = []

    def send_message(self, msg):
        self.messages.append(msg)


# --- mailer ---

def test_build_message_targets_the_test_inbox():
    msg = build_message(PROFILE, OFFER, LETTER, settings())
    assert msg["To"] == "test-inbox@example.com"
    assert msg["Subject"] == "Application - Data Science Intern - Alice Martin"
    assert LETTER in msg.get_content() and "Nimbus AI" in msg.get_content()


def test_header_injection_from_offer_is_rejected():
    evil = Offer(source="s", url="https://x/1", title="Intern\nBcc: all@evil.example", company="c")
    with pytest.raises(MailerError, match="line breaks"):
        build_message(PROFILE, evil, LETTER, settings())


def test_short_letter_is_rejected():
    with pytest.raises(MailerError):
        build_message(PROFILE, OFFER, "too short", settings())


def test_dry_run_builds_but_does_not_send():
    record = send_application(PROFILE, OFFER, LETTER, dry_run=True, settings=settings())
    assert record["sent"] is False and record["to"] == "test-inbox@example.com"


def test_real_send_uses_the_transport_and_reports_failure():
    smtp = FakeSMTP()
    record = send_application(PROFILE, OFFER, LETTER, dry_run=False, settings=settings(), smtp=smtp)
    assert record["sent"] is True and len(smtp.messages) == 1

    class Broken:
        def send_message(self, msg):
            raise OSError("connection refused")
    with pytest.raises(MailerError, match="SMTP send failed"):
        send_application(PROFILE, OFFER, LETTER, dry_run=False, settings=settings(), smtp=Broken())


# --- tracker ---

def test_already_applied_only_counts_successful_applications():
    applied = Application(offer_id="a", cover_letter="x", status=OfferStatus.applied)
    failed = Application(offer_id="b", cover_letter="x", status=OfferStatus.failed)
    assert already_applied("a", [applied, failed]) is True
    assert already_applied("b", [applied, failed]) is False
    assert make_entry("a", OfferStatus.applied).status == OfferStatus.applied


# --- stage 10 node ---

def base_state(report, **kw):
    state = {"current_offer": OFFER, "profile": PROFILE,
             "cover_letters": {OFFER.id: LETTER},
             "cover_letter_reports": {OFFER.id: report},
             "applications": [], "applications_sent": 0, "send_dry_run": True}
    state.update(kw)
    return state


def test_passing_letter_is_applied_and_counted():
    out = S10_apply.node(base_state({"passed": True}))
    assert out["applications_sent"] == 1
    assert out["applications"][0].status == OfferStatus.applied
    assert out["current_offer"] is None


@pytest.mark.parametrize("report", [{"passed": False}, None])
def test_failed_or_missing_fact_check_is_never_sent(report):
    out = S10_apply.node(base_state(report))
    assert out["applications_sent"] == 0
    assert out["applications"][0].status == OfferStatus.failed
    assert out["errors"]


def test_duplicate_offer_is_blocked():
    applied = Application(offer_id=OFFER.id, cover_letter=LETTER, status=OfferStatus.applied)
    out = S10_apply.node(base_state({"passed": True}, applications=[applied], applications_sent=1))
    assert out["applications_sent"] == 1 and len(out["applications"]) == 1


def test_every_return_reports_applications_sent():
    for report in ({"passed": True}, {"passed": False}, None):
        assert "applications_sent" in S10_apply.node(base_state(report))
