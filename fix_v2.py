#!/usr/bin/env python3
"""Simple, correct fix for _build_analysen indentation."""

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

# ===== Nested functions (593-700) =====
# State machine:
# depth 0 = method body
# depth 1 = nested function body
# depth 2 = inside for/if/while block

depth = 0
for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    
    # Nested function def
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        depth = 1
        set_indent(idx, 8)
        continue
    
    # Next class method (def at 4 spaces)
    if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
        depth = 0
        continue
    
    if depth == 0:
        # Method body
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13)
        else:
            set_indent(idx, 8)
    elif depth >= 1:
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        is_control = stripped.startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:'))
        is_simple = not is_control and not stripped.startswith('def ')
        
        if prev.endswith(('(', ',', '\\')):
            # Continuation
            set_indent(idx, 13 if depth == 1 else 17)
        elif prev.endswith(':'):
            # Block start
            if is_control:
                if depth == 1:
                    depth = 2
                set_indent(idx, 12 if depth == 1 else 16)
            else:
                set_indent(idx, 12 if depth == 1 else 16)
        else:
            # Simple statement
            set_indent(idx, 12 if depth == 1 else 16)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")