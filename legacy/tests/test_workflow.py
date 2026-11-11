"""Integration and limit tests using the real compiled graph, without a model server."""
import json

import pytest

from agent.agent import Config, RunResult, legacy_approval, run_agent
from agent.llm import OllamaLLM, ScriptedLLM
from agent.tools import MockTools
from run_demo import SCRIPT


def test_complete_script_preserves_result_tools_and_jsonl(tmp_path):
    tools, llm, approvals = MockTools(), ScriptedLLM(SCRIPT), []
    log = tmp_path / "logs" / "run.jsonl"

    def approve(action, args):
        approvals.append((action, args))
        return True

    result = run_agent("find internships", "Python CV", llm, tools, approve, log_path=log)
    assert isinstance(result, RunResult)
    assert result.answer == "Applied to o1."
    assert result.stop_reason == "done" and result.tokens == 500
    assert list(tools.tracker) == list(tools.submitted) == ["o1"]
    assert [name for name, _ in approvals] == ["update_tracker", "submit_application"]
    assert approvals[0][1] == json.loads(SCRIPT[2])["args"]
    assert approvals[1][1] == json.loads(SCRIPT[3])["args"]
    assert [step["step"] for step in result.steps] == [1, 2, 3, 4, 5]
    records = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    assert records == result.steps
    assert set(records[0]) == {"step", "ts", "tool", "input", "output", "tokens"}


@pytest.mark.parametrize(("setting", "reason"), [
    ("max_steps", "max_steps"), ("max_tokens", "budget"),
    ("max_applications", "max_applications"),
])
def test_zero_limits_stop_before_model_or_tools(setting, reason):
    llm, tools = ScriptedLLM(SCRIPT), MockTools()
    approvals = []
    result = run_agent("test", "cv", llm, tools,
                       lambda *request: approvals.append(request) or True,
                       Config(**{setting: 0}))
    assert result.stop_reason == reason and result.steps == []
    assert result.tokens == llm.i == 0
    assert approvals == [] and tools.tracker == tools.submitted == {}


@pytest.mark.parametrize("limit", ["steps", "tokens", "applications"])
def test_python_limits_still_hold_with_very_high_graph_recursion_limit(monkeypatch, limit):
    # Raising the framework ceiling cannot disable application policy.
    import agent.agent as agent_module

    original_build = agent_module._build_graph

    def build(*args):
        graph = original_build(*args)
        original_invoke = graph.invoke

        def invoke(state, config):
            return original_invoke(state, config={**config, "recursion_limit": 100000})

        graph.invoke = invoke
        return graph

    monkeypatch.setattr(agent_module, "_build_graph", build)
    if limit == "applications":
        replies = [json.dumps({"action": "submit_application", "args": {
            "offer_id": f"o{i}", "letter": "A sufficiently long application letter."}})
            for i in (1, 2, 3)]
        config = Config(max_applications=1, max_steps=100)
        calls, reason = 1, "max_applications"
    else:
        replies = [SCRIPT[0]]
        config = Config(max_steps=40, max_tokens=100000) if limit == "steps" else Config(
            max_steps=100, max_tokens=200)
        calls, reason = (40, "max_steps") if limit == "steps" else (2, "budget")
    llm, tools = ScriptedLLM(replies, repeat_last=True), MockTools()
    result = run_agent("test", "cv", llm, tools, lambda action, args: True, config)
    assert result.stop_reason == reason
    assert llm.i == calls and result.tokens == calls * 100
    assert len(tools.submitted) == (1 if limit == "applications" else 0)


def test_one_completion_can_overshoot_budget_but_no_next_call_occurs():
    llm = ScriptedLLM([SCRIPT[0]], tokens_per_call=600, repeat_last=True)
    result = run_agent("test", "cv", llm, MockTools(), lambda *args: True,
                       Config(max_tokens=1000, max_steps=50))
    assert result.stop_reason == "budget" and result.tokens == 1200
    assert llm.i == len(result.steps) == 2


def test_failed_and_duplicate_submissions_do_not_consume_application_slots():
    def submit(offer):
        return json.dumps({"action": "submit_application", "args": {
            "offer_id": offer, "letter": "A sufficiently long application letter."}})

    tools = MockTools()
    result = run_agent("test", "cv", ScriptedLLM([
        submit("missing"), submit("o1"), submit("o1"), submit("o2"), submit("o3")]),
        tools, lambda *args: True, Config(max_applications=2))
    assert result.stop_reason == "max_applications"
    assert list(tools.submitted) == ["o1", "o2"]
    assert "not found" in result.steps[0]["output"]
    assert "Already applied" in result.steps[2]["output"]


def test_legacy_submission_callback_is_adapted_and_tracker_denied_by_default():
    approvals, tools = [], MockTools()
    approve = legacy_approval(lambda offer, letter: approvals.append((offer, letter)) or True)
    result = run_agent("test", "cv", ScriptedLLM(SCRIPT), tools, approve)
    assert result.stop_reason == "done"
    assert tools.tracker == {} and list(tools.submitted) == ["o1"]
    assert approvals == [("o1", json.loads(SCRIPT[3])["args"]["letter"])]


def test_legacy_adapter_can_use_a_separate_tracker_checkpoint():
    requests, tools = [], MockTools()
    approve = legacy_approval(lambda offer, letter: True,
                              lambda action, args: requests.append((action, args)) or True)
    run_agent("test", "cv", ScriptedLLM(SCRIPT), tools, approve)
    assert requests == [("update_tracker", json.loads(SCRIPT[2])["args"])]
    assert list(tools.tracker) == list(tools.submitted) == ["o1"]


def test_runs_do_not_share_steps_or_authorization():
    tools = MockTools()
    first = run_agent("test", "cv", ScriptedLLM([SCRIPT[2]]), tools, lambda *args: True)
    second = run_agent("test", "cv", ScriptedLLM([SCRIPT[3]]), tools, lambda *args: False)
    assert first.stop_reason == second.stop_reason == "done"
    assert tools.submitted == {} and len(first.steps) == len(second.steps) == 2
    assert "declined" in second.steps[0]["output"]


def test_ollama_interface_works_with_graph_without_a_live_server(monkeypatch):
    requests = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": '{"action":"finish","answer":"ok"}'},
                    "prompt_eval_count": 11, "eval_count": 7}

    def post(url, **kwargs):
        requests.append((url, kwargs))
        return Response()

    monkeypatch.setattr("agent.llm.requests.post", post)
    result = run_agent("test", "cv", OllamaLLM(), MockTools(), lambda *args: False)
    assert result.answer == "ok" and result.tokens == 18 and result.stop_reason == "done"
    url, kwargs = requests[0]
    assert url == "http://localhost:11434/api/chat"
    assert kwargs["json"]["format"] == "json"
    assert [message["role"] for message in kwargs["json"]["messages"]] == ["system", "user"]


@pytest.mark.parametrize("used", [-100, 1.5, True])
def test_invalid_token_accounting_fails_before_any_action(used):
    tools = MockTools()
    with pytest.raises(ValueError, match="token usage"):
        run_agent("test", "cv", ScriptedLLM([SCRIPT[2]], tokens_per_call=used),
                  tools, lambda *args: True)
    assert tools.tracker == tools.submitted == {}
