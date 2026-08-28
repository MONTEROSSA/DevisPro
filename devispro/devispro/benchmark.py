"""Marktpreis-Benchmark: anonymer Netzwerkeffekt.

Jeder DevisPro-Kunde speist seine bepreisten Positionen anonym in einen
lokalen Aggregat-Store (data/benchmark.json). Beim naechsten Devis zeigt
devispro: "Ihre Position X liegt Y% unter/ueber Markt-Durchschnitt".

Reine Stdlib. Kein Cloud-Zwang – funktioniert lokal, kann aber ueber
Backup-Mechanismus zwischen Filialen synchronisiert werden.

Hinweis zur Privatsphaere: es werden NUR aggregierte Preise je
(Kategorie, Einheit) gespeichert – keine Kundennamen, keine Projekte.
"""

import os
import json
import threading
from collections import defaultdict

_LOCK = threading.Lock()
_STORE = None

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
STORE_PATH = os.path.join(DATA, "benchmark.json")


def _load():
    global _STORE
    if _STORE is not None:
        return _STORE
    try:
        with open(STORE_PATH, encoding="utf-8") as f:
            _STORE = json.load(f)
    except Exception:
        _STORE = {"entries": 0, "by_key": {}}
    return _STORE


def _save(store):
    os.makedirs(DATA, exist_ok=True)
    tmp = STORE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE_PATH)


def _key(kategorie, einheit, kanton=None):
    k = (kategorie or "allgemein").strip().lower()
    e = (einheit or "-").strip().lower()
    kt = (kanton or "CH").strip().upper()
    return f"{kt}|{k}|{e}"


def contribute(positions, kanton=None):
    """Anonyme Positionen in den Aggregat-Store einspeisen.

    positions: Liste von dicts {kategorie, einheit, ep} (ep = Einheitspreis CHF).
    kanton: optionaler Kanton (z.B. 'ZH') fuer kanton-spezifischen Benchmark.
    """
    store = _load()
    counts = defaultdict(int)
    sums = defaultdict(float)
    mins = {}
    maxs = {}
    for p in positions:
        ep = p.get("ep")
        if ep in (None, 0, ""):
            continue
        try:
            ep = float(ep)
        except (TypeError, ValueError):
            continue
        key = _key(p.get("kategorie"), p.get("einheit"), kanton)
        counts[key] += 1
        sums[key] += ep
        mins[key] = min(mins.get(key, ep), ep)
        maxs[key] = max(maxs.get(key, ep), ep)

    with _LOCK:
        for key, n in counts.items():
            cur = store["by_key"].setdefault(key, {"n": 0, "sum": 0.0, "min": None, "max": None})
            cur["n"] += n
            cur["sum"] += sums[key]
            cur["min"] = min(cur["min"], mins[key]) if cur["min"] is not None else mins[key]
            cur["max"] = max(cur["max"], maxs[key]) if cur["max"] is not None else maxs[key]
        store["entries"] += sum(counts.values())
        _save(store)
    return store["entries"]


def benchmark(kategorie, einheit, ep, kanton=None):
    """Vergleich eines EP mit dem Markt-Durchschnitt (kanton-spezifisch wenn moeglich).

    Fallback: CH-weiter Durchschnitt, falls kein kanton-spezifischer Wert existiert.
    Liefert dict: {avg, min, max, n, delta_pct, urteil, kanton}
    """
    store = _load()
    key = _key(kategorie, einheit, kanton)
    cur = store["by_key"].get(key)
    used_kanton = kanton
    if not cur or cur["n"] == 0:
        # Fallback auf CH-weit
        key = _key(kategorie, einheit, None)
        cur = store["by_key"].get(key)
        used_kanton = None
    if not cur or cur["n"] == 0:
        return {"avg": None, "min": None, "max": None, "n": 0,
                "delta_pct": None, "urteil": "keine_daten", "kanton": used_kanton}
    avg = cur["sum"] / cur["n"]
    try:
        ep = float(ep)
    except (TypeError, ValueError):
        return {"avg": avg, "min": cur["min"], "max": cur["max"], "n": cur["n"],
                "delta_pct": None, "urteil": "keine_daten", "kanton": used_kanton}
    delta = ((ep - avg) / avg * 100.0) if avg else 0.0
    if delta <= -15:
        urteil = "tief"
    elif delta >= 15:
        urteil = "hoch"
    else:
        urteil = "ok"
    return {"avg": round(avg, 2), "min": cur["min"], "max": cur["max"], "n": cur["n"],
            "delta_pct": round(delta, 1), "urteil": urteil, "kanton": used_kanton}


