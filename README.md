# Internship Application Assistant

An assistant that helps you apply to internships. You upload your resume; it builds a
profile, finds and ranks matching offers, and drafts a cover letter for each offer you
pick. **Nothing is sent without your approval**, and applications go to a test inbox,
never to the employer.

## How it works

1. **Upload** your resume.
2. **Profile**: your skills, experience, education and target roles are extracted.
3. **Find offers**: new offers are collected from job websites (Jobijoba for France, Keejob for
   Tunisia, Arbeitnow for Europe and remote); ones already seen are skipped.
4. **Security check**: offers containing prompt injection, suspicious links or requests for
   personal data are quarantined.
5. **Rank**: safe offers get a score and a short reason.
6. **Browse**: offers are shown in small batches.
7. **Decide**: mark each offer apply, decline or dismiss, then ask for the next batch,
   look for other offers, or finish.
8. **Cover letter**: written from your resume facts only.
9. **Review** (optional): confirm, edit or cancel before anything is sent.
10. **Apply**: the application and letter are emailed to a test inbox and the tracker is updated.

The run stops on its own when it hits a limit: maximum steps, token budget, or maximum
applications per session. Every run ends with a stop reason.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env
```

Fill in `.env` with your keys (not needed for the demo run). Settings include the OpenAI,
Google and LangSmith keys, the mail server and test inbox, the batch size, the three limits,
and the model call timeout and retries (`LLM_TIMEOUT`, `LLM_MAX_RETRIES`).

Two model providers are supported: **OpenAI** (`OPENAI_API_KEY`) and **Gemini**
(`GOOGLE_API_KEY`, free key from Google AI Studio). One provider is chosen at the start of a run
and used by every step until the end. `LLM_PROVIDER` in `.env` sets the default.

## Usage

### Web interface

```bash
streamlit run app/main.py
```

Opens at http://localhost:8501. At the top right, choose the **model provider** (OpenAI or
Gemini); it shows whether that provider's key is set in `.env`. Once a run has started the choice
is locked, so the same provider is used for the whole run; **Start over** clears the run and
unlocks it.

On the **Resume & profile** page:

1. Choose your resume (PDF or TXT, max 5 MB).
2. Type where you want to work, separated by commas (e.g. `Lyon, Remote`).
3. Keep **Use the real model** checked to build the profile with the model from
   `config/models.yaml` (needs its API key), or uncheck it to get a fixed sample profile.
4. Choose **How to find offers**: *Sample offers*, *Job sites* (`scrape` mode) or *Job sites,
   searches chosen by the AI* (`agent` mode, needs the provider's key). See step 3 below.
5. Click **Build my profile and find offers**. Searching job sites takes one to two minutes.

The profile appears closed: click it to see the details. Below it, each safe offer is shown in
its own box (click **Description** to read it). Offers blocked by the security check are listed
apart, closed, with the reasons. The **Offers** page in the sidebar shows the same offers.

Uploaded files are checked (type, size, real content) and saved under a random name in
`data/uploads/`, which is git-ignored. Errors (wrong file, unreadable PDF, missing key, model
busy) are shown on the page; unexpected errors are logged in the terminal running Streamlit.

### Command line

```bash
python -m graph.run --dry                       # full run with sample data, no API keys
python -m graph.run --dry --resume data/samples/resume_bob.txt --locations "Lyon, Remote"
python -m graph.run --dry --llm --resume my_cv.pdf --locations "Lyon, Remote"
python -m graph.run --dry --llm --provider gemini --resume my_cv.pdf
python -m graph.run --dry --search scrape --locations "Lyon, Tunis"   # real job sites, no LLM
python -m graph.run --dry --llm --search agent --locations "Lyon, Remote"   # LLM picks the searches
```

| Flag | Meaning |
|---|---|
| `--dry` | Every step uses sample data; a scripted user answers the pauses. |
| `--resume PATH` | Resume to read (`.pdf` or `.txt`). Default: a sample resume. |
| `--locations "A, B"` | Where the user wants to work. |
| `--llm` | The profile step calls its real model (needs its key in `.env`). |
| `--provider openai\|gemini` | Model provider for the whole run. Default: `LLM_PROVIDER` in `.env`. |
| `--search stub\|scrape\|agent` | How step 3 finds offers (default `stub`, see below). |

It prints the provider, the start of the resume text, the profile, the searches run and the
offers found, any errors, and the stop reason.

### Finding offers (step 3)

| Mode | What happens |
|---|---|
| `stub` | Sample offers from `data/samples/`. Offline, no key. |
| `scrape` | Real job sites, no LLM: each target role from the profile is searched in each location on every site (at most `MAX_QUERIES` pairs). |
| `agent` | Real job sites; the model chooses the site, the query and the location, at most `FIND_MAX_TOOL_CALLS` searches. Needs the provider's key. |

| Site | Covers | How offers are read |
|---|---|---|
| Jobijoba | France | Search page, then the structured `JobPosting` data on each offer page |
| Keejob | Tunisia | Same as Jobijoba; the city is checked on each offer |
| Arbeitnow | Europe (mostly Germany), remote | Free public JSON API |

Scraping is polite and limited: only these three sites can be fetched, with a delay between
requests to the same site (`SCRAPE_DELAY`), a timeout (`SCRAPE_TIMEOUT`), a page size cap, and at
most `MAX_OFFERS_PER_SEARCH` new offers per search. Each site's robots.txt allows the pages used.
The same job listed twice (other URL, same title and place) is kept once. "Find others" reads
the next results page of each search. Offer text is only extracted as data: the model in `agent`
mode sees title, company and place, never the full page, and is told not to follow instructions
found in it. A site that fails is logged in `errors` and the run goes on.

A scrape run takes about a minute or two: Jobijoba answers in 1 to 5 seconds per page.

### Tests

```bash
python -m pytest -q
```

### Models

`config/models.yaml` gives, for each step, the model name and temperature for both providers
(`openai` and `google_genai`). Changing a model needs no code change.

## Project status

- **Done:** steps 1 and 2. A PDF or TXT resume is read and turned into a profile by the model,
  from the web page or the command line. If the model fails, the run stops with
  `stop_reason="llm_error"` and the error is shown.
- **Done:** step 3, from the web page or the command line (`--search scrape` or `--search agent`).
- **Still sample data:** steps 4 to 10. The Decisions, Review and Tracker pages are placeholders.

See [FILES.md](FILES.md) for the folder layout and what each file is for.

## Tech

Python, OpenAI API, LangChain, LangGraph, LangSmith, Streamlit, Pydantic, SQLite, pytest.
