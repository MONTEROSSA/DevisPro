"""GAEB D84 Adapter (Deutschland - Ausschreibungen, XML-Standard).

GAEB D84 enthaelt Positionen mit LV-Text, Menge, Einheit und ggf.
Einheitspreis. Wir parsen das XML in unser Position-Modell.
"""
import re
import xml.etree.ElementTree as ET
from . import BaseImporter, register
from ..models import Devis, Position


@register
class GaebImporter(BaseImporter):
    name = "GAEB D84 (DE)"
    extensions = ("xml", "gaeb", "txt")

    def parse(self, path: str) -> Devis:
        tree = ET.parse(path)
        root = tree.getroot()
        # Namensraum ignorieren
        positions = []
        projekt = "GAEB-Import"
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag == "OUPOS":  # Position
                pos_nr = ""
                text = ""
                menge = 0.0
                einheit = ""
                ep = None
                for child in elem:
                    ct = child.tag.split("}")[-1]
                    if ct == "POSNR":
                        pos_nr = (child.text or "").strip()
                    elif ct in ("POSART", "LVART"):
                        pass
                    elif ct == "KURZTEXT":
                        text = (child.text or "").strip()
                    elif ct == "LANGE":
                        # Menge in Attribut oder Unterelement
                        pass
                    elif ct == "MENGE":
                        try:
                            menge = float((child.text or "0").replace(",", "."))
                        except ValueError:
                            menge = 0.0
                    elif ct == "ME":  # Mengeneinheit
                        einheit = (child.text or "").strip()
                    elif ct == "EP":
                        try:
                            ep = float((child.text or "0").replace(",", "."))
                        except ValueError:
                            ep = None
                if text:
                    p = Position(pos_nr=pos_nr or str(len(positions) + 1),
                                 text=text, menge=menge, einheit=einheit, ep=ep)
                    p.fill()
                    positions.append(p)
        return self._devis(projekt, positions)
