"""Installierte Versionsnummer von DevisPro (SemVer).

Der Anbieter erhoeht VERSION bei jeder Veroeffentlichung ueber
`python3 bump_version.py`. Die zentrale Vergleichsdatei (version.json)
wird auf devispro.de hochgeladen; die lokale App prueft beim Oeffnen
darauf und informiert KMU-Kunden ueber verfuegbare Updates.
"""
VERSION = "1.3.1"
RELEASED = "2026-08-13"
CHANNEL = "stable"

# Changelog der installierten Version (nur Info, das live-Banner nutzt
# die Notes aus der zentralen version.json).
CHANGELOG = {
    "de": [
        "System-Diagnose (Selbsttest): prueft Module, Lizenz, Datenverzeichnis, Richtpreise, Stammdaten – offline, via CLI 'python -m devispro diagnose' und Web-Route /diagnose",
        "KI-Agent (lokal, offline) – beantwortet Fragen und fuehrt Aktionen aus: MWST/Kanton aendern, Export in Buchhaltung, Waehrung umrechnen, Marketing-Texte, Devis oeffnen",
        "Ersteinrichtung (Setup-Wizard): Betrieb, Gewerk, Kanton, MWST und Richtpreise in 2 Minuten",
        "Plattformuebergreifend: macOS (.command), Windows (.bat + install_windows.bat), Linux (python -m devispro)",
        "Backup & Wiederherstellung der KMU-Daten (integritaetsgesichert)",
        "Ordner-Import ganzer Projektordner -> Devis (SIA-451/Sorba, Bauweb, CSV/Excel, GAEB, ONORM, XRechnung; OCR-faehig)",
        "13 Buchhaltungs-Exporte + HMAC-ERP-API (Abacus, Proffix, BMD, DATEV, Banana, SAP, Lexoffice, SevDesk, WinOffice, RamCO, Mobit, Kleinvieh, CSV/Excel/XML)",
        "Mehrwaehrung CHF->EUR/USD/GBP, Margen-Copilot, Subunternehmer-Marge, Marketing-Assistent, WhatsApp-Bot",
        "Rechnungsmodul mit Zahlungsplan (30/40/30) und Swiss-QR; Mahnwesen (3 Stufen)",
        "Echtes PDF ohne Zusatzprogramm; Dokumente pro Devis dauerhaft gespeichert",
    ],
    "fr": [
        "Diagnostic systeme (autotest): modules, licence, dossier donnees, prix, profil – hors ligne, CLI et Web /diagnose",
        "Assistant IA (local, hors ligne) – questions et actions: TVA/canton, export compta, devise, marketing, ouvrir devis",
        "Assistant de premiere installation (Setup-Wizard) en 2 minutes",
        "Multiplateforme: macOS, Windows, Linux",
        "Sauvegarde et restauration des donnees KMU",
        "Import dossier complet -> devis; 13 exports comptables + API ERP HMAC",
        "Devises, co-pilote de marge, marge sous-traitant, assistant marketing, WhatsApp",
        "Facturation avec plan de paiement et QR suisse; rappels (3 niveaux)",
        "Vrai PDF sans logiciel externe",
    ],
    "it": [
        "Diagnostica di sistema (autotest): moduli, licenza, cartella dati, prezzi, profilo – offline, CLI e Web /diagnose",
        "Assistente IA (locale, offline) – domande e azioni: IVA/canton, export contabilita, valuta, marketing, apri devis",
        "Assistente di prima installazione (Setup-Wizard) in 2 minuti",
        "Multipiattaforma: macOS, Windows, Linux",
        "Backup e ripristino dati KMU",
        "Import cartella completa -> devis; 13 export contabili + API ERP HMAC",
        "Valute, co-pilota margine, margine subappalto, assistente marketing, WhatsApp",
        "Fatturazione con piano di pagamento e QR svizzero; solleciti (3 livelli)",
        "PDF reale senza software esterno",
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
