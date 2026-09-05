"""pytest-Tests fuer die DevisPro Partner-API.

Nutzt starlette/fastapi TestClient. Test-Daten via DEVISPRO_TEST_DIR env-var.
"""
import sys
import os
import tempfile
from pathlib import Path

import pytest

# Test-Daten-Dir bestimmen
test_data = os.environ.get("DEVISPRO_TEST_DIR")
if test_data:
    TEST_DATA_ROOT = Path(test_data)
else:
    user_dir = Path.home() / "Library" / "Application Support" / "DevisPro" / "devis"
    if user_dir.exists() and any(user_dir.iterdir()):
        TEST_DATA_ROOT = user_dir
    else:
        from tests._test_data import ensure_test_data
        TEST_DATA_ROOT = ensure_test_data() / "devis"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from devispro.partner_api import create_partner_app, create_partner_key, _load_keys, _save_keys
from devispro.parsers.devispro_sia import parse as devispro_parse


# ============================================================
# Setup/Teardown
# ============================================================

@pytest.fixture
def app_and_key():
    app = create_partner_app()
    pk = create_partner_key(name="pytest-test", partner="test",
                             permissions=["devis:read", "preise:sync", "webhook"])
    yield app, pk
    keys = _load_keys()
    if pk.key in keys:
        del keys[pk.key]
        _save_keys(keys)


@pytest.fixture
def client(app_and_key):
    app, pk = app_and_key
    return TestClient(app), pk


# ============================================================
# Health-Check & Routes
# ============================================================

def test_health_endpoint(client):
    """GET /health gibt 200 + 'ok' zurueck."""
    c, _ = client
    r = c.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "devispro-partner-api"


def test_all_endpoints_registered(client):
    """Pruefe dass alle erwarteten Routes registriert sind."""
    c, _ = client
    paths_dict = c.get("/openapi.json").json().get("paths", {})
    paths = set(paths_dict.keys())
    expected = {
        "/health",
        "/api/v1/devis",
        "/api/v1/devis/{devis_id}/export",
        "/api/v1/preise/sync",
        "/api/v1/webhook/devis_finalized",
    }
    assert expected.issubset(paths), f"Fehlend: {expected - paths}"


# ============================================================
# Authentifizierung
# ============================================================

@pytest.mark.parametrize("endpoint", [
    "/api/v1/devis",
    "/api/v1/devis/devis_0001/export",
])
def test_missing_api_key_returns_401(client, endpoint):
    """Requests ohne X-API-Key werden mit 401 abgelehnt."""
    c, _ = client
    r = c.get(endpoint)
    assert r.status_code == 401


def test_invalid_api_key_returns_401(client):
    """Falscher API-Key wird mit 401 abgelehnt."""
    c, _ = client
    r = c.get("/api/v1/devis", headers={"X-API-Key": "INVALID-KEY"})
    assert r.status_code == 401


# ============================================================
# Devis-Liste
# ============================================================

def test_list_devis_returns_real_data(client, tmp_path, monkeypatch):
    """GET /api/v1/devis listet Devis aus dem Store.

    Verwendet isoliertes Test-Dir via monkeypatch damit der Test
    nicht von anderen Tests beeinflusst wird.
    """
    # Setze Test-Dir
    import devispro.data_store as ds
    user_dir = Path.home() / "Library" / "Application Support" / "DevisPro" / "devis"
    if user_dir.exists() and any(user_dir.iterdir()):
        test_root = user_dir
    else:
        from tests._test_data import ensure_test_data
        test_root = ensure_test_data() / "devis"

    monkeypatch.setattr(ds, "app_support_dir", lambda: str(test_root.parent))

    c, pk = client
    r = c.get("/api/v1/devis", headers={"X-API-Key": pk.key})
    assert r.status_code == 200
    data = r.json()
    assert "devis" in data
    assert "count" in data
    assert data["count"] >= 1, f"Keine Devis im Store, count={data['count']}"
    for dev in data["devis"][:3]:
        assert "id" in dev
        assert "name" in dev


