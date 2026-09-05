import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devispro.parsers import crb, json_if
from devispro.pricelist import load as load_prices
from devispro.matcher import Matcher
from devispro.validators import validate
from devispro.monitor import list_portals, open_portal, import_ausschreibung
from devispro.sample_project import build_realistic_devis
from devispro import backup as backup_mod
from devispro import ordner_import as ordner_mod
from devispro import accounting as accounting_mod
from devispro import agent as agent_mod
from devispro import multicurrency as mc_mod
from devispro import stammdaten
from devispro import diagnostics as diag_mod
from devispro.parsers import crb as _crb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)


def _run_price(input_path, pricelist_path, output_path, fmt_in, out_fmt, method, threshold):
    devis = crb.parse(input_path) if fmt_in == "crb" else json_if.parse(input_path)
    prices = load_prices(pricelist_path)
    matcher = Matcher(method=method, threshold=threshold)

    review = 0
    for p in devis.positions:
        r = matcher.match(p, prices)
        p.ep = r.einheitspreis_chf
        p.matched_artikel = r.matched_artikel_id
        p.confidence = r.confidence
        p.requires_review = r.requires_review
        p.begruendung = r.begruendung
        p.fill()
        if p.requires_review:
            review += 1

    exporter_mod = crb if (out_fmt or fmt_in) == "crb" else json_if
    exporter_mod.export(devis, output_path)

    total = sum((p.betrag or 0.0) for p in devis.positions)
    cur = devis.meta.get("currency", "CHF")
    print(f"Devis bepreist: {len(devis.positions)} Positionen | Methode: {method}")
    print(f"  Projekt: {devis.meta.get('projekt', '-')} ({devis.meta.get('devis_nr', '-')})")
    print(f"  Gesamtbetrag (Netto): {total:,.2f} {cur}")
    print(f"  Manuelle Prüfung nötig: {review}")
    print(f"  Ausgabe ({out_fmt or fmt_in}): {output_path}")
    print()
    print(f"{'Pos':<10}{'Artikel':<10}{'EP CHF':>10}{'Menge':>9}{'Betrag':>12}  Review  Conf")
    print("-" * 72)
    for p in devis.positions:
        ep = f"{p.ep:,.2f}" if p.ep is not None else "  -  "
        bet = f"{p.betrag:,.2f}" if p.betrag is not None else "  -  "
        flag = "!" if p.requires_review else " "
        conf = f"{p.confidence:.2f}" if p.confidence is not None else "-"
        print(f"{p.pos_nr:<10}{str(p.matched_artikel):<10}{ep:>10}{p.menge:>9.2f}{bet:>12}  {flag:<7}{conf}")
    return devis


def cmd_price(args):
    _run_price(
        args.input, args.pricelist, args.output,
        args.format, args.output_format, args.method, args.threshold,
    )
    return 0


def cmd_demo(args):
    print("=== devispro DEMO: Sanierung MFH Zürich-Wiedikon ===\n")
    devis = build_realistic_devis()
    sample_crb = os.path.join(DATA, "devis_wiedikon.sia")
    sample_json = os.path.join(DATA, "devis_wiedikon.json")
    crb.export(devis, sample_crb)
    json_if.export(devis, sample_json)
    print(f"Beispiel-Devis erzeugt:\n  {sample_crb}\n  {sample_json}\n")

    print(f"Beispiel-Richtpreise: {args.pricelist}\n")
    _run_price(
        sample_crb, args.pricelist,
        os.path.join(DATA, "devis_wiedikon_bepreist.sia"),
        "crb", "crb", args.method, args.threshold,
    )

    out = os.path.join(DATA, "devis_wiedikon_bepreist.sia")
    issues = validate(out)
    print("\nValidierung der Sorba-Exportdatei:")
    if issues:
        for i in issues:
            print("  - FEHLER:", i)
        return 1
    print("  OK – Datei entspricht dem Referenzlayout (Sorba-Import bereit).")
    return 0


