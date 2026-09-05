#!/usr/bin/env python3
"""Direct fix for the exact lines shown."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    content = f.read()

lines = content.splitlines(keepends=True)

def set_indent(idx, spaces):
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# ===== _build_mehr method =====
for idx in [537, 540, 543]:
    set_indent(idx, 8)
for idx in [538, 539, 541, 542, 544, 545]:
    set_indent(idx, 13)

# ===== Class level =====
for idx in [547, 548, 549]:
    set_indent(idx, 4)

# ===== _build_analysen method =====
set_indent(550, 4)

# ===== _build_analysen body (551-592) =====
for idx in range(551, 592):
    if lines[idx].strip():
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)

# ===== Nested functions - fix exact lines =====
# Line 593: def _analysen_liste_aktualisieren at 8
set_indent(593, 8)
# Line 594: body at 12
set_indent(594, 12)
# Line 595: body at 12
set_indent(595, 12)
# Line 596: for at 12
set_indent(596, 12)
# Line 597-599: for body at 16
for idx in [597, 598, 599]:
    set_indent(idx, 16)

# Line 601: def _analysen_on_select at 8
set_indent(601, 8)
# Line 602: body at 12
set_indent(602, 12)
# Line 603: if at 12
set_indent(603, 12)
# Line 604: if body at 16
set_indent(604, 16)
# Line 605: body at 12
set_indent(605, 12)
# Line 606: if at 12
set_indent(606, 12)
# Line 607-608: if body at 16
for idx in [607, 608]:
    set_indent(idx, 16)

# Line 610: def _analysen_zeige_leer at 8
set_indent(610, 8)
# Line 611: for at 12
set_indent(611, 12)
# Line 612-614: for body at 16
for idx in [612, 613, 614]:
    set_indent(idx, 16)

# Line 616: def _analysen_zeige_detail at 8
set_indent(616, 8)
# Line 617: for at 12
set_indent(617, 12)
# Line 618-625: for body at 16
for idx in range(618, 626):
    if lines[idx].strip():
        set_indent(idx, 16)
# Line 626: if at 16
set_indent(626, 16)
# Line 627: if body at 20
set_indent(627, 20)
# Line 630: body at 16
set_indent(630, 16)
# Line 631: if at 16
set_indent(631, 16)
# Line 632-633: if body at 20
for idx in [632, 633]:
    set_indent(idx, 20)
# Line 635-644: body at 16
for idx in range(635, 645):
    if lines[idx].strip():
        set_indent(idx, 16)
# Line 637-644: list items at 20
for idx in range(637, 645):
    if lines[idx].strip():
        set_indent(idx, 20)
# Line 646-655: body at 16
for idx in range(646, 660):
    if lines[idx].strip():
        set_indent(idx, 16)
# Line 649: for at 16
set_indent(649, 16)
# Line 650-660: for body at 20
for idx in range(650, 660):
    if lines[idx].strip():
        set_indent(idx, 20)

# Rest of file - just ensure consistent 12 for nested functions
for idx in range(660, min(700, len(lines))):
    if lines[idx].strip():
        set_indent(idx, 12)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")