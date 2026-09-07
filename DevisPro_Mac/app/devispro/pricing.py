"""Zentrale Preis- und Tarif-Definition fuer DevisPro.

Zwei Tarife (Editionen):
  - 'devis' : nur DevisPro (SIA-451-Devis automatisch bepreisen)
  - 'erp'   : DevisPro + integriertes ERP (Lager, Einkauf, Verkauf,
              Kunden/Lieferanten, Buchhaltung, Dashboard)

Preise sind realistisch und konkurrenzfaehig positioniert:
  - DevisPro allein liegt deutlich unter klassischen Bau-/ERP-Suiten.
  - DevisPro+ERP ist preiswert gegenueber Abacus/Proffix mit ERP-Modul
    (dort oft 5'000-15'000 CHF Einrichtung + 2'000-4'000 CHF/Jahr),
    aber vollwertig fuer KMU im Bau.
"""

# --- Tarif-Preise (CHF) ---------------------------------------------------
PREISE = {
    "devis": {
        "einrichtung": 3500.0,        # einmalig
        "lizenz_jahr": 1490.0,        # pro Jahr
        "pilot_monate": 3,            # gratis Testphase
        "bezeichnung": "DevisPro",
        "untertitel": "SIA-451-Devis automatisch bepreisen",
    },
    "erp": {
        "einrichtung": 8900.0,        # einmalig (hoher Mehrwert)
        "lizenz_jahr": 3490.0,        # pro Jahr
        "pilot_monate": 3,
        "bezeichnung": "DevisPro + ERP",
        "untertitel": "DevisPro mit integriertem ERP (Lager, Einkauf, Verkauf, Buchhaltung)",
    },
}

# Inkludierte ERP-Module (nur bei Tarif 'erp')
ERP_MODULE = [
    "Artikel & Lager (Bestand, Mindestbestand, Wareneingaenge)",
    "Kunden & Lieferanten (Stammdaten, Offerten, Bestellungen)",
    "Einkauf (Bestellungen, Wareneingang, Kreditor-Buchung)",
    "Verkauf (Offerte->Auftrag->Rechnung, Devis-Integration)",
    "Buchhaltung (Journal, Kontenrahmen, Debitoren/Kreditoren, Saldo)",
    "Dashboard (Umsatz, Offene Posten, Lagerwert, Marge)",
    "Schnittstellen (13 Buchhaltungs-Exporte + HMAC-API)",
]

TARIFE = ["devis", "erp"]


def preis(tarif: str) -> dict:
    """Gibt das Preis-Dict fuer einen Tarif zurueck (Default 'devis')."""
    return PREISE.get(tarif, PREISE["devis"])


def ist_erp(tarif: str) -> bool:
    return tarif == "erp"


def tarif_aus_lizenz(lizenz: dict) -> str:
    """Liest den Tarif aus einem Lizenz-Dict (Fallbacks sicher)."""
    if not lizenz:
        return "devis"
    t = str(lizenz.get("tarif", "devis")).lower()
    return t if t in TARIFE else "devis"


def alle_tarife() -> list:
    return [
        {"tarif": "devis", **PREISE["devis"]},
        {"tarif": "erp", **PREISE["erp"], "module": ERP_MODULE},
    ]
