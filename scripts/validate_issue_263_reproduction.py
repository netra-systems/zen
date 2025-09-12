#!/usr/bin/env python3
"""
GitHub Issue #263 Validation Script
===================================

Quick validation script to confirm that the issue #263 reproduction tests work correctly.
This script can be run to verify that:

1. The broken patterns fail as expected
2. The fixed patterns work as expected  
3. All test infrastructure is functioning

Usage:
    python3 scripts/validate_issue_263_reproduction.py
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n SEARCH:  {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print(f"Return code: {result.returncode}")
    return result.returncode == 0


def main():
    """Main validation function."""
    print("=" * 80)
    print("GitHub Issue #263 Test Reproduction Validation")
    print("=" * 80)
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")
    
    # Test files to validate
    test_files = [
        "tests/validation/test_issue_263_core_problems.py",
        "tests/validation/test_issue_263_broken_patterns_demo.py"
    ]
    
    all_tests_passed = True
    
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f" FAIL:  ERROR: Test file not found: {test_file}")
            all_tests_passed = False
            continue
        
        # Run the specific test file
        cmd = ["python3", "-m", "pytest", test_file, "-v", "--tb=short"]
        success = run_command(cmd, f"Running {test_file}")
        
        if not success:
            print(f" FAIL:  FAILED: {test_file}")
            all_tests_passed = False
        else:
            print(f" PASS:  PASSED: {test_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    if all_tests_passed:
        print(" PASS:  ALL VALIDATION TESTS PASSED")
        print("\n[U+1F4CB] EVIDENCE COLLECTED:")
        print("   [U+2022] setUp() vs setup_method() incompatibility demonstrated")
        print("   [U+2022] ExecutionResult parameter incompatibility demonstrated")  
        print("   [U+2022] AttributeError: 'golden_user_context' reproduction confirmed")
        print("   [U+2022] TypeError for old ExecutionResult parameters confirmed")
        print("   [U+2022] Complete fixed pattern working correctly confirmed")
        print("\n TARGET:  READY FOR FIX IMPLEMENTATION")
        print("   The test implementations can now be used to:")
        print("   1. Validate the fix works correctly")
        print("   2. Prevent regression of these issues")
        print("   3. Guide developers on correct patterns")
        
        return 0
    else:
        print(" FAIL:  VALIDATION FAILED")
        print("\n[U+1F527] TROUBLESHOOTING:")
        print("   [U+2022] Check that all test dependencies are installed")
        print("   [U+2022] Verify you're running from the project root directory")
        print("   [U+2022] Ensure Python 3.7+ is being used")
        print("   [U+2022] Check that pytest is installed and accessible")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())