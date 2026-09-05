import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devispro.parsers import crb, json_if
from devispro.pricelist import load as load_prices
from devispro.matcher import Matcher
from devispro.validators import validate
from devispro.monitor import list_portals, open_portal
from devispro.sample_project import build_realistic_devis

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
    po.set_defaults(func=cmd_portals)

    va = sub.add_parser("validate", help="SIA-451-Exportdatei prüfen")
    va.add_argument("--input", required=True)
    va.set_defaults(func=cmd_validate)
    return p


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
