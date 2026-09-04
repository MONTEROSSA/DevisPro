#!/bin/bash
# DevisPro CI Build - NUR Ad-Hoc Sign, keine Apple-Notarization
# Plan B: CI baut, lokales sign_fix notariert.
set -e

APP="$HOME/Desktop/DevisPro.app"
SRC="$GITHUB_WORKSPACE/devispro"

echo "=== Plan B: CI Build (Ad-Hoc only) ==="
echo "App-Pfad: $APP"
echo "Source: $SRC"

# Workspace bereinigen
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources/devispro"
mkdir -p "$APP/Contents/Resources/kataloge"

# Source kopieren
cp -R "$SRC/." "$APP/Contents/Resources/devispro/"
if [ -d "$SRC/../kataloge" ]; then
  cp -R "$SRC/../kataloge/." "$APP/Contents/Resources/kataloge/"
fi

# Info.plist kopieren
cp "$GITHUB_WORKSPACE/.github/scripts/Info.plist.template" "$APP/Contents/Info.plist"

# Version setzen wenn Tag-Push (dynamisch aus Git-Tag)
if [ -n "$GITHUB_REF_NAME" ] && [ "$GITHUB_REF_TYPE" = "tag" ]; then
  VERSION="${GITHUB_REF_NAME#v}"  # strip leading "v"
  sed -i '' "s|<string>1.4.8</string>|<string>${VERSION}</string>|g" "$APP/Contents/Info.plist"
  echo "Version auf ${VERSION} gesetzt"
fi

# Tote .so entfernen (kann Notarize brechen, aber bei ad-hoc ok)
rm -f "$APP/Contents/Resources/devispro/fpdf/fpdf*.so" 2>/dev/null || true
rm -f "$APP/Contents/Resources/devispro/segno"/*.so 2>/dev/null || true

# Version.txt
BUILD_DATE=$(date +%Y-%m-%d_%H:%M)
echo "DevisPro build $BUILD_DATE (CI-adhoc)" > "$APP/Contents/Resources/version.txt"

echo "Build done: $(du -sh "$APP" | cut -f1)"

# AD-HOC Codesign (KEIN Apple-Notarize, KEIN Developer-ID)
echo "=== Ad-Hoc Codesign (Plan B) ==="
# Erst alle nested binaries signen (ohne runtime/timestamp — geht schnell)
find "$APP" -type f \( -name "*.so" -o -name "*.dylib" -o -name "python3.11" \) 2>/dev/null | while read f; do
  codesign --force --sign - "$f" 2>/dev/null || true
done

# Dann die ganze App deep-signen
codesign --force --deep --sign - "$APP" 2>&1 | head -5
echo "Codesign done"

# Verify
codesign --verify --deep --strict "$APP" 2>&1 | head -3 || echo "verify-ok"

# ZIP erstellen
echo "=== ZIP erstellen ==="
DIST="$GITHUB_WORKSPACE/DevisPro-macOS-adhoc"
rm -rf "$DIST" "$DIST.zip"
mkdir -p "$DIST"
cp -R "$APP" "$DIST/"
cd "$GITHUB_WORKSPACE"
ditto -c -k --keepParent "$DIST" "$DIST.zip"
ls -la "$DIST.zip"
echo "ZIP erstellt: $DIST.zip"

echo "=== PLAN B BUILD DONE ==="
echo "ZIP: $DIST.zip"
echo "App: $APP"
echo "Diese Version ist AD-HOC signiert. Für Developer-ID + Notarization:"
echo "  → sign_fix.command lokal auf Mac ausführen"