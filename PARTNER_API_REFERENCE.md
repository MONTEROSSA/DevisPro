# DevisPro Partner-API — Technische Referenz für ERP-Integratoren

**Version:** 1.5.0
**Base URL:** `http://localhost:8765` (lokal) oder via Cloud-Sync-Tunnel
**Authentifizierung:** API-Key (X-API-Key Header)

---

## Übersicht

Die DevisPro Partner-API ist ein **FastAPI-basierter** REST-Endpunkt der Devis-Daten für ERP-Systeme und externe Tools bereitstellt.

**Use Cases:**
- ERP-Systeme (Abacus, Proffix, SAP) lesen Devis automatisch aus
- Web-Shops zeigen Echtzeit-Preise aus DevisPro
- Mobile Apps greifen auf Devis-Daten zu
- Buchhaltungs-Software importiert Rechnungen

**Starten der API:**
```bash
python -m devispro.partner_api
# API laeuft auf http://localhost:8765
```

**OpenAPI-Spec:** `http://localhost:8765/docs` (Swagger UI)

---

## Authentifizierung

Alle geschützten Endpoints erfordern einen **API-Key** im Header:

```http
GET /api/v1/devis HTTP/1.1
Host: localhost:8765
X-API-Key: dp_test_aabbccddeeff00112233445566778899
```

### API-Key erstellen (Admin)

```http
POST /api/v1/admin/keys
Content-Type: application/json

{
  "name": "ERP Integration Abacus",
  "partner": "abacus-import",
  "permissions": ["devis:read", "preise:sync", "webhook"]
}
```

**Response:**
```json
{
  "key": "dp_live_aabbccddeeff00112233445566778899",
  "name": "ERP Integration Abacus",
  "partner": "abacus-import",
  "permissions": ["devis:read", "preise:sync", "webhook"],
  "created_at": "2026-09-04T18:30:00Z"
}
```

⚠️ **Wichtig:** Den API-Key nur einmalig zurückgeben. Speichern Sie ihn sicher (Vault, env-Variable).

### Permissions

