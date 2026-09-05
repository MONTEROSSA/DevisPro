"""XRechnung / ZUGFeRD Adapter (EU - EN 16931 eInvoice).

Parst die XML-Struktur (Invoice/Item) in das Position-Modell.
XRechnung nutzt CII (Cross Industry Invoice) oder UBL.
"""
import xml.etree.ElementTree as ET
from . import BaseImporter, register
from ..models import Devis, Position


@register
class XRechnungImporter(BaseImporter):
    name = "XRechnung / ZUGFeRD (EU)"
    extensions = ("xml", "xrechnung", "pdf")

    def parse(self, path: str) -> Devis:
        # Bei PDF (hybrid) nur XML-Teil - hier vereinfacht XML
        tree = ET.parse(path)
        root = tree.getroot()
        positions = []
        for elem in root.iter():
            tag = elem.tag.split("}")[-1].lower()
            if tag in ("lineitem", "item", "invoicedline", "invoiceline",
                       "supplychainnettradelineitem", "includedsupplychaintradelineitem",
                       "tradelineitem"):
                text = ""
                menge = 0.0
                einheit = ""
                ep = None
                betrag = None
                for child in elem.iter():
                    ct = child.tag.split("}")[-1].lower()
                    if ct in ("description", "name", "itemname", "productname", "modelname"):
                        text = (child.text or "").strip() or text
                    elif ct in ("quantity", "billedquantity", "unitquantity"):
                        try:
                            menge = float((child.text or "0").replace(",", "."))
                        except ValueError:
                            menge = 0.0
                    elif ct in ("unitcode", "unit", "measureunitcode"):
                        einheit = (child.text or "").strip()
                    elif ct in ("priceamount", "netprice", "chargeamount", "netpriceproducttradeprice"):
                        try:
                            ep = float((child.text or "0").replace(",", "."))
                        except ValueError:
                            ep = None
                    elif ct in ("lineextensionamount", "linetotal", "linetotalamount"):
                        try:
                            betrag = float((child.text or "0").replace(",", "."))
                        except ValueError:
                            betrag = None
                if text:
                    p = Position(pos_nr=str(len(positions) + 1),
                                 text=text, menge=menge, einheit=einheit,
                                 ep=ep, betrag=betrag)
                    p.fill()
                    positions.append(p)
        return self._devis("XRechnung", positions)
