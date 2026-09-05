#!/usr/bin/env python3
"""KMU-Installer fuer DevisPro (lokal, ohne Cloud, plattformuebergreifend: macOS & Windows).

Was er macht:
  1. Python-Version pruefen (>= 3.8)
  2. Abhaengigkeiten: openpyxl optional (Excel-Upload), sonst reine Stdlib
  3. Port waehlbar (default 5070)
  4. Erstellt start_devispro.command (macOS) und start_devispro.bat (Windows)
     zum Doppelklick-Starten
  5. Startet den Server und gibt die Adresse aus

Start:  python3 install_kmu.py   (danach Doppelklick auf den passenden Launcher)
"""
import os
import sys
import subprocess
import webbrowser
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "5070"))


def check_python():
    v = sys.version_info
    if (v.major, v.minor) < (3, 8):
        print("FEHLER: Python 3.8+ wird benoetigt (aktuell %d.%d)." % (v.major, v.minor))
        sys.exit(1)
    print(f"OK Python {v.major}.{v.minor}.{v.micro}")


def check_openpyxl():
    try:
        import openpyxl  # noqa: F401
        print("OK openpyxl vorhanden (Excel-Upload aktiv)")
    except ImportError:
        print("Hinweis: openpyxl fehlt -> Excel-Upload inaktiv. Aktivieren mit:")
        print("   python3 -m pip install --user openpyxl")


def write_launcher():
    # macOS: Doppelklick-Starter (.command)
    cmd = os.path.join(HERE, "start_devispro.command")
    content = (
        "#!/bin/bash\n"
        f'cd "{HERE}"\n'
        "PORT=5070 exec python3 webui.py\n"
    )
    with open(cmd, "w") as f:
        f.write(content)
    os.chmod(cmd, 0o755)
    print(f"OK macOS-Launcher erstellt: {cmd}")
    # Windows: Doppelklick-Starter (.bat)
    bat = os.path.join(HERE, "start_devispro.bat")
    batcontent = (
        "@echo off\n"
        f'cd /d "{HERE}"\n'
        "set PORT=5070\n"
        "python webui.py\n"
        "pause\n"
    )
    with open(bat, "w") as f:
        f.write(batcontent)
    print(f"OK Windows-Launcher erstellt: {bat}")


def main():
    print("=== DevisPro KMU-Setup ===")
    check_python()
    check_openpyxl()
    write_launcher()

    env = dict(os.environ)
    env["PORT"] = str(PORT)
    print(f"Starte DevisPro auf Port {PORT} ...")
    proc = subprocess.Popen([sys.executable, "webui.py"], env=env, cwd=HERE)
    time.sleep(2)
    url = f"http://localhost:{PORT}"
    try:
        import http.client
        h = http.client.HTTPConnection("127.0.0.1", PORT, timeout=4)
        h.request("GET", "/")
        code = h.getresponse().status
        if code == 200:
            print(f"ERFOLG: {url}")
            webbrowser.open(url)
        else:
            print(f"WARN: Server antwortet mit {code}")
    except Exception as e:
        print(f"WARN: Server nicht erreichbar ({e})")
    print("\nServer laeuft. Zum Beenden dieses Fenster schliessen.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()


if __name__ == "__main__":
    main()
