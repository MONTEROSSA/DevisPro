import sys, os
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
import importlib
checks = [
    ("devispro.accounting", "export"),
    ("devispro.pdf", "export_pdf"),
    ("devispro.agent", "chat"),
    ("devispro.agent", "set_devis"),
    ("devispro.parsers.crb", "export"),
    ("devispro.importers", "import_devis"),
    ("devispro.stammdaten", "save_profile"),
    ("devispro.history", "list_all"),
    ("devispro.firmen_preise", "speichern_aus_upload"),
]
for mod, fn in checks:
    try:
        m = importlib.import_module(mod)
        ok = hasattr(m, fn)
        print(f"{mod}.{fn}: {'OK' if ok else 'FEHLT'}")
    except Exception as e:
        print(f"{mod}.{fn}: IMPORT-FEHLER {e}")
