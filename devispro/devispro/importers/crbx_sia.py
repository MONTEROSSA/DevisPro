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
            # 1) eigene preise (bkp-nr, fuzzy-text, stundenlohn)
            ep_eigen = None
            info = None
            if eigen_preise:
                res = firmen_preise.preis_fuer(p.text, bkp=bkp, menge=p.menge, einheit=p.einheit)
                if res:
                    einheit, ep, info = res
                    ep_eigen = (einheit, ep)
            if ep_eigen:
                einheit, ep = ep_eigen
                # menge: falls im crbx leer, ueber text schaetzen
                menge = p.menge if (p.menge and p.menge > 0) else ch_preise._detect_menge(p.text)
                if menge is None:
                    menge = 1.0 if einheit in ("Stk", "Pauschal", "t", "h") else 10.0
                # stundenlohn-position: ep als stundensatz -> betrag = stundensatz * zeit
                if info and info.get("art") == "stunde" and p.menge and p.menge > 0:
                    ep = info.get("stundensatz", ep)
                    betrag = round(p.menge * ep, 2)
                else:
                    betrag = round(menge * ep, 2)
                pos = self._pos(p.pos_nr, p.text, menge, einheit, ep=ep, betrag=betrag, chapter=p.chapter)
                if info:
                    pos.matched_artikel = info.get("quelle")
                    pos.confidence = info.get("confidence")
                    pos.requires_review = info.get("confidence", 1.0) < 0.6
                    pos.begruendung = f"Match: {info.get('art')} ({info.get('confidence', 1.0)})"
                positions.append(pos)
            else:
                # 2) fallback simulation (kein treffer -> explizit als unbepreist markieren)
                einheit, ep, menge, betrag = ch_preise.bepreise_position(p.text)
                pos = self._pos(p.pos_nr, p.text, menge, einheit, ep=ep, betrag=betrag, chapter=p.chapter)
                pos.requires_review = True
                pos.begruendung = "Kein Firmenpreis gefunden - Simulation"
                positions.append(pos)
        meta = dict(d.meta)
        meta["projekt"] = meta.get("project_name") or meta.get("projekt") or "CRB-Import"
        meta["simuliert"] = not eigen_preise
        meta["eigene_preise"] = eigen_preise
        return DevisLocal(meta, d.addresses, d.chapters, positions)


# lokale Devis-Klasse (vermeidet zirkulaere imports mit models)
from ..models import Devis as DevisLocal