def cmd_portals(args):
    if args.open:
        url = open_portal(args.open, args.kanton)
        print(f"Öffne: {url}")
        return 0
    if getattr(args, "file", None):
        try:
            devis, did = import_ausschreibung(args.file, kanton=args.kanton, stichwort=args.stichwort or "")
        except Exception as e:
            print("FEHLER beim Import der Ausschreibung: %s" % e)
            return 1
        netto = sum((p.betrag or 0) for p in devis.positions)
        print("Ausschreibung importiert & bepreist -> Verlauf %s" % did)
        print("  %d Positionen | Netto %s CHF" % (len(devis.positions), f"{netto:,.2f}".replace(",", "'")))
        print("  Jetzt als Angebot: webui oeffnen -> Verlauf -> %s" % did)
        return 0
    list_portals()
    return 0


def cmd_validate(args):
    issues = validate(args.input)
    if issues:
        for i in issues:
            print("FEHLER:", i)
        return 1
    print("OK – Datei entspricht dem Referenzlayout.")
    return 0


def cmd_backup(args):
    zpath, man = backup_mod.create(label=args.label, note=args.note)
    ok, info = backup_mod.verify(zpath)
    print(f"Backup erstellt: {zpath}")
    print(f"  Dateien: {len(man['files'])} | Integrität: {info}")
    return 0 if ok else 1


def cmd_restore(args):
    n = backup_mod.restore(args.zip, DATA)
    ok, info = backup_mod.verify(args.zip)
    print(f"Wiederhergestellt: {n} Dateien | Integrität: {info}")
    return 0 if ok else 1


def cmd_ordner(args):
    devis, report = ordner_mod.analyse_ordner(args.ordner)
    devis = ordner_mod.passe_an(devis)
    print(f"Ordner analysiert: {args.ordner}")
    print(f"  Lesbare Dateien: {report['n_lesbar']}")
    print(f"  Manuell/Bild/PDF: {report['n_manuell']}")
    print(f"  Positionen erkannt: {report['n_positionen']}")
    for d in report["dateien"]:
        print(f"   - {d['datei']}: {d['status']} ({d['info']})")
    if args.output:
        crb.export(devis, args.output)
        print(f"  Devis gespeichert: {args.output}")
    return 0


def cmd_export(args):
    devis = _crb.parse(args.input)
    profil = stammdaten.load_profile()
    out = accounting_mod.export(args.system, devis, profil,
                                devis.meta.get("project_name") or "Offerte",
                                str(devis.meta.get("date", "") or ""))
    if args.output:
        if isinstance(out, bytes):
            with open(args.output, "wb") as f:
                f.write(out)
        else:
            open(args.output, "w", encoding="utf-8-sig").write(out)
        print(f"Export ({args.system}) -> {args.output} ({len(out.splitlines())} Zeilen)")
    else:
        sys.stdout.buffer.write(out) if isinstance(out, bytes) else print(out)
    return 0


def cmd_agent(args):
    ctx = {"lang": args.lang, "did": args.devis, "data_dir": DATA}
    r = agent_mod.chat(args.message, ctx)
    print(r["answer"])
    return 0


def cmd_waehrung(args):
    betrag = mc_mod.umrechnen(args.betrag, args.ziel)
    print(f"{args.betrag:,.2f} CHF = {mc_mod.format(args.ziel, betrag)} "
          f"(Kurs 1 CHF = {mc_mod.kurs_chf_nach(args.ziel):.4f} {args.ziel})")
    return 0


def cmd_lerne(args):
    """Lernt Richtpreise aus einem echten, bepreisten Devis -> Stammdaten."""
    from devispro import importers, pricelist as pl_mod
    path = args.datei
    if not os.path.exists(path):
        print("FEHLER: Datei nicht gefunden: %s" % path)
        return 1
    try:
        dev = importers.import_devis(path)
    except Exception as e:
        print("FEHLER beim Einlesen des Devis: %s" % e)
        return 1
    added = pl_mod.learn_from_devis(dev)
    print("Aus %s Positionen gelernt und %d neue Preise uebernommen." % (len(dev.positions), added))
    print("Ihre Richtpreisliste (data/meine_preise.csv) ist jetzt gefuellt.")
    return 0


def cmd_diagnose(args):
    report = diag_mod.selfcheck()
    print(diag_mod.cli_ausgabe(report))
    return 0 if report["gesamt_ok"] else 1


