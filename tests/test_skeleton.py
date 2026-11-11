import pytest
from pydantic import ValidationError

from core.config import ConfigError, Settings, get_model_spec, get_settings, load_model_config
from core.models import (Offer, OfferStatus, Profile, RankedOffer, SecurityVerdict,
                         make_offer_id)
from core.samples import load_offers
from graph import graph as graph_module
from graph.run import ScriptedUser, default_dry_script, run_graph
from langgraph.types import Command

STAGE_NAMES = set(graph_module.STAGES)


def settings(**kw):
    base = dict(openai_api_key=None, batch_size=3, max_applications=3, max_steps=50,
                max_tokens=200_000)
    return Settings(_env_file=None, **{**base, **kw})


# --- models ---
def test_offer_id_is_stable_and_computed():
    a = Offer(source="s", url="http://x/1", title="t", company="c")
    b = Offer(source="s", url="http://x/1", title="other", company="c")
    assert a.id == b.id == make_offer_id("s", "http://x/1")
    assert a.id != Offer(source="s", url="http://x/2", title="t", company="c").id


def test_models_validate():
    with pytest.raises(ValidationError):
        RankedOffer(offer=load_offers()[0], score=101)
    assert SecurityVerdict(offer_id="a", safe=True).reasons == []
    assert Profile(name="n", email="e").skills == []
    assert {s.value for s in OfferStatus} == {
        "shown", "applied", "declined", "dismissed", "failed", "quarantined"}


def test_samples_load():
    assert len(load_offers()) == 10


# --- config ---
def test_missing_key_is_error_unless_dry(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(Settings, "model_config", {**Settings.model_config, "env_file": None})
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        get_settings(dry=False)
    assert get_settings(dry=True).openai_api_key is None


def test_models_yaml_has_every_model_stage():
    cfg = load_model_config()
    assert set(cfg) == {"profile", "find_offers", "security", "rank", "cover_letter"}
    assert get_model_spec("rank").temperature == 0.0


# --- graph ---
def test_graph_reaches_every_stage_in_dry_mode(monkeypatch):
    visited = []
    for name, module in graph_module.STAGES.items():
        real = module.node
        monkeypatch.setattr(module, "node",
                            lambda s, real=real, name=name: (visited.append(name), real(s))[1])
    state = run_graph(settings(), default_dry_script())
    assert STAGE_NAMES <= set(visited)
    assert state["stop_reason"] == "user_done"
    assert state["applications_sent"] == 1
    assert len(state["quarantined"]) == 2  # the two trapped sample offers


def test_quarantined_offers_are_never_ranked():
    state = run_graph(settings(), default_dry_script())
    bad = {v.offer_id for v in state["quarantined"]}
    assert bad and not bad & {r.offer.id for r in state["ranked"]}


def test_application_cap_stops_the_run():
    user = ScriptedUser(user_decides=[{"select": [0, 1, 2], "action": "done"}])
    state = run_graph(settings(max_applications=2), user, review_enabled=False)
    assert state["applications_sent"] == 2
    assert state["stop_reason"] == "max_applications"


def test_forced_loop_stops_at_max_steps():
    user = ScriptedUser(user_decides=[{"select": [], "action": "find_others"}], repeat_last=True)
    state = run_graph(settings(max_steps=30), user)
    assert state["stop_reason"] == "max_steps"
    assert state["steps"] == 31


def test_token_budget_stops_the_run():
    user = ScriptedUser(user_decides=[{"select": [], "action": "find_others"}], repeat_last=True)
    state = run_graph(settings(max_tokens=250), user)
    assert state["stop_reason"] == "token_budget"


def test_review_cancel_returns_to_user_without_applying():
    user = ScriptedUser(user_decides=[{"select": [0], "action": "done"}], review=["cancel"])
    state = run_graph(settings(), user)
    assert state["applications_sent"] == 0
    assert state["stop_reason"] == "user_done"


def test_graph_pauses_at_user_decision():
    g = graph_module.build_graph(settings())
    cfg = {"configurable": {"thread_id": "t"}}
    from core.state import initial_state
    out = g.invoke(initial_state(), cfg)
    assert out["__interrupt__"][0].value["stage"] == "user_decides"
    assert Command  # resume path is exercised by run_graph tests
