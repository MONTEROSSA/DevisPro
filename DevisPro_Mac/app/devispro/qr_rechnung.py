"""Swiss QR-Rechnung (CH) - Export aus einem Devis.

Erzeugt den QR-Code-String im offiziellen Schweizer Format
(SPC / Schema 0200) sowie eine vollstaendige Rechnung als Text/SVG.
Reine Stdlib - keine externen Abhaengigkeiten.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from .models import Devis


# --- QR-Code (optional, falls qrcode-Lib verfuegbar) -------------------
def qr_verfuegbar() -> bool:
    """True, wenn die 'qrcode'-Bibliothek installiert ist (fuer PNG/SVG)."""
    try:
        import qrcode  # type: ignore
        return True
    except ImportError:
        return False


@dataclass
class QrRechnung:
    """Daten einer Swiss QR-Rechnung."""
    kreditor_name: str = "Monterossa AG"
    kreditor_strasse: str = "Hauptstrasse 1"
    kreditor_plz_ort: str = "8000 Zuerich"
    kreditor_land: str = "CH"
    iban: str = "CH3908704016075473007"
    zahlungsempfaenger: str = "Monterossa AG"
    betrag: Decimal = Decimal("0.00")
    waehrung: str = "CHF"
    schuldner_name: str = ""
    schuldner_strasse: str = ""
    schuldner_plz_ort: str = ""
    schuldner_land: str = "CH"
    ref_nr: str = ""
    zusatz: str = ""

    def payload(self) -> str:
        """Offizieller SPC-Payload (Schema 0200)."""
        lines = [
            "SPC", "0200", "1",
            self.iban,
            "S", self.kreditor_name, self.kreditor_strasse,
            self.kreditor_plz_ort, "", self.kreditor_land,
            "", "", "", "", "", "", "", "",
            f"{self.betrag:.2f}", self.waehrung,
            self.zahlungsempfaenger, self.schuldner_strasse or self.kreditor_strasse,
            self.schuldner_plz_ort or self.kreditor_plz_ort, "",
            self.schuldner_land, "", "", "", "", "", "", "", "",
            self.ref_nr or "NON", self.zusatz or "",
        ]
        return "\n".join(lines)

    def als_text(self) -> str:
        betrag = self.betrag.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return (
            "=============================================\n"
            "        DevisPro - Swiss QR-Rechnung\n"
            "=============================================\n"
            f"Kreditor:    {self.kreditor_name}\n"
            f"IBAN:        {self.iban}\n"
            f"Empfaenger:  {self.zahlungsempfaenger}\n"
            f"Betrag:      {betrag} {self.waehrung}\n"
            f"Referenz:    {self.ref_nr or '-'}\n"
            f"Schuldner:   {self.schuldner_name or '-'}\n"
            f"            {self.schuldner_plz_ort or '-'}\n"
            "---------------------------------------------\n"
            "QR-Code (SPC 0200):\n"
            f"{self.payload()}\n"
            "=============================================\n"
        )


def rechnung_aus_devis(devis: Devis, kreditor=None, schuldner=None, ref_nr="") -> QrRechnung:
    """Berechnet Gesamtbetrag aus Devis und erstellt QrRechnung."""
    total = Decimal("0.00")
    for p in devis.positions:
        if p.betrag:
            total += Decimal(str(p.betrag))
    k = kreditor or {}
    s = schuldner or {}
    return QrRechnung(
        kreditor_name=k.get("name", "Monterossa AG"),
        kreditor_strasse=k.get("strasse", "Hauptstrasse 1"),
        kreditor_plz_ort=k.get("plz_ort", "8000 Zuerich"),
        kreditor_land=k.get("land", "CH"),
        iban=k.get("iban", "CH3908704016075473007"),
        zahlungsempfaenger=k.get("name", "Monterossa AG"),
        betrag=total,
        waehrung="CHF",
        schuldner_name=s.get("name", ""),
        schuldner_strasse=s.get("strasse", ""),
        schuldner_plz_ort=s.get("plz_ort", ""),
        schuldner_land=s.get("land", "CH"),
        ref_nr=ref_nr,
    )


def qr_matrix_aus_rechnung(r: "rmod.Rechnung") -> "tuple":
    """Baut die QR-Matrix aus einer Rechnung (braucht devispro.rechnung)."""
    betrag = getattr(r, "_offen_override", None)
    if betrag is None:
        betrag = r.brutto()
    qr = QrRechnung(
        kreditor_name=r.betrieb or "Monterossa AG",
        kreditor_plz_ort="8000 Zuerich",
        betrag=Decimal(str(betrag)),
        schuldner_name=r.kunde,
        schuldner_plz_ort=r.objekt,
    )
    from . import qr_render as QR
    return QR.encode(qr.payload())

