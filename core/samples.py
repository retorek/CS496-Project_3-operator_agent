"""Loaders for data/samples/, used by the stub nodes."""
import json
from pathlib import Path

from core.models import Offer

SAMPLES = Path(__file__).resolve().parent.parent / "data" / "samples"


def load_resume(name: str = "resume_alice.txt") -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def load_offers() -> list[Offer]:
    return [Offer(**o) for o in json.loads((SAMPLES / "offers.json").read_text(encoding="utf-8"))]
