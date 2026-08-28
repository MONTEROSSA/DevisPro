"""Zentrale Preis- und Tarif-Definition fuer DevisPro.

Drei Tarife (Preismodell v3 FINAL):
  - Starter     : Pay-per-Devis (CHF 89/Devis, 5 Gratis, Pakete 5er/10er)
  - Professional: Monatlich CHF 350 (alles inkl. ERP-Schnittstellen)
  - Enterprise  : Auf Anfrage (Team, API, SLA, On-Prem, White-Label)

Preise sind realistisch und konkurrenzfaehig positioniert:
  - Starter liegt unter klassischen Abo-Modellen fuer Einsteiger.
  - Professional (CHF 350/Mt.) ist preiswert gegenueber Sorba/Abacus/Proffix
    (dort oft 5'000-15'000 CHF Einrichtung + 2'000-4'000 CHF/Jahr pro Modul),
    aber vollwertig fuer KMU im Bau mit ERP-Schnittstellen inklusive.
"""

# --- Tarif-Preise (CHF) ---------------------------------------------------
TARIFE = {
    "starter": {
        "modell": "pay_per_devis",
        "name": "Starter",
        "einzeln_chf": 89,
        "paket5_chf": 395,
        "paket10_chf": 690,
        "erp_zuschlag_chf": 49,  # pro exportiertem Devis
        "gratis_devis": 5,
        "bezeichnung": "Starter",
        "untertitel": "Pay-per-Devis — nur zahlen, was Sie brauchen",
    },
    "professional": {
        "modell": "subscription",
        "name": "Professional",
        "miete_chf": 350,          # pro Monat
        "einmal_chf": 2400,        # einmalig
        "support_jahr": 990,       # pro Jahr
        "erp_zuschlag_chf": 0,     # inklusive
        "bezeichnung": "Professional",
        "untertitel": "Alles inklusive — ERP-Schnittstellen, unbegrenzte Devis",
    },
    "enterprise": {
        "modell": "custom",
        "name": "Enterprise",
        "miete_chf": None,         # auf Anfrage
        "einmal_chf": None,
        "support_jahr": None,
        "erp_zuschlag_chf": 0,     # inklusive
        "bezeichnung": "Enterprise",
        "untertitel": "Team, API, SLA, On-Prem, White-Label — massgeschneidert",
    },
}

# Inkludierte ERP-Features (ab Professional)
ERP_FEATURES = [
    "connector_abacus",
    "connector_proffix",
    "mahnung",
    "white_label",
    "teilrechnung",
    "multiwährung",
    "mehrsprachig",
    "prio_support",
]

# Enterprise-Zusatzfeatures
ENTERPRISE_FEATURES = ERP_FEATURES + [
    "team_admin",
    "api_access",
    "sla",
    "on_prem_option",
    "dedicated_support",
    "custom_integrations",
]

TARIF_KEYS = ["starter", "professional", "enterprise"]


def preis(tarif: str) -> dict:
    """Gibt das Preis-Dict fuer einen Tarif zurueck (Default 'starter')."""
    return TARIFE.get(tarif, TARIFE["starter"])


def ist_erp(tarif: str) -> bool:
    """True wenn Professional oder Enterprise (ERP-Schnittstellen inklusive)."""
    return tarif in ("professional", "enterprise")


def tarif_aus_lizenz(lizenz: dict) -> str:
    """Liest den Tarif aus einem Lizenz-Dict (Fallbacks sicher)."""
    if not lizenz:
        return "starter"
    t = str(lizenz.get("modus") or lizenz.get("tarif", "starter")).lower()
    # Legacy-Mapping
    if t in ("devis", "voll", "ppd"):
        return "starter"
    if t == "erp":
        return "professional"
    return t if t in TARIF_KEYS else "starter"


def alle_tarife() -> list:
    return [
        {"tarif": "starter", **TARIFE["starter"]},
        {"tarif": "professional", **TARIFE["professional"], "erp_features": ERP_FEATURES},
        {"tarif": "enterprise", **TARIFE["enterprise"], "erp_features": ENTERPRISE_FEATURES},
    ]