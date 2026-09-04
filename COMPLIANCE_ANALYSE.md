# DevisPro Compliance-Gapanalyse (CH/DSG · DSGVO · ISO 27001)

**Analyst:** Compliance-Subagent
**Datum:** 2026-09-04
**Scope:** `/Users/ferdinandrothlisberger/devis-auto/devispro/*.py` (~95 Module), Backup-/Sync-/Auth-Stack
**Methodik:** Statische Code-Analyse (Quellcode + Kommentare), kein Runtime-Pentest

---

## 1. Wo personenbezogene Daten verarbeitet werden

DevisPro ist ein Offert-/Rechnungs-Tool für CH-Bau-/Handwerks-KMU. Folgende **DSG/DSGVO-relevante Daten** werden gespeichert und verarbeitet (alle unverschlüsselt als Klartext-JSON/CSV im `data/`-Verzeichnis):

| Datenkategorie (DSG Art. 5 lit. a, DSGVO Art. 4) | Speicherort | Klasse |
|---|---|---|
| Kundendaten (Firma, Name, Adresse, PLZ/Ort, E-Mail, Tel.) | `data/kundenstamm.json`, in jeder Rechnung (`kunde`-Feld, `rechnung.py:56`) | identifizierbar |
| Mitarbeiterkonten (Benutzername, Rolle, PBKDF2-Hash) | `data/team.json` (`team_auth.py:53-83`) | identifizierbar + Auth-Geheimnis |
| Admin-Passwort | `data/admin_pass.json` (`admin_auth.py:18-39`) | Auth-Geheimnis |
| Bankverbindungen Kunden (IBAN via QR-Rechnung) | `qr_rechnung.py`, `rechnung.py` | finanzielle Daten (sensibel) |
| Angebote, Werkverträge, Abnahmeprotokolle (Vertragspartner, Liegenschaftsadresse, Bauphase) | `data/devis/<id>/*.pdf`, `meta.json` (`history.py:33-60`) | Vertragsdaten |
| Marktpreis-Benchmark-Daten | `benchmark.py` (anonymisiert, aber kein dokumentiertes Anonymisierungsverfahren) | ggf. ableitbar |
| Backup-Artefakte (sämtliche obige Daten) | `data/backups/devispro_backup_*.zip` | vollständiger Klon |

**Rechtsgrundlage:** DevisPro ist Auftragsverarbeiter für die KMU-Kunden (= Verantwortliche). KMU tragen die DSGVO/DSG-Haftung gegenüber Bauherren/Endkunden. DevisPro muss die dazu nötige **Technik- und Organisations­sicherheit** (TOM, DSG Art. 7, DSGVO Art. 32) bereitstellen — die folgenden Lücken verhindern, dass ein KMU DevisPro **DSGVO-konform einsetzen** kann.

---

## 2. FINMA-Konformität

**Status:** Nicht direkt FINMA-pflichtig (DevisPro ist keine Bank/kein Finanzintermediär i.S.v. FINIG/FINIA). **ABER:** Verarbeitet Zahlungs­verbindungen (QR-Rechnung mit IBAN), Mahnungen (`mahnung.py`) und Rechnungs­historien. Wenn ein KMU-Kunde DevisPro zur Verwaltung **grenz­überschreitender Zahlungen** oder zur **Inkasso­automation** einsetzt, kann es unter `MwG` (Geldwäschereigesetz, Art. 2 lit. b) als "Finanzintermediär im Nebenberuf" eingestuft werden, wenn es regelmässig Drittzahlungen > CHF 1'000/abwickelt.

→ **Aktuelle Lücke:** Keine Transaktionsüberwachung, kein AML-Screening, keine Schwellenwert­logik, kein Pflicht­feld "Verwendungszweck/KYC".

---

## 3. Die 7 wesentlichen Compliance-Lücken

### Lücke 1: Backups sind NICHT verschlüsselt (KRITISCH)
**Beweis:** `backup.py:5-10` (Kommentar): *"Voll-Verschluesselung waere mit cryptography, das auf dem Zielsystem nicht verfuegbar ist – daher integritaetsgesichert."* → ZIP-Container mit Klartext-Inhalt, nur SHA-256-Manifest-Hash als Integritätsschutz.

**Verstoss gegen:** DSG Art. 7 (TOM), DSGVO Art. 32 lit. a (Verschlüsselung als angemessene Massnahme), ISO 27001 A.10.1.1, NIST CSF Protect.Data-at-rest.

**Folge:** Bei Diebstahl/Laptop-Verlust/Break-in sind alle Kunden­daten, Mitarbeiter­passwörter, IBANs ungeschützt.

