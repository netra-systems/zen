#!/usr/bin/env python3
"""
Import Validation Test Runner

This script runs the import validation tests that are designed to FAIL
until collection error fixes are applied. It provides detailed reporting
of which modules are missing and what needs to be implemented.

Usage:
    python tests/validation/import_fixes/run_validation_tests.py

Options:
    --verbose: Show detailed test output
    --summary: Show only summary of failures
    --category: Run specific test category
    --business-impact: Show business impact of failures

Business Impact: Running these tests before fixes shows the scope of
import/collection issues blocking ~10,000+ tests and $500K+ ARR validation.
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path


def run_validation_tests(verbose=False, category=None, summary=False, business_impact=False):
    """
    Run import validation tests and report results.
    
    Args:
        verbose: Show detailed test output
        category: Run specific test category (module, class, fixture, websocket, e2e)
        summary: Show only summary of failures
        business_impact: Show business impact analysis
    """
    
    # Base command
    base_cmd = ["python", "-m", "pytest"]
    
    # Test directory
    test_dir = "tests/validation/import_fixes/"
    
    # Build command based on options
    if category:
        category_map = {
            "module": "test_module_import_validation.py",
            "class": "test_class_existence_validation.py", 
            "fixture": "test_fixture_availability_validation.py",
            "websocket": "test_websocket_module_structure.py",
            "e2e": "test_e2e_helper_modules.py"
        }
        
        if category in category_map:
            test_file = f"{test_dir}{category_map[category]}"
        else:
            print(f"Unknown category: {category}")
            print(f"Available categories: {', '.join(category_map.keys())}")
            return False
    else:
        test_file = test_dir
    
    # Build pytest command
    cmd = base_cmd + [test_file]
    
    # Add pytest options
    if verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.extend(["-q"])
    
    # Add markers for collection fix tests
    cmd.extend(["-m", "collection_fix"])
    
    # Add additional options
    cmd.extend(["--tb=short"])  # Short traceback format
    
    print("=" * 80)
    print("IMPORT VALIDATION TEST RUNNER")
    print("=" * 80)
    print(f"Running: {' '.join(cmd)}")
    print()
    
    if business_impact:
        print_business_impact()
        print()
    
    # Run the tests
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="C:\\GitHub\\netra-apex")
        
        # Print results
        if verbose or not summary:
            print("STDOUT:")
            print(result.stdout)
            print("\nSTDERR:")
            print(result.stderr)
        
        # Summary reporting
        print("\n" + "=" * 80)
        print("VALIDATION TEST SUMMARY")
        print("=" * 80)
        
        if result.returncode == 0:
            print(" PASS:  ALL VALIDATION TESTS PASSED")
            print("   This indicates that import fixes have been successfully applied!")
            print("   Test collection should now discover significantly more tests.")
        else:
            print(" ALERT:  VALIDATION TESTS FAILED (EXPECTED)")
            print("   This indicates that import/collection fixes still need to be applied.")
            
            # Parse and summarize failures
            if "FAILED" in result.stdout:
                failed_tests = [line for line in result.stdout.split('\n') if 'FAILED' in line]
                print(f"\n   Failed Tests: {len(failed_tests)}")
                for test in failed_tests[:10]:  # Show first 10 failures
                    print(f"     - {test.strip()}")
                if len(failed_tests) > 10:
                    print(f"     ... and {len(failed_tests) - 10} more")
            
            # Show expected errors
            if "ModuleNotFoundError" in result.stdout:
                print("\n   [U+1F4CB] Missing Modules Detected (Expected):")
                print("     - WebSocket manager modules")
                print("     - E2E helper modules")
                print("     - Factory pattern modules")
            
            if "SyntaxError" in result.stdout:
                print("\n   [U+1F4CB] Syntax Errors Detected (Expected):")
                print("     - WebSocket test file syntax issues")
                print("     - Invalid class name definitions")
        
        print(f"\n   Return Code: {result.returncode}")
        print(f"   Test Command: {' '.join(cmd)}")
        
        return result.returncode == 0
        
    except FileNotFoundError as e:
        print(f"ERROR: Could not run pytest: {e}")
        print("Make sure you're in the correct directory and pytest is installed.")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error running tests: {e}")
        return False


def print_business_impact():
    """Print business impact analysis of validation test failures."""
    
    print("BUSINESS IMPACT ANALYSIS")
    print("=" * 40)
    print()
    
    impacts = [
        ("Golden Path Tests", "321 integration tests blocked", "$500K+ ARR validation"),
        ("Enterprise SSO", "SSO authentication testing blocked", "$15K+ MRR per customer"),  
        ("Unit Test Discovery", "~10,000 unit tests hidden", "Major testing confidence gap"),
        ("Thread Isolation", "Multi-user Enterprise features blocked", "User isolation validation"),
        ("WebSocket Events", "Real-time chat functionality blocked", "Primary value delivery"),
        ("Token Security", "Authentication security validation blocked", "All customer tiers"),
    ]
    
    for feature, issue, business_value in impacts:
        print(f" ALERT:  {feature}:")
        print(f"   Issue: {issue}")
        print(f"   Business Value: {business_value}")
        print()


def main():
    """Main entry point for validation test runner."""
    
    parser = argparse.ArgumentParser(
        description="Run import validation tests for collection error fixes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/validation/import_fixes/run_validation_tests.py
  python tests/validation/import_fixes/run_validation_tests.py --verbose
  python tests/validation/import_fixes/run_validation_tests.py --category websocket
  python tests/validation/import_fixes/run_validation_tests.py --business-impact
        """
    )
    
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed test output")
    parser.add_argument("--summary", "-s", action="store_true", 
                       help="Show only summary of failures")
    parser.add_argument("--category", "-c", choices=["module", "class", "fixture", "websocket", "e2e"],
                       help="Run specific test category")
    parser.add_argument("--business-impact", "-b", action="store_true",
                       help="Show business impact analysis")
    
    args = parser.parse_args()
    
    # Run the validation tests
    success = run_validation_tests(
        verbose=args.verbose,
        category=args.category, 
        summary=args.summary,
        business_impact=args.business_impact
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()