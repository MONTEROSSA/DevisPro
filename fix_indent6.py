with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'r') as f:
    lines = f.readlines()

# The class method body uses 8 spaces (4 for class + 4 for method)
# Continuation lines use 13 spaces (8 + 5)

# Fix lines 538, 541, 544 (card calls) to 8 spaces
for idx in [537, 540, 543]:
    lines[idx] = ' ' * 8 + lines[idx].lstrip()

# Fix continuation lines to 13 spaces
for idx in [538, 539, 541, 542, 544, 545]:
    lines[idx] = ' ' * 13 + lines[idx].lstrip()

# Class level (comments, method defs) = 4 spaces
for idx in [547, 548, 549]:  # comments
    lines[idx] = ' ' * 4 + lines[idx].lstrip()

# _build_analysen method def = 4 spaces (class method)
lines[550] = ' ' * 4 + lines[550].lstrip()

# _build_analysen body = 8 spaces
for idx in range(551, 570):
    if idx < len(lines):
        stripped = lines[idx].lstrip()
        if stripped:
            # Check if continuation (previous line ends with ( or ,)
            prev = lines[idx-1].rstrip() if idx > 0 else ''
            if prev.endswith(('(', ',', '\\')):
                lines[idx] = ' ' * 13 + stripped
            else:
                lines[idx] = ' ' * 8 + stripped

with open('/Users/ferdinandrothlisberger/Desktop/DevisPro.app/Contents/Resources/devispro/app_gui.py', 'w') as f:
    f.writelines(lines)

print("Fixed to standard 4/8/13 space indentation")