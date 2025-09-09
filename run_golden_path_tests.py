#!/usr/bin/env python3
"""
Golden Path Test Runner

This script runs the PRIMARY golden path tests that validate the complete business value
delivery journey from user connection through AI-powered cost optimization results.

CRITICAL BUSINESS CONTEXT:
These tests protect $500K+ ARR by ensuring the core revenue-generating user flow works.

Usage:
    python run_golden_path_tests.py                    # Run all golden path tests
    python run_golden_path_tests.py --primary-only     # Run only the primary test
    python run_golden_path_tests.py --real-services    # Run with real services
    python run_golden_path_tests.py --verbose          # Run with verbose output
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_command(cmd, verbose=False):
    """Run command and return result."""
    if verbose:
        print(f">>> Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: Command failed with exit code {result.returncode}")
        if not verbose and result.stderr:
            print(f"Error: {result.stderr}")
        return False
    
    if verbose:
        print("SUCCESS: Command completed successfully")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Run Golden Path Tests")
    parser.add_argument("--primary-only", action="store_true", 
                       help="Run only the primary golden path test")
    parser.add_argument("--real-services", action="store_true",
                       help="Run with real services (Docker)")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--env", default="test", choices=["test", "staging"],
                       help="Test environment")
    
    args = parser.parse_args()
    
    print("*** GOLDEN PATH TEST RUNNER ***")
    print("=" * 50)
    print("CRITICAL MISSION: Validate $500K+ ARR protection")
    print("Testing complete user journey to business value delivery")
    print("=" * 50)
    
    # Change to project directory
    os.chdir(project_root)
    
    # Build base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if args.primary_only:
        # Run only the primary golden path test
        cmd.extend([
            "tests/e2e/golden_path/test_complete_golden_path_business_value.py::TestCompleteGoldenPathBusinessValue::test_complete_user_journey_delivers_business_value",
            "-v", "--tb=short"
        ])
        print(">>> Running PRIMARY GOLDEN PATH test only")
    else:
        # Run all golden path tests
        cmd.extend([
            "tests/e2e/golden_path/",
            "-v", "--tb=short"
        ])
        print(">>> Running ALL golden path tests")
    
    # Add markers
    cmd.extend(["-m", "e2e"])
    
    if args.real_services:
        cmd.extend(["-m", "real_services"])
        print(">>> Using REAL services (Docker)")
    
    if args.verbose:
        cmd.append("-s")
        print(">>> Verbose output enabled")
    
    # Set environment
    env = os.environ.copy()
    env["TEST_ENV"] = args.env
    print(f">>> Test environment: {args.env}")
    
    print(f"\n>>> Executing command: {' '.join(cmd)}")
    print("=" * 50)
    
    # Run the tests
    result = subprocess.run(cmd, env=env)
    
    print("\n" + "=" * 50)
    if result.returncode == 0:
        print("SUCCESS: GOLDEN PATH TESTS PASSED!")
        print("SUCCESS: $500K+ ARR protection VALIDATED")
        print("SUCCESS: Business value delivery confirmed")
    else:
        print("FAILED: GOLDEN PATH TESTS FAILED!")
        print("WARNING: CRITICAL: Revenue-generating flow broken")
        print("WARNING: Immediate attention required")
    
    print("=" * 50)
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())