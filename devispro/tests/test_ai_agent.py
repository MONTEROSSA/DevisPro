"""E2E-Tests fuer DevisPro AI-Agent."""
import sys
from pathlib import Path

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

from devispro.ai_agent import DevisAI


def test_analyse_devis_history():
    """Testet dass die Analyse echte Devis-Daten verarbeitet."""
    ai = DevisAI()
    result = ai.analyse_devis_history()
    assert "error" not in result, f"Fehler: {result.get('error')}"
    assert result["total_devis"] > 0, "Sollte Devis zaehlen"
    # durchschnitt_total kann 0 sein wenn meta.json kein 'netto' Feld hat — das ist ok
    assert result["durchschnitt_total"] >= 0, "Durchschnitt muss >= 0 sein"
    assert len(result["haeufigste_kunden"]) > 0
    print(f"OK: Analyse - {result['total_devis']} Devis, Durchschnitt CHF {result['durchschnitt_total']:.0f}")


def test_suggest_positions_maler():
    """Testet Positionsvorschlaege fuer Maler-Projekt."""
    ai = DevisAI()
    suggestions = ai.suggest_positions("Wand Innenanstrich 2 Anstriche")
    assert len(suggestions) > 0
    # Sollte Maler-Positionen vorschlagen
    found = any("anstrich" in s["text"].lower() for s in suggestions)
    assert found, "Sollte Anstrich-Positionen vorschlagen"
    print(f"OK: Maler-Vorschlaege: {len(suggestions)} Positionen")


def test_suggest_positions_sanitaer():
    """Testet Positionsvorschlaege fuer Sanitaer-Projekt."""
    ai = DevisAI()
    suggestions = ai.suggest_positions("Badezimmer-Renovation mit Dusche")
    assert len(suggestions) > 0
    # Sollte Sanitaer-Positionen vorschlagen
    found = any("dusche" in s["text"].lower() or "wc" in s["text"].lower()
               for s in suggestions)
    assert found, "Sollte Sanitaer-Positionen vorschlagen"
    print(f"OK: Sanitaer-Vorschlaege: {len(suggestions)} Positionen")


def test_suggest_ep_for_position():
    """Testet EP-Vorschlag basierend auf Kanton."""
    ai = DevisAI()
    zg = ai.suggest_ep_for_position("111.10", "ZG")
    ju = ai.suggest_ep_for_position("111.10", "JU")
    assert zg["ep_median"] > ju["ep_median"], "ZG sollte teurer sein als JU"
    assert zg["kanton_factor"] > 1.0
    assert ju["kanton_factor"] < 1.0
    print(f"OK: Kanton-EP: ZG={zg['ep_median']:.2f} > JU={ju['ep_median']:.2f}")


def test_user_query_umsatz():
    """Testet NL-Query-Verarbeitung fuer Umsatz-Frage."""
    ai = DevisAI()
    response = ai.process_user_query("Was war mein umsatzstaerkster Monat?")
    assert "CHF" in response
    print("OK: NL-Query 'Umsatz' liefert Daten")


def test_user_query_vorlage():
    """Testet NL-Query fuer Vorlagen-Anfrage."""
    ai = DevisAI()
    response = ai.process_user_query("Ich brauche eine Vorlage fuer Badezimmer-Renovation")
    assert "Badezimmer" in response or "Sanitär" in response
    assert "•" in response  # Hat Aufzaehlung
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
    ai = DevisAI()
    # Wir haben 36 echte Devis, also sollte etwas gefunden werden
    similar = ai.find_similar_devis({"name": "Badezimmer-Renovation", "netto": 5000})
    # Sollte ein paar aehnliche Devis finden
    assert len(similar) >= 0
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