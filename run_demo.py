"""Run the agent.  Examples:
    python run_demo.py                       # fake scripted model (no Ollama needed)
    python run_demo.py --model llama3.1      # local model through Ollama
    python run_demo.py --yes                 # auto-approve (for scripted runs only)
"""
import argparse
import json
from pathlib import Path

from agent.agent import Config, run_agent
from agent.llm import OllamaLLM, ScriptedLLM
from agent.tools import MockTools

ROOT = Path(__file__).parent
LETTER = "Dear Acme Tech team, I am a CS student with Python, SQL and FastAPI experience and would love to join as a backend intern."
SCRIPT = [
    '{"action": "search_jobs", "args": {"query": "python"}}',
    '{"action": "read_offer", "args": {"offer_id": "o1"}}',
    '{"action": "update_tracker", "args": {"offer_id": "o1", "status": "interested", "match_score": 90}}',
    '{"action": "submit_application", "args": {"offer_id": "o1", "letter": "%s"}}' % LETTER,
    '{"action": "finish", "answer": "Applied to o1."}',
]


def human_approve(action, args):
    print(f"\n--- CHECKPOINT: approve {action}? ---")
    print(json.dumps(args, indent=2, ensure_ascii=False))
    return input("Type 'yes' to approve this exact action: ").strip().lower() == "yes"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", help="Ollama model name; omit to use the scripted fake model")
    p.add_argument("--yes", action="store_true", help="auto-approve writes (scripted model only)")
    p.add_argument("--task", default="Find Python internships, track them, and apply to the best match.")
    args = p.parse_args()
    if args.yes and args.model:
        p.error("--yes is only allowed with the scripted model; omit --model")

    llm = OllamaLLM(args.model) if args.model else ScriptedLLM(SCRIPT)
    approve = (lambda action, args: True) if args.yes else human_approve
    tools = MockTools()
    cv = (ROOT / "data/cv.txt").read_text()

    res = run_agent(args.task, cv, llm, tools, approve, Config(), log_path=ROOT / "logs/run.jsonl")
    for s in res.steps:
        print(f"[{s['step']}] {s['tool']}({s['input']}) -> {str(s['output'])[:100]}")
    print(f"\nStop reason: {res.stop_reason} | tokens: {res.tokens} | sent: {list(tools.submitted)}")
    print(f"Answer: {res.answer}")


if __name__ == "__main__":
    main()
