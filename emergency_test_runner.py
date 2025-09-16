#!/usr/bin/env python3
"""
Emergency Test Runner for Netra Apex - IMMEDIATE RECOVERY PATHWAY

This script provides a working test execution pathway when the unified test runner
or Docker dependencies are not available. It bypasses Docker requirements and
runs tests directly with pytest.

Created: 2025-09-15
Purpose: Restore test infrastructure functionality for immediate development needs
"""
import sys
import subprocess
import argparse
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Run a command and return success/failure."""
    print(f"\n=== {description} ===")
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Command timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Emergency Test Runner")
    parser.add_argument("--category", choices=["unit", "integration", "e2e", "critical"],
                       default="unit", help="Test category to run")
    parser.add_argument("--path", help="Specific test path to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-capture", action="store_true", help="Disable output capture")

    args = parser.parse_args()

    print("=== EMERGENCY TEST RUNNER - IMMEDIATE RECOVERY ===")
    print("This bypasses Docker dependencies and runs tests directly with pytest")

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    if args.path:
        cmd.append(args.path)
    elif args.category == "unit":
        cmd.append("netra_backend/tests/unit/")
    elif args.category == "integration":
        cmd.append("netra_backend/tests/integration/")
    elif args.category == "e2e":
        cmd.append("tests/e2e/")
    elif args.category == "critical":
        cmd.append("tests/mission_critical/")

    # Add common pytest flags
    if args.verbose:
        cmd.append("-v")
    if args.no_capture:
        cmd.append("-s")

    # Add basic flags for better output
    cmd.extend([
        "--tb=short",        # Short traceback format
        "--maxfail=10",     # Stop after 10 failures
        "--timeout=120"     # 2 minute timeout per test
    ])

    # Run the tests
    success = run_command(cmd, f"Running {args.category} tests")

    if success:
        print("\n[SUCCESS] Tests completed successfully!")
        return 0
    else:
        print("\n[FAILURE] Some tests failed or there were errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())