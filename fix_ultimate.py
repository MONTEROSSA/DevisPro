#!/usr/bin/env python3
"""Final fix - proper indentation for nested function bodies with loops/ifs."""

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

def set_indent(idx, spaces):
    if idx < len(lines):
        lines[idx] = ' ' * spaces + lines[idx].lstrip()

# ===== _build_mehr method (lines 537-547) =====
for idx in [537, 540, 543]:
    set_indent(idx, 8)
for idx in [538, 539, 541, 542, 544, 545]:
    set_indent(idx, 13)

# ===== Class level (4 spaces) =====
for idx in [547, 548, 549]:
    set_indent(idx, 4)

# ===== _build_analysen method =====
set_indent(550, 4)

# ===== _build_analysen body (lines 551-592) - 8 spaces =====
for idx in range(551, 592):
    stripped = lines[idx].lstrip()
    if stripped and not stripped.startswith('#'):
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)

# ===== Nested functions (lines 593-700) =====
# Structure:
# - def at 8 spaces
# - body at 12 spaces  
# - for/if/while body at 16 spaces
# - continuations at 13 spaces (or 17 if in loop)

in_nested = False
nested_depth = 0  # 0=method, 1=nested func, 2=in loop/if

for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    
    # Check for nested function definition
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        in_nested = True
        nested_depth = 1
        set_indent(idx, 8)
        continue
    
    # Check for next class method
    if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
        in_nested = False
        nested_depth = 0
    
    if in_nested:
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        
        # Detect loop/if start
        if stripped.startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:')):
            nested_depth = 2
        
        # Detect dedent (return, break, continue, or less indent)
        if stripped.startswith(('return', 'break', 'continue')):
            pass  # stay at current depth
        
        # Apply indentation
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13 if nested_depth == 1 else 17)
        elif prev.endswith(':'):
            if nested_depth == 1:
                set_indent(idx, 12)
            else:
                set_indent(idx, 16)
        else:
            if nested_depth == 1:
                set_indent(idx, 12)
            else:
                set_indent(idx, 16)
    else:
        # Method body
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")