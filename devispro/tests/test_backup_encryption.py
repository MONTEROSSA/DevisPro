"""Tests fuer M27 verschluesseltes Backup."""
import sys
import os
import tempfile
import json
import zipfile
import io

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

from devispro.backup import (
    create, restore, verify, list_backups,
    MAGIC, FORMAT_VERSION, PBKDF2_ITERATIONS,
)


def test_create_unverschluesseltes_backup():
    """Backup ohne Passwort = Klartext-ZIP (Abwaertskompatibilitaet)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out, manifest = create(label="test")
        assert os.path.exists(out)
        assert out.endswith(".zip")
        # Inhalt ist ZIP
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
        assert "MANIFEST.json" in names
        os.unlink(out)
    print("OK: Unverschluesseltes Backup als ZIP geschrieben")


def test_create_verschluesseltes_backup():
    """Backup MIT Passwort = AES-256-CTR + HMAC-SHA256 (.dpbk)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out, manifest = create(label="encrypted", password="test123")
        assert os.path.exists(out)
        assert out.endswith(".dpbk")
        assert manifest["encrypted"] is True
        # Erste 4 Bytes sind MAGIC
        with open(out, "rb") as f:
            magic = f.read(4)
        assert magic == MAGIC
        os.unlink(out)
    print("OK: Verschluesseltes Backup als .dpbk geschrieben")


def test_verify_unverschluesseltes_backup():
    """Verify eines unverschluesselten Backups."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _ = create(label="verify-test")
        ok, msg = verify(out)
        assert ok, f"Verify fehlgeschlagen: {msg}"
        os.unlink(out)
    print("OK: Verify unverschluesseltes Backup")


def test_verify_verschluesseltes_backup_mit_passwort():
    """Verify eines verschluesselten Backups mit korrektem Passwort."""
    out, _ = create(label="verify-encrypted", password="MeinPasswort123!")
    ok, msg = verify(out, password="MeinPasswort123!")
    assert ok, f"Verify fehlgeschlagen: {msg}"
    os.unlink(out)
    print("OK: Verify verschluesseltes Backup mit korrektem PW")


def test_verify_verschluesseltes_backup_mit_falschem_passwort():
    """Verify eines verschluesselten Backups mit FALSCHEM Passwort schlaegt fehl."""
    out, _ = create(label="verify-wrong-pw", password="RichtigesPW")
    ok, msg = verify(out, password="FalschesPW")
    assert not ok, "Verify haette fehlschlagen sollen"
    assert "HMAC" in msg or "Passwort" in msg, f"Unerwartete Fehlermeldung: {msg}"
    os.unlink(out)
    print("OK: Verify mit falschem Passwort schlaegt fehl")


def test_restore_unverschluesseltes_backup():
    """Restore funktioniert fuer unverschluesseltes Backup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _ = create(label="restore-test")
        n = restore(out, target_data=tmpdir)
        assert n > 0, "Restore sollte mindestens 1 Datei extrahieren"
        os.unlink(out)
    print(f"OK: Restore extrahiert Dateien")


def test_restore_verschluesseltes_backup():
    """Restore eines verschluesselten Backups mit korrektem Passwort."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out, _ = create(label="restore-encrypted", password="BackupPW2026")
        n = restore(out, target_data=tmpdir, password="BackupPW2026")
        assert n > 0, "Restore sollte Dateien extrahieren"
        os.unlink(out)
    print(f"OK: Restore verschluesseltes Backup mit PW")


def test_restore_verschluesseltes_backup_ohne_passwort_fails():
    """Restore ohne Passwort fuer verschluesseltes Backup schlaegt fehl."""
    out, _ = create(label="restore-no-pw", password="SecretPW")
    try:
        restore(out, target_data=tempfile.mkdtemp())
        assert False, "Restore ohne PW haette fehlschlagen sollen"
    except ValueError as e:
        assert "Passwort" in str(e), f"Unerwartete Fehlermeldung: {e}"
    finally:
        os.unlink(out)
    print("OK: Restore ohne Passwort wird abgelehnt")


def test_pbkdf2_iterationen_ausreichend():
    """Verifiziert dass PBKDF2 mit 200k Iterations verwendet wird (OWASP 2023+)."""
    assert PBKDF2_ITERATIONS >= 600_000, f"PBKDF2 Iterations zu niedrig: {PBKDF2_ITERATIONS} (OWASP 2023: min 600k)"
    print(f"OK: PBKDF2 mit {PBKDF2_ITERATIONS} Iterations (OWASP-konform)")


def test_kunden_daten_nicht_im_klartext():
    """Wenn ein Backup verschluesselt ist, darf kein Klartext-Kundennamen im File sein."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Erstelle eine fake kunden.json mit sensiblen Daten
        test_data_dir = os.path.expanduser("~/Library/Application Support/DevisPro")
        test_file = os.path.join(test_data_dir, "kunden.json")
        sensitive = "TESTKUNDE_GEHEIM_12345"
        with open(test_file, "w") as f:
            f.write(json.dumps([{"name": sensitive, "iban": "CH123"}]))

        try:
            out, _ = create(label="sensitive", password="encrypt2026")
            # Versuche sensitive Daten im Klartext zu finden
            with open(out, "rb") as f:
                content = f.read()
            assert sensitive.encode() not in content, "Sensible Daten im Klartext gefunden!"
            print("OK: Sensible Daten nicht im Klartext im verschluesselten Backup")
        finally:
            os.unlink(test_file)
            if os.path.exists(out):
                os.unlink(out)


if __name__ == "__main__":
    print("=" * 60)
    print("M27 Compliance - Verschlüsseltes Backup Tests")
    print("=" * 60)
    test_create_unverschluesseltes_backup()
    test_create_verschluesseltes_backup()
    test_verify_unverschluesseltes_backup()
    test_verify_verschluesseltes_backup_mit_passwort()
    test_verify_verschluesseltes_backup_mit_falschem_passwort()
    test_restore_unverschluesseltes_backup()
    test_restore_verschluesseltes_backup()
    test_restore_verschluesseltes_backup_ohne_passwort_fails()
    test_pbkdf2_iterationen_ausreichend()
    test_kunden_daten_nicht_im_klartext()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN - Backups sind verschluesselt")
    print("=" * 60)