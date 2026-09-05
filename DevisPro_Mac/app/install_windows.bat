@echo off
REM ============================================================
REM  DevisPro - Windows Installer / Starter
REM  Ein Produkt der Monterossa AG (devispro.ch)
REM  Doppelklick -> prueft Python, startet DevisPro.
REM ============================================================
SET HERE=%~dp0

REM 1) Python vorhanden?
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo FEHLER: Python 3.8+ ist nicht installiert.
    echo Laden Sie es von https://www.python.org/downloads/ (Haekchen bei "Add Python to PATH").
    pause
    exit /b 1
)

REM 2) Launcher sicherstellen
IF NOT EXIST "%HERE%start_devispro.bat" (
    echo Erstelle start_devispro.bat ...
    echo @echo off > "%HERE%start_devispro.bat"
    echo cd /d "%HERE%" >> "%HERE%start_devispro.bat"
    echo set PORT=5070 >> "%HERE%start_devispro.bat"
    echo python webui.py >> "%HERE%start_devispro.bat"
    echo pause >> "%HERE%start_devispro.bat"
)

REM 3) Server starten
cd /d "%HERE%"
set PORT=5070
echo Starte DevisPro auf http://localhost:5070 ...
start "" http://localhost:5070
python webui.py
pause
