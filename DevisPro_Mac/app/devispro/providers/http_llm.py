import json
import os
from typing import List

from ..models import Position
from ..pricelist import PriceItem
from .base import BaseProvider, MatchResult
from ..prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


class HttpLlmProvider(BaseProvider):
    """Echter LLM-Provider (Claude via Anthropic Messages API oder Abacus.ai Proxy).

    Benoetigt einen API-Key in der Umgebungsvariable ANTHROPIC_API_KEY
    (bzw. ABACUS_API_KEY) oder per Parameter. Optional dependency: `requests`
    (installierbar via `pip install devispro[llm]`).
    """

    ENDPOINT = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str = None, model: str = "claude-3-5-sonnet-latest"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ABACUS_API_KEY")
        self.model = model

    def _pricelist_text(self, pricelist: List[PriceItem]) -> str:
        lines = []
        for it in pricelist:
            lines.append(f"{it.artikel_id} | {it.bezeichnung} | {it.npk} | {it.einheit} | {it.ep_chf}")
        return "\n".join(lines)

    def match(self, position: Position, pricelist: List[PriceItem]) -> MatchResult:
        if not self.api_key:
            raise RuntimeError(
                "HttpLlmProvider: Kein API-Key gefunden "
                "(setze ANTHROPIC_API_KEY oder ABACUS_API_KEY)."
            )

        import requests  # optional dependency

        user = USER_PROMPT_TEMPLATE.format(
            pos_id=position.pos_nr,
            text=position.text,
            menge=position.menge,
            einheit=position.einheit,
            pricelist_text=self._pricelist_text(pricelist),
        )
        payload = {
            "model": self.model,
            "max_tokens": 512,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        resp = requests.post(self.ENDPOINT, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        text = "".join(block.get("text", "") for block in resp.json().get("content", []))

        # JSON aus der Antwort extrahieren (robust gegen whitespace)
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return MatchResult(
            pos_id=data.get("pos_id", position.pos_nr),
            matched_artikel_id=data.get("matched_artikel_id"),
            einheitspreis_chf=data.get("einheitspreis_chf"),
            confidence=float(data.get("confidence", 0.0)),
            requires_review=bool(data.get("requires_review", False)),
            begruendung=data.get("begruendung", ""),
        )
