#!/usr/bin/env python3
"""Patch app_gui.py for Windows compatibility."""

with open('/Users/ferdinandrothlisberger/devis-auto/devispro/devispro/app_gui.py', 'r') as f:
    content = f.read()

# Replace /tmp with platform-independent temp directory
import tempfile
tmpdir = tempfile.gettempdir()

content = content.replace(
    'with open("/tmp/devispro_geom.txt", "w") as f:',
    f'with open(os.path.join("{tmpdir}", "devispro_geom.txt"), "w") as f:'
)

content = content.replace(
    'open("/tmp/devispro_geom.txt", "w").write("ERR %s\\n" % e)',
    f'open(os.path.join("{tmpdir}", "devispro_geom.txt"), "w").write("ERR %s\\n" % e)'
)

# Add import os if not present (it is)
# Disable the diagnostic dump on Windows by making it conditional
content = content.replace(
    '        # diagnose: echte geomentrie auf dem laufenden mac messen\n        self.after(1500, self._diag_dump)',
    '        # diagnose: skip on Windows\n        # self.after(1500, self._diag_dump)'
)

with open('/Users/ferdinandrothlisberger/devis-auto/devispro/devispro/app_gui.py', 'w') as f:
    f.write(content)

print("DONE: Patched app_gui.py for Windows")