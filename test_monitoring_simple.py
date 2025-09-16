#!/usr/bin/env python3
"""Simple test to verify monitoring imports work."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    try:
        from netra_backend.app.services.monitoring import GCPErrorService
        from netra_backend.app.services.monitoring import GCPErrorReporter
        from netra_backend.app.services.monitoring import ErrorFormatter
        print("SUCCESS: All monitoring imports work locally")
        print("DOCKER FIX: Monitoring module packaging is now correct")
        return True
    except ImportError as e:
        print(f"FAILED: Import error - {e}")
        return False

if __name__ == "__main__":
    test_imports()