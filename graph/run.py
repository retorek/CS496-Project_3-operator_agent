"""CLI: `python -m graph.run --dry` runs the whole graph with stubs and no API keys."""
import argparse
import sys
import uuid

from langgraph.types import Command

from core.config import ConfigError, Settings, get_settings
from core.state import initial_state
from graph.graph import build_graph


class ScriptedUser:
    """Fixed script standing in for the human in --dry mode.

    `user_decides` entries: {"select": [batch indexes], "action": "next|find_others|done"}.
    `review` entries: "confirm" | "edit" | "cancel".
    When a list runs out: "done" / "confirm", or the last entry again if repeat_last.
    """

    def __init__(self, user_decides=None, review=None, repeat_last=False):
        self.script = {"user_decides": list(user_decides or []), "review": list(review or [])}
        self.repeat_last = repeat_last
        self.calls = {"user_decides": 0, "review": 0}

    def answer(self, payload: dict):
        stage = payload["stage"]
        i, items = self.calls[stage], self.script[stage]
        self.calls[stage] += 1
        if i < len(items):
            item = items[i]
        elif self.repeat_last and items:
            item = items[-1]
        else:
            item = {"select": [], "action": "done"} if stage == "user_decides" else "confirm"
        if stage == "review":
            return {"decision": item}
        batch = payload["batch"]
        return {"selected": [batch[k] for k in item["select"] if k < len(batch)],
                "action": item["action"]}


def default_dry_script() -> ScriptedUser:
    """Applies to one offer (after one 'edit' of the letter), asks for more, then finishes."""
    return ScriptedUser(
        user_decides=[{"select": [0], "action": "next"},
                      {"select": [], "action": "find_others"},
                      {"select": [], "action": "done"}],
        review=["edit", "confirm"],
    )


def run_graph(settings: Settings, user: ScriptedUser, review_enabled: bool = True,
              thread_id: str | None = None) -> dict:
    """Run to the end, answering each interrupt with `user`. Returns the final state."""
    graph = build_graph(settings)
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())},
              # LangGraph's own cap must stay above our max_steps so ours triggers first.
              "recursion_limit": settings.max_steps + 20}
    result = graph.invoke(initial_state(review_enabled), config)
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        result = graph.invoke(Command(resume=user.answer(payload)), config)
    return graph.get_state(config).values


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the internship application graph.")
    parser.add_argument("--dry", action="store_true", help="stubs + scripted user, no API keys")
    args = parser.parse_args(argv)
    try:
        settings = get_settings(dry=args.dry)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    if not args.dry:
        print("Real mode is not implemented yet (stages are still stubs). Use --dry.")
        return 1
    state = run_graph(settings, default_dry_script())
    print(f"stop_reason={state['stop_reason']} steps={state['steps']} "
          f"applications_sent={state['applications_sent']} "
          f"quarantined={len(state['quarantined'])} tokens_used={state['tokens_used']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
