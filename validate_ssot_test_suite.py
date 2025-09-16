#!/usr/bin/env python3
"""
SSOT Test Suite Validation Script

Quick validation that the SSOT compliance test suite is properly configured.
"""

import sys
import os
from pathlib import Path

def validate_test_suite():
    """Validate that SSOT test suite is properly configured."""
    print("🔍 Validating SSOT Compliance Test Suite")

    # Check test file structure
    test_files = [
        "tests/unit/ssot_compliance/test_websocket_factory_elimination.py",
        "tests/unit/ssot_compliance/test_import_structure_validation.py",
        "tests/integration/ssot_compliance/test_canonical_patterns_validation.py",
        "tests/integration/websocket/test_golden_path_preservation.py",
        "tests/mission_critical/test_ssot_production_compliance.py",
        "tests/run_ssot_compliance_tests.py"
    ]

    print("📁 Checking test file structure...")
    missing_files = []
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"  ✅ {test_file}")
        else:
            print(f"  ❌ {test_file}")
            missing_files.append(test_file)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    # Check __init__.py files
    init_files = [
        "tests/unit/ssot_compliance/__init__.py",
        "tests/integration/ssot_compliance/__init__.py",
        "tests/integration/websocket/__init__.py"
    ]

    print("📦 Checking __init__.py files...")
    for init_file in init_files:
        if Path(init_file).exists():
            print(f"  ✅ {init_file}")
        else:
            print(f"  ❌ {init_file}")

    # Check baseline file
    baseline_file = "tests/mission_critical/ssot_baseline_violations.json"
    if Path(baseline_file).exists():
        print(f"  ✅ {baseline_file}")
    else:
        print(f"  ❌ {baseline_file}")

    # Validate test imports (basic syntax check)
    print("🔍 Validating test syntax...")
    try:
        import ast
        for test_file in test_files[:-1]:  # Skip the runner script
            if Path(test_file).exists():
                with open(test_file, 'r') as f:
                    content = f.read()
                ast.parse(content)
                print(f"  ✅ {test_file} - syntax OK")
    except SyntaxError as e:
        print(f"  ❌ Syntax error in {test_file}: {e}")
        return False

    print("✅ SSOT Compliance Test Suite validation completed successfully!")
    return True

if __name__ == "__main__":
    success = validate_test_suite()
    sys.exit(0 if success else 1)