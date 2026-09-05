"""Abo-/Tarif-Modell fuer DevisPro.

Ergaenzt die einmalige Lizenz (license.py) um wiederkehrende Tarife.
Konfigurierbar ueber data/abo.json (vom Anbieter pro Kunde gesetzt).
Fallback: Hybrid-Tarif (alt) wenn keine abo.json vorhanden.

Tarife:
  starter   : 89 CHF/Monat  – Bepreisung + Margen-Copilot, 1 Gewerk
  pro       : 149 CHF/Monat – + Benchmark-Netzwerk, alle Formate, QR-Rechnung
  premium   : 249 CHF/Monat – + ERP-Connector (Abacus/Proffix), Mahnung, White-Label

Feature-Gating ueber tarif_features() -> set von Schluesseln.
"""
import os
import json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
ABO_PFAD = os.path.join(DATA, "abo.json")

TARIFE = {
    "starter": {
        "name": "Starter", "preis_chf": 89, "intervall": "Monat",
        "features": ["bepreisung", "margen_copilot", "check_gratis", "formate_basis"],
    },
    "pro": {
        "name": "Pro", "preis_chf": 149, "intervall": "Monat",
        "features": ["bepreisung", "margen_copilot", "benchmark_netzwerk", "alle_formate",
                     "qr_rechnung", "check_gratis", "formate_crbx", "rechnung"],
    },
    "premium": {
        "name": "Premium", "preis_chf": 249, "intervall": "Monat",
        "features": ["bepreisung", "margen_copilot", "benchmark_netzwerk", "alle_formate",
                     "qr_rechnung", "check_gratis", "formate_crbx", "rechnung",
                     "connector_abacus", "connector_proffix", "mahnung", "white_label",
                     "teilrechnung"],
    },
}

# Abwaertskompatibel: Einmalkauf 2'400 + 990/Jahr hat alle Features ausser connector/white_label
HYBRID_FEATURES = set()
for t in TARIFE.values():
    HYBRID_FEATURES.update(t["features"])
HYBRID_FEATURES.update({"connector_abacus", "connector_proffix", "mahnung", "white_label"})


def laden() -> dict:
    if os.path.exists(ABO_PFAD):
        try:
            return json.load(open(ABO_PFAD, encoding="utf-8"))
        except Exception:
            pass
    return {"tarif": "hybrid", "seit": "", "kunde_id": ""}


def tarif_key() -> str:
    return laden().get("tarif", "hybrid")


def ist_premium() -> bool:
    return tarif_key() in ("premium", "hybrid")


def tarif_features() -> set:
    key = tarif_key()
    if key == "hybrid":
        return set(HYBRID_FEATURES)
    return set(TARIFE.get(key, {}).get("features", []))


def darf(feature: str) -> bool:
    return feature in tarif_features()


def info() -> dict:
    key = tarif_key()
    if key == "hybrid":
        return {"tarif": "hybrid", "name": "Vollversion (Einmalzahlung)",
                "preis_chf": 2400, "intervall": "einmalig + 990/Jahr",
                "features": sorted(HYBRID_FEATURES)}
    t = TARIFE.get(key, TARIFE["starter"])
    return {"tarif": key, "name": t["name"], "preis_chf": t["preis_chf"],
            "intervall": t["intervall"], "features": t["features"]}


def setze_tarif(kunde_id: str, tarif: str, seit: str = "") -> dict:
    if tarif not in TARIFE and tarif != "hybrid":
        return {"ok": False, "fehler": "Unbekannter Tarif"}
    neu = {"tarif": tarif, "kunde_id": kunde_id, "seit": seit}
    with open(ABO_PFAD, "w", encoding="utf-8") as f:
        json.dump(neu, f, indent=2, ensure_ascii=False)
    return {"ok": True, **neu}
