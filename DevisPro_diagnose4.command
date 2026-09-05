#!/bin/bash
# DevisPro DIAGNOSE v4 - WO wird die signatur verloren? (xattr vs binary, ditto-extrakt vs unzip)
LOG=/tmp/diag4.log
rm -f "$LOG"
exec > >(tee -a "$LOG") 2>&1
echo "=== DevisPro DIAGNOSE v4 (xattr-vs-binary + ditto-extract) ==="

KEYCHAIN="$HOME/Library/Keychains/devispro3.keychain-db"
PW="devispro2026"
CERT="Developer ID Application: Ferdinand Ferdinand Röthlisberger (T3VS7P5X5D)"
SRC="/Volumes/SHGN7/DevisPro.app"
WORK="/Users/ferdinandrothlisberger/devis-auto/_diag4"
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

codesign --deep --force --options runtime --timestamp --keychain "$KEYCHAIN" -s "$CERT" "$APP" && echo "SIGN OK (lokal valid)"

echo
echo "=== WO STECKT DIE SIGNATUR? ==="
echo "--- xattr -l auf den launcher (smoking gun: com.apple.cs.* ?) ---"
xattr -l "$OLD" 2>&1 || echo "(keine xattrs)"
echo "--- otool -l LC_CODE_SIGNATURE im binary? ---"
otool -l "$OLD" 2>/dev/null | grep -E "LC_CODE_SIGNATURE|LC_BUILD_VERSION" || echo "(kein LC_CODE_SIGNATURE im binary)"

# ---- TEST A: zip -r -q -> unzip ----
echo
echo "=== TEST A: zip -r -q -> unzip -q -> strict verify ==="
cd "$WORK"; rm -f a.zip; zip -r -q a.zip DevisPro.app
rm -rf /tmp/extA; mkdir -p /tmp/extA; cd /tmp/extA; unzip -q "$WORK/a.zip"
A=$(find . -name "DevisPro.app" -maxdepth 2 -type d | head -1)
if codesign --verify --deep --strict --verbose=4 "$A" 2>/tmp/errA; then echo "TEST A: STRICT VALID"; else echo "TEST A: STRICT INVALID"; echo "--- detail ---"; head -20 /tmp/errA; fi

# ---- TEST B: ditto -c -k --keepParent -> ditto -x -k (KORREKTE extraktion) ----
echo
echo "=== TEST B: ditto -c -k --keepParent -> ditto -x -k -> strict verify ==="
rm -f "$WORK/b.zip"; ditto -c -k --keepParent "$APP" "$WORK/b.zip"
rm -rf /tmp/extB; mkdir -p /tmp/extB; ditto -x -k "$WORK/b.zip" /tmp/extB
B=$(find /tmp/extB -name "DevisPro.app" -maxdepth 2 -type d | head -1)
if codesign --verify --deep --strict --verbose=4 "$B" 2>/tmp/errB; then echo "TEST B: STRICT VALID"; else echo "TEST B: STRICT INVALID"; echo "--- detail ---"; head -20 /tmp/errB; fi

# ---- TEST C: zip -r --macosx -> ditto -x -k ----
echo
echo "=== TEST C: zip -r --macosx -> ditto -x -k -> strict verify ==="
cd "$WORK"; rm -f c.zip; zip -r --macosx -q c.zip DevisPro.app
rm -rf /tmp/extC; mkdir -p /tmp/extC; ditto -x -k "$WORK/c.zip" /tmp/extC
C=$(find /tmp/extC -name "DevisPro.app" -maxdepth 2 -type d | head -1)
if codesign --verify --deep --strict --verbose=4 "$C" 2>/tmp/errC; then echo "TEST C: STRICT VALID"; else echo "TEST C: STRICT INVALID"; echo "--- detail ---"; head -20 /tmp/errC; fi

echo
echo "=== FAZIT ==="
echo "TEST A (zip -r -q + unzip):     $([ -f /tmp/errA ] && ! grep -q 'valid on disk' /tmp/errA && echo INVALID || echo VALID)"
echo "TEST B (ditto + ditto -x -k):   $([ -f /tmp/errB ] && ! grep -q 'valid on disk' /tmp/errB && echo INVALID || echo VALID)"
echo "TEST C (zip --macosx + ditto):  $([ -f /tmp/errC ] && ! grep -q 'valid on disk' /tmp/errC && echo INVALID || echo VALID)"
echo "DONE-DIAGNOSE4 -> Log unter $LOG"
open -t "$LOG"
