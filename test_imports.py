#!/usr/bin/env python
"""
Quick test to identify import issues without running full test suite.
"""
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing basic imports...")

try:
    from shared.isolated_environment import get_env
    print("PASS: shared.isolated_environment imported successfully")
except ImportError as e:
    print(f"FAIL: shared.isolated_environment import failed: {e}")

try:
    from test_framework.test_config import configure_mock_environment
    print("PASS: test_framework.test_config imported successfully")
except ImportError as e:
    print(f"FAIL: test_framework.test_config import failed: {e}")

try:
    from netra_backend.app.dependencies import get_db
    print("PASS: netra_backend.app.dependencies imported successfully")
except ImportError as e:
    print(f"FAIL: netra_backend.app.dependencies import failed: {e}")

try:
    from netra_backend.app.main import app
    print("PASS: netra_backend.app.main imported successfully")
except ImportError as e:
    print(f"FAIL: netra_backend.app.main import failed: {e}")

try:
    # Try importing a simple e2e test to see what breaks
    sys.path.insert(0, str(PROJECT_ROOT / "tests"))
    from e2e.test_simple_agent_flow import *
    print("PASS: e2e.test_simple_agent_flow imported successfully")
except ImportError as e:
    print(f"FAIL: e2e.test_simple_agent_flow import failed: {e}")

print("Import test completed.")