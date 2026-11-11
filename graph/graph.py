"""LangGraph wiring of the 10 stages, with global limits enforced in code.

Flow: upload -> profile -> find_offers -> security -> rank -> show_batch -> user_decides
      user_decides -> cover_letter (selected offer) | show_batch (next)
                      | find_offers (find others) | END (done)
      cover_letter -> review -> apply (confirm) | cover_letter (edit) | user_decides (cancel)
      apply -> user_decides

Stages 7 and 9 pause with `interrupt`, so a checkpointer is required.
"""
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from core.config import Settings
from core.state import WorkflowState
from graph.nodes import (apply, cover_letter, find_offers, profile, rank, review,
                         security, show_batch, upload, user_decides)

STAGES = {
    "upload": upload, "profile": profile, "find_offers": find_offers, "security": security,
    "rank": rank, "show_batch": show_batch, "user_decides": user_decides,
    "cover_letter": cover_letter, "review": review, "apply": apply,
}


def _guarded(name: str, fn, settings: Settings):
    """Wrap a node: count steps and enforce the global limits (never left to prompts)."""

    def run(state: WorkflowState) -> dict:
        steps = state.get("steps", 0) + 1
        if steps > settings.max_steps:
            return {"steps": steps, "stop_reason": "max_steps"}
        if state.get("tokens_used", 0) >= settings.max_tokens:
            return {"steps": steps, "stop_reason": "token_budget"}
        if name == "apply" and state.get("applications_sent", 0) >= settings.max_applications:
            return {"steps": steps, "stop_reason": "max_applications"}

        out = {**fn(state), "steps": steps}
        if out.get("tokens_used", 0) >= settings.max_tokens:
            out["stop_reason"] = "token_budget"
        if name == "apply" and out["applications_sent"] >= settings.max_applications:
            out["stop_reason"] = "max_applications"
        if name == "user_decides" and out.get("route") == "done":
            out["stop_reason"] = "user_done"
        return out

    return run


def _then(target: str):
    """Edge to `target`, unless a stop reason is set."""
    return lambda s: END if s.get("stop_reason") else target


def _branch(key: str, mapping: dict[str, str]):
    """Edge chosen by state[key], unless a stop reason is set. Unknown value -> END."""
    return lambda s: END if s.get("stop_reason") else mapping.get(s.get(key), END)


# Pydantic models stored in the checkpoint must be allow-listed for deserialization.
_SERDE = JsonPlusSerializer(allowed_msgpack_modules=[
    ("core.models", n) for n in ("Profile", "Offer", "SecurityVerdict", "RankedOffer",
                                 "OfferStatus", "Application")])


def build_graph(settings: Settings, checkpointer=None):
    g = StateGraph(WorkflowState)
    for name, module in STAGES.items():
        g.add_node(name, _guarded(name, module.node, settings))

    g.add_edge(START, "upload")
    for src, dst in [("upload", "profile"), ("profile", "find_offers"),
                     ("find_offers", "security"), ("security", "rank"),
                     ("rank", "show_batch"), ("show_batch", "user_decides"),
                     ("cover_letter", "review"), ("apply", "user_decides")]:
        g.add_conditional_edges(src, _then(dst), [dst, END])

    g.add_conditional_edges(
        "user_decides",
        _branch("route", {"apply": "cover_letter", "next": "show_batch",
                          "find_others": "find_offers"}),
        ["cover_letter", "show_batch", "find_offers", END])
    g.add_conditional_edges(
        "review",
        _branch("review_decision", {"confirm": "apply", "edit": "cover_letter",
                                    "cancel": "user_decides"}),
        ["apply", "cover_letter", "user_decides", END])

    return g.compile(checkpointer=checkpointer or MemorySaver(serde=_SERDE))
