"""Verlauf der bepreisten Devis pro KMU.

Jedes bepreiste Devis wird unter data/devis/<id>/ abgelegt:
  - meta.json   : {id, name, datum, netto, status, method, kanton}
  - bepreist.sia : die final bepreiste SIA-Datei (fuer Download/Offerte)
  - review.json  : (optional) manuell gepruefte Positionen

So kann der KMU ein Devis spaeter erneut ansehen, drucken oder die
Sorba-Datei herunterladen – ohne dass es vom naechsten Upload ueberschrieben wird.
"""
import os
import json
import time
import shutil
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
DEVIS_DIR = os.path.join(DATA, "devis")


def _ensure():
    os.makedirs(DEVIS_DIR, exist_ok=True)


def _next_id():
    _ensure()
    existing = glob.glob(os.path.join(DEVIS_DIR, "devis_*"))
    return f"devis_{len(existing) + 1:04d}"


def save(devis, netto, name=None, method="mock", kanton="ZH", status="offen"):
    """Speichert ein bepreites Devis im Verlauf. Gibt die id zurueck."""
    _ensure()
    did = _next_id()
    ddir = os.path.join(DEVIS_DIR, did)
    os.makedirs(ddir, exist_ok=True)
    from devispro.parsers import crb
    crb.export(devis, os.path.join(ddir, "bepreist.sia"))
    meta = {
        "id": did,
        "name": name or f"{devis.meta.get('projekt', '')} {devis.meta.get('objekt', '')}".strip() or did,
        "datum": time.strftime("%Y-%m-%d %H:%M"),
        "netto": round(float(netto), 2),
        "status": status,
        "method": method,
        "kanton": kanton,
    }
    with open(os.path.join(ddir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    # Marktpreis-Benchmark: bepreiste Positionen anonym ins Netzwerk einspeisen
    try:
        from devispro import benchmark as _bm
        if _bm.stats()["entries"] == 0:
            _bm.seed_market(silent=True)
        _bm.contribute_devis(devis.positions, kanton=kanton)
    except Exception:
        pass
    return did


def list_all():
    _ensure()
    out = []
    for d in sorted(glob.glob(os.path.join(DEVIS_DIR, "devis_*")), reverse=True):
        mp = os.path.join(d, "meta.json")
        if os.path.exists(mp):
            try:
                m = json.load(open(mp, encoding="utf-8"))
                m["_dir"] = os.path.basename(d)
                out.append(m)
            except Exception:
                pass
    return out


def path_of(did, fname="bepreist.sia"):
    return os.path.join(DEVIS_DIR, did, fname)


def save_doc(did, typ, payload: bytes, ext="pdf"):
    """Speichert ein erzeugtes Dokument (Werkvertrag/Abnahme/Rechnung) dauerhaft
    unter data/devis/<id>/ ab und liefert den Dateipfad zurueck."""
    if not exists(did):
        return None
    fname = f"{typ}.{ext}"
    path = os.path.join(DEVIS_DIR, did, fname)
    with open(path, "wb") as f:
        f.write(payload)
    return path


def list_docs(did):
    """Liefert die gespeicherten Dokumente eines Devis als Liste von (typ, pfad)."""
    if not exists(did):
        return []
    out = []
    for fn in os.listdir(os.path.join(DEVIS_DIR, did)):
        if fn in ("bepreist.sia", "meta.json", "angebot.html"):
            continue
        if fn.endswith(".pdf") or fn.endswith(".html"):
            out.append((fn.rsplit(".", 1)[0], os.path.join(DEVIS_DIR, did, fn)))
    return sorted(out)


def exists(did):
    return os.path.isdir(os.path.join(DEVIS_DIR, did))


def delete(did):
    d = os.path.join(DEVIS_DIR, did)
    if os.path.isdir(d):
        shutil.rmtree(d)
        return True
    return False


def set_status(did, status):
    mp = os.path.join(DEVIS_DIR, did, "meta.json")
    if not os.path.exists(mp):
        return
    m = json.load(open(mp, encoding="utf-8"))
    m["status"] = status
    json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
