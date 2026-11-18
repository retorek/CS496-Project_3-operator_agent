"""CLI: `python -m graph.run --dry` runs the whole graph with stubs and no API keys."""
import argparse
import sys
import uuid
from collections import Counter

from langgraph.types import Command

from core.config import PROVIDERS, ConfigError, Settings, get_settings
from core.state import initial_state
from graph.graph import build_graph

# --provider value -> LangChain provider name
CLI_PROVIDERS = {"openai": "openai", "gemini": "google_genai"}


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
              thread_id: str | None = None, resume_path: str = "",
              location_preferences: list[str] | None = None, use_llm: bool = False,
              llm_provider: str | None = None, search_mode: str = "stub",
              security_dry_run: bool = True, rank_dry_run: bool = True) -> dict:
    """Run to the end, answering each interrupt with `user`. Returns the final state.
    `llm_provider` defaults to LLM_PROVIDER in .env.
    Security and ranking use offline demo modes unless their dry-run flags are False."""
    graph = build_graph(settings)
    config = {"configurable": {"thread_id": thread_id or str(uuid.uuid4())},
              # LangGraph's own cap must stay above our max_steps so ours triggers first.
              "recursion_limit": settings.max_steps + 20}
    start = initial_state(review_enabled, resume_path, location_preferences, use_llm,
                          llm_provider=llm_provider or settings.llm_provider,
                          search_mode=search_mode, security_dry_run=security_dry_run,
                          rank_dry_run=rank_dry_run)
    result = graph.invoke(start, config)
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        result = graph.invoke(Command(resume=user.answer(payload)), config)
    return graph.get_state(config).values


def print_offers(offers: list) -> None:
    """Offers found by stage 3, grouped by source."""
    by_source = Counter(o.source for o in offers)
    print(f"offers: {len(offers)} " + " ".join(f"{s}={n}" for s, n in by_source.items()))
    for o in offers:
        print(f"  [{o.source}] {o.title[:70]} | {o.company[:30]} | {o.location[:40]}")


def print_applications(state: dict) -> None:
    """Stages 8-10: the cover letter, its fact check and the (dry-run) application."""
    reports = state.get("cover_letter_reports", {})
    for offer_id, letter in state.get("cover_letters", {}).items():
        print(f"\n--- cover letter [{offer_id}] ---\n{letter}")
        report = reports.get(offer_id)
        if report is not None:
            flags = report.get("unsupported") or []
            print(f"fact check: passed={report.get('passed')} unsupported={len(flags)}")
            for flag in flags:
                print(f"  - {flag}")
    dry = state.get("send_dry_run", True)
    for app in state.get("applications", []):
        if app.status.value == "applied":
            how = "dry run, not actually emailed" if dry else "emailed to the test inbox"
        else:
            how = "no email"
        print(f"application: offer={app.offer_id} status={app.status.value} ({how})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the internship application graph.")
    parser.add_argument("--dry", action="store_true", help="stubs + scripted user, no API keys")
    parser.add_argument("--resume", default="", help="resume file (.pdf or .txt); default: mock")
    parser.add_argument("--locations", default="", help='where to look, e.g. "Lyon,Remote"')
    parser.add_argument("--llm", action="store_true", help="profile stage calls its real model")
    parser.add_argument("--provider", choices=list(CLI_PROVIDERS),
                        help="model provider for the whole run (default: LLM_PROVIDER in .env)")
    parser.add_argument("--search", choices=["stub", "scrape", "agent"], default="stub",
                        help="stage 3: sample offers, real job sites, or real sites driven by the LLM")
    args = parser.parse_args(argv)
    locations = [loc.strip() for loc in args.locations.split(",") if loc.strip()]
    provider = CLI_PROVIDERS.get(args.provider)
    try:
        settings = get_settings(dry=args.dry, provider=provider)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    if not args.dry:
        print("Real mode is not implemented yet (stages are still stubs). Use --dry.")
        return 1
    try:
        state = run_graph(settings, default_dry_script(),
                          resume_path=args.resume, location_preferences=locations,
                          use_llm=args.llm, llm_provider=provider, search_mode=args.search)
    except (OSError, ValueError) as e:  # missing file, bad format, empty PDF
        print(f"Resume error: {e}", file=sys.stderr)
        return 2
    except ConfigError as e:  # e.g. GOOGLE_API_KEY missing
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    print(f"provider: {PROVIDERS[state['llm_provider']]}")
    print(f"resume_text (first 200 chars): {state['resume_text'][:200]!r}")
    if state["profile"]:
        print(f"profile: {state['profile'].model_dump_json(indent=2)}")
    for key, next_page in state.get("search_pages", {}).items():
        print(f"search: {key} (pages read: {next_page - 1})")
    print_offers(state["offers"])
    print_applications(state)
    for error in state["errors"]:
        print(f"error: {error}", file=sys.stderr)
    print(f"stop_reason={state['stop_reason']} steps={state['steps']} "
          f"applications_sent={state['applications_sent']} "
          f"quarantined={len(state['quarantined'])} tokens_used={state['tokens_used']}")
    return 1 if state["stop_reason"] == "llm_error" else 0


if __name__ == "__main__":
    sys.exit(main())
