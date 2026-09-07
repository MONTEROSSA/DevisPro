"""Gewerksspezifische Zusatzpositionen (Vorschlaege fuer den Fachbetrieb).

Nach der Auto-Bepreisung des Devis sieht der Fachbetrieb eine Liste typischer
Vorarbeiten/Zuschlaege, die er VOR ORT erst erkennt. Er kreuzt an, was
zutrifft, und kann eigene Positionen frei ergaenzen.
Das Modell: Mensch behaelt die Kontrolle (Human-in-the-Loop).

Deckt ALLE relevanten Schweizer Bau-Gewerke ab (Hoch-, Tief-, Untertagbau
sowie Gebaeudetechnik), orientiert an der NPK-Kapitelstruktur.

ep_chf = None  -> KMU muss den Preis selbst eingeben (typisch bei unklaren Vorarbeiten)
ep_chf > 0    -> Vorschlagswert aus der Richtpreisliste, KMU kann ueberschreiben
"""
from typing import List, Dict

# Gewerk -> Liste von Vorschlaegen (typische Vor-Ort-Erkenntnisse)
SUGGESTED_EXTRAS: Dict[str, List[Dict]] = {
    "Bodenleger": [
        {"id": "ug_pruefen", "bezeichnung": "Untergrund prüfen / Feuchtigkeit messen", "einheit": "m2", "ep_chf": None},
        {"id": "ug_ausgleichen", "bezeichnung": "Untergrund ausgleichen (Nivelliermasse)", "einheit": "m2", "ep_chf": 18.0},
        {"id": "ug_grundieren", "bezeichnung": "Grundieren", "einheit": "m2", "ep_chf": 4.5},
        {"id": "ug_abdichten", "bezeichnung": "Abdichtung / Entkopplung verlegen", "einheit": "m2", "ep_chf": 22.0},
        {"id": "abdeck", "bezeichnung": "Schutzabdeckung / Abkleben", "einheit": "m2", "ep_chf": 3.0},
        {"id": "alt_platten", "bezeichnung": "Alte Beläge entfernen", "einheit": "m2", "ep_chf": 14.0},
    ],
    "Maler": [
        {"id": "spachteln", "bezeichnung": "Wände spachteln / glätten", "einheit": "m2", "ep_chf": 9.0},
        {"id": "grundieren", "bezeichnung": "Grundieren", "einheit": "m2", "ep_chf": 3.5},
        {"id": "risse", "bezeichnung": "Risse armieren / Risssanierung", "einheit": "m", "ep_chf": 12.0},
        {"id": "abkleben", "bezeichnung": "Abkleben / Abdecken", "einheit": "m2", "ep_chf": 2.5},
        {"id": "altfarbe", "bezeichnung": "Alte Farbe entfernen / abwaschen", "einheit": "m2", "ep_chf": 5.0},
        {"id": "isolation", "bezeichnung": "Fleckschutz / Isolieranstrich", "einheit": "m2", "ep_chf": 4.0},
    ],
    "Sanitärinstallation": [
        {"id": "aufstemmen", "bezeichnung": "Wand-/Boden aufstemmen", "einheit": "m", "ep_chf": 55.0},
        {"id": "verrohrung", "bezeichnung": "Neu verrohren (Kupfer/PE)", "einheit": "m", "ep_chf": 48.0},
        {"id": "abdichtung", "bezeichnung": "Abdichtung Sanitärbereich", "einheit": "m2", "ep_chf": 28.0},
        {"id": "alt_demont", "bezeichnung": "Alte Installation demontieren/entsorgen", "einheit": "h", "ep_chf": 75.0},
        {"id": "putz", "bezeichnung": "Wieder verputzen / schliessen", "einheit": "m2", "ep_chf": 35.0},
    ],
    "Heizung": [
        {"id": "aufstemmen", "bezeichnung": "Schlitze fräsen / Aufstemmen", "einheit": "m", "ep_chf": 52.0},
        {"id": "rohr", "bezeichnung": "Rohrleitungen verlegen", "einheit": "m", "ep_chf": 45.0},
        {"id": "heizkoerper", "bezeichnung": "Heizkörper demont./mont. neu", "einheit": "Stk", "ep_chf": 120.0},
        {"id": "pumpe", "bezeichnung": "Umwälzpumpe / Mischer tauschen", "einheit": "Stk", "ep_chf": 180.0},
        {"id": "entsorgung", "bezeichnung": "Alte Anlage entsorgen", "einheit": "Pauschal", "ep_chf": None},
    ],
    "Lüftung": [
        {"id": "kanal", "bezeichnung": "Lüftungskanal verlegen", "einheit": "m", "ep_chf": 38.0},
        {"id": "decke", "bezeichnung": "Deckenausschnitte / Schächte", "einheit": "Stk", "ep_chf": 65.0},
        {"id": "geraet", "bezeichnung": "Gerät demont./mont. neu", "einheit": "Stk", "ep_chf": 150.0},
        {"id": "isol", "bezeichnung": "Kanalisolierung / Schalldämmung", "einheit": "m", "ep_chf": 12.0},
    ],
    "Elektro": [
        {"id": "kanal", "bezeichnung": "Kabelkanal fräsen / verlegen", "einheit": "m", "ep_chf": 18.0},
        {"id": "feuchtraum", "bezeichnung": "Feuchtraum-Schutz / Abdichtung", "einheit": "Stk", "ep_chf": 9.0},
        {"id": "alt_demont", "bezeichnung": "Alte Leitungen demontieren", "einheit": "h", "ep_chf": 72.0},
        {"id": "zaehler", "bezeichnung": "Zähler / Verteilung anpassen", "einheit": "Stk", "ep_chf": 140.0},
        {"id": "smart", "bezeichnung": "Smart-Home / Bus-System nachrüsten", "einheit": "Pauschal", "ep_chf": None},
    ],
    "Gipser": [
        {"id": "abriss", "bezeichnung": "Abriss / Entfernen Altputz", "einheit": "m2", "ep_chf": 16.0},
        {"id": "grundputz", "bezeichnung": "Grundputz aufbringen", "einheit": "m2", "ep_chf": 22.0},
        {"id": "feinputz", "bezeichnung": "Feinputz / Glattstrich", "einheit": "m2", "ep_chf": 19.0},
        {"id": "abdeck", "bezeichnung": "Abdecken / Schutz", "einheit": "m2", "ep_chf": 3.0},
        {"id": "entsorgung", "bezeichnung": "Materialentsorgung", "einheit": "t", "ep_chf": 120.0},
    ],
    "Schreiner": [
        {"id": "ausbau", "bezeichnung": "Altbauteile ausbauen", "einheit": "h", "ep_chf": 70.0},
        {"id": "anpass", "bezeichnung": "Massanfertigung / Anpassen", "einheit": "h", "ep_chf": 85.0},
        {"id": "montage", "bezeichnung": "Montage / Verbinden", "einheit": "h", "ep_chf": 80.0},
        {"id": "versiegeln", "bezeichnung": "Versiegeln / Ölen", "einheit": "m2", "ep_chf": 12.0},
        {"id": "entsorgung", "bezeichnung": "Altmaterial entsorgen", "einheit": "t", "ep_chf": 110.0},
    ],
    "Glaser": [
        {"id": "ausbau", "bezeichnung": "Alte Scheibe / Rahmen ausbauen", "einheit": "Stk", "ep_chf": 45.0},
        {"id": "versiegeln", "bezeichnung": "Abdichten / Versiegeln", "einheit": "m", "ep_chf": 14.0},
        {"id": "geruest", "bezeichnung": "Gerüst / Hebebühne nötig", "einheit": "Pauschal", "ep_chf": None},
        {"id": "entsorgung", "bezeichnung": "Altglas entsorgen", "einheit": "Stk", "ep_chf": 15.0},
    ],
    "Spengler": [
        {"id": "demont", "bezeichnung": "Alte Bleche demontieren", "einheit": "m", "ep_chf": 22.0},
        {"id": "neubl", "bezeichnung": "Blech neu falzen / verlegen", "einheit": "m", "ep_chf": 38.0},
        {"id": "abdicht", "bezeichnung": "Anschluss / Abdichtung", "einheit": "m", "ep_chf": 18.0},
        {"id": "entsorgung", "bezeichnung": "Altmetall entsorgen", "einheit": "Pauschal", "ep_chf": 40.0},
    ],
    "Dachdecker": [
        {"id": "alt_abd", "bezeichnung": "Alte Abdichtung / Eindeckung abbauen", "einheit": "m2", "ep_chf": 12.0},
        {"id": "unterbau", "bezeichnung": "Unterbau / Konterlattung", "einheit": "m2", "ep_chf": 16.0},
        {"id": "abdicht", "bezeichnung": "Dampfsperre / Abdichtung", "einheit": "m2", "ep_chf": 9.0},
        {"id": "entsorgung", "bezeichnung": "Altmaterial entsorgen", "einheit": "t", "ep_chf": 115.0},
    ],
    "Baumeister": [
        {"id": "aushub", "bezeichnung": "Mehr-/Weniger-Aushub als geplant", "einheit": "m3", "ep_chf": 28.0},
        {"id": "abbruch", "bezeichnung": "Abbruch / Entsorgung Altbau", "einheit": "m3", "ep_chf": 95.0},
        {"id": "beton", "bezeichnung": "Betonzugabe / Nacharbeiten", "einheit": "m3", "ep_chf": 180.0},
        {"id": "geruest", "bezeichnung": "Gerüststellung", "einheit": "m2", "ep_chf": 8.0},
        {"id": "entsorgung", "bezeichnung": "Bauschuttentsorgung", "einheit": "t", "ep_chf": 130.0},
    ],
    "Maurer": [
        {"id": "abriss", "bezeichnung": "Abriss / Mauerwerk entfernen", "einheit": "m2", "ep_chf": 18.0},
        {"id": "fundament", "bezeichnung": "Fundament / Sockel zusätzlich", "einheit": "m3", "ep_chf": 160.0},
        {"id": "verputz", "bezeichnung": "Verputzarbeiten aussen", "einheit": "m2", "ep_chf": 24.0},
        {"id": "entsorgung", "bezeichnung": "Materialentsorgung", "einheit": "t", "ep_chf": 120.0},
    ],
    "Schlosser": [
        {"id": "demont", "bezeichnung": "Alte Konstruktion demontieren", "einheit": "Stk", "ep_chf": 55.0},
        {"id": "mont", "bezeichnung": "Neu montieren / justieren", "einheit": "Stk", "ep_chf": 90.0},
        {"id": "korros", "bezeichnung": "Korrosionsschutz / streichen", "einheit": "m2", "ep_chf": 14.0},
        {"id": "entsorgung", "bezeichnung": "Altmetall entsorgen", "einheit": "Pauschal", "ep_chf": 40.0},
    ],
    "Gartenbau": [
        {"id": "aushub", "bezeichnung": "Bodenaushub / Planie", "einheit": "m3", "ep_chf": 22.0},
        {"id": "entsorgung", "bezeichnung": "Boden / Grünschnitt entsorgen", "einheit": "t", "ep_chf": 65.0},
        {"id": "abdicht", "bezeichnung": "Dränung / Abdichtung", "einheit": "m", "ep_chf": 16.0},
        {"id": "befest", "bezeichnung": "Befestigung / Wegebau", "einheit": "m2", "ep_chf": 35.0},
    ],
    "Pflaster": [
        {"id": "aushub", "bezeichnung": "Bettungsmaterial / Aushub", "einheit": "m2", "ep_chf": 14.0},
        {"id": "alt_entf", "bezeichnung": "Alte Beläge entfernen", "einheit": "m2", "ep_chf": 11.0},
        {"id": "fuge", "bezeichnung": "Verfugen / Abdichten", "einheit": "m2", "ep_chf": 8.0},
        {"id": "entsorgung", "bezeichnung": "Altmaterial entsorgen", "einheit": "t", "ep_chf": 110.0},
    ],
    "GU": [
        {"id": "bauleitung", "bezeichnung": "Bauleitung / Koordination", "einheit": "h", "ep_chf": 95.0},
        {"id": "entsorgung", "bezeichnung": "Bauschuttentsorgung", "einheit": "t", "ep_chf": 130.0},
        {"id": "geruest", "bezeichnung": "Gerüststellung", "einheit": "m2", "ep_chf": 8.0},
        {"id": "abdeck", "bezeichnung": "Schutzabdeckung Baustelle", "einheit": "m2", "ep_chf": 3.5},
        {"id": "puffer", "bezeichnung": "Unvorhergesehenes / Pauschale", "einheit": "Pauschal", "ep_chf": None},
    ],
}

GENERIC = [
    {"id": "anfahrt", "bezeichnung": "Anfahrt / Kleinmaterial", "einheit": "Pauschal", "ep_chf": 60.0},
    {"id": "entsorgung", "bezeichnung": "Entsorgung", "einheit": "Pauschal", "ep_chf": 90.0},
]


def vorschlaege_fuer(gewerk: str) -> List[Dict]:
    """Gibt die passenden Vorschlaege fuer ein Gewerk zurueck (plus generische)."""
    base = SUGGESTED_EXTRAS.get(gewerk, [])
    return base + GENERIC


def gewerke_liste() -> List[str]:
    return list(SUGGESTED_EXTRAS.keys())
