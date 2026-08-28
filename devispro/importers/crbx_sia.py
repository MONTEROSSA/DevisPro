"""CRBX-SIA Importer (.crbx = ZIP mit SIAFILE.e1s, fixed-width SIA-451 LV).

Erkennt CRB-Submission-Verzeichnisse (Messerli/SORBA/Comatic): .crbx ist ein
ZIP-Container mit genau einer 'SIAFILE.e1s'. Diese wird vom Parser
devispro.parsers.crb_sia gelesen (A/B/C/G/Z fixed-width Zeilen).
Nach dem Einlesen werden Mengen + Einheitspreise bepreist:
  1) eigene Firmenpreise (devispro.firmen_preise), falls hochgeladen
  2) sonst CH-Durchschnittssimulation (devispro.ch_preise) als Fallback
"""
import os
from . import BaseImporter, register
from ..parsers.crb_sia import parse as parse_sia
from .. import ch_preise
from .. import firmen_preise


@register
class CrbxSiaImporter(BaseImporter):
    name = "CRB-SIA (.crbx Leistungsverzeichnis, Messerli/SORBA)"
    extensions = ("crbx", "e1s", "sia")

    def parse(self, path: str, simulate=True):
        d = parse_sia(path)
        eigen_preise = firmen_preise.exists()
        positions = []
        for p in d.positions:
            # bkp aus kapitel ableiten (z.b. "221.11")
            bkp = ""
            if p.chapter and len(p.chapter) >= 3:
                bkp = str(p.chapter[2])
            # 1) eigene preise
            ep_eigen = None
            if eigen_preise:
                res = firmen_preise.preis_fuer(p.text, bkp=bkp)
                if res:
                    ep_eigen = res
            if ep_eigen:
                einheit, ep = ep_eigen
                menge = ch_preise._detect_menge(p.text)
                if menge is None:
                    menge = 1.0 if einheit in ("Stk", "Pauschal", "t", "h") else 10.0
                betrag = round(menge * ep, 2)
                positions.append(self._pos(
                    p.pos_nr, p.text, menge, einheit, ep=ep, betrag=betrag, chapter=p.chapter))
            else:
                # 2) fallback simulation
                einheit, ep, menge, betrag = ch_preise.bepreise_position(p.text)
                positions.append(self._pos(
                    p.pos_nr, p.text, menge, einheit, ep=ep, betrag=betrag, chapter=p.chapter))
        meta = dict(d.meta)
        meta["projekt"] = meta.get("project_name") or meta.get("projekt") or "CRB-Import"
        meta["simuliert"] = not eigen_preise
        meta["eigene_preise"] = eigen_preise
        return DevisLocal(meta, d.addresses, d.chapters, positions)


# lokale Devis-Klasse (vermeidet zirkulaere imports mit models)
from ..models import Devis as DevisLocal