def cmd_werbe(args):
    """Verschickt die HTML-Werbe-Mail (ohne Anhang) an die angegebenen Empfaenger."""
    from devispro import license_admin as adm
    from devispro import marketing as marketing_mod
    adm._smtp_laden()
    if not adm.SMTP["host"]:
        print("FEHLER: Kein SMTP konfiguriert. Zuerst Hostinger/SMTP in der Web-UI speichern "
              "oder 'devispro smtp' nutzen.")
        return 1
    empfaenger = [e.strip() for e in args.empfaenger.split(",") if e.strip() and "@" in e]
    if not empfaenger:
        print("FEHLER: Mindestens ein gueltiger Empfaenger (enthaelt @) erforderlich.")
        return 1
    text, html = marketing_mod.werbe_mail_html(args.lang)
    fehler = []
    for e in empfaenger:
        ok = adm.mail_html(e, "DevisPro – Ihr SIA-451-Devis automatisch bepreisen", text, html)
        if not ok:
            fehler.append(e)
    if fehler:
        print("FEHLER: Versand an %s fehlgeschlagen (SMTP-Host/Passwort pruefen)." % ", ".join(fehler))
        return 1
    print("OK: Werbe-Mail (HTML, ohne Anhang) an %d Empfaenger gesendet: %s"
          % (len(empfaenger), ", ".join(empfaenger)))
    return 0


