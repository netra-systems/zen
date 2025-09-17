#!/usr/bin/env python3
"""
Wrapper script to run golden path tests on Windows with proper error handling.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print("=== GOLDEN PATH TESTS EXECUTION ===")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print("=" * 50)

    # Change to project directory
    os.chdir(PROJECT_ROOT)

    print("\n1. Testing Python environment and imports...")
    try:
        import pytest
        print("✅ pytest available")
    except ImportError as e:
        print(f"❌ pytest not available: {e}")
        return 1

    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        print("✅ SSotAsyncTestCase imported successfully")
    except ImportError as e:
        print(f"❌ SSotAsyncTestCase import failed: {e}")
        print("This might indicate PYTHONPATH issues")

    print("\n2. Running simplified golden path e2e test...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/e2e/golden_path/test_simplified_golden_path_e2e.py",
        "-v", "--tb=short", "-s"
    ]

    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print("\n✅ SIMPLIFIED GOLDEN PATH TEST PASSED!")
    else:
        print(f"\n❌ SIMPLIFIED GOLDEN PATH TEST FAILED (exit code: {result.returncode})")

    print("\n3. Running unified test runner with golden filter...")
    cmd = [
        sys.executable, "tests/unified_test_runner.py",
        "--category", "e2e", "--env", "staging", "--fast-fail", "--no-docker", "--filter", "golden"
    ]

    print(f"Command: {' '.join(cmd)}")
    result2 = subprocess.run(cmd, capture_output=False)

    if result2.returncode == 0:
        print("\n✅ UNIFIED TEST RUNNER WITH GOLDEN FILTER PASSED!")
    else:
        print(f"\n❌ UNIFIED TEST RUNNER WITH GOLDEN FILTER FAILED (exit code: {result2.returncode})")

    print("\n=== SUMMARY ===")
    print(f"Simplified Golden Path Test: {'PASSED' if result.returncode == 0 else 'FAILED'}")
    print(f"Unified Test Runner: {'PASSED' if result2.returncode == 0 else 'FAILED'}")

    # Return non-zero if any test failed
    return max(result.returncode, result2.returncode)

if __name__ == "__main__":
    sys.exit(main())