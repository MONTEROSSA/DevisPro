"""OENORM B 2063 / B 2110 Adapter (Oesterreich - oeffentlicher Bau).

OENORM-Devis werden meist als CSV (semikolon) oder Excel geliefert:
  Pos;Bezeichnung;Menge;Einheit;EP;Betrag
"""
import csv
from . import BaseImporter, register
from ..models import Devis, Position


@register
class OenormImporter(BaseImporter):
    name = "OENORM B 2063 (AT)"
    extensions = ("csv", "txt")

    def _num(self, s):
        if s is None:
            return 0
        s = str(s).strip().replace(" ", "").replace("'", "")
        s = s.replace(".", "").replace(",", ".") if "," in s else s
        try:
            return float(s)
        except ValueError:
            return 0

    def parse(self, path: str) -> Devis:
        positions = []
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            rd = csv.reader(f, delimiter=";")
            rows = [r for r in rd]
        start = 1 if rows and any(h.lower() in ("pos", "bezeichnung", "lfd", "position")
                                  for h in rows[0]) else 0
        for row in rows[start:]:
            if len(row) < 3:
                continue
            text = row[1].strip() if len(row) > 1 else ""
            if not text:
                continue
            pos_nr = row[0].strip()
            menge = self._num(row[2]) if len(row) > 2 else 0.0
            einheit = row[3].strip() if len(row) > 3 else ""
            ep = self._num(row[4]) if len(row) > 4 else None
            betrag = self._num(row[5]) if len(row) > 5 else None
            p = Position(pos_nr=pos_nr or str(len(positions) + 1),
                         text=text, menge=menge, einheit=einheit,
                         ep=(float(ep) if ep else None),
                         betrag=(float(betrag) if betrag else None))
            p.fill()
            positions.append(p)
        return self._devis("OENORM B 2063", positions)
