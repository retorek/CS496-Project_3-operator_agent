"""Stage 6 - Show batch."""
from core.config import get_settings


def node(state: dict) -> dict:
    """Input: `ranked`, `batch_cursor`.
    Output: `current_batch` (next BATCH_SIZE unseen offers) and an advanced `batch_cursor`.
    Will: also mark the offers 'shown' in the tracker and display them on the web page."""
    size = get_settings(dry=True).batch_size
    cur = state.get("batch_cursor", 0)
    ranked = state.get("ranked", [])
    shown = list(state.get("shown_offer_ids", []))
    shown_set = set(shown)
    batch = []
    while cur < len(ranked) and len(batch) < size:
        item = ranked[cur]
        cur += 1
        if item.offer.id not in shown_set:
            batch.append(item)
            shown.append(item.offer.id)
            shown_set.add(item.offer.id)
    return {"current_batch": batch, "batch_cursor": cur, "shown_offer_ids": shown}
