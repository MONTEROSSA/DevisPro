"""SIA451 Roundtrip — Bidirektional: Import LV → Bearbeiten → Export (unverändert zurück an Architekt)."""
from __future__ import annotations
import os
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# SIA451 Fixed-Width Format (CRB/Sorba Standard)
# Zeilentyp A: Kopfdaten
# Zeilentyp B: Gliederung (Kapitel)
# Zeilentyp C: Position
# Zeilentyp D: Preiszeile
# Zeilentyp E: Langtext
# Zeilentyp Z: Ende

@dataclass
class SIA451Position:
    pos_nr: str
    text: str
    menge: float
    einheit: str
    ep: Optional[float] = None  # in Rappen
    betrag: Optional[float] = None
    gliederung: str = ""
    langtext: str = ""

@dataclass
class SIA451Projekt:
    projekt_nr: str
    projekt_name: str
    bauherr: str = ""
    datum: str = ""
    waehrung: str = "CHF"
    positionen: List[SIA451Position] = None
    
    def __post_init__(self):
        if self.positionen is None:
            self.positionen = []


def parse_sia451_fixed_width(path: str) -> SIA451Projekt:
    """Parst echtes SIA451 Fixed-Width (.e1s / .crbx entpackt)."""
    path = Path(path)
    if path.suffix == ".crbx":
        import zipfile
        with zipfile.ZipFile(path, "r") as z:
            # CRBX enthält genau eine SIAFILE.e1s
            for name in z.namelist():
                if name.endswith(".e1s") or "SIAFILE" in name.upper():
                    with z.open(name) as f:
                        content = f.read().decode("iso-8859-1", errors="ignore")
                    return _parse_sia451_content(content)
        raise ValueError("Keine SIAFILE.e1s im CRBX gefunden")
    else:
        with open(path, "r", encoding="iso-8859-1", errors="ignore") as f:
            content = f.read()
        return _parse_sia451_content(content)


def _parse_sia451_content(content: str) -> SIA451Projekt:
    projekt = SIA451Projekt(projekt_nr="", projekt_name="")
    current_gliederung = ""
    
    for line in content.splitlines():
        if len(line) < 2:
            continue
        typ = line[:2]
        
        if typ == "01":  # Kopfdaten (Sorba-Export)
            # 01 + ProjektNr(9) + ProjektName(40) + Datum(8) + Waehrung(3) + Bauherr(40)
            projekt.projekt_nr = line[2:11].strip()
            projekt.projekt_name = line[11:51].strip()
            projekt.datum = line[51:59].strip()
            projekt.waehrung = line[59:62].strip()
            projekt.bauherr = line[62:102].strip()
            
        elif typ == "11":  # Gliederung
            # 11 + GliederungsNr(12) + Text(40)
            gnr = line[2:14].strip()
            gtext = line[14:54].strip()
            current_gliederung = f"{gnr} {gtext}"
            
        elif typ == "21":  # Position
            # 21 + PosNr(12) + Text(40) + Menge(10 Rappen) + Einheit(4) + EP(10 Rappen) + Betrag(12 Rappen)
            pos_nr = line[2:14].strip()
            text = line[14:54].strip()
            menge_rap = line[54:64].strip()
            einheit = line[64:68].strip()
            ep_rap = line[68:78].strip()
            betrag_rap = line[78:90].strip()
            
            menge = int(menge_rap) / 100 if menge_rap.isdigit() else 0
            ep = int(ep_rap) / 100 if ep_rap.isdigit() else None
            betrag = int(betrag_rap) / 100 if betrag_rap.isdigit() else None
            
            pos = SIA451Position(
                pos_nr=pos_nr,
                text=text,
                menge=menge,
                einheit=einheit.strip(),
                ep=ep,
                betrag=betrag,
                gliederung=current_gliederung,
            )
            projekt.positionen.append(pos)
            
        elif typ == "31":  # Preiszeile (alternativ zu 21)
            # 31 + PosNr(12) + EP(10) + Betrag(12)
            pos_nr = line[2:14].strip()
            ep_rap = line[14:24].strip()
            betrag_rap = line[24:36].strip()
            ep = int(ep_rap) / 100 if ep_rap.isdigit() else None
            betrag = int(betrag_rap) / 100 if betrag_rap.isdigit() else None
            # Update existing position
            for pos in projekt.positionen:
                if pos.pos_nr == pos_nr:
                    pos.ep = ep
                    pos.betrag = betrag
                    break
                    
        elif typ == "41":  # Langtext
            # 41 + PosNr(12) + Text(80)
            pos_nr = line[2:14].strip()
            langtext = line[14:94].strip()
            for pos in projekt.positionen:
                if pos.pos_nr == pos_nr:
                    pos.langtext = langtext
                    break
    
    return projekt


