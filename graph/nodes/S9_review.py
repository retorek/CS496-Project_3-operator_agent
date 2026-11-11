"""Stage 9 - Review (optional pause for user)."""
from langgraph.types import interrupt


def node(state: dict) -> dict:
    """Input: `current_offer`, `cover_letters`, `review_enabled`.
    Output: `review_decision`: "confirm" (-> 10), "edit" (-> 8) or "cancel" (-> 7).
    Will: show the letter and pause with `interrupt` if `review_enabled`.
    Resume value: {"decision": "confirm" | "edit" | "cancel"}."""
    if not state.get("review_enabled", True):
        return {"review_decision": "confirm"}
    offer = state["current_offer"]
    answer = interrupt({
        "stage": "review",
        "offer_id": offer.id,
        "letter": state.get("cover_letters", {}).get(offer.id, ""),
    })
    return {"review_decision": answer.get("decision", "cancel")}
