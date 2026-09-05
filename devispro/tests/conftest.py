"""Setzt TEST-Daten-Dir BEVOR andere Tests importieren.

Enthaelt auch gemeinsame Fixtures fuer die Test-Suite.
"""
import os
import sys
import pytest
from pathlib import Path

# Source-Pfad ins sys.path aufnehmen, damit 'devispro' importierbar ist
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def setup_test_env():
    """Stellt TEST-Daten bereit und setzt DEVISPRO_TEST_DIR env-var."""
    user_dir = Path.home() / "Library" / "Application Support" / "DevisPro" / "devis"
    if user_dir.exists() and any(user_dir.iterdir()):
        # Echte User-Daten vorhanden
        os.environ["DEVISPRO_TEST_DIR"] = str(user_dir)
    else:
        # Erstelle Test-Daten in Temp
        from tests._test_data import ensure_test_data
        test_data = ensure_test_data()
        os.environ["DEVISPRO_TEST_DIR"] = str(test_data / "devis")


# Sofort beim Import aufrufen
setup_test_env()


# ============================================================
# Pytest-Fixtures
# ============================================================

@pytest.fixture
def sample_devis_dir(tmp_path):
    """Erstellt ein temporaeres Devis-Verzeichnis mit realistischen Test-Daten."""
    devis_dir = tmp_path / "devis" / "devis_0001"
    devis_dir.mkdir(parents=True)

    (devis_dir / "meta.json").write_text(
        '{"id": "devis_0001", "name": "Test-Devis", "datum": "2026-09-04", '
        '"netto": 9449.50, "status": "importiert", "method": "import", "kanton": "ZG"}',
        encoding="utf-8"
    )

    (devis_dir / "bepreist.sia").write_text(
        "01                                                     CHF\n"
        "11110000000000Innenanstrich Wand 2 Anstriche          0000006500m2  \n"
        "311100000000000000004250000000276250\n"
        "11120000000000Spachteln und Grundieren                0000004000m2  \n"
        "311200000000000000003000000000120000\n"
        "11130000000000Deckanstrich aussen Fassade             0000005200m2  \n"
        "311300000000000000003800000000197600\n"
        "11200000000000Gerueststellung                         0000000100Paus\n"
        "312000000000000000082000000000082000\n"
        "11300000000000Montage Fenster                         0000001200h   \n"
        "313000000000000000007800000000093600\n"
        "11400000000000Reinigung nach Ausfuehrung              0000000100Paus\n"
        "314000000000000000048000000000048000\n"
        "11500000000000Innenanstrich Wand 2 Anstriche          0000003000m2  \n"
        "315000000000000000004250000000127500\n"
        "99000007\n",
        encoding="utf-8"
    )

    return devis_dir


@pytest.fixture
def empty_sia_file(tmp_path):
    """Erstellt eine leere bepreist.sia fuer Edge-Case-Tests."""
    sia = tmp_path / "empty.sia"
    sia.write_text("")
    return sia


@pytest.fixture
def valid_api_key():
    return "test-key-dp_test_aabbccddeeff00112233445566778899"


@pytest.fixture
def invalid_api_key():
    return "INVALID-KEY-FOR-TESTING"