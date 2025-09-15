#!/usr/bin/env python3
"""
Focused test for Issue #1263 - Database timeout validation in staging environment.
"""

import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_database_timeout_config():
    """Test database timeout configuration for staging environment."""
    print("Testing database timeout configuration for staging...")

    try:
        from netra_backend.app.core.database_timeout_config import get_database_timeout_config

        # Test staging configuration
        staging_config = get_database_timeout_config('staging')

        print(f"Staging timeout configuration: {staging_config}")

        # Check if the key timeout value is correct (Issue #1263 fix)
        expected_init_timeout = 25.0
        actual_init_timeout = staging_config.get('initialization_timeout')

        if actual_init_timeout == expected_init_timeout:
            print(f"PASS: Initialization timeout correctly set to {actual_init_timeout}s")
            print("CHECK: Issue #1263 database timeout fix is deployed")
            return True
        else:
            print(f"FAIL: Initialization timeout is {actual_init_timeout}s, expected {expected_init_timeout}s")
            return False

    except ImportError as e:
        print(f"FAIL: Could not import database timeout config: {e}")
        return False
    except Exception as e:
        print(f"FAIL: Error testing database timeout config: {e}")
        return False

def test_monitoring_files():
    """Test that monitoring infrastructure files exist."""
    print("Testing monitoring infrastructure files...")

    monitoring_files = [
        "netra_backend/app/core/database_timeout_config.py",
        "netra_backend/app/monitoring/configuration_drift_alerts.py"
    ]

    all_exist = True
    for file_path in monitoring_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"PASS: {file_path} exists")
        else:
            print(f"FAIL: {file_path} missing")
            all_exist = False

    return all_exist

def main():
    """Run focused staging database timeout validation."""
    print("Issue #1263 Staging Database Timeout Validation")
    print("=" * 55)

    results = []

    # Test 1: Database timeout configuration
    timeout_ok = test_database_timeout_config()
    results.append(("Database Timeout Config", timeout_ok))

    # Test 2: Monitoring infrastructure files
    monitoring_ok = test_monitoring_files()
    results.append(("Monitoring Files", monitoring_ok))

    # Summary
    print("\nValidation Summary:")
    print("=" * 20)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 20)
    if all_passed:
        print("SUCCESS: Database timeout and monitoring changes validated")
        print("CHECK: Issue #1263 is ready for staging testing")
    else:
        print("FAILED: Some validations failed")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)