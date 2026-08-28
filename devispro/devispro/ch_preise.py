"""Schweizer Durchschnittspreise fuer die Bepreisungs-Simulation.

Realistische CH-Richtpreise (Handwerker/Einzelunternehmen, inkl. Material +
Arbeit, ohne MWST) fuer typische BKP-Gewerke. Diemenen werden aus dem
Positions-Text abgeleitet (m2, Stk, m, lfm). Die Preise sind Markt-Schaetzwerte
(2024/25) und dienen der SIMULATION, nicht der Offerte.

Quelle: uebliche CH-Baukosten-Richtwerte (Baupreisspiegel, Branchen-Durchschnitt).
"""
import re

# Woerter die anzeigen, dass dies KEINE echte Kostenposition ist
# (Gliederung / Ueberschrift / Verweis) -> 0 CHF
_KEINE_KOSTEN = (
    "vorbedingung", "ausführung", "allgemeine", "bedingung", "gemäss dem kapitel",
    "kapitel", "beschrieb", "vorbeschrieb", "gemäss", "laut", "siehe", "lv ",
    "übersicht", "inhalt", "verzeichnis", "reserve", "allgemeines",
)

# (Schluesselwort im Text -> (Einheit, EP_CHF))  - spezifisch zuerst
_PREISE = [
    ("fenster aus holz-metall", ("m2", 950)),
    ("fenster aus holz", ("m2", 820)),
    ("fenster aus metall", ("m2", 780)),
    ("fenster aus kunststoff", ("m2", 620)),
    ("schaufenster", ("m2", 1050)),
    ("fassadenfenster", ("m2", 980)),
    ("fenster", ("m2", 850)),
    ("aussentuer", ("Stk", 2400)),
    ("tuer", ("Stk", 1500)),
    ("tor", ("Stk", 3200)),
    ("brüstung", ("m2", 880)),
    ("brustung", ("m2", 880)),
    ("fassadenelement", ("m2", 720)),
    ("fassade", ("m2", 680)),
    ("montage", ("h", 145)),
    ("liefer", ("Pauschal", 1500)),
    ("innenanstrich", ("m2", 45)),
    ("aussenanstrich", ("m2", 65)),
    ("anstrich", ("m2", 50)),
    ("tapezierung", ("m2", 38)),
    ("spachteln", ("m2", 35)),
    ("streichen", ("m2", 42)),
    ("innenputz", ("m2", 75)),
    ("aussenputz", ("m2", 95)),
    ("putz", ("m2", 80)),
    ("abrieb", ("m2", 60)),
    ("deckputz", ("m2", 90)),
    ("gipser", ("m2", 80)),
    ("dämmung", ("m2", 110)),
    ("daemmung", ("m2", 110)),
    ("isolierung", ("m2", 105)),
    ("bodenbelag", ("m2", 120)),
    ("parkett", ("m2", 180)),
    ("fliesen", ("m2", 220)),
    ("platten", ("m2", 210)),
    ("estrich", ("m2", 85)),
    ("boden", ("m2", 120)),
    ("steckdose", ("Stk", 180)),
    ("lichtaustritt", ("Stk", 320)),
    ("schalter", ("Stk", 150)),
    ("kabel", ("m", 45)),
    ("elektro", ("Stk", 250)),
    ("heizkoerper", ("Stk", 950)),
    ("wasser", ("Stk", 420)),
    ("sanitaer", ("Stk", 500)),
    ("abfluss", ("m", 180)),
    ("demontage", ("h", 140)),
    ("rueckbau", ("h", 140)),
    ("abbruch", ("h", 130)),
    ("entsorgung", ("t", 220)),
    ("transport", ("h", 120)),
    ("geruest", ("m2", 35)),
    ("gerüst", ("m2", 35)),
    ("baustelleneinrichtung", ("Pauschal", 3500)),
    ("bauleitung", ("Pauschal", 8500)),
    ("honorar", ("Pauschal", 6000)),
    ("versicherung", ("Pauschal", 1200)),
]

_DEFAULT = ("m2", 95)


def _detect_menge(text):
    """Liest Menge aus Text: '12 m2', '3 Stk', '1x 2-flüglig' -> 1."""
    m = re.search(r"(\d{1,4}[.,]?\d*)\s*(m2|m³|m3|m|stk|lfm|t|h|m1|m²)", text.lower())
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            return None
    # "1x 2-flueglig" -> 1 stk
    m2 = re.search(r"(\d{1,3})\s*[x×]", text.lower())
    if m2:
        try:
            return float(m2.group(1))
        except ValueError:
            return None
    return None


def _ist_kostenposition(text):
    tl = (text or "").lower()
    if not tl.strip():
        return False
    # wenn ein gewerk-keywort drin ist -> ja
    for kw, _ in _PREISE:
        if kw in tl:
            return True
    # reine ueberschriften/verweise -> nein
    for k in _KEINE_KOSTEN:
        if k in tl:
            return False
    return False


def preis_fuer(text):
    """Liefert (einheit, ep_chf, menge_or_none) fuer eine Positions-Beschreibung."""
    tl = (text or "").lower()
    for kw, (einheit, ep) in _PREISE:
        if kw in tl:
            return einheit, ep, _detect_menge(text)
    return _DEFAULT[0], _DEFAULT[1], _detect_menge(text)


def bepreise_position(text):
    """Gibt (einheit, ep, menge, betrag) zurueck.

    Kostenlose Ueberschriften/Verweise -> (None, None, 0, 0).
    """
    if not _ist_kostenposition(text):
        return None, None, 0.0, 0.0
    einheit, ep, menge = preis_fuer(text)
    if menge is None:
        menge = 1.0 if einheit in ("Stk", "Pauschal", "t", "h") else 10.0
    betrag = round(menge * ep, 2)
    return einheit, ep, menge, betrag
