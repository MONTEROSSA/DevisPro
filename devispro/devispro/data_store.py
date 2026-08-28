"""Zentraler, persistenter Datenspeicher fuer DevisPro.

WICHTIG: Alle Nutzerdaten (Profil, Preisliste, Verlauf, Kunden) liegen
ausserhalb des App-Bundles, damit sie beim Update nicht verloren gehen
und das Codesign-Siegel des Bundles intakt bleibt.

Speicherort: ~/Library/Application Support/DevisPro  (macOS)
            bzw. ~/.devispro  (fallback / andere OS)
"""
import os
import json
import platform


def app_support_dir() -> str:
    """Liefert das DevisPro-Datenverzeichnis (anlegt falls noetig)."""
    if platform.system() == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/DevisPro")
    else:
        base = os.path.expanduser("~/.devispro")
    os.makedirs(base, exist_ok=True)
    return base


def path(*parts) -> str:
    """Baut einen Pfad im Datenverzeichnis."""
    return os.path.join(app_support_dir(), *parts)


# --- Dateipfade ------------------------------------------------------------
PROFILE_PATH = path("profil.json")
PREISE_PATH = path("meine_preise.csv")
NPK_PATH = path("npk_preise.csv")
KUNDEN_PATH = path("kunden.json")
VERLAUF_PATH = path("verlauf.json")
LOGO_PATH = path("logo.png")


def _read_json(p, default):
    try:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    except (OSError, ValueError):
        pass
    return default


def _write_json(p, obj) -> None:
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
