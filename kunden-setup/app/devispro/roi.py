"""ROI-Kalkulator: Zeigt einem Betrieb, was die App an Zeit + Geld spart.

Annahmen (vom Betrieb aenderbar):
  - zeit_manuell_h:   Aufwand pro Devis von Hand (Lesen, Matchen, Tippen, Pruefen)
  - zeit_app_h:       Aufwand pro Devis mit App (nur noch Pruefen/Freigeben)
  - devis_pro_monat:  Anzahl Devis pro Monat
  - fehler_ersparnis: geschätzte CHF-Ersparnis pro Devis durch weniger
                      Kalkulationsfehler / vergessene Positionen
  - app_preis:        einmaliger Anschaffungspreis
  - app_jahr:         jaehrliche Gebuehr

Ergebnis:
  - monatliche / jaehrliche Netto-Ersparnis (reiner Betriebseffekt)
  - Break-even in Monaten
  - kumulierter Cashflow ueber 12 Monate (fuer Graphik)
"""
from .stammdaten import load_profile


def calculate(profile: dict,
              zeit_manuell_h: float = 2.0,
              zeit_app_h: float = 0.2,
              devis_pro_monat: int = 20,
              fehler_ersparnis_chf: float = 40.0,
              app_preis: float = 2400.0,
              app_jahr: float = 900.0) -> dict:
    stundenlohn = float(profile.get("stundenlohn_chf", 82.0))
    zeit_erspart_pro_devis = max(0.0, zeit_manuell_h - zeit_app_h)
    geld_zeit_pro_devis = zeit_erspart_pro_devis * stundenlohn
    geld_pro_devis = geld_zeit_pro_devis + fehler_ersparnis_chf
    monat_ersparnis = geld_pro_devis * devis_pro_monat
    jahr_ersparnis = monat_ersparnis * 12

    # Break-even: wann hat die Ersparnis die Anschaffung + laufende Kosten gedeckt?
    kumuliert = 0.0
    break_even_monat = None
    cashflow = []
    for m in range(1, 13):
        kosten = app_jahr / 12.0
        kumuliert += (monat_ersparnis - kosten)
        if m == 1:
            kumuliert -= app_preis  # Anschaffung im ersten Monat
        cashflow.append(round(kumuliert, 2))
        if break_even_monat is None and kumuliert >= 0:
            break_even_monat = m

    roi_jahr1 = cashflow[-1]  # Gewinn nach 12 Monaten
    roi_pct = (roi_jahr1 / (app_preis + app_jahr)) * 100 if (app_preis + app_jahr) else 0.0

    return {
        "stundenlohn": stundenlohn,
        "zeit_manuell_h": zeit_manuell_h,
        "zeit_app_h": zeit_app_h,
        "zeit_erspart_pro_devis": round(zeit_erspart_pro_devis, 2),
        "devis_pro_monat": devis_pro_monat,
        "geld_pro_devis": round(geld_pro_devis, 2),
        "monat_ersparnis": round(monat_ersparnis, 2),
        "jahr_ersparnis": round(jahr_ersparnis, 2),
        "app_preis": app_preis,
        "app_jahr": app_jahr,
        "break_even_monat": break_even_monat,
        "cashflow": cashflow,
        "roi_jahr1": round(roi_jahr1, 2),
        "roi_pct": round(roi_pct, 1),
        "zeit_erspart_jahr_h": round(zeit_erspart_pro_devis * devis_pro_monat * 12, 1),
    }


def calculate_from_profile(profile: dict = None, **kwargs) -> dict:
    if profile is None:
        from .stammdaten import load_profile
        profile = load_profile()
    return calculate(profile, **kwargs)
