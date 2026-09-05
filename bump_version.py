#!/usr/bin/env python3
"""Anbieter-Tool: Version erhoehen + version.json fuer devispro.ch erzeugen.

Ablauf bei einer neuen Veroeffentlichung:
  1. python3 bump_version.py --major|--minor|--patch
     (erhoeht devispro/version.py VERSION und aktualisiert version.json)
  2. Changelog-Notizen fuer de/fr/it im Prompt eingeben (oder --notes-de ...)
  3. version.json auf https://devispro.ch/version.json hochladen
  -> alle KMU-Installationen zeigen beim naechsten Oeffnen das Update-Banner

Ohne Argumente zeigt es die aktuelle Version.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VER_FILE = os.path.join(HERE, "devispro", "version.py")
JSON_OUT = os.path.join(HERE, "version.json")
DOWNLOAD = "https://devispro.ch"


def read_version():
    src = open(VER_FILE, "r", encoding="utf-8").read()
    m = re.search(r'VERSION\s*=\s*"([^"]+)"', src)
    return m.group(1) if m else "0.0.0"


def bump(v, kind):
    a, b, c = (int(x) for x in v.split("."))
    if kind == "major":
        a, b, c = a + 1, 0, 0
    elif kind == "minor":
        b, c = b + 1, 0
    else:
        c += 1
    return f"{a}.{b}.{c}"


def write_version(v):
    src = open(VER_FILE, "r", encoding="utf-8").read()
    src = re.sub(r'(VERSION\s*=\s*")[^"]+(")', r'\g<1>' + v + r'\g<2>', src)
    open(VER_FILE, "w", encoding="utf-8").write(src)


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Aktuelle Version:", read_version())
        print("Usage: bump_version.py [--major|--minor|--patch] [--notes-de '...'] [--notes-fr '...'] [--notes-it '...']")
        return
    kind = "patch"
    for a in ("--major", "--minor", "--patch"):
        if a in args:
            kind = a.lstrip("-")
    cur = read_version()
    new = bump(cur, kind)
    write_version(new)
    notes = {"de": [], "fr": [], "it": []}
    for suf in ("de", "fr", "it"):
        key = f"--notes-{suf}"
        for i, a in enumerate(args):
            if a == key and i + 1 < len(args):
                notes[suf].extend(
                    x.strip() for x in args[i + 1].split("|") if x.strip()
                )
    import json
    from datetime import date
    doc = {
        "version": new,
        "channel": "stable",
        "released": date.today().isoformat(),
        "download_url": DOWNLOAD,
        "notes": notes,
    }
    json.dump(doc, open(JSON_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Version {cur} -> {new}")
    print(f"version.json geschrieben: {JSON_OUT}")
    print("Jetzt version.json auf https://devispro.ch/ hochladen.")


if __name__ == "__main__":
    main()
