"""Firmen-eigene Leistungspreise (echte Offerten-Bepreisung).

Das KMU pflegt EINMALIG sein Leistungsverzeichnis:
    bkp;bezeichnung;einheit;ep_chf;stundensatz_chf;kosten_chf;kategorie
oder ueber das Formular / CSV-/Excel-/PDF-Import.

Beim Import einer Ausschreibung (.crbx/SIA/GAEB/...) wird jede fremde
Position gegen diese Liste gematcht:
  1) exakte BKP/NPK-Nummer  (praezise)
  2) Fuzzy-Text (token-ueberschneidung, laengster Treffer)
  3) Stundenlohn-Positionen: stundensatz * zeit = betrag
Fallback (kein Treffer) -> Position als 'unbepreist' markieren,
NICHT still simulieren.
"""
import os
import csv
import re

from . import data_store as ds

PATH = ds.PREISE_PATH

_COLS = ["bkp", "bezeichnung", "einheit", "ep_chf", "stundensatz_chf", "kosten_chf", "kategorie"]


def _norm(s):
    return (s or "").strip().lower()


# Fuellwoerter, die beim Text-Matching nichts aussagen (Orts-/Projektangaben,
# Geschosse, Qualitaetsstufen). Werden nicht als Treffer-Tokens gezaehlt.
_STOPWORTE = {
    "neubau", "umbau", "sanierung", "renovation", "projekt", "mfh", "efh",
    "eg", "og", "dg", "ug", "kg", "erdgeschoss", "obergeschoss",
    "dachgeschoss", "keller", "kellergeschoss", "bad", "badegeschoss",
    "wohnzimmer", "schlafzimmer", "kinderzimmer", "arbeitszimmer", "zimmer",
    "kueche", "empfangsbereich", "nordseite", "suedseite", "ostseite",
    "westseite", "podest", "hauseingang", "terrassenueberdachung",
}

# Synonyme: Architekten-Kurztitel verwenden oft andere Woerter als die
# eigene Preisliste. Vor dem Tokenisieren werden Fachsynonyme vereinheitlicht.
_SYNONYME = [
    ("teppichboden", "teppich bodenbelag"),
    ("velours", "teppich bodenbelag"),
    ("vinyl klick", "designbelag vinyl"),
    ("vinyl", "designbelag"),
    ("mosaik", "fliesen mosaik"),
    ("steckdosenanschluss", "steckdose"),
    ("steckdosen", "steckdose"),
    ("schalteranschluss", "schalter"),
    ("netzerkdose", "netzwerkdose"),
    ("netzwerkdosen", "netzwerkdose"),
    ("aussenleuchte", "aussenleuchten"),
    ("leitungsziehen", "leitung ziehen"),
    ("ht anbindung", "abwasser ht"),
    ("pex leitung", "wasserleitung pex"),
    ("pex zuleitung", "wasserleitung pex"),
    ("designheizkoerper", "heizkoerper"),
    ("innendaemmung", "daemmung innen"),
    ("tu unterkonstruktion", "unterkonstruktion"),
    ("gaube ausbauen", "gaubenausbau"),
    ("anstrichfertig", "spachteln anstrich"),
    ("grund+deck", "grundierung deckanstrich"),
    ("q4 spachtelarbeit", "spachtelarbeiten q4"),
]


def _norm_syn(s):
    """Normierung inkl. Synonym-Vereinheitlichung (fuer Matching)."""
    t = _norm(s)
    for alt, neu in _SYNONYME:
        if alt in t:
            t = t.replace(alt, neu)
    return t


def _tokenize(s):
    return set(re.findall(r"[a-zäöü0-9]+", _norm(s)))


def _tokenize_match(s):
    """Tokens fuers Matching: mit Synonymen + ohne Stopworte."""
    return {t for t in re.findall(r"[a-zäöü0-9]+", _norm_syn(s))
            if t not in _STOPWORTE}


