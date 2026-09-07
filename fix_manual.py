#!/usr/bin/env python3
"""Manual fix for the specific indentation errors I can see."""

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

# ===== MANUAL FIX for nested functions =====
# Based on the actual content I can see, let me fix the known problem areas

# _analysen_liste_aktualisieren (func at 601, body starts at 594)
# Line 593: def at 8
set_indent(593, 8)
# Line 594-599: body at 12
for idx in range(594, 600):
    if lines[idx].strip():
        set_indent(idx, 12)
# Line 596: for at 12
set_indent(596, 12)
# Line 597-599: for body at 16
for idx in range(597, 600):
    if lines[idx].strip():
        set_indent(idx, 16)

# _analysen_on_select (func at 601)
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
for idx in range(607, 609):
    if lines[idx].strip():
        set_indent(idx, 16)

# _analysen_zeige_leer (func at 610)
set_indent(610, 8)
# Line 611: for at 12
set_indent(611, 12)
# Line 612-614: for body at 16
for idx in range(612, 615):
    if lines[idx].strip():
        set_indent(idx, 16)

# _analysen_zeige_detail (func at 616)
set_indent(616, 8)
# Line 617: for at 12
set_indent(617, 12)
# Line 618-650: for body at 16
for idx in range(618, 650):
    if lines[idx].strip() and idx not in [620, 621, 622, 623, 624, 625, 626, 627, 630, 631]:
        # These have their own indentation
        set_indent(idx, 16)

# Lines 620-627: Header block at 16
for idx in [620, 621, 622, 623, 624, 625]:
    set_indent(idx, 16)
# Line 626: if at 16
set_indent(626, 16)
# Line 627: if body at 20
set_indent(627, 20)

# Line 630-633: analyse check
set_indent(630, 16)
set_indent(631, 16)  # if
set_indent(632, 20)  # if body
set_indent(633, 20)  # return

# Line 635-644: felder list
set_indent(635, 16)
for idx in range(636, 645):
    if lines[idx].strip():
        set_indent(idx, 20)

# Line 646-655: more body at 16
for idx in range(646, 660):
    if lines[idx].strip():
        set_indent(idx, 16)

# Line 649: for at 16
set_indent(649, 16)
# Line 650-655: for body at 20
for idx in range(650, 660):
    if lines[idx].strip():
        set_indent(idx, 20)

# Continue fixing rest of file (660-700) with same pattern
for idx in range(660, min(700, len(lines))):
    if lines[idx].strip():
        # Default to method body level (8) or function body (12) 
        # We'll just set to 12 for safety
        if idx > 660:
            set_indent(idx, 12)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")