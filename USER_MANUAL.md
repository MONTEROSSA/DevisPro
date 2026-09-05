# DevisPro v1.5 — Benutzer-Handbuch

**Version:** 1.5.0
**Datum:** September 2026
**Sprache:** Deutsch
**Zielgruppe:** Schweizer Bau-KMU, Architekturbüros, Generalunternehmer

---

## Inhaltsverzeichnis

1. [Installation](#installation)
2. [Erste Schritte](#erste-schritte)
3. [Devis erstellen](#devis-erstellen)
4. [Verbandskataloge nutzen](#verbandskataloge)
5. [Buchhaltungsexport](#buchhaltungsexport)
6. [Cloud-Sync & Teamwork](#cloud-sync)
7. [Subunternehmer-Marktplatz](#subunternehmer)
8. [KI-Agent nutzen](#ki-agent)
9. [Backup & Wiederherstellung](#backup)
10. [Datenschutz & DSGVO](#datenschutz)
11. [Fehlerbehebung](#fehlerbehebung)
12. [Support & Kontakt](#support)

---

## 1. Installation

### macOS (empfohlen)

**Systemanforderungen:**
- macOS 11.0 (Big Sur) oder neuer
- Apple Silicon (M1/M2/M3/M4) oder Intel
- 200 MB freier Festplattenspeicher
- Internetverbindung (für Updates + Cloud-Sync, optional)

**Installation Schritt für Schritt:**

1. **Download:** Klicke auf [Download macOS](https://devispro.de/DevisPro-2026-09-03-adhoc.zip) (46 MB)
2. **Entpacken:** Doppelklick auf `DevisPro_Mac.zip`
3. **Verschieben:** Ziehe `DevisPro.app` in den `Programme`-Ordner
4. **Erstmaliges Öffnen:** Doppelklick auf DevisPro
5. **Gatekeeper-Warnung?** "DevisPro kann nicht geöffnet werden, da es von einem nicht verifizierten Entwickler stammt"
   - Lösung: **Rechtsklick** auf DevisPro.app → "Öffnen" → "Öffnen" bestätigen
   - Oder Terminal: `xattr -d com.apple.quarantine /Applications/DevisPro.app`
6. **Fertig!** DevisPro startet.

**Was wird installiert:**
- DevisPro.app im Programme-Ordner
- `~/Library/Application Support/DevisPro/` (User-Daten)
  - `data/devis/` (Devis-Datenbank)
  - `data/meine_preise.csv` (eigene Preise)
  - `data/kundenstamm.json` (Firmenprofil)
  - `data/backups/` (verschlüsselte Backups)
  - `data/audit.log` (DSGVO-konformes Audit-Log)

**Was wird NICHT installiert:**
- Keine System-Extensions
- Keine Kernel-Module
- Keine Hintergrund-Daemons
- Keine Tracker, keine Telemetrie

### Windows

**Systemanforderungen:**
- Windows 10/11 (64-bit)
- 150 MB freier Festplattenspeicher
- .NET Framework 4.8+ (bei Windows 10/11 vorinstalliert)

**Installation:**

1. **Download:** [Download Windows](https://github.com/MONTEROSSA/DevisPro/releases/latest) (~50 MB)
2. **Entpacken:** Rechtsklick → "Alle extrahieren"
3. **Starten:** Doppelklick auf `DevisPro.exe`
4. **Windows-SmartScreen-Warnung?** "Mehr Info" → "Trotzdem ausführen"
5. **Fertig!**

### Linux

```bash
# Via pip
pip install git+https://github.com/MONTEROSSA/DevisPro.git

# Oder manuell
git clone https://github.com/MONTEROSSA/DevisPro.git
cd DevisPro
pip install -r requirements.txt
python -m devispro.app_gui
```

---

## 2. Erste Schritte

### Der Welcome-Wizard

Beim **allerersten Start** erscheint ein 5-Schritte-Wizard, der Sie durch die wichtigsten Funktionen führt:

1. **Willkommen** — Übersicht
2. **Profil einrichten** — Firmendaten, Kanton, SIA-Identifikation
3. **Erstes Devis importieren** — SIA-451/Sorba/PDF
4. **Kataloge nutzen** — NPK/BKS/HLKS/CRB-Marktpreise
5. **Bereit zum Verkauf!** — PDF, QR-Rechnung, Buchhaltung

Den Wizard können Sie jederzeit über **Hilfe → Tutorial starten** wiederholen.

### Stammdaten einrichten

Vor dem ersten Devis sollten Sie Ihre **Firmendaten** einrichten:

1. Menü: **Stammdaten** → **Profil**
2. Eingeben:
   - Firmenname (erscheint auf allen Devis/Rechnungen)
   - SIA-Identifikation (für SIA-451-Schnittstelle)
   - Kanton (für kantonale Marktpreise)
   - Stundensatz (CHF/h, z.B. 85.00)
   - Materialaufschlag (%, z.B. 12%)
   - Gemeinkosten (%, z.B. 10%)
   - Gewinn (%) — meist 5-10%
   - Mehrwertsteuer (%) — 8.1% für Werkleistungen, 7.7% für Lieferungen
3. **Speichern** klicken.

Diese Daten fliessen automatisch in alle neuen Devis ein.

### Lizenz-Status prüfen

Standardmässig sind **5 Devis kostenlos** (Trial). Menü **Hilfe → Lizenz-Status** zeigt:
- Verbleibende Gratis-Devis
- Ablaufdatum (falls Pro-Lizenz)
- Verlängerungs-Optionen

Für eine **Pro-Lizenz** (CHF 350/Mt, alle Funktionen): kontakt@devispro.de.

---

## 3. Devis erstellen

### Schritt 1: Import

**4 Wege um ein Devis zu erstellen:**

| Methode | Format | Wann nutzen? |
|---------|--------|--------------|
| **CRB-SIA Import** | .crbx | Sorba/SIA-451-Original |
| **SIA-451 Import** | .sia / .crb | Standard SIA-451 |
| **PDF-Devis** | .pdf | Architekten-PDF scannen |
| **CSV/Excel** | .xlsx, .csv | Eigene Vorlagen |

**So geht's:**
1. Klick auf **"Importieren"** in der linken Sidebar
2. Wähle das passende Format
3. Wähle die Datei
4. DevisPro erkennt automatisch Positionen, Mengen, Einheiten

### Schritt 2: Prüfen & Anpassen

Nach dem Import sehen Sie das Devis in der **Hauptansicht**:
- **Positionen** (links) — alle erkannten Positionen mit Mengen, Einheiten, EP
- **Material-Tab** (rechts) — Materialvorschläge pro Position
- **Total** (unten) — automatisch berechnete Summe

**Häufige Anpassungen:**
- **EP ändern:** Doppelklick auf den EP-Wert
- **Menge korrigieren:** Doppelklick auf die Menge
- **Position löschen:** Rechtsklick → Löschen
- **Neue Position:** "+" Button am Ende der Liste

### Schritt 3: Marktpreise nutzen (Verbandskataloge)

DevisPro **schlägt automatisch** Marktpreise aus den Schweizer Verbandskatalogen vor:

1. Klick auf **"Kataloge"** in der linken Sidebar
2. Wähle einen Katalog (NPK, BKS, HLKS, CRB)
3. Suche nach Positionen (z.B. "Innenanstrich")
4. Klick auf "+" um die Position mit EP zu übernehmen

**Verfügbare Kataloge:**
- **NPK** — 55 Positionen (Maler, Sanitär, Elektriker, Schreiner)
- **BKS** — 15 Positionen (Hochbau, Dach, Fenster, Türen)
- **HLKS** — 11 Positionen (Heizung, Lüftung, Klima)
- **CRB** — 7 Positionen (Baukostenschlüssel)

Die Preise sind **kantonal angepasst** (z.B. ZG +20%, JU -10%).

### Schritt 4: Export

**4 Export-Formate:**

| Format | Datei-Endung | Verwendung |
|--------|--------------|-------------|
| **PDF** | .pdf | E-Mail-Versand, Druck |
| **SIA-451** | .sia | Sorba/SIA-konforme Archive |
| **CSV** | .csv | Eigene Weiterverarbeitung |
| **Buchhaltung** | .csv | Abacus, Proffix, BMD, DATEV |
| **JSON** | .json | Eigene API-Integration |

**So geht's:**
1. Klick auf **"Export"** in der linken Sidebar
2. Wähle das Format
3. Speicherort wählen (DevisPro schlägt Dateinamen vor)
4. **Fertig** — Datei wird geschrieben und Statusbar zeigt "✓ Export: [Pfad]"

### Schritt 5: Rechnung & QR

**Aus einem bepreisten Devis eine Rechnung erstellen:**

1. Menü **Rechnung** → **Aus Devis erstellen**
2. Wähle das Devis aus
3. Rechnungsdaten prüfen (Empfänger, IBAN, MwSt)
4. **Generieren** — PDF mit Swiss-QR (SIX-konform) wird erstellt
5. **Versenden** per Mail oder WhatsApp

---

## 4. Verbandskataloge

### Was sind Verbandskataloge?

Die Schweizer Bauwirtschaft nutzt standardisierte Positionskataloge:
- **NPK** (Normenpositionen-Katalog)
- **BKS** (Baukosten-Standard)
- **HLKS** (Heizung-Lüftung-Klima-Sanitär)
- **CRB** (Baukostenschlüssel)

Diese enthalten **geprüfte Marktpreise** für Standardleistungen.

### Kataloge in DevisPro

**Import:**
1. Klick auf **"Kataloge"** → **"Katalog laden"**
2. Wähle eine .csv oder .xlsx-Datei (z.B. NPK-Preise 2026 vom SBV)
3. DevisPro importiert die Positionen
4. Sie sind ab sofort in der Suche verfügbar

**Verwendung:**
- Positionen aus Katalogen in Devis übernehmen (Klick "+")
- Eigene Preise gegen Marktpreise vergleichen
- Margen-Analyse pro Position

**Kantons-Anpassung:**
DevisPro berücksichtigt automatisch kantonale Preisunterschiede:
- ZG, GE, ZH: überdurchschnittlich
- BE, LU, FR: durchschnittlich
- AI, JU, UR: unterdurchschnittlich

---

## 5. Buchhaltungsexport

### Unterstützte ERP-Systeme

DevisPro exportiert direkt in:

- **Abacus** (Schweiz Marktführer)
- **Proffix** (Schweiz, KMU)
- **BMD** (Österreich)
- **DATEV** (Deutschland)
- **Banana** (Buchhaltung Plus)
- **SAP** (Enterprise)
- **Lexoffice** (Cloud)
- **SevDesk** (Cloud)
- **WinOffice** (Schweiz)
- **Mobit** (Schweiz)

### So exportieren Sie

1. Klick auf **"Buchhaltung"** in der linken Sidebar
2. Wähle dein ERP-System
3. DevisPro generiert eine CSV-Datei im richtigen Format
4. Importiere die CSV in dein ERP-System (siehe ERP-Handbuch)

### Format-Beispiel (Abacus)

```csv
Belegnr;Datum;Konto;Gegenkonto;Betrag;MwSt;Text
RG-2026-0001;04.09.2026;3200;1100;10000.00;810.00;Innenanstrich EFH Muster
```

---

## 6. Cloud-Sync & Teamwork

### Was ist Cloud-Sync?

**Optional.** Standardmäßig ist DevisPro **lokal** (keine Cloud). Sie können aber **optional** Cloud-Sync aktivieren, um:
- Mit Architekten zu arbeiten (Devis-Versand ohne PDF-Pingpong)
- Mit Subunternehmern zu koordinieren
- Im Team zu arbeiten (mehrere Mitarbeiter auf demselben Devis)

### Sync-Anbieter

- **Dropbox**
- **Google Drive**
- **OneDrive** (Microsoft)
- **iCloud Drive** (Apple)
- **Eigener Server** (SFTP/WebDAV)

### Ende-zu-Ende-Verschlüsselung

DevisPro **verschlüsselt alle Devis-Daten** vor dem Sync mit AES-256.
Sie behalten die **Datenhoheit** — der Cloud-Anbieter sieht nur verschlüsselte Blöcke.

### Aktivierung

1. Menü **Einstellungen** → **Cloud-Sync**
2. Wähle Anbieter (z.B. Dropbox)
3. Autorisiere DevisPro
4. **Sync starten**

---

## 7. Subunternehmer-Marktplatz

### Was ist der Marktplatz?

DevisPro hat einen **integrierten Marktplatz** für Subunternehmer-Vergabe:
- Profile von Elektrikern, Spenglern, Malern etc. in Ihrer Region
- Verfügbarkeits-Anfragen
- Angebots-Vergleich
- **Keine Provision**, keine versteckten Gebühren

### Subunternehmer finden

1. Menü **Marktplatz** → **Suchen**
2. Filter:
   - **Region** (Postleitzahl)
   - **Gewerk** (Maler, Elektriker, etc.)
   - **Verfügbarkeit** (sofort, diese Woche, nächsten Monat)
3. Klick auf **"Kontaktieren"** für eine Anfrage

### Ihre Firma sichtbar machen

1. Menü **Marktplatz** → **Mein Profil**
2. Eintragen:
   - Firmenname, Kontakt, Region
   - Gewerke die Sie anbieten
   - Kapazität (verfügbar pro Monat)
3. **Veröffentlichen** — Sie werden von anderen DevisPro-Nutzern gefunden

---

## 8. KI-Agent nutzen

### Was ist der KI-Agent?

DevisPro hat einen **integrierten KI-Agent** der Ihre Daten versteht. Sie können ihn in **natürlicher Sprache** fragen — kein Formular, keine Suche.

### Beispiele

**Im Devis-Hauptfenster** (Klick auf **"AI"**-Button):

```
Sie: "Was war mein umsatzstärkster Monat?"
AI:  "Ihr Gesamtumsatz: CHF 84'250 (aus 36 Devis).
     Durchschnittlicher Devis: CHF 2'340."

Sie: "Ich brauche eine Vorlage für Badezimmer-Renovation 12m2"
AI:  "Basierend auf 'Badezimmer-Renovation' (Sanitär) habe ich
     10 Standardpositionen aus dem NPK-Katalog:
     - 311.10 Montage WC-Anlage Standard — CHF 1'450/Stk
     - 311.20 Montage Waschbecken — CHF 1'180/Stk
     - 320.20 Kaltwasser-Leitung verlegen — CHF 125/m
     ..."

Sie: "Wie viel MwSt hab ich bezahlt?"
AI:  "Gesamt-MwSt 8.1%: CHF 6'824. Brutto: CHF 91'074."

Sie: "Zeig mir alle Maler-Devis vom letzten Jahr"
AI:  [filtert nach Branche "Maler" und Jahr 2025]
```

### Was der KI-Agent kann

- **Analyse:** Umsatz, Top-Kunden, Branchen-Aufteilung
- **Vorlagen:** Intelligente Positionsvorschläge pro Projekt
- **Marktpreise:** Kantons-spezifische EP-Empfehlungen
- **MwSt-Berechnungen:** Automatisch 8.1% / 7.7%
- **Filter:** Alle Devis nach Branche, Jahr, Kunde

### Was er NICHT kann

- **Keine** externen Daten abrufen (kein Web-Zugriff)
- **Keine** Live-Marktpreise (Stand Q1/2026)
- **Keine** Rechtsberatung

---

## 9. Backup & Wiederherstellung

### Backup erstellen

1. Menü **Datei** → **Backup erstellen**
2. Wähle: **Verschlüsselt** (empfohlen) oder **Klartext**
3. Wenn verschlüsselt: **Passwort eingeben** (mindestens 12 Zeichen)
4. Klick **Erstellen** — Backup wird in `~/Library/Application Support/DevisPro/backups/` gespeichert

**Verschlüsseltes Format: `.dpbk`**
- AES-256-CTR
- PBKDF2-HMAC-SHA256 (600'000 Iterationen, OWASP-konform)
- HMAC-SHA256 Integritäts-Check

### Backup wiederherstellen

1. Menü **Datei** → **Backup wiederherstellen**
2. Wähle die .dpbk- oder .zip-Datei
3. Wenn verschlüsselt: Passwort eingeben
4. Klick **Wiederherstellen** — Devis-Daten werden zurückgespielt

### Automatische Backups

DevisPro erstellt **automatisch** ein Backup:
- Beim ersten Start
- Alle 7 Tage (falls nicht schon eines erstellt)
- Vor jedem Update

### Aufbewahrung

- **Standard:** 365 Tage (automatische Löschung älterer Backups)
- **Audit-Log:** 10'000 Einträge (Ring-Buffer)

---

## 10. Datenschutz & DSGVO

### Was DevisPro speichert

- **Firmendaten** (Profil, Konditionen)
- **Devis** (Positionen, Preise, Mengen)
- **Kunden-Daten** (Namen, Adressen — nur lokal)
- **Eigene Preise** (meine_preise.csv)
- **Audit-Log** (Login, Export, Löschung — für Compliance)

### Wo die Daten liegen

**Lokal** auf Ihrem Mac/PC:
- `~/Library/Application Support/DevisPro/` (macOS)
- `C:\Users\<Name>\AppData\Local\DevisPro\` (Windows)
- `~/.local/share/DevisPro/` (Linux)

**Optional verschlüsselt in der Cloud** (nur wenn Sie Cloud-Sync aktivieren).

### Auskunftsrecht (DSGVO Art. 15)

Menü **Datenschutz** → **Meine Daten exportieren**

Sie erhalten eine **JSON-Datei** mit ALLEN Ihren Daten:
- Profil
- Devis (alle)
- Preise
- Kunden
- Audit-Log (DSGVO-konform: nur Ihre eigenen Aktionen)

### Recht auf Vergessenwerden (DSGVO Art. 17)

Menü **Datenschutz** → **Alle Daten löschen** (mit Passwort-Bestätigung)

**ACHTUNG:** Dies ist **unwiderruflich**! Vorher Backup erstellen!

### Audit-Log einsehen

Menü **Datenschutz** → **Audit-Log anzeigen**

Sie sehen alle Security-Events:
- Login/Logout
- Export-Aktionen
- Daten-Änderungen
- Löschungen

---

## 11. Fehlerbehebung

### "DevisPro kann nicht geöffnet werden" (macOS)

**Problem:** Gatekeeper blockt die App
**Lösung:**
1. Rechtsklick auf DevisPro.app → "Öffnen"
2. Klick auf "Öffnen" im erscheinenden Dialog
3. **ODER** Terminal: `xattr -d com.apple.quarantine /Applications/DevisPro.app`

### "App startet nicht" (Windows)

**Problem:** Visual C++ Redistributable fehlt
**Lösung:** Microsoft Visual C++ 2015-2022 Redistributable installieren (siehe https://aka.ms/vs/17/release/vc_redist.x64.exe)

### "Import schlägt fehl"

**Mögliche Ursachen:**
- Datei nicht im richtigen Format (SIA-451, Sorba, etc.)
- Datei beschädigt
- Encoding nicht UTF-8

**Lösung:** Datei mit anderem Tool öffnen (z.B. Excel für CSV), als UTF-8 speichern, erneut importieren.

### "Katalog-Preise fehlen"

**Lösung:** Kataloge müssen separat importiert werden. Menü **Kataloge** → **Katalog laden** → CSV/XLSX-Datei wählen.

### "Backup-Passwort vergessen"

**Es gibt KEINE Passwort-Wiederherstellung.** Verschlüsselte Backups sind ohne Passwort nutzlos (Sicherheits-Feature).

**Empfehlung:** Passwörter in einem Passwort-Manager speichern (z.B. 1Password, Bitwarden).

### Performance-Probleme

**App langsam?**
- Menü **Hilfe** → **Cache leeren** (löscht temporäre Dateien)
- Anzahl geöffneter Devis reduzieren
- Bei grossen Preislisten (>10'000 Positionen): Filter aktivieren

### Support kontaktieren

- **E-Mail:** info@devispro.de
- **Telefon:** +41 41 534 48 90
- **GitHub Issues:** https://github.com/MONTEROSSA/DevisPro/issues

Bitte immer beilegen:
- macOS/Windows-Version
- DevisPro-Version (Menü Hilfe → Über)
- Fehlermeldung (Screenshot)
- Reproduktions-Schritte

---

## 12. Support & Kontakt

### Offizieller Support

- **E-Mail:** info@devispro.de
- **Telefon:** +41 41 534 48 90 (Bürozeiten CH)
- **Web:** https://devispro.de
- **GitHub:** https://github.com/MONTEROSSA/DevisPro

### Community

- **GitHub Discussions:** https://github.com/MONTEROSSA/DevisPro/discussions
- **Issues:** https://github.com/MONTEROSSA/DevisPro/issues

### Schulungen

Für Architekten und Treuhänder bieten wir **kostenlose Online-Schulungen** an.
Kontakt: info@devispro.de

### Enterprise-Support

Für Enterprise-Kunden (10+ Mitarbeiter, API-Zugriff):
- Dedizierter Account-Manager
- SLA: 24h-Reaktion auf kritische Bugs
- Custom-Onboarding
- Prioritäts-Support

**Kontakt:** enterprise@devispro.de

---

**© 2026 Monterossa · DevisPro v1.5 · Made in Switzerland 🇨🇭**
