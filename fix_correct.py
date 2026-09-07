#!/usr/bin/env python3
"""Correct fix - track depth based on PREVIOUS line's control structure."""

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
# Track depth by looking at PREVIOUS line
# depth 0 = method body (8)
# depth 1 = nested function body (12)  
# depth 2 = inside for/if/while (16)

# First, set all nested function defs to 8
nested_funcs = []
for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        nested_funcs.append(idx)
        set_indent(idx, 8)

# Now process each nested function's body
for func_idx in nested_funcs:
    # Find end of this function (next def at 8 spaces or class method at 4 spaces)
    end_idx = len(lines)
    for idx in range(func_idx + 1, min(700, len(lines))):
        stripped = lines[idx].lstrip()
        if stripped.startswith('def ') and lines[idx].startswith(' ' * 8):
            end_idx = idx
            break
        if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
            end_idx = idx
            break
    
    # Process body of this nested function
    depth = 1  # start at function body level
    for idx in range(func_idx + 1, end_idx):
        stripped = lines[idx].lstrip()
        if not stripped:
            continue
        
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        
        # Check if previous line was a control structure that starts a block
        prev_stripped = prev.lstrip()
        prev_was_control = prev_stripped.startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:')) and prev.endswith(':')
        
        # Check if current line is a control structure
        is_control = stripped.startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:'))
        is_simple = not is_control and not stripped.startswith('def ')
        
        if prev_was_control:
            depth = 2
        elif depth == 2 and not (is_control or is_simple):
            # Check for dedent (return, break, continue, or less indented)
            pass  # stay at depth 2
        
        # Apply indentation
        if prev.endswith(('(', ',', '\\')):
            set_indent(idx, 13 if depth == 1 else 17)
        elif prev.endswith(':'):
            if is_control:
                depth = 2
                set_indent(idx, 12 if depth == 1 else 16)
            else:
                set_indent(idx, 12 if depth == 1 else 16)
        else:
            set_indent(idx, 12 if depth == 1 else 16)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")