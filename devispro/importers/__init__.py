"""Adapter-faehige Import-Architektur.

Jede Plattform (Sorba/CRB, Bauweb, Daedalus, generisches CSV/Excel,
GAEB, OENORM, XRechnung) ist ein eigener Importer, der auf das
gemeinsame Devis/Position-Modell mappt. Sorba ist nur einer von N.
"""

import os
from ..models import Devis, Position


class BaseImporter:
    """Basis aller Format-Adapter.

    Subklassen implementieren parse() und liefern ein Devis-Objekt
    mit normalisierten Positionen zurueck.
    """

    name = "Basis"
    extensions = ()

    def parse(self, path: str) -> Devis:
        raise NotImplementedError

    @staticmethod
    def _pos(pos_nr, text, menge, einheit, ep=None, betrag=None, chapter=None):
        p = Position(
            pos_nr=str(pos_nr),
            text=str(text).strip(),
            menge=float(menge) if menge not in (None, "") else 0.0,
            einheit=str(einheit or "").strip(),
            ep=(float(ep) if ep not in (None, "") else None),
            betrag=(float(betrag) if betrag not in (None, "") else None),
            chapter=chapter,
        )
        p.fill()
        return p

    @staticmethod
    def _devis(projekt, positions):
        return Devis(meta={"projekt": projekt}, addresses=[], chapters=[],
                     positions=positions)


# --- Registry + Factory ------------------------------------------------
_REGISTRY = {}


def register(cls):
    _REGISTRY[cls.__name__] = cls
    return cls


def list_importers():
    out = []
    for cls in _REGISTRY.values():
        out.append((cls.name, cls))
    return sorted(out, key=lambda x: x[0])


def detect_importer(path: str):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    # Bei XML: Inhalt pruefen (GAEB vs XRechnung), da beide .xml nutzen
    if ext == "xml":
        try:
            head = open(path, encoding="utf-8", errors="ignore").read(2000).lower()
        except OSError:
            head = ""
        if "gaeb" in head:
            from .gaeb import GaebImporter
            return GaebImporter
        if "<invoice" in head or "xrechnung" in head or "crossindustry" in head:
            from .xrechnung import XRechnungImporter
            return XRechnungImporter
        # Default: GAEB
        from .gaeb import GaebImporter
        return GaebImporter
    for cls in _REGISTRY.values():
        if ext in cls.extensions:
            return cls
    return None


def import_devis(path: str, importer=None) -> Devis:
    if importer is None:
        importer = detect_importer(path)
        if importer is None:
            from .sia451 import Sia451Importer
            importer = Sia451Importer
    inst = importer()
    return inst.parse(path)


# Eager-Import aller Adapter (damit @register greift)
from . import sia451    # noqa: F401
from . import crbx_sia  # noqa: F401  (CRB .crbx = ZIP+SIAFILE.e1s, VOR crbx!)
from . import crbx       # noqa: F401
from . import generic    # noqa: F401
from . import bauweb    # noqa: F401
from . import gaeb      # noqa: F401
from . import oenorm    # noqa: F401
from . import xrechnung # noqa: F401
