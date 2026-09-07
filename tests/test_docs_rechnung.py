"""Permanente Edge-Case-Tests fuer Dokumenten- und Rechnungs-Modul."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devispro.documents import build_pdf, build
from devispro.rechnung import (
    Rechnung, RechnungsPosition, Teilzahlung, from_devis, build_html, build_pdf as rech_pdf
)
from devispro.models import Devis
from devispro.parsers import crb


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIA = os.path.join(ROOT, "data", "devis_maler_beispiel.sia")


def _devis():
    return crb.parse(SIA)


def _profil():
    return {"betrieb": "Maler Muster AG", "gewerk": "Maler",
            "strasse": "Hauptstr 1", "ort": "8000 Zuerich", "mwst_pct": 8.1}


class TestDocumentsEdge(unittest.TestCase):
    def setUp(self):
        self.devis = _devis()
        self.profil = _profil()

    def test_pdf_header_valid(self):
        data = build_pdf("werkvertrag", self.devis, self.profil, "de")
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))

    def test_pdf_malformed_devis_empty_positions(self):
        d = Devis(meta={}, addresses=[], chapters=[], positions=[])
        data = build_pdf("werkvertrag", d, self.profil, "de")
        self.assertTrue(data.startswith(b"%PDF"))

    def test_pdf_abnahme_without_maengel(self):
        data = build_pdf("abnahme", self.devis, self.profil, "de", maengel=None)
        self.assertTrue(data.startswith(b"%PDF"))

    def test_pdf_fr_it(self):
        for lang in ("fr", "it"):
            data = build_pdf("devis_muster", self.devis, self.profil, lang)
            self.assertTrue(data.startswith(b"%PDF"))

    def test_build_unknown_typ(self):
        with self.assertRaises(ValueError):
            build("x", self.devis, self.profil, "de")


class TestRechnungEdge(unittest.TestCase):
    def setUp(self):
        self.devis = _devis()
        self.profil = _profil()
        # bepreise: ep/betrag setzen (echter Flow hat bepreistes Devis)
        for i, p in enumerate(self.devis.positions, start=1):
            p.ep = round(i * 10.5, 2)
            p.betrag = round(p.ep * (p.menge or 1.0), 2)

    def test_from_devis_sums(self):
        r = from_devis(self.devis, self.profil, "R-1", "2026-01-01", "2026-02-01")
        self.assertGreater(r.netto(), 0)
        self.assertAlmostEqual(r.brutto(), round((r.netto_nach_rabatt() + r.mwst()) * 100) / 100, 1)

    def test_rabatt_reduces(self):
        r = from_devis(self.devis, self.profil, "R-2", "2026-01-01", "2026-02-01", rabatt_pct=10)
        self.assertLess(r.netto_nach_rabatt(), r.netto())

    def test_skonto(self):
        r = from_devis(self.devis, self.profil, "R-3", "2026-01-01", "2026-02-01", skonto_pct=2)
        self.assertGreater(r.skonto_betrag(), 0)
        self.assertLess(r.brutto_mit_skonto(), r.brutto())

    def test_empty_devis(self):
        d = Devis(meta={}, addresses=[], chapters=[], positions=[])
        r = from_devis(d, self.profil, "R-0", "", "")
        self.assertEqual(r.netto(), 0.0)
        self.assertEqual(r.brutto(), 0.0)
        html = build_html(r, "de")
        self.assertIn("Rechnung", html)

    def test_html_and_pdf(self):
        r = from_devis(self.devis, self.profil, "R-4", "2026-01-01", "2026-02-01")
        r.zahlungsplan = [Teilzahlung("sofort", 100.0, "1. Rate"),
                          Teilzahlung("spaeter", 200.0, "2. Rate")]
        html = build_html(r, "de")
        self.assertIn("Zahlungsplan", html)
        self.assertIn("100.00", html)
        pdf = rech_pdf(r, "de")
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
