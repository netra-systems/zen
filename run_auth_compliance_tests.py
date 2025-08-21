"""
Standalone runner for auth service compliance tests.
This runs the tests without needing the full test infrastructure.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run tests directly
from netra_backend.tests.integration.critical_paths.test_auth_service_compliance_suite1_oauth_l4 import (
    TestDirectOAuthImplementationDetection,
)
from netra_backend.tests.integration.critical_paths.test_auth_service_compliance_suite2_bypass_l4 import (
    TestAuthServiceBypassDetection,
)
from netra_backend.tests.integration.critical_paths.test_auth_service_compliance_suite3_reimplementation_l4 import (
    TestLocalAuthReimplementationDetection,
)


def run_test_suite(test_class, suite_name):
    """Run a test suite and report results."""
    print(f"\n{'='*60}")
    print(f"Running {suite_name}")
    print('='*60)
    
    test_instance = test_class()
    passed = 0
    failed = 0
    errors = []
    
    # Get all test methods
    test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
    
    for method_name in test_methods:
        try:
            method = getattr(test_instance, method_name)
            print(f"\nRunning: {method_name}")
            method()
            print(f"  [PASSED]")
            passed += 1
        except AssertionError as e:
            print(f"  [FAILED]: {str(e)[:200]}")
            failed += 1
            errors.append((method_name, str(e)))
        except Exception as e:
            print(f"  [ERROR]: {str(e)[:200]}")
            failed += 1
            errors.append((method_name, f"ERROR: {str(e)}"))
    
    print(f"\n{suite_name} Results: {passed} passed, {failed} failed")
    
    if errors:
        print("\nDetailed Failures:")
        for test_name, error in errors[:3]:  # Show first 3 errors
            print(f"\n  {test_name}:")
            print(f"    {error[:500]}")
    
    return passed, failed


def main():
    """Run all auth compliance test suites."""
    print("\n" + "="*70)
    print("AUTH SERVICE COMPLIANCE TEST RUNNER")
    print("="*70)
    print("\nThese tests validate that all modules use the centralized AUTH SERVICE")
    print("and do not bypass or reimplement authentication locally.")
    print("\nViolations are only allowed if marked with '@auth_service_marked:' justification")
    
    total_passed = 0
    total_failed = 0
    
    # Run Suite 1: OAuth Implementation Detection
    passed, failed = run_test_suite(
        TestDirectOAuthImplementationDetection,
        "Suite 1: Direct OAuth Implementation Detection"
    )
    total_passed += passed
    total_failed += failed
    
    # Run Suite 2: Auth Service Bypass Detection
    passed, failed = run_test_suite(
        TestAuthServiceBypassDetection,
        "Suite 2: Auth Service Bypass Detection"
    )
    total_passed += passed
    total_failed += failed
    
    # Run Suite 3: Local Reimplementation Detection
    passed, failed = run_test_suite(
        TestLocalAuthReimplementationDetection,
        "Suite 3: Local Authentication Reimplementation Detection"
    )
    total_passed += passed
    total_failed += failed
    
    # Final Summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Total Tests Run: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    
    if total_failed == 0:
        print("\n[SUCCESS] All auth service compliance tests passed!")
        print("The codebase properly uses the centralized auth service.")
    else:
        print("\n[WARNING] Auth service compliance violations detected!")
        print("Review the failures above and either:")
        print("  1. Fix the code to use the auth service")
        print("  2. Add '@auth_service_marked:' justification if intentional")
    
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())