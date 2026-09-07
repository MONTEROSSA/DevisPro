# Feature-Gap-Analyse: DevisPro vs. Mitbewerber (Bauwise / bauMax / Sorba / SIA-451-Umfeld)
**Analyst:** Devis-Software-Experte  · **Datum:** 2026-09-04  · **Codebase:** ~/devis-auto/devispro/devispro/ (83 Module, ~20 k LOC)

## Bestand (was DevisPro schon hat – die Basis ist solide)
- Import: CRB-SIA, SIA-451, GAEB, XRechnung, ÖNORM, Bauweb, CSV/Excel, **Foto/PDF-OCR** (vision.py – tesseract im Bundle)
- Bepreisung: EK → Aufschlag → GK → Gewinn (kalkulation.py), Margen-Copilot (plausibility.py), Verbandskataloge
- Exporte: SIA, CSV, PDF (pdf_native.py – stdlib, dependency-frei), QR-Rechnung (qr_rechnung.py), Abacus/Proffix-Import (connector.py)
- Lifecycle: Bepreist → Offerte → Rechnung → Teilzahlung → Mahnung (lifecycle.py, mahnung.py)
- Risiko-Cockpit + Zahlungsplan (zahlungsplan.py – beworben als USP)
- Wiederkehrende Rechnungen (recurring.py – erst seit kurzem, vorhanden)
- Multicurrency CH/EUR/USD/GBP (multicurrency.py, nur Anzeige/Export)
- Cloud-Sync, ERP-Ökosystem, KI-Agent (Lokal via Ollama), WhatsApp-Deep-Link
- Marketplace, Team-Auth, Lizenz/Abo, Lead-Magnet
- Marketing-Materialien, Analysen-Bibliothek, Kantone-Spezifika

## Was FEHLT – aber jeder grössere Mitbewerber hat (Bauwise, bauMax, Sorba, Abacus, Proffix)
Recherche-Basis: Bauwise-Website & Reviews, branchenübliche Erwartungen im CH-Bau-KMU.

---

### 🔴 KILLER-FEATURE 1: Rapport- / Regie-Modul (Tagesrapport, Regiezettel, mobile Erfassung)
**Wettbewerbs-Realität:** Jeder Bauleiter/-monteur füllt heute täglich Regie- oder Tagesrapporte aus (Std, Material, Maschinen, Wetter, Fotos, GPS). Bauwise, bauMax und Sorba haben das als Kernmodul. DevisPro hat dafür **kein Modul** (Suche nach "rapport|regie|stundenzettel" liefert nur 3 Treffer in 83 Modulen — alles nur in Doku/Kommentaren).

**Umfang für 2-4 Wochen:**
- `rapport.py` – Datenmodell Rapport (Datum, Projekt, Monteur, Stunden, Materialverbrauch, Notiz, Wetter, GPS optional)
- GUI: Tagesrapport-Erfassung im Hauptfenster + **PWA-Mobilversion** (eigener `rapport_pwa.py`, Browser, offline-fähig via Service Worker — keine App-Store-Abhängigkeit)
- Automatische Übernahme ins Devis (Rapport → Regieposition mit Stundensatz aus `firmen_preise.py`)
- PDF-Export Rapport mit Logo/Fotoanhängen

**Hebel:** Ersetzt Excel- und WhatsApp-Foto-Listen. Tagesgeschäft jedes Poliers/ Bauleiters.

---

### 🔴 KILLER-FEATURE 2: Gantt-/Bauzeitenplan (Bauablaufplan, Meilensteine, Soll-/Ist-Vergleich)
**Wettbewerbs-Realität:** Sorba, bauMax und Bauwise haben visuelle Gantt-Charts mit Phasen, Abhängigkeiten, kritischem Pfad. DevisPro hat **keine Terminplanung** (kein Modul mit "gantt|zeitplan|milestone" — 0 Treffer).

**Umfang für 2-4 Wochen:**
- `gantt.py` – Phasen + Vorgänge, Vorgänger/Nachfolger-DAG, Dauer in AT, Pufferzeit
- Visualisierung: einfaches **SVG-Gantt** (kein Charting-Lib nötig, reine Stdlib — passt zur Dependency-Frei-Philosophie) oder matplotlib falls schon vorhanden
- Soll-/Ist-Vergleich aus Rapport-Daten (Kreuzung mit Feature 1)
- Export PDF (SIA-konformer Bauzeitplan) + CSV (für MS Project Import)

