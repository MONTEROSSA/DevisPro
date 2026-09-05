"""Erstellt Test-Daten in TEST_DIR fuer alle Tests die ~/Library-Daten brauchen.

Damit Tests auch nach Datenverlust (oder in CI) noch funktionieren.
"""
import os
import sys
import json
import tempfile
from pathlib import Path


def ensure_test_data():
    """Stellt sicher dass Test-Daten fuer devis_0001..0008 existieren.

    Verwendet TEST_DATA_DIR (env-var) oder erstellt im temp.
    Returns: Path zum Test-Daten-Root.
    """
    test_dir = os.environ.get("TEST_DATA_DIR")
    if test_dir:
        root = Path(test_dir)
    else:
        # Default: in den User-Application-Support falls vorhanden,
        # sonst in Temp
        user_dir = Path.home() / "Library" / "Application Support" / "DevisPro" / "devis"
        if user_dir.parent.exists() and (user_dir.parent / "meine_preise.csv").exists():
            # User hat echte Daten - nutze die
            return user_dir.parent
        root = Path(tempfile.mkdtemp(prefix="devispro_test_data_"))

    if not (root / "devis").exists():
        create_sample_data(root / "devis")
    return root


def create_sample_data(devis_root: Path):
    """Erstellt 8 Beispiel-Devis im SIA-451-DevisPro-Format."""
    devis_root.mkdir(parents=True, exist_ok=True)

    for i in range(1, 9):
        dev_dir = devis_root / f"devis_{i:04d}"
        dev_dir.mkdir(exist_ok=True)
        # meta.json
        meta = {
            "id": f"devis_{i:04d}",
            "name": f"Beispiel-Devis {i}",
            "datum": "2026-09-04",
            "kunde": f"Beispiel-Kunde {chr(64 + i)} AG",
            "netto": 1000.0 + i * 100,
            "branche": ["Maler", "Sanitär", "Elektriker", "Schreiner", "Maurer", "Spengler", "Gipser", "Bodenleger"][i-1],
            "status": "bepreist",
        }
        (dev_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        # bepreist.sia
        positions = []
        for j in range(1, 4):
            pos_nr = f"11{i:02d}{j:011d}"
            text = ["Innenanstrich Wand", "Spachteln", "Deckanstrich aussen"][j-1]
            menge = 10.0 + j * 5
            einheit = ["m2", "m2", "m2"][j-1]
            ep = 25.0 + j * 5
            betrag = menge * ep
            positions.append((pos_nr, text, menge, einheit, ep, betrag))
        lines = ["01                                                     CHF"]
        for pos in positions:
            pos_nr, text, menge, einheit, ep, betrag = pos
            text_padded = text.ljust(40)[:40]
            menge_str = f"{int(menge*1000):010d}"
            einheit_padded = einheit.ljust(4)[:4]
            lines.append(f"1{pos_nr}{text_padded}{menge_str}{einheit_padded}")
            ep_str = f"{int(ep*100):010d}"
            total_str = f"{int(betrag*100):012d}"
            lines.append(f"3{pos_nr}{ep_str}{total_str}")
        lines.append("99000003")
        (dev_dir / "bepreist.sia").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    root = ensure_test_data()
    print(f"Test-Daten bereit: {root}")
    print(f"Devis: {len(list((root / 'devis').iterdir()))} Verzeichnisse")