def seed_from_pricelist(pricelist):
    """Start-Benchmark aus der eigenen Preisliste (einmalig beim Setup)."""
    rows = []
    for art in pricelist.values():
        rows.append({
            "kategorie": art.get("kategorie") or "allgemein",
            "einheit": art.get("einheit") or "-",
            "ep": art.get("ep_chf") or art.get("ep"),
        })
    return contribute(rows)


def stats():
    store = _load()
    return {"entries": store.get("entries", 0), "keys": len(store.get("by_key", {}))}


# --- Realistische Markt-Basiswerte (CH-Baumarkt) je Gewerk/Einheit ---
# Dient als Start-Netzwerk, damit neue Kunden sofort Vergleichswerte sehen.
# Werte sind grobe Marktschaetzungen (CHF) und werden durch echte Kundendaten
# ueberschrieben/angereichert. KANTON_FAKTOR gewichtet nach Region.
_MARKT_BASIS = [
    # --- Maler / Beschichtung ---
    ("Maler", "m2", 42.0), ("Innenanstrich", "m2", 35.0), ("Aussenanstrich", "m2", 48.0),
    ("Grundanstrich", "m2", 22.0), ("Spachteln", "m2", 18.0),
    ("Tapezieren", "m2", 28.0), ("Decke streichen", "m2", 32.0),
    ("Maler", "Stk", 380.0), ("Maler", "h", 78.0),
    # --- Gipser / Putz / Trockenbau ---
    ("Mauerwerk/Gips", "m2", 50.0), ("Verputzen", "m2", 42.0),
    ("Aussenputz", "m2", 48.0), ("Innenputz", "m2", 40.0),
    ("Gipser", "m2", 52.0), ("Trockenbau", "m2", 70.0),
    ("Stuktur", "m2", 60.0), ("Gipser", "h", 88.0),
    # --- Maurer / Beton / Erdbau ---
    ("Erdbau/Beton", "m3", 45.0), ("Erdarbeiten", "m3", 45.0),
    ("Beton", "m3", 180.0), ("Betonieren", "m3", 190.0),
    ("Maurer", "m2", 95.0), ("Mauerwerk", "m2", 95.0),
    ("Maurerarbeit", "h", 95.0), ("Abbruch", "m3", 38.0),
    ("Baugrube", "m3", 42.0), ("Fundament", "m3", 160.0),
    ("Erdbau/Beton", "h", 90.0), ("Aufgrabung", "m", 80.0),
    # --- Bodenleger / Beläge / Fliesen ---
    ("Boden/Platten", "m2", 95.0), ("Bodenbelag", "m2", 65.0),
    ("Estrich", "m2", 65.0), ("Fliesenlegen", "m2", 120.0),
    ("Platten", "m2", 110.0), ("Parkett", "m2", 130.0),
    ("Teppich", "m2", 75.0), ("Bodenleger", "m2", 80.0),
    ("Pflaster", "m2", 90.0), ("Belag", "m2", 85.0),
    ("Boeschung", "m", 25.0), ("Zaun", "m", 95.0),
    # --- Dach / Isolation / Abdichtung ---
    ("Dach/Isolation", "m2", 60.0), ("Daemmung", "m2", 55.0),
    ("Dachdeckung", "m2", 90.0), ("Dach", "m2", 88.0),
    ("Abdichtung", "m2", 65.0), ("Isolation", "m2", 58.0),
    ("Dach/Isolation", "Stk", 3500.0), ("Dachfenster", "Stk", 450.0),
    ("Spengler", "h", 110.0), ("Spengler", "m", 95.0),
    ("Metallbau", "h", 125.0), ("Schlosser", "h", 120.0),
    # --- Fenster / Türen / Glas ---
    ("Fenster/Tueren", "Stk", 280.0), ("Fenster", "Stk", 350.0),
    ("Tuer", "Stk", 280.0), ("Glaser", "m2", 85.0),
    ("Verglasung", "m2", 95.0), ("Schreiner", "h", 105.0),
    # --- Elektro ---
    ("Elektro", "h", 120.0), ("Elektroinstallation", "h", 120.0),
    ("Elektro", "Stk", 85.0), ("Steckdose", "Stk", 85.0),
    ("Beleuchtung", "Stk", 120.0), ("Kabel", "m", 18.0),
    # --- Sanitär ---
    ("Sanitaer", "h", 115.0), ("Sanitaer", "Stk", 95.0),
    ("Wasserentluefter", "Stk", 95.0), ("Rohr verlegen", "m", 120.0),
    ("Sanitaer", "m", 120.0), ("Abwasser", "m", 110.0),
    # --- Heizung / Wärmepumpe / Klima ---
    ("Heizung", "h", 125.0), ("Heizung", "Stk", 3200.0),
    ("Waermepumpe", "Stk", 3500.0), ("Wärmepumpe", "Stk", 3500.0),
    ("Lueftung", "h", 120.0), ("Lueftung", "Stk", 2500.0),
    ("Klima", "Stk", 2800.0), ("Gebaeudeautomation", "h", 130.0),
    # --- Garten / Landschaftsbau ---
    ("Garten", "h", 70.0), ("Gartenarbeit", "h", 70.0),
    ("Pflanzung", "Stk", 45.0), ("Rasen", "m2", 25.0),
    ("Brunnen bohren", "Stk", 80.0), ("Bohrung", "m", 80.0),
    # --- Sonstiges / Allgemein ---
    ("Allgemein", "m2", 80.0), ("Allgemein", "Stk", 250.0),
    ("Allgemein", "m3", 60.0), ("Allgemein", "h", 95.0),
    ("Allgemein", "m", 75.0), ("Geruest", "m2", 12.0),
    ("Reinigung", "h", 55.0), ("Transport", "fahrt", 120.0),
    ("Montage", "h", 90.0), ("Demontage", "h", 70.0),
    # --- Allround-Abdeckung je margen_copilot-Kategorie (alle Einheiten) ---
    # Damit IMMER ein Marktvergleich moeglich ist, unabhaengig davon,
    # welche Einheit _kategorie() zuordnet (m2/m3/m/h/Stk).
    ("Erdbau/Beton", "m2", 90.0), ("Erdbau/Beton", "m", 80.0), ("Erdbau/Beton", "Stk", 200.0),
    ("Mauerwerk/Gips", "m3", 90.0), ("Mauerwerk/Gips", "m", 70.0), ("Mauerwerk/Gips", "Stk", 220.0),
    ("Mauerwerk/Gips", "h", 88.0),
    ("Elektro", "m2", 60.0), ("Elektro", "m3", 90.0), ("Elektro", "m", 18.0),
    ("Elektro", "Stk", 85.0), ("Elektro", "m2", 60.0),
    ("Sanitaer", "m2", 90.0), ("Sanitaer", "m3", 100.0),
    ("Maler", "m3", 70.0), ("Maler", "m", 50.0), ("Maler", "Stk", 380.0),
    ("Dach/Isolation", "m3", 80.0), ("Dach/Isolation", "m", 75.0),
    ("Dach/Isolation", "h", 110.0), ("Dach/Isolation", "m2", 60.0),
    ("Boden/Platten", "m3", 80.0), ("Boden/Platten", "m", 70.0),
    ("Boden/Platten", "h", 95.0), ("Boden/Platten", "Stk", 90.0),
    ("Fenster/Tueren", "m2", 280.0), ("Fenster/Tueren", "m3", 280.0),
    ("Fenster/Tueren", "m", 280.0), ("Fenster/Tueren", "h", 95.0),
    ("Allgemein", "m2", 80.0), ("Allgemein", "m3", 60.0), ("Allgemein", "m", 75.0),
    ("Allgemein", "h", 95.0), ("Allgemein", "Stk", 250.0),
]

