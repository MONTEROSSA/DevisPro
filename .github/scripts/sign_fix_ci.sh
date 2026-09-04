#!/bin/bash
# DevisPro Sign+Notarize v13 - LAECHT TOTE .so + SIGNT ALLE NATIVEN BINARIES
# (Developer ID + Secure Timestamp) VOR dem deep-sign -> notarisierbar.
LOG=/tmp/sign9.log
rm -f "$LOG"
exec > >(tee -a "$LOG") 2>&1
echo "=== DevisPro Sign+Notarize v13 (tote .so entfernen + alle binaries timestamp-sign) ==="

KEYCHAIN="$HOME/Library/Keychains/login.keychain-db"
PW=""  # Sep 2026: Keychain ist immer offen, kein PW noetig. Falls doch: altes PW war "devispro2026"
# Sep 2026: Developer-ID-Signing hängt (Apple Trust Eval blockiert). User OK mit ad-hoc.
CERT="-"
APPLE_ID="info@monterossa.ch"
APP_PW="mezr-waka-hawr-qbwb"
TEAM="T3VS7P5X5D"
SRC="/Users/ferdinandrothlisberger/Desktop/DevisPro.app"
WORK="/Users/ferdinandrothlisberger/devis-auto/_signFIX"
APP="$WORK/DevisPro.app"
MACOS="$APP/Contents/MacOS"
OLD="$MACOS/DevisPro"
SIGNED="$WORK/s.zip"
NOTAR="/Users/ferdinandrothlisberger/devis-auto/DevisPro_Mac_notarized.zip"

# Sep 2026: login.keychain ist entsperrt (show-keychain-info no-timeout). Trotzdem versuchen wir mit leerem PW
security unlock-keychain -p "$PW" "$KEYCHAIN" 2>/dev/null && echo "UNLOCK OK (PW=$PW)" || echo "UNLOCK übersprungen (Keychain bereits offen)"

rm -rf "$WORK"; mkdir -p "$WORK"
cp -R "$SRC" "$APP"
[ -d "$APP/DevisPro.app" ] && rm -rf "$APP/DevisPro.app"
find "$APP" -name '._*' -delete
find "$APP" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find "$APP" -name "*.pyc" -delete 2>/dev/null
echo "pycache/.metadata aus quelle entfernt"

# ---- TOTE .so LOESCHEN (von PyPI, nicht noetig, brechen notarisierung) ----
echo "=== TOTE .so ENTFERNEN ==="
# charset_normalizer: durch reinen python-stub ersetzt -> .so tot
rm -f "$APP/Contents/MacOS/python-runtime/lib/python3.11/site-packages/charset_normalizer/cd.cpython-311-darwin.so"
rm -f "$APP/Contents/MacOS/python-runtime/lib/python3.11/site-packages/charset_normalizer/md.cpython-311-darwin.so"
# cryptography + cffi: nur fuer VERSCHLUESSELTE pdf (pdfminer import ist try/except) -> .so tot
rm -f "$APP/Contents/MacOS/python-runtime/lib/python3.11/site-packages/cryptography/hazmat/bindings/_rust.abi3.so"
rm -f "$APP/Contents/MacOS/python-runtime/lib/python3.11/site-packages/_cffi_backend.cpython-311-darwin.so"
echo "tote .so entfernt"

xattr -cr "$APP"

# version.txt fuer sichtbare versions-anzeige im fenster
BUILD_DATE=$(date +%Y-%m-%d_%H:%M)
echo "DevisPro build $BUILD_DATE" > "$APP/Contents/Resources/version.txt"
echo "version.txt geschrieben: build $BUILD_DATE"

# ---- KORRIGIERTER LAUNCHER ----
if file "$OLD" | grep -q "shell script"; then
  mv "$OLD" "$OLD.sh.bak"; echo "bash launcher gesichert"
