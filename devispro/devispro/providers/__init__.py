"""Provider-Basis für den Matcher (Preislisten-Abgleich).

Lokaler Heuristik-Provider: gleicht Devis-Positionen gegen die
KMU-Richtpreisliste ab (Text-Ähnlichkeit + Einheit). Keine externe API nötig.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class MatchResult:
    matched_artikel_id: str = ""
    confidence: float = 0.0
    requires_review: bool = False
    hinweis: str = ""


class BaseProvider:
    name = "base"

    def match(self, position, pricelist):
        raise NotImplementedError


def _norm(text):
    import re
    return re.sub(r"\s+", " ", (text or "").lower().strip())


class LocalProvider(BaseProvider):
    name = "local"

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def match(self, position, pricelist):
        a = _norm(getattr(position, "text", "") or "")
        best = None
        best_score = 0.0
        for item in pricelist:
            b = _norm(getattr(item, "bezeichnung", "") or getattr(item, "text", "") or "")
            if not a or not b:
                continue
            score = SequenceMatcher(None, a, b).ratio()
            if score > best_score:
                best_score = score
                best = item
        if best is None or best_score < self.threshold:
            return MatchResult(requires_review=True,
                               hinweis="kein ausreichend ähnlicher Artikel gefunden")
        return MatchResult(
            matched_artikel_id=getattr(best, "artikel_id", "") or getattr(best, "bkp", ""),
            confidence=round(best_score, 2),
            requires_review=best_score < 0.85,
            hinweis=f"Übereinstimmung {best_score:.0%}",
        )


def get_provider(method: str = "local", threshold: float = 0.6):
    if method in ("mock", "llm", "local"):
        return LocalProvider(threshold=threshold)
    return LocalProvider(threshold=threshold)
