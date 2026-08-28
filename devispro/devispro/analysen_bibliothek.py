"""Analysen-Bibliothek — 'Lernende Kalkulation Light' für DevisPro.
Sorba-Feature zum Fixpreis, offen, erweiterbar. Kein Verbandszwang.
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / "Library" / "Application Support" / "DevisPro" / "data"
ANALYSEN_FILE = DATA_DIR / "analysen.json"

# Vordefinierte Templates (Sorba-Style)
TEMPLATES = {
    "Standard Bau": {
        "zuschlaege": {
            "lohn": 15.0,
            "material": 10.0,
            "geraet": 8.0,
            "agk": 12.0,
            "gav": 3.5,
            "wagnis": 3.0,
            "gewinn": 8.0,
        },
        "beschreibung": "Standard-Zuschläge für Neubau/Umbau (CH-Durchschnitt)",
    },
    "Sanierung": {
        "zuschlaege": {
            "lohn": 20.0,  # mehr Aufwand, Unwägbarkeiten
            "material": 12.0,
            "geraet": 10.0,
            "agk": 14.0,
            "gav": 3.5,
            "wagnis": 5.0,  # höheres Risiko
            "gewinn": 10.0,
        },
        "beschreibung": "Erhöhte Zuschläge für Sanierung/Bestand (Risiko, Zusatzaufwand)",
    },
    "Neubau": {
        "zuschlaege": {
            "lohn": 12.0,
            "material": 8.0,
            "geraet": 6.0,
            "agk": 10.0,
            "gav": 3.5,
            "wagnis": 2.0,
            "gewinn": 7.0,
        },
        "beschreibung": "Optimierte Zuschläge für serielle Neubauten (Effizienz)",
    },
    "Gesamtkostengarantie": {
        "zuschlaege": {
            "lohn": 18.0,
            "material": 15.0,
            "geraet": 12.0,
            "agk": 16.0,
            "gav": 3.5,
            "wagnis": 8.0,  # sehr hohes Risiko
            "gewinn": 12.0,
        },
        "beschreibung": "Maximale Sicherheit für GU-Pauschalen (Risikopuffer)",
    },
}


@dataclass
class Analyse:
    name: str
    version: int
    zuschlaege: Dict[str, float]  # lohn, material, geraet, agk, gav, wagnis, gewinn
    beschreibung: str = ""
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    autor: str = "user"
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Standard-Zuschläge prüfen/ergänzen
        defaults = {"lohn": 0, "material": 0, "geraet": 0, "agk": 0, "gav": 0, "wagnis": 0, "gewinn": 0}
        for k, v in defaults.items():
            if k not in self.zuschlaege:
                self.zuschlaege[k] = v

    def total_zuschlag(self) -> float:
        """Summe aller Zuschläge in %."""
        return sum(self.zuschlaege.values())

    def apply_to_position(self, ek_preis: float) -> float:
        """Wendet alle Zuschläge auf EK-Preis an → VK-Preis."""
        faktor = 1.0
        for key in ["material", "geraet", "agk", "gav", "wagnis", "gewinn"]:
            faktor += self.zuschlaege.get(key, 0) / 100.0
        # Lohn wird oft separat addiert, hier vereinfacht als % auf EK
        faktor += self.zuschlaege.get("lohn", 0) / 100.0
        return round(ek_preis * faktor, 2)

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Analyse":
        return cls(**data)


class AnalysenBibliothek:
    """Verwaltet die Sammlung von Kalkulations-Analysen."""

    def __init__(self, pfad: Optional[Path] = None):
        self.pfad = pfad or ANALYSEN_FILE
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Optional[List[Analyse]] = None

    def _laden(self) -> List[Analyse]:
        if self._cache is not None:
            return self._cache
        if self.pfad.exists():
            try:
                with open(self.pfad, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cache = [Analyse.from_json(a) for a in data]
                return self._cache
            except Exception as e:
                logger.error(f"Fehler beim Laden der Analysen: {e}")
        self._cache = []
        return self._cache

    def _speichern(self, analysen: List[Analyse]):
        self._cache = analysen
        data = [a.to_json() for a in analysen]
        tmp = self.pfad.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.pfad)

    def laden(self) -> List[Analyse]:
        return self._laden()

    def speichern(self, analyse: Analyse) -> Analyse:
        """Speichert oder aktualisiert eine Analyse (upsert by name)."""
        analysen = self._laden()
        for i, a in enumerate(analysen):
            if a.name.lower() == analyse.name.lower():
                analyse.version = a.version + 1
                analyse.created = a.created
                analyse.modified = datetime.now().isoformat()
                analysen[i] = analyse
                self._speichern(analysen)
                return analyse
        # Neu
        analyse.version = 1
        analysen.append(analyse)
        self._speichern(analysen)
        return analyse

    def laden_name(self, name: str) -> Optional[Analyse]:
        for a in self._laden():
            if a.name.lower() == name.lower():
                return a
        return None

    def loeschen(self, name: str) -> bool:
        analysen = self._laden()
        for i, a in enumerate(analysen):
            if a.name.lower() == name.lower():
                del analysen[i]
                self._speichern(analysen)
                return True
        return False

    def liste(self) -> List[Dict[str, Any]]:
        return [
            {"name": a.name, "version": a.version, "total_zuschlag": a.total_zuschlag(),
             "modified": a.modified, "beschreibung": a.beschreibung}
            for a in self._laden()
        ]

    def export_json(self, name: str) -> Optional[str]:
        """Exportiert eine Analyse als JSON-String (für Team-Share)."""
        a = self.laden_name(name)
        if a:
            return json.dumps(a.to_json(), ensure_ascii=False, indent=1)
        return None

    def import_json(self, json_str: str) -> Analyse:
        """Importiert Analyse aus JSON-String."""
        data = json.loads(json_str)
        a = Analyse.from_json(data)
        return self.speichern(a)

    def templates_laden(self) -> Dict[str, Analyse]:
        """Gibt alle Templates als Analyse-Objekte zurück."""
        result = {}
        for name, tpl in TEMPLATES.items():
            result[name] = Analyse(
                name=name,
                version=1,
                zuschlaege=tpl["zuschlaege"],
                beschreibung=tpl["beschreibung"],
                autor="system",
                tags=["template"],
            )
        return result

    def template_als_basis(self, template_name: str, neuer_name: str) -> Optional[Analyse]:
        """Erstellt neue Analyse basierend auf Template."""
        tpl = TEMPLATES.get(template_name)
        if not tpl:
            return None
        return self.speichern(Analyse(
            name=neuer_name,
            version=1,
            zuschlaege=tpl["zuschlaege"].copy(),
            beschreibung=f"Basiert auf Template '{template_name}'",
            tags=["custom"],
        ))


# Globale Instanz
_bibliothek: Optional[AnalysenBibliothek] = None

def get_bibliothek() -> AnalysenBibliothek:
    global _bibliothek
    if _bibliothek is None:
        _bibliothek = AnalysenBibliothek()
    return _bibliothek


# Convenience Functions
def analysen_liste() -> List[Dict[str, Any]]:
    return get_bibliothek().liste()

def analyse_speichern(name: str, zuschlaege: Dict[str, float], beschreibung: str = "") -> Analyse:
    a = Analyse(name=name, version=1, zuschlaege=zuschlaege, beschreibung=beschreibung)
    return get_bibliothek().speichern(a)

def analyse_laden(name: str) -> Optional[Analyse]:
    return get_bibliothek().laden_name(name)

def analyse_loeschen(name: str) -> bool:
    return get_bibliothek().loeschen(name)

def analyse_export(name: str) -> Optional[str]:
    return get_bibliothek().export_json(name)

def analyse_import(json_str: str) -> Analyse:
    return get_bibliothek().import_json(json_str)

def templates() -> Dict[str, Analyse]:
    return get_bibliothek().templates_laden()

def aus_template(template_name: str, neuer_name: str) -> Optional[Analyse]:
    return get_bibliothek().template_als_basis(template_name, neuer_name)


# Test
if __name__ == "__main__":
    bib = AnalysenBibliothek(Path("/tmp/test_analysen.json"))
    
    # Template prüfen
    for name, a in bib.templates_laden().items():
        print(f"Template: {name} → Total Zuschlag: {a.total_zuschlag()}%")
    
    # Eigene speichern
    a = bib.speichern(Analyse("Meine Sanierung v1", 1, {
        "lohn": 22.0, "material": 14.0, "geraet": 11.0,
        "agk": 15.0, "gav": 3.5, "wagnis": 6.0, "gewinn": 11.0
    }, "Meine angepasste Sanierungs-Analyse"))
    print(f"Gespeichert: {a.name} v{a.version}")
    
    # Export
    print(bib.export_json("Meine Sanierung v1"))