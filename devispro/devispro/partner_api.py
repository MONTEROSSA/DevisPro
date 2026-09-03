"""Partner API für ERP-Integration (Abacus, Proffix, SAP, etc.).
Embedded FastAPI + uvicorn Thread. White-Label 'DevisPro inside'.
"""
from __future__ import annotations
import os
import json
import threading
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# Optional imports
try:
    from fastapi import FastAPI, HTTPException, Depends, Request, status
    from fastapi.security import APIKeyHeader
    from fastapi.responses import HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = object
    HTTPException = Exception
    Depends = lambda x: x
    Request = object
    APIKeyHeader = object
    HTMLResponse = str
    CORSMiddleware = object
    uvicorn = None

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False) if FASTAPI_AVAILABLE else None

# API Keys speichern (data/partner_keys.json)
DATA_DIR = Path.home() / "Library" / "Application Support" / "DevisPro" / "data"
KEYS_FILE = DATA_DIR / "partner_keys.json"
RATE_LIMIT_FILE = DATA_DIR / "partner_ratelimit.json"

DEFAULT_RATE_LIMIT = 100  # requests per minute
RATE_WINDOW = 60  # seconds


@dataclass
class PartnerKey:
    key: str
    name: str
    partner: str  # "abacus", "proffix", "sap", "custom"
    created: str
    active: bool = True
    rate_limit: int = DEFAULT_RATE_LIMIT
    permissions: List[str] = None  # ["devis:read", "devis:write", "preise:sync", "webhook"]

    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ["devis:read", "preise:sync"]


def _load_keys() -> Dict[str, PartnerKey]:
    if KEYS_FILE.exists():
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: PartnerKey(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Fehler beim Laden Partner-Keys: {e}")
    return {}


def _save_keys(keys: Dict[str, PartnerKey]):
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {k: asdict(v) for k, v in keys.items()}
    tmp = KEYS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, KEYS_FILE)


