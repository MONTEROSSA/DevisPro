"""Basis-Klassen für Matcher-Provider."""

from dataclasses import dataclass


@dataclass
class MatchResult:
    matched_artikel_id: str = ""
    confidence: float = 0.0
    requires_review: bool = False
    hinweis: str = ""
