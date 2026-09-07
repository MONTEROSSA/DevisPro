"""Bauweb / Daedalus Adapter (CH-Ausschreibungsportale).

Beide Portale exportieren Devis als CSV mit fixen Spalten:
  Position;Bezeichnung;Menge;Einheit;Einheitspreis;Betrag
Die Spalten koennen leicht variieren - wir nutzen daher das
generische Mapping, aber mit semikolon als Trenner und CH-Layout.
"""
import csv
from . import BaseImporter, register
from ..models import Devis, Position


@register
class BauwebImporter(BaseImporter):
    name = "Bauweb / Daedalus (CH)"
    extensions = ("csv", "txt")

    def parse(self, path: str) -> Devis:
        positions = []
        with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
            rd = csv.reader(f, delimiter=";")
            rows = [r for r in rd]
        # Header ueberspringen
        start = 1 if rows and any(h.lower() in ("position", "bezeichnung", "text", "lfd")
                                  for h in rows[0]) else 0
        for row in rows[start:]:
            if len(row) < 4:
                continue
            pos_nr = row[0].strip()
            text = row[1].strip() if len(row) > 1 else ""
            if not text:
                continue
            try:
                menge = float(self._num(row[2])) if len(row) > 2 else 0.0
            except ValueError:
                menge = 0.0
            einheit = row[3].strip() if len(row) > 3 else ""
            ep = self._num(row[4]) if len(row) > 4 else None
            betrag = self._num(row[5]) if len(row) > 5 else None
            p = Position(pos_nr=pos_nr or str(len(positions) + 1),
                         text=text, menge=menge, einheit=einheit,
                         ep=(float(ep) if ep else None),
                         betrag=(float(betrag) if betrag else None))
            p.fill()
            positions.append(p)
        return self._devis("Bauweb/Daedalus", positions)

    @staticmethod
    def _num(s):
        if s is None:
            return 0
        s = str(s).strip().replace("'", "").replace(" ", "").replace("’", "")
        if s.count(".") > 1:
            s = s.replace(".", "")
        try:
            return float(s)
        except ValueError:
            return 0
