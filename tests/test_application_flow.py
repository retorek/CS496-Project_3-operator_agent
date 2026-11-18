"""Agents 5 + 6 through the compiled graph in dry mode (no model, no SMTP)."""
from core.config import Settings
from core.models import OfferStatus
from graph.run import ScriptedUser, run_graph


def settings(**kw):
    base = dict(openai_api_key=None, batch_size=3, max_applications=3, max_steps=50,
                max_tokens=200_000)
    return Settings(_env_file=None, **{**base, **kw})


def apply_first_offer():
    """Apply to the first shown offer, then finish (review on, confirmed)."""
    return ScriptedUser(user_decides=[{"select": [0], "action": "done"}], review=["confirm"])


def test_dry_run_writes_checks_and_records_a_dry_application():
    state = run_graph(settings(), apply_first_offer())
    assert state["applications_sent"] == 1
    app = state["applications"][0]
    assert app.status == OfferStatus.applied and app.offer_id

    # The letter is written from profile facts and passed the fact check.
    report = state["cover_letter_reports"][app.offer_id]
    assert report["passed"] is True
    letter = state["cover_letters"][app.offer_id]
    assert state["profile"].name in letter


def test_review_cancel_writes_a_letter_but_applies_nothing():
    user = ScriptedUser(user_decides=[{"select": [0], "action": "done"}], review=["cancel"])
    state = run_graph(settings(), user)
    assert state["applications_sent"] == 0
    assert state["cover_letters"]  # a letter was still drafted at stage 8
