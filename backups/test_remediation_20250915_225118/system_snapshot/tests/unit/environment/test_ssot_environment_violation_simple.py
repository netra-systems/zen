#!/usr/bin/env python3
"""
Simple targeted test to expose the SSOT environment access violation in secret_manager_core.py.
This test should FAIL to demonstrate the violation exists.

Issue #711: Step 4 - Execute test plan to detect remaining SSOT environment access violations
"""

import pytest
import os
import sys
import re
from pathlib import Path


@pytest.mark.unit
def test_secret_manager_core_violation_exists():
    """
    Test to confirm that the SSOT violation exists in secret_manager_core.py line 47.
    This test should FAIL initially to demonstrate the violation.
    """
    # Read the secret_manager_core.py file
    secret_manager_path = Path(__file__).parent.parent.parent.parent / "netra_backend" / "app" / "core" / "secret_manager_core.py"

    assert secret_manager_path.exists(), f"Could not find secret_manager_core.py at {secret_manager_path}"

    with open(secret_manager_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for the specific violation: direct os.environ assignment
    violation_pattern = r'os\.environ\[.*?\]\s*='
    violations = []

    for line_num, line in enumerate(content.split('\n'), 1):
        if re.search(violation_pattern, line):
            violations.append((line_num, line.strip()))

    # The test should FAIL if violations are found (which they should be)
    assert len(violations) == 0, (
        f"SSOT VIOLATION DETECTED in secret_manager_core.py:\n"
        f"Found {len(violations)} direct os.environ assignments:\n" +
        "\n".join([f"  Line {line_num}: {line}" for line_num, line in violations]) +
        f"\n\nThese should be replaced with IsolatedEnvironment.set() calls.\n"
        f"The violation on line 47 should be: os.environ[secret_name] = value"
    )


@pytest.mark.unit
def test_broader_codebase_scan_for_environ_violations():
    """
    Broader scan to detect os.environ assignments in key files.
    This test should FAIL if violations exist in the target files.
    """
    base_path = Path(__file__).parent.parent.parent.parent

    # Key files to check for violations
    target_files = [
        "netra_backend/app/core/secret_manager_core.py",
        "netra_backend/app/core/secret_manager_factory.py",
        "netra_backend/app/core/secret_manager_loading.py",
        "netra_backend/app/core/secret_manager_helpers.py",
    ]

    all_violations = []
    violation_pattern = r'os\.environ\[.*?\]\s*='

    for file_path in target_files:
        full_path = base_path / file_path
        if not full_path.exists():
            continue

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for line_num, line in enumerate(content.split('\n'), 1):
                if re.search(violation_pattern, line):
                    all_violations.append((file_path, line_num, line.strip()))
        except Exception as e:
            print(f"Could not read {file_path}: {e}")

    # The test should FAIL if violations are found
    assert len(all_violations) == 0, (
        f"SSOT VIOLATIONS DETECTED in core secret manager files:\n"
        f"Found {len(all_violations)} direct os.environ assignments:\n" +
        "\n".join([f"  {file_path}:{line_num}: {line}" for file_path, line_num, line in all_violations]) +
        f"\n\nThese should be replaced with IsolatedEnvironment.set() calls."
    )


@pytest.mark.unit
def test_validation_verification():
    """
    Test to verify our detection mechanism is working.
    This should PASS to confirm the test framework is functional.
    """
    # Test our regex pattern on a known violation
    test_lines = [
        "os.environ['TEST'] = 'value'",
        "os.environ[secret_name] = value",
        "    os.environ[key] = val",
        "get_env().set('KEY', 'value')",  # This should NOT match
        "os.getenv('KEY')",  # This should NOT match
    ]

    violation_pattern = r'os\.environ\[.*?\]\s*='
    matches = []

    for line in test_lines:
        if re.search(violation_pattern, line):
            matches.append(line)

    # Should find exactly 3 violations
    expected_violations = 3
    assert len(matches) == expected_violations, (
        f"Test validation failed: Expected {expected_violations} violations, found {len(matches)}: {matches}"
    )


if __name__ == '__main__':
    print("="*80)
    print("TESTING FOR SSOT ENVIRONMENT ACCESS VIOLATIONS")
    print("="*80)
    print("These tests are designed to FAIL if violations exist.")
    print("FAILURE = Violations detected (needs remediation)")
    print("SUCCESS = No violations found (good)")
    print("="*80)

    try:
        test_validation_verification()
        print("[PASS] Test validation mechanism working correctly")
    except AssertionError as e:
        print(f"[FAIL] Test validation failed: {e}")
        sys.exit(1)

    try:
        test_secret_manager_core_violation_exists()
        print("[PASS] No violations found in secret_manager_core.py")
    except AssertionError as e:
        print(f"[FAIL] VIOLATIONS DETECTED in secret_manager_core.py:")
        print(e)
        violation_detected = True
    else:
        violation_detected = False

    try:
        test_broader_codebase_scan_for_environ_violations()
        print("[PASS] No violations found in secret manager files")
    except AssertionError as e:
        print(f"[FAIL] VIOLATIONS DETECTED in secret manager files:")
        print(e)
        violation_detected = True

    print("="*80)
    if violation_detected:
        print("RESULT: SSOT VIOLATIONS DETECTED - Remediation needed")
        print("Issue #711 Step 4: Tests successfully exposed violations")
    else:
        print("RESULT: No violations detected - Tests may need adjustment")
    print("="*80)
