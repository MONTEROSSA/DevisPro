"""E2E-Tests fuer den DevisPro-SIA-Format Parser (M16).

Nutzt TEST_DEVIS_DIR (env oder User-Dir) - keine Hardcoded Live-Pfade.
"""
import sys
import os
import tempfile
from pathlib import Path

# Test-Daten-Dir bestimmen
test_data = os.environ.get("DEVISPRO_TEST_DIR")
if test_data:
    TEST_DEVIS_DIR = Path(test_data)
else:
    # Default: User-Application-Support
    user_dir = Path.home() / "Library" / "Application Support" / "DevisPro" / "devis"
    if user_dir.exists() and any(user_dir.iterdir()):
        TEST_DEVIS_DIR = user_dir
    else:
        # Fallback: Temp mit Test-Daten
        from tests._test_data import ensure_test_data
        TEST_DEVIS_DIR = ensure_test_data() / "devis"

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')
from devispro.parsers.devispro_sia import parse as devispro_parse


def test_parse_devis_0001():
    """devis_0001: Standard-Devis parsen."""
    p = TEST_DEVIS_DIR / "devis_0001" / "bepreist.sia"
    if not p.exists():
        import pytest
        pytest.skip(f"{p} nicht vorhanden")
    dev = devispro_parse(str(p))
    assert dev is not None
    assert len(dev.positions) >= 1
    total = sum(p.betrag for p in dev.positions)
    assert total > 0
    print(f"OK: devis_0001 - {len(dev.positions)} Positionen, Total CHF {total:.2f}")


def test_parse_header():
    """Header-Zeile (01) muss project_id, name, devis_nr, date, currency extrahieren."""
    test_sia = tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False)
    test_sia.write("01D0001    Test Projekt                A1      20260904CHF\n")
    test_sia.write("11110000000000Test Pos 1                  0000001000m2  \n")
    test_sia.write("311100000000000000005000000000005000\n")
    test_sia.write("99000001\n")
    test_sia.close()
    dev = devispro_parse(test_sia.name)
    os.unlink(test_sia.name)
    assert dev.meta["project_id"] == "D0001"
    assert dev.meta["project_name"] == "Test Projekt"
    assert dev.meta["devis_nr"] == "A1"
    assert dev.meta["date"] == "20260904"
    assert dev.meta["currency"] == "CHF"
    assert len(dev.positions) == 1
    print("OK: Header-Parsing - alle 5 Felder korrekt")


def test_parse_empty():
    """Leere bepreist.sia darf nicht crashen."""
    test_sia = tempfile.NamedTemporaryFile(mode='w', suffix='.sia', delete=False)
    test_sia.write("")
    test_sia.close()
    dev = devispro_parse(test_sia.name)
    os.unlink(test_sia.name)
    assert dev is not None
    assert len(dev.positions) == 0
    print("OK: Leere Datei - 0 Positionen, kein Crash")


def test_all_devis():
    """Alle verfuegbaren Devis muessen parsbar sein."""
    if not TEST_DEVIS_DIR.exists():
        import pytest
        pytest.skip(f"{TEST_DEVIS_DIR} existiert nicht")
    count = 0
    total_positions = 0
    for dev_dir in sorted(TEST_DEVIS_DIR.iterdir()):
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
    assert total_positions > 0


if __name__ == "__main__":
    print("=" * 60)
    print("DevisPro-SIA-Format Parser - E2E Tests")
    print("=" * 60)
    test_parse_devis_0001()
    test_parse_header()
    test_parse_empty()
    test_all_devis()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN")
    print("=" * 60)