from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python
"""
Quick script to run tests against the actual staging environment.

Usage:
    python scripts/test_staging.py           # Run all staging tests
    python scripts/test_staging.py --quick   # Run quick health checks only
    python scripts/test_staging.py --full    # Run comprehensive staging tests
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path

env = get_env()
def setup_staging_env():
    """Set up environment variables for staging tests."""
    staging_env = {
        "ENVIRONMENT": "staging",
        "STAGING_URL": "https://app.staging.netrasystems.ai",
        "STAGING_API_URL": "https://api.staging.netrasystems.ai",
        "STAGING_AUTH_URL": "https://auth.staging.netrasystems.ai",
        "STAGING_FRONTEND_URL": "https://app.staging.netrasystems.ai",
        "BASE_URL": "https://app.staging.netrasystems.ai",
        "API_BASE_URL": "https://api.staging.netrasystems.ai",
        "AUTH_BASE_URL": "https://auth.staging.netrasystems.ai",
        "FRONTEND_URL": "https://app.staging.netrasystems.ai",
        "WS_BASE_URL": "wss://api.staging.netrasystems.ai/ws",
        "GCP_PROJECT_ID": "netra-ai-staging",
        "GCP_REGION": "us-central1",
        "USE_REAL_SERVICES": "true"
    }
    
    # Update environment
    env.update(staging_env, "test")
    
    print("=" * 80)
    print("STAGING ENVIRONMENT TEST RUNNER")
    print("=" * 80)
    print(f"Testing against:")
    print(f"  - App: {staging_env['STAGING_URL']}")
    print(f"  - API: {staging_env['STAGING_API_URL']}")
    print(f"  - Auth: {staging_env['STAGING_AUTH_URL']}")
    print(f"  - Frontend: {staging_env['STAGING_FRONTEND_URL']}")
    print("=" * 80)

def run_staging_tests(test_level="staging-real"):
    """Run staging tests using the test framework."""
    cmd = [
        sys.executable,
        "-m", "test_framework.test_runner",
        "--level", test_level,
        "--env", "staging"
    ]
    
    print(f"\nRunning command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test run cancelled by user")
        return 130
    except Exception as e:
        print(f"[ERROR] Failed to run tests: {e}")
        return 1

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run tests against staging environment")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick staging health checks only"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run comprehensive staging tests"
    )
    parser.add_argument(
        "--no-env-setup",
        action="store_true",
        help="Skip environment setup (use existing environment variables)"
    )
    
    args = parser.parse_args()
    
    # Set up staging environment
    if not args.no_env_setup:
        setup_staging_env()
    
    # Determine test level
    if args.quick:
        test_level = "staging-quick"
        print("\n[INFO] Running quick staging health checks...")
    elif args.full:
        test_level = "staging"
        print("\n[INFO] Running full staging test suite...")
    else:
        test_level = "staging-real"
        print("\n[INFO] Running standard staging tests...")
    
    # Run tests
    exit_code = run_staging_tests(test_level)
    
    if exit_code == 0:
        print("\n PASS:  STAGING TESTS PASSED")
    else:
        print(f"\n FAIL:  STAGING TESTS FAILED (exit code: {exit_code})")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())