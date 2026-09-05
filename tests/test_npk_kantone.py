"""Tests fuer NPK-Struktur, Kanton-Modell und Gewerk-Abdeckung."""
import os, sys, unittest
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
from devispro import npk as npk_mod
from devispro import kantone as kant_mod
from devispro import extras as ex_mod

class TestNpk(unittest.TestCase):
    def test_gewerk_mapping(self):
        self.assertEqual(npk_mod.gewerk_fuer_kapitel(241), "Baumeister")
        self.assertEqual(npk_mod.gewerk_fuer_kapitel(342), "Gipser")
        self.assertEqual(npk_mod.gewerk_fuer_kapitel(410), "Sanitaer")
        self.assertEqual(npk_mod.gewerk_fuer_kapitel(700), "Elektro")
    def test_import_npk_csv(self):
        import csv, tempfile
        d = tempfile.mkdtemp()
        src = os.path.join(d, "npk.csv")
        with open(src, "w") as f:
            f.write("241.1100,Ortbeton 25MPa,m3,180.00\n990.9999,Unbekannt,x,1.00\n")
        out = os.path.join(d, "out.csv")
        neu, skip = npk_mod.import_npk_csv(src, out)
        self.assertEqual(neu, 2)
        self.assertEqual(skip, 0)
        self.assertTrue(os.path.exists(out))

class TestKantone(unittest.TestCase):
    def test_faktoren(self):
        self.assertEqual(kant_mod.faktor("ZH"), 1.0)
        self.assertGreater(kant_mod.faktor("GE"), kant_mod.faktor("VS"))
        self.assertEqual(kant_mod.label("TI"), "Tessin")
    def test_waehle(self):
        p = kant_mod.waehle_kanton_profil({"kanton": "GE"})
        self.assertAlmostEqual(p["kanton_faktor"], 1.07, places=2)

class TestGewerke(unittest.TestCase):
    def test_alle_gewerke(self):
        gw = ex_mod.gewerke_liste()
        # Deckung aller Hauptbau-Gewerke
        for needed in ["Bodenleger","Maler","Sanitärinstallation","Heizung","Lüftung",
                       "Elektro","Gipser","Schreiner","Glaser","Spengler","Dachdecker",
                       "Baumeister","Maurer","Schlosser","Gartenbau","Pflaster","GU"]:
            self.assertIn(needed, gw, f"Gewerk fehlt: {needed}")
    def test_vorschlaege_inkl_generic(self):
        v = ex_mod.vorschlaege_fuer("Heizung")
        self.assertTrue(any(x["id"]=="anfahrt" for x in v))  # generic

if __name__ == "__main__":
    unittest.main()
