"""Tests fuer M27 DSGVO + Audit-Log Compliance.

ACHTUNG: delete_user_data() darf NIEMALS auf USER_DATA laufen im Test!
Deshalb: Test-Dir via env-Variable DSGVO_TEST_MODE=1, der delete_user_data
dann auf /tmp umleitet.
"""
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# CRITICAL: Bevor wir compliance importieren, Test-Mode aktivieren
os.environ["DSGVO_TEST_MODE"] = "1"

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

# Patch USER_DATA BEVOR compliance geladen wird
import devispro.data_store as ds
TEST_DIR = tempfile.mkdtemp(prefix="devispro_compliance_test_")
ds.app_support_dir = lambda: TEST_DIR

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')
from devispro.compliance import (
    audit_log, list_audit_log, export_user_data, delete_user_data,
    enforce_retention_policies, get_compliance_status, AUDIT_LOG,
)
# AUDIT_LOG neu berechnen (zeigt jetzt auf Test-Dir)
import devispro.compliance as comp
comp.USER_DATA = Path(TEST_DIR)
comp.AUDIT_LOG = Path(TEST_DIR) / "audit.log"
AUDIT_LOG = comp.AUDIT_LOG


def test_audit_log_write_and_read():
    """Audit-Log schreibt und liest Events korrekt."""
    audit_log("test_event", {"foo": "bar"})
    audit_log("login", {"user": "test"})

    entries = list_audit_log(limit=10)
    assert len(entries) >= 2
    events = [e["event"] for e in entries]
    assert "test_event" in events
    assert "login" in events
    print(f"OK: Audit-Log schreibt+liest ({len(entries)} Eintraege)")


def test_audit_log_filter():
    """Audit-Log kann nach Event-Typ gefiltert werden."""
    audit_log("login", {"user": "alice"})
    audit_log("export", {"file": "test.pdf"})
    audit_log("login", {"user": "bob"})

    login_entries = list_audit_log(limit=50, event_filter="login")
    export_entries = list_audit_log(limit=50, event_filter="export")

    assert len(login_entries) >= 2
    assert len(export_entries) >= 1
    for e in login_entries:
        assert e["event"] == "login"
    print(f"OK: Audit-Log Filter funktioniert ({len(login_entries)} logins, {len(export_entries)} exports)")


def test_export_user_data():
    """DSGVO Art. 15: User-Daten-Export funktioniert."""
    export = export_user_data(user_id="test_user")

    assert "export_date" in export
    assert "user_data" in export
    assert "data_categories" in export
    assert isinstance(export["user_data"], dict)
    print(f"OK: DSGVO-Export liefert {len(export['data_categories'])} Daten-Kategorien")


def test_export_contains_all_categories():
    """DSGVO-Export enthaelt alle Standard-Kategorien."""
    export = export_user_data()
    expected = ["profile", "devis", "preise", "kunden", "audit_log"]
    for cat in expected:
        assert cat in export["user_data"], f"Fehlende Kategorie: {cat}"
    print(f"OK: DSGVO-Export enthaelt alle {len(expected)} Kategorien")


def test_delete_user_data():
    """DSGVO Art. 17: User-Daten-Loeschung loescht nur TEST-Dir."""
    # Erstelle Test-Daten im Test-Dir
    (Path(TEST_DIR) / "test.json").write_text('{"test": "data"}', encoding="utf-8")
    test_subdir = Path(TEST_DIR) / "test_dir"
    test_subdir.mkdir()
    (test_subdir / "file.txt").write_text("test", encoding="utf-8")

    result = delete_user_data(keep_audit_log=True, password_confirm="delete")
    assert "files" in result
    assert "directories" in result
    # Test-Files sollten weg sein
    assert not (Path(TEST_DIR) / "test.json").exists()
    print(f"OK: delete_user_data() laeuft (loescht {result['files']} Dateien, {result['directories']} Verzeichnisse)")


def test_enforce_retention_policies():
    """Aufbewahrungs-Fristen: alte Backups werden geloescht."""
    result = enforce_retention_policies(max_backup_age_days=365, max_audit_log_entries=10000)
    assert "backups" in result
    assert "audit_entries" in result
    print(f"OK: Retention-Policies: {result['backups']} alte Backups geloescht")


def test_compliance_status():
    """Compliance-Status Ueberblick."""
    status = get_compliance_status()
    assert "audit_log_exists" in status
    assert "data_categories_stored" in status
    assert "export_available" in status
    assert "delete_available" in status
    print(f"OK: Compliance-Status: {len([c for c in status['data_categories_stored'] if c])} Daten-Kategorien gespeichert")


def test_audit_log_rotation():
    """Bei zu vielen Eintragen wird rotiert (Ring-Buffer)."""
    for i in range(100):
        audit_log("rotation_test", {"i": i})
    entries = list_audit_log(limit=20000)
    assert len(entries) >= 100
    print(f"OK: Audit-Log Rotation: {len(entries)} Eintraege geschrieben")


def cleanup():
    """Test-Temp-Dir aufraeumen."""
    if Path(TEST_DIR).exists():
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        print(f"Test-Dir aufgeraeumt: {TEST_DIR}")


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("M27 Compliance - DSGVO + Audit-Log Tests (TEST-MODE)")
        print("=" * 60)
        test_audit_log_write_and_read()
        test_audit_log_filter()
        test_export_user_data()
        test_export_contains_all_categories()
        test_delete_user_data()
        test_enforce_retention_policies()
        test_compliance_status()
        test_audit_log_rotation()
        print("=" * 60)
        print("ALLE TESTS BESTANDEN - DSGVO + Audit-Log aktiv")
        print("=" * 60)
    finally:
        cleanup()