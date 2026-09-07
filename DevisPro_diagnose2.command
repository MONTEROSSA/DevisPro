#!/bin/bash
# DevisPro DIAGNOSE v2 (robust) - kein set -e, voller output nach /tmp/diag2.log + TextEdit
LOG=/tmp/diag2.log
rm -f "$LOG"
exec > >(tee -a "$LOG") 2>&1
echo "=== DevisPro DIAGNOSE v2 (robust) ==="

KEYCHAIN="$HOME/Library/Keychains/devispro3.keychain-db"
PW="devispro2026"
CERT="Developer ID Application: Ferdinand Ferdinand Röthlisberger (T3VS7P5X5D)"
SRC="/Volumes/SHGN7/DevisPro.app"
WORK="/Users/ferdinandrothlisberger/devis-auto/_diag"
APP="$WORK/DevisPro.app"
MACOS="$APP/Contents/MacOS"
OLD="$MACOS/DevisPro"

security unlock-keychain -p "$PW" "$KEYCHAIN" && echo "UNLOCK OK"

rm -rf "$WORK"; mkdir -p "$WORK"
cp -R "$SRC" "$APP"
[ -d "$APP/DevisPro.app" ] && rm -rf "$APP/DevisPro.app"
find "$APP" -name '._*' -delete
xattr -cr "$APP"

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
    char contents[PATH_MAX]; snprintf(contents, sizeof(contents), "%s/..", exe_path);
    char python[PATH_MAX]; snprintf(python, sizeof(python), "%s/../MacOS/python-runtime/bin/python3.11", contents);
    char resdir[PATH_MAX];  snprintf(resdir, sizeof(resdir), "%s/../Resources", contents);
    char mainpy[PATH_MAX];  snprintf(mainpy, sizeof(mainpy), "%s/devispro/app_gui.py", resdir);
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
RT="$MACOS/python-runtime"
[ -d "$RT/include" ] && rm -rf "$RT/include"
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

echo "=== SIGN (wie v7) ==="
codesign --deep --force --options runtime --timestamp --keychain "$KEYCHAIN" -s "$CERT" "$APP" && echo "SIGN OK"

echo
echo "=== DIAGNOSE 1: codesign -dvvv auf den LAUNCHER ==="
codesign -dvvv "$OLD" 2>&1 || echo "(dvvv rc=$?)"
echo
echo "=== DIAGNOSE 2: codesign --verify --deep --verbose=4 auf die APP ==="
codesign --verify --deep --verbose=4 "$APP" 2>&1 || echo "(verify rc=$? - das ist der fehler den Apple sieht)"
echo
echo "=== DIAGNOSE 3: otool -l (LC_CODE_SIGNATURE / LC_BUILD_VERSION) ==="
otool -l "$OLD" 2>&1 | grep -E "LC_CODE_SIGNATURE|LC_BUILD_VERSION" || echo "(kein LC_CODE_SIGNATURE)"
echo
echo "=== DIAGNOSE 4: file-type launcher ==="
file "$OLD"
echo
echo "=== DIAGNOSE 5: spctl -a -vv auf die APP (lokal) ==="
spctl -a -vv "$APP" 2>&1 || echo "(spctl rc=$?)"
echo
echo "DONE-DIAGNOSE -> Log unter $LOG"
open -t "$LOG"