def _check_rate_limit(key: str, limit: int) -> bool:
    """Einfaches In-Memory Rate Limiting (pro Minute)."""
    now = time.time()
    window_start = now - RATE_WINDOW
    
    if RATE_LIMIT_FILE.exists():
        try:
            with open(RATE_LIMIT_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}
    else:
        data = {}
    
    # Alte Einträge bereinigen
    if key in data:
        data[key] = [ts for ts in data[key] if ts > window_start]
    else:
        data[key] = []
    
    if len(data[key]) >= limit:
        return False
    
    data[key].append(now)
    
    try:
        with open(RATE_LIMIT_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass
    
    return True


def create_partner_key(name: str, partner: str, permissions: List[str] = None, rate_limit: int = DEFAULT_RATE_LIMIT) -> PartnerKey:
    """Erstellt neuen API Key für ERP-Partner."""
    import secrets
    key = f"dp_{partner}_{secrets.token_hex(16)}"
    pk = PartnerKey(
        key=key,
        name=name,
        partner=partner,
        created=datetime.now().isoformat(),
        rate_limit=rate_limit,
        permissions=permissions or ["devis:read", "preise:sync"],
    )
    keys = _load_keys()
    keys[key] = pk
    _save_keys(keys)
    return pk


def verify_api_key(api_key: str = Depends(API_KEY_HEADER)) -> PartnerKey:
    """FastAPI Dependency: Prüft API Key und Rate Limit."""
    if not FASTAPI_AVAILABLE:
        raise HTTPException(status_code=500, detail="FastAPI nicht installiert")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key erforderlich (Header: X-API-Key)")
    
    keys = _load_keys()
    if api_key not in keys:
        raise HTTPException(status_code=401, detail="Ungültiger API Key")
    
    pk = keys[api_key]
    if not pk.active:
        raise HTTPException(status_code=403, detail="API Key deaktiviert")
    
    if not _check_rate_limit(api_key, pk.rate_limit):
        raise HTTPException(status_code=429, detail="Rate Limit überschritten")
    
    return pk


def require_permission(perm: str):
    """Decorator für Permission-Check."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # PartnerKey aus kwargs extrahieren (wird von verify_api_key injiziert)
            pk = None
            for arg in args:
                if isinstance(arg, PartnerKey):
                    pk = arg
                    break
            if pk is None:
                for v in kwargs.values():
                    if isinstance(v, PartnerKey):
                        pk = v
                        break
            if pk and perm not in pk.permissions:
                raise HTTPException(status_code=403, detail=f"Permission '{perm}' erforderlich")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# FastAPI App erstellen
# ============================================================

def create_partner_app() -> "FastAPI":
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI/uvicorn nicht installiert. pip install fastapi uvicorn")
    
    app = FastAPI(
        title="DevisPro Partner API",
        description="ERP-Integration API für Abacus, Proffix, SAP, etc. — White-Label 'DevisPro inside'",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In Prod einschränken
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health Check
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "devispro-partner-api", "version": "1.0.0"}
    
    # --- Devis List ---
    @app.get("/api/v1/devis")
    @require_permission("devis:read")
    async def list_devis(pk: PartnerKey = Depends(verify_api_key)):
        """Listet alle Devis im lokalen DevisPro-Store."""
        from devispro.data_store import app_support_dir
        devis_dir = Path(app_support_dir()) / "devis"
        if not devis_dir.exists():
            return {"devis": [], "count": 0}
        results = []
        for dev_dir in sorted(devis_dir.iterdir()):
            if not dev_dir.is_dir():
                continue
            meta_file = dev_dir / "meta.json"
            if not meta_file.exists():
                continue
            try:
                with open(meta_file, encoding="utf-8") as f:
                    meta = json.load(f)
                # Betrag aus bepreist.sia lesen (letzte Position vor 99-Total)
                sia_file = dev_dir / "bepreist.sia"
                netto = meta.get("netto", 0.0)
                position_count = 0
                if sia_file.exists():
                    sia_text = sia_file.read_text(encoding="utf-8")
                    position_count = sia_text.count("\n1")  # Positionen starten mit "1"
                meta["position_count"] = position_count
                results.append(meta)
            except Exception as e:
                logger.warning(f"Devis {dev_dir.name} konnte nicht gelesen werden: {e}")
        return {"devis": results, "count": len(results)}

    # --- Devis Export ---
    @app.get("/api/v1/devis/{devis_id}/export")
    @require_permission("devis:read")
    async def export_devis(devis_id: str, pk: PartnerKey = Depends(verify_api_key)):
        """Exportiert fertiges Devis für ERP (Abacus/Proffix/SAP Format)."""
        from devispro.data_store import app_support_dir
        devis_dir = Path(app_support_dir()) / "devis" / devis_id
        if not devis_dir.exists():
            raise HTTPException(status_code=404, detail=f"Devis {devis_id} nicht gefunden")

        meta_file = devis_dir / "meta.json"
        sia_file = devis_dir / "bepreist.sia"
        if not meta_file.exists() or not sia_file.exists():
            raise HTTPException(status_code=404, detail=f"Devis-Daten unvollständig")

        try:
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
            sia_text = sia_file.read_text(encoding="utf-8")

            # SIA-451 Positionen parsen (vereinfachtes Format)
            positions = []
            for raw_line in sia_text.splitlines():
                # Position-Zeile beginnt mit "3" (berechnete Pos) — Format: 3NNNNNMengeEinheit
                if not raw_line.startswith("3"):
                    continue
                # Numerische Felder extrahieren (SIA-451 Festformat 16-Stellen)
                try:
                    # Pos-Nr (Stelle 1-16, 1-indexed), Menge (16-30), Ep (30-46), Total (46-62)
                    pos_nr = raw_line[0:16].strip()
                    menge_str = raw_line[16:30].strip()
                    einheit = raw_line[30:34].strip()
                    ep_str = raw_line[34:50].strip()
                    total_str = raw_line[50:66].strip()
                    menge = float(menge_str) / 10000 if menge_str else 0.0
                    ep = float(ep_str) / 100000 if ep_str else 0.0
                    total = float(total_str) / 100 if total_str else 0.0
                    positions.append({
                        "pos_nr": pos_nr,
                        "menge": menge,
                        "einheit": einheit,
                        "ep": ep,
                        "total": total,
                    })
                except (ValueError, IndexError):
                    continue

            summe_netto = sum(p["total"] for p in positions)
            mwst = summe_netto * 0.081  # CH MwSt 8.1%
            summe_brutto = summe_netto + mwst

            return {
                "devis_id": devis_id,
                "format": "erp_native",
                "status": "exported",
                "meta": meta,
                "data": {
                    "positions": positions,
                    "summe_netto": round(summe_netto, 2),
                    "mwst": round(mwst, 2),
                    "summe_brutto": round(summe_brutto, 2),
                },
            }
        except Exception as e:
            logger.error(f"Devis-Export fehlgeschlagen für {devis_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Export-Fehler: {e}")

    # --- Preis-Sync ---
    @app.post("/api/v1/preise/sync")
    @require_permission("preise:sync")
    async def sync_preise(request: Request, pk: PartnerKey = Depends(verify_api_key)):
        """Empfängt Preisliste von ERP (Artikel, Preise, Rabattgruppen)."""
        from devispro.data_store import PREISE_PATH
        data = await request.json()
        artikel = data.get("artikel", [])
        imported_count = 0

        try:
            # Bestehende CSV lesen
            existing = []
            if Path(PREISE_PATH).exists():
                with open(PREISE_PATH, encoding="utf-8") as f:
                    existing = [l.rstrip() for l in f.readlines()]

            # Neue Artikel anhängen (csv-append Modus)
            with open(PREISE_PATH, "a", encoding="utf-8") as f:
                for art in artikel:
                    art_nr = art.get("nr", "")
                    text = art.get("text", "").replace(",", ";")  # CSV-Schutz
                    einheit = art.get("einheit", "Stk")
                    preis = art.get("preis", 0.0)
                    row = f"{art_nr},{text},{einheit},{preis}"
                    if row not in existing:
                        f.write(row + "\n")
                        imported_count += 1

            return {
                "status": "synced",
                "received": len(artikel),
                "imported": imported_count,
                "skipped_duplicates": len(artikel) - imported_count,
            }
        except Exception as e:
            logger.error(f"Preis-Sync fehlgeschlagen: {e}")
            raise HTTPException(status_code=500, detail=f"Sync-Fehler: {e}")

    # --- Webhook: Devis finalisiert ---
    @app.post("/api/v1/webhook/devis_finalized")
    @require_permission("webhook")
    async def webhook_devis_finalized(request: Request, pk: PartnerKey = Depends(verify_api_key)):
        """Webhook wird aufgerufen wenn Devis in DevisPro finalisiert wird."""
        from devispro.data_store import path as ds_path
        data = await request.json()
        devis_id = data.get("devis_id")
        if not devis_id:
            raise HTTPException(status_code=400, detail="devis_id erforderlich")

        # ERP-Queue: Webhook-Daten persistent in der Partner-Queue speichern
        queue_path = Path(ds_path("partner_erp_queue.json"))
        try:
            queue = []
            if queue_path.exists():
                with open(queue_path, encoding="utf-8") as f:
                    queue = json.load(f)

            queue.append({
                "devis_id": devis_id,
                "partner": pk.partner,
                "partner_name": pk.name,
                "received_at": datetime.now().isoformat(),
                "payload": data,
                "forwarded": False,
            })

            with open(queue_path, "w", encoding="utf-8") as f:
                json.dump(queue, f, ensure_ascii=False, indent=2)

            logger.info(f"Webhook Devis finalisiert: {devis_id} von Partner {pk.name} (Queue: {len(queue)})")
            return {
                "status": "queued",
                "devis_id": devis_id,
                "queue_position": len(queue),
            }
        except Exception as e:
            logger.error(f"Webhook-Queue fehlgeschlagen: {e}")
            raise HTTPException(status_code=500, detail=f"Queue-Fehler: {e}")
    
    # --- Partner Key Management (Admin) ---
    @app.post("/api/v1/admin/keys")
    async def create_key(request: Request):
        """Erstellt neuen Partner Key (Admin only - separater Auth in Prod)."""
        data = await request.json()
        pk = create_partner_key(
            name=data.get("name", "Unbenannt"),
            partner=data.get("partner", "custom"),
            permissions=data.get("permissions"),
            rate_limit=data.get("rate_limit", DEFAULT_RATE_LIMIT),
        )
        return {"key": pk.key, "name": pk.name, "partner": pk.partner}
    
    @app.get("/api/v1/admin/keys")
    async def list_keys():
        keys = _load_keys()
        return {k: {"name": v.name, "partner": v.partner, "active": v.active, "created": v.created} 
                for k, v in keys.items()}
    
    @app.delete("/api/v1/admin/keys/{key}")
    async def revoke_key(key: str):
        keys = _load_keys()
        if key in keys:
            keys[key].active = False
            _save_keys(keys)
            return {"status": "revoked"}
        raise HTTPException(status_code=404, detail="Key nicht gefunden")
    
    # OpenAPI Spec Export
    @app.get("/openapi.json")
    async def openapi_spec():
        return app.openapi()
    
    return app


# ============================================================
# Embedded Server Thread
# ============================================================

class PartnerAPIServer:
    """Läuft als Daemon-Thread im DevisPro Prozess."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.app = None
        self.server = None
        self.thread = None
        self._running = False
    
    def start(self):
        if self._running:
            return
        if not FASTAPI_AVAILABLE:
            logger.warning("FastAPI nicht verfügbar — Partner API nicht gestartet")
            return
        
        self.app = create_partner_app()
        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self._running = True
        logger.info(f"Partner API gestartet auf http://{self.host}:{self.port}")
    
    def _run(self):
        import asyncio
        asyncio.run(self.server.serve())
    
    def stop(self):
        if self.server:
            self.server.should_exit = True
        self._running = False


# Globale Instanz
_partner_server: Optional[PartnerAPIServer] = None

def get_partner_server() -> PartnerAPIServer:
    global _partner_server
    if _partner_server is None:
        _partner_server = PartnerAPIServer()
    return _partner_server

def start_partner_api(host: str = "127.0.0.1", port: int = 8765):
    """Startet Partner API (aus DevisPro main/app_gui.py aufrufen)."""
    global _partner_server
    _partner_server = PartnerAPIServer(host, port)
    _partner_server.start()
    return _partner_server

def stop_partner_api():
    global _partner_server
    if _partner_server:
        _partner_server.stop()
        _partner_server = None


# Test
if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        print("FastAPI verfügbar — Starte Test-Server auf :8765")
        server = start_partner_api()
        try:
            import time
            time.sleep(2)
            import requests
            r = requests.get("http://127.0.0.1:8765/health")
            print(f"Health: {r.json()}")
            
            # Key erstellen
            pk = create_partner_key("Test Partner", "abacus", ["devis:read", "preise:sync", "webhook"])
            print(f"Key: {pk.key}")
            
            # Test mit Key
            r = requests.get("http://127.0.0.1:8765/api/v1/devis/123/export", headers={"X-API-Key": pk.key})
            print(f"Export: {r.json()}")
        except Exception as e:
            print(f"Test Fehler: {e}")
        finally:
            stop_partner_api()
    else:
        print("FastAPI nicht installiert: pip install fastapi uvicorn")