def export_sia451(devis: Any, original_lv_path: str, out_path: str) -> Dict[str, Any]:
    """Exportiert Devis als SIA451 Roundtrip — nur Preise geändert, Struktur identisch.
    
    Args:
        devis: DevisPro Devis-Objekt (mit positionen, meta)
        original_lv_path: Pfad zum originalen LV (.e1s/.crbx) für Struktur-Erhalt
        out_path: Ausgabe-Pfad (.e1s)
    
    Returns:
        Dict mit Report: {'updated': n, 'unchanged': n, 'errors': []}
    """
    # 1. Original LV parsen für Struktur
    original = parse_sia451_fixed_width(original_lv_path)
    
    # 2. DevisPro-Positionen nach Pos-Nr matchen
    devis_pos_map = {}
    for p in getattr(devis, "positionen", []):
        if hasattr(p, "pos_nr"):
            devis_pos_map[p.pos_nr.strip()] = p
    
    # 3. Original-Zeilen lesen
    with open(original_lv_path, "r", encoding="iso-8859-1", errors="ignore") as f:
        lines = f.readlines()
    
    # 4. Nur Preis-Zeilen (21/31) aktualisieren
    updated = 0
    errors = []
    out_lines = []
    
    for line in lines:
        if len(line) < 2:
            out_lines.append(line)
            continue
            
        typ = line[:2]
        out_line = line
        
        if typ == "21":  # Position mit Preis
            pos_nr = line[2:14].strip()
            if pos_nr in devis_pos_map:
                p = devis_pos_map[pos_nr]
                if p.ep is not None:
                    ep_rap = f"{int(round(p.ep * 100)):010d}"
                    betrag = p.menge * p.ep
                    betrag_rap = f"{int(round(betrag * 100)):012d}"
                    # EP an Pos 68-77, Betrag 78-89
                    out_line = line[:68] + ep_rap + betrag_rap + line[90:]
                    updated += 1
                    
        elif typ == "31":  # Preiszeile
            pos_nr = line[2:14].strip()
            if pos_nr in devis_pos_map:
                p = devis_pos_map[pos_nr]
                if p.ep is not None:
                    ep_rap = f"{int(round(p.ep * 100)):010d}"
                    betrag = p.menge * p.ep
                    betrag_rap = f"{int(round(betrag * 100)):012d}"
                    out_line = line[:14] + ep_rap + betrag_rap + line[36:]
                    updated += 1
                    
        out_lines.append(out_line)
    
    # 5. Schreiben
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="iso-8859-1") as f:
        f.writelines(out_lines)
    
    report = {
        "updated": updated,
        "total_positions": len(original.positionen),
        "matched": len([p for p in original.positionen if p.pos_nr in devis_pos_map]),
        "output": out_path,
    }
    logger.info(f"SIA451 Roundtrip Export: {report}")
    return report


def roundtrip_test(original_lv: str, devis: Any, tmp_dir: Optional[str] = None) -> Dict[str, Any]:
    """Test: Import → Bearbeiten → Export → Diff (soll nur Preise unterscheiden)."""
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp(prefix="sia451_rt_")
    
    out_path = os.path.join(tmp_dir, "roundtrip.e1s")
    report = export_sia451(devis, original_lv, out_path)
    
    # Diff: Original vs Export
    with open(original_lv, "r", encoding="iso-8859-1", errors="ignore") as f:
        orig_lines = f.readlines()
    with open(out_path, "r", encoding="iso-8859-1", errors="ignore") as f:
        new_lines = f.readlines()
    
    diffs = []
    for i, (o, n) in enumerate(zip(orig_lines, new_lines)):
        if o != n:
            diffs.append({"line": i+1, "original": o.strip(), "export": n.strip()})
    
    report["diff_count"] = len(diffs)
    report["diffs"] = diffs[:20]  # max 20
    report["roundtrip_ok"] = all(
        d["original"][2:4] in ("21", "31") for d in diffs  # nur Preis-Zeilen geändert
    )
    return report


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        proj = parse_sia451_fixed_width(sys.argv[1])
        print(f"Projekt: {proj.projekt_nr} - {proj.projekt_name}")
        print(f"Positionen: {len(proj.positionen)}")
        for p in proj.positionen[:5]:
            print(f"  {p.pos_nr}: {p.text[:40]} | {p.menge} {p.einheit} | EP: {p.ep}")