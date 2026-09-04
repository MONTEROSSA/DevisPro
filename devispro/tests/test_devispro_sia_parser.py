"""E2E-Tests fuer den neuen DevisPro-SIA-Format-Parser."""
import sys
import os
from pathlib import Path

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

from devispro.parsers.devispro_sia import parse as devispro_parse


def test_parse_devis_0001():
    """devis_0001: Sanierung Einfamilienhaus, 7 Positionen"""
    p = '/Users/ferdinandrothlisberger/Library/Application Support/DevisPro/devis/devis_0001/bepreist.sia'
    if not os.path.exists(p):
        print(f"SKIP: {p} existiert nicht")
        return
    dev = devispro_parse(p)
    assert dev is not None
    assert len(dev.positions) == 7, f"Erwartet 7 Positionen, gefunden {len(dev.positions)}"
    total = sum(p.betrag for p in dev.positions)
    assert 8000 < total < 11000, f"Total {total} ausserhalb plausibler Range"
    print(f"OK: devis_0001 - 7 Positionen, Total CHF {total:.2f}")
    pos1 = dev.positions[0]
    assert pos1.text == "Innenanstrich Wand 2 Anstriche", f"Falscher Text: {pos1.text!r}"
    assert pos1.menge == 65.0, f"Falsche Menge: {pos1.menge}"
    assert pos1.einheit == "m2", f"Falsche Einheit: {pos1.einheit!r}"
    assert abs(pos1.ep - 42.50) < 0.01, f"Falscher EP: {pos1.ep}"
    assert abs(pos1.betrag - 2762.50) < 0.01, f"Falscher Total: {pos1.betrag}"
    print(f"OK: devis_0001[0] - Innenanstrich 65m2 x 42.50 = 2762.50")


def test_parse_header():
    """Header-Zeile (01) muss project_id, name, devis_nr, date, currency extrahieren"""
    import tempfile
    test_sia = tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False)
    test_sia.write("01D0001    Test Projekt                A1      20260904CHF\n")
    test_sia.write("11110000000000Test Pos 1                  0000001000m2  \n")
    test_sia.write("311100000000000000005000000000005000\n")
    test_sia.write("99000001\n")
    test_sia.close()
    dev = devispro_parse(test_sia.name)
    os.unlink(test_sia.name)
    assert dev.meta["project_id"] == "D0001", f"project_id={dev.meta['project_id']!r}"
    assert dev.meta["project_name"] == "Test Projekt", f"name={dev.meta['project_name']!r}"
    assert dev.meta["devis_nr"] == "A1", f"devis_nr={dev.meta['devis_nr']!r}"
    assert dev.meta["date"] == "20260904", f"date={dev.meta['date']!r}"
    assert dev.meta["currency"] == "CHF", f"currency={dev.meta['currency']!r}"
    assert len(dev.positions) == 1
    print("OK: Header-Parsing - alle 5 Felder korrekt")


def test_parse_empty():
    """Leere bepreist.sia darf nicht crashen"""
    import tempfile
    test_sia = tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False)
    test_sia.write("")
    test_sia.close()
    dev = devispro_parse(test_sia.name)
    os.unlink(test_sia.name)
    assert dev is not None
    assert len(dev.positions) == 0
    print("OK: Leere Datei - 0 Positionen, kein Crash")


def test_parse_all_devis():
    """Alle 36 Devis im Store muessen parsbar sein"""
    devis_dir = Path('/Users/ferdinandrothlisberger/Library/Application Support/DevisPro/devis')
    if not devis_dir.exists():
        print(f"SKIP: {devis_dir} existiert nicht")
        return
    count = 0
    total_positions = 0
    for dev_dir in sorted(devis_dir.iterdir()):
        sia = dev_dir / "bepreist.sia"
        if not sia.exists():
            continue
        try:
            dev = devispro_parse(str(sia))
            count += 1
            total_positions += len(dev.positions)
        except Exception as e:
            print(f"FAIL bei {dev_dir.name}: {e}")
            raise
    assert count > 0
    print(f"OK: {count} Devis geparst, {total_positions} Positionen gesamt")
    assert total_positions > 0, "Mindestens eine Position muss da sein"


if __name__ == "__main__":
    print("=" * 60)
    print("DevisPro-SIA-Format Parser - E2E Tests")
    print("=" * 60)
    test_parse_header()
    test_parse_empty()
    test_parse_devis_0001()
    test_parse_all_devis()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN")
    print("=" * 60)