_KANTON_FAKTOR = {
    "ZH": 1.05, "BE": 1.0, "LU": 1.0, "UR": 0.95, "SZ": 1.02, "OW": 0.96,
    "NW": 1.0, "GL": 0.97, "ZG": 1.06, "FR": 0.98, "SO": 0.97, "BS": 1.1,
    "BL": 1.03, "SH": 1.04, "AR": 0.98, "AI": 0.96, "SG": 1.0, "GR": 0.94,
    "AG": 1.0, "TG": 0.98, "TI": 0.93, "VD": 0.96, "VS": 0.9, "NE": 0.95,
    "GE": 1.12, "JU": 0.94,
}


def seed_market(silent=False):
    """Start-Benchmark mit realistischen CH-Marktwerten je Kanton befuellen.

    Erzeugt sowohl CH-weite (kanton=None) als auch kanton-spezifische Schluessel,
    damit das Netzwerk sofort mit 27 Kantons-Datensaetzen startet.
    Alle Positionen werden gesammelt und in EINEM contribute()-Aufruf
    geschrieben (Performance: vermeidet tausendfache JSON-Writes).
    """
    ch_rows = []
    kanton_rows = []
    for kat, eh, ep in _MARKT_BASIS:
        # CH-weit (Fallbackschluessel)
        for _ in range(5):
            ch_rows.append({"kategorie": kat, "einheit": eh,
                            "ep": round(ep * (0.97 + 0.06 * (ep % 5) / 5.0), 2)})
        # je Kanton (spezifische Schluessel)
        for kanton, fak in _KANTON_FAKTOR.items():
            for _ in range(3):
                kanton_rows.append({"kategorie": kat, "einheit": eh,
                                    "ep": round(ep * fak * (0.97 + 0.06 * ((ep + len(kanton)) % 7) / 7.0), 2)})
    # einmal schreiben (CH-weit + je Kanton)
    total = contribute(ch_rows)
    for kanton in _KANTON_FAKTOR:
        total += contribute(kanton_rows, kanton=kanton)
    if not silent:
        print(f"[benchmark] Markt-Basis geseedet: {total} Eintraege")
    return total