def laden():
    """Liest die eigene Preisliste -> Liste von Dictionaries."""
    if not os.path.exists(PATH):
        return []
    out = []
    with open(PATH, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            d = {_norm(k): v for k, v in row.items() if k}
            bez = (d.get("bezeichnung") or d.get("text") or d.get("artikel")
                   or d.get("positionsbezeichnung") or d.get("pos") or "").strip()
            if not bez:
                continue
            einh = (d.get("einheit") or d.get("me") or "").strip()
            ep = _to_float(d.get("ep_chf") or d.get("ep") or d.get("epreis")
                           or d.get("einheitspreis") or d.get("chf") or "")
            std = _to_float(d.get("stundensatz_chf") or d.get("stundensatz") or "")
            kosten = _to_float(d.get("kosten_chf") or d.get("kosten") or "")
            bkp = (d.get("bkp") or d.get("npk") or d.get("kapitel") or "").strip()
            kat = (d.get("kategorie") or d.get("gewerk") or "").strip()
            out.append({
                "bkp": bkp.replace(".", ""),
                "bez": bez.lower(),
                "tokens": _tokenize_match(bez),
                "einheit": einh,
                "ep": ep,
                "stundensatz": std,
                "kosten": kosten,
                "kategorie": kat.lower(),
            })
    return out


def _to_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace("'", "").replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return None


def preis_fuer(text, bkp=None, menge=None, einheit=None):
    """Liefert (einheit, ep, info) aus der eigenen Liste oder None.

    info = {'art': 'bkp'|'text'|'stunde', 'quelle': bez, 'confidence': 0..1}
    """
    preise = laden()
    if not preise:
        return None
    tl = _norm(text)
    bkp_clean = (bkp or "").replace(".", "")

    # 1) BKP / NPK exakt
    if bkp_clean:
        for p in preise:
            if p["bkp"] and p["bkp"] == bkp_clean:
                return _ergebnis(p, "bkp")

    # 2) Fuzzy-Text: groesste token-ueberschneidung (Synonyme + Stopworte
    #    beruecksichtigt, damit Architekten-Kurztitel ihre Firmenpreise treffen)
    best = None
    best_score = 0.0
    tt = _tokenize_match(text)
    for p in preise:
        if not p["tokens"] or not tt:
            continue
        overlap = len(p["tokens"] & tt)
        if overlap == 0:
            continue
        # score: treffer-tokens / kleinere token-menge (0..1)
        score = overlap / min(len(p["tokens"]), len(tt))
        if score > best_score:
            best_score = score
            best = p
        elif score == best_score and score > 0 and best is not None:
            # Tiebreak bei Gleichstand: Kandidat mit MEHR absoluten
            # Treffer-Tokens gewinnt (spezifischer); dann der, dessen
            # Bezeichnung MEHR gemeinsame Substanz mit dem Suchtext hat —
            # konkret: laengster gemeinsamer Token (z.B. 'rahmenwerk' im
            # Suchtext schlaegt 'dachstock', weil beide Woerter des
            # Suchtexts in Kombination auf Holzkonstruktion passen).
            # Letzter Tiebreak: kuerzere Bezeichnung.
            ov_best = len(best["tokens"] & tt)
            if overlap > ov_best:
                best = p
            elif overlap == ov_best:
                max_tok_p = max((t2 for t2 in p["tokens"] & tt), key=len)
                max_tok_b = max((t2 for t2 in best["tokens"] & tt), key=len)
                if len(max_tok_p) > len(max_tok_b):
                    best = p
    if best and best_score >= 0.30:   # schwelle gegen zufallstreffer
        # (0.30 statt 0.34: mit Synonym-/Stopwort-Matching sind Treffer nun
        # praeziser, knapp verwandte Kurztitel wie 'LED Spots' oder
        # 'Teppichboden Schlafräume' sollen ihren Firmenpreis finden)
        return _ergebnis(best, "text", best_score)

    return None


# --- CH-Referenzschätzung fuer nicht erfasste Positionen ------------------
# Grobe Marktwerte (CH-Baustelle, inkl. MWST-frei, nur Richtwert).
# Wird NUR verwendet, wenn KEIN eigener Preis existiert -> immer als
# 'schaetzung' markieren, damit der KMU prueft.
_REF_GEWERK = {
    "mauerwerk": 120.0, "wand": 85.0, "decke": 95.0, "boden": 75.0,
    "anstrich": 42.0, "farbe": 42.0, "putz": 55.0, "isolier": 60.0,
    "daemm": 60.0, "elektro": 95.0, "strom": 95.0, "sanitaer": 110.0,
    "wasser": 110.0, "heizung": 130.0, "lüftung": 120.0, "luftung": 120.0,
    "spengler": 105.0, "dach": 90.0, "fenster": 350.0, "tuer": 280.0,
    "trockenbau": 70.0, "abdicht": 65.0, "erdbau": 80.0, "belag": 70.0,
    "montage": 90.0, "demontage": 70.0, "reinigung": 45.0, "geruest": 35.0,
    "abbruch": 75.0, "aufgrabung": 80.0, "kran": 150.0, "transport": 60.0,
}


def _gewerk_aus_text(text):
    t = _norm(text)
    for g in _REF_GEWERK:
        if g in t:
            return g
    return "sonstiges"


_REF_SONST = 80.0


# --- Marktrichtpreise aus der Agenten-Recherche (Richtpreis-Forscher + ---
# --- Inspektor, wöchentlich aktualisiert & geprüft). Diese DB hat VOR-   ---
# --- RANG vor den groben internen Referenzwerten: Nur Einträge mit       ---
# --- geprueft:true werden verwendet. --------------------------------------
_RICHTPREISE_PATH = os.path.join(
    os.path.expanduser("~"), ".hermes", "workspace", "richtpreise.json")


def _richtpreise_laden():
    """Liest die geprueften Marktrichtpreise der Agenten (falls vorhanden).

    Liefert Liste von dicts: {"schlagwort", "ep", "ep_min", "ep_max",
    "einheit", "gewerk", "quelle"} — nur gepruefte Eintraege.
    """
    if not os.path.exists(_RICHTPREISE_PATH):
        return []
    try:
        import json
        with open(_RICHTPREISE_PATH, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for gewerk, eintraege in db.items():
        if gewerk == "stand" or not isinstance(eintraege, dict):
            continue
        for schlüssel, e in eintraege.items():
            if not isinstance(e, dict) or not e.get("geprueft"):
                continue
            ep = _to_float(e.get("ep"))
            if ep is None or ep <= 0:
                continue
            out.append({
                "schlagwort": schlüssel,
                "tokens": _tokenize_match(schlüssel),
                "ep": ep,
                "ep_min": _to_float(e.get("ep_min")),
                "ep_max": _to_float(e.get("ep_max")),
                "einheit": (e.get("einheit") or "").strip(),
                "gewerk": gewerk,
                "quelle": e.get("quelle") or "",
            })
    return out


def _marktpreis_fuer(text, richtpreise):
    """Beste Token-Uebereinstimmung gegen die Richtpreis-DB.

    Nutzt dasselbe Matching (Synonyme/Stopworte/Tiebreak) wie preis_fuer.
    Liefert (dict, score) oder (None, 0.0).
    """
    tt = _tokenize_match(text)
    if not tt:
        return None, 0.0
    best = None
    best_score = 0.0
    for p in richtpreise:
        if not p["tokens"]:
            continue
        overlap = len(p["tokens"] & tt)
        if overlap == 0:
            continue
        score = overlap / min(len(p["tokens"]), len(tt))
        if score > best_score:
            best_score = score
            best = p
        elif score == best_score and best is not None:
            ov_b = len(best["tokens"] & tt)
            if overlap > ov_b:
                best = p
            elif overlap == ov_b:
                max_p = max((t for t in p["tokens"] & tt), key=len)
                max_b = max((t for t in best["tokens"] & tt), key=len)
                if len(max_p) > len(max_b):
                    best = p
    if best and best_score >= 0.40:   # strenger als Firmenpreis-Matching:
        return best, best_score       # Schaetzungen muessen sicher sein
    return None, 0.0


def bepreise_position(text, einheit=None):
    """Liefert (einheit, ep, info) als CH-Schaetzung fuer fehlende Positionen.

    Reihenfolge:
      1) Gepruefter Marktrichtpreis aus der Agenten-DB (Quelle angegeben,
         Spanne min/max) -> art 'marktrichtpreis'
      2) Grober interner CH-Referenzwert -> art 'schaetzung' (wie bisher)

    Wird AUSSCHLIESSLICH aufgerufen, wenn kein eigener Preis existiert.
    Der Rueckgabe-Preis ist ein Schätzwert und muss vom KMU geprueft werden.
    """
    # 1) Markt-Richtpreise der Agenten (geprueft) haben Vorrang
    hit = _marktpreis_fuer(text, _richtpreise_laden())
    if hit and hit[0] is not None:
        p, score = hit
        einh = einheit or p["einheit"] or "m2"
        info = {
            "art": "marktrichtpreis",
            "quelle": "Markt (%s): %s" % (p["gewerk"], p["quelle"] or "Agenten-Recherche"),
            "confidence": round(score, 2),
            "schaetzung": True,
        }
        if p["ep_min"] and p["ep_max"]:
            info["spanne"] = "%.2f–%.2f CHF" % (p["ep_min"], p["ep_max"])
        return einh, p["ep"], info

    # 2) Fallback: grober interner Referenzwert (wie bisher)
    gewerk = _gewerk_aus_text(text)
    ep = _REF_GEWERK.get(gewerk, _REF_SONST)
    einh = einheit or "m2"
    if gewerk in ("fenster", "tuer"):
        einh = "Stk"
    info = {"art": "schaetzung", "quelle": "CH-Referenz (%s)" % gewerk,
            "confidence": 0.0, "schaetzung": True}
    return einh, ep, info


def _ergebnis(p, art, confidence=1.0):
    # Stundenlohn-Position: wenn stundensatz gesetzt (und kein EP), dann als stunde markieren
    if p["stundensatz"] is not None and p["ep"] is None:
        art = "stunde"
    info = {"art": art, "quelle": p["bez"], "confidence": round(confidence, 2)}
    if p["stundensatz"] is not None and p["ep"] is None:
        info["stundensatz"] = p["stundensatz"]
    return p["einheit"] or "", p["ep"], info


def exists():
    return os.path.exists(PATH) and len(laden()) > 0


def speichern_aus_upload(fp):
    """Liest hochgeladene Preisliste (CSV/xlsx/db) und uebernimmt sie normalisiert
    in die eigene Preisdatei (7-Spalten, Semikolon). Gibt Anzahl zurueck."""
    ext = os.path.splitext(fp)[1].lower()
    os.makedirs(ds.app_support_dir(), exist_ok=True)
    if ext in (".xlsx", ".xls"):
        from . import preise_import as pi
        n = pi.import_xlsx(fp)
    elif ext in (".sqlite", ".db", ".sqlite3"):
        from . import preise_import as pi
        n = pi.import_sqlite(fp)
    elif ext == ".pdf":
        from . import preise_import as pi
        n = pi.import_pdf(fp)
    else:
        # csv/txt: zeilen uebernehmen + normalisiert schreiben
        zeilen = _lese_alle(fp)
        _schreiben(zeilen)
        n = len(zeilen)
    return n


def _lese_alle(fp):
    """Liest eine beliebige CSV (semi/komma, tolerante spalten) -> liste von dicts."""
    out = []
    with open(fp, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            d = {_norm(k): v for k, v in row.items() if k}
            bez = (d.get("bezeichnung") or d.get("text") or d.get("artikel")
                   or d.get("leistung") or "").strip()
            if not bez:
                continue
            ep = _to_float(d.get("ep_chf") or d.get("ep") or d.get("einheitspreis")
                          or d.get("preis") or d.get("chf") or "")
            std = _to_float(d.get("stundensatz_chf") or d.get("stundensatz") or "")
            einh = (d.get("einheit") or d.get("me") or "").strip()
            bkp = (d.get("bkp") or d.get("npk") or d.get("nummer") or "").strip()
            kat = (d.get("kategorie") or d.get("gewerk") or "").strip()
            out.append({
                "bkp": bkp, "bezeichnung": bez, "einheit": einh,
                "ep_chf": ("" if ep is None else ep),
                "stundensatz_chf": ("" if std is None else std),
                "kosten_chf": "", "kategorie": kat,
            })
    return out


def alle_zeilen():
    """Gibt rohe Liste von Dictionaries zurueck (fuer den Tabellen-Editor)."""
    if not os.path.exists(PATH):
        return []
    with open(PATH, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        r = csv.DictReader(f, delimiter=delim)
        cols = r.fieldnames or _COLS
        out = []
        for row in r:
            out.append({c: (row.get(c) or "") for c in cols})
        return out


def zeile_speichern(zeile: dict):
    """Haengt eine Preiszeile an (oder ersetzt, wenn bkp+bez gleich)."""
    zeilen = alle_zeilen()
    key = (zeile.get("bkp", "").strip().lower(), zeile.get("bezeichnung", "").strip().lower())
    for i, z in enumerate(zeilen):
        zk = (z.get("bkp", "").strip().lower(), z.get("bezeichnung", "").strip().lower())
        if zk == key:
            zeilen[i] = zeile
            _schreiben(zeilen)
            return
    zeilen.append(zeile)
    _schreiben(zeilen)


def zeile_loeschen(index: int):
    zeilen = alle_zeilen()
    if 0 <= index < len(zeilen):
        del zeilen[index]
        _schreiben(zeilen)


def _schreiben(zeilen: list):
    os.makedirs(ds.app_support_dir(), exist_ok=True)
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLS, delimiter=";")
        w.writeheader()
        for z in zeilen:
            w.writerow({c: z.get(c, "") for c in _COLS})
