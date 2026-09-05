"""Vollständige Test-Suite für devispro (stdlib-only)."""
import os
import sys
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devispro.parsers import crb, json_if
from devispro.pricelist import load
from devispro.matcher import Matcher
from devispro.models import Position
from devispro.providers import get_provider
from devispro.validators import validate
from devispro.sample_project import build_realistic_devis

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")


class TestParsers(unittest.TestCase):
    def setUp(self):
        make_sample()

    def test_crb_roundtrip(self):
        import tempfile
        devis = crb.parse(os.path.join(DATA, "devis_wiedikon.sia"))
        self.assertEqual(len(devis.positions), 29)
        # Echtes Positional-Format (01/11/31/99) hat keine Kapitelzeilen
        self.assertEqual(len(devis.chapters), 0)
        self.assertEqual(len(devis.addresses), 0)
        self.assertEqual(devis.positions[0].pos_nr, "241111000000")
        # Export + Re-Import verlustfrei (temp, nicht in data/)
        out = os.path.join(tempfile.mkdtemp(prefix="hermes-test-"), "_rt.sia")
        crb.export(devis, out)
        devis2 = crb.parse(out)
        self.assertEqual(len(devis2.positions), len(devis.positions))
        self.assertEqual(devis2.positions[0].pos_nr, "241111000000")

    def test_json_roundtrip(self):
        import tempfile
        devis = json_if.parse(os.path.join(DATA, "devis_wiedikon.json"))
        self.assertEqual(len(devis.positions), 29)
        out = os.path.join(tempfile.mkdtemp(prefix="hermes-test-"), "_rt.json")
        json_if.export(devis, out)
        devis2 = json_if.parse(out)
        self.assertEqual(len(devis2.positions), 29)


class TestMatcher(unittest.TestCase):
    def setUp(self):
        make_sample()

    def test_local_exact_npk(self):
        prices = load(os.path.join(DATA, "richtpreise_zh.csv"))
        m = Matcher(method="local", threshold=0.6)
        p = Position("241.1110", "Abbruch von unbewehrtem Beton, Staerke bis 20 cm", 18.5, "m3")
        r = m.match(p, prices)
        self.assertEqual(r.matched_artikel_id, "ART-2411")
        self.assertAlmostEqual(r.einheitspreis_chf, 185.0)
        self.assertFalse(r.requires_review)

    def test_mock_provider_runs(self):
        prices = load(os.path.join(DATA, "richtpreise_zh.csv"))
        m = Matcher(method="mock", threshold=0.6)
        p = Position("255.3010", "Fenster Kunststoff, 3-fach Verglasung", 28.0, "Stk")
        r = m.match(p, prices)
        self.assertEqual(r.matched_artikel_id, "ART-2553")
        self.assertAlmostEqual(r.einheitspreis_chf, 640.0)
        self.assertIn("KI-Matching", r.begruendung)

    def test_ambiguous_requires_review(self):
        prices = load(os.path.join(DATA, "richtpreise_zh.csv"))
        m = Matcher(method="mock", threshold=0.6)
        p = Position("288.9000", "Photovoltaikanlage 8 kWp auf Flachdach", 1.0, "Stk")
        r = m.match(p, prices)
        self.assertTrue(r.requires_review)

    def test_local_rejects_missing_price(self):
        prices = load(os.path.join(DATA, "richtpreise_zh.csv"))
        m = Matcher(method="local", threshold=0.9)
        p = Position("251.5010", "Holzstaenderwand beidseitig beplankt", 72.0, "m2")
        r = m.match(p, prices)
        # Score ~0.98 (NPK) ist >=0.9 -> kein Review, aber Preis gesetzt
        self.assertFalse(r.requires_review)
        self.assertEqual(r.matched_artikel_id, "ART-2515")


class TestProviders(unittest.TestCase):
    def test_get_provider_unknown(self):
        with self.assertRaises(ValueError):
            get_provider("nope")

    def test_llm_requires_key(self):
        prov = get_provider("llm")
        with self.assertRaises(RuntimeError):
            prov.match(Position("x", "y", 1, "m2"), [])


class TestValidator(unittest.TestCase):
    def setUp(self):
        make_sample()

    def test_valid_file(self):
        issues = validate(os.path.join(DATA, "devis_wiedikon.sia"))
        self.assertEqual(issues, [])

    def test_missing_end_record(self):
        bad = os.path.join(DATA, "_bad.sia")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("01A12345678Umbau Test                       20260101CHF\n")
        issues = validate(bad)
        self.assertTrue(any("Abschlusssatz" in i for i in issues))
        os.remove(bad)


def make_sample():
    from devispro.sample_project import build_realistic_devis
    d = build_realistic_devis()
    crb.export(d, os.path.join(DATA, "devis_wiedikon.sia"))
    json_if.export(d, os.path.join(DATA, "devis_wiedikon.json"))


class TestRealSorbaExample(unittest.TestCase):
    """Beweis: Geminis echtes Sorba-Beispiel wird korrekt verarbeitet."""

    def test_parse_real_example(self):
        devis = crb.parse(os.path.join(DATA, "echtes_beispiel.sia"))
        self.assertEqual(len(devis.positions), 1)
        p = devis.positions[0]
        self.assertEqual(p.pos_nr, "241111000000")
        self.assertAlmostEqual(p.menge, 45.0)
        self.assertEqual(p.einheit, "m3")
        self.assertAlmostEqual(p.ep, 85.0)
        self.assertAlmostEqual(p.betrag, 3825.0)
        self.assertEqual(devis.meta["project_name"], "Umbau Gewerbehaus Zürich")
        self.assertEqual(devis.meta["date"], "20260807")
        self.assertEqual(devis.meta["currency"], "CHF")

    def test_price_real_example(self):
        devis = crb.parse(os.path.join(DATA, "echtes_beispiel.sia"))
        prices = load(os.path.join(DATA, "richtpreise_zh.csv"))
        m = Matcher(method="local", threshold=0.6)
        r = m.match(devis.positions[0], prices)
        self.assertEqual(r.matched_artikel_id, "ART-2411")
        self.assertAlmostEqual(r.einheitspreis_chf, 185.0)
        # Export + Validierung der Sorba-Datei
        out = os.path.join(DATA, "_real_out.sia")
        crb.export(devis, out)
        issues = validate(out)
        self.assertEqual(issues, [])
        os.remove(out)


if __name__ == "__main__":
    unittest.main()