**Hebel:** Bauablauf ist im SIA-451-Alltag Pflicht; DevisPro positioniert sich damit als "vollständige Werkzeugkette", nicht nur Bepreisung.

---

### 🔴 KILLER-FEATURE 3: CRM-light + Kunden-Pipeline (Lead → Offerte → Auftrag → Follow-up)
**Wettbewerbs-Realität:** bauMax/Sorba haben klassische CRM-Ansichten mit Wahrscheinlichkeit, Erinnerungen, Aktivitäten-Historie. DevisPro hat `lead_magnet.py` (nur anonyme Web-Leads) und `recurring.py` — aber **keine Kunden-/Pipeline-Verwaltung** im Produkt.

**Umfang für 2-4 Wochen:**
- `crm.py` – Kundenakte mit Kontakten, Notizen, Aktivitäten, Wahrscheinlichkeit pro Devis
- Pipeline-Ansicht (Kanban): Offen / Offeriert / Verhandelt / Gewonnen / Verloren
- Auto-Erinnerungen (E-Mail / Desktop-Toast): "Offerte xy läuft in 5 Tagen ab"
- Übergabe an Marketing-Modul (Referenzen automatisch aus gewonnenen Devis)

**Hebel:** Konversiontracking — heute sieht das KMU nicht, welche Offerten sterben. Hoher operativer Wert.

---

### 🔴 KILLER-FEATURE 4: Qualifizierte elektronische Signatur (QES) für Offerte & Vertrag
**Wettbewerbs-Realität:** bauMax und grosse ERP bieten SwissID-Signing oder DocuSign-Integration. DevisPro hat nur PDF-Signatur im fpdf-Sign-Modul (für PDF-PKI, kein Geschäftsprozess) — kein "Offerte per Link vom Kunden unterschreiben lassen".

**Umfang für 2-4 Wochen:**
- `signatur.py` – Wrapper für **Skribble / DocuSign / SwissID** (Partner-API, offiziell verfügbar)
- "Sign-Link erzeugen" aus einer Offerte → Mail an Kunden → Status-Polling (Webhook)
- Audit-Log (wer hat wann unterschrieben, IP, Gerät) im Lifecycle
- Fallback: einfacher Signatur-Pin per Mail (für Prepaid-Tarif)

**Hebel:** Differenziert DevisPro von Gratis-Offerten-Editoren — kompletter digitaler Abschluss ohne Druck/Scan.

---

### 🔴 KILLER-FEATURE 5: Nachkalkulation & Soll-Ist-Vergleich (echte Marge pro Projekt)
**Wettbewerbs-Realität:** Bauwise' Kernversprechen. LiveCosts' USP. DevisPro hat `roi.py` (Marketing-Stundenersparnis) und `margen_copilot.py` (Plausibilität VOR Angebot), aber **kein Modul, das nach Projektabschluss die echte Marge gegen die Offerte rechnet**.

**Umfang für 2-4 Wochen:**
- `nachkalkulation.py` – verrechnete Ist-Kosten pro Position (aus Rapporten + Materialentnahmen + Subunternehmer-Rechnungen)
- "Projekt-Cockpit": Offerte-Summe ↔ Ist-Summe, Marge live, Ampel
- Lernende Margen-Korrektur: KI-Agent vergleicht mit historischen Projekten und schlägt EP-Korrekturen vor (baut auf vorhandenes `local_ai.py`)

**Hebel:** Bringt DevisPro auf Augenhöhe mit Bauwise. Soll/Ist ist DAS Verkaufsargument im Bau.

---

### 🔴 KILLER-FEATURE 6: Subunternehmer-Vergleichsportal & Ausschreibungs-Modul
**Wettbewerbs-Realität:** Sorba/Messerli haben SU-Verwaltung mit Vergleichsmatrix. DevisPro hat `subunternehmer.py` (sehr klein, 71 LOC, vermutlich nur Stammdaten). Kein Vergleichs-/Vergabe-Workflow.