| Permission | Beschreibung |
|-------------|--------------|
| `devis:read` | Devis lesen (list, export) |
| `preise:sync` | Preise synchronisieren (POST /api/v1/preise/sync) |
| `webhook` | Webhooks empfangen (POST /api/v1/webhook/*) |
| `admin:keys` | API-Keys verwalten (nur für interne Tools) |

---

## Endpoints

### Health Check

**GET /health**

```bash
curl http://localhost:8765/health
```

**Response 200:**
```json
{
  "status": "ok",
  "service": "devispro-partner-api",
  "version": "1.5.0"
}
```

### Devis auflisten

**GET /api/v1/devis**

```bash
curl -H "X-API-Key: dp_live_abc..." http://localhost:8765/api/v1/devis
```

**Query-Parameter:**
- `limit` (int, default 100) — Max Anzahl Devis
- `offset` (int, default 0) — Pagination
- `kunde` (str, optional) — Filter nach Kunden-Name
- `branche` (str, optional) — Filter nach Branche (Maler, Sanitär, etc.)
- `datum_von` (ISO date, optional) — Filter ab Datum
- `datum_bis` (ISO date, optional) — Filter bis Datum

**Response 200:**
```json
{
  "devis": [
    {
      "id": "devis_0001",
      "name": "Badezimmer-Renovation",
      "datum": "2026-09-04",
      "kunde": "Bauunternehmung XY AG",
      "netto": 9449.50,
      "status": "bepreist"
    },
    ...
  ],
  "count": 36,
  "total": 36,
  "limit": 100,
  "offset": 0
}
```

### Devis-Export

**GET /api/v1/devis/{devis_id}/export**

```bash
curl -H "X-API-Key: dp_live_abc..." \
     http://localhost:8765/api/v1/devis/devis_0001/export
```

**Response 200 (mit M16 DevisPro-Parser):**
```json
{
  "devis_id": "devis_0001",
  "format": "devispro_sia",
  "status": "bepreist",
  "meta": {
    "project_id": "D0001",
    "project_name": "EFH Muster",
    "devis_nr": "A001",
    "date": "2026-09-04",
    "currency": "CHF"
  },
  "data": {
    "positions": [
      {
        "pos_nr": "1111000000000",
        "text": "Innenanstrich Wand 2 Anstriche",
        "menge": 65.0,
        "einheit": "m2",
        "ep": 42.50,
        "total": 2762.50
      },
      ...
    ],
    "summe_netto": 9449.50,
    "mwst": 765.41,
    "summe_brutto": 10214.91
  }
}
```

**Response 404 (Devis nicht gefunden):**
```json
{
  "detail": "Devis devis_9999 nicht gefunden"
}
```

### Preise synchronisieren

**POST /api/v1/preise/sync**

Synchronisiert Preise aus einem ERP zurück in DevisPro (z.B. Artikel-Stamm).

```bash
curl -X POST \
     -H "X-API-Key: dp_live_abc..." \
     -H "Content-Type: application/json" \
     -d '{
       "artikel": [
         {"nr": "AB-001", "text": "WC Standard", "einheit": "Stk", "preis": 1450.00},
         {"nr": "AB-002", "text": "Waschbecken", "einheit": "Stk", "preis": 1180.00}
       ]
     }' \
     http://localhost:8765/api/v1/preise/sync
```

**Response 200:**
```json
{
  "received": 2,
  "imported": 2,
  "duplicates": 0,
  "errors": [],
  "status": "synced",
  "file": "meine_preise.csv"
}
```

**Deduplication:** Artikel mit gleicher `nr` werden nicht erneut importiert.

### Webhook: Devis finalized

**POST /api/v1/webhook/devis_finalized**

Wird von DevisPro aufgerufen wenn ein Devis bepreist/finalisiert wird. Externe Systeme (z.B. ERP) können dann reagieren.

**Beispiel-Request (DevisPro → ERP):**
```json
{
  "devis_id": "devis_0001",
  "kunde": "Bauunternehmung XY AG",
  "betrag": 9449.50,
  "mwst": 765.41,
  "brutto": 10214.91,
  "timestamp": "2026-09-04T18:30:00Z"
}
```

**Response 200:**
```json
{
  "status": "queued",
  "devis_id": "devis_0001",
  "queue_position": 1
}
```

Die Webhooks werden in `~/Library/Application Support/DevisPro/data/partner_erp_queue.json` persistiert (für Robustheit bei ERP-Ausfall).

---

## Code-Beispiele

### Python (mit `httpx`)

```python
import httpx

API_KEY = "dp_live_abc..."
BASE_URL = "http://localhost:8765"

with httpx.Client(base_url=BASE_URL, headers={"X-API-Key": API_KEY}) as client:
    # Devis auflisten
    response = client.get("/api/v1/devis")
    devis_list = response.json()["devis"]

    # Erstes Devis exportieren
    first_id = devis_list[0]["id"]
    response = client.get(f"/api/v1/devis/{first_id}/export")
    export = response.json()

    # Preise syncen
    response = client.post("/api/v1/preise/sync", json={
        "artikel": [
            {"nr": "NEU-001", "text": "Neuer Artikel", "einheit": "Stk", "preis": 99.50}
        ]
    })
    print(response.json())
```

### JavaScript (Browser/Node.js)

```javascript
const API_KEY = 'dp_live_abc...';
const BASE_URL = 'http://localhost:8765';

async function listDevis() {
  const response = await fetch(`${BASE_URL}/api/v1/devis`, {
    headers: { 'X-API-Key': API_KEY }
  });
  return await response.json();
}

async function exportDevis(id) {
  const response = await fetch(`${BASE_URL}/api/v1/devis/${id}/export`, {
    headers: { 'X-API-Key': API_KEY }
  });
  return await response.json();
}
```

### cURL

```bash
# Devis auflisten
curl -H "X-API-Key: dp_live_abc..." http://localhost:8765/api/v1/devis

# Devis exportieren
curl -H "X-API-Key: dp_live_abc..." \
     http://localhost:8765/api/v1/devis/devis_0001/export

# Preise synchronisieren
curl -X POST \
     -H "X-API-Key: dp_live_abc..." \
     -H "Content-Type: application/json" \
     -d '{"artikel":[{"nr":"X1","text":"Test","einheit":"Stk","preis":99.50}]}' \
     http://localhost:8765/api/v1/preise/sync
```

---

## Fehlerbehandlung

### HTTP-Status-Codes

| Code | Bedeutung | Beispiel |
|------|-----------|----------|
| 200 | OK | Erfolgreicher Request |
| 401 | Unauthorized | API-Key fehlt oder ungültig |
| 403 | Forbidden | Permission fehlt |
| 404 | Not Found | Devis existiert nicht |
| 422 | Validation Error | Pflichtfeld fehlt |
| 500 | Server Error | Interner Fehler |

### Error-Response-Format

```json
{
  "detail": "Devis devis_9999 nicht gefunden"
}
```

### Best Practices

1. **API-Key rotieren** alle 90 Tage
2. **HTTPS** verwenden in Produktion (TLS-Proxy vorschalten)
3. **Rate-Limiting** beachten (max 100 Requests/Min)
4. **Webhook-Queue** regelmäßig pollen (falls ERP offline war)
5. **Logs** mit Correlation-IDs führen (Header: `X-Request-ID`)

---

## Sicherheit

### Empfehlungen

1. **API-Key niemals im Code hardcoden** — nutze env-Variablen
2. **HTTPS** in Produktion (nicht HTTP)
3. **Least Privilege** — nur die Permissions anfordern die gebraucht werden
4. **Audit-Log** regelmäßig prüfen (alle API-Calls werden geloggt)
5. **Rate-Limiting** auf Client-Seite (Backoff bei 429)

### Bedrohungsmodell

- **Vertraulichkeit:** API-Key ist wie ein Passwort zu behandeln
- **Integrität:** HMAC-SHA256-signierte Webhooks (geplant für v1.6)
- **Verfügbarkeit:** Lokale API läuft nur wenn DevisPro läuft

### Compliance

- **DSGVO:** Alle Daten lokal, API-Key-Aktivität im Audit-Log
- **DSG:** Audit-Log 10 Jahre aufbewahrt (Schweizer Standard)
- **ISO 27001:** Backups verschlüsselt, Compliance-Lücken dokumentiert

---

## Changelog

### v1.5.0 (Sep 2026)
- **M16:** DevisPro-Format-Parser (echte bepreist.sia lesen)
- **M18:** DevisPro-Export (Round-Trip-fähig)
- Neue Endpoints: `GET /api/v1/devis/{id}/export`
- Permissions-System eingeführt
- Audit-Log für alle API-Calls

### v1.0.0 (Aug 2026)
- Initiale API
- 4 Endpoints: list, export, sync, webhook

---

**© 2026 Monterossa · DevisPro Partner-API v1.5 · Made in Switzerland 🇨🇭**
