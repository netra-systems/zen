#!/usr/bin/env python3
"""
Configuration Integration Tests Runner

This script runs the comprehensive configuration management and regression prevention
integration tests to validate deployment stability and configuration correctness.

Business Value: Prevents configuration cascade failures that have caused production outages.

Usage:
    python shared/tests/integration/run_configuration_tests.py
    python shared/tests/integration/run_configuration_tests.py --verbose
    python shared/tests/integration/run_configuration_tests.py --test-pattern "*regression*"

The tests validate:
- IsolatedEnvironment usage and enforcement
- Critical environment variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
- Configuration cascade failure prevention
- Service configuration discovery and validation
- Multi-environment configuration isolation
- Regression prevention for known incidents
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add project root and shared paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))
sys.path.insert(0, str(project_root / "test_framework"))

import pytest


def setup_test_environment():
    """Set up the test environment for configuration tests."""
    # Set test environment variables
    test_env = {
        "TESTING": "1",
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG"
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    print("Test environment configured:")
    for key, value in test_env.items():
        print(f"  {key}={value}")


def run_configuration_tests(verbose: bool = False, test_pattern: str = None) -> Dict[str, Any]:
    """
    Run the configuration integration tests.
    
    Args:
        verbose: Enable verbose output
        test_pattern: Pattern to match specific tests
        
    Returns:
        Dictionary with test results and summary
    """
    setup_test_environment()
    
    # Define test files to run
    test_files = [
        "shared/tests/integration/test_configuration_management_critical_integration.py",
        "shared/tests/integration/test_configuration_regression_prevention.py"
    ]
    
    # Build pytest arguments
    pytest_args = []
    
    # Add verbosity
    if verbose:
        pytest_args.extend(["-v", "-s"])
    else:
        pytest_args.append("-q")
    
    # Add test pattern if specified
    if test_pattern:
        pytest_args.extend(["-k", test_pattern])
    
    # Add markers for integration tests
    pytest_args.extend(["-m", "integration"])
    
    # Add test files
    pytest_args.extend(test_files)
    
    # Add output formatting
    pytest_args.extend([
        "--tb=short",          # Shorter traceback format
        "--no-header",         # No pytest header
        "--disable-warnings"   # Disable warnings for cleaner output
    ])
    
    print("\n" + "="*80)
    print("RUNNING CONFIGURATION INTEGRATION TESTS")
    print("="*80)
    print(f"Test files: {len(test_files)}")
    print(f"Pattern: {test_pattern or 'All tests'}")
    print(f"Verbose: {verbose}")
    print("="*80)
    
    start_time = time.time()
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Determine result
    success = exit_code == 0
    
    # Print summary
    print("\n" + "="*80)
    print("CONFIGURATION TESTS SUMMARY")
    print("="*80)
    print(f"Status: {'PASSED' if success else 'FAILED'}")
    print(f"Duration: {duration:.2f}s")
    print(f"Exit Code: {exit_code}")
    
    if success:
        print("\n✅ All configuration tests passed!")
        print("✅ Configuration management systems are working correctly")
        print("✅ Regression prevention measures are in place")
        print("✅ Environment isolation is functioning properly")
    else:
        print("\n❌ Configuration tests failed!")
        print("❌ Review the errors above to identify configuration issues")
        print("❌ These failures indicate potential deployment risks")
    
    print("="*80)
    
    return {
        "success": success,
        "exit_code": exit_code,
        "duration": duration,
        "test_files": test_files,
        "pattern": test_pattern
    }


def validate_test_structure():
    """Validate that test files exist and are properly structured."""
    print("\n" + "="*60)
    print("VALIDATING TEST STRUCTURE")
    print("="*60)
    
    test_files = [
        "shared/tests/integration/test_configuration_management_critical_integration.py",
        "shared/tests/integration/test_configuration_regression_prevention.py"
    ]
    
    validation_results = []
    
    for test_file in test_files:
        file_path = project_root / test_file
        exists = file_path.exists()
        
        if exists:
            try:
                # Try to import the test class
                if "critical_integration" in test_file:
                    from shared.tests.integration.test_configuration_management_critical_integration import TestConfigurationManagementCriticalIntegration
                    test_class = TestConfigurationManagementCriticalIntegration
                elif "regression_prevention" in test_file:
                    from shared.tests.integration.test_configuration_regression_prevention import TestConfigurationRegressionPrevention
                    test_class = TestConfigurationRegressionPrevention
                
                # Count test methods
                test_methods = [method for method in dir(test_class) if method.startswith("test_")]
                method_count = len(test_methods)
                
                print(f"✅ {test_file}")
                print(f"   Class: {test_class.__name__}")
                print(f"   Methods: {method_count}")
                
                validation_results.append({
                    "file": test_file,
                    "exists": True,
                    "importable": True,
                    "method_count": method_count
                })
                
            except Exception as e:
                print(f"❌ {test_file} - Import error: {e}")
                validation_results.append({
                    "file": test_file,
                    "exists": True,
                    "importable": False,
                    "error": str(e)
                })
        else:
            print(f"❌ {test_file} - File not found")
            validation_results.append({
                "file": test_file,
                "exists": False,
                "importable": False
            })
    
    total_methods = sum(result.get("method_count", 0) for result in validation_results)
    importable_count = sum(1 for result in validation_results if result.get("importable", False))
    
    print(f"\nSummary:")
    print(f"  Test files: {len(test_files)}")
    print(f"  Importable: {importable_count}/{len(test_files)}")
    print(f"  Total test methods: {total_methods}")
    
    all_valid = all(result.get("importable", False) for result in validation_results)
    
    if all_valid:
        print("✅ All test files are valid and ready to run")
    else:
        print("❌ Some test files have issues")
    
    print("="*60)
    
    return all_valid


def main():
    """Main entry point for the configuration test runner."""
    parser = argparse.ArgumentParser(
        description="Run configuration management integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose test output"
    )
    
    parser.add_argument(
        "--test-pattern", "-k",
        type=str,
        help="Run only tests matching this pattern"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate test structure, don't run tests"
    )
    
    args = parser.parse_args()
    
    print("Configuration Integration Tests Runner")
    print("=" * 80)
    
    # Validate test structure
    structure_valid = validate_test_structure()
    
    if args.validate_only:
        sys.exit(0 if structure_valid else 1)
    
    if not structure_valid:
        print("❌ Test structure validation failed. Fix issues before running tests.")
        sys.exit(1)
    
    # Run tests
    results = run_configuration_tests(
        verbose=args.verbose,
        test_pattern=args.test_pattern
    )
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()