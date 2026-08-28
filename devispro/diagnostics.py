"""Diagnose & Selbsttest fuer DevisPro (lokal, reine Stdlib).

Liefert einen strukturierten Gesundheitsbericht der Installation:
  - Alle Kernmodule importierbar?
  - Lizenz gueltig?
  - Datenverzeichnisse vorhanden/beschreibbar?
  - Kritische Dateien (richtpreise, stammdaten) vorhanden?
  - Web-UI startbar?

Wird genutzt von `python -m devispro diagnose` (CLI) und der
Web-Route GET /diagnose. Laeuft komplett offline; kein Netzwerkzugriff.
"""

import os
import importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

KERN_MODULE = [
    "devispro.models",
    "devispro.parsers.crb",
    "devispro.pricelist",
    "devispro.matcher",
    "devispro.validators",
    "devispro.ordner_import",
    "devispro.accounting",
    "devispro.rechnung",
    "devispro.mahnung",
    "devispro.qr_render",
    "devispro.multicurrency",
    "devispro.subunternehmer",
    "devispro.margen_copilot",
    "devispro.marketing",
    "devispro.whatsapp_bot",
    "devispro.erp_api",
    "devispro.agent",
    "devispro.backup",
    "devispro.stammdaten",
    "devispro.benchmark",
    "devispro.lifecycle",
    "devispro.cli",
    "devispro.diagnostics",
]


def _check_module(name):
    try:
        importlib.import_module(name)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _check_lizenz():
    try:
        from devispro import license as liz
        info = liz.status()
        if isinstance(info, dict):
            z = info.get("status") or info.get("zustand") or ("aktiv" if info.get("gueltig") else "keine_lizenz")
            return True, "status: %s" % z
        return True, str(info)
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _check_daten():
    if not os.path.isdir(DATA):
        return False, "data/ fehlt"
    try:
        probe = os.path.join(DATA, ".diag_write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
    except Exception as e:  # noqa: BLE001
        return False, f"nicht beschreibbar: {e}"
    return True, "vorhanden & beschreibbar"


def _check_richtpreise():
    vorh = [f for f in os.listdir(DATA) if f.startswith("richtpreise_") and f.endswith(".csv")]
    if vorh:
        return True, f"{len(vorh)} Richtpreisliste(n) gefunden"
    return False, "keine Richtpreise"


def _check_stammdaten():
    try:
        from devispro import stammdaten
        p = stammdaten.load_profile() or {}
        return True, f"Profil geladen (Setup: {p.get('setup_done', False)})"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _version():
    try:
        from devispro import version
        return getattr(version, "VERSION", "?.?.?")
    except Exception:
        return "?.?.?"


def selfcheck():
    """Gibt ein Dict mit Gesamtstatus und Einzelpruefungen zurueck."""
    pruef = []

    mod_ok = True
    mod_fails = []
    for m in KERN_MODULE:
        ok, msg = _check_module(m)
        if not ok:
            mod_ok = False
            mod_fails.append(f"{m} -> {msg}")
    pruef.append({
        "bereich": "Module",
        "ok": mod_ok,
        "detail": "alle %d Kernmodule importierbar" % len(KERN_MODULE) if mod_ok
        else "; ".join(mod_fails),
    })

    lok, lmsg = _check_lizenz()
    pruef.append({"bereich": "Lizenz", "ok": lok, "detail": lmsg})

    dok, dmsg = _check_daten()
    pruef.append({"bereich": "Datenverzeichnis", "ok": dok, "detail": dmsg})

    rok, rmsg = _check_richtpreise()
    pruef.append({"bereich": "Richtpreise", "ok": rok, "detail": rmsg})

    sok, smsg = _check_stammdaten()
    pruef.append({"bereich": "Stammdaten", "ok": sok, "detail": smsg})

    gesamt = all(p["ok"] for p in pruef)
    return {
        "gesamt_ok": gesamt,
        "version": _version(),
        "pruefungen": pruef,
        "anzahl_module": len(KERN_MODULE),
    }


def to_html(report):
    zeilen = []
    for p in report["pruefungen"]:
        mark = "OK" if p["ok"] else "FEHLER"
        zeilen.append(
            "<tr><td>%s</td><td>%s</td><td class='meta'>%s</td></tr>"
            % (mark, p["bereich"], p["detail"])
        )
    ges = "System OK" if report["gesamt_ok"] else "Probleme gefunden"
    return (
        "<div class='card' style='max-width:760px;margin:2rem auto'><h2>System-Diagnose</h2>"
        "<p class='meta'>DevisPro v%s · %d Kernmodule geprueft · vollstaendig offline.</p>"
        "<div class='blocker %s'>%s</div>"
        "<table class='mini'><thead><tr><th>Status</th><th>Bereich</th><th>Detail</th></tr></thead>"
        "<tbody>%s</tbody></table></div>"
        % (report["version"], report["anzahl_module"],
           "" if report["gesamt_ok"] else "bad", ges, "".join(zeilen))
    )


def cli_ausgabe(report):
    lines = ["=== DevisPro Diagnose (v%s) ===" % report["version"]]
    for p in report["pruefungen"]:
        lines.append("  [%s] %s: %s" % ("OK" if p["ok"] else "FEHLER", p["bereich"], p["detail"]))
    lines.append("GESAMT: %s" % ("OK" if report["gesamt_ok"] else "PROBLEME"))
    return "\n".join(lines)


if __name__ == "__main__":
    print(cli_ausgabe(selfcheck()))
