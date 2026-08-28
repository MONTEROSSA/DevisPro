"""SIA 451 Roundtrip: Import -> Export -> Diff (nur Preise geändert)."""

from __future__ import annotations
import difflib
import tempfile
from pathlib import Path
from typing import Any

from .crb import parse as crb_parse, export as crb_export
from ..models import Devis, Position


def export_sia451(devis: Devis, original_lv_path: str) -> str:
    """
    Exportiert Devis als SIA-451 Roundtrip-Format.
    
    Erstellt eine LV-Datei die dem Original entspricht, aber mit 
    bepreisten Positionen (EP + Betrag gefüllt).
    
    Args:
        devis: Devis-Objekt mit bepreisten Positionen
        original_lv_path: Pfad zur Original-LV (für Metadaten-Struktur)
    
    Returns:
        Pfad zur exportierten SIA-451 Datei
    """
    # Original-LV parsen für Metadaten-Struktur (Kopf, Gliederung)
    original = crb_parse(original_lv_path)
    
    # Neues Devis-Objekt: Original-Metadaten + bepreiste Positionen
    roundtrip_devis = Devis(
        meta={
            **original.meta,
            "version": "SIA451-ROUNDTRIP",
            "currency": original.meta.get("currency", "CHF"),
        },
        addresses=original.addresses,
        chapters=original.chapters,
        positions=devis.positions,  # Positionen mit Preisen
    )
    
    # Temporäre Datei für Export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False, encoding='utf-8') as f:
        output_path = f.name
    
    crb_export(roundtrip_devis, output_path)
    return output_path


def roundtrip_test(original_lv_path: str, priced_devis: Devis) -> dict[str, Any]:
    """
    Roundtrip-Test: Import -> Export -> Diff.
    
    Verifiziert dass nur Preise geändert wurden (EP, Betrag),
    alle anderen Felder (Pos-Nr, Text, Menge, Einheit, Gliederung) identisch.
    
    Returns:
        Dict mit Test-Ergebnis: {'passed': bool, 'diff_lines': int, 'details': list}
    """
    # 1. Original importieren
    original = crb_parse(original_lv_path)
    
    # 2. Export mit bepreisten Positionen
    exported_path = export_sia451(priced_devis, original_lv_path)
    
    # 3. Wieder importieren
    reimported = crb_parse(exported_path)
    
    # 4. Vergleichen (Zeile für Zeile als Text für exakte fixed-width Prüfung)
    with open(original_lv_path, 'r', encoding='utf-8') as f:
        original_lines = f.readlines()
    
    with open(exported_path, 'r', encoding='utf-8') as f:
        exported_lines = f.readlines()
    
    # Diff berechnen
    diff = list(difflib.unified_diff(
        original_lines, exported_lines,
        fromfile='original', tofile='exported',
        lineterm=''
    ))
    
    # Nur Preis-Zeilen (Typ 31) dürfen sich ändern
    price_changes_only = True
    changed_non_price = []
    
    for line in diff:
        if line.startswith('+') or line.startswith('-'):
            # Header-Linien überspringen
            if line.startswith('+++') or line.startswith('---') or line.startswith('@@'):
                continue
            content = line[1:].strip()
            if content and not content.startswith('31'):  # Nicht Preiszeile
                price_changes_only = False
                changed_non_price.append(content[:80])
    
    # Cleanup
    Path(exported_path).unlink(missing_ok=True)
    
    return {
        'passed': price_changes_only,
        'diff_count': len([d for d in diff if d.startswith('+') or d.startswith('-')]),
        'price_changes_only': price_changes_only,
        'non_price_changes': changed_non_price,
        'original_positions': len(original.positions),
        'exported_positions': len(reimported.positions),
        'details': diff[:50]  # Erste 50 Diff-Zeilen
    }


def validate_positions_unchanged(original: Devis, reimported: Devis) -> dict[str, Any]:
    """
    Validiert dass Positionen (außer Preise) unverändert sind.
    """
    issues = []
    
    if len(original.positions) != len(reimported.positions):
        issues.append(f"Positionsanzahl geändert: {len(original.positions)} -> {len(reimported.positions)}")
    
    for i, (orig, reimp) in enumerate(zip(original.positions, reimported.positions)):
        if orig.pos_nr != reimp.pos_nr:
            issues.append(f"Pos {i}: pos_nr geändert '{orig.pos_nr}' -> '{reimp.pos_nr}'")
        if orig.text != reimp.text:
            issues.append(f"Pos {i}: text geändert")
        if abs(orig.menge - reimp.menge) > 0.01:
            issues.append(f"Pos {i}: menge geändert {orig.menge} -> {reimp.menge}")
        if orig.einheit != reimp.einheit:
            issues.append(f"Pos {i}: einheit geändert '{orig.einheit}' -> '{reimp.einheit}'")
        if orig.chapter != reimp.chapter:
            issues.append(f"Pos {i}: chapter geändert")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }


if __name__ == "__main__":
    # Demo / Selbsttest
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m parsers.sia451_roundtrip <original_lv.sia> [priced_lv.json]")
        sys.exit(1)
    
    original_path = sys.argv[1]
    
    # Original parsen
    original = crb_parse(original_path)
    print(f"Original: {len(original.positions)} Positionen geladen")
    print(f"  Projekt: {original.meta.get('project_name', 'N/A')}")
    print(f"  Währung: {original.meta.get('currency', 'CHF')}")
    
    # Wenn priced_lv.json gegeben: Roundtrip testen
    if len(sys.argv) > 2:
        from .json_if import parse as json_parse
        priced = json_parse(sys.argv[2])
        print(f"Bepreist: {len(priced.positions)} Positionen geladen")
        
        result = roundtrip_test(original_path, priced)
        print(f"\nRoundtrip Test: {'BESTANDEN' if result['passed'] else 'FEHLGESCHLAGEN'}")
        print(f"  Diff-Zeilen: {result['diff_count']}")
        print(f"  Nur Preis-Änderungen: {result['price_changes_only']}")
        if result['non_price_changes']:
            print(f"  NICHT-Preis-Änderungen: {result['non_price_changes'][:5]}")
        for d in result['details'][:20]:
            print(f"    {d}")
    else:
        # Demo: Positionen mit Dummy-Preisen füllen
        for p in original.positions:
            if p.ep is None:
                p.ep = 100.0  # Dummy EP
            p.fill()
        
        result = roundtrip_test(original_path, original)
        print(f"\nRoundtrip Test (Dummy-Preise): {'BESTANDEN' if result['passed'] else 'FEHLGESCHLAGEN'}")
        print(f"  Diff-Zeilen: {result['diff_count']}")
        print(f"  Nur Preis-Änderungen: {result['price_changes_only']}")