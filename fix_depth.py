#!/usr/bin/env python3
"""Correct fix - properly track nested depth for if/for inside for."""

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
# Mark all nested function defs
nested_funcs = []
for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        nested_funcs.append(idx)
        set_indent(idx, 8)

# Process each nested function body with proper depth tracking
for func_idx in nested_funcs:
    end_idx = len(lines)
    for idx in range(func_idx + 1, min(700, len(lines))):
        stripped = lines[idx].lstrip()
        if stripped.startswith('def ') and lines[idx].startswith(' ' * 8):
            end_idx = idx
            break
        if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
            end_idx = idx
            break
    
    depth = 1  # 1 = function body (12 spaces), 2 = for/if block (16), 3 = nested in for/if (20)
    
    for idx in range(func_idx + 1, end_idx):
        stripped = lines[idx].lstrip()
        if not stripped:
            continue
        
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        
        # Check what the PREVIOUS line was
        prev_stripped = prev.lstrip()
        prev_was_for_if = prev_stripped.startswith(('for ', 'if ', 'while ', 'elif ')) and prev.endswith(':')
        prev_was_else = prev_stripped.startswith(('else:', 'except', 'finally:')) and prev.endswith(':')
        prev_was_control = prev_was_for_if or prev_was_else
        
        # Check current line
        is_control = stripped.startswith(('for ', 'if ', 'while ', 'elif ')) and stripped.endswith(':')
        is_else = stripped.startswith(('else:', 'except', 'finally:'))
        is_simple = not is_control and not is_else and not stripped.startswith('def ')
        is_return = stripped.startswith(('return', 'break', 'continue'))
        
        # Update depth based on previous line
        if prev_was_control:
            depth += 1
        elif is_return:
            # return/break/continue don't change depth but are at current depth
            pass
        
        # Apply indentation
        if prev.endswith(('(', ',', '\\')):
            # Continuation
            base = {1: 12, 2: 16, 3: 20}.get(depth, 12)
            set_indent(idx, base + 4)
        elif prev.endswith(':'):
            if is_control or is_else:
                # Control structure at current depth
                base = {1: 12, 2: 16, 3: 20}.get(depth, 12)
                set_indent(idx, base)
                if is_control:
                    depth += 1
            else:
                # Function def or other
                base = {1: 12, 2: 16, 3: 20}.get(depth, 12)
                set_indent(idx, base)
        else:
            # Simple statement
            base = {1: 12, 2: 16, 3: 20}.get(depth, 12)
            set_indent(idx, base)

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")