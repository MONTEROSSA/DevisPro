#!/usr/bin/env python3
"""Surgical fix for _build_analysen nested functions."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

def set_indent(idx, spaces):
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# Fix known lines in _build_analysen (551-700)
# Method body: 8 spaces
# Nested function def: 8 spaces
# Nested function body: 12 spaces
# Continuations: 13 spaces

# Lines 551-592: method body (8 spaces)
for idx in range(551, 592):
    stripped = lines[idx].lstrip()
    if stripped and not stripped.startswith('#'):
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)

# Lines 593-700: nested functions
# Each nested function: def at 8, body at 12
in_nested = False
for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    
    # Check for nested function definition
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        in_nested = True
        set_indent(idx, 8)
        continue
    
    # Check for next class method (def at 4 spaces)
    if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
        in_nested = False
    
    if in_nested:
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        elif prev.endswith(':'):
            set_indent(idx, 12)
        else:
            set_indent(idx, 12)
    else:
        # Back to method body
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")