"""Stage 6 - Show batch."""
from core.config import get_settings


def node(state: dict) -> dict:
    """Input: `ranked`, `batch_cursor`.
    Output: `current_batch` (next BATCH_SIZE unseen offers) and an advanced `batch_cursor`.
    Will: also mark the offers 'shown' in the tracker and display them on the web page."""
    size = get_settings(dry=True).batch_size
    cur = state.get("batch_cursor", 0)
    return {"current_batch": state.get("ranked", [])[cur:cur + size], "batch_cursor": cur + size}
