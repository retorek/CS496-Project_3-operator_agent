"""Stage 7 - User decides (pause for user)."""
from langgraph.types import interrupt


def node(state: dict) -> dict:
    """Input: `current_batch`, `selected_offer_ids` (queue), `next_action`.
    Output: `route`. "apply" with the next queued offer as `current_offer` (-> stage 8);
    once the queue is empty, the remembered action: "next" -> 6, "find_others" -> 3,
    "done" -> end.
    Will: pause with `interrupt` until the user marks each offer apply / declined /
    dismissed and picks Next / Find others / Done.
    Resume value: {"selected": [offer_id], "declined": [offer_id],
    "dismissed": [offer_id], "action": "next" | "find_others" | "done"}."""
    queue = list(state.get("selected_offer_ids", []))
    action = state.get("next_action", "")
    if not queue and not action:
        decision = interrupt({
            "stage": "user_decides",
            "batch": [r.offer.id for r in state.get("current_batch", [])],
        })
        queue = list(decision.get("selected", []))
        action = decision.get("action", "done")
    if queue:
        by_id = {o.id: o for o in state.get("offers", [])}
        return {"selected_offer_ids": queue[1:], "current_offer": by_id[queue[0]],
                "next_action": action, "route": "apply"}
    return {"selected_offer_ids": [], "current_offer": None, "next_action": "", "route": action}
