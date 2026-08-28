"""CRB-XML (.crbx) Adapter -- modernes SORBA / Messerli / Comatic Exportformat.

SORBA, Messerli Informatik und Comatic exportieren Devis heute primaer als
CRB-XML (.crbx), nicht mehr als fixed-width .sia. Dieser Adapter parst das
XML in unser Position-Modell.

Struktur (CRB-XML / SIA 451, Anhang D -- dokumentierte Referenz):
  <CRB Version="2.0">
    <Kopf>
      <Projekt>Projektname</Projekt>
      <ProjektNr>12345</ProjektNr>
    </Kopf>
    <Positionen>
      <Position PosArt="E">           <!-- E=Einzelposition, Z=Zwischensumme -->
        <PosNr>1.1</PosNr>
        <Bezeichnung>Malerarbeiten Innenanstrich</Bezeichnung>
        <Menge>40.000</Menge>
        <Einheit>m2</Einheit>
        <EPreis>35.00</EPreis>
        <BPreis>1400.00</BPreis>
      </Position>
    </Positionen>
  </CRB>

Varianten (robust behandelt):
  - PosNr/Posnummer/PositionNr/Nr
  - Bezeichnung/Text/Artikel/Beschrieb (+ verschachtelte <Text>/<P>)
  - Menge/Anzahl/QMenge/Meng
  - Einheit/ME/Einheitscode
  - EPreis/EP/Einheitspreis
  - BPreis/Betrag/Total/Summe
  - PosArt="Z" (Zwischensumme) wird uebersprungen
"""
import xml.etree.ElementTree as ET
from . import BaseImporter, register
from ..models import Devis, Position

_SKIP_POSART = {"Z", "S", "G", "U", "T", "B", "P"}  # Zwischensumme/Gliederung/Summe


@register
class CrbxImporter(BaseImporter):
    name = "CRB-XML (.crbx, SORBA/Messerli/Comatic)"
    extensions = ("crbx", "crb")

    @staticmethod
    def _local(tag):
        return tag.split("}")[-1]

    @staticmethod
    def _find_text(elem, *names):
        """Sucht ueber exakte Tag-Namen, dann case-insensitiv im ganzen Baum.
        Falls ein Treffer Kindelemente hat (z.B. <Bezeichnung><Text>..</Text></Bezeichnung>),
        wird deren Text konkateniert."""
        for nm in names:
            for e in elem.iter():
                if CrbxImporter._local(e.tag).lower() == nm.lower():
                    # Text direkt
                    if (e.text or "").strip():
                        return e.text.strip()
                    # oder verschachtelte Texte sammeln
                    sub = [c.text.strip() for c in e if (c.text or "").strip()]
                    if sub:
                        return " ".join(sub)
        return ""

    @staticmethod
    def _find_float(elem, *names):
        t = CrbxImporter._find_text(elem, *names)
        if not t:
            return None
        t = t.replace("'", "").replace(" ", "").replace(",", ".")
        try:
            return float(t)
        except ValueError:
            return None

    @staticmethod
    def _is_position(elem):
        tag = CrbxImporter._local(elem.tag).lower()
        # Nur echte Positionselemente, nicht der Container <Positionen>
        return tag in ("position", "pos", "item", "lvposition", "leistungsposition")

    @staticmethod
    def _collect_positions(root):
        """Positionselemente finden (Container <Positionen> ausschliessen)."""
        found = [e for e in root.iter() if CrbxImporter._is_position(e)]
        if found:
            return found
        # Fallback: Elemente die eine PosNr direkt enthalten
        res = []
        for e in root.iter():
            if any(CrbxImporter._local(c.tag).lower() in ("posnr", "posnummer", "positionnr", "oz")
                   for c in e):
                res.append(e)
        return res

    def parse(self, path: str) -> Devis:
        tree = ET.parse(path)
        root = tree.getroot()
        positions = []
        projekt = "CRB-Import"
        for nm in ("Projekt", "Bezeichnung", "Titel", "Name", "Projektname"):
            v = self._find_text(root, nm)
            if v:
                projekt = v
                break

        pos_elems = self._collect_positions(root)
        if not pos_elems:
            for e in root.iter():
                if self._find_text(e, "PosNr", "Posnummer", "PositionNr"):
                    pos_elems.append(e)

        for el in pos_elems:
            # PosArt Attribut -> Zwischensummen/Gliederung ueberspringen
            posart = (el.get("PosArt") or el.get("Art") or "").upper()
            if posart in _SKIP_POSART:
                continue
            pos_nr = self._find_text(el, "PosNr", "Posnummer", "PositionNr", "Nr", "OZ")
            text = self._find_text(el, "Bezeichnung", "Text", "Artikel",
                                   "Beschrieb", "LVText", "Kurztext")
            menge = self._find_float(el, "Menge", "Anzahl", "QMenge", "Meng")
            einheit = self._find_text(el, "Einheit", "ME", "Einheitscode", "EinheitCode")
            ep_datei = self._find_float(el, "EPreis", "EP", "Einheitspreis", "UP")
            betrag_datei = self._find_float(el, "BPreis", "Betrag", "Total", "Summe", "VIP")
            if not text and not pos_nr:
                continue

            # --- eigene firmenpreise (bkp/fuzzy-text/stundenlohn) VORRANG ---
            ep_eigen = None
            info = None
            try:
                from .. import firmen_preise
                if firmen_preise.exists():
                    res = firmen_preise.preis_fuer(text, bkp="", menge=menge, einheit=einheit)
                    if res:
                        einheit_e, ep_e, info = res
                        ep_eigen = (einheit_e, ep_e)
            except Exception:
                ep_eigen = None

            if ep_eigen:
                einheit, ep = ep_eigen
                m = menge if (menge and menge > 0) else 1.0
                # stundenlohn-position: ep ist None, stundensatz kommt aus info
                if info and info.get("art") == "stunde" and menge and menge > 0:
                    ep = info.get("stundensatz", ep) or 0.0
                betrag = round((menge or m) * (ep or 0.0), 2)
                p = Position(
                    pos_nr=pos_nr or str(len(positions) + 1),
                    text=text or "(ohne Bezeichnung)",
                    menge=float(m or 0.0),
                    einheit=einheit or "",
                    ep=ep,
                    betrag=betrag,
                )
                if info:
                    p.matched_artikel = info.get("quelle")
                    p.confidence = info.get("confidence")
                    p.requires_review = info.get("confidence", 1.0) < 0.6
                    p.begruendung = f"Match: {info.get('art')} ({info.get('confidence', 1.0)})"
                p.fill()
                positions.append(p)
            else:
                # fallback: datei-eigenepreise (wenn vorhanden) sonst simulation
                p = Position(
                    pos_nr=pos_nr or str(len(positions) + 1),
                    text=text or "(ohne Bezeichnung)",
                    menge=float(menge or 0.0),
                    einheit=einheit or "",
                    ep=ep_datei,
                    betrag=betrag_datei,
                )
                if ep_datei is None and betrag_datei is None:
                    try:
                        from .. import ch_preise
                        eu, epp, mm, bb = ch_preise.bepreise_position(text or "")
                        p.einheit = p.einheit or eu
                        p.ep = epp
                        p.menge = float(menge or mm or 0.0)
                        p.betrag = round((menge or mm or 0.0) * (epp or 0.0), 2)
                        p.requires_review = True
                        p.begruendung = "Kein Firmenpreis gefunden - Simulation"
                    except Exception:
                        pass
                p.fill()
                positions.append(p)
        return self._devis(projekt, positions)
