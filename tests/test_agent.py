import json

from agent.agent import Config, run_agent
from agent.llm import ScriptedLLM
from agent.tools import MockTools

LETTER = "Dear team, I am very interested in this internship and match the requirements."


def act(name, **args):
    return json.dumps({"action": name, "args": args})


def run(replies, approve=lambda action, args: True, repeat_last=False, tokens=100, **cfg):
    tools = MockTools()
    llm = ScriptedLLM(replies, tokens_per_call=tokens, repeat_last=repeat_last)
    return run_agent("test", "cv", llm, tools, approve, Config(**cfg)), tools


# ---- stop rule ----
def test_infinite_loop_stops_at_max_steps():
    res, _ = run([act("search_jobs", query="python")], repeat_last=True, max_steps=5)
    assert res.stop_reason == "max_steps" and len(res.steps) == 5


def test_max_applications_cap():
    replies = [act("submit_application", offer_id=f"o{i}", letter=LETTER) for i in (1, 2, 3, 5)]
    res, tools = run(replies, max_applications=2)
    assert res.stop_reason == "max_applications" and len(tools.submitted) == 2


def test_token_budget():
    res, _ = run([act("search_jobs", query="python")], repeat_last=True,
                 tokens=600, max_tokens=1000, max_steps=50)
    assert res.stop_reason == "budget" and res.tokens <= 1200


# ---- checkpoint ----
def test_declined_application_is_not_sent():
    res, tools = run([act("submit_application", offer_id="o1", letter=LETTER)],
                     approve=lambda action, args: False)
    assert tools.submitted == {}


def test_bad_args_never_reach_the_human():
    asked = []
    res, tools = run([act("submit_application", offer_id="o1", letter="short")],
                     approve=lambda action, args: asked.append((action, args)) or True)
    assert asked == [] and tools.submitted == {}


# ---- tools ----
def test_tracker_is_idempotent():
    t = MockTools()
    a = dict(offer_id="o1", status="interested", match_score=80)
    t.call("update_tracker", a)
    t.call("update_tracker", a)
    assert len(t.tracker) == 1


def test_errors_are_readable_not_stack_traces():
    res, _ = run([act("read_offer", offer_id="zzz"), act("finish", answer="x")])
    assert "ERROR: Offer 'zzz' not found" in res.steps[0]["output"]
    assert "Traceback" not in res.steps[0]["output"]


def test_invalid_json_is_survived():
    res, _ = run(["not json at all", act("finish", answer="ok")])
    assert res.stop_reason == "done" and res.steps[0]["tool"] == "<invalid_reply>"


# ---- injection (structural defense) ----
def test_obedient_model_hit_by_injection_is_still_capped_and_gated():
    """Worst case: the model obeys the trapped offer and tries to apply to everything."""
    replies = [act("read_offer", offer_id="o4")] + \
              [act("submit_application", offer_id=f"o{i}", letter=LETTER) for i in (1, 2, 3, 5, 4)]
    approvals = []
    res, tools = run(replies, approve=lambda action, args: approvals.append((action, args)) or False,
                     max_applications=2)
    assert tools.submitted == {}                       # human said no -> nothing sent
    assert "<untrusted_offer>" in res.steps[0]["output"]  # offer was fenced as data
    # and with approval, the cap still holds:
    res, tools = run(replies, max_applications=2)
    assert len(tools.submitted) == 2
