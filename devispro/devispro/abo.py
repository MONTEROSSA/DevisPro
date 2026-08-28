"""Abo-/Tarif-Modell fuer DevisPro.

Drei Tarife (Pay-per-Use / Monatlich / Enterprise):
  - Starter (Pay-per-Devis)     : CHF 89/Devis, 5er-Paket 395, 10er 690
  - Professional (Monatlich)    : CHF 350/Mt. alles inkl. ERP-Schnittstellen
  - Enterprise (Auf Anfrage)    : Team, API, SLA, White-Label, On-Prem

Aktiver Tarif ueber data/abo.json (vom Anbieter pro Kunde gesetzt).
Fallback: Starter (Pay-per-Devis) wenn keine abo.json vorhanden.

PREISMODELL v3 FINAL: Pay-per-Devis (Konzept A, B.3, C.4)
CHF 89 pro Devis; 5er-Paket 395 (=79/Stk), 10er-Paket 690 (=69/Stk);
ERP-Zuschlag CHF 49 pro exportiertem Devis im PPD-Tarif (Entscheidung 3).
"""

import os
import json

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
ABO_PFAD = os.path.join(DATA, "abo.json")

# Drei Tarife: Starter (PPD), Professional (Monatlich), Enterprise (Custom)
PRODUKTE = {
    "starter": {
        "name": "Starter",
        "modell": "pay_per_devis",
        "einzeln_chf": 89,
        "paket5_chf": 395,
        "paket10_chf": 690,
        "erp_zuschlag_chf": 49,
        "miete_chf": None,
        "einmal_chf": None,
        "support_jahr": None,
        "features": ["bepreisung", "margen_copilot", "check_gratis", "formate_basis",
                     "benchmark_netzwerk", "alle_formate", "qr_rechnung",
                     "formate_crbx", "rechnung"],
    },
    "professional": {
        "name": "Professional",
        "modell": "subscription",
        "miete_chf": 350,
        "einmal_chf": 2400,
        "support_jahr": 990,
        "einmal_intervall": "einmalig + 990/Jahr Support",
        "miete_intervall": "Monat",
        "erp_zuschlag_chf": 0,  # inklusive
        "features": ["bepreisung", "margen_copilot", "check_gratis", "formate_basis",
                     "benchmark_netzwerk", "alle_formate", "qr_rechnung",
                     "formate_crbx", "rechnung",
                     "connector_abacus", "connector_proffix", "mahnung",
                     "white_label", "teilrechnung",
                     "multiwährung", "mehrsprachig", "prio_support"],
    },
    "enterprise": {
        "name": "Enterprise",
        "modell": "custom",
        "miete_chf": None,  # auf Anfrage
        "einmal_chf": None,
        "support_jahr": None,
        "features": ["bepreisung", "margen_copilot", "check_gratis", "formate_basis",
                     "benchmark_netzwerk", "alle_formate", "qr_rechnung",
                     "formate_crbx", "rechnung",
                     "connector_abacus", "connector_proffix", "mahnung",
                     "white_label", "teilrechnung",
                     "multiwährung", "mehrsprachig", "prio_support",
                     "team_admin", "api_access", "sla", "on_prem_option",
                     "dedicated_support", "custom_integrations"],
    },
}

# Anzeige-Reihenfolge der drei Verkaufstarife
ANZEIGE_PRODUKTE = ["starter", "professional", "enterprise"]


def _produkt_anzeige(key: str) -> dict:
    """Liefert die Anzeige-Daten eines Tarifs."""
    p = PRODUKTE[key]
    base = {"key": key, "name": p["name"], "modell": p["modell"],
            "features": list(p["features"])}
    if p["modell"] == "pay_per_devis":
        base.update({
            "einzeln_chf": p["einzeln_chf"],
            "paket5_chf": p["paket5_chf"],
            "paket10_chf": p["paket10_chf"],
            "erp_zuschlag_chf": p["erp_zuschlag_chf"],
        })
    elif p["modell"] == "subscription":
        base.update({
            "miete_chf": p["miete_chf"],
            "einmal_chf": p["einmal_chf"],
            "support_jahr": p["support_jahr"],
            "einmal_intervall": p["einmal_intervall"],
            "miete_intervall": p["miete_intervall"],
            "erp_zuschlag_chf": p["erp_zuschlag_chf"],
        })
    else:  # enterprise/custom
        base.update({
            "miete_chf": None,
            "einmal_chf": None,
            "support_jahr": None,
            "erp_zuschlag_chf": 0,
            "auf_anfrage": True,
        })
    return base


def laden() -> dict:
    if os.path.exists(ABO_PFAD):
        try:
            return json.load(open(ABO_PFAD, encoding="utf-8"))
        except Exception:
            pass
    # Default: Starter (Pay-per-Devis)
    return {"produkt": "starter", "zahlart": "pay_per_devis", "seit": "", "kunde_id": ""}


def tarif_key() -> tuple:
    d = laden()
    return d.get("produkt", "starter"), d.get("zahlart", "pay_per_devis")


def ist_erp() -> bool:
    """True wenn Professional oder Enterprise (ERP-Schnittstellen inklusive)."""
    prod, _ = tarif_key()
    return prod in ("professional", "enterprise")


def tarif_features() -> set:
    prod, _ = tarif_key()
    return set(PRODUKTE.get(prod, {}).get("features", []))