**Aufwand Schliessung:** **Mittel (3-5 PT)**
- Backup-Modul: ZIP durch `cryptography.fernet.Fernet` (oder AES-GCM via `cryptography.hazmat`) ersetzen, Passwort aus PBKDF2(user_key, salt).
- Optional: User-UI "Backup-Passwort setzen", Schlüsselableitung 600'000 Iterationen (OWASP 2023).
- Akzeptanzkriterium: `verify_backup()` entschlüsselt + re-hashed Manifest, Restore nur mit Passwort.

---

### Lücke 2: Kein echter Audit-Log (DSG Art. 4 lit. d Protokollierung, ISO 27001 A.12.4)
**Beweis:** Im gesamten Quellbaum finden sich **keine** `logging`-Handler, kein `RotatingFileHandler`, keine `audit_log`-Tabelle. `history.py` speichert nur fachliche Aktionen (Devis-Status), **keine sicherheits­relevanten Ereignisse** (Login fehlgeschlagen, Passwort-Reset, Backup-Erstellung, Admin-Privileg-Eskalation, Datenexport).

**Verstoss gegen:** DSG Art. 4 lit. d (Bearbeitungs­protokoll), DSGVO Art. 30 (Verzeichnis der Verarbeitungs­tätigkeiten), ISO 27001 A.12.4.1/A.12.4.3.

**Aufwand Schliessung:** **Mittel (4-6 PT)**
- Modul `audit_log.py` mit JSONL-Appender + Rotation (10 MB × 5).
- Mandatory Hook in `team_auth.pruefen()`, `admin_auth.pruefen()`, `backup.create()`, `history.delete()`, `cloud_sync.push/pull`.
- Felder: `ts, actor, role, action, resource, ip (optional), outcome`.
- Append-only via `os.O_APPEND` + Hash-Chain (jede Zeile enthält `prev_hash` → Tamper-Evidence, ISO 27001 A.12.4.2).

---

### Lücke 3: Cross-Border-Datentransfer ohne Schutz (DSGVO Art. 44 ff.)
**Beweis:** `cloud_sync.py:33-67, 209-275` — Provider-Klasse für **iCloud Drive, OneDrive, Google Drive, Dropbox, NAS** mit unverschlüsseltem `shutil.copy2()` der Daten (`push`/`pull`, Zeilen 158-184). Klartext-Kunden­daten wandern in US-/Irland-Rechen­zentren ohne SCC, ohne TIA, ohne User-Einwilligung.

**Verstoss gegen:** DSGVO Art. 44-49 (Drittlandtransfer), DSG Art. 6 lit. b (Bearbeitungs­regeln), Schweizer DSV (Verordnung zum DSG) Art. 8 ff. (Drittstaaten).

**Aufwand Schliessung:** **Hoch (8-12 PT)**
- Pre-Encryption-Layer: alle synchronisierten Files vor `push` mit AES-GCM (Header pro File, Key vom User-Master-Passwort via Argon2id) verschlüsseln; auf Remote nur `.age`/`.enc.aes` Files.
- Settings: Standard **alle Cloud-Provider DEAKTIVIERT**, Opt-in mit erklärender Einwilligungs­maske (DSG Art. 6 Einwilligung) + Auswahl "Schweiz-only" (z.B. Infomaniak, SWISS RABBIT).
- Akzeptanzkriterium: Audit-Log-Eintrag bei jeder Provider-Aktivierung; User kann Anbieter-Liste sehen.

---

### Lücke 4: Admin-Passwort = ungesalzenes SHA-256 (DSG Art. 7, ISO 27001 A.9.2.4)
**Beweis:** `admin_auth.py:30, 37`: `hashlib.sha256(neues.encode()).hexdigest()` — **kein Salt**, **kein Stretching**, **kein Pepper**, 600'000× zu schnell gegen Rainbow-Tables/GPU-Brute-Force.

**Vergleich:** Team-Passwörter (`team_auth.py:53-54`) benutzen korrekt PBKDF2-HMAC-SHA256 mit 100'000 Iterationen + Salt → Inkonsistenz im selben Produkt.

**Verstoss gegen:** DSG Art. 7 (Verhältnismässigkeit), ISO 27001 A.9.2.4 (Passwort-Management), NIST SP 800-63B (Argon2id/bcrypt/PBKDF2 mit Mindest-Iterationen).

**Aufwand Schliessung:** **Niedrig (0.5-1 PT)**
- `admin_auth._lade_hash` + `passwort_setzen` ersetzen: `hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 600_000)` (oder `argon2-cffi` falls Dependency erlaubt).
- Migration: Beim ersten Login mit Default-Passwort "devispro-admin-2026" (immer noch hardcoded!) erzwingen — **diesen Hardcode unbedingt entfernen**.