**Umfang für 2-4 Wochen:**
- `su_vergabe.py` – SU pro Gewerk listen, Preisanfrage als PDF (anonymisiert) rausschicken, Angebote zurück-importieren
- Vergleichsmatrix: SU × EP × Lieferzeit × Bonität (Bonität: optional Bonapay/CRIF-Lookup-API, schlank integrierbar)
- Vergabeentscheid dokumentieren (Audit)
- Folge: automatische Bestellung (baut auf connector.py / ERP auf)

**Hebel:** Sub-Unternehmer machen bei GU/TU-Projekten 60–80 % des Volumens aus. Heute in Excel.

---

### 🔴 KILLER-FEATURE 7: Mobile Offerte-Erfassung vor Ort (Foto → KI-Devis auf der Baustelle)
**Wettbewerbs-Realität:** Viele Wettbewerber haben Mobile-Apps. DevisPro hat vision.py (OCR-Foto-Import) — aber nur für Desktop. Keine mobile Erfassung auf der Baustelle ("stehe beim Kunden, will in 5 Min eine Offerte").

**Umfang für 2-4 Wochen:**
- `mobile.py` + kleine **PWA** (Service-Worker, manifest.json, offline-cache — passt zur "lokal & stdlib"-Philosophie, keine App-Store-Notwendigkeit)
- Foto aufnehmen → OCR (baut auf vision.py auf) → KI-Agent (lokal_ai.py) → Devis-Vorschlag
- Sprach-Eingabe (Web Speech API — keine Server-Kosten)
- "In 30 Sek. Offerte per WhatsApp" — nutzt vorhandenes whatsapp_bot.py

**Hebel:** Killer-Demo-Feature für Marketing-Videos. Konkurrenzlos in CH-KMU-Segment.

---

## Bonus-Gaps (kleinere, schnell mitzunehmen, <1 Woche)
| Lücke | Wettbewerber | Quick-Win-Modul |
|---|---|---|
| Mehrere Bilder pro Position (Baufortschritts-Fotos) | bauMax, Sorba | `position_media.py` |
| Abnahmeprotokoll & Mängelliste | Sorba, Bauwise | `abnahme.py` |
| Garantie-/Rückbehalts-Tracking über alle Projekte | bauMax | `garantie_tracker.py` (am Zahlungsplan angedockt — teilweise in zahlungsplan.py vorhanden, aber nicht projektübergreifend) |
| MwSt-Abrechnung & ESTV-Sammelbeleg-Export | Sorba | in `erp.py` teils vorhanden, aber nicht CH-ESTV-konformer XML-Export |
| Wissens-DB mit typischen Vorlagen (Bad-/Küchen-Renovation etc.) | — | `templates_bibliothek.py` (Vorlagen gibt's in templates.py — aber nur als einzelne Datei, keine kuratierte Bibliothek) |

---

## Realistische 2-4-Wochen-Priorisierung (was zuerst?)
1. **Killer-Feature 1: Rapport/Regie** — grösster operativer Schmerz, hebt DevisPro auf "Werkzeugkette"-Niveau
2. **Killer-Feature 7: Mobile Offerte (PWA)** — bestes Marketing-Feature, baut auf Vorhandenem
3. **Killer-Feature 5: Nachkalkulation/Soll-Ist** — der Bauwise-Killer
4. **Killer-Feature 2: Gantt** — SIA-Pflicht, fehlt komplett
5. **Killer-Feature 4: QES-Signatur** — Differenzierung gegen Gratis-Tools

Diese 5 sind in 4 Wochen realistisch (1 erfahrener Dev Vollzeit + Claude/AI-Hilfe für UI-Skelett). CRM (3) und SU-Vergabe (6) brauchen je 2-3 Wochen extra — eher 6-8 Wochen.

---

## STRATEGISCHE EMPFEHLUNG
DevisPro ist **technisch solide und breit** — die grösste Lücke ist nicht ein Modul, sondern die **fehlende Bindung an den Bauleitungs-Alltag**. Mit Rapport + Gantt + Nachkalkulation (Features 1, 2, 5) wird DevisPro vom "Preis-Tool" zum "Bauprojekt-Cockpit" — und das ist genau die Position, in der Bauwise heute Geld verdient. Die AI-Hooks (lokal_ai.py, agent.py, vision.py) sind bereits da und ungenutzt — jede dieser Erweiterungen kann sie nutzen, ohne neue Abhängigkeiten.