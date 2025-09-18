#!/usr/bin/env python
"""
Golden Path Phase 2 Test Runner

Quick execution script for running the critical Golden Path Phase 2 regression prevention test.
This script validates 500K+ ARR protection during MessageRouter proxy removal.

Usage:
    python tests/e2e/staging/run_golden_path_phase2_test.py [--quick | --full | --baseline]
    
Options:
    --quick     Run only the core user flow test
    --full      Run all Golden Path Phase 2 tests (default)
    --baseline  Run performance baseline establishment only
"""

import asyncio
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from tests.e2e.staging_config import get_staging_config, is_staging_available


def validate_environment():
    """Validate environment setup for Golden Path testing."""
    print("🔍 Validating environment setup...")
    
    env = get_env()
    issues = []
    
    # Check required environment variables
    required_vars = [
        "JWT_SECRET_STAGING",
        "E2E_OAUTH_SIMULATION_KEY"
    ]
    
    for var in required_vars:
        if not env.get(var):
            issues.append(f"Missing required environment variable: {var}")
    
    # Check staging availability
    if not is_staging_available():
        issues.append("Staging environment not available")
    
    if issues:
        print("X Environment validation failed:")
        for issue in issues:
            print(f"   • {issue}")
        return False
    
    print("CHECK Environment validation passed")
    return True


def run_test_command(test_pattern: str, description: str):
    """Run pytest command with proper configuration."""
    import subprocess

    print(f"\n🚀 {description}")
    print("=" * 80)

    cmd = [
        "python", "-m", "pytest",
        f"tests/e2e/staging/test_golden_path_phase2_regression_prevention.py::{test_pattern}",
        "-v",
        "--tb=short",
        "--capture=no",
        "--color=yes"
    ]

    start_time = time.time()
    # Fix Unicode/encoding issues for Windows compatibility
    result = subprocess.run(
        cmd,
        cwd=project_root,
        encoding='utf-8',
        errors='replace',
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    duration = time.time() - start_time

    # Print the output with proper encoding handling
    if result.stdout:
        print(result.stdout)

    if result.returncode == 0:
        print(f"CHECK {description} PASSED ({duration:.1f}s)")
    else:
        print(f"X {description} FAILED ({duration:.1f}s)")

    return result.returncode == 0


def run_quick_test():
    """Run only the core Golden Path user flow test."""
    return run_test_command(
        "TestGoldenPathPhase2RegressionPrevention::test_complete_golden_path_user_flow",
        "GOLDEN PATH CORE USER FLOW TEST"
    )


def run_baseline_test():
    """Run only the performance baseline test."""
    return run_test_command(
        "TestGoldenPathPhase2RegressionPrevention::test_performance_baseline_establishment",
        "GOLDEN PATH PERFORMANCE BASELINE TEST"
    )


def run_full_test_suite():
    """Run all Golden Path Phase 2 tests."""
    test_scenarios = [
        ("TestGoldenPathPhase2RegressionPrevention::test_complete_golden_path_user_flow", 
         "COMPLETE GOLDEN PATH USER FLOW"),
        ("TestGoldenPathPhase2RegressionPrevention::test_websocket_event_sequence_validation", 
         "WEBSOCKET EVENT SEQUENCE VALIDATION"),
        ("TestGoldenPathPhase2RegressionPrevention::test_concurrent_user_isolation", 
         "CONCURRENT USER ISOLATION"),
        ("TestGoldenPathPhase2RegressionPrevention::test_error_handling_graceful_degradation", 
         "ERROR HANDLING AND GRACEFUL DEGRADATION"),
        ("TestGoldenPathPhase2RegressionPrevention::test_performance_baseline_establishment", 
         "PERFORMANCE BASELINE ESTABLISHMENT")
    ]
    
    results = []
    total_start = time.time()
    
    for test_pattern, description in test_scenarios:
        success = run_test_command(test_pattern, description)
        results.append((description, success))
        
        if not success:
            print(f"\nWARNING️  Test failure detected. Continuing with remaining tests...")
    
    total_duration = time.time() - total_start
    
    # Summary report
    print(f"\n{'=' * 80}")
    print("GOLDEN PATH PHASE 2 TEST SUITE SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total execution time: {total_duration:.1f}s")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for description, success in results:
        status = "CHECK PASS" if success else "X FAIL"
        print(f"   {status} {description}")
    
    if passed == total:
        print(f"\n🎉 ALL GOLDEN PATH PHASE 2 TESTS PASSED!")
        print("CHECK 500K+ ARR Golden Path is protected and ready for MessageRouter proxy removal")
        return True
    else:
        print(f"\n🚨 GOLDEN PATH PHASE 2 TESTS FAILED!")
        print("X DO NOT PROCEED with MessageRouter proxy removal until all tests pass")
        print(f"X {total - passed} test(s) failed - investigate and fix before migration")
        return False


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="Golden Path Phase 2 Test Runner")
    parser.add_argument("--quick", action="store_true", 
                       help="Run only the core user flow test")
    parser.add_argument("--baseline", action="store_true", 
                       help="Run only the performance baseline test")
    parser.add_argument("--full", action="store_true", 
                       help="Run all Golden Path Phase 2 tests (default)")
    
    args = parser.parse_args()
    
    # Default to full test suite if no specific option
    if not args.quick and not args.baseline:
        args.full = True
    
    print("🔒 GOLDEN PATH PHASE 2 REGRESSION PREVENTION")
    print("🎯 Mission: Protect 500K+ ARR during MessageRouter proxy removal")
    print("🌐 Environment: Staging (real services, no mocks)")
    print("=" * 80)
    
    # Validate environment
    if not validate_environment():
        print("\nX Environment validation failed. Cannot run Golden Path tests.")
        return 1
    
    # Set test environment variables
    env = get_env()
    env.set("GOLDEN_PATH_PHASE2_TEST", "true", "test_runner")
    env.set("TEST_USER_ISOLATION", "enabled", "test_runner")
    env.set("ENVIRONMENT", "staging", "test_runner")
    
    # Run selected tests
    success = False
    
    if args.quick:
        success = run_quick_test()
    elif args.baseline:
        success = run_baseline_test()
    elif args.full:
        success = run_full_test_suite()
    
    # Exit with appropriate code
    if success:
        print(f"\nCHECK Golden Path Phase 2 testing completed successfully!")
        return 0
    else:
        print(f"\nX Golden Path Phase 2 testing failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)