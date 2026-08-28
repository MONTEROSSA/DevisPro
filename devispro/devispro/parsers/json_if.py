"""JSON-Zwischenformat – praktisch für den LLM-Hook (Abacus.ai, RAG, etc.)."""
import json
from ..models import Devis, Position


def parse(path: str) -> Devis:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    positions = [Position(**p) for p in data.get("positions", [])]
    return Devis(
        meta=data.get("meta", {}),
        addresses=data.get("addresses", []),
        chapters=data.get("chapters", []),
        positions=positions,
    )


def export(devis: Devis, path: str) -> None:
    data = {
        "meta": devis.meta,
        "addresses": devis.addresses,
        "chapters": devis.chapters,
        "positions": [p.__dict__ for p in devis.positions],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
