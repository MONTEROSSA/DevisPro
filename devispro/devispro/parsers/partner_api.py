"""Partner API MVP: FastAPI App für ERP-Partner-Channel.

Endpoints:
- GET  /api/v1/devis/{id}/export     -> SIA-451 Export
- POST /api/v1/preise/sync           -> Preise von Partner empfangen
- POST /api/v1/webhook/devis_finalized -> Webhook wenn Devis finalisiert

Auth: API-Key Header (X-API-Key)
Rate-Limit: 100 req/min pro API-Key
"""

from __future__ import annotations
import json
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn


# ============================================================
# In-Memory Storage (MVP - später DB)
# ============================================================

@dataclass
class Partner:
    api_key: str
    name: str
    email: str
    rate_limit: int = 100  # req/min
    created_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True


@dataclass
class DevisRecord:
    id: str
    partner_id: str
    original_path: str
    priced_path: Optional[str] = None
    status: str = "imported"  # imported, priced, exported, finalized
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    meta: dict = field(default_factory=dict)


@dataclass
class PriceSyncRequest:
    devis_id: str
    positions: list[dict]  # [{pos_nr, ep, betrag, ...}]
    partner_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


# In-Memory Stores
PARTNERS: dict[str, Partner] = {}
DEVIS_STORE: dict[str, DevisRecord] = {}
PRICE_SYNC_LOG: list[PriceSyncRequest] = []

# Rate Limiting: {api_key: [(timestamp, count), ...]}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 100
_rate_buckets: dict[str, list[tuple[float, int]]] = {}


# ============================================================
# Demo Partner registrieren
# ============================================================

def register_demo_partner() -> Partner:
    """Registriert Demo-Partner für Tests."""
    api_key = "demo-partner-key-12345"
    partner = Partner(
        api_key=api_key,
        name="Demo ERP AG",
        email="api@demo-erp.ch",
        rate_limit=100,
    )
    PARTNERS[api_key] = partner
    return partner


DEMO_PARTNER = register_demo_partner()


# ============================================================
# Rate Limiting
# ============================================================

def check_rate_limit(api_key: str) -> bool:
    """Prüft Rate-Limit für API-Key. Returns True wenn OK."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    if api_key not in _rate_buckets:
        _rate_buckets[api_key] = []
    
    # Alte Einträge entfernen
    _rate_buckets[api_key] = [
        (ts, cnt) for ts, cnt in _rate_buckets[api_key] if ts > window_start
    ]
    
    # Aktuelle Count
    current_count = sum(cnt for _, cnt in _rate_buckets[api_key])
    
    partner = PARTNERS.get(api_key)
    limit = partner.rate_limit if partner else RATE_LIMIT_MAX
    
    if current_count >= limit:
        return False
    
    # Bucket hinzufügen
    _rate_buckets[api_key].append((now, 1))
    return True


def get_rate_limit_info(api_key: str) -> dict:
    """Gibt Rate-Limit Info zurück für Header."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    
    if api_key not in _rate_buckets:
        return {"limit": RATE_LIMIT_MAX, "remaining": RATE_LIMIT_MAX, "reset": int(now + RATE_LIMIT_WINDOW)}
    
    current = sum(cnt for ts, cnt in _rate_buckets[api_key] if ts > window_start)
    partner = PARTNERS.get(api_key)
    limit = partner.rate_limit if partner else RATE_LIMIT_MAX
    
    return {
        "limit": limit,
        "remaining": max(0, limit - current),
        "reset": int(now + RATE_LIMIT_WINDOW)
    }


# ============================================================
# Auth Dependency
# ============================================================

