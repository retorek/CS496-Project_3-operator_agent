"""Terminal log: one timestamped line per action, tagged USER or SYSTEM.

    2026-11-18 09:30:12 [USER]   decisions: apply 1, decline 1, dismiss 0, then next
    2026-11-18 09:30:12 [SYSTEM] stage cover_letter started
"""
import logging
import sys

_logger = logging.getLogger("operator")
if not _logger.handlers:  # Streamlit re-imports on reruns: add the handler only once
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(owner)-6s] %(message)s",
                                            "%Y-%m-%d %H:%M:%S"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def user(message: str) -> None:
    """Something the user did: a click, a choice, an answer."""
    _logger.info(message, extra={"owner": "USER"})


def system(message: str) -> None:
    """Something the system did: a stage, a model call, a web request."""
    _logger.info(message, extra={"owner": "SYSTEM"})
