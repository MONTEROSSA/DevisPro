#!/bin/bash
# DevisPro Diagnose: Apple-Notarization-Log + lokale Bundle-Checks
# Kein codesign/security -> sicher doppelklickbar
set +e
echo "=== DevisPro Diagnose (Apple-Log + Bundle-Check) ==="

APPLE_ID="info@monterossa.ch"
APP_PW="mezr-waka-hawr-qbwb"
TEAM="T3VS7P5X5D"
SUBID="f3030733-1e01-470e-b8fb-5c5df1ec736b"

echo "=== 1) Apple Notarization-Log (Submission $SUBID) ==="
xcrun notarytool log "$SUBID" --apple-id "$APPLE_ID" --password "$APP_PW" --team-id "$TEAM" 2>&1 | head -60
echo "(ende log)"

APP="/Users/ferdinandrothlisberger/devis-auto/_signFIX/DevisPro.app"
echo "=== 2) Shell-Skripte / .sh im Bundle (Apple lehnt oft ab) ==="
find "$APP" -type f \( -name "*.sh" -o -name "*.command" \) 2>/dev/null | head
echo "-- dateien die mit #! beginnen --"
find "$APP" -type f 2>/dev/null | while read f; do
  head -c 2 "$f" 2>/dev/null | grep -q '#!' && echo "SCRIPT: $f"
done | head

echo "=== 3) Mach-O-Binaries OHNE gueltige signatur ==="
find "$APP" -type f 2>/dev/null | while read f; do
  if file "$f" 2>/dev/null | grep -q "Mach-O"; then
    if ! codesign --verify --verbose=2 "$f" >/dev/null 2>&1; then
      echo "UNSIGNED/INVALID: $f"
    fi
  fi
done | head -20
echo "(ende diagnose)"
echo "DONE"