async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    request: Request = None,
) -> Partner:
    """Validiert API-Key und prüft Rate-Limit."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    
    partner = PARTNERS.get(x_api_key)
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    
    if not partner.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key deactivated",
        )
    
    # Rate Limit prüfen
    if not check_rate_limit(x_api_key):
        info = get_rate_limit_info(x_api_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": str(info["remaining"]),
                "X-RateLimit-Reset": str(info["reset"]),
            },
        )
    
    # Rate-Limit Headers setzen
    if request:
        info = get_rate_limit_info(x_api_key)
        request.state.rate_limit = info
    
    return partner


# ============================================================
# Pydantic Models
# ============================================================

class DevisExportResponse(BaseModel):
    devis_id: str
    download_url: str
    expires_at: datetime
    positions_count: int


class PriceSyncPayload(BaseModel):
    devis_id: str = Field(..., description="Devis-ID aus DevisPro")
    positions: list[dict] = Field(..., description="Liste bepreister Positionen")
    # Erwartete Keys pro Position: pos_nr, ep, betrag, menge, einheit, text (optional)


class PriceSyncResponse(BaseModel):
    success: bool
    devis_id: str
    synced_positions: int
    errors: list[str] = []


class WebhookPayload(BaseModel):
    devis_id: str
    event: str = "devis_finalized"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict = {}


class WebhookResponse(BaseModel):
    received: bool
    devis_id: str


class ErrorResponse(BaseModel):
    detail: str
    code: str


# ============================================================
# FastAPI App
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[Partner API] Starting up...")
    # Demo-Daten laden falls vorhanden
    yield
    # Shutdown
    print("[Partner API] Shutting down...")


app = FastAPI(
    title="DevisPro Partner API",
    description="API für ERP-Partner: SIA-451 Export, Preis-Sync, Webhooks",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS für Partner-Portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Prod: spezifische Domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate-Limit Headers Middleware
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    if hasattr(request.state, "rate_limit"):
        info = request.state.rate_limit
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
    return response


# ============================================================
# Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0", "partners": len(PARTNERS)}


@app.get("/api/v1/devis/{devis_id}/export", response_model=DevisExportResponse)
async def export_devis(
    devis_id: str,
    partner: Partner = Depends(verify_api_key),
):
    """Exportiert Devis als SIA-451 Datei für Partner."""
    record = DEVIS_STORE.get(devis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {devis_id} nicht gefunden",
        )
    
    # Partner-Prüfung: Partner darf nur eigene Devisse exportieren
    if record.partner_id != partner.api_key and partner.api_key != DEMO_PARTNER.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen Devis",
        )
    
    # Für MVP: Datei existiert bereits (priced_path) oder wird on-the-fly generiert
    if record.priced_path and Path(record.priced_path).exists():
        file_path = record.priced_path
    else:
        # Fallback: Original-Datei zurückgeben (unbepreist)
        file_path = record.original_path
    
    if not Path(file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export-Datei nicht verfügbar",
        )
    
    # Temporäre Download-URL (in Prod: signed S3 URL)
    download_token = str(uuid.uuid4())[:8]
    download_url = f"/api/v1/download/{download_token}"
    # In-memory mapping für Demo
    app.state.downloads = getattr(app.state, "downloads", {})
    app.state.downloads[download_token] = file_path
    
    return DevisExportResponse(
        devis_id=devis_id,
        download_url=download_url,
        expires_at=datetime.utcnow() + timedelta(hours=1),
        positions_count=record.meta.get("positions_count", 0),
    )


@app.get("/api/v1/download/{token}")
async def download_file(token: str):
    """Temporärer Datei-Download (Demo)."""
    downloads = getattr(app.state, "downloads", {})
    file_path = downloads.get(token)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Download abgelaufen oder nicht gefunden")
    
    # Nach Download löschen (One-Time)
    del downloads[token]
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=Path(file_path).name,
    )


@app.post("/api/v1/preise/sync", response_model=PriceSyncResponse)
async def sync_prices(
    payload: PriceSyncPayload,
    partner: Partner = Depends(verify_api_key),
):
    """Empfängt bepreiste Positionen vom ERP-Partner."""
    record = DEVIS_STORE.get(payload.devis_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Devis {payload.devis_id} nicht gefunden",
        )
    
    # Partner-Prüfung
    if record.partner_id != partner.api_key and partner.api_key != DEMO_PARTNER.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf diesen Devis",
        )
    
    errors = []
    synced = 0
    
    for pos_data in payload.positions:
        pos_nr = pos_data.get("pos_nr")
        ep = pos_data.get("ep")
        betrag = pos_data.get("betrag")
        
        if not pos_nr:
            errors.append("Position ohne pos_nr übersprungen")
            continue
        
        if ep is None:
            errors.append(f"Position {pos_nr}: ep fehlt")
            continue
        
        # In MVP: Loggen, echtes Update würde Devis-Objekt modifizieren
        PRICE_SYNC_LOG.append(PriceSyncRequest(
            devis_id=payload.devis_id,
            positions=[pos_data],
            partner_id=partner.api_key,
        ))
        synced += 1
    
    # Status aktualisieren
    record.status = "priced"
    record.updated_at = datetime.utcnow()
    record.meta["last_price_sync"] = datetime.utcnow().isoformat()
    record.meta["synced_positions"] = synced
    
    return PriceSyncResponse(
        success=len(errors) == 0,
        devis_id=payload.devis_id,
        synced_positions=synced,
        errors=errors,
    )


@app.post("/api/v1/webhook/devis_finalized", response_model=WebhookResponse)
async def webhook_devis_finalized(
    payload: WebhookPayload,
    partner: Partner = Depends(verify_api_key),
):
    """Webhook: Wird aufgerufen wenn Partner Devis finalisiert hat."""
    record = DEVIS_STORE.get(payload.devis_id)
    if not record:
        # Webhook für unbekannten Devis - trotzdem akzeptieren (idempotent)
        pass
    else:
        # Partner-Prüfung
        if record.partner_id != partner.api_key and partner.api_key != DEMO_PARTNER.api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Kein Zugriff auf diesen Devis",
            )
        
        record.status = "finalized"
        record.updated_at = datetime.utcnow()
        record.meta["finalized_at"] = payload.timestamp.isoformat()
        record.meta["finalized_by"] = partner.name
    
    return WebhookResponse(received=True, devis_id=payload.devis_id)


# ============================================================
# Admin / Management Endpoints (für DevisPro intern)
# ============================================================

@app.post("/admin/devis/register")
async def register_devis(
    original_path: str,
    partner_api_key: str = DEMO_PARTNER.api_key,
    meta: Optional[dict] = None,
):
    """Registriert neuen Devis für Partner-Export (interner Aufruf)."""
    partner = PARTNERS.get(partner_api_key)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner nicht gefunden")
    
    devis_id = str(uuid.uuid4())[:12]
    record = DevisRecord(
        id=devis_id,
        partner_id=partner_api_key,
        original_path=original_path,
        meta=meta or {},
    )
    DEVIS_STORE[devis_id] = record
    
    return {"devis_id": devis_id, "partner": partner.name}


@app.get("/admin/devis/{devis_id}")
async def get_devis_status(devis_id: str):
    record = DEVIS_STORE.get(devis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Nicht gefunden")
    return {
        "id": record.id,
        "partner_id": record.partner_id,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
        "meta": record.meta,
    }


@app.get("/admin/partners")
async def list_partners():
    return [
        {
            "api_key": p.api_key[:8] + "...",
            "name": p.name,
            "email": p.email,
            "active": p.active,
            "rate_limit": p.rate_limit,
        }
        for p in PARTNERS.values()
    ]


# ============================================================
# Embedded Uvicorn Server (Thread)
# ============================================================

class PartnerAPIServer:
    """FastAPI Server im Hintergrund-Thread für DevisPro Integration."""
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        log_level: str = "info",
    ):
        self.host = host
        self.port = port
        self.log_level = log_level
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()
    
    def start(self, background: bool = True) -> None:
        """Startet den Server."""
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level=self.log_level,
            lifespan="on",
        )
        self._server = uvicorn.Server(config)
        
        if background:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            # Warten bis Server ready
            self._started.wait(timeout=10)
            print(f"[Partner API] Running at http://{self.host}:{self.port}")
        else:
            self._run()
    
    def _run(self) -> None:
        self._started.set()
        self._server.run()
    
    def stop(self) -> None:
        """Stoppt den Server."""
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)
        print("[Partner API] Stopped")
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_running(self) -> bool:
        return self._server is not None and not self._server.should_exit


# Singleton für einfache Integration
_server_instance: Optional[PartnerAPIServer] = None


def get_partner_api_server() -> PartnerAPIServer:
    """Gibt Singleton Server-Instanz zurück."""
    global _server_instance
    if _server_instance is None:
        _server_instance = PartnerAPIServer()
    return _server_instance


def start_partner_api(host: str = "127.0.0.1", port: int = 8765) -> PartnerAPIServer:
    """Startet Partner API Server (Convenience-Funktion)."""
    server = get_partner_api_server()
    server.host = host
    server.port = port
    server.start(background=True)
    return server


def stop_partner_api() -> None:
    """Stoppt Partner API Server."""
    global _server_instance
    if _server_instance:
        _server_instance.stop()
        _server_instance = None


# ============================================================
# CLI / Direct Run
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "openapi":
        # OpenAPI Spec exportieren
        import json
        from fastapi.openapi.utils import get_openapi
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        print(json.dumps(openapi_schema, indent=2, ensure_ascii=False))
    else:
        # Server direkt starten
        uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")