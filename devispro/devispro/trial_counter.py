"""Trial-/PPD-Zaehler fuer DevisPro (Preismodell v3 FINAL: 3-Tarif-Modell).

Zaehlt die finalisierten Devis ueber den bestehenden history-Speicher
(data/devis/devis_*/). Ein "Devis" zaehlt einmal: das ERSTE finalisierte
Speichern einer Offerte (Status != Entwurf, siehe Konzept Entscheidung 2).
Danach bearbeiten/neu bepreisen/Versionen erzeugen zaehlt nicht erneut.

Missbrauchsschutz: Marker-File data/.dp_state enthaelt einen SHA-256-Hash
ueber (kunde_id, anzahl, install_datum). Wird der Ordner einfach geleert,
passt der Hash nicht mehr -> status() meldet manipulation_verdaechtig=True
und die App faellt auf den gesicherten Stand im Marker zurueck.

ENTSCHEIDUNG (pragmatisch): Der Hash ist kein kryptographischer Schutz
gegen einen determinierten Angreifer, sondern eine Reibungs-Schwelle —
siehe Konzept Abschnitt D («Kontrolle, die dem ehrlichen Kunden im Weg
steht, kostet mehr Umsatz als sie vor Diebstahl schützt»).

Neu: Starter-Tarif (Pay-per-Devis) hat 5 Gratis-Devis, dann PPD.
Professional/Enterprise haben keine Zaehlung (unbegrenzt).
"""
import os
import json
import glob
import hashlib

from . import data_store as ds

DEVIS_DIR = os.path.join(ds.app_support_dir(), "devis")
STATE_PFAD = os.path.join(ds.app_support_dir(), ".dp_state")

GRATIS_DEVIS = 5  # Starter: erste 5 Devis kostenlos

# Statuswerte, die als "finalisiert/offerte" zaehlen (Entscheidung 2).
# Entwuerfe ("offen", "entwurf", "importiert") sind gratis und unbegrenzt.
ZAEHLende_STATUStextE = ("finalisiert", "offerte", "offerte erstellt",
                         "exportiert", "abgeschlossen")


def _hash(kunde_id: str, anzahl: int, install: str) -> str:
    basis = f"{kunde_id}|{anzahl}|{install}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _lade_state() -> dict:
    try:
        with open(STATE_PFAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _schreibe_state(state: dict) -> None:
    with open(STATE_PFAD, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _zaehle_ordner() -> int:
    """Anzahl history-Ordner mit zaehlendem Status."""
    if not os.path.isdir(DEVIS_DIR):
        return 0
    n = 0
    for mp in glob.glob(os.path.join(DEVIS_DIR, "devis_*", "meta.json")):
        try:
            with open(mp, encoding="utf-8") as f:
                m = json.load(f)
            if (m.get("status") or "").lower() in ZAEHLende_STATUStextE:
                n += 1
        except Exception:
            pass
    return n


def kunde_id() -> str:
    """Kunden-ID aus der Lizenz bzw. Profil-Fallback."""
    try:
        from devispro import license as liz
        lz = liz.lizenz_laden()
        if lz and lz.get("kunde_id"):
            return lz["kunde_id"]
    except Exception:
        pass
    return "LOKAL"


def install_datum() -> str:
    st = _lade_state()
    if not st.get("install"):
        st["install"] = __import__("time").strftime("%Y-%m-%d")
        _schreibe_state(st)
    return st["install"]


def _tarif_hat_limit() -> bool:
    """True wenn Starter (Pay-per-Devis) - nur da zaehlen wir."""
    try:
        from devispro import abo as abomod
        prod, _ = abomod.tarif_key()
        return prod == "starter"
    except Exception:
        return True  # fallback: zaehlen


def aktualisiere(status: str = None) -> dict:
    """Nach jedem save() aufrufen: Zaehler + Hash-Marker neu schreiben.
    Gibt den neuen Zaehlerstand zurueck."""
    # Nur zaehlen wenn Starter-Tarif
    if not _tarif_hat_limit():
        return {"anzahl": 0, "kunde_id": kunde_id()}

    kid = kunde_id()
    inst = install_datum()
    # Zaehlung: Ordner mit zaehlendem Status ODER (Fallback aelterer
    # Versionen ohne Status-Pflege) alle Ordner, wenn state das sagt.
    n = _zaehle_ordner()
    st = _lade_state()
    st["anzahl"] = max(n, int(st.get("anzahl", 0)))
    # Monotonie: ein geloeschter Ordner senkt den Zaehler NICHT (Marker)
    st["kunde_id"] = kid
    st["hash"] = _hash(kid, st["anzahl"], inst)
    st.setdefault("gesichert_anzahl", st["anzahl"])
    _schreibe_state(st)
    return {"anzahl": st["anzahl"], "kunde_id": kid}


def stand() -> dict:
    """Aktueller Zaehlerstand inkl. Plausibilitaetspruefung (.dp_state).

    ENTSCHEIDUNG: Wenn der Ordner-Inhalt vom Marker abweicht (Devis-Ordner
    einfach geloescht), gilt der HOEHERE der beiden Werte — Loeschen lohnt
    sich so nie, und ein legitimer Umzug/Konsolidierung wird nicht bestraft.
    """
    # Professional/Enterprise: unbegrenzt
    if not _tarif_hat_limit():
        return {
            "finalisierte_devis": 0,
            "gratis_uebrig": 999999,
            "manipulation_verdaechtig": False,
            "kunde_id": kunde_id(),
            "install": install_datum(),
            "unbegrenzt": True,
        }

    st = _lade_state()
    ordner_n = _zaehle_ordner()
    marker_n = int(st.get("anzahl", 0))
    anzahl = max(ordner_n, marker_n)
    manipulationsverdacht = False
    if st.get("hash"):
        erwartet = _hash(st.get("kunde_id", ""), marker_n, st.get("install", ""))
        manipulationsverdacht = (erwartet != st["hash"])
    else:
        # erster Lauf: State initialisieren
        r = aktualisiere()
        anzahl = r["anzahl"]
    return {
        "finalisierte_devis": anzahl,
        "gratis_uebrig": max(0, GRATIS_DEVIS - anzahl),
        "manipulation_verdaechtig": manipulationsverdacht,
        "kunde_id": st.get("kunde_id", kunde_id()),
        "install": st.get("install"),
        "unbegrenzt": False,
    }


def gratis_erlaubt() -> bool:
    """True solange das Gratis-Kontingent (5 Devis) nicht ausgeschöpft ist.
    Nur relevant für Starter-Tarif."""
    if not _tarif_hat_limit():
        return True  # Professional/Enterprise: immer erlaubt
    return stand()["finalisierte_devis"] < GRATIS_DEVIS


def reset_fuer_tests() -> None:
    """NUR fuer die Testsuite: Zaehler komplett zuruecksetzen (Marker +
    Devis-Ordner im Test-Datenverzeichnis leeren)."""
    if os.path.exists(STATE_PFAD):
        os.remove(STATE_PFAD)
    import shutil
    import glob as _glob
    for d in _glob.glob(os.path.join(DEVIS_DIR, "devis_*")):
        shutil.rmtree(d, ignore_errors=True)