def darf(feature: str) -> bool:
    return feature in tarif_features()


# --- PREISMODELL v3 FINAL: Pay-per-Devis (Konzept A, B.3, C.4) -------------
# CHF 89 pro Devis; 5er-Paket 395 (=79/Stk), 10er-Paket 690 (=69/Stk);
# ERP-Zuschlag CHF 49 pro exportiertem Devis im PPD-Tarif (Entscheidung 3).


def ppd_preis(anzahl: int) -> int:
    """Bester Preis fuer n Pay-per-Devis (Einzeln / 5er / 10er-Kombination)."""
    p = PRODUKTE["starter"]
    zehner, rest10 = divmod(anzahl, 10)
    fuenfer, rest5 = divmod(rest10, 5)
    return (zehner * p["paket10_chf"] + fuenfer * p["paket5_chf"]
            + rest5 * p["einzeln_chf"])


def erp_zuschlag_chf() -> int:
    """ERP-Zuschlag pro exportiertem Devis fuer PPD-Kunden (Starter)."""
    return PRODUKTE["starter"]["erp_zuschlag_chf"]


def upsell_hinweis(ppd_genutzt: int) -> str:
    """Hinweis, bei wie vielen weiteren Devis die Professional-Lizenz guenstiger waere."""
    p = PRODUKTE["starter"]
    lizenz_preis = PRODUKTE["professional"]["miete_chf"]  # Monatlich 350
    # Break-even: 350 / 89 ≈ 4 Devis/Monat → ca. 48/Jahr
    weitere = max(0, round(lizenz_preis / p["einzeln_chf"]) - ppd_genutzt)
    return (f"Tipp: Bei {weitere} weiteren Devis/Monat ist Professional "
            f"({lizenz_preis}.-/Mt.) bereits günstiger.")


def info() -> dict:
    prod, zahl = tarif_key()
    p = PRODUKTE.get(prod, PRODUKTE["starter"])

    if p["modell"] == "pay_per_devis":
        return {"produkt": prod, "name": p["name"], "zahlart": "pay_per_devis",
                "preis_chf": p["einzeln_chf"], "intervall": "pro Devis",
                "features": list(p["features"]),
                "paket5_chf": p["paket5_chf"], "paket10_chf": p["paket10_chf"],
                "erp_zuschlag_chf": p["erp_zuschlag_chf"]}

    if p["modell"] == "subscription":
        if zahl == "miete":
            return {"produkt": prod, "name": p["name"], "zahlart": "miete",
                    "preis_chf": p["miete_chf"], "intervall": p["miete_intervall"],
                    "features": list(p["features"])}
        return {"produkt": prod, "name": p["name"], "zahlart": "einmal",
                "preis_chf": p["einmal_chf"], "intervall": p["einmal_intervall"],
                "features": list(p["features"])}

    # enterprise
    return {"produkt": prod, "name": p["name"], "zahlart": "custom",
            "preis_chf": None, "intervall": "auf Anfrage",
            "features": list(p["features"]), "auf_anfrage": True}


def setze_tarif(kunde_id: str, produkt: str = None, zahlart: str = "pay_per_devis",
               tarif: str = None, seit: str = "") -> dict:
    # Abwaertskompatibel: alte Signatur setze_tarif(kunde_id, tarif="devispro")
    if tarif is not None and produkt is None:
        produkt = tarif
    if produkt not in PRODUKTE:
        return {"ok": False, "fehler": "Unbekanntes Produkt"}
    if zahlart not in ("pay_per_devis", "miete", "einmal", "custom"):
        return {"ok": False, "fehler": "Unbekannte Zahlart"}
    neu = {"produkt": produkt, "zahlart": zahlart, "kunde_id": kunde_id, "seit": seit}
    with open(ABO_PFAD, "w", encoding="utf-8") as f:
        json.dump(neu, f, indent=2, ensure_ascii=False)
    return {"ok": True, **neu}


def aktiver_tarif() -> str:
    """Liefert den aktiven Tarif-Namen (aus data/abo.json)."""
    try:
        if os.path.exists(ABO_PFAD):
            with open(ABO_PFAD, encoding="utf-8") as f:
                d = json.load(f)
            prod = d.get("produkt", "starter")
            return PRODUKTE.get(prod, {}).get("name", prod)
    except Exception:
        pass
    return "Starter (Pay-per-Devis)"


def ppd_code_erzeugen(kunde_id: str, anzahl: int) -> str:
    """Erzeugt einen RSA-signierten Pay-per-Devis-Code.

    PREISMODELL v3 (Konzept C.6): Format "kunde_id|PPD:<anzahl>|SIGNATUR"
    — gleiche Infrastruktur wie jahres_code_erzeugen().
    """
    try:
        from devispro import license_admin as lamod
        priv = lamod._lade_private_key()
        from devispro import crypto_rsa as rsa
        payload = f"PPD:{int(anzahl)}"
        sig = rsa.sign(priv, f"{kunde_id}|{payload}")
        return f"{kunde_id}|{payload}|{sig}"
    except Exception as e:
        return f"FEHLER: {e}"


def jahres_code_erzeugen(kunde_id: str) -> str:
    """Erzeugt einen Jahres-Freischaltcode ueber license_admin (RSA-signiert)."""
    try:
        from devispro import license_admin as lamod
        return lamod.jahres_code_erzeugen(kunde_id)
    except Exception as e:
        return f"FEHLER: {e}"
