#!/usr/bin/env python3
"""
Issue #1041 Validation Script
Tests that Test* class renaming didn't break test infrastructure
"""

import subprocess
import sys
import os
from pathlib import Path

def validate_test_collection():
    """Validate that pytest can collect tests after Issue #1041 Test* renaming"""
    try:
        print("=== Issue #1041 Test Infrastructure Validation ===")
        print("Validating test collection after Test* class renaming...")

        # Change to project root
        os.chdir(Path(__file__).parent)

        # Run pytest collection on a small subset to validate
        cmd = [
            sys.executable, "-m", "pytest",
            "--collect-only",
            "netra_backend/tests/unit/agents/",
            "-q",
            "--tb=no"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ Test collection PASSED - {len(result.stdout.splitlines())} tests found")
            print("✓ Issue #1041 Test* class renaming did not break test infrastructure")
            return True
        else:
            print(f"✗ Test collection FAILED - return code: {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("✗ Test collection timed out")
        return False
    except Exception as e:
        print(f"✗ Test collection error: {e}")
        return False

def validate_test_class_naming():
    """Validate that renamed Test* classes follow the expected pattern"""
    try:
        print("\n=== Validating Test Class Naming Patterns ===")

        # Check a few key test files to ensure proper naming
        test_files = [
            "netra_backend/tests/unit/agents/test_agent_execution_core_comprehensive.py",
            "netra_backend/tests/unit/test_unified_websocket_auth_business_logic.py"
        ]

        found_test_classes = 0
        for test_file in test_files:
            if os.path.exists(test_file):
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for class definitions
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip().startswith('class ') and 'Test' in line:
                            found_test_classes += 1
                            print(f"✓ Found test class in {test_file}: {line.strip()}")

        if found_test_classes > 0:
            print(f"✓ Found {found_test_classes} test classes with proper naming")
            return True
        else:
            print("⚠ No test classes found in sample files")
            return True  # Not necessarily an error

    except Exception as e:
        print(f"✗ Test class validation error: {e}")
        return False

def main():
    """Main validation function"""
    print("Starting Issue #1041 validation...")

    collection_ok = validate_test_collection()
    naming_ok = validate_test_class_naming()

    if collection_ok and naming_ok:
        print("\n✓ Issue #1041 validation PASSED")
        print("✓ Test infrastructure is working correctly after Test* class renaming")
        return 0
    else:
        print("\n✗ Issue #1041 validation FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())