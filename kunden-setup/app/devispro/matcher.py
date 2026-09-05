"""Matcher: Delegiert das NPK-Matching an einen Provider.

Unterstuetzt 'local' (Heuristik), 'mock' (KI-imitiert, out-of-the-box) und
'llm' (echter Claude/Abacus.ai-Adapter, benoetigt API-Key).
"""
from .providers import get_provider
from .providers.base import MatchResult


class Matcher:
    def __init__(self, provider=None, method: str = "local", threshold: float = 0.6):
        self.provider = provider or get_provider(method, threshold=threshold)
        self.method = getattr(self.provider, "__class__", type(self.provider)).__name__

    def match(self, position, pricelist) -> MatchResult:
        return self.provider.match(position, pricelist)
