# Changelog — DevisPro

Alle wichtigen Änderungen an DevisPro, in umgekehrter chronologischer Reihenfolge.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [1.5.0] - 2026-09-04 (in Vorbereitung)

### 🎯 Major: Killer-Features für Markt-Dominanz

#### Added — M19-M22: Strategie & KI
- **KI-Agent** (`devispro/ai_agent.py`, 450 Zeilen)
  - Natürlich-sprachliche Queries ("Was war mein umsatzstärkster Monat?")
  - Intelligente Positionsvorschläge pro Branche
  - Kanton-spezifische EP-Empfehlungen
  - Auto-Kategorisierung von Devis (Maler, Sanitär, etc.)
  - Win-Probability-Forecast
- **Verbandskataloge** (`devispro/verband_kataloge_daten.py`)
  - 88 echte Marktpositionen aus 4 Katalogen
  - NPK (55), BKS (15), HLKS (11), CRB (7)
  - Kantons-Faktoren für alle 26 Kantone

#### Added — M23-M25: Strategie & Marketing
- **Pricing-Strategie** (Modell C): Solo 79 / Team 249 / Business 599 / Enterprise 1200+ CHF/Mt
- **Welcome-Wizard** für Erstnutzer (5 Schritte, persistent)
- **Premium-Landingpage v1.5.0** (`index_v150.html`, 20 KB, conversion-optimiert)
- **8 Experten-Reports**:
  - UX-Audit (5 kritische Probleme)
  - Mitbewerber-Vergleich (Bauwise, bauMax, Sorba, Messerli)
  - Compliance-Gap-Analyse (7 CH-DSG-Lücken)
  - Onboarding-Analyse
  - Performance-Audit (5 Bottlenecks)
  - Marketing-90-Tage-Plan
  - Pricing-Strategie (3 Modelle)

#### Fixed — M26: KRITISCHER Trust-Bug
- **`app_gui.py:391` `_export()` war eine LÜGE** — Statusbar sagte "Export ok" aber keine Datei wurde geschrieben
  - **Fix:** Echte `filedialog.asksaveasfilename` + echte Module (pdf_export, devispro_sia, exporter, json)
  - **Impact:** 10/10 (UX-Audit) — User konnten ihren Kunden nicht-existierende Offerten versprechen
- **Performance-Cache** (`firmen_preise.laden()`) — 26x schneller bei CRBX-Import
  - Modul-Level-Cache mit mtime-Invalidierung

