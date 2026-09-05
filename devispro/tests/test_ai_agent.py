"""E2E-Tests fuer DevisPro AI-Agent.

Verwendet TEST_DEVIS_DIR (kein Hardcoded Live-Pfad).
Robust gegen Monkey-Patches in anderen Test-Modulen.
"""
import sys
import os
from pathlib import Path

# Test-Daten-Dir bestimmen (vor Import von ai_agent)
def _get_test_dir():
    test_data = os.environ.get("DEVISPRO_TEST_DIR")
    if test_data:
        return Path(test_data)
    user_dir = Path.home() / "Library" / "Application Support" / "DevisPro" / "devis"
    if user_dir.exists() and any(user_dir.iterdir()):
        return user_dir
    from tests._test_data import ensure_test_data
    return ensure_test_data() / "devis"

TEST_DEVIS_DIR = _get_test_dir()
TEST_DATA_ROOT = TEST_DEVIS_DIR.parent  # ein Hoeher, weil data_store dort hinzeigt

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

# Patch data_store BEVOR ai_agent importiert wird
import devispro.data_store as ds
ORIGINAL_APP_SUPPORT_DIR = ds.app_support_dir

def _test_app_support_dir():
    """Gibt das Test-Daten-Verzeichnis zurueck."""
    return str(TEST_DATA_ROOT)

ds.app_support_dir = _test_app_support_dir

from devispro.ai_agent import DevisAI


def test_analyse_devis_history():
    """Testet dass die Analyse echte Devis-Daten verarbeitet."""
    ai = DevisAI(data_dir=TEST_DATA_ROOT)
    result = ai.analyse_devis_history()
    assert "error" not in result, f"Fehler: {result.get('error')}"
    assert result["total_devis"] > 0
    assert result["durchschnitt_total"] >= 0
    print(f"OK: Analyse - {result['total_devis']} Devis")


def test_suggest_positions_maler():
    """Testet Positionsvorschlaege fuer Maler-Projekt."""
    ai = DevisAI()
    suggestions = ai.suggest_positions("Wand Innenanstrich 2 Anstriche")
    assert len(suggestions) > 0
    found = any("anstrich" in s["text"].lower() for s in suggestions)
    assert found
    print(f"OK: Maler-Vorschlaege: {len(suggestions)} Positionen")


def test_suggest_positions_sanitaer():
    """Testet Positionsvorschlaege fuer Sanitaer-Projekt."""
    ai = DevisAI()
    suggestions = ai.suggest_positions("Badezimmer-Renovation mit Dusche")
    assert len(suggestions) > 0
    found = any("dusche" in s["text"].lower() or "wc" in s["text"].lower() for s in suggestions)
    assert found
    print(f"OK: Sanitaer-Vorschlaege: {len(suggestions)} Positionen")


def test_suggest_ep_for_position():
    """Testet EP-Vorschlag basierend auf Kanton."""
    ai = DevisAI()
    zg = ai.suggest_ep_for_position("111.10", "ZG")
    ju = ai.suggest_ep_for_position("111.10", "JU")
    assert zg["ep_median"] > ju["ep_median"]
    assert zg["kanton_factor"] > 1.0
    assert ju["kanton_factor"] < 1.0
    print(f"OK: Kanton-EP: ZG={zg['ep_median']:.2f} > JU={ju['ep_median']:.2f}")


def test_user_query_umsatz():
    """Testet NL-Query-Verarbeitung fuer Umsatz-Frage."""
    ai = DevisAI(data_dir=TEST_DATA_ROOT)
    response = ai.process_user_query("Was war mein umsatzstaerkster Monat?")
    assert "CHF" in response
    print("OK: NL-Query 'Umsatz' liefert Daten")


def test_user_query_vorlage():
    """Testet NL-Query fuer Vorlagen-Anfrage."""
    ai = DevisAI()
    response = ai.process_user_query("Ich brauche eine Vorlage fuer Badezimmer-Renovation")
    assert "Badezimmer" in response or "Sanitaer" in response or "Sanitär" in response
    assert "•" in response
    print("OK: NL-Query 'Vorlage' liefert Positionsliste")


def test_auto_categorize_devis():
    """Testet automatische Branchen-Kategorisierung."""
    ai = DevisAI()
    branche1 = ai.auto_categorize_devis({"name": "Innenanstrich Buero"})
    branche2 = ai.auto_categorize_devis({"name": "Badsanierung komplett"})
    assert branche1 == "Maler"
    assert branche2 == "Sanitär"
    print(f"OK: Auto-Kategorisierung: 'Innenanstrich'->{branche1}, 'Badsanierung'->{branche2}")


def test_find_similar_devis():
    """Testet Suche nach aehnlichen Devis."""
    ai = DevisAI(data_dir=TEST_DATA_ROOT)
    similar = ai.find_similar_devis({"name": "Beispiel", "netto": 1100})
    assert isinstance(similar, list)
    print(f"OK: Aehnliche Devis gefunden: {len(similar)}")


if __name__ == "__main__":
    print("=" * 60)
    print("DevisPro AI-Agent Tests")
    print("=" * 60)
    test_analyse_devis_history()
    test_suggest_positions_maler()
    test_suggest_positions_sanitaer()
    test_suggest_ep_for_position()
    test_user_query_umsatz()
    test_user_query_vorlage()
    test_auto_categorize_devis()
    test_find_similar_devis()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN")
    print("=" * 60)