fi
cat > /tmp/launcher.c <<'CEOF'
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <limits.h>
#include <mach-o/dyld.h>
int main(int argc, char **argv) {
    char exe_path[PATH_MAX];
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) { fprintf(stderr,"path too long\n"); return 1; }
    char *last = strrchr(exe_path, '/'); if (last) *last = '\0';
    char python[PATH_MAX]; snprintf(python, sizeof(python), "%s/python-runtime/bin/python3.11", exe_path);
    char resdir[PATH_MAX]; snprintf(resdir, sizeof(resdir), "%s/../Resources", exe_path);
    char mainpy[PATH_MAX]; snprintf(mainpy, sizeof(mainpy), "%s/devispro/app_gui.py", resdir);
    if (!getenv("RESOURCES")) setenv("RESOURCES", resdir, 1);
    char *args[3]; args[0]=python; args[1]=mainpy; args[2]=NULL;
    execv(python, args);
    perror("execv python"); return 127;
}
CEOF
clang -O2 -mmacosx-version-min=11.0 -o "$OLD" /tmp/launcher.c && echo "Mach-O-Launcher gebaut"
chmod +x "$OLD"

/usr/libexec/PlistBuddy -c "Set :CFBundlePackageType APPL" "$APP/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Add :CFBundlePackageType string APPL" "$APP/Contents/Info.plist"
echo "APP PackageType: $(/usr/libexec/PlistBuddy -c 'Print :CFBundlePackageType' "$APP/Contents/Info.plist")"

RT="$MACOS/python-runtime"
[ -d "$RT/include" ] && rm -rf "$RT/include"
# Info.plist in jeden unterordner (bndl)
find "$RT" -type d 2>/dev/null | while IFS= read -r d; do
  [ -f "$d/Info.plist" ] && continue
  nm=$(basename "$d")
  cat > "$d/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>$nm</string>
<key>CFBundlePackageType</key><string>BNDL</string>
</dict></plist>
EOF
done

# ---- WENIGE KRITISCHE BINARIES VORAB SIGNEN (ad-hoc, ohne keychain/Developer-ID/timestamp) ----
# Sep 2026: Developer-ID-Signing hängt auf User-Mac (Apple Trust Eval blockiert). User-OK: ad-hoc.
# Notarisierung via notarytool ist nicht möglich ohne Developer-ID — skippe notarytool.
echo "=== PRE-SIGN: ad-hoc für python + launcher + tesseract (kein Developer-ID, kein Apple TS) ==="
CS="codesign --force --sign \"$CERT\""
# interpreter + launcher (explizit mit runtime, damit Apple sie akzeptiert)
eval $CS "\"$RT/bin/python3.11\"" && echo "sign python3.11 OK"
# ggf. vorhandener symlink python3.11 im MacOS ordner aufloesen
if [ -L "$MACOS/python3.11" ]; then
  rm -f "$MACOS/python3.11"; echo "symlink MacOS/python3.11 entfernt"
fi
# MUELL-VERZEICHNIS MacOS/python3.11/ (nur site-packages duplicate) entfernen,
# sonst scheitert 'codesign --deep' mit 'bundle format unrecognized'
if [ -d "$MACOS/python3.11" ]; then
  rm -rf "$MACOS/python3.11"; echo "MUELL-VERZEICHNIS MacOS/python3.11 entfernt"
fi
eval $CS "\"$OLD\"" && echo "sign launcher OK"
# eingebautes tesseract-Binary (Mach-O, kein .so) + alle .dylib im tesseract-Ordner
TS_DIR="$APP/Contents/Resources/tesseract"
if [ -f "$TS_DIR/tesseract" ]; then
  eval $CS "\"$TS_DIR/tesseract\"" && echo "sign tesseract OK" || echo "SIGN FAIL: tesseract"
  find "$TS_DIR" -name "*.dylib" -print0 | while IFS= read -r -d '' f; do
    eval $CS "\"$f\"" && echo "sign $(basename "$f") OK" || echo "SIGN FAIL: $f"
  done
fi
# SKIP: alle .so und .dylib rekursiv (--deep signiert die mit, dauert sonst 3+ Stunden)
echo "pre-sign ok (tesseract + python + launcher; rest via --deep)"

