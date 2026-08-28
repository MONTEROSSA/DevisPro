#!/usr/bin/env python3
"""DevisPro Windows Entry Point - minimal, keine zirkulären Imports."""

import os
import sys

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Now import the actual app
from devispro.app_gui import main

if __name__ == "__main__":
    main()