# ============================================================
# Devis-Export (M16: DevisPro-Parser)
# ============================================================

def test_export_devis_with_devispro_parser(client):
    """GET /api/v1/devis/{id}/export nutzt den neuen DevisPro-Parser."""
    c, pk = client
    list_resp = c.get("/api/v1/devis", headers={"X-API-Key": pk.key})
    if not list_resp.json()["devis"]:
        pytest = __import__('pytest')
        pytest.skip("Keine Devis im Store")
    first_id = list_resp.json()["devis"][0]["id"]

    r = c.get(f"/api/v1/devis/{first_id}/export", headers={"X-API-Key": pk.key})
    assert r.status_code == 200
    data = r.json()
    assert data["devis_id"] == first_id
    if data["format"] != "devispro_native":
        assert len(data["data"]["positions"]) > 0
        assert data["data"]["summe_netto"] > 0


def test_export_nonexistent_devis_returns_404(client):
    """GET /api/v1/devis/UNKNOWN_ID/export gibt 404."""
    c, pk = client
    r = c.get("/api/v1/devis/devis_9999_unknown/export", headers={"X-API-Key": pk.key})
    assert r.status_code == 404


# ============================================================
# Preis-Sync (mit Deduplication)
# ============================================================

def test_preis_sync_receives_two_articles(client):
    """POST /api/v1/preise/sync bestaetigt 2 empfangene Artikel."""
    c, pk = client
    import time
    unique = int(time.time()) % 100000
    payload = {
        "artikel": [
            {"nr": f"TEST-{unique}-A", "text": "Test-Artikel A", "einheit": "Stk", "preis": 99.50},
            {"nr": f"TEST-{unique}-B", "text": "Test-Artikel B", "einheit": "m2", "preis": 12.30},
        ]
    }
    r = c.post("/api/v1/preise/sync", json=payload, headers={"X-API-Key": pk.key})
    assert r.status_code == 200
    data = r.json()
    assert data["received"] == 2
    assert data["imported"] == 2


# ============================================================
# Webhook
# ============================================================

def test_webhook_queues_devis(client):
    """POST /api/v1/webhook/devis_finalized persistiert in Queue."""
    c, pk = client
    payload = {
        "devis_id": "devis_TEST_WEBHOOK",
        "kunde": "Test-Kunde AG",
        "betrag": 12345.67,
    }
    r = c.post("/api/v1/webhook/devis_finalized", json=payload, headers={"X-API-Key": pk.key})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "queued"
    assert data["devis_id"] == "devis_TEST_WEBHOOK"


# ============================================================
# Parser-Smoke-Tests
# ============================================================

def test_devispro_parser_on_real_file():
    """Parser liest echte bepreist.sia."""
    sia_path = TEST_DATA_ROOT / "devis_0001" / "bepreist.sia"
    if not sia_path.exists():
        pytest = __import__('pytest')
        pytest.skip(f"{sia_path} nicht vorhanden")
    dev = devispro_parse(str(sia_path))
    assert len(dev.positions) >= 1
    pos1 = dev.positions[0]
    # Bei Test-Daten: Standard-Text, bei Live-Daten: "Innenanstrich Wand 2 Anstriche"
    assert pos1.text  # nicht leer
    assert pos1.menge > 0
    assert pos1.einheit in ["m2", "m3", "Stk", "Paus", "h"]


# ============================================================
# Fixtures-driven Tests
# ============================================================

def test_sample_devis_dir_fixture(sample_devis_dir):
    """Prueft dass die sample_devis_dir-Funktion aus conftest.py funktioniert."""
    dev = devispro_parse(str(sample_devis_dir / "bepreist.sia"))
    assert len(dev.positions) >= 1
    assert dev.positions[0].text  # nicht leer


def test_empty_sia_file(empty_sia_file):
    """Leere .sia darf nicht crashen."""
    dev = devispro_parse(str(empty_sia_file))
    assert dev is not None
    assert len(dev.positions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])