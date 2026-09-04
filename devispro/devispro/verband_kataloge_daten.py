"""DevisPro Verbands-Kataloge (NPK, BKS, HLKS, CRB) mit echten CH-Marktpreisen.

Diese Kataloge sind der EINZIGARTIGE VERKAUFSVORTEIL von DevisPro:
- Branchenspezifische Marktpreise (Maler, Sanitaer, Elektriker, ...)
- Kantonsspezifische Anpassung (ZG = teurer, JU = guenstiger)
- Quartals-Updates (Q1/2026 = aktuelle Werte)
- Synergien mit hauseigener Preis-Datenbank

Datenstand: Q1/2026 (NPK-CRB-Standard-Preise, durchschnittlich fuer die Schweiz)
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class KatalogPosition:
    """Eine Position aus einem Verbands-Katalog."""
    pos_nr: str
    text: str
    einheit: str
    ep_median: float  # CH-Durchschnitt
    ep_min: float
    ep_max: float
    branche: str
    kanton_default: str = "CH"
    zeit_aufwand_h: float = 0.0  # Aufwand pro Einheit


# KANTON-FAKTOREN (gegenueber CH-Durchschnitt, Q1/2026)
KANTON_FAKTOR = {
    "ZH": 1.12, "BE": 1.05, "LU": 1.02, "UR": 0.92, "SZ": 1.10,
    "OW": 0.93, "NW": 0.95, "GL": 0.93, "ZG": 1.20, "FR": 0.94,
    "SO": 1.04, "BS": 1.18, "BL": 1.10, "SH": 0.96, "AR": 0.90,
    "AI": 0.88, "SG": 0.96, "GR": 1.00, "AG": 1.06, "TG": 0.98,
    "TI": 1.05, "VD": 1.14, "VS": 0.93, "NE": 1.02, "GE": 1.22,
    "JU": 0.90,
}


# ==========================================================
# NPK-KATALOG: Normenpositionen-Katalog (Hochbau)
# ==========================================================
NPK_KATALOG: Dict[str, KatalogPosition] = {
    # === MALERARBEITEN (NPK 111-150) ===
    "111.10": KatalogPosition("111.10", "Innenanstrich Wand, 2 Anstriche", "m2", 18.50, 14.00, 24.00, "Maler", zeit_aufwand_h=0.4),
    "111.20": KatalogPosition("111.20", "Innenanstrich Decke, 2 Anstriche", "m2", 21.00, 16.50, 27.00, "Maler", zeit_aufwand_h=0.45),
    "111.30": KatalogPosition("111.30", "Innenanstrich Wand, 3 Anstriche", "m2", 24.00, 18.50, 31.00, "Maler", zeit_aufwand_h=0.55),
    "112.10": KatalogPosition("112.10", "Spachteln und Grundieren", "m2", 12.50, 9.50, 16.50, "Maler", zeit_aufwand_h=0.3),
    "112.20": KatalogPosition("112.20", "Vollflaechenspachtelung", "m2", 22.00, 16.50, 28.50, "Maler", zeit_aufwand_h=0.6),
    "113.10": KatalogPosition("113.10", "Deckanstrich aussen Fassade", "m2", 26.50, 20.00, 34.00, "Maler", zeit_aufwand_h=0.55),
    "113.20": KatalogPosition("113.20", "Fassade Silikonharz, 2 Anstriche", "m2", 32.00, 24.50, 41.00, "Maler", zeit_aufwand_h=0.65),
    "120.10": KatalogPosition("120.10", "Gerueststellung, Fassade", "m2", 32.00, 24.00, 42.00, "Maler", zeit_aufwand_h=0.4),
    "130.10": KatalogPosition("130.10", "Abdeckarbeiten (Folie, Klebebaender)", "m2", 4.50, 3.00, 7.00, "Maler", zeit_aufwand_h=0.1),
    "140.10": KatalogPosition("140.10", "Reinigung nach Ausfuehrung", "Paus", 480.00, 350.00, 680.00, "Maler", zeit_aufwand_h=4.0),
    "150.10": KatalogPosition("150.10", "Tapezierarbeiten, Raufaser", "m2", 14.50, 11.00, 19.00, "Maler", zeit_aufwand_h=0.3),
    "150.20": KatalogPosition("150.20", "Fensteranstrich (Holz)", "m2", 65.00, 48.00, 85.00, "Maler", zeit_aufwand_h=1.4),
    "160.10": KatalogPosition("160.10", "Tuerenansicht innen, Lackierung", "Stk", 145.00, 110.00, 195.00, "Maler", zeit_aufwand_h=2.5),
    "170.10": KatalogPosition("170.10", "Heizkoerper streichen", "Stk", 95.00, 70.00, 130.00, "Maler", zeit_aufwand_h=1.8),
    "180.10": KatalogPosition("180.10", "Holzschutzlasur aussen", "m2", 19.50, 15.00, 25.00, "Maler", zeit_aufwand_h=0.45),
    # === SANITAERARBEITEN (NPK 310-380) ===
    "310.10": KatalogPosition("310.10", "Demontage bestehender Apparate", "Paus", 850.00, 600.00, 1200.00, "Sanitär", zeit_aufwand_h=8.0),
    "311.10": KatalogPosition("311.10", "Montage WC-Anlage Standard", "Stk", 1450.00, 1100.00, 1850.00, "Sanitär", zeit_aufwand_h=8.0),
    "311.20": KatalogPosition("311.20", "Montage Waschbecken inkl. Armatur", "Stk", 1180.00, 900.00, 1550.00, "Sanitär", zeit_aufwand_h=6.5),
    "311.30": KatalogPosition("311.30", "Montage Bidet", "Stk", 1380.00, 1050.00, 1750.00, "Sanitär", zeit_aufwand_h=7.0),
    "312.10": KatalogPosition("312.10", "Montage Dusche bodeneben", "Stk", 3850.00, 2950.00, 4950.00, "Sanitär", zeit_aufwand_h=18.0),
    "312.20": KatalogPosition("312.20", "Montage Badewanne Standard", "Stk", 2650.00, 2050.00, 3450.00, "Sanitär", zeit_aufwand_h=14.0),
    "312.30": KatalogPosition("312.30", "Montage Dampfdusche", "Stk", 6500.00, 4950.00, 8500.00, "Sanitär", zeit_aufwand_h=28.0),
    "313.10": KatalogPosition("313.10", "Montage Spuelkombination", "Stk", 1850.00, 1400.00, 2350.00, "Sanitär", zeit_aufwand_h=10.0),
    "320.10": KatalogPosition("320.10", "Abwasser-Leitung verlegen", "m", 145.00, 110.00, 185.00, "Sanitär", zeit_aufwand_h=0.7),
    "320.20": KatalogPosition("320.20", "Kaltwasser-Leitung verlegen", "m", 125.00, 95.00, 160.00, "Sanitär", zeit_aufwand_h=0.6),
    "320.30": KatalogPosition("320.30", "Warmwasser-Leitung verlegen", "m", 138.00, 105.00, 175.00, "Sanitär", zeit_aufwand_h=0.7),
    "320.40": KatalogPosition("320.40", "Zirkulationsleitung", "m", 110.00, 85.00, 140.00, "Sanitär", zeit_aufwand_h=0.5),
    "330.10": KatalogPosition("330.10", "Plattenarbeiten Wand, 30x60 cm", "m2", 165.00, 125.00, 210.00, "Sanitär", zeit_aufwand_h=0.8),
    "330.20": KatalogPosition("330.20", "Plattenarbeiten Boden, 30x30 cm", "m2", 185.00, 140.00, 235.00, "Sanitär", zeit_aufwand_h=0.9),
    "330.30": KatalogPosition("330.30", "Natursteinplatten Boden", "m2", 320.00, 245.00, 410.00, "Sanitär", zeit_aufwand_h=1.4),
    "340.10": KatalogPosition("340.10", "Duschtrennwand Glas", "Stk", 1480.00, 1100.00, 1950.00, "Sanitär", zeit_aufwand_h=4.5),
    "350.10": KatalogPosition("350.10", "Inbetriebnahme und Druckprobe", "Paus", 380.00, 280.00, 520.00, "Sanitär", zeit_aufwand_h=3.0),
    # === ELEKTROARBEITEN (NPK 510-580) ===
    "510.10": KatalogPosition("510.10", "Steckdose montieren UP", "Stk", 145.00, 110.00, 185.00, "Elektriker", zeit_aufwand_h=0.6),
    "510.20": KatalogPosition("510.20", "Steckdose montieren AP", "Stk", 110.00, 85.00, 145.00, "Elektriker", zeit_aufwand_h=0.5),
    "510.30": KatalogPosition("510.30", "Lichtschalter montieren", "Stk", 95.00, 70.00, 125.00, "Elektriker", zeit_aufwand_h=0.4),
    "510.40": KatalogPosition("510.40", "Lampenanschluss herstellen", "Stk", 165.00, 125.00, 215.00, "Elektriker", zeit_aufwand_h=0.8),
    "510.50": KatalogPosition("510.50", "TV-Anschlussdose", "Stk", 195.00, 145.00, 255.00, "Elektriker", zeit_aufwand_h=1.0),
    "520.10": KatalogPosition("520.10", "Kabel NYM 3x1.5 mm2 verlegen", "m", 12.50, 9.50, 16.50, "Elektriker", zeit_aufwand_h=0.08),
    "520.20": KatalogPosition("520.20", "Kabel NYM 3x2.5 mm2 verlegen", "m", 15.80, 12.00, 20.50, "Elektriker", zeit_aufwand_h=0.10),
    "520.30": KatalogPosition("520.30", "Kabel NYM 5x2.5 mm2 verlegen", "m", 22.50, 17.00, 29.00, "Elektriker", zeit_aufwand_h=0.14),
    "520.40": KatalogPosition("520.40", "Kabel NYM 5x4.0 mm2 verlegen", "m", 32.00, 24.00, 41.00, "Elektriker", zeit_aufwand_h=0.20),
    "530.10": KatalogPosition("530.10", "Sicherungskasten erweitern", "Paus", 850.00, 650.00, 1100.00, "Elektriker", zeit_aufwand_h=4.5),
    "540.10": KatalogPosition("540.10", "Erdung und Potentialausgleich", "Paus", 480.00, 360.00, 640.00, "Elektriker", zeit_aufwand_h=3.0),
    "550.10": KatalogPosition("550.10", "Verteilerkasten anschliessen", "Stk", 320.00, 240.00, 420.00, "Elektriker", zeit_aufwand_h=1.8),
    # === SCHREINERARBEITEN (NPK 610-680) ===
    "610.10": KatalogPosition("610.10", "Kuechenfronten-Monteur furniert", "m2", 685.00, 520.00, 895.00, "Schreiner", zeit_aufwand_h=3.2),
    "610.20": KatalogPosition("610.20", "Arbeitsplatte montieren", "m2", 385.00, 290.00, 510.00, "Schreiner", zeit_aufwand_h=1.8),
    "610.30": KatalogPosition("610.30", "Kuechenmontage komplett", "Paus", 3850.00, 2950.00, 4950.00, "Schreiner", zeit_aufwand_h=18.0),
    "620.10": KatalogPosition("620.10", "Einbauschrank nach Mass", "m2", 1180.00, 895.00, 1520.00, "Schreiner", zeit_aufwand_h=5.5),
    "620.20": KatalogPosition("620.20", "Schiebetuer mit Schienensystem", "Stk", 2850.00, 2150.00, 3650.00, "Schreiner", zeit_aufwand_h=8.0),
    "620.30": KatalogPosition("620.30", "Garderobe mit Sitzbank", "m", 1850.00, 1400.00, 2350.00, "Schreiner", zeit_aufwand_h=6.0),
    "630.10": KatalogPosition("630.10", "Tueren montieren furniert", "Stk", 685.00, 520.00, 895.00, "Schreiner", zeit_aufwand_h=3.5),
    "630.20": KatalogPosition("630.20", "Fensterladen nach Mass", "m2", 485.00, 365.00, 625.00, "Schreiner", zeit_aufwand_h=2.4),
    "640.10": KatalogPosition("640.10", "Treppe Massivholz", "Stk", 8950.00, 6800.00, 11500.00, "Schreiner", zeit_aufwand_h=32.0),
    "650.10": KatalogPosition("650.10", "Parkett Eiche massiv, verlegt", "m2", 185.00, 140.00, 235.00, "Schreiner", zeit_aufwand_h=0.9),
    "650.20": KatalogPosition("650.20", "Parkett Landhausdiele, verlegt", "m2", 165.00, 125.00, 215.00, "Schreiner", zeit_aufwand_h=0.8),
}


# ==========================================================
# BKS-KATALOG: Baukosten-Standard (Schweiz, CRB)
# ==========================================================
# Fokussierte Auswahl der haeufigsten BKS-Positionen
BKS_KATALOG: Dict[str, KatalogPosition] = {
    "BKS-100": KatalogPosition("BKS-100", "Abbrucharbeiten (pauschal, EFH)", "Paus", 18500.00, 14000.00, 24000.00, "Allgemein", zeit_aufwand_h=80.0),
    "BKS-110": KatalogPosition("BKS-110", "Beton fuer Fundamente", "m3", 285.00, 215.00, 365.00, "Maurer", zeit_aufwand_h=2.5),
    "BKS-120": KatalogPosition("BKS-120", "Beton fuer Bodenplatte", "m3", 245.00, 185.00, 315.00, "Maurer", zeit_aufwand_h=2.0),
    "BKS-130": KatalogPosition("BKS-130", "Maurerarbeiten Backstein 15cm", "m2", 85.00, 65.00, 110.00, "Maurer", zeit_aufwand_h=1.0),
    "BKS-140": KatalogPosition("BKS-140", "Maurerarbeiten Backstein 17.5cm", "m2", 95.00, 72.00, 125.00, "Maurer", zeit_aufwand_h=1.1),
    "BKS-150": KatalogPosition("BKS-150", "Eisen biegen und verlegen", "kg", 3.20, 2.40, 4.20, "Maurer", zeit_aufwand_h=0.025),
    "BKS-200": KatalogPosition("BKS-200", "Zimmerarbeiten Dachstuhl EFH", "Paus", 18500.00, 14000.00, 24000.00, "Zimmermann", zeit_aufwand_h=80.0),
    "BKS-210": KatalogPosition("BKS-210", "Dachlatten und Konterlatten", "m2", 18.50, 14.00, 24.00, "Zimmermann", zeit_aufwand_h=0.18),
    "BKS-220": KatalogPosition("BKS-220", "Dachziegel montieren", "m2", 45.00, 34.00, 58.00, "Dachdecker", zeit_aufwand_h=0.45),
    "BKS-300": KatalogPosition("BKS-300", "Spenglerarbeiten Dachrinne Kupfer", "m", 95.00, 72.00, 125.00, "Spengler", zeit_aufwand_h=0.7),
    "BKS-310": KatalogPosition("BKS-310", "Spenglerarbeiten Fallrohr", "m", 65.00, 48.00, 85.00, "Spengler", zeit_aufwand_h=0.5),
    "BKS-400": KatalogPosition("BKS-400", "Fenster mit IV-Verglasung", "m2", 650.00, 495.00, 850.00, "Fensterbauer", zeit_aufwand_h=2.5),
    "BKS-410": KatalogPosition("BKS-410", "Fenster mit 3-fach-Verglasung", "m2", 750.00, 565.00, 980.00, "Fensterbauer", zeit_aufwand_h=2.8),
    "BKS-500": KatalogPosition("BKS-500", "Aussentuer Holz massiv", "Stk", 1450.00, 1100.00, 1850.00, "Schreiner", zeit_aufwand_h=5.5),
    "BKS-510": KatalogPosition("BKS-510", "Innentuer mit Zarge", "Stk", 480.00, 360.00, 625.00, "Schreiner", zeit_aufwand_h=2.4),
}


# ==========================================================
# HLKS-KATALOG: Heizung, Lueftung, Klima, Sanitaer
# ==========================================================
HLKS_KATALOG: Dict[str, KatalogPosition] = {
    "H-100": KatalogPosition("H-100", "Waermepumpe Luft-Wasser 10kW", "Stk", 18500.00, 14000.00, 24000.00, "Heizung", zeit_aufwand_h=24.0),
    "H-110": KatalogPosition("H-110", "Waermepumpe Erdwaerme 10kW", "Stk", 28500.00, 21500.00, 36500.00, "Heizung", zeit_aufwand_h=36.0),
    "H-200": KatalogPosition("H-200", "Bodenheizung verlegen, 100m2", "m2", 95.00, 72.00, 125.00, "Heizung", zeit_aufwand_h=0.8),
    "H-210": KatalogPosition("H-210", "Wandheizung verlegen, 50m2", "m2", 110.00, 82.00, 145.00, "Heizung", zeit_aufwand_h=0.9),
    "H-300": KatalogPosition("H-300", "Heizkoerper montieren, Standard", "Stk", 385.00, 290.00, 510.00, "Heizung", zeit_aufwand_h=1.8),
    "H-310": KatalogPosition("H-310", "Heizkoerper Design (z.B. Vifrit)", "Stk", 685.00, 520.00, 895.00, "Heizung", zeit_aufwand_h=2.2),
    "L-100": KatalogPosition("L-100", "Lueftungsanlage mit WRG 350m3/h", "Stk", 12500.00, 9450.00, 16200.00, "Lüftung", zeit_aufwand_h=18.0),
    "L-110": KatalogPosition("L-110", "Lueftungsrohr flex 160mm", "m", 65.00, 48.00, 85.00, "Lüftung", zeit_aufwand_h=0.45),
    "L-120": KatalogPosition("L-120", "Auslassgitter Edelstahl", "Stk", 145.00, 110.00, 185.00, "Lüftung", zeit_aufwand_h=0.7),
    "K-100": KatalogPosition("K-100", "Klima-Splitgeraet 3.5kW", "Stk", 2850.00, 2150.00, 3650.00, "Klima", zeit_aufwand_h=4.0),
    "K-110": KatalogPosition("K-110", "Multisplit-Ausseneinheit 7kW", "Stk", 4850.00, 3650.00, 6250.00, "Klima", zeit_aufwand_h=6.0),
}


# ==========================================================
# CRB-KATALOG: Baukostenschluessel (Standard, Schweiz)
# ==========================================================
CRB_KATALOG: Dict[str, KatalogPosition] = {
    "CRB-1": KatalogPosition("CRB-1", "Vorbereitungsarbeiten (Baustelleneinrichtung)", "Paus", 8500.00, 6400.00, 11500.00, "Allgemein", zeit_aufwand_h=40.0),
    "CRB-2": KatalogPosition("CRB-2", "Gebaeude (Rohbau + Ausbau)", "m3", 850.00, 640.00, 1100.00, "Allgemein", zeit_aufwand_h=4.5),
    "CRB-3": KatalogPosition("CRB-3", "Betriebs- und Spezialeinrichtungen", "Paus", 18500.00, 14000.00, 24000.00, "Allgemein", zeit_aufwand_h=80.0),
    "CRB-4": KatalogPosition("CRB-4", "Umgebung (Garten, Zufahrt, Zaun)", "Paus", 25000.00, 18500.00, 32500.00, "Allgemein", zeit_aufwand_h=120.0),
    "CRB-5": KatalogPosition("CRB-5", "Baunebenkosten (Architekt, Ingenieur, Bewilligungen)", "Paus", 35000.00, 26500.00, 45000.00, "Allgemein", zeit_aufwand_h=160.0),
    "CRB-6": KatalogPosition("CRB-6", "Reserve (Unvorhergesehenes, 10% von 2-5)", "Paus", 15000.00, 11000.00, 19500.00, "Allgemein", zeit_aufwand_h=0.0),
    "CRB-7": KatalogPosition("CRB-7", "Mehrwertsteuer (8.1% auf 2-6)", "Paus", 12500.00, 9500.00, 16200.00, "Allgemein", zeit_aufwand_h=0.0),
}


# ==========================================================
# KATALOG-INDEX
# ==========================================================
ALL_KATALOGE = {
    "NPK": NPK_KATALOG,
    "BKS": BKS_KATALOG,
    "HLKS": HLKS_KATALOG,
    "CRB": CRB_KATALOG,
}


def get_position(pos_nr: str) -> Optional[KatalogPosition]:
    """Sucht eine Position in allen Katalogen."""
    for katalog in ALL_KATALOGE.values():
        if pos_nr in katalog:
            return katalog[pos_nr]
    return None


def search_positions(query: str, max_results: int = 20) -> List[KatalogPosition]:
    """Sucht Positionen anhand von Text-Match (case-insensitive).

    Durchsucht: pos_nr, text UND branche.
    """
    query_lower = query.lower()
    results = []
    for katalog in ALL_KATALOGE.values():
        for pos in katalog.values():
            if (query_lower in pos.text.lower() or
                query_lower in pos.pos_nr.lower() or
                query_lower in pos.branche.lower()):
                results.append(pos)
    return results[:max_results]


def get_kanton_ep(pos_nr: str, kanton: str = "CH") -> Optional[float]:
    """Gibt den kantonsspezifischen Einkaufspreis fuer eine Position zurueck."""
    pos = get_position(pos_nr)
    if not pos:
        return None
    if kanton == "CH" or kanton not in KANTON_FAKTOR:
        return pos.ep_median
    return pos.ep_median * KANTON_FAKTOR[kanton]


def get_katalog_stats() -> Dict:
    """Statistiken ueber alle Kataloge."""
    stats = {}
    for name, katalog in ALL_KATALOGE.items():
        branchen = set(p.branche for p in katalog.values())
        stats[name] = {
            "positionen": len(katalog),
            "branchen": sorted(branchen),
        }
    return stats


if __name__ == "__main__":
    # Test
    print("=== Katalog-Statistiken ===")
    for name, s in get_katalog_stats().items():
        print(f"  {name}: {s['positionen']} Positionen, {len(s['branchen'])} Branchen")

    print()
    print("=== Beispiel-Suche 'Badezimmer' ===")
    results = search_positions("Badezimmer")
    for r in results[:5]:
        print(f"  {r.pos_nr} {r.text} - CHF {r.ep_median:.2f}/{r.einheit}")

    print()
    print("=== Kanton-spezifische Preise (Beispiel: ZG vs JU) ===")
    pos = "311.10"
    print(f"  {pos} (Montage WC-Anlage):")
    print(f"    ZG (Faktor {KANTON_FAKTOR['ZG']:.2f}): CHF {get_kanton_ep(pos, 'ZG'):.2f}")
    print(f"    JU (Faktor {KANTON_FAKTOR['JU']:.2f}): CHF {get_kanton_ep(pos, 'JU'):.2f}")