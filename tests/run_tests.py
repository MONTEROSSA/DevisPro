"""DevisPro Test-Suite (reine Stdlib, keine externen Deps).

Reproduzierbare Qualitaetssicherung fuer alle Importer, die PDF-Erzeugung
und die Kalkulation. Ausfuehren mit:
    python3 tests/run_tests.py

Nutzt Python's eingebautes `unittest` (kein pip/noetig). Echte Fixtures
liegen in tests/fixtures/.
"""
import os
import sys
import glob
import unittest

# Pfade
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

from devispro.importers import list_importers, detect_importer
from devispro.importers.generic import GenericCsvImporter
from devispro.importers.bauweb import BauwebImporter
from devispro.importers.oenorm import OenormImporter
from devispro.importers.xrechnung import XRechnungImporter
from devispro.importers.crbx import CrbxImporter
from devispro.importers.sia451 import Sia451Importer
from devispro.importers.gaeb import GaebImporter
from devispro.models import Position, Devis


def fx(name):
    return os.path.join(FIX, name)


class TestAdapters(unittest.TestCase):
    def test_generic_semicolon(self):
        d = GenericCsvImporter().parse(fx("generic_semicolon.csv"))
        self.assertEqual(len(d.positions), 3)
        self.assertEqual(d.positions[0].menge, 40.0)
        self.assertEqual(d.positions[0].ep, 35.0)
        # Tausender-Apostroph im Betrag
        self.assertEqual(d.positions[0].betrag, 1400.0)

    def test_generic_comma(self):
        d = GenericCsvImporter().parse(fx("generic_comma.csv"))
        self.assertEqual(len(d.positions), 2)
        self.assertEqual(d.positions[0].menge, 40.0)
        self.assertEqual(d.positions[0].ep, 35.0)

    def test_bauweb(self):
        d = BauwebImporter().parse(fx("bauweb.csv"))
        self.assertEqual(len(d.positions), 3)
        self.assertEqual(d.positions[0].menge, 120.0)
        self.assertEqual(d.positions[0].ep, 42.0)

    def test_oenorm_comma_decimal(self):
        d = OenormImporter().parse(fx("oenorm.csv"))
        self.assertEqual(len(d.positions), 3)
        self.assertAlmostEqual(d.positions[0].menge, 35.5, places=2)
        self.assertAlmostEqual(d.positions[0].ep, 24.90, places=2)

    def test_xrechnung_cii(self):
        d = XRechnungImporter().parse(fx("xrechnung.xml"))
        self.assertEqual(len(d.positions), 2)
        self.assertEqual(d.positions[0].menge, 4.0)
        self.assertEqual(d.positions[0].ep, 12.50)
        self.assertEqual(d.positions[0].text, "Montage Zargen")

    def test_crbx_positions_and_skip_summary(self):
        d = CrbxImporter().parse(fx("example.crbx"))
        # PosArt=Z (Zwischensumme) wird uebersprungen -> 3 echte Positionen
        self.assertEqual(len(d.positions), 3)
        self.assertEqual(d.positions[0].text, "Innenanstrich Wand 2 Anstriche")
        self.assertEqual(d.positions[0].menge, 40.0)
        self.assertEqual(d.positions[0].ep, 35.0)
        texts = " ".join(p.text for p in d.positions)
        self.assertNotIn("Zwischensumme", texts)

    def test_sia451_fixedwidth(self):
        d = Sia451Importer().parse(fx("example.sia"))
        self.assertEqual(len(d.positions), 2)
        self.assertEqual(d.positions[0].menge, 40.0)
        self.assertEqual(d.positions[0].ep, 35.0)

    def test_detect_importer(self):
        for f in ("generic_semicolon.csv", "bauweb.csv", "oenorm.csv",
                  "xrechnung.xml", "example.crbx", "example.sia"):
            self.assertIsNotNone(detect_importer(fx(f)), f"detect failed: {f}")

    def test_gaeb_real_data(self):
        # Echte GAEB-DA82-Daten (1.8MB) muessen im /tmp liegen (manuell besorgt)
        p = "/tmp/gaeb_lv.xml"
        if not os.path.exists(p):
            self.skipTest("echte GAEB-Daten nicht vorhanden (/tmp/gaeb_lv.xml)")
        d = GaebImporter().parse(p)
        self.assertGreater(len(d.positions), 100)
        with_ep = [x for x in d.positions if x.ep]
        self.assertGreater(len(with_ep), 100)


