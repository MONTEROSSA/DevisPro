# M9: DevisPro v1.4.0 Konsolidierung (Sep 2026)

## Stand
- Bundle ~/Desktop/DevisPro.app: 284 Module (vs. v1.0 mit nur 89)
- Version: 1.4.0 (Info.plist aktualisiert)
- 4 Moats integriert: verbaende_kataloge (M1), marketplace (M2), cloud_sync (M3), erp_ecosystem (M4)
- Repo HEAD: 2cec012 (M8.2) + M9 Notes

## Mac-Sign-Way
- Lokal (~/devis-auto/DevisPro_sign_fix.command): ad-hoc only wegen Apple Trust Eval blockiert
- GitHub Actions (build-deploy-mac.yml): voller Developer-ID + Notarize Workflow sobald MAC_CERT_P12_BASE64 Secret gesetzt
- Live ZIP deployed: https://devispro.de/DevisPro-2026-09-03-adhoc.zip

## Cron-Jobs (21 aktiv)
- Vor Sep 2026: 9/19 kaputt wegen google/gemini-2.0-flash-exp:free + qwen-2.5-72b-instruct tot
- Fix: model.default = minimax/minimax-m3:free (Datei: ~/.hermes/cron/jobs.json direkt editiert)
- Smoke-Test: Kunden-Scott Job 6bb7a29d1f4c — ok

## Landingpage
- Live: /var/www/devispro/index.html (auf VPS, separater Editor)
- Neue Vorlage: ~/devis-auto/index_v140.html (v1.4.0, 4 Profit-Module)
- Telefonnummer: +41 41 534 48 90 (war Platzhalter in alter Version)
