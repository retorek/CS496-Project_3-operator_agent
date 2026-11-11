# Internship application assistant

Reads a resume, finds and ranks internship offers, drafts cover letters, and applies
**only after the user approves**. Applications go to a TEST inbox, never to the employer.
This repo is currently a **skeleton**: every stage is a stub returning sample data.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env            # then fill in keys (not needed for --dry)
```

## Run

```bash
python -m graph.run --dry         # whole graph with stubs, no API keys
streamlit run app/main.py         # placeholder web page
python -m pytest -q               # tests
```

## Workflow (10 stages)

1 upload -> 2 profile -> 3 find_offers -> 4 security -> 5 rank -> 6 show_batch ->
7 user_decides (pause) -> 8 cover_letter -> 9 review (optional pause) -> 10 apply -> 7.
From 7 the user can also go to "Next" (6), "Find others" (3) or "Done" (end).
Review can confirm (10), edit (8) or cancel (7).

Global limits (`MAX_STEPS`, `MAX_TOKENS`, `MAX_APPLICATIONS`) are enforced in
`graph/graph.py`, not in prompts. The final state always has a `stop_reason`:
`user_done`, `max_steps`, `token_budget` or `max_applications`.

## Which file to edit for which task

| Task | File |
|---|---|
| SET-01 layout, dependencies | `requirements.txt`, `.gitignore` |
| SET-02 settings and secrets | `core/config.py`, `.env.example` |
| SET-03 data models | `core/models.py` |
| SET-04 workflow state | `core/state.py` |
| SET-05 model per stage | `config/models.yaml` |
| Stage 1 upload resume | `graph/nodes/upload.py` (UI: `app/main.py`) |
| Stage 2 build profile | `graph/nodes/profile.py` |
| Stage 3 find offers | `graph/nodes/find_offers.py`, `services/scraping/` |
| Stage 4 security check | `graph/nodes/security.py` |
| Stage 5 rank offers | `graph/nodes/rank.py` |
| Stage 6 show batch | `graph/nodes/show_batch.py` |
| Stage 7 user decides | `graph/nodes/user_decides.py` |
| Stage 8 cover letter | `graph/nodes/cover_letter.py` |
| Stage 9 review | `graph/nodes/review.py` |
| Stage 10 apply | `graph/nodes/apply.py`, `services/mailer/`, `services/tracker/` |
| Graph wiring, limits, stop reasons | `graph/graph.py` |
| Dry-run CLI and scripted user | `graph/run.py` |
| Evaluation scenarios | `eval/` |
| Sample resumes and offers | `data/samples/` |

Each node file exposes `node(state) -> dict` (a partial state update). Keep to that
signature and you will not need to touch other stages.

`legacy/` holds the old draft (kept for reference, not used).
