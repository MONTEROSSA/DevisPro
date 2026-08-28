"""Provider-Paket: LP fuer das NPK-Matching (lokal, Mock-KI, HTTP-LLM)."""
from .base import BaseProvider, MatchResult
from .local import LocalProvider
from .mock import MockProvider
from .http_llm import HttpLlmProvider


def get_provider(name: str, **kwargs):
    name = (name or "local").lower()
    if name == "local":
        return LocalProvider(threshold=kwargs.get("threshold", 0.6))
    if name == "mock":
        return MockProvider(threshold=kwargs.get("threshold", 0.6))
    if name in ("llm", "http", "claude", "abacus"):
        return HttpLlmProvider(
            api_key=kwargs.get("api_key"),
            model=kwargs.get("model", "claude-3-5-sonnet-latest"),
        )
    raise ValueError(f"Unbekannter Provider: {name}")
