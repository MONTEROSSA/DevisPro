"""Installierte Versionsnummer von DevisPro (SemVer).

Der Anbieter erhoeht VERSION bei jeder Veroeffentlichung ueber
`python3 bump_version.py`. Die zentrale Vergleichsdatei (version.json)
wird auf devispro.ch hochgeladen; die lokale App prueft beim Oeffnen
darauf und informiert KMU-Kunden ueber verfuegbare Updates.
"""
VERSION = "1.1.0"
RELEASED = "2026-08-10"
CHANNEL = "stable"

# Changelog der installierten Version (nur Info, das live-Banner nutzt
# die Notes aus der zentralen version.json).
CHANGELOG = {
    "de": [
        "Rechnungsmodul mit Zahlungsplan (30/40/30 bei Bauleistung)",
        "Echtes PDF ohne Zusatzprogramm (Werkvertrag, Abnahme, Devis, Rechnung)",
        "Dokumente werden pro Devis dauerhaft gespeichert",
    ],
    "fr": [
        "Module de facturation avec plan de paiement",
        "Vrai PDF sans logiciel externe",
        "Documents sauvegardes par devis",
    ],
    "it": [
        "Modulo fattura con piano di pagamento",
        "PDF reale senza software esterno",
        "Documenti salvati per devis",
    ],
}


def parse(v: str):
    """Zerlegt '1.2.3' -> (1,2,3); toleriert Praefixe wie 'v1.2.3'."""
    s = str(v).strip().lstrip("vV")
    parts = []
    for p in s.split("."):
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def newer(remote: str, local: str = VERSION) -> bool:
    try:
        return parse(remote) > parse(local)
    except Exception:
        return False
