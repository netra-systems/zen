#!/usr/bin/env python3
"""
OAuth Integration Test Runner

Business Value:
- Enterprise SSO validation for $100K+ contracts
- Critical for Enterprise customer acquisition
- Prevents OAuth failures that block high-value deals

Usage:
    python run_oauth_integration_tests.py
    python run_oauth_integration_tests.py --test-specific test_complete_oauth_google_integration
    python run_oauth_integration_tests.py --verbose
"""

import sys
import subprocess
import argparse
from pathlib import Path

def run_oauth_integration_tests(test_name=None, verbose=False, timeout=30):
    """Run OAuth integration tests with proper configuration"""
    
    # Set up test command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unified/e2e/test_real_oauth_integration.py",
        "--asyncio-mode=auto",  # Enable asyncio support
        "--tb=short"
    ]
    
    if test_name:
        cmd.append(f"::TestRealOAuthIntegration::{test_name}")
    
    if verbose:
        cmd.extend(["-v", "-s"])
    else:
        cmd.append("-q")
    
    # Add timeout for enterprise performance validation
    cmd.extend(["--timeout", str(timeout)])
    
    print("=" * 80)
    print("RUNNING CRITICAL OAUTH INTEGRATION TESTS")
    print("=" * 80)
    print(f"Business Value: Enterprise SSO for $100K+ MRR contracts")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 80)
    
    # Run the tests
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except KeyboardInterrupt:
        print("\nOAuth integration tests interrupted by user")
        return 130
    except Exception as e:
        print(f"Failed to run OAuth integration tests: {e}")
        return 1

def main():
    """Main entry point for OAuth integration test runner"""
    parser = argparse.ArgumentParser(
        description="Run OAuth Integration Tests for Enterprise SSO"
    )
    parser.add_argument(
        "--test-specific", 
        help="Run specific test method (e.g., test_complete_oauth_google_integration)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Test timeout in seconds (default: 60)"
    )
    
    args = parser.parse_args()
    
    # Validate we're in the right directory
    if not Path("tests/unified/e2e/test_real_oauth_integration.py").exists():
        print("Error: OAuth integration test file not found")
        print("Make sure you're running from the project root directory")
        return 1
    
    # Run the tests
    return_code = run_oauth_integration_tests(
        test_name=args.test_specific,
        verbose=args.verbose,
        timeout=args.timeout
    )
    
    if return_code == 0:
        print("\n" + "=" * 80)
        print("OAUTH INTEGRATION TESTS PASSED")
        print("Enterprise SSO capability VALIDATED")
        print("$100K+ MRR Enterprise deals PROTECTED")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("OAUTH INTEGRATION TESTS FAILED")
        print("Enterprise SSO capability AT RISK")
        print("$100K+ MRR Enterprise deals THREATENED")
        print("=" * 80)
    
    return return_code

if __name__ == "__main__":
    sys.exit(main())