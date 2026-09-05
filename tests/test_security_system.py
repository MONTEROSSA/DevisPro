"""Tests fuer neue Sicherheits-/Zuverlaessigkeits-Module."""
import os
import sys
import unittest
import datetime as dt

sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
from devispro import crypto_rsa as rsa
from devispro import admin_auth as auth
from devispro import kalkulation as kal
from devispro import i18n as i18n_mod
from devispro import system as sys_mod
from devispro.parsers import crb


class TestRSA(unittest.TestCase):
    def test_sign_verify(self):
        pub, priv = rsa.generate_keypair(512)  # klein fuer Test-Speed
        msg = "KMU-1|2027-01-01"
        sig = rsa.sign(priv, msg)
        self.assertTrue(rsa.verify(pub, msg, sig))
        self.assertFalse(rsa.verify(pub, "KMU-1|2028-01-01", sig))
        self.assertFalse(rsa.verify(pub, msg, sig[:-1] + "0"))


class TestAdminAuth(unittest.TestCase):
    def test_login_flow(self):
        # Default-Passwort bei Erststart
        self.assertTrue(auth.pruefen("devispro-admin-2026"))
        tok = auth.session_token()
        self.assertTrue(auth.session_gueltig(tok))
        self.assertFalse(auth.session_gueltig("x|y|z"))


class TestKalkulation(unittest.TestCase):
    def test_ep_zerlegung(self):
        netto, auf = kal.berechne_ep(100.0, 12.0, 10.0, 8.0)
        self.assertGreater(netto, 100.0)
        self.assertAlmostEqual(auf["netto"], netto, places=4)
        # Faktor-Konsistenz
        faktor = (1+12/100)*(1+10/100)*(1+8/100)
        self.assertAlmostEqual(netto, 100.0*faktor, places=2)


class TestI18n(unittest.TestCase):
    def test_sprachen(self):
        self.assertEqual(i18n_mod.t("bepreisen", "de"), "Bepreisen")
        self.assertEqual(i18n_mod.t("bepreisen", "fr"), "Tarifer")
        self.assertEqual(i18n_mod.t("bepreisen", "it"), "Preventivare")
        self.assertIn("de", i18n_mod.LANGS)


class TestSystem(unittest.TestCase):
    def test_backup_audit(self):
        d = sys_mod.backup("test")
        self.assertTrue(os.path.isdir(d))
        # Audit-Log geschrieben
        self.assertTrue(os.path.exists(sys_mod.LOG_PFAD))
        ok, msgs = sys_mod.gesundheitscheck()
        self.assertIsInstance(ok, bool)


class TestSiaExtras(unittest.TestCase):
    def test_export_mit_extras(self):
        dev = crb.parse("/Users/ferdinandrothlisberger/devis-auto/data/devis_wiedikon.sia")
        n0 = len(dev.positions)
        extras = [{"pos_nr": "Z001", "text": "Zusatz", "menge": 2, "einheit": "m2",
                  "ep": 10.0, "betrag": 20.0}]
        out = "/tmp/_sia_ext_test.sia"
        crb.export(dev, out, extras=extras)
        dev2 = crb.parse(out)
        self.assertEqual(len(dev2.positions), n0 + 1)
        self.assertTrue(any("Zusatz" in (p.text or "") for p in dev2.positions))
        os.remove(out)


if __name__ == "__main__":
    unittest.main()
