#!/usr/bin/env python3
"""Complete fix for app_gui.py indentation."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

def set_indent(idx, spaces):
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# ===== _build_mehr method (lines 487-547) - method body = 8 spaces =====
# card calls at method level
for idx in [537, 540, 543]:
    set_indent(idx, 8)
# continuations
for idx in [538, 539, 541, 542, 544, 545]:
    set_indent(idx, 13)

# ===== Class level (4 spaces) =====
for idx in [547, 548, 549]:
    set_indent(idx, 4)

# ===== _build_analysen method =====
set_indent(550, 4)  # def _build_analysen

# Method body (8 spaces), continuations (13 spaces)
# We'll process lines 551-650
in_method = True
for idx in range(551, min(650, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    # Check if we're still in _build_analysen (next method starts with 'def ' at 4 spaces)
    if stripped.startswith('def ') and not lines[idx].startswith(' ' * 8):
        in_method = False
        break
    if in_method:
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")