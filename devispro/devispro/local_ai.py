"""Lokale KI mit llama.cpp (llama-cpp-python) — Offline, DSGVO-sicher.

Model Manager: Download/Verify via HuggingFace (llama3.1:8b, phi3:3.8b, qwen2.5:14b).
chat_completion(prompt, model, temp) → stream.
Prompt Templates: margen_live(position), text_to_devis(email/pdf), preis_optimierung(history).
Fallback: OpenRouter wenn Ollama/lokales Model nicht läuft.
"""

from __future__ import annotations

import os
import json
import logging
import hashlib
import threading
from pathlib import Path
from typing import Optional, Iterator, Dict, Any, List, Literal
from dataclasses import dataclass
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Optional imports — lazy loaded
_llama_cpp = None
_hf_hub = None
_requests = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model Registry
# ---------------------------------------------------------------------------

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "llama3.1:8b": {
        "repo_id": "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.7,
        "ctx": 8192,
        "description": "Meta Llama 3.1 8B Instruct — stark in Code & Reasoning",
    },
    "phi3:3.8b": {
        "repo_id": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "filename": "Phi-3-mini-4k-instruct-q4.gguf",
        "size_gb": 2.3,
        "ctx": 4096,
        "description": "Microsoft Phi-3 Mini — schnell, wenig VRAM",
    },
    "qwen2.5:14b": {
        "repo_id": "lmstudio-community/Qwen2.5-14B-Instruct-GGUF",
        "filename": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "size_gb": 8.2,
        "ctx": 32768,
        "description": "Qwen 2.5 14B — stark in Multilingual & Structured Output",
    },
}

DEFAULT_MODEL = "phi3:3.8b"  # klein, schnell, gut für CPU

# Model cache directory
CACHE_DIR = Path.home() / ".cache" / "devispro" / "models"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ModelInfo:
    name: str
    repo_id: str
    filename: str
    local_path: Path
    size_gb: float
    ctx: int
    downloaded: bool = False
    verified: bool = False


def _get_llama_cpp():
    """Lazy import llama_cpp"""
    global _llama_cpp
    if _llama_cpp is None:
        try:
            import llama_cpp
            _llama_cpp = llama_cpp
        except ImportError:
            raise RuntimeError(
                "llama-cpp-python nicht installiert. "
                "Installieren Sie es mit: pip install llama-cpp-python"
            )
    return _llama_cpp


def _get_hf_hub():
    """Lazy import huggingface_hub"""
    global _hf_hub
    if _hf_hub is None:
        try:
            from huggingface_hub import hf_hub_download
            _hf_hub = hf_hub_download
        except ImportError:
            raise RuntimeError(
                "huggingface_hub nicht installiert. "
                "Installieren Sie es mit: pip install huggingface_hub"
            )
    return _hf_hub


def _get_requests():
    """Lazy import requests for OpenRouter fallback"""
    global _requests
    if _requests is None:
        try:
            import requests
            _requests = requests
        except ImportError:
            raise RuntimeError(
                "requests nicht installiert für OpenRouter-Fallback. "
                "Installieren Sie es mit: pip install requests"
            )
    return _requests


# ---------------------------------------------------------------------------
# Model Manager
# ---------------------------------------------------------------------------

