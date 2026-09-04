# DevisPro – Onboarding-Analyse (erste 5 Minuten)

**Analyst:** Subagent (Onboarding-Experte)
**Datum:** 2026-09-04
**Code-Basis:** `/devis-auto/DevisPro_Mac/app/webui.py` (3603 Z.) + `devispro/`
**Produktart:** Lokale Web-App (Python stdlib, Port 5070), Devis-Bepreisung für CH-KMU

---

## 1. Tatsächlicher Erst-User-Flow (Quellen: webui.py Z. 1163–1263, 943–985, 1733–1758, 2399–2478)

```
Browser öffnen (localhost:5070)
   │
   ├── KEINE Lizenz  ──►  /lizenz  ──►  /trial
   │       Formular: 8 Felder (Firma*, Name, Email*, Projekt, Kanton, Gewerk, Tarif)
   │       ↓  POST /trial_anmelden
   │       ↓  Trial = 90 Tage, mail an info@monterossa.ch, profil vorausgefüllt
   │       ↓  Redirect → /bepreisen
   │
   ├── Lizenz  ──►  /bepreisen  (= render_index, Z. 483–547)
   │       4 parallele Upload-Cards:
   │         • Datei (SIA/Bauweb/CSV/Excel/GAEB/ÖNORM/XRechnung)
   │         • 📷 Foto
   │         • 📡 Portal-Import
   │         • 🧠 Preise automatisch lernen (Zero-Typing)
   │       ↓  POST /import_devis
   │       ↓  Matcher (mock, threshold 0.6), Preise aus meine_preise.csv
   │       ↓  Speichert in history/, contributes Benchmark
   │       ↓  Redirect → /devis/{did}?importiert=1
   │
   └── /devis/{did}  ──►  Erste Wertanzeige:
        • Positions-Tabelle mit EP, Menge, Total
        • Margen-Copilot-Box (Plausi)
        • 📊 Markt-Benchmark-Box (kantonspezifisch)
        • Buttons: Offerte/PDF, Sorba, Abacus, Proffix, Mahnung, Lebenszyklus
```

### Time-to-First-Value (Schätzung)
| Pfad | Schritte | TTV |
|---|---|---|
| **Trial-First** (kein Code vorhanden) | Landing → /trial → 8 Felder → Mail → /bepreisen → Datei hochladen → /devis/{id} | **~3–5 Min** (synchroner Trial = sofort, kein Warten auf Mail-Code) |
| **Lizenz-First** | Lizenzcode eingeben → /bepreisen → Upload → /devis/{id} | **~90 Sek** |
| **Lead-Magnet** (`/check`) | 1 Klick → Datei → 3 Problempositionen | **~30 Sek** (kein Login) |

---

## 2. Drop-off-Punkte (Hauptrisiken)