def cmd_erp(args):
    """DevisPro ERP: voll funktionsfaehiges ERP (nur bei Tarif 'erp')."""
    from devispro import erp as erp_mod
    from devispro import license as liz
    tarif = liz.tarif()
    if tarif != "erp":
        print("DevisPro ERP ist nur im Tarif 'DevisPro + ERP' verfuegbar.")
        print("Aktueller Tarif: %s" % tarif)
        print("Upgrade ueber Monterossa AG (info@devispro.de).")
        return 1
    a = args
    if a.aktion == "dashboard":
        d = erp_mod.dashboard()
        print("=== ERP Dashboard (%s) ===" % tarif)
        print("  Umsatz (Jahr):   %s CHF" % f"{d['umsatz_jahr']:,.2f}".replace(",", "'"))
        print("  Offene Posten:   %s CHF" % f"{d['offene_posten']:,.2f}".replace(",", "'"))
        print("  Lagerwert:       %s CHF" % f"{d['lagerwert']:,.2f}".replace(",", "'"))
        print("  Artikel: %d | Kunden: %d | Lieferanten: %d" % (d['artikel'], d['kunden'], d['lieferanten']))
        if d['nachbestellung']:
            print("  Nachbestellen:  %s" % ", ".join(d['nachbestellung']))
        mw = d["mwst"]
        print("  MWST-Abrechnung: geschuldet %s / Vorsteuer %s / Saldo %s CHF" % (
            f"{mw['mwst_geschuldet']:,.2f}".replace(",", "'"),
            f"{mw['vorsteuer']:,.2f}".replace(",", "'"),
            f"{mw['saldo_zahlbar']:,.2f}".replace(",", "'")))
    elif a.aktion == "list":
        if a.typ == "artikel":
            print("=== Artikel ===")
            for x in erp_mod.artikel_liste():
                print("  %s | %s | Bestand %s | EK %s | VK %s" % (x.nr, x.bezeichnung, x.bestand, x.ek_preis, x.vk_preis))
        elif a.typ == "partner":
            print("=== Partner ===")
            for x in erp_mod.partner_liste():
                print("  %s | %s | %s | offen %s" % (x.nr, x.name, x.typ, x.offen))
        else:
            print("=== Belege ===")
            for x in erp_mod.beleg_liste():
                print("  %s | %s | %s | Netto %s | %s" % (x.nr, x.typ, x.partner_name, x.netto(), "bezahlt" if x.bezahlt else "offen"))
    elif a.aktion == "neu":
        if a.typ == "artikel":
            art = erp_mod.artikel_ergaenzen(a.nr, a.name, a.einheit or "Stk",
                                            a.ek or 0.0, a.vk or 0.0, a.bestand or 0.0, a.mindest or 0.0)
            print("Artikel %s angelegt: %s (Bestand %s)" % (art.nr, art.bezeichnung, art.bestand))
        elif a.typ == "partner":
            p = erp_mod.partner_ergaenzen(a.nr, a.name, a.art or "kunde")
            print("Partner %s angelegt: %s (%s)" % (p.nr, p.name, p.typ))
    elif a.aktion == "rechnung":
        pos = [{"artikel_nr": a.artikel, "bezeichnung": a.name or a.artikel,
                "menge": a.menge, "einheit": a.einheit or "Stk", "ep": a.ep}]
        b = erp_mod.beleg_erstellen("rechnung", a.partner, a.partner_name or a.partner, pos)
        print("Rechnung %s erstellt: %s CHF (Netto)" % (b.nr, f"{b.netto():,.2f}".replace(",", "'")))
    elif a.aktion == "wareneingang":
        erp_mod.artikel_wareneingang(a.nr, a.menge)
        print("Wareneingang %s fuer %s erfasst." % (a.menge, a.nr))
    elif a.aktion == "zahlung":
        erp_mod.beleg_zahlung(a.nr, a.ep if a.ep else a.menge)
        print("Zahlung auf %s erfasst." % a.nr)
    elif a.aktion == "inventur":
        diff = erp_mod.inventur_erfassen(a.nr, a.menge)
        neu = next((x.bestand for x in erp_mod.artikel_liste() if x.nr == a.nr), None)
        print("Inventur %s: Korrektur %s (neuer Bestand %s)" % (a.nr, diff, neu))
    elif a.aktion == "status":
        erp_mod.beleg_status_setzen(a.nr, a.name or "versendet")
        print("Beleg %s -> Status %s" % (a.nr, a.name or "versendet"))
    elif a.aktion == "export":
        data = erp_mod.export_buchhaltung(a.nr, system=a.system or "csv")
        if a.output:
            open(a.output, "wb").write(data)
            print("Export (%s) -> %s (%d Bytes)" % (a.system or "csv", a.output, len(data)))
        else:
            sys.stdout.buffer.write(data)
    elif a.aktion == "reset":
        erp_mod.zuruecksetzen()
        print("ERP-Daten zurueckgesetzt.")
    else:
        print("Aktion '%s' unbekannt. Nutze: dashboard | list | neu | rechnung | "
              "wareneingang | zahlung | inventur | status | export | reset" % a.aktion)
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog="devispro",
        description="SIA-451-Devis automatisch mit Richtpreisen bepreisen (Sorba-Import), Kt. Zürich.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="Realistische End-to-End-Demo (MFH Zürich)")
    d.add_argument("--pricelist", default=os.path.join(DATA, "richtpreise_zh.csv"))
    d.add_argument("--method", choices=["local", "mock", "llm"], default="mock")
    d.add_argument("--threshold", type=float, default=0.6)
    d.set_defaults(func=cmd_demo)

    pr = sub.add_parser("price", help="Devis einlesen, bepreisen, ausgeben")
    pr.add_argument("--input", required=True)
    pr.add_argument("--pricelist", required=True)
    pr.add_argument("--output", required=True)
    pr.add_argument("--format", choices=["crb", "json"], default="crb")
    pr.add_argument("--output-format", choices=["crb", "json"], default=None)
    pr.add_argument("--method", choices=["local", "mock", "llm"], default="mock")
    pr.add_argument("--threshold", type=float, default=0.6)
    pr.set_defaults(func=cmd_price)

    po = sub.add_parser("portals", help="Ausschreibungs-Portale Kt. Zürich auflisten")
    po.add_argument("--kanton", default="Zürich")
    po.add_argument("--open", default=None, help="Portal öffnen: simap|devisio|olmero|baublatt|infobau")
    po.add_argument("--file", default=None, help="Heruntergeladene Ausschreibung (SIA/Bauweb/CSV/GAEB/PDF) importieren & bepreisen")
    po.add_argument("--stichwort", default="", help="Projektname für den Verlauf")
    po.set_defaults(func=cmd_portals)

    va = sub.add_parser("validate", help="SIA-451-Exportdatei prüfen")
    va.add_argument("--input", required=True)
    va.set_defaults(func=cmd_validate)

    ba = sub.add_parser("backup", help="Backup der KMU-Daten erstellen")
    ba.add_argument("--label", default=None)
    ba.add_argument("--note", default=None)
    ba.set_defaults(func=cmd_backup)

    re_ = sub.add_parser("restore", help="Backup wiederherstellen")
    re_.add_argument("--zip", required=True, help="Pfad zur Backup-ZIP")
    re_.set_defaults(func=cmd_restore)

    of = sub.add_parser("ordner", help="Ganzen Projektordner -> Devis")
    of.add_argument("--ordner", required=True)
    of.add_argument("--output", default=None, help="Devis als .sia speichern")
    of.set_defaults(func=cmd_ordner)

    ex = sub.add_parser("export", help="Devis in Buchhaltungssystem exportieren")
    ex.add_argument("--input", required=True, help="Bepreistes Devis (.sia)")
    ex.add_argument("--system", required=True, help="abacus|proffix|datev|bmd|banan|sap|...")
    ex.add_argument("--output", default=None, help="CSV-Datei (sonst stdout)")
    ex.set_defaults(func=cmd_export)

    ag = sub.add_parser("agent", help="KI-Agent (Frage oder Aktion)")
    ag.add_argument("message", help="z.B. 'setze MWST auf 7.7'")
    ag.add_argument("--devis", default=None)
    ag.add_argument("--lang", default="de")
    ag.set_defaults(func=cmd_agent)

    wa_ = sub.add_parser("waehrung", help="CHF in Zielwährung umrechnen")
    wa_.add_argument("--betrag", type=float, required=True)
    wa_.add_argument("--ziel", default="EUR", help="EUR|USD|GBP")
    wa_.set_defaults(func=cmd_waehrung)

    dg = sub.add_parser("diagnose", help="System-Selbsttest (Module/Lizenz/Daten)")
    dg.set_defaults(func=cmd_diagnose)

    wb = sub.add_parser("werbe", help="HTML-Werbe-Mail (ohne Anhang) versenden")
    wb.add_argument("empfaenger", help="Komma-getrennte Empfaenger, z.B. info@monterossa.ch,kunde@beispiel.ch")
    wb.add_argument("--lang", default="de", choices=["de", "fr", "it"])
    wb.set_defaults(func=cmd_werbe)

    ln = sub.add_parser("lerne", help="Richtpreise aus eigenem Devis lernen (Zero-Typing-Onboarding)")
    ln.add_argument("datei", help="Eigenes bepreites Devis (.sia/.crb/.csv/.xlsx/.xml)")
    ln.set_defaults(func=cmd_lerne)

    er = sub.add_parser("erp", help="DevisPro ERP (Tarif 'erp'): Lager, Verkauf, Buchhaltung")
    er.add_argument("aktion", help="dashboard|list|neu|rechnung|wareneingang|zahlung|inventur|status|export|reset")
    er.add_argument("--nr", default=None, help="Artikel/Partner/Beleg-Nr")
    er.add_argument("--name", default=None, help="Bezeichnung/Name oder Status-Wert")
    er.add_argument("--typ", default="artikel", help="artikel | partner | beleg (bei list)")
    er.add_argument("--art", default="kunde", help="kunde | lieferant (bei partner)")
    er.add_argument("--einheit", default=None)
    er.add_argument("--ek", type=float, default=0.0)
    er.add_argument("--vk", type=float, default=0.0)
    er.add_argument("--bestand", type=float, default=0.0)
    er.add_argument("--mindest", type=float, default=0.0)
    er.add_argument("--partner", default=None)
    er.add_argument("--partner_name", default=None)
    er.add_argument("--artikel", default=None)
    er.add_argument("--menge", type=float, default=1.0)
    er.add_argument("--ep", type=float, default=0.0)
    er.add_argument("--system", default="csv", help="Buchhaltungs-Export: abacus|proffix|csv|...")
    er.add_argument("--output", default=None, help="Export-Datei (sonst stdout)")
    er.set_defaults(func=cmd_erp)
    return p


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
