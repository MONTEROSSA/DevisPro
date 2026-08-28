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
    
    # --- Devis Export ---
    @app.get("/api/v1/devis/{devis_id}/export")
    @require_permission("devis:read")
    async def export_devis(devis_id: str, pk: PartnerKey = Depends(verify_api_key)):
        """Exportiert fertiges Devis für ERP (Abacus/Proffix/SAP Format)."""
        # TODO: Echte Devis-Ladung aus DevisPro Daten
        # Hier Mock-Response
        return {
            "devis_id": devis_id,
            "format": "erp_native",
            "status": "exported",
            "data": {
                "positions": [
                    {"pos_nr": "0901.010", "text": "Betonabbruch", "menge": 45, "einheit": "m2", "ep": 85.0, "total": 3825.0},
                ],
                "summe_netto": 3825.0,
                "mwst": 310.0,
                "summe_brutto": 4135.0,
            }
        }
    
    # --- Preis-Sync ---
    @app.post("/api/v1/preise/sync")
    @require_permission("preise:sync")
    async def sync_preise(request: Request, pk: PartnerKey = Depends(verify_api_key)):
        """Empfängt Preisliste von ERP (Artikel, Preise, Rabattgruppen)."""
        data = await request.json()
        artikel = data.get("artikel", [])
        # TODO: In meine_preise.csv importieren
        return {"status": "synced", "received": len(artikel), "imported": len(artikel)}
    
    # --- Webhook: Devis finalisiert ---
    @app.post("/api/v1/webhook/devis_finalized")
    @require_permission("webhook")
    async def webhook_devis_finalized(request: Request, pk: PartnerKey = Depends(verify_api_key)):
        """Webhook wird aufgerufen wenn Devis in DevisPro finalisiert wird."""
        data = await request.json()
        # TODO: An ERP weiterleiten / Queue
        logger.info(f"Webhook Devis finalisiert: {data.get('devis_id')} von Partner {pk.name}")
        return {"status": "received", "devis_id": data.get("devis_id")}
    
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