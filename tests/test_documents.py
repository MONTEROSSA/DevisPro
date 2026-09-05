"""Permanente Tests fuer das SIA-118 Dokumenten-Modul (devispro.documents)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devispro.documents import (
    build_werkvertrag_html,
    build_abnahme_html,
    build_devis_muster_html,
    build,
    export_pdf,
)
from devispro.models import Devis
from devispro.parsers import crb


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIA = os.path.join(ROOT, "data", "devis_maler_beispiel.sia")


def _devis():
    return crb.parse(SIA)


def _profil():
    return {
        "betrieb": "Maler Muster AG",
        "gewerk": "Maler",
        "strasse": "Hauptstrasse 1",
        "ort": "8000 Zuerich",
        "mwst_pct": 8.1,
    }


class TestDocuments(unittest.TestCase):
    def setUp(self):
        self.devis = _devis()
        self.profil = _profil()

    def test_werkvertrag_de(self):
        html = build_werkvertrag_html(self.devis, self.profil, "de")
        self.assertIn("Werkvertrag", html)
        self.assertIn("SIA 118", html)
        self.assertIn("Maler Muster AG", html)
        # Positionstabelle vorhanden
        self.assertIn("<table", html)
        # Netto/Brutto erwaehnt
        self.assertIn("CHF", html)

    def test_werkvertrag_bindend_bis(self):
        html = build_werkvertrag_html(self.devis, self.profil, "de", bindend_bis="31.12.2026")
        self.assertIn("31.12.2026", html)
        self.assertIn("Verbindlich bis", html)

    def test_werkvertrag_fr(self):
        html = build_werkvertrag_html(self.devis, self.profil, "fr")
        self.assertIn("Contrat", html)

    def test_werkvertrag_it(self):
        html = build_werkvertrag_html(self.devis, self.profil, "it")
        self.assertIn("Contratto", html)

    def test_abnahme_kein_mangel(self):
        html = build_abnahme_html(self.devis, self.profil, "de")
        self.assertIn("Abnahmeprotokoll", html)
        self.assertIn("Keine Mängel", html)

    def test_abnahme_mit_maengel(self):
        html = build_abnahme_html(self.devis, self.profil, "de",
                                  maengel=["Riss im Putz", "Kante beschädigt"], bedingt=True)
        self.assertIn("Riss im Putz", html)
        self.assertIn("Kante beschädigt", html)
        self.assertIn("Vorbehalt", html)

    def test_devis_muster(self):
        html = build_devis_muster_html(self.devis, self.profil, "de")
        self.assertIn("Kostenvoranschlag", html)
        self.assertIn("unverbindlich", html)

    def test_devis_muster_bindend(self):
        html = build_devis_muster_html(self.devis, self.profil, "de", bindend_bis="15.09.2026")
        self.assertIn("15.09.2026", html)
        self.assertIn("Verbindlich bis", html)

    def test_build_dispatches(self):
        for typ in ("werkvertrag", "abnahme", "devis_muster"):
            html = build(typ, self.devis, self.profil, "de")
            self.assertTrue(html.strip().startswith("<!doctype html>"), typ)

    def test_build_unknown_raises(self):
        with self.assertRaises(ValueError):
            build("nope", self.devis, self.profil, "de")

    def test_export_pdf_fallback_html(self):
        html = build_devis_muster_html(self.devis, self.profil, "de")
        out = os.path.join(ROOT, "data", "_test_doc.pdf")
        # Ohne wkhtmltopdf -> Fallback HTML
        res = export_pdf(html, out)
        # entweder PDF erzeugt oder HTML-Fallback
        self.assertTrue(os.path.exists(out) or os.path.exists(out + ".html"))
        for p in (out, out + ".html"):
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