| # | Wo | Risiko | Grund |
|---|---|---|---|
| **D1** | `/lizenz` als Default (Z. 1170) | **HOCH** | Trial-Gate ist **nicht** Default – User ohne Lizenz landet sofort auf Lizenzcode-Formular. Wer keine 24-stellige Code-Zeichenkette hat, denkt „kein Zugang" und schließt den Tab. Es gibt keinen sichtbaren Link zur Trial-Anmeldung im ersten Screen (man muss `/trial` manuell aufrufen oder den CTA „Code anwenden" ignorieren). |
| **D2** | Trial-Formular 8 Felder (Z. 943–985) | **HOCH** | Pflichtfelder: Firma*, Email*, Kanton (Dropdown), Gewerk (Dropdown), Tarif. Kein Progress-Indikator, kein „Skip-for-now". KMU-Handwerker ohne Laptop-Tastatur-Typing-Motivation springen ab. |
| **D3** | `/bepreisen` – 4 parallele Upload-Cards (Z. 496–544) | **MITTEL** | Choice-Paralyse. Keine klare „Empfehlung", keine Reihenfolge. User fragt sich: „Was ist meine Datei? Ist es SIA? Bauweb? Muss ich erst Preise anlegen?" |
| **D4** | Keine Preise in `meine_preise.csv` (Z. 486–491) | **MITTEL** | Hinweis oben: „⚠ Noch keine Richtpreisliste gespeichert" – der User kann Devis hochladen, aber bekommt **alle Positionen mit EP=0** (Matcher findet nichts). Schock-Moment, wirkt wie Bug. |
| **D5** | CSV-Format für Richtpreise (Z. 1751) | **MITTEL** | Spalten: `artikel_id;bezeichnung;einheit;ep_chf;kategorie`. Erwartet wird vom KMU eine Excel-Liste, nicht CSV mit Semikolon. Hoher Formatierungs-Aufwand. |
| **D6** | Trial-Mail-Doppelpunkt (Z. 142–150) | **NIEDRIG** | Bestaetigungs-Mail an Kunden + interne Mail an Monterossa + Lead-Log. Wenn SMTP nicht konfiguriert, schweigt die App still. |
| **D7** | Trial ohne Preise-Flow | **HOCH** | Trial_User lädt Devis hoch, sieht Tabelle mit Total = 0.00 CHF, denkt „funktioniert nicht" und schließt. Die App **hat** Zero-Typing-Flow (`/learn_prices`, Z. 536–542), aber er ist eine 4. Option in einem Wust von Cards, nicht der Default-Pfad. |

---

## 3. Aha-Moment / First-Value

Der wahre „Aha" ist `/devis/{did}` (Z. 412–423) – er zeigt:
- konkrete Summe in CHF
- Positions-Tabelle
- Margen-Copilot-Warnungen
- Markt-Benchmark (▼/▲/● pro Position)
- 7 Buttons zu Folge-Aktionen (Offerte, Sorba, Abacus, Mahnung, Lebenszyklus, Vorlage)

Aber: User sehen diesen Bildschirm nur, **wenn** (a) Trial da ist und (b) Preise stimmen. Sonst nur Nullen.

---

## 4. 5 konkrete Onboarding-Verbesserungen

### ① Sofort-Trial statt Lizenz-Gate (P0)
**Problem (D1):** `/lizenz` redirectet nicht-Trial-User weg.
**Fix:** Wenn `darf_nutzen()` False und kein `lizenz.json` existiert, **direkt** auf `/trial` umleiten (nicht auf `/lizenz`). Lizenzseite bekommt prominenten Link „Noch keinen Code? → 3 Monate gratis testen".
**Code:** webui.py Z. 1163–1172, ergänzen um Pfad `/trial?reason=keine_lizenz` als Default.

### ② Trial-Formular: 8 → 3 Felder (P0)
**Problem (D2):** 8 Felder am ersten Touch.
**Fix:** Nur Firma*, Email*, Kanton* (Pflicht). Rest (Name, Gewerk, Projekt, Tarif) per „Später ausfüllen" optional. Kanton-Default = Firmensitz-Heuristik aus IP/Email (`.ch → ZH`, `.de → DE-Hinweis`). Tarif = Default „devis" (kann jederzeit in Abo geändert werden).
**Code:** `render_trial` Z. 943–985 + `_profil_vorbelegen` in license_admin.py.

### ③ Zero-Typing als Default-Onboarding (P0, löst D3+D4+D7)
**Problem:** User muss Datei hochladen **und** Preise haben → tote Straße ohne Preise.
**Fix:** Neuer Wizard `/start`:
  1. **„Lade 1–3 deiner alten Devis hoch"** (`/learn_prices`, Z. 2479+)
  2. **„DevisPro lernt deine Einheitspreise"** – Status-Bar, animierte Confidence
  3. **„Importiere dein erstes Devis zum Bepreisen"** – derselbe Matcher, aber **jetzt** mit deinen Preisen
  4. **Ergebnis** `/devis/{did}` mit echten Summen
**Ergebnis:** TTV von ~3 Min auf **~90 Sek**, ohne Tippen.

