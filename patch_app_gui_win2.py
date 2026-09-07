#!/usr/bin/env python3
"""Patch app_gui.py for Windows compatibility - fix temp path."""

with open('/Users/ferdinandrothlisberger/devis-auto/devispro/devispro/app_gui.py', 'r') as f:
    content = f.read()

# Fix the hardcoded temp path to use tempfile.gettempdir() dynamically
import tempfile

# Replace the hardcoded paths
old_path = '/var/folders/4r/cwlct0_s34n8zxpn974f_qd00000gn/T'
new_path = tempfile.gettempdir()

content = content.replace(old_path, new_path)

with open('/Users/ferdinandrothlisberger/devis-auto/devispro/devispro/app_gui.py', 'w') as f:
    f.write(content)

print("DONE: Fixed temp path in app_gui.py")