#!/usr/bin/env python3
"""Security test runner for agent execution protection.

This script runs the comprehensive security test suite to validate
all protection mechanisms against agent death, resource exhaustion,
and DoS attacks.

Usage:
    python run_security_tests.py [--quick] [--category CATEGORY]
    
Categories:
    - timeout: Timeout enforcement tests
    - resource: Resource protection tests  
    - circuit: Circuit breaker tests
    - death: Agent death prevention tests
    - all: All security tests (default)
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(category="all", quick=False):
    """Run security tests with specified category and options."""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Test paths
    security_tests_dir = Path("tests/security")
    
    if not security_tests_dir.exists():
        print(f" FAIL:  Security tests directory not found: {security_tests_dir}")
        return 1
    
    # Add test directory
    cmd.append(str(security_tests_dir))
    
    # Add category filter
    if category != "all":
        category_filters = {
            "timeout": "test_timeout_enforcement",
            "resource": "test_resource_protection", 
            "circuit": "test_circuit_breaker",
            "death": "test_agent_death_prevention"
        }
        
        if category in category_filters:
            cmd.extend(["-k", category_filters[category]])
        else:
            print(f" FAIL:  Unknown category: {category}")
            print(f"Available categories: {', '.join(category_filters.keys())}")
            return 1
    
    # Add options
    if quick:
        cmd.extend(["--tb=short", "-x"])  # Stop on first failure, short traceback
    else:
        cmd.extend(["-v", "--tb=long"])   # Verbose with full traceback
    
    # Add security marker
    cmd.extend(["-m", "security"])
    
    # Add output formatting
    cmd.extend(["--color=yes"])
    
    print(f"[U+1F512] Running security tests: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F]  Tests interrupted by user")
        return 130
    except Exception as e:
        print(f" FAIL:  Error running tests: {e}")
        return 1


def main():
    """Main entry point for security test runner."""
    parser = argparse.ArgumentParser(
        description="Run security tests for agent execution protection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_security_tests.py                    # Run all security tests
  python run_security_tests.py --quick            # Run all tests, stop on first failure
  python run_security_tests.py --category timeout # Run only timeout tests
  python run_security_tests.py --category death   # Run only agent death prevention tests
        """
    )
    
    parser.add_argument(
        "--category", 
        choices=["all", "timeout", "resource", "circuit", "death"],
        default="all",
        help="Category of security tests to run (default: all)"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run tests quickly, stop on first failure"
    )
    
    args = parser.parse_args()
    
    print("[U+1F6E1][U+FE0F]  Netra Security Test Suite")
    print(f"Category: {args.category}")
    print(f"Quick mode: {args.quick}")
    print()
    
    exit_code = run_tests(args.category, args.quick)
    
    if exit_code == 0:
        print()
        print(" PASS:  All security tests passed!")
        print("[U+1F6E1][U+FE0F]  Agent execution protection is working correctly.")
    else:
        print()
        print(f" FAIL:  Security tests failed with exit code: {exit_code}")
        print(" ALERT:  Security vulnerabilities may exist - review failures above.")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())