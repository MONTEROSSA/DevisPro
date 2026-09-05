#!/usr/bin/env python3
"""Fix app_gui.py indentation - single run, no AI."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

# Standard indentation: class=4, method=8, continuation=13, body=8
# Fix specific problem lines (0-indexed)
fixes = {
    # card calls in _build_mehr (method body = 8 spaces)
    537: 8,   # card(2, 2, "Team & Sync"
    540: 8,   # card(3, 0, "Anbieter-Konsole"
    543: 8,   # card(3, 1, "Anleitung"
    # Continuations (13 spaces)
    538: 13, 539: 13, 541: 13, 542: 13, 544: 13, 545: 13,
    # Class-level comments (4 spaces)
    547: 4, 548: 4, 549: 4,
    # _build_analysen method def (4 spaces)
    550: 4,
    # _build_analysen body (8 spaces)
    551: 8, 552: 8, 553: 13, 554: 13, 555: 13, 556: 13, 557: 13, 558: 13, 559: 8,
}

for idx, spaces in fixes.items():
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# Fix rest of _build_analysen body (lines 560-600 approx)
for idx in range(560, min(600, len(lines))):
    stripped = lines[idx].lstrip()
    if stripped and not stripped.startswith('#'):
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            lines[idx] = ' ' * 13 + stripped
        else:
            lines[idx] = ' ' * 8 + stripped

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")