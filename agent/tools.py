"""4 mock tools on dummy data. Swap for P2's real tools later (same call() signature)."""
import json
from pathlib import Path

from pydantic import ValidationError

from .schemas import (ReadOfferInput, SearchJobsInput, SubmitApplicationInput,
                      ToolError, UpdateTrackerInput, readable)

DATA = Path(__file__).resolve().parent.parent / "data"

TOOL_DESCRIPTIONS = """\
search_jobs(query: str, limit: int=5)            -> list of {id, title, company}
read_offer(offer_id: str)                        -> full offer text
update_tracker(offer_id, status, match_score, notes="")
    status is one of: interested | skip | applied ; match_score is 0-100 (needs human approval)
submit_application(offer_id: str, letter: str)   -> sends the application (needs human approval)"""


class MockTools:
    def __init__(self, offers_path=DATA / "offers.json"):
        self.offers = {o["id"]: o for o in json.loads(Path(offers_path).read_text())}
        self.tracker: dict[str, dict] = {}    # idempotent: keyed by offer_id
        self.submitted: dict[str, str] = {}   # offer_id -> letter

    def call(self, name: str, args: dict):
        specs = {
            "search_jobs": (SearchJobsInput, self._search_jobs),
            "read_offer": (ReadOfferInput, self._read_offer),
            "update_tracker": (UpdateTrackerInput, self._update_tracker),
            "submit_application": (SubmitApplicationInput, self._submit_application),
        }
        if name not in specs:
            raise ToolError(f"Unknown tool '{name}'. Available: {', '.join(specs)}.")
        model, fn = specs[name]
        try:
            parsed = model(**args)
        except (ValidationError, TypeError) as e:
            msg = readable(e) if isinstance(e, ValidationError) else str(e)
            raise ToolError(f"Invalid arguments for {name}: {msg}") from None
        return fn(parsed)

    def validate(self, name: str, args: dict) -> None:
        """Check write arguments without executing (before asking the human)."""
        try:
            {"update_tracker": UpdateTrackerInput,
             "submit_application": SubmitApplicationInput}[name](**args)
        except KeyError:
            raise ToolError(f"Unknown write tool '{name}'.") from None
        except (ValidationError, TypeError) as e:
            msg = readable(e) if isinstance(e, ValidationError) else str(e)
            raise ToolError(f"Invalid arguments for {name}: {msg}") from None

    # --- tools ---
    def _search_jobs(self, a: SearchJobsInput):
        q = a.query.lower()
        hits = [o for o in self.offers.values()
                if q in (o["title"] + " " + o["description"] + " " + o["company"]).lower()]
        if not hits:
            return []  # empty result is a valid outcome, not an exception
        return [{"id": o["id"], "title": o["title"], "company": o["company"]}
                for o in hits[: a.limit]]

    def _read_offer(self, a: ReadOfferInput):
        if a.offer_id not in self.offers:
            raise ToolError(f"Offer '{a.offer_id}' not found. Use an id from search_jobs.")
        return self.offers[a.offer_id]

    def _update_tracker(self, a: UpdateTrackerInput):
        if a.offer_id not in self.offers:
            raise ToolError(f"Offer '{a.offer_id}' not found.")
        self.tracker[a.offer_id] = a.model_dump()  # same call twice = same state
        return {"ok": True, "rows": len(self.tracker)}

    def _submit_application(self, a: SubmitApplicationInput):
        if a.offer_id not in self.offers:
            raise ToolError(f"Offer '{a.offer_id}' not found.")
        if a.offer_id in self.submitted:
            raise ToolError(f"Already applied to '{a.offer_id}'. Nothing was sent again.")
        self.submitted[a.offer_id] = a.letter
        return {"ok": True, "message": f"Application sent (mock) to {a.offer_id}."}
