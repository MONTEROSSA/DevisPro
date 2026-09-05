"""Validierung des SIA-451-Positional-Layouts (crb.py WIDTHS).

Prueft, dass eine Datei dem erwarteten Spaltenlayout entspricht, bevor sie
in Sorba importiert wird. Gibt eine Liste von Fehlern zurueck (leer = OK).
"""
from .parsers import crb


def validate(path: str) -> list:
    issues = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f if ln.strip()]
    except OSError as e:
        return [f"Datei nicht lesbar: {e}"]

    if not lines:
        return ["Datei ist leer."]

    if not any(ln[:2] == "01" for ln in lines):
        issues.append("Fehlender Kopfsatz (Zeile 01).")

    types_seen = set()
    for i, ln in enumerate(lines, 1):
        if not ln:
            continue
        typ = ln[:2]
        types_seen.add(typ)
        if typ == "11":
            # qty muß numerisch (Rappen) sein
            qty = ln[54:64].strip()
            try:
                int(qty)
            except ValueError:
                issues.append(f"Zeile {i} (Typ 11): Menge '{qty}' ist nicht numerisch.")
        elif typ == "31":
            up = ln[14:24].strip()
            try:
                int(up)
            except ValueError:
                issues.append(f"Zeile {i} (Typ 31): EP '{up}' ist nicht numerisch.")
        elif typ not in ("01", "99"):
            issues.append(f"Zeile {i}: unbekannter Zeilentyp '{typ}'.")

    if "99" not in types_seen:
        issues.append("Fehlender Abschlusssatz (Zeile 99).")
    return issues
