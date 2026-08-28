"""CRB-SIA 451 (.crbx -> SIAFILE.e1s) fixed-width Parser.

Echtes CRB/CRBX-Format (Messerli, SORBA, Comatic Submission-Verzeichnisse):
  .crbx ist ein ZIP-Container mit genau einer Datei 'SIAFILE.e1s'.
  Die .e1s ist ein fixed-width SIA-451 Leistungsverzeichnis mit Zeilentypen:
    A  = Kopfdaten (Projekt, BKP, Firma)
    B  = Gliederung (Gebaeude / Rohbau / ...)
    C  = Rabatt / Skonto / MWST
    G  = Position oder Gliederungsebene
    Z  = Abschluss
  G-Zeile Layout:
    [0]   Typ 'G'
    [1:4] LV-Nummer (3)
    [4:10] Kapitel-Nummer (6)
    [10:17] Positionsnummer (7)
    [17:19] Ebene (1=Kapitel, 2=Unterkapitel, 3=Position)
    [ca. 90:] Beschreibungstext
  Mengen/Einheitspreise stehen in Submit-Verzeichnissen oft noch leer ->
  Positionen werden mit Beschreibung uebernommen, Menge/EP = 0 (ausfuellen).
"""
import os
import re
import zipfile

# Spaltenbreiten der G-Zeile (fixed)
G_LV = (1, 4)
G_KAP = (4, 10)
G_POS = (10, 17)
G_EBENE = (17, 19)
G_TEXT_START = 89


def _read_e1s(path):
    """Liest SIAFILE.e1s aus .crbx (zip) oder direkt aus .e1s/.sia/.txt."""
    if path.lower().endswith(".crbx"):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            e1s = [n for n in names if n.upper().endswith(".E1S")]
            name = e1s[0] if e1s else (names[0] if names else None)
            if name is None:
                raise ValueError("Leeres .crbx (keine Datei im ZIP)")
            raw = z.read(name)
    else:
        with open(path, "rb") as f:
            raw = f.read()
    # CRB-Dateien sind meist latin-1; falls UTF-8 sauber dekodierbar, vorziehen
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "replace")


def parse(path):
    from ..models import Devis, Position

    raw = _read_e1s(path)
    lines = raw.splitlines()

    meta = {"version": "SIA451-CRB", "currency": "CHF", "mwst": 8.1,
            "project_name": "", "projekt_nr": "", "bkp": "", "firma": ""}
    addresses = []
    chapters = []
    positions = []
    current_chapter = None
    mwst_pct = 8.1

    for ln in lines:
        if not ln.strip():
            continue
        typ = ln[0]

        if typ == "A":
            # Projektkopf: Text ab Spalte 100 = " - TGS - Ueberbauung ... BKP ..."
            head = ln[100:].strip()
            head = head.split("BKP")[0].strip().lstrip("-").strip()
            # "TGS - Ueberbauung «T000002111" -> Projektname
            meta["project_name"] = head or ln[20:80].strip()
            # Firma: im A-Kopf steht "Messerli AG" nach "BKP 221.11 ... /"
            fir = ln[100:200]
            if "Messerli" in fir:
                meta["firma"] = "Messerli AG"
            m = re.search(r"BKP\s*([\d.]+)", ln)
            if m:
                meta["bkp"] = m.group(1)

        elif typ == "B":
            # B001 17  ...  4  ...  Fenster aus Holz-Metall  221.1
            # ebene = ln[6:9], nr = ln[38:45], text = ln[~90:]
            ebene = ln[6:9].strip()
            nr = ln[38:45].strip()
            txt = ln[90:].strip()
            if txt:
                current_chapter = (ebene, nr, txt)
                chapters.append((ebene, nr, txt))

        elif typ == "C":
            # C003203  02  1 %+000000000000000+  +000770  MWST
            if "MWST" in ln or "MwSt" in ln:
                m = re.search(r"\+000(\d{3})\s", ln)
                if m:
                    try:
                        mwst_pct = int(m.group(1)) / 100.0
                        meta["mwst"] = mwst_pct
                    except ValueError:
                        pass

        elif typ == "G":
            lv = ln[G_LV[0]:G_LV[1]].strip()
            kap = ln[G_KAP[0]:G_KAP[1]].strip()
            posnr = ln[G_POS[0]:G_POS[1]].strip()
            text = ln[G_TEXT_START:].strip()
            # ebene aus nummern-laenge bestimmen (spalte 17-19 ist hier leer)
            # posnr 3-stellig -> kapitel, 7-stellig -> unterkapitel/position
            digits = posnr.replace(" ", "")
            if len(digits) <= 3:
                # kapitel-ueberschrift (z.b. "000" Vorbedingungen)
                if text and not text.startswith("BKP") and "Reserve" not in text:
                    current_chapter = ("1", digits or kap, text)
                    chapters.append(("1", digits or kap, text))
                continue
            if len(digits) == 7:
                # 7-stellig: wenn kapitel-vorfeld (0000001) -> unterkapitel
                if kap in ("", "000", "000000"):
                    if text and not text.startswith("BKP"):
                        current_chapter = ("2", digits, text)
                        chapters.append(("2", digits, text))
                    continue
                # echte position (kap=090 etc.)
                if not text:
                    continue
                p = Position(
                    pos_nr=(kap + digits).strip() or str(len(positions) + 1),
                    text=text,
                    menge=0.0,
                    einheit="",
                    ep=None,
                    betrag=None,
                )
                p.chapter = current_chapter
                p.fill()
                positions.append(p)

    meta["mwst"] = mwst_pct
    return Devis(meta=meta, addresses=addresses, chapters=chapters, positions=positions)
