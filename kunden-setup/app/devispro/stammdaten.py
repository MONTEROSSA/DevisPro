"""Persistente Stammdaten eines Betriebs.

Einmal eingeben -> bleibt in data/ gespeichert und wird fuer jedes neue
Devis automatisch verwendet (kein erneuter Upload noetig).
"""
import os
import json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /devis-auto (Root mit data/)
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

PROFILE_PATH = os.path.join(DATA, "profil.json")
PREISE_PATH = os.path.join(DATA, "meine_preise.csv")


def default_profile() -> dict:
    return {
        "betrieb": "Malergeschäft Muster AG",
        "gewerk": "Maler",
        "stundenlohn_chf": 82.0,        # Lohn + Lohnnebenkosten, marktueblich CH
        "material_aufschlag_pct": 12.0, # Aufschlag auf Materialeinkauf
        "gemeinkosten_pct": 10.0,       # BK, Miete, Auto, Versicherung
        "gewinn_pct": 8.0,              # Unternehmerlohn/Gewinn
        "mwst_pct": 8.1,
    }


def save_profile(profile: dict) -> None:
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def load_profile() -> dict:
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return default_profile()


def save_prices_csv(content: str) -> None:
    with open(PREISE_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def load_prices_csv() -> str:
    if os.path.exists(PREISE_PATH):
        with open(PREISE_PATH, encoding="utf-8") as f:
            return f.read()
    return ""


def prices_exist() -> bool:
    return os.path.exists(PREISE_PATH) and os.path.getsize(PREISE_PATH) > 0