class ModelManager:
    """Verwaltet Download, Verifikation und Laden von GGUF-Modellen."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_model: Optional[Any] = None
        self._loaded_name: Optional[str] = None
        self._lock = threading.Lock()

    def list_available(self) -> List[str]:
        """Gibt Liste der registrierten Modell-Namen zurück."""
        return list(MODEL_REGISTRY.keys())

    def get_model_info(self, name: str) -> ModelInfo:
        """Erstellt ModelInfo für ein registriertes Modell."""
        if name not in MODEL_REGISTRY:
            raise ValueError(f"Unbekanntes Modell: {name}. Verfügbar: {self.list_available()}")
        reg = MODEL_REGISTRY[name]
        local_path = self.cache_dir / reg["filename"]
        return ModelInfo(
            name=name,
            repo_id=reg["repo_id"],
            filename=reg["filename"],
            local_path=local_path,
            size_gb=reg["size_gb"],
            ctx=reg["ctx"],
            downloaded=local_path.exists(),
            verified=self._verify_checksum(local_path) if local_path.exists() else False,
        )

    def _verify_checksum(self, path: Path) -> bool:
        """Einfache Größen-Prüfung (voller Checksum-Check optional)."""
        if not path.exists():
            return False
        # Mindestgröße prüfen (GGUF Header ~100KB + Tensoren)
        min_size = 100 * 1024
        return path.stat().st_size > min_size

    def download(self, name: str, progress_callback=None) -> Path:
        """Lädt Modell von HuggingFace herunter."""
        info = self.get_model_info(name)
        if info.downloaded and info.verified:
            logger.info(f"Modell {name} bereits vorhanden und verifiziert.")
            return info.local_path

        hf_hub_download = _get_hf_hub()

        logger.info(f"Lade {name} von {info.repo_id}...")

        try:
            # hf_hub_download handhabt Resume & Progress automatisch
            downloaded_path = hf_hub_download(
                repo_id=info.repo_id,
                filename=info.filename,
                local_dir=self.cache_dir,
                local_dir_use_symlinks=False,
            )
            path = Path(downloaded_path)

            if not self._verify_checksum(path):
                raise RuntimeError(f"Download verfehlt Größenprüfung: {path}")

            logger.info(f"Modell {name} erfolgreich heruntergeladen: {path}")
            if progress_callback:
                progress_callback(1.0, "Fertig")
            return path

        except Exception as e:
            logger.error(f"Download fehlgeschlagen für {name}: {e}")
            raise

    def load(self, name: str = DEFAULT_MODEL, n_ctx: Optional[int] = None, n_gpu_layers: int = -1) -> Any:
        """Lädt Modell in llama.cpp (Thread-safe, Singleton pro Instanz)."""
        with self._lock:
            if self._loaded_name == name and self._loaded_model is not None:
                return self._loaded_model

            info = self.get_model_info(name)
            if not info.downloaded:
                self.download(name)

            llama_cpp = _get_llama_cpp()
            ctx = n_ctx or info.ctx

            logger.info(f"Lade {name} in llama.cpp (ctx={ctx}, gpu_layers={n_gpu_layers})...")

            self._loaded_model = llama_cpp.Llama(
                model_path=str(info.local_path),
                n_ctx=ctx,
                n_gpu_layers=n_gpu_layers,  # -1 = alle auf GPU (Metal auf macOS)
                verbose=False,
                use_mmap=True,
                use_mlock=False,
            )
            self._loaded_name = name
            logger.info(f"Modell {name} geladen.")
            return self._loaded_model

    def unload(self):
        """Entlädt aktuelles Modell (Speicher freigeben)."""
        with self._lock:
            self._loaded_model = None
            self._loaded_name = None


# Global Model Manager Instance
_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Gibt den globalen ModelManager zurück."""
    return _model_manager


# ---------------------------------------------------------------------------
# Chat Completion — Streaming
# ---------------------------------------------------------------------------

