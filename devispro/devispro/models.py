from dataclasses import dataclass
from typing import Optional


@dataclass
class Position:
    pos_nr: str
    text: str
    menge: float
    einheit: str
    ep: Optional[float] = None          # Einheitspreis (CHF)
    betrag: Optional[float] = None      # Menge x EP
    chapter: Optional[tuple] = None     # (level, number, title)
    matched_artikel: Optional[str] = None
    confidence: Optional[float] = None
    requires_review: bool = False
    begruendung: str = ""
    kategorie: Optional[str] = None      # Gewerk/Kategorie fuer Benchmark-Matching
    unbepreist: bool = False             # KEINE Preisquelle gefunden
    schaetzung: bool = False             # Preis ist CH-Referenzschaetzung (pruefen!)

    def fill(self) -> None:
        """Betrag aus EP und Menge berechnen (nur wenn bepreist)."""
        if self.ep is not None and self.menge is not None:
            self.betrag = round(self.ep * self.menge, 2)


@dataclass
class Devis:
    meta: dict          # version, currency, mwst, date, ...
    addresses: list     # [{'role','name','street','city'}, ...]
    chapters: list      # [(level, number, title), ...]
    positions: list     # [Position, ...]
