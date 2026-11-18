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
├── data/samples/   sample resumes and offers (mock data)
├── data/uploads/   resumes uploaded from the web page (git-ignored)
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
| `data/uploads/` | Resumes uploaded from the web page, saved under random names. Git-ignored (personal data). |
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
| `.gitignore` | Files kept out of git (secrets, caches, databases, logs, local notes, uploaded resumes). |
| `.streamlit/config.toml` | Streamlit settings: maximum upload size (5 MB). |
| `pytest.ini` | pytest settings. |

## `app/`

| File | Intended use |
|---|---|
| `main.py` | Streamlit entry point: title, provider picker (top right), sidebar and page selection. Pages after Offers are placeholders. |
| `offers_view.py` | Ranked offers, best match first, each in a card (position, title, company, location, match score coloured green/orange/red with a bar, the reason for the score, source, URL, description hidden until clicked). If ranking failed, the safe offers in the order found; offers blocked by the security check in a separate closed section with the reasons; searches that failed. Text from job sites is escaped or shown as plain text, so it cannot add links or formatting. |
| `provider_picker.py` | OpenAI / Gemini choice with key status (set or missing in `.env`). Locked while a run exists; **Start over** clears the run. |
| `upload_page.py` | Resume & profile page: upload form (resume, locations, real model or not, how to find offers), runs the graph up to the first pause, shows the profile (closed until clicked) and the offers, or a clear error. |
| `uploads.py` | Checks an uploaded file (PDF/TXT only, max 5 MB, real content) and saves it under a random name in `data/uploads/`. |

## `core/`

| File | Intended use |
|---|---|
| `config.py` | Loads settings from `.env` (keys, default provider, limits, model timeout and retries) and the per-step, per-provider models from `config/models.yaml`. `key_status()` tells which provider keys are set. Raises a clear error if the chosen provider's key is missing (not in dry mode). |
| `llm.py` | `get_chat_model(stage, settings, provider)`: builds the chat model for a step with the run's provider, with the timeout and retry limits. Clear error if that provider's key is missing. |
| `resume_reader.py` | Reads a resume file (`.pdf` with pypdf, or `.txt`) and returns its text. Clear errors for other formats, damaged or scanned PDFs. |
| `models.py` | Shared data models: Profile, Offer, SecurityVerdict, RankedOffer, OfferStatus, Application, TrackerEntry. |
| `state.py` | The workflow state passed between steps. Inputs set at the start: `resume_path`, `location_preferences`, `use_llm`, `llm_provider` (used by every step that calls a model), `search_mode` (step 3). |
| `samples.py` | Loads the sample resumes and offers for the stubs. |

## `config/`

| File | Intended use |
|---|---|
| `models.yaml` | For each step that calls a model: model name and temperature for OpenAI (`openai`) and for Gemini (`google_genai`). |

## `graph/`

| File | Intended use |
|---|---|
| `graph.py` | Wires the 10 steps with their branches and loops, pauses for the user (stages 7 and 9), and enforces the limits and stop reasons. |
| `run.py` | Command line entry point. `--dry` runs the whole graph on sample data with a scripted user and no keys; `--resume`, `--locations` and `--llm` feed a real resume to the profile step; `--provider openai\|gemini` picks the model provider for the run; `--search stub\|scrape\|agent` picks how step 3 finds offers. |

## `graph/nodes/`

Files are named `S<stage number>_<name>.py`. Each exposes `node(state) -> dict`, a partial update of the workflow state.

| File | Step |
|---|---|
| `S1_upload.py` | 1. Read the resume at `resume_path` (sample resume if empty). |
| `S2_profile.py` | 2. Build a structured profile with the model (or a fixed one without `use_llm`); copies the user's locations. Stops with `llm_error` if the model fails. |
| `S3_find_offers.py` | 3. Find new offers, skipping those already seen. Three modes: `stub` (samples), `scrape` (each role in each location on each site, no LLM), `agent` (the model calls one tool, `SearchJobs`, to pick site, query and location). `Collector` runs the searches, drops duplicates and remembers the next page of each search. |
| `S4_security.py` | 4. Quarantine unsafe offers. |
| `S5_rank.py` | 5. Score and rank safe offers. |
| `S6_show_batch.py` | 6. Pick the next batch of offers to show. |
| `S7_user_decides.py` | 7. Pause for the user's choices and the next action. |
| `S8_cover_letter.py` | 8. Write a cover letter from profile facts and fact-check it (Agent 5). |
| `S9_review.py` | 9. Optional pause to confirm, edit or cancel. |
| `S10_apply.py` | 10. Refuse unchecked letters, then email the application to the test inbox (dry run by default) and avoid duplicates (Agent 6). |

## `services/`

### `services/letter/` (Agent 5)

| File | Intended use |
|---|---|
| `writer.py` | Writes the letter from the `Profile` only; offer fenced as `<untrusted_offer>`. `stub_letter` is the no-model version used in dry mode. |
| `factcheck.py` | Splits the letter into claims and judges each against the profile (LLM), plus a deterministic number check the LLM cannot override. Fails closed. |
| `__init__.py` | `write_verified_letter`: the write -> check -> retry loop, returning the letter and a `FactCheckReport`. |

### `services/mailer/` (Agent 6)

| File | Intended use |
|---|---|
| `__init__.py` | Builds the application email (always to `test_inbox`, never the employer; headers reject line breaks) and sends it; `dry_run=True` composes without opening SMTP. |

### `services/tracker/` (Agent 6)

| File | Intended use |
|---|---|
| `__init__.py` | `already_applied()` blocks duplicate submissions; `make_entry()` builds a `TrackerEntry`. In-memory for now (SQLite later). |

### `services/scraping/`

Every source has the same function: `search(query, location, page, max_offers, seen_ids) -> list[Offer]`.

| File | Intended use |
|---|---|
| `__init__.py` | `SOURCES` (name, module, what it covers) and `search(source, ...)`: the only entry point stage 3 uses. |
| `fetch.py` | `fetch_html()` / `fetch_json()`: allowed hosts only, delay per host, timeout, size cap. `ScrapeError` on failure, `PageNotFound` for HTTP 404. |
| `jsonld.py` | Reads schema.org `JobPosting` blocks from an offer page and turns them into `Offer`s. `read_offer_pages()` opens offer pages, skipping seen ones and duplicates. |
| `filters.py` | Text helpers: location match, keyword match, duplicate key, French query (`intern` -> `stage`), shorter fallback query. |
| `jobijoba.py` | Jobijoba (France): `/fr/emploi/<query>/<city>?page=N`, then each offer page. |
| `keejob.py` | Keejob (Tunisia): `/offres-emploi/?keywords=...&page=N`, then each offer page; city checked per offer. |
| `arbeitnow.py` | Arbeitnow (Europe, remote): public JSON API, keywords and location filtered in code. |

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