### ④ Progress-Indikator + Erfolgs-Animation (P1)
**Fix:** Top-Bar mit 4 Schritten (Trial → Stammdaten → Erstes Devis → Erstes PDF). Jeder Step grün animiert, wenn erreicht. Beim Klick auf `/devis/{did}` → Konfetti-Banner „Dein erstes Devis ist bepreist: 12'450 CHF in 47 Sek." + animiertes Hochzählen.
**Code:** Neuer `progress_mod.py` mit Cookie-State `onboarding_step`.

### ⑤ Pre-Mapped 3-Sample-Projekte beim ersten Start (P1)
**Problem:** Leere History = leerer Bildschirm = „ist das alles?".
**Fix:** Beim ersten `/bepreisen`-Aufruf (wenn `setup_done != True`) ein Modal: **„Willst du mit einem Demo-Devis starten? Drei echte Beispiele (Sanitaer, Gipser, Elektro) zeigen alle Funktionen."** → Klick lädt `/sample_project.py`, füllt Stammdaten + History mit echten Beispielen.
**Code:** Datei existiert bereits: `devispro/sample_project.py` (80 Zeilen) – muss nur noch in `render_index` Z. 486–547 eingebunden werden.

---

## 5. A/B-Test-Design

**Hypothese:** Reduzierung Trial-Felder + Zero-Typing-Onboarding erhöht Trial→TTV-Conversion um ≥40 %.

| Variante | Beschreibung | Primär-Metrik |
|---|---|---|
| **A (Kontrolle)** | 8-Felder-Trial → /bepreisen → 4 Upload-Cards | Time-to-First-Devis-View |
| **B (Treatment)** | 3-Felder-Trial → Zero-Typing-Wizard (`/learn_prices` zuerst) → Sample-Projekt-Modal | Time-to-First-Devis-View |

**Setup:**
- Cookie-Bucket: `ab_onboarding` ∈ `{control, treatment}` (50/50 deterministisch aus User-ID-Hash)
- Event-Tracking in `data/trial_leads.log` (JSONL, schon vorhanden in lead_magnet.py Z. 95–106)
- Neue Events:
  - `trial_started` (mit `bucket`)
  - `trial_completed`
  - `first_devis_uploaded` (mit `bucket`, `ttv_seconds`)
  - `first_pdf_generated`
- Dauer: 4 Wochen oder n=200 Trials pro Bucket
- Entscheidungs-Threshold: ≥20 % relative Verbesserung bei p<0.05 (zweiseitiger t-Test auf log-transformierte TTV-Sekunden)

**Sekundär-Metriken (Guardrails):**
- Trial→Paying-Conversion (Langzeit, 60 Tage)
- Support-Tickets/Woche pro Bucket (sollte nicht steigen)
- 7-Tage-Retention

**Implementation:**
- Datei: `devispro/onboarding_ab.py` (~80 Z.)
- Bucket-Vergabe in `license_admin.trial_anmelden` Z. 137 (nach `kunde_anlegen`)
- Varianten-Code in `webui.py` Z. 2776 ff. via `if bucket == "treatment": render_zero_typing_form() else: render_trial()`

---

## 6. Quick-Wins (heute machbar, <1 h)

1. `/lizenz?lang=de` → Button ergänzen: `<a class='btn-sm' href='/trial'>3 Monate gratis testen</a>` (5 Min)
2. Trial-Formular: Felder Name, Projekt, Gewerk auf `<details>` mit „optional" zusammenfassen (15 Min)
3. Wenn `darf_nutzen()` False **und** keine `lizenz.json` → Redirect zu `/trial` statt `/lizenz` (10 Min)
4. `render_index` Z. 488–491: Wenn keine Preise, dann **großes** Banner mit CTA „→ Preise in 60 Sek. lernen (Zero-Typing)" statt kleinem Warn-Hinweis (20 Min)

---

**Erwartete Effekte:**
- TTV von ~3 Min auf ~90 Sek (Variante B)
- Trial-Conversion +30–50 % (eigene Schätzung, Branchen-Benchmark)
- Drop-off D1/D2 zusammen: –60 %
- Aha-Moment früher (Sample-Projekt vor leerer History)