DevisPro – SIA-451 Devis automatisch bepreisen
===============================================
Ein Produkt der Monterossa AG · info@monterossa.ch · devispro.de

INHALT
------
DevisPro ist die schweizerische Komplettlösung für Bauleistungs-Devis.
Es liest Ausschreibungen in vielen Formaten, bepreist sie automatisch
mit Ihren Richtpreisen, erstellt Offerte/Rechnung mit Swiss-QR und
exportiert in gängige Buchhaltungssysteme.

FUNKTIONEN (Überblick)
----------------------
• Ordner-Import: ganzer Projektordner → komplettes Devis (SIA-451/Sorba,
  Bauweb/Daedalus, CSV/Excel, GAEB, ÖNORM, XRechnung; Bilder/PDF via OCR
  sofern tessseract installiert).
• Bepreisung: automatischer Abgleich mit Richtpreisliste, inkl.
  Konfidenz und «manuelle Prüfung nötig»-Flag.
• Angebot & Rechnung: echtes PDF ohne Zusatzprogramm, inkl. Zahlungsplan.
• Swiss-QR: einzahlen.bar / PostFinance / Bank (gesetzeskonform).
• 26 Kantone: kantonale Aufschläge (NPK) + Marktpreis-Benchmark.
• Mehrwährung: CHF → EUR/USD/GBP (SNB/EZB-Kurse, sicherer Offline-Fallback).
• Buchhaltungs-Export: Abacus, Proffix, BMD, DATEV, Banana, SAP,
  Lexoffice, SevDesk, WinOffice, RamCO, Mobit, Kleinvieh, CSV/Excel/XML.
• ERP-API: HMAC-signierter REST-Push an Abacus/Proffix/andere.
• Subunternehmer-Marge: Marge pro Position (Verkauf − Sub-Kosten).
• Margen-Copilot: Marktpreis-Vergleich, flaggt zu tiefe/hoche Kalkulation.
• Marketing-Assistent: Social Posts, Ausschreibungs-Anschreiben, Referenz-PDF.
• WhatsApp-Bot: klick-freier Angebotstext + Deep-Link.
• Wiederkehrende Rechnungen, Mahnwesen, Team & Rollen, Offline-Sync.
• Backup & Wiederherstellung: integritätsgesicherte ZIP aller Kundendaten.
• KI-Agent: lokaler, offline Assistent für Fragen und Aktionen
  (MWST/Kanton ändern, Export, Währung, Marketing, Devis öffnen).

START (macOS)
-------------
Doppelklick auf «DevisPro_Installer_Mac.command» (oder «start_devispro.command»).
DevisPro startet auf http://localhost:5070 und öffnet den Browser.

START (Windows)
---------------
Python 3.8+ von python.org installieren (Häkchen bei «Add Python to PATH»).
Dann Doppelklick auf «install_windows.bat» (oder «start_devispro.bat»).
DevisPro läuft auf http://localhost:5070.

START (Linux / Terminal)
------------------------
  python -m devispro        # startet die Web-Oberfläche auf Port 5070
  python install_kmu.py     # prüft Python, erstellt Launcher, startet

ERSTEINRICHTUNG
---------------
Beim ersten Start: Menü «Setup» → Betrieb, Gewerk, Kanton, MWST und
optional Ihre Richtpreis-CSV erfassen (2 Minuten). Danach sofort produktiv.

COMMAND-LINE (headless, für Automation)
----------------------------------------
  python -m devispro.cli --help
  python -m devispro.cli waehrung --betrag 5000 --ziel EUR
  python -m devispro.cli backup --label tagesbackup
  python -m devispro.cli ordner --ordner ./mein_projekt --output devis.sia
  python -m devispro.cli export --input devis.sia --system abacus --output b.csv
  python -m devispro.cli agent "setze MWST auf 7.7"

LIZENZ & PREIS
--------------
2'400 CHF einmalig + 990 CHF/Jahr (Wartung, Updates, Benchmark-Netzwerk).
3 Monate Pilot gratis, danach 500 CHF Rabatt. Lizenz lokal beim KMU,
jährlicher Freischalt-Code vom Anbieter (ohne Code unbrauchbar).
Support: info@monterossa.ch

DATENSCHUTZ
-----------
Alles läuft lokal auf Ihrem Rechner. Keine Daten verlassen das Gerät.
SMTP-Zugangsdaten liegen nur in data/smtp.json (nicht im Code).

TESTS
-----
  python3 tests/run_tests.py   (reine Stdlib, keine externen Abhängigkeiten)

© Monterossa AG. Alle Rechte vorbehalten.
