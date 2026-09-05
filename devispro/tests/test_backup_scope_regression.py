"""Test fuer M27-FIX: devis/ muss im SCOPE sein, sonst gehen Devis verloren.

Regression-Test: Wenn dieser Test fehlschlaegt, ist es derselbe Bug
der zum Verlust von 28 Devis gefuehrt hat.
"""
import sys
import os

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

from devispro.backup import SCOPE, BUNDLE_SCOPE


def test_devis_in_bundle_scope():
    """devis/ muss im BUNDLE_SCOPE sein, sonst werden Devis nie gesichert."""
    assert "devis" in BUNDLE_SCOPE, (
        f"BUG! 'devis' fehlt in BUNDLE_SCOPE={BUNDLE_SCOPE}. "
        f"Devis wuerden NICHT ins Backup genommen! "
        f"Siehe: 28 Devis gingen am 05.09.2026 verloren wegen dieses Bugs."
    )
    print("OK: 'devis' ist im BUNDLE_SCOPE -> wird ins Backup genommen")


def test_critical_files_in_scope():
    """Kritische Dateien muessen im SCOPE sein."""
    critical = [
        "meine_preise.csv",
        "profil.json",
        "kunden.json",
        "audit.log",  # neu seit M27
    ]
    for f in critical:
        assert f in SCOPE, f"WICHTIG: {f} fehlt im SCOPE!"
    print(f"OK: Alle {len(critical)} kritischen Dateien im SCOPE")


def test_audit_log_in_scope():
    """Audit-Log muss im Backup sein fuer DSGVO-Compliance."""
    assert "audit.log" in SCOPE, "audit.log fehlt im SCOPE!"
    print("OK: audit.log im SCOPE (DSGVO-konform)")


if __name__ == "__main__":
    print("=" * 60)
    print("M27 Regression-Test: Backup-Scope vollstaendig?")
    print("=" * 60)
    test_devis_in_bundle_scope()
    test_critical_files_in_scope()
    test_audit_log_in_scope()
    print("=" * 60)
    print("ALLE TESTS BESTANDEN - Backup erfasst alle wichtigen Daten")
    print("=" * 60)