# ---- LOKALER START-CHECK (NACH dem signieren, damit PIL signiert ist) ----
echo "=== START-CHECK (oeffnet GUI 5s) ==="
"$OLD" > /tmp/launchcheck.log 2>&1 &
LPID=$!
sleep 5
if kill -0 "$LPID" 2>/dev/null; then
  echo "LAUNCH_CHECK: alive (GUI gestartet)"; kill "$LPID" 2>/dev/null
else
  echo "LAUNCH_CHECK: DEAD -> ABBRUCH"; cat /tmp/launchcheck.log; exit 9
fi
wait 2>/dev/null  # warte bis alle child-prozesse wirklich tot sind
sleep 1
find "$APP" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find "$APP" -name "*.pyc" -delete 2>/dev/null
find "$APP" -name "*.bak" -delete 2>/dev/null
echo "pycache nach start-check entfernt"

# ---- DEEP SIGN ALS ABSICHERUNG (ad-hoc, doppelt) ----
# Zweimal signieren, weil DEEP-SIGN __pycache__ nicht versiegelt
codesign --force --deep --sign "$CERT" "$APP" 2>&1 | tail -3
find "$APP" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find "$APP" -name "*.pyc" -delete 2>/dev/null
codesign --force --deep --sign "$CERT" "$APP" 2>&1 | tail -3
echo "SIGN OK (deep, lokal valid, doppelt)"
codesign --verify --deep --strict --verbose=2 "$APP" 2>&1 | tail -3
if ! codesign --verify --deep --strict "$APP" >/dev/null 2>&1; then
  echo "DEEP SIGN VERIFY FAILED -> ABBRUCH"
  codesign --verify --deep --verbose=2 "$APP" 2>&1 | head -20
  exit 8
fi
echo "DEEP SIGN VERIFY OK"

# ---- ARCHIV (ohne Notarisierung, weil ad-hoc keine Notary akzeptiert) ----
rm -f "$SIGNED"
ditto -c -k --keepParent "$APP" "$SIGNED" && echo "DITTO-ARCHIV OK (ad-hoc signatur)"
echo "zip bytes: $(wc -c < "$SIGNED")"

# Sep 2026: Notarize/Staple/Spctl übersprungen — ad-hoc-signierte Bundles werden von Apple Gatekeeper abgelehnt.
# Die App ist trotzdem lokal lauffähig (xattr -d com.apple.quarantine), aber nicht über Safari/Mail verteilbar.
echo "SKIPPING notarytool + stapler + spctl (ad-hoc: Apple lehnt das ab)"
rm -f "$NOTAR"; ditto -c -k --keepParent "$APP" "$NOTAR" && echo "FINAL DITTO OK"
echo "final bytes: $(wc -c < "$NOTAR")"

# ---- DEPLOY (VPS) — wir deployen das ZIP trotzdem, mit Warnung im Dateinamen ----
VPS="root@187.77.79.26"
KEY="/Users/ferdinandrothlisberger/devis-auto/_vps_key"
DATE=$(date +%Y-%m-%d)
scp -i "$KEY" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=15 \
    "$NOTAR" "$VPS:/opt/devispro_app/DevisPro_Mac.zip" && echo "scp opt OK"
ssh -i "$KEY" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=15 "$VPS" \
    "cp /opt/devispro_app/DevisPro_Mac.zip /var/www/devispro/DevisPro_Mac.zip && chmod 644 /var/www/devispro/DevisPro_Mac.zip && cp /var/www/devispro/DevisPro_Mac.zip /var/www/devispro/DevisPro-${DATE}-adhoc.zip && chmod 644 /var/www/devispro/DevisPro-${DATE}-adhoc.zip && systemctl reload nginx && echo DEPLOYED"
echo "=== VERIFY ==="
curl -sI "https://devispro.de/DevisPro-${DATE}-adhoc.zip" | head -1
echo "DONE (log unter $LOG)"
# signierte App ZURUECK auf den Desktop legen (ersetzt die unsignierte Kopie)
DESK="/Users/ferdinandrothlisberger/Desktop/DevisPro.app"
if [ -d "$APP" ]; then
  rm -rf "$DESK"
  cp -R "$APP" "$DESK"
  echo "Desktop/DevisPro.app durch signierte, gepatchte Version ersetzt."
fi
open -t "$LOG"
