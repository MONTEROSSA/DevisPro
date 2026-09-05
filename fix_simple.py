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
# Rules:
# - def _analysen_xxx: 8 spaces
# - body statements: 12 spaces
# - for/if/while statements: 12 spaces (same as body)
# - for/if/while body: 16 spaces
# - continuations: +4 from current

in_nested = False
for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if not stripped:
        continue
    
    # Nested function def
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        in_nested = True
        set_indent(idx, 8)
        continue
    
    # Next class method
    if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
        in_nested = False
        continue
    
    if in_nested:
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        
        # Check current context
        # If previous line was a control structure (for/if/while/elif/else/try/except)
        prev_was_control = prev.lstrip().startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:'))
        prev_was_def = 'def _analysen_' in prev
        
        # Current line is a control structure
        is_control = stripped.startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:'))
        # Current line is a simple statement
        is_simple = not is_control and not stripped.startswith('def ')
        
        if prev_was_control or (nested_depth == 2):
            # We're inside a loop/if body
            if prev.endswith(('(', ',', '\\')):
                set_indent(idx, 17)
            else:
                set_indent(idx, 16)
            nested_depth = 2
        elif prev_was_def or (nested_depth == 1 and not is_control):
            # We're at function body level
            if prev.endswith(('(', ',', '\\')):
                set_indent(idx, 13)
            else:
                set_indent(idx, 12)
            nested_depth = 1
        elif is_control:
            # Control structure at function body level
            if prev.endswith(('(', ',', '\\')):
                set_indent(idx, 13)
            else:
                set_indent(idx, 12)
            nested_depth = 1
        else:
            # Simple statement at function body level
            if prev.endswith(('(', ',', '\\')):
                set_indent(idx, 13)
            else:
                set_indent(idx, 12)
            nested_depth = 1
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