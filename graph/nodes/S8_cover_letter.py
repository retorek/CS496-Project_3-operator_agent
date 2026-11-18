"""Stage 8 - Write cover letter (Agent 5)."""
from core.config import ConfigError
from services.letter import write_verified_letter


def node(state: dict) -> dict:
    """Input: `current_offer`, `profile`, `use_llm`, `llm_provider`.
    Output: `cover_letters[offer_id]` (resume facts only), `cover_letter_reports[offer_id]`
    (the fact-check result), updated `tokens_used`.
    Writes the letter from the profile only, with the offer fenced as untrusted data,
    then fact-checks it. A letter that fails the check is still recorded with
    passed=False so stage 10 refuses to send it.
    If the model call fails: no change, `stop_reason="llm_error"`, the reason in `errors`."""
    offer = state["current_offer"]
    profile = state["profile"]
    letters = dict(state.get("cover_letters", {}))
    reports = dict(state.get("cover_letter_reports", {}))
    try:
        letter, report, tokens = write_verified_letter(
            profile, offer, use_llm=bool(state.get("use_llm")),
            provider=state.get("llm_provider", "openai"))
    except ConfigError:
        raise  # missing key: a setup problem, shown by the CLI
    except Exception as e:  # overload, timeout, quota, network, bad output
        return {"stop_reason": "llm_error",
                "errors": [f"cover_letter: model call failed ({type(e).__name__}): {str(e)[:200]}"]}

    letters[offer.id] = letter
    reports[offer.id] = report.to_dict()
    return {"cover_letters": letters, "cover_letter_reports": reports,
            "tokens_used": state.get("tokens_used", 0) + tokens}
