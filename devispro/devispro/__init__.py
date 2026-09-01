"""devispro – SIA-451 Devis automatisch bepreisen und für Sorba aufbereiten."""

# 1) data_store ZUERST — stammdaten.py hängt davon ab und wird in Schritt 3 geladen.
import os, sys, importlib.util as _ilu
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = _ilu.spec_from_file_location('devispro.data_store', os.path.join(_HERE, 'data_store.py'))
_data_store_mod = _ilu.module_from_spec(_spec)
sys.modules['devispro.data_store'] = _data_store_mod
_spec.loader.exec_module(_data_store_mod)

# 2) crypto_rsa wird von license/license_admin gebraucht — vorab laden.
_spec = _ilu.spec_from_file_location('devispro.crypto_rsa', os.path.join(_HERE, 'crypto_rsa.py'))
_crypto_rsa_mod = _ilu.module_from_spec(_spec)
sys.modules['devispro.crypto_rsa'] = _crypto_rsa_mod
_spec.loader.exec_module(_crypto_rsa_mod)

# 3)Core modules in Reihenfolge, die Zirkel-Imports vermeidet:
#    - models: keine externen Abhängigkeiten
#    - stammdaten: braucht data_store (ist in sys.modules)
#    - importers: braucht models + stammdaten
from .models import Devis, Position
from .stammdaten import load_profile, save_profile
from .importers import import_devis

# 4) Daten/Pricing-Module, die keine Zirkel-Imports haben
from . import history, firmen_preise, ch_preise, pricing
from . import kantone, multicurrency
from . import accounting, marketing, diagnostics
from . import backup, ordner_import, templates
from . import version

# 5) Module mit potenziellen Zirkel-Imports (license ↔ crypto_rsa ↔ license_admin) —
#    NACH allen anderen laden, damit die anderen vollständig im sys.modules sind.
from . import license, license_admin, trial_counter, benchmark, abo
from . import erp, bridge_agent, monitor, agent

# 6) Diese Module können Probleme mit Zirkel-Imports haben — lazy import
#    via __getattr__ in den jeweiligen Modulen
__all__ = [
    "Devis", "Position",
    "load_profile", "save_profile",
    "import_devis",
    "history", "firmen_preise", "ch_preise", "pricing",
    "kantone", "multicurrency",
    "accounting", "marketing", "diagnostics",
    "license", "license_admin", "trial_counter", "benchmark", "abo",
    "erp", "bridge_agent", "backup", "ordner_import", "templates",
    "agent", "monitor",
    "version",
]
