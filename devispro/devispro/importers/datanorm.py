"""Datanorm 4/5 Parser für Lieferantenkataloge (.dat/.daten)."""
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Datanorm Satzarten
SATZART_KOPF = "000"
SATZART_HERSTELLER = "100"
SATZART_ARTIKEL = "200"
SATZART_PREIS = "300"
SATZART_LANGTEXT = "400"
SATZART_ZUSATZ = "500"

def parse_datanorm(path: str) -> List[Dict[str, Any]]:
    """Parst Datanorm 4/5 Datei und gibt Liste von Artikeln zurück."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Datanorm-Datei nicht gefunden: {path}")
    
    # Encoding erkennen (meist ISO-8859-1 / Latin-1)
    for encoding in ("iso-8859-1", "cp1252", "utf-8"):
        try:
            with open(path, "r", encoding=encoding) as f:
                lines = f.readlines()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Kein passendes Encoding gefunden (versucht: latin-1, cp1252, utf-8)")
    
    artikel_dict: Dict[str, Dict[str, Any]] = {}
    hersteller_map: Dict[str, str] = {}
    current_hersteller = ""
    
    for line_num, line in enumerate(lines, 1):
        line = line.rstrip("\n\r")
        if len(line) < 4:
            continue
            
        satzart = line[:3]
        
        if satzart == SATZART_HERSTELLER:
            # Hersteller-Satz: 100 + Herstellernummer(7) + Name(40) + ...
            hersteller_nr = line[3:10].strip()
            hersteller_name = line[10:50].strip()
            hersteller_map[hersteller_nr] = hersteller_name
            
        elif satzart == SATZART_ARTIKEL:
            # Artikel-Satz: 200 + Artikelnummer(18) + EAN(14) + Herstellernummer(7) + 
            # Bestellnummer(20) + Bezeichnung1(40) + Bezeichnung2(40) + Einheit(4) + ...
            artikel_nr = line[3:21].strip()
            ean = line[21:35].strip()
            hersteller_nr = line[35:42].strip()
            bestell_nr = line[42:62].strip()
            bezeichnung1 = line[62:102].strip()
            bezeichnung2 = line[102:142].strip()
            einheit = line[142:146].strip()
            rabattgruppe = line[146:149].strip()
            preis_ek = line[149:160].strip()  # in Cent/Rappen
            preis_vk = line[160:171].strip()
            
            hersteller_name = hersteller_map.get(hersteller_nr, "")
            
            key = f"{artikel_nr}|{ean}"
            if key not in artikel_dict:
                artikel_dict[key] = {
                    "artikelnummer": artikel_nr,
                    "ean": ean or None,
                    "hersteller": hersteller_name,
                    "hersteller_nr": hersteller_nr,
                    "bestellnummer": bestell_nr,
                    "bezeichnung": f"{bezeichnung1} {bezeichnung2}".strip(),
                    "einheit": einheit or "STK",
                    "rabattgruppe": rabattgruppe or None,
                    "preis_ek": float(preis_ek) / 100 if preis_ek.isdigit() else None,
                    "preis_vk": float(preis_vk) / 100 if preis_vk.isdigit() else None,
                    "langtexte": [],
                    "zusatzdaten": {},
                }
                
        elif satzart == SATZART_LANGTEXT and artikel_dict:
            # Langtext-Satz: 400 + Artikelnummer(18) + Text(80) + ...
            artikel_nr = line[3:21].strip()
            langtext = line[21:101].strip()
            # Finde passenden Artikel (erste Übereinstimmung)
            for key, art in artikel_dict.items():
                if art["artikelnummer"] == artikel_nr:
                    art["langtexte"].append(langtext)
                    break
                    
        elif satzart == SATZART_ZUSATZ and artikel_dict:
            # Zusatzdaten-Satz: 500 + Artikelnummer(18) + ...
            artikel_nr = line[3:21].strip()
            zusatz_typ = line[21:24].strip()
            zusatz_wert = line[24:].strip()
            for key, art in artikel_dict.items():
                if art["artikelnummer"] == artikel_nr:
                    art["zusatzdaten"][zusatz_typ] = zusatz_wert
                    break
    
    # Dubletten entfernen (bevorzuge Eintrag mit mehr Daten)
    result = []
    seen = set()
    for art in artikel_dict.values():
        dedup_key = (art["artikelnummer"], art["ean"] or "")
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        # Bezeichung zusammenfassen
        if art["langtexte"]:
            art["bezeichnung"] += " | " + " ".join(art["langtexte"])
        result.append(art)
    
    logger.info(f"Datanorm geparst: {len(result)} Artikel aus {path.name}")
    return result


def detect_datanorm_version(path: str) -> int:
    """Erkennt Datanorm-Version (4 oder 5) anhand Header."""
    with open(path, "r", encoding="iso-8859-1", errors="ignore") as f:
        first_line = f.readline().strip()
    if first_line.startswith("000"):
        # Version 5 hat erweiterte Felder im Kopf-Satz
        if len(first_line) > 200:
            return 5
        return 4
    return 4


def import_to_meine_preise(datanorm_path: str, meine_preise_path: str) -> Dict[str, int]:
    """Importiert Datanorm-Artikel in meine_preise.csv (Mapping UI separat)."""
    from firmen_preise import laden, speichern
    import csv
    
    artikel = parse_datanorm(datanorm_path)
    existing = laden(meine_preise_path)
    existing_keys = {(a.get("artikelnummer"), a.get("ean")) for a in existing}
    
    added = 0
    updated = 0
    
    for art in artikel:
        key = (art["artikelnummer"], art["ean"])
        preis = art["preis_vk"] or art["preis_ek"]
        if preis is None:
            continue
            
        eintrag = {
            "artikelnummer": art["artikelnummer"],
            "ean": art["ean"] or "",
            "bezeichnung": art["bezeichnung"],
            "einheit": art["einheit"],
            "preis": preis,
            "hersteller": art["hersteller"],
            "kategorie": _kategorie_aus_bezeichnung(art["bezeichnung"]),
        }
        
        if key in existing_keys:
            # Update
            for i, ex in enumerate(existing):
                if (ex.get("artikelnummer"), ex.get("ean")) == key:
                    existing[i] = eintrag
                    updated += 1
                    break
        else:
            existing.append(eintrag)
            added += 1
    
    speichern(existing, meine_preise_path)
    return {"added": added, "updated": updated, "total": len(existing)}


def _kategorie_aus_bezeichnung(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("beton", "fundament", "erdbau", "abtra", "bagger")):
        return "Erdbau/Beton"
    if any(w in t for w in ("mauer", "wand", "gips", "putz", "ziegel", "stein")):
        return "Mauerwerk/Gips"
    if any(w in t for w in ("elektro", "kabel", "strom", "steck", "leuchte", "schalter")):
        return "Elektro"
    if any(w in t for w in ("sanit", "wasser", "abfluss", "rohr", "wc", "bad", "dusche")):
        return "Sanitär"
    if any(w in t for w in ("anstrich", "farbe", "lack", "maler", "tapezier", "grundier")):
        return "Maler"
    if any(w in t for w in ("dach", "isolation", "dämm", "folie", "abdicht")):
        return "Dach/Isolation"
    if any(w in t for w in ("boden", "platten", "fliesen", "parkett", "estrich", "belag")):
        return "Boden/Platten"
    if any(w in t for w in ("fenster", "tür", "tuer", "verglasung", "rahmen")):
        return "Fenster/Türen"
    return "Allgemein"


# Test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        artikel = parse_datanorm(sys.argv[1])
        print(f"Gefunden: {len(artikel)} Artikel")
        for a in artikel[:3]:
            print(f"  {a['artikelnummer']} | {a['ean']} | {a['bezeichnung'][:50]} | {a['einheit']} | {a['preis_vk']}")