"""NPK-Struktur fuer DevisPro (Schweizer Normpositionen-Katalog).

WICHTIG / LIZENZ:
  Die NPK-Kapitelnummern + Gewerk-Zuordnung sind aus dem offiziellen
  Kapitelverzeichnis (NPK-Liste D, Baumeisterverband) uebernommen und
  bilden das GERUEST. Die VOLLEN Leistungspositionen (1 Mio+) sind
  urheberrechtlich geschuetzt (CRB-Datennutzungslizenz) und werden NICHT
  mitgeliefert.

  Stattdessen bietet dieses Modul eine IMPORT-SCHNITTSTELLE:
  - import_npk_csv(datei): laedt lizenzierte NPK-Daten (CSV: npk,text,
    einheit, beispielpreis) des Kunden und haengt sie an die Richtpreisliste an.
  - kapitel_fuer_gewerk(gewerk): liefert die relevanten NPK-Kapitelnummern.

So bleibt DevisPro 100% legal: Der Kunde spielt seine eigene (lizenzierte)
NPK-Liste ein; DevisPro macht das Matching + Bepreisung.
"""
import csv
import os

# NPK-Kapitelgruppe -> Gewerk (aus Kapitelverzeichnis NPK, ergaenzt um
# oeffentlich bekannte Nummernbereiche der uebrigen Gewerke).
# (nummernbereich_start, nummern bereich_end, gewerk, bezeichnung)
NPK_GEWERKE = [
    (102, 268, "Baumeister", "Baumeisterarbeiten (Hoch-/Tief-/Untertagbau)"),
    (211, 237, "Baumeister", "Erd- und Strassenbau"),
    (314, 315, "Maurer", "Maurerarbeiten / Betonelemente"),
    (342, 348, "Gipser", "Aussenwaermedaemmung / Aussenputze"),
    (643, 643, "Gipser", "Trockenbau Waende"),
    (661, 662, "Bodenleger", "Estriche / Bodenbelaege Zement/Kunstharz"),
    (671, 671, "Gipser", "Gipserarbeiten Innenputze/Stukkaturen"),
    (681, 681, "Baumeister", "Bauheizung/Bautrocknung"),
    # Gebaeudetechnik (oeffentlich bekannte NPK-Bereiche)
    (400, 499, "Sanitaer", "Sanitaerinstallationen (NPK 41x/44x)"),
    (500, 599, "Heizung", "Heizung / Waermeerzeugung (NPK 50x)"),
    (600, 699, "Lueftung", "Lueftung / Klima (NPK 60x)"),
    (700, 799, "Elektro", "Elektroinstallationen (NPK 70x)"),
    (800, 899, "Gebaeudeautomation", "Gebaeudeautomation MSRL (NPK 80x)"),
    # Weitere Hochbau-Gewerke
    (341, 341, "Maler", "Maler-/Beschichtungsarbeiten (NPK 34x)"),
    (351, 359, "Glaser", "Glaserarbeiten / Fenster (NPK 35x)"),
    (361, 369, "Schreiner", "Schreinerarbeiten / Tischelemente (NPK 36x)"),
    (371, 379, "Spengler", "Spenglerarbeiten / Metallblech (NPK 37x)"),
    (381, 389, "Dach", "Dachdeckung / Abdichtung (NPK 38x)"),
    (391, 399, "Schlosser", "Schlosserarbeiten / Metallbau (NPK 39x)"),
    (221, 229, "Pflaster", "Pflaster-/Belagsarbeiten (NPK 22x)"),
    (181, 189, "Garten", "Garten-/Landschaftsbau (NPK 18x)"),
]


def gewerk_fuer_kapitel(nr: int) -> str:
    """Ordnet eine NPK-Kapitelnummer einem Gewerk zu."""
    for a, b, gw, _ in NPK_GEWERKE:
        if a <= nr <= b:
            return gw
    return "Sonstige"


def kapitel_fuer_gewerk(gewerk: str):
    """Liefert die NPK-Kapitelnummern-Bereiche fuer ein Gewerk."""
    return [(a, b, bez) for a, b, gw, bez in NPK_GEWERKE if gw == gewerk]


def import_npk_csv(datei: str, ziel_csv: str):
    """Importiert lizenzierte NPK-Daten (CSV: npk,text,einheit,preis_chf)
    und haengt sie an die Richtpreisliste an.

    Rueckgabe: (neue_zeilen, uebersprungen)
    """
    neu = 0
    skip = 0
    with open(datei, encoding="utf-8") as f:
        rdr = csv.reader(f)
        zeilen = []
        for row in rdr:
            if len(row) < 3:
                skip += 1
                continue
            npk = row[0].strip()
            text = row[1].strip()
            einheit = row[2].strip()
            preis = row[3].strip() if len(row) > 3 else ""
            if not npk or not text:
                skip += 1
                continue
            gw = gewerk_fuer_kapitel(int(npk.split(".")[0]) if npk[:3].isdigit() else 0)
            zeilen.append(f"{npk},{text},{einheit},{preis},{gw}")
            neu += 1
    with open(ziel_csv, "a", encoding="utf-8") as f:
        f.write("\n".join(zeilen) + "\n")
    return neu, skip
