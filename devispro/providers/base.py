from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from ..models import Position
from ..pricelist import PriceItem


@dataclass
class MatchResult:
    pos_id: str
    matched_artikel_id: Optional[str]
    einheitspreis_chf: Optional[float]
    confidence: float
    requires_review: bool
    begruendung: str


class BaseProvider(ABC):
    @abstractmethod
    def match(self, position: Position, pricelist: List[PriceItem]) -> MatchResult:
        ...

    @staticmethod
    def _to_result(*, pos_id, item, score, review, begruendung):
        return MatchResult(
            pos_id=pos_id,
            matched_artikel_id=item.artikel_id if item else None,
            einheitspreis_chf=item.ep_chf if item else None,
            confidence=round(score, 2),
            requires_review=review,
            begruendung=begruendung,
        )
