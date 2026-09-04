# DevisPro

**DevisPro v1.4.8** — SIA-451 Devis-Software für Schweizer Bau-KMU.

DevisPro importiert Architekten-Devis (SIA-451, Sorba, GAEB), füllt sie automatisch
mit Ihren Preisen und ergänzt fehlende Positionen mit geprüften CH-Marktrichtpreisen.
Lokal, offline-fähig, ohne Cloud-Zwang.

## Download

- **macOS (ad-hoc signiert, CI-Build):** Siehe [GitHub Actions Artifact](../../actions)
  oder https://devispro.de/DevisPro-2026-09-04-ci-adhoc.zip
- **macOS (Developer-ID + Apple-notarisiert, lokal signiert):**
  https://devispro.de/DevisPro-2026-09-03-adhoc.zip
- **Windows:** v1.3.1 verfügbar, v1.4.x folgt

Beim ersten Öffnen der macOS-Version: Rechtsklick → "Öffnen" → "Bestätigen"
(oder im Terminal: `xattr -d com.apple.quarantine ~/Downloads/DevisPro_Mac.app`).

## Features

- **SIA-451 / Sorba / GAEB-Import** — Positionen automatisch erkannt
- **Automatisches Befüllen** mit Ihren Ansätzen, Rabatten, Konditionen
- **CH-Marktrichtpreise** — 7 Gewerke abgedeckt
- **13 Buchhaltungs-Exporte** — Abacus, Proffix, BMD, DATEV, Banana, SAP u.a.
- **Margen-Copilot** — Variantenvergleich vor Versand
- **Mahnwesen & Rechnungen** — Swiss-QR (SIX), MwSt 8.1%, WhatsApp-Versand
- **4 Profit-Module** (NEU in v1.4.x):
  - **Verbandskataloge** NPK / BKS / HLKS / CRB — Import + Suche
  - **Marktplatz** für Subunternehmer-Suche
  - **Cloud-Sync** (optional, Ende-zu-Ende-verschlüsselt)
  - **ERP-Ecosystem** — 10 Direktanbindungen
- **Partner-API** — FastAPI-basiert für ERP-Integration (Abacus, Proffix, SAP)

## Entwicklung

### Voraussetzungen
- macOS (für lokales Signieren)
- Python 3.11
- Git

### Lokales Build
```bash
# 1. Source klonen
git clone https://github.com/MONTEROSSA/DevisPro.git
cd DevisPro

# 2. Dependencies installieren
pip install -r requirements.txt
cd devispro
pip install -e .

# 3. App starten
python -m devispro.app_gui
```

### Lokales Signieren + Notarisieren (Plan A)
```bash
~/DevisPro_sign_fix.command
```
Erzeugt eine Developer-ID-signierte und Apple-notarisierte Version in `_signFIX/`,
ZIP-File in `DevisPro_Mac_notarized.zip`, und deployed auf `devispro.de`.

### CI-Build (Plan B)
Push eines `v*`-Tags triggert GitHub Actions `.github/workflows/build-deploy-mac.yml`:
- Build + Ad-Hoc-Codesign (~45s)
- GitHub-Release erstellen
- Deploy auf VPS als `DevisPro-YYYY-MM-DD-ci-adhoc.zip`

Apple Developer-ID-Sign und Notarization läuft **lokal** via `sign_fix.command` —
nicht im CI (Apple Trust-Eval-Issue auf M4-Mac seit Sep 2026).

## Architektur

- **Core:** `devispro/app_gui.py` (CustomTkinter, dunkles Design)
- **Parser:** `devispro/parsers/` (SIA-451, CRB, Bauweb, GAEB, ÖNorm, XRechnung)
- **Daten:** `devispro/data_store.py` (lokal in `~/Library/Application Support/DevisPro/`)
- **Partner-API:** `devispro/partner_api.py` (FastAPI + uvicorn)
- **Moats:**
  - `devispro/verbaende_kataloge.py` (NPK/BKS/HLKS/CRB)
  - `devispro/marketplace.py` (Subunternehmer-Marktplatz)
  - `devispro/cloud_sync.py` (optional Cloud-Sync)
  - `devispro/erp_ecosystem.py` (10 ERP-Direktanbindungen)

## Lizenz

Proprietär. © 2026 Monterossa. Alle Rechte vorbehalten.

## Kontakt

- E-Mail: info@devispro.de
- Telefon: +41 41 534 48 90
- Web: https://devispro.de
- Support: Deutsch, Französisch, Italienisch