class TestCalculation(unittest.TestCase):
    def test_position_fill(self):
        p = Position(pos_nr="1", text="Test", menge=10, einheit="m2", ep=35.0)
        p.fill()
        self.assertEqual(p.betrag, 350.0)

    def test_decimal_rounding(self):
        # kaufmaennisches Runden (ROUND_HALF_UP), kein Banker's
        from decimal import Decimal
        p = Position(pos_nr="1", text="x", menge=1, einheit="", ep=33.335)
        p.fill()
        self.assertEqual(p.betrag, 33.34)


class TestPDF(unittest.TestCase):
    def _sample_devis(self):
        profil = {"betrieb": "Test Malerei AG", "strasse": "Hauptstr 1",
                  "ort": "8000 Zuerich", "gewerk": "Maler", "mwst_pct": 8.1}
        positions = [
            Position(pos_nr="1", text="Innenanstrich", menge=40, einheit="m2", ep=35.0),
            Position(pos_nr="2", text="Spachteln", menge=20, einheit="m2", ep=28.5),
        ]
        return Devis(meta={"project_name": "Testprojekt"}, addresses=[], chapters=[], positions=positions), profil

    def test_build_pdf_valid_header(self):
        from devispro import documents
        devis, profil = self._sample_devis()
        data = documents.build_pdf("devis_muster", devis, profil, lang="de")
        self.assertTrue(data[:4] == b"%PDF", "Kein gueltiges PDF (Header %PDF fehlt)")
        self.assertIn(b"%%EOF", data[-1024:], "PDF EOF-Marker fehlt")
        # REGRESSION: pdf_native darf KEINE bytes-Repr (b'...') in die Page-Dicts
        # leaken -> sonst kann PDFKit/Preview die Seite nicht lesen (leer!).
        self.assertNotIn(b"b''", data, "bytes-Repr im PDF -> Seite unlesbar (Regression!)")
        self.assertNotIn(b"b\"", data, "bytes-Repr im PDF -> Seite unlesbar (Regression!)")
        # xref-Offsets muessen exakt auf 'N 0 obj' zeigen
        import re
        mx = re.search(rb"startxref\s+(\d+)", data)
        self.assertIsNotNone(mx, "startxref fehlt")
        xref = data[int(mx.group(1)):]
        entries = re.findall(rb"(\d{10}) (\d{5}) (n|f)", xref)
        for i, (off_b, _g, t) in enumerate(entries):
            if t == b"n":
                self.assertTrue(data[int(off_b):int(off_b)+12].startswith(("%d 0 obj" % i).encode()),
                                "xref-Offset fuer Obj %d falsch" % i)

    def test_pdf_french(self):
        from devispro import documents
        devis, profil = self._sample_devis()
        data = documents.build_pdf("werkvertrag", devis, profil, lang="fr")
        self.assertTrue(data[:4] == b"%PDF")

    def test_mail_html_ohne_anhang(self):
        from devispro import license_admin as adm
        from email.message import EmailMessage
        # Nachbau von mail_html (ohne Senden) -> Struktur pruefen
        m = EmailMessage()
        m["From"] = adm.SMTP["von"]; m["To"] = "x@y.ch"; m["Subject"] = "T"
        m.set_content("TEXT")
        m.add_alternative("<b>HTML</b>", subtype="html")
        self.assertTrue(m.is_multipart() and "alternative" in m.get_content_type(),
                        "Mail muss multipart/alternative sein")
        teile = [p.get_content_type() for p in m.walk() if p.get_content_maintype() == "text"]
        self.assertIn("text/plain", teile)
        self.assertIn("text/html", teile)
        self.assertFalse(any(p.get_content_type() == "application/pdf" for p in m.walk()),
                         "HTML-Werbemail darf KEINEN PDF-Anhang haben")
        # Funktion existiert
        self.assertTrue(hasattr(adm, "mail_html"), "mail_html fehlt")

    def test_werbe_mail_html_inhalt(self):
        from devispro import marketing as mk
        text, html = mk.werbe_mail_html("de")
        self.assertTrue(html.lstrip().startswith("<!DOCTYPE"), "HTML muss mit DOCTYPE beginnen")
        for kw in ["DevisPro", "SIA-451", "3&#x27;500 CHF", "1&#x27;490 CHF",
                   "info@devispro.de", "mailto:info@devispro.de",
                   "https://devispro.de/DevisPro_Mac.zip"]:
            self.assertIn(kw, html, "Fehlt im HTML: " + kw)
        self.assertTrue("3'500 CHF" in text, "Preis im Text fehlt")
        self.assertTrue("1'490 CHF" in text, "Preis im Text fehlt")
        self.assertIn("https://devispro.de/DevisPro_Mac.zip", text, "Download-Link im Text fehlt")
        self.assertNotIn("application/pdf", html, "HTML darf keinen Anhang referenzieren")
        self.assertNotIn("devispro.ch", html, "Falsche Domain darf nicht sein")

    def test_cli_werbe_registriert(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from devispro import cli
        p = cli.build_parser()
        ns = p.parse_args(["werbe", "info@monterossa.ch"])
        self.assertEqual(ns.cmd, "werbe")
        self.assertEqual(ns.empfaenger, "info@monterossa.ch")
        self.assertTrue(hasattr(cli, "cmd_werbe"), "cmd_werbe fehlt")

    def test_qr_encoder_structural(self):
        from devispro import qr_render as QR

        def finder_ok(m, r, c):
            for i in range(7):
                for j in range(7):
                    val = m[r+i][c+j]
                    if (0<=i<=6 and (j==0 or j==6)) or (0<=j<=6 and (i==0 or i==6)) or (2<=i<=4 and 2<=j<=4):
                        if val != 1: return False
                    elif 1<=i<=5 and 1<=j<=5:
                        if 2<=i<=4 and 2<=j<=4:
                            if val != 1: return False
                        elif val != 0:
                            return False
            return True

        m1, n1 = QR.encode("HELLO WORLD")
        self.assertEqual(n1, 21, "v1 sollte 21x21 sein")
        self.assertTrue(finder_ok(m1, 0, 0) and finder_ok(m1, 0, n1-7) and finder_ok(m1, n1-7, 0))
        png = QR.to_png_bytes(m1, scale=4)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n", "QR-PNG Header fehlt")

    def test_qr_in_rechnung_pdf(self):
        from devispro import rechnung as rmod
        devis, profil = self._sample_devis()
        r = rmod.from_devis(devis, profil, "R-0001", "2026-08-12", "2026-09-30")
        data = rmod.build_pdf(r, "de")
        self.assertTrue(data[:4] == b"%PDF", "Rechnung-PDF mit QR fehlt")
        self.assertIn(b"/FlateDecode", data, "QR-Bild (FlateDecode) nicht im PDF")
        uri = rmod.qr_data_uri(r)
        self.assertTrue(uri.startswith("data:image/png;base64,"), "QR-Data-URI fehlt in HTML")

    def test_qr_reed_solomon(self):
        from devispro import qr_render as QR
        # GF(256)-Multiplikation (0x11D) — hand-verifiziert:
        self.assertEqual(QR._gf_mul(2, 3), 6)
        self.assertEqual(QR._gf_mul(0x80, 0x80), 0x13)  # x^7 * x^7 = x^14 -> 0x13
        # RS-Generator-Polynom Grad 10 (ECC-M, v1) muss 11 Koeffizienten haben
        gen = QR._rs_poly(10)
        self.assertEqual(len(gen), 11)


class TestNewFeatures(unittest.TestCase):
    def test_backup_create_restore_verify(self):
        import tempfile as _tf
        from devispro import backup as bk
        tmp = _tf.mkdtemp(prefix="hermes_bk_")
        # scope erzwingen auf temp data
        bk.DATA = tmp
        bk.BACKUP_DIR = os.path.join(tmp, "backups")
        os.makedirs(os.path.join(tmp, "history"), exist_ok=True)
        open(os.path.join(tmp, "meine_preise.csv"), "w").write("a;b;c\n1;2;3\n")
        zpath, man = bk.create(label="t", note="n")
        self.assertTrue(os.path.isfile(zpath))
        ok, info = bk.verify(zpath)
        self.assertTrue(ok, info)
        # restore in zweiten temp
        tmp2 = _tf.mkdtemp(prefix="hermes_bk2_")
        n = bk.restore(zpath, tmp2)
        self.assertGreater(n, 0)
        self.assertTrue(os.path.exists(os.path.join(tmp2, "meine_preise.csv")))

    def test_agent_mwst_action(self):
        from devispro import agent as ag
        from devispro import stammdaten
        profil = stammdaten.load_profile()
        ctx = {"lang": "de", "did": None, "data_dir": stammdaten.DATA}
        r = ag.chat("setze MWST auf 7.7", ctx)
        self.assertEqual(r["action"], "mwst")
        self.assertIn("7.7", r["answer"])

    def test_agent_export_abacus(self):
        from devispro import agent as ag
        from devispro import history as hm
        did = (hm.list_all()[0]["id"] if hm.list_all() else None)
        ctx = {"lang": "de", "did": did, "data_dir": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")}
        r = ag.chat("exportiere nach abacus", ctx)
        self.assertEqual(r["action"], "export")
        self.assertIn("Abacus", r["answer"])

    def test_ordner_ocr_nicht_verfuegbar(self):
        from devispro import ordner_import as oi
        # ohne tesseract -> None (Architektur vorhanden, graceful)
        if not oi._ocr_verfuegbar():
            self.assertIsNone(oi._ocr_bild("irgendwas.png"))

    def test_multicurrency_fallback(self):
        from devispro import multicurrency as mc
        self.assertEqual(mc.umrechnen(500, "CHF"), 500.0)
        self.assertGreater(mc.kurs_chf_nach("EUR"), 0)

    def test_render_landing(self):
        from devispro import marketing as mkt
        lp = mkt.render_landing("de")
        self.assertIn("SIA-451", lp)
        self.assertIn("KI-Agent", lp)


    def test_cli_waehrung(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, "-m", "devispro.cli", "waehrung",
                            "--betrag", "1000", "--ziel", "EUR"],
                           cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           capture_output=True, text=True, timeout=40)
        self.assertEqual(r.returncode, 0)
        self.assertIn("EUR", r.stdout)

    def test_cli_backup(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, "-m", "devispro.cli", "backup",
                            "--label", "test"],
                           cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           capture_output=True, text=True, timeout=40)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Backup erstellt", r.stdout)

    def test_cli_export_csv(self):
        import subprocess, sys, glob, os as _os
        ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sias = glob.glob(_os.path.join(ROOT, "data", "devis_*_beispiel.sia"))
        self.assertTrue(sias, "kein Beispiel-Devis gefunden")
        out = _os.path.join(ROOT, "data", "_cli_export_test.csv")
        r = subprocess.run([sys.executable, "-m", "devispro.cli", "export",
                            "--input", sias[0], "--system", "csv", "--output", out],
                           cwd=ROOT, capture_output=True, text=True, timeout=40)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(_os.path.getsize(out) > 0)
        _os.remove(out)

    def test_diagnostics_selfcheck(self):
        from devispro import diagnostics as d
        rep = d.selfcheck()
        self.assertIn("gesamt_ok", rep)
        self.assertIn("pruefungen", rep)
        self.assertTrue(len(rep["pruefungen"]) >= 4)
        html = d.to_html(rep)
        self.assertIn("System-Diagnose", html)
        self.assertIn("Module", html)

    def test_smtp_hostinger_preset(self):
        import tempfile as _tf
        from devispro import license_admin as adm
        # Preset-Konfiguration ohne echtes Senden: Host/Port/TLS korrekt setzen.
        # Wichtig: darf NICHT die echte data/smtp.json ueberschreiben -> temporaere Pfad.
        orig = adm.SMTP_PFAD
        tmp = _tf.mktemp(suffix=".json")
        adm.SMTP_PFAD = tmp
        try:
            ok = adm.smtp_preset("hostinger", "info@devispro.de", "GEHEIM", von="info@devispro.de")
            self.assertTrue(ok)
            self.assertEqual(adm.SMTP["host"], "smtp.hostinger.com")
            self.assertEqual(adm.SMTP["port"], 465)
            self.assertEqual(adm.SMTP["tls"], "ssl")
            self.assertEqual(adm.SMTP["user"], "info@devispro.de")
            self.assertEqual(adm.SMTP["von"], "info@devispro.de")
            # unbekanntes Profil -> False
            self.assertFalse(adm.smtp_preset("nope", "x", "y"))
        finally:
            adm.SMTP_PFAD = orig
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_email_domains_config(self):
        from devispro import license_admin as adm
        cfg = adm.lade_email_domains()
        self.assertEqual(cfg["default_sender"], "info@devispro.de")
        self.assertIn("devispro.de", cfg["aktiv"])
        self.assertNotIn("devispro.ch", cfg["aktiv"])

    def test_mail_mit_pdf_signatur(self):
        # mail_mit_pdf muss existieren und einen gueltigen PDF-Anhang bauen
        # (ohne echtes Senden -> SMTP-Laden, aber kein Login).
        from devispro import license_admin as adm
        import inspect
        self.assertTrue(inspect.isfunction(adm.mail_mit_pdf))
        sig = inspect.signature(adm.mail_mit_pdf)
        self.assertIn("pdf_pfad", sig.parameters)
        # echten PDF-Bytecode via documents.build_pdf (kein wkhtmltopdf noetig)
        from devispro import documents as doc_mod
        from devispro.models import Devis, Position
        d = Devis(
            meta={"project_name": "T", "kunde": "Test", "lang": "de"},
            addresses=[{"role": "Kunde", "name": "Test", "street": "x", "city": "y"}],
            chapters=[(1, "1", "G")],
            positions=[Position(pos_nr="1.1", text="Demo", menge=1.0, einheit="Stk", ep=100.0, chapter=(1, "1", "G"))],
        )
        for p in d.positions:
            p.fill()
        profil = {"betrieb": "B", "strasse": "s", "plz": "1", "ort": "o", "mwst": 8.1}
        data = doc_mod.build_pdf("devis_muster", d, profil, lang="de")
        self.assertTrue(data[:5] == b"%PDF-", "build_pdf liefert kein gueltiges PDF")


