"""Entry-Point:  python -m devispro   startet die DevisPro-Web-Oberflaeche.

Plattformuebergreifend (macOS/Windows/Linux), reine Stdlib.
Oeffnet Port 5070 (oder $PORT). Im Browser: http://localhost:5070

Hinweis: webui.py liegt im Projekt-Root (nicht im Paket devispro/),
daher laden wir es ueber die Datei und fuehren es aus.
"""

import os
import sys
import runpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBUI = os.path.join(ROOT, "webui.py")

if __name__ == "__main__":
    # webui.py startet bei Ausfuehrung den HTTPServer (if __name__ == "__main__")
    runpy.run_path(WEBUI, run_name="__main__")
