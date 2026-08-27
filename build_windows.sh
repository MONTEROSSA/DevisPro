#!/bin/bash
# build_windows.sh — Build DevisPro für Windows (via PyInstaller)
# Läuft auf Windows (GitHub Actions / Windows Runner) oder via Wine auf Mac/Linux

set -e

echo "=== DevisPro Windows Build ==="

# Prerequisites check
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
rm -rf build dist DevisPro_Windows

# Create spec file
cat > DevisPro.spec << 'SPEC'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['devispro/app_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('devispro', 'devispro'),
        ('../Resources/tesseract', 'tesseract'),
        ('../Resources/devispro', 'devispro'),
    ],
    hiddenimports=[
        'customtkinter',
        'darkdetect',
        'packaging',
        'PIL',
        'pypdfium2',
        'cryptography',
        'requests',
        'pandas',
        'openpyxl',
        'lxml',
        'crypto_rsa',
        'license_admin',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'test',
        'unittest',
        'pdb',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Filter out unwanted binaries
a.binaries = [x for x in a.binaries if not any(bad in x[0] for bad in ['test', 'Test', '__pycache__'])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DevisPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI app - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='devispro/icon.ico' if os.path.exists('devispro/icon.ico') else None,
)

app = BUNDLE(
    exe,
    name='DevisPro.app',
    icon='devispro/icon.ico' if os.path.exists('devispro/icon.ico') else None,
    bundle_identifier='ch.devispro.app',
    info_plist={
        'CFBundleName': 'DevisPro',
        'CFBundleDisplayName': 'DevisPro',
        'CFBundleVersion': '1.3.1',
        'CFBundleShortVersionString': '1.3.1',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
    },
)
SPEC

# Build
echo "Building with PyInstaller..."
pyinstaller --clean DevisPro.spec

# Create distribution folder
mkdir -p DevisPro_Windows
cp -r dist/DevisPro/* DevisPro_Windows/

# Create README for Windows
cat > DevisPro_Windows/README.txt << 'README'
DevisPro für Windows
====================

Installation:
1. Entpacken Sie dieses Archiv an einen beliebigen Ort
2. Doppelklicken Sie auf DevisPro.exe

Systemvoraussetzungen:
- Windows 10/11 (64-bit)
- Keine zusätzliche Installation nötig (Python, Tesseract, alle Libraries sind enthalten)

Erster Start:
- Beim ersten Start kann Windows SmartScreen warnen → "Weitere Informationen" → "Trotzdem ausführen"
- Die App startet im Dark Mode (passend zur Landingpage)

Support: info@devispro.de
Web: www.devispro.de
README

# Create ZIP for distribution
cd DevisPro_Windows
zip -r ../DevisPro_Windows.zip .
cd ..

echo "=== Build complete ==="
echo "Output: DevisPro_Windows/ and DevisPro_Windows.zip"
SPEC