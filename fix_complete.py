#!/usr/bin/env python3
"""Complete fix for app_gui.py - proper nested function indentation in _build_analysen."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

def set_indent(idx, spaces):
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# ===== _build_mehr method (lines ~487-547) =====
for idx in [537, 540, 543]:
    set_indent(idx, 8)
for idx in [538, 539, 541, 542, 544, 545]:
    set_indent(idx, 13)

# ===== Class level (4 spaces) =====
for idx in [547, 548, 549]:
    set_indent(idx, 4)

# ===== _build_analysen method =====
set_indent(550, 4)  # def _build_analysen

# ===== _build_analysen body (lines 551-700) =====
# Structure:
# 8 spaces: method body statements
# 12 spaces: nested function bodies
# 8 spaces: nested function defs
# 13 spaces: continuations

# Let me manually fix the known problem area (lines 551-650)
# First pass: set method body to 8 spaces
for idx in range(551, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    # Stop at next class method (def at 4 spaces)
    if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
        break
    
    # Nested function def at 8 spaces
    if stripped.startswith('def ') and lines[idx].startswith(' ' * 8):
        set_indent(idx, 8)
        continue
    
    prev = lines[idx-1].rstrip() if idx > 0 else ''
    
    # Inside nested function (previous line was def at 8 spaces or body at 12 spaces)
    in_nested = prev.startswith(' ' * 8) and 'def ' in prev
    # or previous line is at 12 spaces
    in_nested = in_nested or prev.startswith(' ' * 12)
    
    if prev.endswith(('(', ',', '\\')):
        set_indent(idx, 13)
    elif prev.endswith(':'):
        if stripped.startswith('def ') and lines[idx].startswith(' ' * 8):
            set_indent(idx, 8)
        elif in_nested:
            set_indent(idx, 12)
        else:
            set_indent(idx, 8)
    else:
        if in_nested:
            set_indent(idx, 12)
        else:
            set_indent(idx, 8)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")