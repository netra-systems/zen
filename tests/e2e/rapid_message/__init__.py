import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
while not (PROJECT_ROOT / 'netra_backend').exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))

"""
Rapid Message Succession Test Suite

This module provides infrastructure and tests for validating message ordering,
idempotency, and state consistency under rapid message succession scenarios.
"""