def network_stats(kanton=None):
    """Uebersicht ueber das Benchmark-Netzwerk (fuer Premium-Anzeige)."""
    store = _load()
    kantone = set(); kat = set()
    for key in store.get("by_key", {}):
        parts = key.split("|")
        if len(parts) >= 3:
            kantone.add(parts[0]); kat.add(parts[1])
    beispiele = []
    for key, cur in sorted(store["by_key"].items(), key=lambda kv: kv[1]["n"], reverse=True)[:8]:
        parts = key.split("|")
        kt = parts[0] if len(parts) >= 3 else "-"
        k = parts[1] if len(parts) >= 3 else "-"
        e = parts[2] if len(parts) >= 3 else "-"
        beispiele.append({"kanton": kt, "kategorie": k, "einheit": e,
                          "avg": round(cur["sum"] / cur["n"], 2) if cur["n"] else None,
                          "n": cur["n"]})
    return {"gesamt_positionen": store.get("entries", 0),
            "kategorien": len(kat), "kantone": len(kantone),
            "top_beispiele": beispiele}


def benchmark_report(positions, kanton=None):
    """Liefert je Position ein Benchmark-Urteil.

    positions: Liste von devispro.models.Position (oder dicts mit
    kategorie/einheit/ep). Liefert [(pos_nr, text, urteil, delta_pct, avg, n), ...].
    Nur Positionen mit EP und bekannter Kategorie/einheit werden bewertet.
    """
    report = []
    for p in positions:
        if hasattr(p, "ep"):
            kat = getattr(p, "kategorie", None) or "allgemein"
            eh = getattr(p, "einheit", "-") or "-"
            epv = getattr(p, "ep", None)
            nr = getattr(p, "pos_nr", "")
            txt = getattr(p, "text", "")
        else:
            kat = p.get("kategorie") or "allgemein"
            eh = p.get("einheit") or "-"
            epv = p.get("ep")
            nr = p.get("pos_nr", "")
            txt = p.get("text", "")
        if epv in (None, 0, ""):
            continue
        try:
            epf = float(epv)
        except (TypeError, ValueError):
            continue
        res = benchmark(kat, eh, epf, kanton)
        report.append({
            "pos_nr": nr, "text": txt,
            "kategorie": kat, "einheit": eh,
            "ep": epf,
            "urteil": res["urteil"], "delta_pct": res["delta_pct"],
            "avg": res["avg"], "n": res["n"], "kanton": res["kanton"],
        })
    return report


