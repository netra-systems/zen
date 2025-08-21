#!/usr/bin/env python3
"""Test runner for refactored components."""

import subprocess
import sys
from pathlib import Path

import pytest

# Setup paths
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

def run_tests():
    """Run all tests for refactored components."""
    
    print("🧪 Running Refactor Test Suite")
    print("=" * 50)
    
    test_modules = [
        "app/tests/core/test_config_manager.py",
        "app/tests/core/test_error_handling.py", 
        "app/tests/core/test_service_interfaces.py",
    ]
    
    # Run pytest with coverage
    pytest_args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker validation
        "--cov=app/core",  # Coverage for core modules
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov/refactor",  # HTML coverage report
        "--cov-fail-under=80",  # Require 80% coverage
    ] + test_modules
    
    print("Running pytest with the following arguments:")
    print(" ".join(["pytest"] + pytest_args))
    print()
    
    # Run tests
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("\n✅ All refactor tests passed!")
        print("📊 Coverage report generated in htmlcov/refactor/")
    else:
        print("\n❌ Some tests failed!")
        print("Check the output above for details.")
    
    return exit_code

def run_specific_test_category(category: str):
    """Run tests for a specific category."""
    
    test_categories = {
        "config": "app/tests/core/test_config_manager.py",
        "errors": "app/tests/core/test_error_handling.py",
        "services": "app/tests/core/test_service_interfaces.py",
    }
    
    if category not in test_categories:
        print(f"❌ Unknown test category: {category}")
        print(f"Available categories: {', '.join(test_categories.keys())}")
        return 1
    
    test_file = test_categories[category]
    
    print(f"🧪 Running {category} tests")
    print("=" * 30)
    
    pytest_args = [
        "-v",
        "--tb=short",
        f"--cov=app/core",
        "--cov-report=term",
        test_file
    ]
    
    return pytest.main(pytest_args)

def main():
    """Main test runner."""
    
    if len(sys.argv) > 1:
        category = sys.argv[1]
        if category == "--help":
            print("Usage: python run_refactor_tests.py [category]")
            print()
            print("Categories:")
            print("  config    - Configuration management tests")
            print("  errors    - Error handling tests")
            print("  services  - Service interface tests")
            print("  (no arg)  - Run all tests")
            return 0
        
        return run_specific_test_category(category)
    else:
        return run_tests()

if __name__ == "__main__":
    sys.exit(main())