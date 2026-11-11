# Internship Application Assistant

An assistant that helps you apply to internships. You upload your resume; it builds a
profile, finds and ranks matching offers, and drafts a cover letter for each offer you
pick. **Nothing is sent without your approval**, and applications go to a test inbox,
never to the employer.

## How it works

1. **Upload** your resume.
2. **Profile**: your skills, experience, education and target roles are extracted.
3. **Find offers**: new offers are collected from job websites; ones already seen are skipped.
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

Fill in `.env` with your keys (not needed for the demo run). Settings include the OpenAI
and LangSmith keys, the mail server and test inbox, the batch size, and the three limits.

## Usage

```bash
python -m graph.run --dry         # full run with sample data, no API keys
streamlit run app/main.py         # web interface
python -m pytest -q               # tests
```

Which model is used for each step is set in `config/models.yaml`.

## Project status

The structure and the flow are in place, but each step still returns sample data, and the web
page is a placeholder. See [FILES.md](FILES.md) for the folder layout and what each file is for.

## Tech

Python, OpenAI API, LangChain, LangGraph, LangSmith, Streamlit, Pydantic, SQLite, pytest.