---

### Lücke 5: Kein DSGVO-Auskunftsrecht (Art. 15) / Recht auf Löschung (Art. 17) implementiert
**Beweis:** Suche nach `consent`, `auskunftsrecht`, `export.*data`, `delete.*account`, `datenlöschung` ergibt **Null Treffer** im App-Code (nur in Vendor-libs). Es gibt keine API/UI für einen Kunden (Bauherr), vom KMU **alle über ihn gespeicherten Daten** als JSON/PDF zu erhalten, und keinen "Lösch-mich"-Workflow.

**Verstoss gegen:** DSGVO Art. 15 (Auskunft), Art. 17 (Vergessenwerden), Art. 20 (Daten­übertrag­barkeit), DSG Art. 8, 32.

**Aufwand Schliessung:** **Mittel (4-6 PT)**
- Modul `dsgvo.py` mit Funktionen `export_subject(name, email)` (gibt alle Rechnungen/Devis/Logs als ZIP) und `delete_subject(...)` (Kaskadierendes Löschen + Anonymisierung der `meta.json`).
- GUI-Button im Reiter "Datenschutz": "Auskunft erteilen" / "Daten löschen" mit 2FA-Bestätigung.
- Standard-Frist 30 Tage (konfigurierbar), mit Audit-Log-Eintrag (an Lücke 2 koppeln).
- **Wichtig:** `history.delete()` und `backup.create()` müssen DSGVO-Löschungen VOR Backup-Rotation aufnehmen.

---

### Lücke 6: Keine Aufbewahrungs-/Lösch-Fristen (DSG Art. 5 lit. e Speicherbegrenzung, OR Art. 957f)
**Beweis:** `history.delete()` löscht nur auf expliziten User-Befehl; keine automatische Retention. Backups akkumulieren unbegrenzt (`data/backups/devispro_backup_*.zip`, hunderte Einträge seit 2026-08).

**Verstoss gegen:** DSG Art. 5 lit. e (Speicherbegrenzung), DSGVO Art. 5 lit. e, OR Art. 957f (10 Jahre Buchhaltungs­belegpflicht → konflikt­anfällig: man muss löschen, ABER Buchhaltung muss 10 J. bleiben).

**Aufwand Schliessung:** **Mittel (3-5 PT)**
- Policy-File `data/retention.json` mit Default-Regeln:
  - `kundenstamm.json`: 7 Jahre nach letztem Kontakt
  - `devis/*.pdf`: 10 Jahre (OR-Pflicht)
  - `team.json` inaktiv: 30 Tage nach Deaktivierung
  - `backups/`: Rolling 90 Tage, dann **sicher löschen** (nicht nur `unlink`, sondern `os.urandom` + `fsync` + `unlink` falls ISO 27001 A.11.2.7).
- Cron-Job beim App-Start (`lifecycle.py` ist vorhanden) prüft Fristen.

---

### Lücke 7: 1024-Bit-RSA + unklare Schlüssel-Hygiene (ISO 27001 A.10.1.2)
**Beweis:** `crypto_rsa.py:9, 64` — *"Schluessellaenge 1024 Bit (ausreichend fuer Lizenz-Codes; reine Python-Generierung in ~20s, Verifikation via pow() in Mikrosekunden)."* → 1024 Bit gilt seit NIST SP 800-131A (2011) als **deprecated** und soll bis 2030 ersetzt werden; BSI TR-02102-1 verlangt seit 2023 mindestens 2048 Bit. Lizenz-Datei (`license.py`) verlässt sich auf Public Key in der App — wenn der Private Key beim Anbieter kompromittiert wird, ist keine CRL/Revocation-Mechanik vorhanden.

**Verstoss gegen:** ISO 27001 A.10.1.2 (Kryptographie­verfahren), BSI TR-02102, NIST SP 800-131A.

**Aufwand Schliessung:** **Niedrig (1-2 PT)** (für Lizenz-Kontext)
- 2048 Bit RSA oder Wechsel auf Ed25519 (pure-stdlib via `cryptography` falls erlaubt).
- CRL-File serverseitig, App prüft vor `verify()` `license.revoked(cert_id)`.
- Falls keine Lib erlaubt: dokumentierte Risiko­akzeptanz (DevisPro-Eigentümer), ausgewiesen im "Statement of Applicability" (ISO 27001 Klausel 6.1.3).

---

## 4. Zusatz­beobachtungen (nicht in Top-7, aber relevant)

