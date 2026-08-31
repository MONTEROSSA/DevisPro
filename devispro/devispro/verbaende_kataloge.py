#!/usr/bin/env python3
"""
Verbandskataloge Import für DevisPro
Unterstützt: NPK (Niederländische Posities Katalogus), BKS (BauKostenStandard), 
HLKS (Hochbau-Landschaftskatalog Schweiz), CRB (Construction Reference Book)
"""

import csv
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class KatalogPosition:
    """Einheitliche Position aus Verbandskatalog"""
    katalog: str           # "NPK", "BKS", "HLKS", "CRB"
    jahr: int              # Katalog-Jahrgang
    nummer: str            # Positionsnummer (z.B. "01.02.03.04")
    titel: str             # Langtext
    kurztext: str          # Kurztext
    einheit: str           # Einheit (m2, m3, Stk, etc.)
    preis: float           # Richtpreis CHF
    waehrung: str = "CHF"
    kategorie: str = ""    # Hauptkategorie (z.B. "Erdarbeiten")
    unterkategorie: str = ""  # Unterkategorie
    zusatzinfo: Optional[Dict] = None  # Zusätzliche Metadaten
    
    def __post_init__(self):
        if self.zusatzinfo is None:
            self.zusatzinfo = {}


class KatalogImporter:
    """Importiert verschiedene Verbandskatalog-Formate"""
    
    # NPK: CSV mit ; Trennung, Spalten: PosNr;Titel;Kurztext;Einheit;Preis;Kategorie
    # BKS: Excel/CSV, spezifische Struktur
    # HLKS: CSV, Schweizer Format
    # CRB: CSV, deutsche Struktur
    
    FORMAT_HANDLERS = {
        'npk': '_import_npk',
        'bks': '_import_bks', 
        'hlks': '_import_hlks',
        'crb': '_import_crb',
    }
    
    def __init__(self, katalog_dir: str = "kataloge"):
        self.katalog_dir = Path(katalog_dir)
        self.katalog_dir.mkdir(exist_ok=True)
        self.positionen: List[KatalogPosition] = []
        self.stats = {
            'total': 0,
            'by_katalog': {},
            'errors': []
        }
    
    def import_katalog(self, file_path: str, katalog_typ: str, jahr: int) -> Dict:
        """Importiert einen Katalog basierend auf Typ"""
        handler_name = self.FORMAT_HANDLERS.get(katalog_typ.lower())
        if not handler_name:
            raise ValueError(f"Unbekannter Katalog-Typ: {katalog_typ}")
        
        handler = getattr(self, handler_name)
        return handler(file_path, jahr)
    
    def _import_npk(self, file_path: str, jahr: int) -> Dict:
        """Importiert NPK-Katalog (CSV, ; getrennt)"""
        count = 0
        errors = []
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # NPK hat oft Header-Zeilen, erste valide Zeile finden
            lines = f.readlines()
        
        # Header finden (erste Zeile mit ; und mindestens 5 Spalten)
        header_idx = 0
        for i, line in enumerate(lines):
            if line.count(';') >= 5 and not line.startswith('#'):
                header_idx = i
                break
        
        reader = csv.DictReader(lines[header_idx:], delimiter=';')
        
        for row_num, row in enumerate(reader, header_idx + 2):
            try:
                # Sichere Defaults als Strings (sonst scheitert .strip()/.replace())
                def _s(k, default=''):
                    v = row.get(k, default)
                    return str(v) if v is not None else default
                pos = KatalogPosition(
                    katalog="NPK",
                    jahr=jahr,
                    nummer=_s('PosNr', _s('Nummer', '')).strip(),
                    titel=_s('Titel', _s('Langtext', '')).strip(),
                    kurztext=_s('Kurztext', '').strip(),
                    einheit=_s('Einheit', _s('ME', 'Stk')).strip(),
                    preis=float(_s('Preis', _s('Richtpreis', '0')).replace(',', '.')),
                    kategorie=_s('Kategorie', _s('Hauptgruppe', '')).strip(),
                    unterkategorie=_s('Unterkategorie', _s('Untergruppe', '')).strip(),
                    zusatzinfo={'original_row': row}
                )
                if pos.nummer and pos.titel:
                    self.positionen.append(pos)
                    count += 1
            except Exception as e:
                errors.append(f"Zeile {row_num}: {e}")
        
        self.stats['by_katalog']['NPK'] = count
        return {'imported': count, 'errors': errors}
    
    def _import_bks(self, file_path: str, jahr: int) -> Dict:
        """Importiert BKS-Katalog"""
        count = 0
        errors = []
        
        # BKS oft als Excel (.xlsx) - hier CSV-Fallback
        if file_path.endswith('.xlsx'):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_path, read_only=True)
                ws = wb.active
                rows = ws.iter_rows(values_only=True)
                first_row = next(rows, None)
                if not first_row:
                    return {'imported': 0, 'errors': ['Leere Excel-Datei']}
                headers = [str(h) if h is not None else '' for h in first_row]
                header_map = {h.lower().strip(): i for i, h in enumerate(headers) if h}
                
                for row_num, row in enumerate(rows, 2):
                    try:
                        pos = KatalogPosition(
                            katalog="BKS",
                            jahr=jahr,
                            nummer=str(row[header_map.get('posnr', header_map.get('nummer', 0))] or '').strip(),
                            titel=str(row[header_map.get('titel', header_map.get('langtext', 1))] or '').strip(),
                            kurztext=str(row[header_map.get('kurztext', 2)] or '').strip(),
                            einheit=str(row[header_map.get('einheit', header_map.get('me', 3))] or 'Stk').strip(),
                            preis=float(str(row[header_map.get('preis', header_map.get('richtpreis', 4))] or '0').replace(',', '.')),
                            kategorie=str(row[header_map.get('kategorie', header_map.get('hauptgruppe', 5))] or '').strip(),
                            unterkategorie=str(row[header_map.get('unterkategorie', header_map.get('untergruppe', 6))] or '').strip(),
                            zusatzinfo={'original_row': dict(zip(headers, row))}
                        )
                        if pos.nummer and pos.titel:
                            self.positionen.append(pos)
                            count += 1
                    except Exception as e:
                        errors.append(f"Zeile {row_num}: {e}")
            except ImportError:
                errors.append("openpyxl nicht installiert für .xlsx Import")
        else:
            # CSV Import
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f, delimiter=';')
                for row_num, row in enumerate(reader, 2):
                    try:
                        def _s(k, default=''):
                            v = row.get(k, default)
                            return str(v) if v is not None else default
                        pos = KatalogPosition(
                            katalog="BKS",
                            jahr=jahr,
                            nummer=_s('PosNr', _s('Nummer', '')).strip(),
                            titel=_s('Titel', _s('Langtext', '')).strip(),
                            kurztext=_s('Kurztext', '').strip(),
                            einheit=_s('Einheit', _s('ME', 'Stk')).strip(),
                            preis=float(_s('Preis', _s('Richtpreis', '0')).replace(',', '.')),
                            kategorie=_s('Kategorie', _s('Hauptgruppe', '')).strip(),
                            unterkategorie=_s('Unterkategorie', _s('Untergruppe', '')).strip(),
                            zusatzinfo={'original_row': row}
                        )
                        if pos.nummer and pos.titel:
                            self.positionen.append(pos)
                            count += 1
                    except Exception as e:
                        errors.append(f"Zeile {row_num}: {e}")
        
        self.stats['by_katalog']['BKS'] = count
        return {'imported': count, 'errors': errors}
    
    def _import_hlks(self, file_path: str, jahr: int) -> Dict:
        """Importiert HLKS-Katalog (Schweizer Hochbau-Landschaftskatalog)"""
        count = 0
        errors = []
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # HLKS oft mit Header-Zeilen
            lines = f.readlines()
        
        header_idx = 0
        for i, line in enumerate(lines):
            if line.count(';') >= 4 and not line.startswith('#'):
                header_idx = i
                break
        
        reader = csv.DictReader(lines[header_idx:], delimiter=';')
        
        for row_num, row in enumerate(reader, header_idx + 2):
            try:
                def _s(k, default=''):
                    v = row.get(k, default)
                    return str(v) if v is not None else default
                pos = KatalogPosition(
                    katalog="HLKS",
                    jahr=jahr,
                    nummer=_s('PosNr', _s('Nummer', '')).strip(),
                    titel=_s('Titel', _s('Bezeichnung', '')).strip(),
                    kurztext=_s('Kurztext', _s('Kurzbezeichnung', '')).strip(),
                    einheit=_s('Einheit', _s('ME', 'm2')).strip(),
                    preis=float(_s('Preis', _s('Richtpreis', '0')).replace(',', '.')),
                    kategorie=_s('Hauptgruppe', _s('Kategorie', '')).strip(),
                    unterkategorie=_s('Untergruppe', _s('Unterkategorie', '')).strip(),
                    zusatzinfo={
                        'original_row': row,
                        'kanton': _s('Kanton', '').strip(),
                        'region': _s('Region', '').strip()
                    }
                )
                if pos.nummer and pos.titel:
                    self.positionen.append(pos)
                    count += 1
            except Exception as e:
                errors.append(f"Zeile {row_num}: {e}")
        
        self.stats['by_katalog']['HLKS'] = count
        return {'imported': count, 'errors': errors}
    
    def _import_crb(self, file_path: str, jahr: int) -> Dict:
        """Importiert CRB-Katalog (Construction Reference Book - Deutschland)"""
        count = 0
        errors = []
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        header_idx = 0
        for i, line in enumerate(lines):
            if line.count(';') >= 4 and not line.startswith('#'):
                header_idx = i
                break
        
        reader = csv.DictReader(lines[header_idx:], delimiter=';')
        
        for row_num, row in enumerate(reader, header_idx + 2):
            try:
                def _s(k, default=''):
                    v = row.get(k, default)
                    return str(v) if v is not None else default
                pos = KatalogPosition(
                    katalog="CRB",
                    jahr=jahr,
                    nummer=_s('PosNr', _s('Nummer', '')).strip(),
                    titel=_s('Titel', _s('Langtext', '')).strip(),
                    kurztext=_s('Kurztext', '').strip(),
                    einheit=_s('Einheit', _s('ME', 'Stk')).strip(),
                    preis=float(_s('Preis', _s('Richtpreis', '0')).replace(',', '.')),
                    kategorie=_s('Kategorie', _s('Hauptgruppe', '')).strip(),
                    unterkategorie=_s('Unterkategorie', _s('Untergruppe', '')).strip(),
                    zusatzinfo={
                        'original_row': row,
                        'din_norm': _s('DIN', _s('Norm', '')).strip(),
                        'vorgabe': _s('Vorgabe', '').strip()
                    }
                )
                if pos.nummer and pos.titel:
                    self.positionen.append(pos)
                    count += 1
            except Exception as e:
                errors.append(f"Zeile {row_num}: {e}")
        
        self.stats['by_katalog']['CRB'] = count
        return {'imported': count, 'errors': errors}
    
    def export_json(self, output_path: str) -> Dict:
        """Exportiert alle Positionen als JSON"""
        output = {
            'meta': {
                'exported_at': datetime.now().isoformat(),
                'total_positions': len(self.positionen),
                'by_katalog': self.stats['by_katalog']
            },
            'positionen': [asdict(p) for p in self.positionen]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output
    
    def export_devispro_json(self, output_path: str) -> Dict:
        """Exportiert im DevisPro-Format für direkten Import"""
        # DevisPro erwartet: Position mit NPK-Nummer, Titel, Einheit, Preis
        devispro_positionen = []
        
        for pos in self.positionen:
            devispro_positionen.append({
                'npk_nummer': pos.nummer,
                'titel': pos.titel,
                'kurztext': pos.kurztext,
                'einheit': pos.einheit,
                'preis': pos.preis,
                'waehrung': pos.waehrung,
                'katalog': pos.katalog,
                'katalog_jahr': pos.jahr,
                'kategorie': pos.kategorie,
                'unterkategorie': pos.unterkategorie
            })
        
        output = {
            'version': '1.0',
            'source': 'Verbandskataloge',
            'imported_at': datetime.now().isoformat(),
            'total': len(devispro_positionen),
            'by_katalog': self.stats['by_katalog'],
            'positionen': devispro_positionen
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        return output
    
    def search(self, query: str, katalog: Optional[str] = None, limit: int = 50) -> List[KatalogPosition]:
        """Sucht in importierten Positionen"""
        query_lower = query.lower()
        results = []
        
        for pos in self.positionen:
            if katalog and pos.katalog != katalog.upper():
                continue
            
            if (query_lower in pos.titel.lower() or 
                query_lower in pos.kurztext.lower() or
                query_lower in pos.nummer.lower() or
                query_lower in pos.kategorie.lower()):
                results.append(pos)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_stats(self) -> Dict:
        self.stats['total'] = len(self.positionen)
        return self.stats


def create_sample_kataloge(katalog_dir: str = "kataloge"):
    """Erstellt Beispiel-Katalog-Dateien für Testing"""
    dir_path = Path(katalog_dir)
    dir_path.mkdir(exist_ok=True)
    
    # NPK Beispiel
    npk_content = """# NPK 2024 Beispiel
PosNr;Titel;Kurztext;Einheit;Preis;Kategorie;Unterkategorie
01.01.01.01;Aushub maschinell, Bodenklasse 1-3;Aushub maschinell;m3;25.50;Erdarbeiten;Aushub
01.01.01.02;Aushub maschinell, Bodenklasse 4-5;Aushub schwer;m3;35.80;Erdarbeiten;Aushub
01.02.01.01;Verfüllen und Verdichten;Verfüllen;m3;18.20;Erdarbeiten;Verfüllen
02.01.01.01;Beton C25/30, fertig gemischt;Beton C25/30;m3;185.00;Betonarbeiten;Sichtbeton
02.01.01.02;Beton C30/37, fertig gemischt;Beton C30/37;m3;195.00;Betonarbeiten;Sichtbeton
03.01.01.01;Mauerwerk Kalksandstein 17,5 N/mm²;KS-Mauerwerk;m2;85.00;Mauerwerk;Kalksandstein
03.01.01.02;Mauerwerk Porenbeton 4 N/mm²;Porenbeton;m2;72.00;Mauerwerk;Porenbeton
04.01.01.01;Dachdeckung Ziegel, inkl. Latten;Ziegeldeckung;m2;125.00;Dacharbeiten;Eindeckung
04.01.01.02;Dachdeckung Blech, Trapezprofil;Blechdach;m2;95.00;Dacharbeiten;Eindeckung
"""
    
    # BKS Beispiel
    bks_content = """PosNr;Titel;Kurztext;Einheit;Preis;Kategorie;Unterkategorie
100.01.01;Erdaushub maschinell Klasse 1-3;Erdaushub;m3;24.80;Erdarbeiten;Aushub
100.01.02;Erdaushub maschinell Klasse 4-5;Erdaushub schwer;m3;34.50;Erdarbeiten;Aushub
200.01.01;Beton C25/30;Beton C25/30;m3;182.00;Beton;Normalbeton
200.01.02;Beton C30/37;Beton C30/37;m3;192.00;Beton;Normalbeton
300.01.01;Mauerwerk KS 12 N/mm²;KS-Mauerwerk;m2;78.00;Mauerwerk;Kalksandstein
300.01.02;Mauerwerk Porenbeton PP4;Porenbeton;m2;68.00;Mauerwerk;Leichtbeton
"""
    
    # HLKS Beispiel (Schweiz)
    hlks_content = """PosNr;Titel;Kurztext;Einheit;Preis;Hauptgruppe;Untergruppe;Kanton;Region
01.01.01;Aushub maschinell, weicher Boden;Aushub weich;m3;28.50;Erdarbeiten;Aushub;ZH;Mittelland
01.01.02;Aushub maschinell, harter Boden;Aushub hart;m3;42.00;Erdarbeiten;Aushub;BE;Mittelland
02.01.01;Beton C30/37, SIA 262;Beton C30/37;m3;210.00;Betonarbeiten;Sichtbeton;ZH;Mittelland
02.01.02;Beton C35/45, SIA 262;Beton C35/45;m3;225.00;Betonarbeiten;Sichtbeton;ZH;Mittelland
03.01.01;Mauerwerk Kalksandstein 20 N/mm²;KS 20;m2;92.00;Mauerwerk;Kalksandstein;ZH;Mittelland
03.01.02;Mauerwerk Hochlochziegel 12 N/mm²;HLZ 12;m2;78.00;Mauerwerk;Ziegel;BE;Mittelland
"""
    
    # CRB Beispiel
    crb_content = """PosNr;Titel;Kurztext;Einheit;Preis;Kategorie;Unterkategorie;DIN;Vorgabe
01.01.01;Erdaushub maschinell Bodenklasse 1-3;Erdaushub 1-3;m3;26.20;Erdarbeiten;Aushub;DIN 18300;
01.01.02;Erdaushub maschinell Bodenklasse 4-5;Erdaushub 4-5;m3;38.50;Erdarbeiten;Aushub;DIN 18300;
02.01.01;Beton C25/30 nach DIN EN 206;Beton C25/30;m3;188.00;Betonarbeiten;Normalbeton;DIN EN 206;
02.01.02;Beton C30/37 nach DIN EN 206;Beton C30/37;m3;198.00;Betonarbeiten;Normalbeton;DIN EN 206;
03.01.01;Mauerwerk Kalksandstein 12 N/mm²;KS 12;m2;82.00;Mauerwerk;Kalksandstein;DIN EN 771-2;
03.01.02;Mauerwerk Porenbeton PP 0,4;Porenbeton PP4;m2;71.00;Mauerwerk;Leichtbeton;DIN EN 771-4;
"""
    
    (dir_path / "npk_2024.csv").write_text(npk_content, encoding='utf-8')
    (dir_path / "bks_2024.csv").write_text(bks_content, encoding='utf-8')
    (dir_path / "hlks_2024.csv").write_text(hlks_content, encoding='utf-8')
    (dir_path / "crb_2024.csv").write_text(crb_content, encoding='utf-8')
    
    print(f"Beispiel-Kataloge erstellt in {katalog_dir}/")
    return {
        'npk': 'npk_2024.csv',
        'bks': 'bks_2024.csv', 
        'hlks': 'hlks_2024.csv',
        'crb': 'crb_2024.csv'
    }


if __name__ == "__main__":
    # Demo
    katalog_dir = "kataloge"
    create_sample_kataloge(katalog_dir)
    
    importer = KatalogImporter(katalog_dir)
    
    # Alle importieren
    results = {}
    for kat, file in [('NPK', 'npk_2024.csv'), ('BKS', 'bks_2024.csv'), 
                       ('HLKS', 'hlks_2024.csv'), ('CRB', 'crb_2024.csv')]:
        result = importer.import_katalog(f"{katalog_dir}/{file}", kat, 2024)
        results[kat] = result
        print(f"{kat}: {result['imported']} Positionen importiert, {len(result['errors'])} Fehler")
    
    # Stats
    print(f"\nGesamt: {importer.get_stats()['total']} Positionen")
    
    # Export für DevisPro
    importer.export_devispro_json("kataloge/verbaende_devispro.json")
    print("\nDevisPro-Export: kataloge/verbaende_devispro.json")
    
    # Suche Test
    results = importer.search("Beton", limit=5)
    print(f"\nSuche 'Beton': {len(results)} Treffer")
    for r in results:
        print(f"  {r.katalog} {r.nummer}: {r.titel} - {r.preis} {r.waehrung}/{r.einheit}")