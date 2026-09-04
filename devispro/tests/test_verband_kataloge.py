"""E2E-Tests fuer Verbandskataloge (NPK, BKS, HLKS, CRB)."""
import sys

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

from devispro.verband_kataloge_daten import (
    NPK_KATALOG, BKS_KATALOG, HLKS_KATALOG, CRB_KATALOG,
    ALL_KATALOGE, get_position, search_positions, get_kanton_ep,
    get_katalog_stats, KANTON_FAKTOR,
)


def test_npk_katalog_complete():
    """NPK-Katalog enthaelt die wichtigsten Positionen."""
    expected = ["111.10", "111.20", "112.10", "120.10", "310.10", "311.10"]
    for pos_nr in expected:
        assert pos_nr in NPK_KATALOG, f"{pos_nr} fehlt im NPK"
    assert len(NPK_KATALOG) >= 50, f"NPK zu klein: {len(NPK_KATALOG)}"
    print(f"OK: NPK-Katalog: {len(NPK_KATALOG)} Positionen")


def test_bks_katalog_complete():
    """BKS-Katalog enthaelt Baukosten-Standard."""
    assert len(BKS_KATALOG) >= 10
    assert "BKS-200" in BKS_KATALOG
    print(f"OK: BKS-Katalog: {len(BKS_KATALOG)} Positionen")


def test_hlks_katalog_complete():
    """HLKS-Katalog enthaelt Heizung/Lueftung/Klima/Sanitaer."""
    assert len(HLKS_KATALOG) >= 8
    assert "H-100" in HLKS_KATALOG  # Waermepumpe
    assert "L-100" in HLKS_KATALOG  # Lueftung
    print(f"OK: HLKS-Katalog: {len(HLKS_KATALOG)} Positionen")


def test_crb_katalog_complete():
    """CRB-Katalog enthaelt Baukostenschluessel."""
    assert len(CRB_KATALOG) >= 5
    for k in ["CRB-1", "CRB-2", "CRB-5"]:
        assert k in CRB_KATALOG
    print(f"OK: CRB-Katalog: {len(CRB_KATALOG)} Positionen")


def test_get_position():
    """Position ueber alle Kataloge suchen."""
    pos = get_position("111.10")
    assert pos is not None
    assert pos.text == "Innenanstrich Wand, 2 Anstriche"
    assert pos.einheit == "m2"
    assert pos.ep_median > 0
    print(f"OK: get_position('111.10') -> {pos.text}")


def test_search_positions():
    """Text-Suche ueber alle Kataloge."""
    # Suche nach einem Wort das definitiv in den Katalogen vorkommt
    results = search_positions("Sanitär")
    assert len(results) > 0, f"Keine Treffer fuer 'Sanitaer': {results}"
    # Sollte Sanitaer-Positionen finden
    assert any(p.branche == "Sanitär" for p in results)
    print(f"OK: Suche 'Sanitaer': {len(results)} Treffer")


def test_kanton_faktoren():
    """Kantons-Faktoren sind korrekt."""
    # ZG ist teuer
    assert KANTON_FAKTOR["ZG"] > 1.15
    # JU ist guenstig
    assert KANTON_FAKTOR["JU"] < 0.95
    # GE ist teuer
    assert KANTON_FAKTOR["GE"] > 1.20
    print("OK: Kanton-Faktoren ZG/JU/GE korrekt")


def test_kanton_ep_berechnung():
    """Kantonspezifischer EP wird korrekt berechnet."""
    base = get_kanton_ep("111.10", "CH")
    zg = get_kanton_ep("111.10", "ZG")
    ju = get_kanton_ep("111.10", "JU")
    # ZG sollte hoeher als CH sein
    assert base is not None and zg is not None and ju is not None, "Position 111.10 fehlt"
    assert zg > base
    # JU sollte tiefer als CH sein
    assert ju < base
    # Faktor muss passen
    assert abs(zg - base * KANTON_FAKTOR["ZG"]) < 0.01
    print(f"OK: Kanton-EP: CH={base:.2f}, ZG={zg:.2f}, JU={ju:.2f}")


def test_zeit_aufwand_gesetzt():
    """Jede Position hat einen Zeit-Aufwand."""
    for katalog_name, katalog in ALL_KATALOGE.items():
        for pos_nr, pos in katalog.items():
            assert pos.zeit_aufwand_h >= 0, f"{katalog_name}/{pos_nr}: kein Zeitaufwand"
    print("OK: Alle Positionen haben Zeitaufwand")


def test_katalog_stats():
    """Statistiken ueber Kataloge."""
    stats = get_katalog_stats()
    assert "NPK" in stats
    assert "BKS" in stats
    assert "HLKS" in stats
    assert "CRB" in stats
    assert stats["NPK"]["positionen"] > 50
    print(f"OK: Stats - NPK={stats['NPK']['positionen']}, BKS={stats['BKS']['positionen']}, "
          f"HLKS={stats['HLKS']['positionen']}, CRB={stats['CRB']['positionen']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Verbandskataloge Tests")
    print("=" * 60)
    test_npk_katalog_complete()
    test_bks_katalog_complete()
    test_hlks_katalog_complete()
    test_crb_katalog_complete()
    test_get_position()
    test_search_positions()
    test_kanton_faktoren()
    test_kanton_ep_berechnung()
    test_zeit_aufwand_gesetzt()
    test_katalog_stats()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN")
    print("=" * 60)