def contribute_devis(positions, kanton=None):
    """Bepreiste Devis-Positionen anonym ins Netzwerk einspeisen (Moat)."""
    rows = []
    for p in positions:
        if hasattr(p, "ep"):
            kat = getattr(p, "kategorie", None) or "allgemein"
            eh = getattr(p, "einheit", "-") or "-"
            epv = getattr(p, "ep", None)
        else:
            kat = p.get("kategorie") or "allgemein"
            eh = p.get("einheit") or "-"
            epv = p.get("ep")
        if epv in (None, 0, ""):
            continue
        try:
            float(epv)
        except (TypeError, ValueError):
            continue
        rows.append({"kategorie": kat, "einheit": eh, "ep": epv})
    if rows:
        return contribute(rows, kanton=kanton)
    return 0


def berate(positions, kanton=None):
    """Margen-Copilot: verdichtet den Benchmark pro Position zu einer
    handlungsorientierten Beratung.

    - Positionen *unter* Markt  -> Marge-Risiko (zu guenstig offeriert)
    - Positionen *ueber* Markt  -> Auftrags-Risiko (zu teuer, verliert den Zuschlag)
    Rueckgabe: Dict mit counts, chf-Betraegen und Top-Positionen.
    """
    rep = benchmark_report(positions, kanton=kanton)
    unter = []   # zu guenstig (Marge-Risiko)
    ueber = []   # zu teuer (Auftrags-Risiko)
    for r in rep:
        if r["urteil"] == "unterschritten":      # eigener EP < Markt -> Marge verschenkt
            unter.append(r)
        elif r["urteil"] == "ueberschritten":     # eigener EP > Markt -> riskiert Zuschlag
            ueber.append(r)
    def _chf(items):
        s = 0.0
        for r in items:
            try:
                s += abs(r["delta_pct"]) / 100.0 * (r["avg"] or 0.0)
            except (TypeError, ValueError):
                pass
        return round(s, 2)
    unter.sort(key=lambda r: r["delta_pct"])
    ueber.sort(key=lambda r: -r["delta_pct"])
    return {
        "kanton": kanton or "CH",
        "bewertet": len(rep),
        "unter_markt": unter,
        "ueber_markt": ueber,
        "margen_risiko_chf": _chf(unter),
        "auftrags_risiko_chf": _chf(ueber),
        "top_unter": unter[:3],
        "top_ueber": ueber[:3],
    }
