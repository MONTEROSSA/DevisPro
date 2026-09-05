@echo off
REM ============================================================
REM  DevisPro - Automatische Installation (Windows)
REM  Klick auf diese Datei -> alles laeuft von alleine.
REM ============================================================
SETLOCAL ENABLEDELAYEDEXPANSION
SET "APP_DIR=%~dp0app"
SET "PORT=5070"

echo.
echo  ========================================
echo   DevisPro Installation (Windows)
echo  ========================================
echo.

REM --- 1) Python vorhanden? ---
python --version >nul 2>&1
IF %ERRORLEVEL%==0 (
    echo [OK] Python ist bereits installiert.
    GOTO START
)

REM --- 2) Embedded Python nachladen (einmalig, automatisch) ---
SET "PYDIR=%~dp0python"
IF EXIST "%PYDIR%\python.exe" (
    echo [OK] Portable Python bereits vorhanden.
    GOTO START
)

echo [..] Python wird automatisch installiert (einmalig, kein Download durch Sie)...
SET "PYURL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
SET "PYZIP=%~dp0python-embed.zip"
powershell -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYZIP%'"
IF NOT EXIST "%PYZIP%" (
    echo [FEHLER] Python konnte nicht heruntergeladen werden. Bitte Internetverbindung pruefen.
    pause
    EXIT /B 1
)
mkdir "%PYDIR%" >nul 2>&1
powershell -Command "Expand-Archive -Path '%PYZIP%' -DestinationPath '%PYDIR%' -Force"
del "%PYZIP%"

REM pip aktivieren (in embedded python)
echo import site >> "%PYDIR%\python311._pth" 2>nul
echo [OK] Portable Python installiert.

:START
echo.
echo [..] DevisPro wird gestartet...
echo      Oeffnen Sie danach im Browser:  http://localhost:%PORT%
echo.

IF EXIST "%PYDIR%\python.exe" (
    "%PYDIR%\python.exe" "%APP_DIR%\webui.py"
) ELSE (
    python "%APP_DIR%\webui.py"
)
pause
