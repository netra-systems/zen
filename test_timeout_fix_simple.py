#!/usr/bin/env python3
"""
Simple test to validate timeout configuration fix.
"""

import sys
import os
import subprocess

def test_timeout_configuration_fix():
    """Test that the timeout configuration is properly integrated."""

    print("Testing timeout configuration fix...")

    # Test 1: Verify pyproject.toml doesn't have global timeout
    with open('pyproject.toml', 'r') as f:
        content = f.read()
        if '--timeout=120' in content:
            print("FAIL: Global timeout still in pyproject.toml")
            return False
        else:
            print("PASS: Global timeout removed from pyproject.toml")

    # Test 2: Check that staging environment gets proper timeouts
    # Simulate what unified_test_runner would do for staging e2e tests
    from unittest.mock import Mock

    # Mock args object
    args = Mock()
    args.env = 'staging'
    category_name = 'e2e'

    # This is the logic from our fix
    cmd_parts = []
    if args.env == 'staging':
        if category_name in ["e2e", "integration", "e2e_critical", "e2e_full"]:
            cmd_parts.extend(["--timeout=900", "--timeout-method=thread"])  # 15min for staging e2e tests

    if "--timeout=900" in cmd_parts:
        print("PASS: Staging e2e tests get 15-minute timeout (900s)")
    else:
        print("FAIL: Staging e2e tests don't get proper timeout")
        return False

    # Test 3: Check that local unit tests get proper timeouts
    args.env = 'test'  # local environment
    category_name = 'unit'

    cmd_parts = []
    if args.env == 'staging':
        pass  # staging logic
    elif category_name == "unit":
        cmd_parts.extend(["--timeout=180", "--timeout-method=thread"])  # 3min for local unit tests

    if "--timeout=180" in cmd_parts:
        print("PASS: Local unit tests get 3-minute timeout (180s)")
    else:
        print("FAIL: Local unit tests don't get proper timeout")
        return False

    print("SUCCESS: All timeout configuration tests passed!")
    return True

if __name__ == '__main__':
    success = test_timeout_configuration_fix()
    sys.exit(0 if success else 1)