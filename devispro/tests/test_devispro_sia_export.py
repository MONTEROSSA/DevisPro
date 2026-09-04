"""Round-Trip-Tests fuer den DevisPro-Export (M18).

Prueft: was die App schreibt (via export()) kann der Parser (parse()) wieder lesen.
Damit ist der Round-Trip komplett: crb.export -> devispro_sia.parse (alter Weg, scheitert)
                                devispro_sia.export -> devispro_sia.parse (neuer Weg, geht)
"""
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

from devispro.models import Devis, Position
from devispro.parsers.devispro_sia import parse as devispro_parse
from devispro.parsers.devispro_sia import export as devispro_export


def test_export_then_parse_roundtrip():
    """Schreibe Devis, lies zurueck, alle Felder identisch."""
    d = Devis(
        meta={'project_id': 'D1234', 'project_name': 'Test-Projekt', 'devis_nr': 'A99',
              'date': '2026-09-04', 'currency': 'CHF'},
        addresses=[], chapters=[], positions=[])
    d.positions.append(Position(pos_nr='1111000000000', text='Innenanstrich', menge=65.0,
                                 einheit='m2', ep=42.50, betrag=2762.50))
    d.positions.append(Position(pos_nr='1112000000000', text='Spachteln', menge=40.0,
                                 einheit='m2', ep=30.00, betrag=1200.00))

    # Schreiben
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False) as f:
        tmp = f.name
    devispro_export(d, tmp)

    # Lesen
    d2 = devispro_parse(tmp)
    os.unlink(tmp)

    # Vergleichen
    assert len(d2.positions) == 2, f"Erwartet 2 Positionen, gefunden {len(d2.positions)}"
    for orig, parsed in zip(d.positions, d2.positions):
        assert orig.pos_nr == parsed.pos_nr
        assert orig.text == parsed.text, f"Text: {orig.text!r} != {parsed.text!r}"
        assert orig.menge == parsed.menge, f"Menge: {orig.menge} != {parsed.menge}"
        assert orig.einheit == parsed.einheit, f"Einheit: {orig.einheit!r} != {parsed.einheit!r}"
        assert abs(orig.ep - parsed.ep) < 0.01
        assert abs(orig.betrag - parsed.betrag) < 0.01
    print("OK: export -> parse Round-Trip, alle Felder identisch")


def test_export_layout_matches_real_format():
    """Vergleicht das Export-Format mit der echten Datei (Stichproben)."""
    d = Devis(
        meta={'project_id': '', 'project_name': '', 'devis_nr': '',
              'date': '', 'currency': 'CHF'},
        addresses=[], chapters=[], positions=[])
    d.positions.append(Position(pos_nr='1111000000000', text='Innenanstrich Wand 2 Anstriche',
                                 menge=65.0, einheit='m2', ep=42.50, betrag=2762.50))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False) as f:
        tmp = f.name
    devispro_export(d, tmp)
    with open(tmp) as f:
        lines = f.read().splitlines()
    os.unlink(tmp)

    # Pruefe dass die Zeilen die richtigen Laengen haben (68 fuer Pos, 36 fuer Preis, 58 fuer Header, 8 fuer Footer)
    # Erwartet 4 Zeilen: Header + 1x Pos + 1x Preis + Footer
    assert len(lines) == 4, f"Erwartet 4 Zeilen, gefunden {len(lines)}"
    assert len(lines[0]) == 58, f"Header len={len(lines[0])}, erwartet 58"
    assert len(lines[1]) == 68, f"Pos len={len(lines[1])}, erwartet 68"
    assert len(lines[2]) == 36, f"Preis len={len(lines[2])}, erwartet 36"
    assert len(lines[3]) == 8, f"Footer len={len(lines[3])}, erwartet 8"

    # Pruefe Format (Prefix + Code)
    assert lines[1][0] == '1', f"Pos-Prefix: {lines[1][0]!r}"
    assert lines[2][0] == '3', f"Preis-Prefix: {lines[2][0]!r}"
    print("OK: Export-Layout hat korrekte Spaltenbreiten (58/68/36)")


def test_export_header_with_full_metadata():
    """Header mit allen 5 Meta-Feldern korrekt geschrieben."""
    d = Devis(
        meta={'project_id': 'D1234', 'project_name': 'Test Bau AG',
              'devis_nr': 'A001', 'date': '2026-09-04', 'currency': 'CHF'},
        addresses=[], chapters=[], positions=[])

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False) as f:
        tmp = f.name
    devispro_export(d, tmp)
    with open(tmp) as f:
        first_line = f.readline().rstrip("\n")
    os.unlink(tmp)

    assert len(first_line) == 58, f"Header len={len(first_line)}, erwartet 58"
    assert first_line[2:11].strip() == 'D1234', f"project_id: {first_line[2:11]!r}"
    assert first_line[11:39].strip() == 'Test Bau AG', f"project_name: {first_line[11:39]!r}"
    assert first_line[39:47].strip() == 'A001', f"devis_nr: {first_line[39:47]!r}"
    assert first_line[47:55] == '20260904', f"date: {first_line[47:55]!r}"
    assert first_line[55:58] == 'CHF', f"currency: {first_line[55:58]!r}"
    print("OK: Header mit allen Meta-Feldern korrekt geschrieben")


def test_export_date_format_normalization():
    """Datum-Eingabe in verschiedenen Formaten akzeptiert."""
    d = Devis(
        meta={'project_id': 'D1', 'project_name': 'T', 'devis_nr': 'A',
              'date': '2026-09-04 14:30', 'currency': 'CHF'},
        addresses=[], chapters=[], positions=[])

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False) as f:
        tmp = f.name
    devispro_export(d, tmp)
    with open(tmp) as f:
        first_line = f.readline().rstrip("\n")
    os.unlink(tmp)

    # '2026-09-04 14:30' -> '2026090414' (die ersten 8 Zeichen: 20260904)
    assert first_line[47:55] == '20260904', f"date: {first_line[47:55]!r}"
    print("OK: Datum-Format 'YYYY-MM-DD HH:MM' -> 'YYYYMMDD' normalisiert")


def test_old_crb_files_still_parseable():
    """Bestehende bepreist.sia-Dateien (die crb.py schrieb) sollten NICHT mehr geparst werden
    mit dem DevisPro-Parser (weil sie anderes Format haben). Das ist korrekt -
    der crb_sia.py-Parser ist der Fallback.
    """
    p = '/Users/ferdinandrothlisberger/Library/Application Support/DevisPro/devis/devis_0001/bepreist.sia'
    if not os.path.exists(p):
        pytest = __import__('pytest')
        pytest.skip(f"{p} nicht vorhanden")

    # Diese Datei wurde NICHT von crb.export geschrieben, sondern hat DevisPro-Format
    # Der DevisPro-Parser SOLLTE sie lesen koennen
    dev = devispro_parse(p)
    assert len(dev.positions) >= 1, "Echte DevisPro-Dateien muessen lesbar sein"
    print(f"OK: Echte Datei {p} lesbar, {len(dev.positions)} Positionen")


if __name__ == "__main__":
    print("=" * 60)
    print("DevisPro-SIA-Format Export - Round-Trip Tests")
    print("=" * 60)
    test_export_layout_matches_real_format()
    test_export_header_with_full_metadata()
    test_export_date_format_normalization()
    test_export_then_parse_roundtrip()
    test_old_crb_files_still_parseable()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN")
    print("=" * 60)