#!/usr/bin/env python3
"""Complete fix for app_gui.py - proper nested function indentation."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

def set_indent(idx, spaces):
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# ===== _build_mehr method (lines ~487-547) - method body = 8 spaces =====
for idx in [537, 540, 543]:
    set_indent(idx, 8)
for idx in [538, 539, 541, 542, 544, 545]:
    set_indent(idx, 13)

# ===== Class level (4 spaces) =====
for idx in [547, 548, 549]:
    set_indent(idx, 4)

# ===== _build_analysen method =====
set_indent(550, 4)  # def _build_analysen

# Method body (8 spaces), continuations (13 spaces)
# Process lines 551-700
for idx in range(551, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    # Check if we're at next class method (def at 4 spaces)
    if stripped.startswith('def ') and idx > 551 and lines[idx].startswith('    '):
        break
    # Check if nested function (def at 8 spaces)
    if stripped.startswith('def ') and lines[idx].startswith(' ' * 8):
        set_indent(idx, 8)  # nested function def at method body level
        continue
    prev = lines[idx-1].rstrip() if idx > 0 else ''
    if prev.endswith(('(', ',', '\\')):
        set_indent(idx, 13)
    elif prev.endswith(':'):
        # Body of function/if/for - 12 spaces for nested, 8 for method
        if stripped.startswith('def '):
            set_indent(idx, 8)
        elif lines[idx-1].startswith(' ' * 8) and 'def ' in lines[idx-1]:
            set_indent(idx, 12)
        else:
            set_indent(idx, 8)
    else:
        set_indent(idx, 8)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")