| Beobachtung | Datei | Risiko |
|---|---|---|
| Default-Passwort hardcoded | `admin_auth.py:23` `DEFAULT_PASS = "devispro-admin-2026"` | Brute-Force bei Erstinstallation trivial |
| `SESSION_SEK = secrets.token_hex(32)` flüchtig pro Prozess | `team_auth.py:23` | Restart = alle Sessions ungültig (UX), aber kein persistenter Schlüssel­schutz |
| `team_auth.pruefen` ohne Rate-Limiting / Lockout | `team_auth.py:96-102` | DSG Art. 7 (Verhältnismässigkeit) — keine Brute-Force-Härtung |
| `cloud_sync.py` schreibt Logs mit absoluten Pfaden (`.log` im ignore_patterns, OK) — aber kein Audit-Log der Sync-Vorgänge | `cloud_sync.py:64-67` | Lücke 2 verschärft |
| `benchmark.py` Beitrag "anonym" ohne dokumentierte Anonymisierungs­methode | `history.py:53-59` | DSG Art. 11 lit. b (Anonymisierung) — fraglich |
| Lizenz-Datei `license.py`: Hardcoded Public-Key-String | (zu prüfen in `license.py`) | Lücke 7 verwandt |
| Kein Auftrags­verarbeitungs­vertrag (AVV/DPA) als Template im Lieferumfang | n/a | Wenn KMU DevisPro einsetzt, brauchen sie AVV mit DevisPro (Auftrags­verarbeiter) |

---

## 5. Aufwands-Tabelle (gesamthaft zur Schliessung der Top-7)

| # | Lücke | Priorität | Aufwand (PT) | Calendar-Dauer |
|---|---|---|---|---|
| 1 | Backups unverschlüsselt | KRITISCH | 3-5 | 1 Woche |
| 2 | Kein Audit-Log | KRITISCH | 4-6 | 1.5 Wochen |
| 3 | Cross-Border ohne Schutz | HOCH | 8-12 | 3 Wochen |
| 4 | SHA-256 Admin-Passwort | HOCH | 0.5-1 | 1 Tag |
| 5 | Kein DSGVO Art. 15/17 | HOCH | 4-6 | 1.5 Wochen |
| 6 | Keine Retention-Fristen | MITTEL | 3-5 | 1 Woche |
| 7 | 1024-bit RSA + CRL | NIEDRIG | 1-2 | 2 Tage |
| **Σ** | | | **24-37 PT** | **~8-10 Wochen (1 FTE)** |

Mit 2 FTE parallel: **4-5 Wochen bis DSGVO-MVP-Compliance**. ISO-27001-Vollzertifizierung zusätzlich +8-12 Wochen (ISMS, SoA, internes Audit, externes Audit durch SQS/TÜV).

---

## 6. Quick-Wins (heute machbar, <1 PT total)

1. Hardcoded `DEFAULT_PASS` entfernen → Erstinstallation erzwingt Passwort-Setzung.
2. `admin_auth.passwort_setzen`: PBKDF2 mit 600'000 Iterationen + Salt.
3. `history.delete()` + `kundenstamm`-Eintrag: Funktion `purge_pii(name)` als Stub, der alle zugehörigen Rechnungen/Devis listet (Vorbereitung für Lücke 5).
4. CLI-Befehl `devispro export --subject "Max Muster"` → ZIP mit allen Treffern (Vorbereitung Lücke 5).
5. `backup.py` Header-Kommentar von "integritaetsgesichert" auf "PLAINTEXT-BACKUP – nur lokal" anpassen → User-Warnung.

---

## 7. Fazit

DevisPro ist ein **funktional vollständiges** KMU-Tool, aber **nicht** "out-of-the-box" DSGVO/DSG-konform. Die grösste rechtliche Gefahr ist die **Kombination aus Lücke 1 (unverschlüsseltes Backup) + Lücke 3 (unkontrollierter Cloud-Sync)** — beides öffnet unbefugten Dritten den Zugriff auf Kunden­daten ohne, dass ein KMU dies überhaupt bemerkt.

Für die ersten 2 Pilot-Kunden (z.B. Malergeschäft Muster AG, DevisPro-Marketing nennt sie) empfehle ich:
- Lücken 1, 2, 4, 5 **vor** dem ersten produktiven Kunden-Einsatz zu schliessen.
- Lücken 3, 6, 7 im ersten grossen Release-Update.
- Eine **Datenschutz­erklärung für DevisPro selbst** zu verfassen (devspro.de ist Endkunden-Touchpoint → Cookie-/Tracking-Pflicht).