def chat_completion(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    stream: bool = True,
    system_prompt: Optional[str] = None,
    n_ctx: Optional[int] = None,
) -> Iterator[str]:
    """
    Führt Chat-Completion mit lokalem llama.cpp Modell aus.

    Args:
        prompt: User-Prompt
        model: Modell-Name aus MODEL_REGISTRY
        temperature: Sampling-Temperatur (0.0-1.0)
        max_tokens: Maximale Antwort-Länge
        stream: True für Token-Stream, False für komplette Antwort
        system_prompt: Optionaler System-Prompt
        n_ctx: Context-Window Override

    Yields:
        Text-Chunks (bei stream=True) oder komplette Antwort (stream=False)
    """
    llama = get_model_manager().load(model, n_ctx=n_ctx)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        if stream:
            for chunk in llama.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            ):
                delta = chunk["choices"][0]["delta"]
                if "content" in delta and delta["content"]:
                    yield delta["content"]
        else:
            result = llama.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            yield result["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"chat_completion Fehler: {e}")
        # Fallback to OpenRouter
        yield from _openrouter_fallback(prompt, model, temperature, max_tokens, system_prompt, stream)


# ---------------------------------------------------------------------------
# OpenRouter Fallback
# ---------------------------------------------------------------------------

_OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
_OPENROUTER_MODEL_MAP = {
    "llama3.1:8b": "meta-llama/llama-3.1-8b-instruct",
    "phi3:3.8b": "microsoft/phi-3-mini-4k-instruct",
    "qwen2.5:14b": "qwen/qwen-2.5-14b-instruct",
}


def _openrouter_fallback(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    system_prompt: Optional[str],
    stream: bool,
) -> Iterator[str]:
    """Fallback auf OpenRouter API wenn lokales Modell fehlschlägt."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        yield "\n[Fehler: Kein lokales Modell verfügbar und OPENROUTER_API_KEY nicht gesetzt.]"
        return

    or_model = _OPENROUTER_MODEL_MAP.get(model, "meta-llama/llama-3.1-8b-instruct")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://devispro.ch",
        "X-Title": "DevisPro Local AI",
    }

    payload = {
        "model": or_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    requests = _get_requests()

    try:
        resp = requests.post(_OPENROUTER_API, headers=headers, json=payload, stream=stream, timeout=60)
        resp.raise_for_status()

        if stream:
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError):
                        continue
        else:
            data = resp.json()
            yield data["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"OpenRouter Fallback fehlgeschlagen: {e}")
        yield f"\n[OpenRouter Fehler: {e}]"


# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_DEVISSPEZIALIST = """Du bist ein erfahrener Schweizer Baukalkulator und DevisPro-Experte.
Du kennst SIA-451, NPK, kantonale Baukosten-Indizes (NPK), Margen-Copilot, Benchmark-Netzwerk.
Antworte präzise, praxisnah und auf Deutsch. Nutze CH-Zahlenformat (Tausender ' = ')."""

PROMPT_MARGEN_LIVE = """Analysiere diese Devis-Position auf Marge & Marktpreis:

Position: {pos_nr}
Text: {text}
Einheitspreis: {ep} CHF/{einheit}
Menge: {menge} {einheit}
Kanton: {kanton}
Kategorie: {kategorie}

Vergleiche mit dem anonymen Marktpreis-Netzwerk (Benchmark).
Gib kurz zurück:
1. Status: 🔴 zu tief / 🟢 ok / 🟡 zu hoch
2. Marktpreis (ca.): X CHF/{einheit}
3. Empfehlung: Ein Satz, was der KMU tun soll.

Antwort formatiert, knapp."""


PROMPT_TEXT_TO_DEVIS = """Extrahiere Devis-Positionen aus diesem Text (E-Mail, PDF-Text, Ausschreibung).

Text:
{text}

Erzeuge eine JSON-Liste von Positionen im Format:
[
  {{"pos_nr": "0901.010", "text": "Betonabbruch, Stärke bis 20cm", "menge": 45.0, "einheit": "m2", "ep_chf": null, "kategorie": "Abbruch"}},
  ...
]

Regeln:
- Pos-Nr nach SIA-451 Schema (NPK-konform wenn möglich)
- Menge & Einheit realistisch schätzen falls nicht explizit
- ep_chf = null (wird später über Firmenpreise/Benchmark befüllt)
- Kategorie: Erdbau/Beton, Mauerwerk/Gips, Elektro, Sanitär, Maler, Dach/Isolation, Boden/Platten, Fenster/Türen, Allgemein
- Nur echte Positionen, keine Kopfzeilen/Summen

Antwort: NUR das JSON-Array, keine Erklärungen."""


PROMPT_PREIS_OPTIMIERUNG = """Optimiere Preise basierend auf Historien-Daten.

Historische Devis-Positionen (letzte 20):
{history}

Aktuelle Position zum Prüfen:
- Pos-Nr: {pos_nr}
- Text: {text}
- Aktueller EP: {ep} CHF/{einheit}
- Menge: {menge} {einheit}
- Kanton: {kanton}

Analysiere:
1. Wie oft kam ähnliche Position vor? (Durchschnitts-EP, Streuung)
2. Marge-Trend: Steigen/fallend über Zeit?
3. Empfohlener EP für aktuelle Marktsituation
4. Risiko: Zu tief (Verlust) / Zu hoch (Auftragsrisiko)

Antwort: JSON mit Keys: empfohlener_ep, confidence (0-1), begruendung, risiko (niedrig/mittel/hoch)"""


def get_prompt_margen_live(position: Dict[str, Any], kanton: str = "ZH") -> str:
    """Erstellt Prompt für Live-Margen-Analyse einer Position."""
    kat = _kategorie_from_text(position.get("text", ""))
    return PROMPT_MARGEN_LIVE.format(
        pos_nr=position.get("pos_nr", ""),
        text=position.get("text", ""),
        ep=position.get("ep", 0),
        einheit=position.get("einheit", "-"),
        menge=position.get("menge", 0),
        kanton=kanton,
        kategorie=kat,
    )


def get_prompt_text_to_devis(text: str) -> str:
    """Erstellt Prompt für Text→Devis Extraktion."""
    return PROMPT_TEXT_TO_DEVIS.format(text=text[:8000])  # begrenzen


def get_prompt_preis_optimierung(
    history: List[Dict[str, Any]],
    position: Dict[str, Any],
    kanton: str = "ZH",
) -> str:
    """Erstellt Prompt für Preis-Optimierung basierend auf Historie."""
    # History auf letzten 20 Einträge kürzen & komprimieren
    hist_text = "\n".join(
        f"- {h.get('pos_nr','')}: {h.get('text','')[:40]} | EP: {h.get('ep',0)} {h.get('einheit','')} | {h.get('datum','')}"
        for h in history[-20:]
    )
    return PROMPT_PREIS_OPTIMIERUNG.format(
        history=hist_text,
        pos_nr=position.get("pos_nr", ""),
        text=position.get("text", ""),
        ep=position.get("ep", 0),
        einheit=position.get("einheit", "-"),
        menge=position.get("menge", 0),
        kanton=kanton,
    )


def _kategorie_from_text(text: str) -> str:
    """Einfache Kategorisierung wie in margen_copilot.py"""
    t = (text or "").lower()
    if any(w in t for w in ("beton", "fundament", "erdbau", "abtra")):
        return "Erdbau/Beton"
    if any(w in t for w in ("mauer", "wand", "gips", "putz")):
        return "Mauerwerk/Gips"
    if any(w in t for w in ("elektro", "kabel", "strom", "steck")):
        return "Elektro"
    if any(w in t for w in ("sanit", "wasser", "abfluss", "rohr")):
        return "Sanitär"
    if any(w in t for w in ("anstrich", "farbe", "lack", "maler")):
        return "Maler"
    if any(w in t for w in ("dach", "ziegel", "isolier")):
        return "Dach/Isolation"
    if any(w in t for w in ("boden", "platten", "flies", "parkett")):
        return "Boden/Platten"
    if any(w in t for w in ("fenster", "tuer")):
        return "Fenster/Türen"
    return "Allgemein"


# ---------------------------------------------------------------------------
# High-Level API Functions
# ---------------------------------------------------------------------------

def margen_live_indicator(position: Dict[str, Any], kanton: str = "ZH") -> Dict[str, Any]:
    """
    Live-Indikator für eine Position: rot/grün/gelb + Marktpreis + Empfehlung.
    Nutzt lokales LLM (streaming) oder OpenRouter-Fallback.
    """
    prompt = get_prompt_margen_live(position, kanton)

    # Streaming-Response sammeln
    full_response = ""
    for chunk in chat_completion(
        prompt,
        model=DEFAULT_MODEL,
        temperature=0.1,
        max_tokens=512,
        stream=True,
        system_prompt=SYSTEM_PROMPT_DEVISSPEZIALIST,
    ):
        full_response += chunk

    # Parse response (einfaches Parsing, da Format fix vorgegeben)
    return _parse_margen_response(full_response, position)


def _parse_margen_response(response: str, position: Dict[str, Any]) -> Dict[str, Any]:
    """Parst die LLM-Antwort für margen_live."""
    result = {
        "status": "🟢 ok",
        "marktpreis": None,
        "empfehlung": "",
        "raw": response.strip(),
    }

    lines = response.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("1.") or "Status" in line or "status" in line.lower():
            if "zu tief" in line.lower() or "🔴" in line:
                result["status"] = "🔴 zu tief"
            elif "zu hoch" in line.lower() or "🟡" in line:
                result["status"] = "🟡 zu hoch"
            elif "ok" in line.lower() or "🟢" in line:
                result["status"] = "🟢 ok"
        elif "marktpreis" in line.lower() or "2." in line:
            # Extrahiere Zahl
            import re
            m = re.search(r"(\d+[.,]?\d*)", line)
            if m:
                result["marktpreis"] = float(m.group(1).replace(",", "."))
        elif "empfehlung" in line.lower() or "3." in line:
            result["empfehlung"] = line.split(":", 1)[-1].strip() if ":" in line else line

    return result


def text_to_devis_positions(text: str) -> List[Dict[str, Any]]:
    """
    Extrahiert Devis-Positionen aus freiem Text (E-Mail, PDF, Ausschreibung).
    Rückgabe: Liste von Position-Dicts für direkten Import.
    """
    prompt = get_prompt_text_to_devis(text)

    full_response = ""
    for chunk in chat_completion(
        prompt,
        model=DEFAULT_MODEL,
        temperature=0.1,
        max_tokens=2048,
        stream=True,
        system_prompt=SYSTEM_PROMPT_DEVISSPEZIALIST,
    ):
        full_response += chunk

    return _parse_devis_positions(full_response)


def _parse_devis_positions(response: str) -> List[Dict[str, Any]]:
    """Parst JSON-Array aus LLM-Antwort."""
    import re
    # Finde JSON-Array in der Antwort
    match = re.search(r"\[.*\]", response, re.DOTALL)
    if not match:
        logger.warning(f"Kein JSON-Array in Antwort gefunden: {response[:200]}")
        return []

    try:
        positions = json.loads(match.group(0))
        # Validierung & Defaults
        validated = []
        for p in positions:
            if not isinstance(p, dict):
                continue
            validated.append({
                "pos_nr": str(p.get("pos_nr", "")).strip() or "(auto)",
                "text": str(p.get("text", "")).strip(),
                "menge": float(p.get("menge", 0) or 0),
                "einheit": str(p.get("einheit", "")).strip() or "St.",
                "ep": None,  # wird später befüllt
                "kategorie": str(p.get("kategorie", "")).strip() or "Allgemein",
            })
        return validated
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parse Fehler: {e}")
        return []


def preis_optimierung(
    history: List[Dict[str, Any]],
    position: Dict[str, Any],
    kanton: str = "ZH",
) -> Dict[str, Any]:
    """
    Preis-Optimierung basierend auf historischer Datenbasis.
    Rückgabe: Dict mit empfohlener_ep, confidence, begruendung, risiko.
    """
    prompt = get_prompt_preis_optimierung(history, position, kanton)

    full_response = ""
    for chunk in chat_completion(
        prompt,
        model=DEFAULT_MODEL,
        temperature=0.1,
        max_tokens=1024,
        stream=True,
        system_prompt=SYSTEM_PROMPT_DEVISSPEZIALIST,
    ):
        full_response += chunk

    return _parse_preis_optimierung(full_response)


def _parse_preis_optimierung(response: str) -> Dict[str, Any]:
    """Parst JSON-Antwort für Preis-Optimierung."""
    import re
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        return {
            "empfohlener_ep": None,
            "confidence": 0.0,
            "begruendung": "Parsing fehlgeschlagen",
            "risiko": "mittel",
            "raw": response.strip(),
        }

    try:
        data = json.loads(match.group(0))
        return {
            "empfohlener_ep": float(data.get("empfohlener_ep", 0) or 0),
            "confidence": float(data.get("confidence", 0) or 0),
            "begruendung": str(data.get("begruendung", "")).strip(),
            "risiko": str(data.get("risiko", "mittel")).strip().lower(),
            "raw": response.strip(),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Preis-Optimierung Parse Fehler: {e}")
        return {
            "empfohlener_ep": None,
            "confidence": 0.0,
            "begruendung": f"Parse-Fehler: {e}",
            "risiko": "mittel",
            "raw": response.strip(),
        }


# ---------------------------------------------------------------------------
# Convenience: Quick-Test Funktion
# ---------------------------------------------------------------------------

def quick_test(model: str = DEFAULT_MODEL) -> str:
    """Schnelltest: Lädt Modell und generiert Test-Antwort."""
    test_prompt = "Nenne mir 3 typische SIA-451 Positionen für 'Betonabbruch' mit Einheit und ca. EP."
    result = ""
    for chunk in chat_completion(test_prompt, model=model, temperature=0.1, max_tokens=256, stream=True):
        result += chunk
    return result


if __name__ == "__main__":
    # Demo-Test beim direkten Ausführen
    import sys
    logging.basicConfig(level=logging.INFO)

    print("=== DevisPro Local AI - Quick Test ===")
    print(f"Verfügbare Modelle: {get_model_manager().list_available()}")
    print(f"Cache: {CACHE_DIR}")
    print()

    # Test Model Manager
    mgr = get_model_manager()
    for name in mgr.list_available():
        info = mgr.get_model_info(name)
        print(f"  {name}: {info.size_gb}GB, ctx={info.ctx}, dl={info.downloaded}, verified={info.verified}")

    print("\n--- Test chat_completion (phi3:3.8b) ---")
    try:
        resp = quick_test("phi3:3.8b")
        print(resp[:500])
    except Exception as e:
        print(f"Fehler (erwartet ohne Modell-Download): {e}")