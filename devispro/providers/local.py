import difflib
import re
from typing import List, Optional

from ..models import Position
from ..pricelist import PriceItem
from .base import BaseProvider, MatchResult


def _normalize(text: str) -> str:
    s = (text or "").lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def _norm_nr(nr: str) -> str:
    return _normalize(nr).replace(" ", "")


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _score(item: PriceItem, position: Position):
    """Gibt (score, reason) zurueck."""
    pos_nr = _norm_nr(position.pos_nr)
    item_nr = _norm_nr(item.npk or "")
    pos_text = _normalize(position.text)
    item_text = _normalize(item.bezeichnung)

    if item_nr and pos_nr.startswith(item_nr):
        # exakter NPK-Praefix -> sehr stark
        extra = ""
        if item.einheit and position.einheit and item.einheit.lower() != position.einheit.lower():
            extra = f" | ACHTUNG Einheit: Richtpreis {item.einheit} vs Devis {position.einheit}"
            return 0.98, "NPK-Praefix-Treffer" + extra, True
        return 0.98, "NPK-Praefix-Treffer", False

    ratio = difflib.SequenceMatcher(None, pos_text, item_text).ratio()
    jac = _jaccard(pos_text, item_text)
    score = max(ratio, jac)
    reason = "Textaehnlichkeit"
    review = False
    if item.einheit and position.einheit and item.einheit.lower() != position.einheit.lower():
        reason += f" | Einheit: {item.einheit} vs {position.einheit}"
        review = True
    return score, reason, review


class LocalProvider(BaseProvider):
    """Heuristisches Matching (NPK-Praefix + Textaehnlichkeit), rein stdlib."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def match(self, position: Position, pricelist: List[PriceItem]) -> MatchResult:
        best: Optional[PriceItem] = None
        best_score = 0.0
        best_reason = ""
        best_review = False

        for item in pricelist:
            score, reason, review = _score(item, position)
            # bei gleichem Score den spezifischeren (laengeren NPK-Prefix) bevorzugen
            if score > best_score or (abs(score - best_score) < 1e-9 and item.npk and (best is None or len(item.npk) > len(best.npk))):
                best_score = score
                best = item
                best_reason = reason
                best_review = review

        if best is None:
            return self._to_result(
                pos_id=position.pos_nr,
                item=None,
                score=0.0,
                review=True,
                begruendung="Keine Richtpreisliste / kein Treffer.",
            )

        review = best_review or best_score < self.threshold
        return self._to_result(
            pos_id=position.pos_nr,
            item=best,
            score=best_score,
            review=review,
            begruendung=f"Lokales Match auf '{best.bezeichnung}' ({best_reason}, Score {best_score:.2f}).",
        )
