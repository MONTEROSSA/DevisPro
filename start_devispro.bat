@echo off
chcp 65001 >nul
REM ============================================================
REM DevisPro - Starter fuer Windows
REM Startet die lokale Web-UI (http://localhost:5070).
REM Benoetigt Python 3.9+. Falls nicht vorhanden, wird eine
REM portable Embedded-Python automatisch heruntergeladen.
REM ============================================================

setlocal
set "PORT=5070"
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM --- 1) Python suchen (py -> python3 -> python) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  where python3 >nul 2>nul && set "PY=python3"
)

REM --- 2) Falls kein Python: Embedded-Download (portabel, kein Install) ---
if not defined PY (
  echo Python wurde nicht gefunden. Lade portable Python herunter ...
  set "EMB_DIR=%APP_DIR%python-embed"
  if not exist "%EMB_DIR%\python.exe" (
    powershell -NoProfile -Command ^
      "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '%TEMP%\py_embed.zip'; Expand-Archive -Force '%TEMP%\py_embed.zip' '%EMB_DIR%'"
    if not exist "%EMB_DIR%\python.exe" (
      echo FEHLER: Embedded-Python konnte nicht geladen werden.
      echo Bitte installieren Sie Python 3.9+ von https://python.org und aktivieren Sie „Add to PATH".
      pause
      exit /b 1
    )
    REM pip aktivieren (embedded hat kein pip) - nur falls noetig; webui.py nutzt reine Stdlib
  )
  set "PY=%EMB_DIR%\python.exe"
)

REM --- 3) Port freimachen ---
taskkill /f /im python.exe >nul 2>nul
timeout /t 1 >nul

REM --- 4) Server starten ---
start "" "%PY%" "%APP_DIR%webui.py"
timeout /t 3 >nul

REM --- 5) Browser oeffnen ---
start "" "http://localhost:%PORT%/"

echo DevisPro gestartet. Browser auf http://localhost:%PORT%/
echo Zum Beenden: dieses Fenster schliessen.
pause
endlocal
