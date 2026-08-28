from typing import List

from ..models import Position
from ..pricelist import PriceItem
from .base import MatchResult
from .local import LocalProvider


class MockProvider(LocalProvider):
    """Imitiert den KI-Agenten (Abacus.ai/Claude) lokal.

    Liefert dasselbe JSON-Format wie der HTTP-Provider, damit die Pipeline ohne
    API-Key sofort laeuft und der Wechsel zu echtem LLM transparent ist.
    Die Begruendung ist etwas ausfuehrlicher formuliert (KI-Stil).
    """

    def match(self, position: Position, pricelist: List[PriceItem]) -> MatchResult:
        res = super().match(position, pricelist)
        if res.matched_artikel_id:
            res.begruendung = (
                f"KI-Matching: Position '{position.text}' wurde dem Richtpreis "
                f"'{res.matched_artikel_id}' zugeordnet "
                f"(Confidence {res.confidence:.2f}). {res.begruendung}"
            )
        else:
            res.begruendung = (
                f"KI-Matching: Kein ausreichend aehnlicher Richtpreis fuer "
                f"'{position.text}' gefunden. Manuelle Kalkulation noetig "
                f"(Confidence {res.confidence:.2f})."
            )
        return res
