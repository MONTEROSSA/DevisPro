# DevisPro – Kurzanleitung für das KMU (Schweizer Bau-Betrieb)

## Was ist DevisPro?
DevisPro bepreist Bau-Devis aus **allen gängigen Formaten** automatisch mit
deinen Richtpreisen – inkl. kantonalem Preisfaktor. Pro Devis in rund 1 Minute
statt 2 Stunden von Hand.

**Unterstützte Import-Formate:**
- **SIA-451 / Sorba** (`.sia`) – CH-Standard
- **Bauweb / Daedalus** (`.csv`) – CH-Ausschreibungsportale
- **Generisches CSV / Excel** (`.csv`, `.xlsx`) – deine eigenen Spalten
- **GAEB D84** (`.xml`) – Deutschland
- **ÖNORM B 2063** (`.csv`) – Österreich
- **XRechnung / ZUGFeRD** (`.xml`) – EU-Rechnungsstandard

Das Format wird **automatisch erkannt** – du wählst einfach die Datei.

## 1 · Starten
Das Programm läuft lokal auf dem Mac (keine Cloud, keine Kundendaten verlassen
den Betrieb). Im Terminal einmalig:

    cd /Users/ferdinandrothlisberger/devis-auto
    python3 webui.py

Oder bequem: `DevisPro_Installer_Mac.command` doppelklicken.
Dann im Browser öffnen:  http://localhost:5070

## 2 · Einrichten (einmalig)
Oben im Menü → **Stammdaten**:
- Betrieb, Gewerk, Kanton, Stundenlohn, Aufschläge, MwSt eintragen → speichern.
- **Richtpreisliste** hochladen (CSV oder Excel):
  - CSV: Spalten `artikel_id;bezeichnung;npk;einheit;ep_chf;kategorie`
  - Excel: nimm die Vorlage `data/vorlage_richtpreise.xlsx`, fülle deine
    Preise ein, lade sie hoch.
- Danach siehst du die Liste und kannst einzelne Preise direkt ändern (✓)
  oder Zeilen löschen (🗑) – ganz ohne neuen Upload.

## 3 · Devis importieren & bepreisen
Oben im Menü → **📁 Meine Devis** → **Devis importieren**.
- Datei in einem der oben genannten Formate wählen → «Import starten».
- **Oder:** Devis abfotografieren und als Bild hochladen – DevisPro extrahiert die
  Positionen (OCR) oder zeigt ein geführtes Formular zur Bestätigung.
- Devis wird automatisch geparst + bepreist und landet in der Historie.
- Unsichere Treffer sind markiert (🔒) – diese einmal von Hand korrigieren.
- **Margen-Copilot** prüft jede Position auf Auffälligkeiten (EP=0, Verlust, Dublette)
  und zeigt sie rot/gelb an.
- **Marktpreis-Benchmark:** bei jeder Position siehst du ▼/●/▲ – ob dein Preis unter,
  im oder über Markt liegt (anonym, Netzwerkeffekt).
- Pro Devis: **Swiss QR-Rechnung** anzeigen, **Offert-PDF**, **Sorba-Export**.

## 3b · Gratis Devis-Check (ohne Login)
Auf devispro.ch → **🔍 Gratis Devis-Check**. Devis hochladen, in 30 Sekunden siehst
du anonym die 3 Positionen mit Margen-Risiko. Perfekt, um DevisPro unverbindlich
kennenzulernen – kein Account nötig.

## 4 · Bisherige Devis wiederfinden
Oben im Menü → **📁 Meine Devis**.
Jedes bepreiste Devis wird automatisch gespeichert (Datum, Netto, Kanton,
Status). Dort kannst du es später erneut **ansehen**, die **Offerte** drucken,
die **Sorba-Datei** herunterladen, die **QR-Rechnung** öffnen, als
**freigegeben** markieren oder **löschen**.

## 5 · Swiss QR-Rechnung
Pro Devis erzeugt DevisPro automatisch eine **QR-Rechnung** im offiziellen
Schweizer Format (SPC-0200) – inkl. deiner IBAN, Betrag und Referenz.
Direkt an die CH-Bank versendbar, kein separates Tool nötig.

## 6 · Sprache
Oben rechts DE · FR · IT umschalten. Die Wahl bleibt im Browser gespeichert
(Cookie) und gilt für die ganze App.

## 7 · Lizenz
Ohne gültigen Jahres-Code ist DevisPro gesperrt. Code eingeben unter
**Lizenz** (kommt automatisch nach Zahlungseingang per E-Mail von Monterossa AG).

## Support
Anbieter-Login oben → «Anbieter» (nur für DevisPro-Support / Monterossa AG).

---
Hinweis: Die Demo-Server laufen zusätzlich auf :5091 und :5092 (selber Stand).
Produktiv nutzt der KMU den Port 5070.

**Hersteller:** Monterossa AG · info@monterossa.ch · devispro.ch

---

## 8 · Warum DevisPro ein Verkaufshit ist (für Beratung / Verkauf)
1. **Margen-Copilot** schützt vor teuren Fehlern: EP=0, Verlust, Dublette, unplausible
   Mengen werden im Devis rot/gelb markiert – bevor sie zum Kunden gehen.
2. **Marktpreis-Benchmark** zeigt anonym, ob deine Kalkulation unter Markt liegt (▼/●/▲).
   Du verhandelst mit Fakten statt Bauchgefühl.
3. **Gratis Devis-Check** auf devispro.ch: KMU prüfen ein Devis in 30 Sek. ohne Login
   und testen 3 Monate gratis – der niedrigschwelligste Einstieg am Markt.
4. **Alle Formate** aus einer Hand: SIA-451/Sorba, Bauweb, CSV/Excel, GAEB (DE),
   ÖNORM (AT), XRechnung (EU) + Swiss QR-Rechnung – keine Medienbrüche mehr.

**Version 1.2.0**
