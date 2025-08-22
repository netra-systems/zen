import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
while not (PROJECT_ROOT / 'netra_backend').exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

"""
Midstream Disconnection Recovery Test Suite.

This package contains focused test modules for validating midstream disconnection handling:
- Text streaming recovery
- JSON streaming integrity 
- Multipart response delivery
- Buffer recovery mechanisms

All tests maintain <300 lines and <8 lines per test function.
"""