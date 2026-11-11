# Project structure

```
.
├── app/            web interface
├── core/           settings, data models, shared state
├── config/         per-step model configuration
├── graph/          the workflow
│   └── nodes/      one file per step
├── services/       integrations with the outside world
│   ├── scraping/
│   ├── mailer/
│   └── tracker/
├── data/samples/   sample resumes and offers
├── eval/           evaluation scenarios
├── tests/          automated tests
└── legacy/         old draft, kept for reference
```

## Folders

| Folder | Intended use |
|---|---|
| `app/` | Streamlit web interface the user interacts with. |
| `core/` | Code shared by everything else: settings, data models, workflow state. |
| `config/` | Configuration files that are not secrets (which model runs each step). |
| `graph/` | The LangGraph workflow: how the steps connect, the pauses for the user, and the global limits. |
| `graph/nodes/` | One file per workflow step, so each step can be developed on its own. |
| `services/scraping/` | Collecting offers from job websites. |
| `services/mailer/` | Sending the application and cover letter to the test inbox. |
| `services/tracker/` | SQLite tracker of each offer's status. |
| `data/samples/` | Sample resumes and offers (two offers contain injection text) used for demos and tests. |
| `eval/` | Scenarios and scoring scripts to evaluate the assistant. |
| `tests/` | pytest tests. |
| `legacy/` | Earlier prototype. Not used by the current code. |

## Root files

| File | Intended use |
|---|---|
| `README.md` | Overview of the project, setup and usage. |
| `FILES.md` | This file: layout and purpose of each file. |
| `requirements.txt` | Python dependencies. |
| `.env.example` | Template for `.env` (keys, mail server, limits). `.env` itself is git-ignored. |
| `.gitignore` | Files kept out of git (secrets, caches, databases, logs, local notes). |
| `pytest.ini` | pytest settings. |

## `app/`

| File | Intended use |
|---|---|
| `main.py` | Streamlit entry point. Currently placeholder pages. |

## `core/`

| File | Intended use |
|---|---|
| `config.py` | Loads settings from `.env` and the per-step models from `config/models.yaml`. Raises a clear error if the OpenAI key is missing (not in dry mode). |
| `models.py` | Shared data models: Profile, Offer, SecurityVerdict, RankedOffer, OfferStatus, Application, TrackerEntry. |
| `state.py` | The workflow state passed between steps. |
| `samples.py` | Loads the sample resumes and offers for the stubs. |

## `config/`

| File | Intended use |
|---|---|
| `models.yaml` | Model name and temperature for each step that calls a model. |

## `graph/`

| File | Intended use |
|---|---|
| `graph.py` | Wires the 10 steps with their branches and loops, pauses for the user (stages 7 and 9), and enforces the limits and stop reasons. |
| `run.py` | Command line entry point. `--dry` runs the whole graph on sample data with a scripted user and no keys. |

## `graph/nodes/`

Each file exposes `node(state) -> dict`, a partial update of the workflow state.

| File | Step |
|---|---|
| `upload.py` | 1. Read the uploaded resume. |
| `profile.py` | 2. Build a structured profile. |
| `find_offers.py` | 3. Find new offers, skipping those already seen. |
| `security.py` | 4. Quarantine unsafe offers. |
| `rank.py` | 5. Score and rank safe offers. |
| `show_batch.py` | 6. Pick the next batch of offers to show. |
| `user_decides.py` | 7. Pause for the user's choices and the next action. |
| `cover_letter.py` | 8. Write a cover letter from resume facts. |
| `review.py` | 9. Optional pause to confirm, edit or cancel. |
| `apply.py` | 10. Send the application to the test inbox and update the tracker. |

## `services/`

`scraping/`, `mailer/` and `tracker/` are empty packages (`__init__.py` only) for now.

## `data/samples/`

| File | Intended use |
|---|---|
| `resume_alice.txt`, `resume_bob.txt` | Sample resumes. |
| `offers.json` | Ten sample offers; two contain injection text or requests for personal data. |

## `eval/` and `tests/`

| File | Intended use |
|---|---|
| `eval/README.md` | Explains that this folder will hold evaluation scenarios. |
| `tests/test_skeleton.py` | Tests for the models, settings, and the workflow (every step reached, limits, stop reasons). |
