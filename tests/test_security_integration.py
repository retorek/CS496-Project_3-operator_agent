from core.config import Settings
from core.models import SecurityVerdict
from core.samples import load_offers
from graph.graph import _guarded
from graph.nodes import S4_security, S5_rank
from graph.run import default_dry_script, run_graph
import pytest


def settings():
    return Settings(_env_file=None)


def test_security_to_ranking_preserves_history_and_blocks_errors(monkeypatch):
    offers = load_offers()[:3]

    def classify(offer, **kwargs):
        assert kwargs["dry_run"] is False
        assert kwargs["provider"] == "google_genai"
        if offer.id == offers[2].id:
            raise RuntimeError("Classifier unavailable")
        return SecurityVerdict(offer_id=offer.id, safe=offer.id == offers[0].id,
                               reasons=[] if offer.id == offers[0].id else ["Suspicious offer"])

    monkeypatch.setattr(S4_security, "analyze_offer", classify)
    state = {"offers": offers, "llm_provider": "google_genai", "rank_dry_run": True}
    state.update(S4_security.node(state))
    result = _guarded("rank", S5_rank.node, settings())(state)
    assert state["offers"] == offers
    assert state["safe_offers"] == [offers[0]]
    assert [r.offer.id for r in result["ranked"]] == [offers[0].id]
    assert {v.offer_id for v in state["quarantined"]} == {offers[1].id, offers[2].id}
    assert all(not v.safe and v.reasons for v in state["quarantined"])


def test_ranking_without_approval_gets_no_offers():
    result = _guarded("rank", S5_rank.node, settings())({"offers": load_offers()})
    assert result["ranked"] == []


def test_dry_graph_needs_no_classifier(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Dry mode must not construct an LLM")

    monkeypatch.setattr("core.llm.get_chat_model", forbidden)
    state = run_graph(settings(), default_dry_script())
    assert state["stop_reason"] == "user_done"
    assert len(state["offers"]) == 10
    assert len(state["safe_offers"]) == 8
    assert len(state["quarantined"]) == 2
    assert {r.offer.id for r in state["ranked"]} == {o.id for o in state["safe_offers"]}


def test_security_adds_usage_to_session_counter(monkeypatch):
    def classify(offer, *, on_tokens, **kwargs):
        on_tokens(7)
        return SecurityVerdict(offer_id=offer.id, safe=True)

    monkeypatch.setattr(S4_security, "analyze_offer", classify)
    state = {"offers": load_offers()[:2], "tokens_used": 30}
    assert S4_security.node(state)["tokens_used"] == 44
    assert state["tokens_used"] == 30
    guarded = _guarded("security", S4_security.node, Settings(_env_file=None, max_tokens=35))
    assert guarded(state)["stop_reason"] == "token_budget"


@pytest.mark.parametrize("selection", ["approved", "quarantined", "unknown", "unchecked"])
@pytest.mark.parametrize("queued", [True, False])
def test_s7_only_processes_approved_ids(selection, queued, monkeypatch):
    from graph.nodes import S7_user_decides

    approved, blocked, unchecked = load_offers()[:3]
    selected = {"approved": approved.id, "quarantined": blocked.id,
                "unknown": "unknown", "unchecked": unchecked.id}[selection]
    state = {"offers": [approved, blocked, unchecked], "safe_offers": [approved, blocked],
             "quarantined": [SecurityVerdict(offer_id=blocked.id, safe=False, reasons=["blocked"])],
             "selected_offer_ids": [selected] if queued else [],
             "next_action": "done" if queued else ""}
    monkeypatch.setattr(S7_user_decides, "interrupt", lambda payload: {
        "selected": [selected], "action": "done"})
    result = S7_user_decides.node(state)
    if selection == "approved":
        assert result["current_offer"] == approved
        assert result["route"] == "apply"
    else:
        assert result["current_offer"] is None
        assert result["route"] == "done"
        assert result["selected_offer_ids"] == []


@pytest.mark.parametrize("action", ["done", "apply"])
def test_invalid_selections_cannot_reach_application_processing(monkeypatch, action):
    from graph.nodes import S8_cover_letter

    def forbidden(state):
        pytest.fail("Invalid selections must not reach cover-letter processing")

    monkeypatch.setattr(S8_cover_letter, "node", forbidden)
    user = default_dry_script()
    monkeypatch.setattr(user, "answer", lambda payload: {
        "selected": [load_offers()[-1].id, "unknown"], "action": action})
    state = run_graph(settings(), user)
    assert state["applications_sent"] == 0
    assert state["current_offer"] is None
    assert state["stop_reason"] == "user_done"
