"""GAEB D84 / DA XML Adapter (Deutschland - Ausschreibungen, XML-Standard).

Geprueft gegen echte GAEB-DA82/DA84-Dateien (xml.etree, namespace-agnostisch).
Struktur (GAEB DA XML, z.B. von NOVA AVA, ORCA, ...) :
  <GAEB>
    <PrjInfo><NamePrj>...</NamePrj></PrjInfo>
    <Award><BoQ ID="B21"><BoQBody>
      <BoQCtgy> ... </BoQCtgy>          (Gliederung, kein Item)
      <Item>
        <IT>132288</IT>                 (ItemType: 132288 = Einzelposition)
        <Description>...LV-Text...</Description>
        <Qty>13.000</Qty>               (Menge)
        <QU>Mon</QU>                    (Mengeneinheit)
        <UP>10176.000</UP>              (Einheitspreis)
        <AwardPrice>...<VIP>...</VIP></AwardPrice>  (falls bepreist)
      </Item>
    </BoQBody></BoQ></Award>
  </GAEB>

Positionen sind <Item>-Elemente. ItemType 132288 = Einzelposition
(132289 = Bedarfsposition, 132301 = Bedarfsumme, etc.) -- wir nehmen
alle mit Menge oder Text als Positionen.
"""
import xml.etree.ElementTree as ET
from . import BaseImporter, register
from ..models import Devis, Position

_ITEM_TYPES_POS = {"132288", "132290", "132299"}  # Einzelposition / Bedarfsposition / Pauschale


@register
class GaebImporter(BaseImporter):
    name = "GAEB D84 / DA XML (DE)"
    extensions = ("xml", "gaeb", "txt")

    @staticmethod
    def _t(elem):
        return (elem.text or "").strip()

    @staticmethod
    def _find(elem, *names):
        for nm in names:
            for e in elem.iter():
                if e.tag.split("}")[-1].lower() == nm.lower():
                    if (e.text or "").strip():
                        return e.text.strip()
        return ""

    @staticmethod
    def _float(elem, *names):
        t = GaebImporter._find(elem, *names)
        if not t:
            return None
        t = t.replace("'", "").replace(" ", "").replace(",", ".")
        try:
            return float(t)
        except ValueError:
            return None

    def parse(self, path: str) -> Devis:
        tree = ET.parse(path)
        root = tree.getroot()
        positions = []
        projekt = "GAEB-Import"
        # Projektname
        for nm in ("NamePrj", "Name"):
            v = self._find(root, nm)
            if v:
                projekt = v
                break
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag != "Item":
                continue
            # ItemType filtern (nur echte Positionen, keine Summen/Gliederung)
            it = self._find(elem, "IT", "ItemType", "Type")
            if it and it not in _ITEM_TYPES_POS and it not in ("",):
                # falls IT gesetzt aber unbekannt -> trotzdem parsen wenn Text/Menge da
                pass
            text = self._find(elem, "Description", "Text", "LVText", "Kurztext")
            menge = self._float(elem, "Qty", "Menge", "Quantity")
            einheit = self._find(elem, "QU", "ME", "Unit", "Einheit")
            ep = self._float(elem, "UP", "EP", "UnitPrice", "Einheitspreis")
            # AwardPrice/VIP als bepreister Betrag
            betrag = self._float(elem, "VIP", "BPreis", "Total", "Amount")
            if not text and not menge and not ep:
                continue
            p = Position(
                pos_nr=self._find(elem, "OZ", "PosNr", "ItemNo", "Number") or str(len(positions) + 1),
                text=text or "(ohne Bezeichnung)",
                menge=float(menge or 0.0),
                einheit=einheit or "",
                ep=ep,
                betrag=betrag,
            )
            p.fill()
            positions.append(p)
        return self._devis(projekt, positions)
