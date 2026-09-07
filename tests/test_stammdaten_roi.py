import unittest, os, sys
sys.path.insert(0, "/Users/ferdinandrothlisberger/devispro")
from devispro import stammdaten, roi as roi_mod
from devispro.pricelist import load

HERE = "/Users/ferdinandrothlisberger/devis-auto"
DATA = os.path.join(HERE, "data")


class TestStammdatenROI(unittest.TestCase):
    def test_profile_default_persist(self):
        p = stammdaten.default_profile()
        stammdaten.save_profile(p)
        p2 = stammdaten.load_profile()
        self.assertEqual(p2["stundenlohn_chf"], p["stundenlohn_chf"])
        self.assertTrue(os.path.exists(os.path.join(DATA, "profil.json")))

    def test_prices_persist(self):
        stammdaten.save_prices_csv("ART-1,Test,243,m2,12.50,Maler\nART-2,Fenster,261,Stk,85.00,Maler\n")
        self.assertTrue(stammdaten.prices_exist())
        items = load(os.path.join(DATA, "meine_preise.csv"))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].ep_chf, 12.5)

    def test_roi_break_even(self):
        profil = stammdaten.default_profile()
        r = roi_mod.calculate(profil, devis_pro_monat=20, app_preis=2400, app_jahr=900)
        # Bei 20 Devis/Monat, 1.8h gespart, 82 CHF/h + 40 Fehler = ~227.6 CHF/Devis
        # -> ~4552 CHF/Monat Ersparnis, Break-even nach ~1 Monat
        self.assertLessEqual(r["break_even_monat"], 2)
        self.assertGreater(r["jahr_ersparnis"], 40000)
        self.assertEqual(len(r["cashflow"]), 12)
        self.assertGreater(r["roi_pct"], 100)

    def test_roi_zeit_jahr(self):
        r = roi_mod.calculate(stammdaten.default_profile())
        self.assertGreater(r["zeit_erspart_jahr_h"], 0)


if __name__ == "__main__":
    unittest.main()