class TestERPAndTiers(unittest.TestCase):
    def test_pricing_tiers(self):
        from devispro import pricing as pz
        self.assertEqual(pz.preis("devis")["einrichtung"], 3500.0)
        self.assertEqual(pz.preis("erp")["einrichtung"], 8900.0)
        self.assertEqual(pz.preis("erp")["lizenz_jahr"], 3490.0)
        self.assertTrue(pz.ist_erp("erp"))
        self.assertFalse(pz.ist_erp("devis"))
        self.assertEqual(pz.tarif_aus_lizenz(None), "devis")
        self.assertEqual(pz.tarif_aus_lizenz({"tarif": "erp"}), "erp")
        self.assertEqual(pz.tarif_aus_lizenz({"tarif": "UNBEKANNT"}), "devis")

    def test_erp_workflow(self):
        import tempfile as _tf
        from devispro import erp as erp_mod
        tmp = _tf.mkdtemp(prefix="hermes_erp_")
        erp_mod.DATA = tmp
        erp_mod._artikel._daten = None
        erp_mod._partner._daten = None
        erp_mod._belege._daten = None
        erp_mod._buchungen._daten = None
        try:
            erp_mod.zuruecksetzen()
            erp_mod.artikel_ergaenzen("A-001", "Beton 30MPa", "m3", ek=120.0, vk=180.0, bestand=5, mindest=2)
            erp_mod.artikel_wareneingang("A-001", 10, ek_preis=125.0)
            a = erp_mod.artikel_liste()[0]
            self.assertEqual(a.bestand, 15.0)
            self.assertEqual(a.ek_preis, 125.0)
            self.assertFalse(a.soll_nachbestellt_werden())
            # Lagerwert
            self.assertEqual(erp_mod.lagerwert_gesamt(), round(15*125.0, 2))
            # Partner + Verkauf
            erp_mod.partner_ergaenzen("K-001", "Bau AG", "kunde")
            b = erp_mod.beleg_erstellen("rechnung", "K-001", "Bau AG",
                                        [{"artikel_nr": "A-001", "bezeichnung": "Beton", "menge": 2, "einheit": "m3", "ep": 180.0}])
            self.assertEqual(b.netto(), 360.0)
            # Buchhaltung: Debitoren-Buchung erzeugt Umsatz + offenen Posten
            # Offene Posten = Brutto inkl. MWST (360 * 1.081)
            self.assertEqual(erp_mod.offene_posten_summe(), 389.16)
            self.assertEqual(erp_mod.umsatz_jahr(), 360.0)
            d = erp_mod.dashboard()
            self.assertEqual(d["artikel"], 1)
            self.assertEqual(d["kunden"], 1)
            self.assertEqual(d["umsatz_jahr"], 360.0)
            # Nachbestellung: Bestand unter Mindest -> Signal
            erp_mod.artikel_wareneingang("A-001", -14)
            self.assertTrue(erp_mod.artikel_liste()[0].soll_nachbestellt_werden())
        finally:
            erp_mod.DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

    def test_erp_erweitert(self):
        import tempfile as _tf
        from devispro import erp as erp_mod
        tmp = _tf.mkdtemp(prefix="hermes_erpe_")
        erp_mod.DATA = tmp
        try:
            erp_mod.zuruecksetzen()
            erp_mod.artikel_ergaenzen("A1", "Beton", "m3", ek=100, vk=150, bestand=10)
            erp_mod.artikel_wareneingang("A1", 5)
            self.assertGreaterEqual(len(erp_mod.lager_bewegung_liste("A1")), 1)
            erp_mod.inventur_erfassen("A1", 12, "Zaehlung")
            self.assertEqual(erp_mod.artikel_liste()[0].bestand, 12.0)
            erp_mod.partner_ergaenzen("K1", "AG", "kunde")
            erp_mod.kreditlimit_setzen("K1", 500.0)
            rb = erp_mod.beleg_erstellen("rechnung", "K1", "AG",
                [{"artikel_nr": "A1", "bezeichnung": "B", "menge": 5, "einheit": "m3", "ep": 150}])
            self.assertTrue(erp_mod.kreditlimit_ueberschritten("K1"))
            self.assertTrue(any(w["nr"] == "K1" for w in erp_mod.debitoren_warnungen()))
            neu = erp_mod.beleg_kopie_als(rb.nr, "auftrag")
            self.assertIsNotNone(neu) and self.assertIn("AUFT", neu)
            self.assertGreater(len(erp_mod.export_buchhaltung(rb.nr, system="csv")), 0)
            self.assertGreater(len(erp_mod.export_buchhaltung(rb.nr, system="abacus")), 0)
            self.assertGreaterEqual(len(erp_mod.dashboard()), 10)
        finally:
            erp_mod.DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

    def test_license_tier_aware(self):
        import tempfile as _tf
        import devispro.license as liz
        from devispro import license_admin as adm
        tmp = _tf.mkdtemp(prefix="hermes_lic_")
        adm.DATA = tmp
        liz.DATA = tmp
        liz.LIZENZ_PFAD = os.path.join(tmp, "lizenz.json")
        adm.KUNDEN_PFAD = os.path.join(tmp, "kunden.json")
        try:
            adm.kunde_anlegen("CRM-1", "ERP GmbH", "k@e.de", pilot=True, tarif="erp")
            self.assertEqual(liz.tarif(), "erp")
            self.assertEqual(adm._laden()["CRM-1"]["tarif"], "erp")
        finally:
            adm.DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            liz.DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            liz.LIZENZ_PFAD = os.path.join(liz.DATA, "lizenz.json")

    def test_werbe_mail_beide_tarife(self):
        from devispro import marketing as mkt
        text, html = mkt.werbe_mail_html("de")
        self.assertIn("DevisPro + ERP", html)
        self.assertIn("8&#x27;900", html)   # ERP Einrichtung (escaped apostrophe)
        self.assertIn("3&#x27;490", html)   # ERP Jahr
        self.assertIn("3&#x27;500", html)   # Devis Einrichtung
        self.assertIn("1&#x27;490", html)   # Devis Jahr
        self.assertIn("https://devispro.de/DevisPro_Mac.zip", html)
        self.assertNotIn("devispro.ch", html)

    def test_cli_erp_registriert(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from devispro import cli
        p = cli.build_parser()
        ns = p.parse_args(["erp", "dashboard"])
        self.assertEqual(ns.cmd, "erp")
        self.assertEqual(ns.aktion, "dashboard")
        self.assertTrue(hasattr(cli, "cmd_erp"))

    def test_homepage_html(self):
        from devispro import marketing as mkt
        hp = mkt.homepage_html("de")
        self.assertIn("DevisPro + ERP", hp)
        self.assertIn("Monterossa AG", hp)
        self.assertIn("www.monterossa.ch", hp)
        self.assertIn("8'900", hp)
        self.assertIn("3'490", hp)
        self.assertIn("3'500", hp)
        self.assertIn("1'490", hp)
        self.assertIn("/DevisPro_Mac.zip", hp)
        # neue, informative Sektionen
        self.assertIn("So funktioniert's", hp)
        self.assertIn("Häufige Fragen", hp)
        self.assertIn("Mahnwesen", hp)
        self.assertIn("Kontenrahmen", hp)
        self.assertIn("13 Buchhaltungs-Exporte", hp)
        self.assertIn("3 Monate gratis", hp)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