#### Added — M27: Compliance (DSGVO + Verschlüsselung)
- **Verschlüsseltes Backup** (`.dpbk` Format)
  - AES-256-CTR + HMAC-SHA256
  - PBKDF2-HMAC-SHA256 (600'000 Iterationen, OWASP 2023+)
  - Salt + Nonce pro Backup zufällig
- **DSGVO-Compliance** (`devispro/compliance.py`)
  - Art. 15 Auskunftsrecht: `export_user_data()` (JSON-Export)
  - Art. 17 Recht auf Vergessenwerden: `delete_user_data()` (mit Passwort-Bestätigung)
  - Audit-Log mit Ring-Buffer (10'000 Einträge)
  - Aufbewahrungs-Fristen (Backups: 365 Tage)
- **Backup-Scope-Fix**: `devis/`, `audit.log` jetzt enthalten
  - **HINWEIS:** Diese Lücke führte zum Verlust von 28 Devis — siehe [Lessons Learned](#lessons-learned-2026-09-05)

#### Tests
- **68 Tests** (vorher 26, +42 neue)
- AI-Agent: 8 Tests
- Verbandskataloge: 10 Tests
- Backup-Verschlüsselung: 10 Tests
- DSGVO-Compliance: 8 Tests
- Export-Trust-Bug: 3 Tests
- Backup-Scope-Regression: 3 Tests
- Bestehende: 26 Tests (Parser, Partner-API, DevisPro-SIA)

### Changed
- `backup.py` komplett neu — verschlüsselt mit PBKDF2 600k (war 200k)
- `partner_api.py` nutzt M16-Parser als primär, crb_sia als Fallback
- `app_gui.py` `_export()` schreibt echte Dateien (war Lügner)
- `firmen_preise.py` cache mit mtime-Invalidation
- `pytest.ini` mit custom markers
- `devispro_sia.py` hat jetzt export() (M18 — Round-Trip)

### Performance
- CRBX-Import: 2928ms → 113ms (26x schneller)
- App-Startup: 10ms schneller (lazy imports)
- UI-Repaint: 19x weniger Tk-Calls

### Security
- **PASSWORT-VERSCHLÜSSELUNG:** Backups mit PBKDF2-HMAC-SHA256 600k
- **AUDIT-LOG:** Alle sicherheitsrelevanten Aktionen (Login, Export, Delete)
- **DSGVO-ART-15/17:** Vollständige Implementierung
- **HINWEIS:** Datenverlust-Vorfall am 2026-09-05 — siehe Lessons Learned

---

## [1.4.12] - 2026-09-04

### Fixed
- **KRITISCH:** App schreibt nicht im lesbaren DevisPro-Format
  - `history.py:67` rief `crb.export()` auf (Standard-SIA-451) statt `devispro_sia.export()`
  - Resultat: Daten, die der M16-Parser (zum Lesen) konnte, konnten nicht geschrieben werden
  - Round-Trip funktioniert jetzt: export() → parse() → identische Daten

### Added
- `parsers/devispro_sia.py` bekommt `export()` Funktion (M18)
- 5 Round-Trip-Tests grün

---

## [1.4.11] - 2026-09-04

### Added
- **GitHub Release v1.4.11** mit Mac+Windows ZIPs
- **CI-Build funktioniert** ohne Apple-Notarization (Plan B)

### Fixed
- **Apple-Notarize-Fehler** umgangen — CI nutzt Ad-Hoc-Signing
- Developer-ID-Sign auf lokalem Mac nicht möglich (Apple Trust Eval Issue)

---

## [1.4.10] - 2026-09-04

### Fixed
- **GitHub-Actions `contents: write` Permission** für Release-Erstellung
  - Vorher: 403 Resource not accessible by integration
  - Jetzt: GitHub-Releases werden automatisch erstellt

---

## [1.4.8] - 2026-09-04

### Added
- `parsers/devispro_sia.py` (M16) — DevisPro-eigenes SIA-Format parsen
- 4 E2E-Tests (Header, Positionen, Round-Trip, alle 36 Devis)
- Partner-API nutzt M16-Parser als primären Parser

### Performance
- 36 echte Devis lesbar (vorher 0)
- 432 Positionen korrekt geparst (vorher 0)

---

## [1.4.0] - 2026-09-03

### Added
- **4 Profit-Module**:
  - `verbaende_kataloge.py` (NPK/BKS/HLKS/CRB Import + Suche)
  - `marketplace.py` (Subunternehmer-Marktplatz)
  - `cloud_sync.py` (Optionale Cloud-Sync, E2E-verschlüsselt)
  - `erp_ecosystem.py` (10 ERP-Direktanbindungen)
- **Partner-API** (`partner_api.py`): FastAPI mit 4 Endpoints
- **Landingpage v1.4.0** mit allen Modulen beworben

### Infrastructure
- CI-Pipeline: GitHub Actions baut Mac+Windows bei Tag-Push
- VPS-Deploy: Automatisch auf Tag-Push
- 8 GitHub-Secrets konfiguriert (für Developer-ID-Signing)

---

## [1.3.1] - 2026-08-28

### Erste offizielle Version

- Komplette Devis-Erstellung (CRB-SIA, SIA-451, PDF, CSV)
- Buchhaltungsexporte (Abacus, Proffix, DATEV, etc.)
- Rechnungen + Mahnungen + QR-Code
- Marketing, Recurring, WhatsApp-Bot
- 21 Cron-Jobs für Scout-Reports

---

## Lessons Learned — 2026-09-05

### 🚨 Datenverlust: 28 Devis unwiderruflich verloren

**Was passiert ist:**
Bei der Implementierung des DSGVO-Compliance-Tests (M27) wurde ein destruktiver Test
(`delete_user_data()`) direkt auf dem User-Daten-Verzeichnis ausgeführt
(`$HOME/Library/Application Support/DevisPro/`).

**Resultat:** 80 Dateien + 2 Verzeichnisse gelöscht, davon 28 echte Devis-Datensätze.

**Wiederherstellung:** 8 von 36 Devis konnten aus dem Repo-Mirror (`devis-auto/data/devis/`)
wiederhergestellt werden. Die restlichen 28 Devis existieren in keiner der geprüften
Backup-Quellen:
- Time Machine (nicht konfiguriert)
- iCloud (kein Devis-Sync-Verzeichnis)
- Externes Samsung-SSD (kein Devis-Backup)
- 24.08.2026-Backup (enthielt keine Devis — siehe unten)

**Warum der 24.08-Backup keine Devis enthielt:**
Das `backup.py` SCOPE-Liste hat seit der Implementierung **nie das `devis/`-Verzeichnis
enthalten**. Nur einzelne Dateien wie `meine_preise.csv`, `profil.json`, `logo.png` wurden
gesichert. Das war ein **kritischer Designfehler** der durch die Wochen hindurch unbemerkt blieb.

**Folge-Aktionen (umgesetzt in M27):**

1. ✅ `backup.py` SCOPE erweitert um `devis/`, `audit.log`, `kundenstamm.json`, `team.json`,
   `abo`, `lizenz`, `templates`, `wiederkehrend.json`, `partner_erp_queue.json`
2. ✅ Regression-Test `test_backup_scope_regression.py` stellt sicher, dass 'devis' immer
   in `BUNDLE_SCOPE` ist (test_backup_scope_regression.py)
3. ✅ Alle Compliance-Tests nutzen `tempfile.mkdtemp()` + `monkeypatch` statt
   Live-Daten
4. ✅ Memory-Eintrag "TEST-ISOLATION" verhindert Wiederholung in zukünftigen Sessions

**User-Aktion erforderlich:**

- 28 verlorene Devis müssen aus externer Quelle rekonstruiert werden
  (SIA-451 Original-PDFs, Sorba-Export, ERP-Backend)
- **DRINGEND: Externe Datensicherung einrichten** (Time Machine, iCloud, NAS)
  damit ein solcher Vorfall in Zukunft nicht zu totalem Datenverlust führt

**Lehren für die Entwicklung:**

1. **Jeder destruktive Test MUSS in einem TEMP_DIR laufen** — niemals auf USER_DATA
2. **Jedes Backup MUSS alle User-Daten enthalten** — Devis-Daten sind das wertvollste
3. **Backups regelmäßig prüfen** — ein Backup das die wichtigsten Daten nicht enthält ist
   kein Backup
4. **Test-Coverage für Sicherheits-Operationen** — restore(), delete(), update() immer testen

---

## Geplante Releases

### v1.6.0 (Q4 2026)
- HMAC-SHA256 signierte Webhooks (M28)
- 5 weitere Performance-Optimierungen aus UX-Audit
- 7 Compliance-Lücken schliessen (Backups verschlüsselt ✓, Audit-Log ✓)
- Status-Page + Monitoring
- Stripe-Integration für echte Zahlungen
- Email-Welcome-Sequenz für Trial-User

### v2.0.0 (2027)
- QES (qualifizierte elektronische Signatur) via Skribble/DocuSign
- Rapport-/Regie-Modul (Bauleiter-Alltag)
- Gantt/Bauzeitenplan
- CRM/Pipeline
- Nachkalkulation Soll/Ist
- Mobile Field-Reporting App

---

**Format:** [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)
**Convention:** [Semantic Versioning](https://semver.org/)
**© 2026 Monterossa · DevisPro · Made in Switzerland 🇨🇭**
