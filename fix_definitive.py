#!/usr/bin/env python3
"""Definitive fix - proper state machine for nested indentation."""

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
# Find all nested function defs
nested_funcs = []
for idx in range(592, min(700, len(lines))):
    stripped = lines[idx].lstrip()
    if stripped.startswith('def _analysen_') and lines[idx].startswith(' ' * 8):
        nested_funcs.append(idx)
        set_indent(idx, 8)

# Process each nested function with proper state machine
for func_idx in nested_funcs:
    # Find end of this function
    end_idx = len(lines)
    for idx in range(func_idx + 1, min(700, len(lines))):
        stripped = lines[idx].lstrip()
        if stripped.startswith('def ') and lines[idx].startswith(' ' * 8):
            end_idx = idx
            break
        if stripped.startswith('def ') and lines[idx].startswith('    ') and not lines[idx].startswith(' ' * 8):
            end_idx = idx
            break
    
    # State: stack of indentation levels
    # Each level: (indent_spaces, is_block_start)
    # Start with function body at 12 spaces
    indent_stack = [(12, True)]  # function body starts at 12
    
    for idx in range(func_idx + 1, end_idx):
        stripped = lines[idx].lstrip()
        if not stripped:
            continue
        
        prev = lines[idx-1].rstrip() if idx > 0 else ''
        prev_stripped = prev.lstrip()
        
        # Check for dedent triggers (return, break, continue, elif, else, except, finally)
        is_dedent = stripped.startswith(('return', 'break', 'continue', 'elif ', 'else:', 'except', 'finally:'))
        is_elif_else = stripped.startswith(('elif ', 'else:', 'except', 'finally:'))
        
        # Check if previous line ended a block
        prev_was_simple = prev_stripped and not prev_stripped.startswith(('for ', 'if ', 'while ', 'def ', 'elif ', 'else:', 'try:', 'except', 'finally:')) and not prev.endswith(':') and not prev.endswith(('(', ',', '\\'))
        
        # Pop stack if we're dedenting
        if is_dedent and not is_elif_else:
            # return/break/continue - pop one level
            if len(indent_stack) > 1:
                indent_stack.pop()
        elif is_elif_else:
            # elif/else/except/finally - same level as matching if/try
            if len(indent_stack) > 1:
                indent_stack[-1] = (indent_stack[-1][0], False)
        
        # Get current indent
        current_indent = indent_stack[-1][0] if indent_stack else 12
        
        # Check if previous line was a block start (ended with :)
        prev_was_block = prev.endswith(':') and prev_stripped.startswith(('for ', 'if ', 'while ', 'elif ', 'else:', 'try:', 'except', 'finally:', 'def '))
        
        if prev_was_block:
            # Push new level
            new_indent = current_indent + 4
            indent_stack.append((new_indent, True))
            set_indent(idx, new_indent)
        elif prev.endswith(('(', ',', '\\')):
            # Continuation
            set_indent(idx, current_indent + 4)
        else:
            # Simple statement
            set_indent(idx, current_indent)
            
            # Check if this line starts a new block
            if stripped.startswith(('for ', 'if ', 'while ', 'try:')) and stripped.endswith(':'):
                # Will be handled on next iteration via prev_was_block
                pass

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("DONE")