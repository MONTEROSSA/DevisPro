"""Abo-/Tarif-Modell fuer DevisPro.

Zwei Produkte, jeweils mit zwei Zahlarten:
  - DevisPro            (Basis)
  - DevisPro & ERP      (mit ERP-Connector Abacus/Proffix)

Pro Produkt: Einmalzahlung (Vollversion) ODER monatlich mieten.
Aktiver Tarif ueber data/abo.json (vom Anbieter pro Kunde gesetzt).
Fallback: DevisPro Einmalzahlung wenn keine abo.json vorhanden.
"""

import os
import json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
ABO_PFAD = os.path.join(DATA, "abo.json")

# Zwei Stufen: Basis-Produkt (DevisPro) + optionales Add-on (ERP-Connector).
# Bundle "DevisPro & ERP" = Basis + Add-on (Preise werden addiert).
# Regel: Kaufen (einmalig + Support) ist im 1. Jahr guenstiger als Mieten (12x Monat),
#        und ab Jahr 2 nur noch Support faellig.
PRODUKTE = {
    "devispro": {
        "name": "DevisPro",
        "einmal_chf": 2400, "support_jahr": 990, "miete_chf": 350,
        "einmal_intervall": "einmalig + 990/Jahr Support", "miete_intervall": "Monat",
        "features": ["bepreisung", "margen_copilot", "check_gratis", "formate_basis",
                     "benchmark_netzwerk", "alle_formate", "qr_rechnung",
                     "formate_crbx", "rechnung"],
    },
    "erp_connector": {
        "name": "ERP-Modul",
        "kurz": "Schnittstelle zu Abacus/Proffix plus Mahnwesen, Teilrechnungen, White-Label",
        "einmal_chf": 1900, "support_jahr": 490, "miete_chf": 248,
        "einmal_intervall": "einmalig + 490/Jahr Support", "miete_intervall": "Monat",
        "features": ["connector_abacus", "connector_proffix", "mahnung",
                     "white_label", "teilrechnung"],
    },
}

# Anzeige-Reihenfolge der beiden Verkaufsprodukte
ANZEIGE_PRODUKTE = ["devispro", "devispro_erp"]


def _bundle(prod: str) -> dict:
    """Liefert die Anzeige-Daten eines Verkaufsprodukts (Basis oder Bundle)."""
    if prod == "devispro":
        b = PRODUKTE["devispro"]
        return {"key": "devispro", "name": b["name"],
                "einmal_chf": b["einmal_chf"], "support_jahr": b["support_jahr"],
                "miete_chf": b["miete_chf"],
                "einmal_intervall": b["einmal_intervall"], "miete_intervall": b["miete_intervall"],
                "features": list(b["features"])}
    if prod == "devispro_erp":
        b = PRODUKTE["devispro"]; a = PRODUKTE["erp_connector"]
        feats = list(dict.fromkeys(b["features"] + a["features"]))
        return {"key": "devispro_erp", "name": "DevisPro & ERP",
                "einmal_chf": b["einmal_chf"] + a["einmal_chf"],
                "support_jahr": b["support_jahr"] + a["support_jahr"],
                "miete_chf": b["miete_chf"] + a["miete_chf"],
                "einmal_intervall": f"einmalig + {b['support_jahr'] + a['support_jahr']}/Jahr Support",
                "miete_intervall": "Monat",
                "features": feats,
                "komponenten": {"devispro": b, "erp_connector": a}}
    return _bundle("devispro")


def laden() -> dict:
    if os.path.exists(ABO_PFAD):
        try:
            return json.load(open(ABO_PFAD, encoding="utf-8"))
        except Exception:
            pass
    return {"produkt": "devispro", "zahlart": "einmal", "seit": "", "kunde_id": ""}


def tarif_key() -> tuple:
    d = laden()
    return d.get("produkt", "devispro"), d.get("zahlart", "einmal")


def ist_erp() -> bool:
    return tarif_key()[0] == "devispro_erp"


def tarif_features() -> set:
    prod, _ = tarif_key()
    if prod in PRODUKTE:
        return set(PRODUKTE[prod]["features"])
    return set(_bundle(prod)["features"])


def darf(feature: str) -> bool:
    return feature in tarif_features()


def info() -> dict:
    prod, zahl = tarif_key()
    if prod in PRODUKTE:
        p = PRODUKTE[prod]
        name = p["name"]
        einmal_chf = p["einmal_chf"]; intervall = p["einmal_intervall"]
        miete_chf = p["miete_chf"]; miete_interv = p["miete_intervall"]
        feats = list(p["features"])
    else:
        b = _bundle(prod)
        name = b["name"]
        einmal_chf = b["einmal_chf"]; intervall = b["einmal_intervall"]
        miete_chf = b["miete_chf"]; miete_interv = b["miete_intervall"]
        feats = list(b["features"])
    if zahl == "miete":
        return {"produkt": prod, "name": name, "zahlart": "miete",
                "preis_chf": miete_chf, "intervall": miete_interv,
                "features": feats}
    return {"produkt": prod, "name": name, "zahlart": "einmal",
            "preis_chf": einmal_chf, "intervall": intervall,
            "features": feats}


def setze_tarif(kunde_id: str, produkt: str = None, zahlart: str = "einmal",
               tarif: str = None, seit: str = "") -> dict:
    # Abwaertskompatibel: alte Signatur setze_tarif(kunde_id, tarif="devispro")
    if tarif is not None and produkt is None:
        produkt = tarif
    if produkt not in PRODUKTE and produkt not in ANZEIGE_PRODUKTE:
        return {"ok": False, "fehler": "Unbekanntes Produkt"}
    if zahlart not in ("einmal", "miete"):
        return {"ok": False, "fehler": "Unbekannte Zahlart"}
    neu = {"produkt": produkt, "zahlart": zahlart, "kunde_id": kunde_id, "seit": seit}
    with open(ABO_PFAD, "w", encoding="utf-8") as f:
        json.dump(neu, f, indent=2, ensure_ascii=False)
    return {"ok": True, **neu}
