"""One graph run per browser session, moved forward through its pauses (stages 7 and 9)."""
import uuid

import streamlit as st
from langgraph.types import Command

from core import log
from core.config import get_settings
from graph.graph import build_graph

# Pause of the graph -> page that answers it.
PAGES = {"user_decides": "Decisions", "review": "Review"}
KEYS = ("profile_run", "graph", "config", "pending")  # everything a run keeps in the session


def start(state: dict) -> None:
    """New run from `state`, up to its first pause."""
    settings = get_settings(dry=True)
    st.session_state["graph"] = build_graph(settings)  # its checkpointer keeps the run
    st.session_state["config"] = {"configurable": {"thread_id": str(uuid.uuid4())},
                                  "recursion_limit": settings.max_steps + 20}
    _run(state)


def resume(answer: dict) -> None:
    """Answer the current pause, run to the next one, and open the page that handles it."""
    _run(Command(resume=answer))
    st.session_state["goto"] = PAGES.get(pending_stage(), "Tracker")


def _run(value) -> None:
    graph, config = st.session_state["graph"], st.session_state["config"]
    paused = graph.invoke(value, config).get("__interrupt__")
    st.session_state["profile_run"] = graph.get_state(config).values
    st.session_state["pending"] = paused[0].value if paused else None
    if not paused:
        log.system(f"run ended: {st.session_state['profile_run'].get('stop_reason')}")


def pending_stage() -> str | None:
    """"user_decides", "review", or None when the run has ended."""
    return (st.session_state.get("pending") or {}).get("stage")


def reset() -> None:
    for key in KEYS:
        st.session_state.pop(key, None)
