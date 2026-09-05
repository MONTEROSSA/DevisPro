import os, sys
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
os.chdir("/Users/ferdinandrothlisberger/devis-auto")

import unittest
from devispro.parsers import crb
from devispro.models import Devis, Position
from devispro.pricelist import PriceItem
from devispro.providers.local import LocalProvider
from devispro.providers.mock import MockProvider
from devispro import i18n as i18n_mod
from devispro import extras as extras_mod
from devispro import pdf as pdf_mod
from devispro import kantone as kant_mod


class TestSiaRoundtrip(unittest.TestCase):
    def _make(self, menge, ep):
        p = Position(pos_nr="241111000000", text="Testpos", menge=menge,
                     einheit="m2", ep=ep, betrag=ep * menge, requires_review=False)
        return Devis(meta={"project_id": "X", "project_name": "P", "devis_nr": "1",
                           "date": "20260312", "currency": "CHF"},
                    addresses=[], chapters=[], positions=[p])

    def test_roundtrip_bleibt_exakt(self):
        dev = self._make(180.0, 9.00)
        crb.export(dev, "/tmp/_rt.sia")
        back = crb.parse("/tmp/_rt.sia")
        self.assertEqual(len(back.positions), 1)
        self.assertAlmostEqual(back.positions[0].menge, 180.0, places=4)
        self.assertAlmostEqual(back.positions[0].ep, 9.00, places=4)
        self.assertAlmostEqual(back.positions[0].betrag, 1620.0, places=4)

    def test_rappen_rundung(self):
        # 12.345 CHF -> 1235 Rappen; Export rundet korrekt
        dev = self._make(1.0, 12.345)
        crb.export(dev, "/tmp/_rt2.sia")
        back = crb.parse("/tmp/_rt2.sia")
        self.assertAlmostEqual(back.positions[0].ep, 12.35, places=2)


class TestMatcher(unittest.TestCase):
    def setUp(self):
        self.prices = [
            PriceItem(artikel_id="M-1", bezeichnung="Innenanstrich Wand",
                      npk="3423", einheit="m2", ep_chf=32.0, kategorie="Maler"),
            PriceItem(artikel_id="M-2", bezeichnung="Spachteln",
                      npk="3421", einheit="m2", ep_chf=18.5, kategorie="Maler"),
        ]

    def test_exakter_npk_prefix_matcht(self):
        pos = Position(pos_nr="342310000000", text="Innenanstrich Wand",
                       menge=10, einheit="m2")
        r = LocalProvider(threshold=0.6).match(pos, self.prices)
        self.assertEqual(r.matched_artikel_id, "M-1")
        self.assertFalse(r.requires_review)

    def test_kein_treffer_forciert_review(self):
        pos = Position(pos_nr="999999000000", text="Gaenzlich unbekannt",
                       menge=1, einheit="Stk")
        r = LocalProvider(threshold=0.6).match(pos, self.prices)
        self.assertTrue(r.requires_review)

    def test_mock_provider_liefert_format(self):
        pos = Position(pos_nr="342310000000", text="Innenanstrich",
                       menge=10, einheit="m2")
        r = MockProvider(threshold=0.6).match(pos, self.prices)
        self.assertEqual(r.matched_artikel_id, "M-1")
        self.assertIn("KI-Matching", r.begruendung)


class TestExtras(unittest.TestCase):
    def test_vorschlaege_kennt_gewerk(self):
        v = extras_mod.vorschlaege_fuer("Maler")
        self.assertTrue(len(v) >= 1)
        # Struktur: id, bezeichnung, einheit, ep_chf (alle positiv)
        for s in v:
            self.assertIn("ep_chf", s)
            self.assertTrue(s["ep_chf"] > 0)


class TestI18n(unittest.TestCase):
    def test_drei_sprachen_vorhanden(self):
        for lang in ["de", "fr", "it"]:
            self.assertIn(lang, i18n_mod.LANGS)
            self.assertTrue(len(i18n_mod.t("bepreisen", lang)) > 0)

    def test_fallback_auf_de(self):
        self.assertEqual(i18n_mod.t("bepreisen", "xx"), i18n_mod.t("bepreisen", "de"))


class TestKantonPreis(unittest.TestCase):
    def test_ag_guenstiger_als_zh(self):
        zh = kant_mod.waehle_kanton_profil({"kanton": "ZH"})
        ag = kant_mod.waehle_kanton_profil({"kanton": "AG"})
        self.assertAlmostEqual(zh["kanton_faktor"], 1.0, places=3)
        self.assertLess(ag["kanton_faktor"], zh["kanton_faktor"])


class TestOffertePdf(unittest.TestCase):
    def test_html_enthaeilt_summe(self):
        dev = Devis(meta={"project_id": "X", "project_name": "P", "devis_nr": "1",
                          "date": "20260312", "currency": "CHF"},
                    addresses=[], chapters=[],
                    positions=[Position(pos_nr="241111000000", text="Test",
                                        menge=10, einheit="m2", ep=9.0,
                                        betrag=90.0, requires_review=False)])
        profil = {"betrieb": "Test AG", "gewerk": "Maler", "kanton": "AG",
                  "mwst_pct": 8.1}
        doc = pdf_mod.build_offerte_html(dev, profil, lang="de")
        self.assertIn("Test AG", doc)
        self.assertIn("90.00", doc)  # Zwischensumme

    def test_pdf_export_fallback_html(self):
        dev = Devis(meta={}, addresses=[], chapters=[],
                    positions=[Position(pos_nr="1", text="T", menge=1,
                                        einheit="Stk", ep=10.0,
                                        betrag=10.0, requires_review=False)])
        ok = pdf_mod.export_pdf(dev, {"betrieb": "B", "mwst_pct": 8.1},
                                "/tmp/_off.pdf", lang="de")
        # ok kann True (wkhtmltopdf) oder False (HTML-Fallback) sein; Datei existiert
        self.assertTrue(os.path.exists("/tmp/_off.pdf") or
                        os.path.exists("/tmp/_off.pdf.html"))


if __name__ == "__main__":
    unittest.main()
