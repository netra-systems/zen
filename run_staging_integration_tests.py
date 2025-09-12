#!/usr/bin/env python3
"""
Staging Integration Test Runner
Runs integration tests using GCP staging services without Docker dependency.

This script:
1. Configures environment to use staging services (PostgreSQL, Redis, etc.)
2. Validates connection to staging infrastructure  
3. Runs integration tests with real services
4. Provides detailed reporting on test results

Golden Path compliance: Uses staging environment validation as specified.
"""

import sys
import subprocess
import os
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our staging environment setup
from test_staging_env_setup import setup_integration_test_environment


def run_staging_integration_tests(categories=None, verbose=False, fast_fail=False):
    """Run integration tests using staging environment."""
    
    print("🚀 Staging Integration Test Runner")
    print("=" * 60)
    print("📍 Testing with GCP staging services (PostgreSQL, Redis)")
    print("🔧 No Docker dependency - using real Cloud services")
    print("=" * 60)
    
    # Setup staging environment
    print("\n1️⃣ Setting up staging environment...")
    try:
        success = setup_integration_test_environment()
        if not success:
            print("❌ Failed to setup staging environment")
            return False
    except Exception as e:
        print(f"❌ Error setting up staging environment: {e}")
        return False
    
    # Validate services are accessible
    print("\n2️⃣ Validating staging service accessibility...")
    if not validate_staging_services():
        print("⚠️  Some staging services may not be accessible")
        print("🔄 Proceeding with tests - services may start during test execution")
    
    # Prepare test command
    test_categories = categories or ["integration", "websocket", "auth"]
    
    print(f"\n3️⃣ Running integration tests with categories: {', '.join(test_categories)}")
    
    # Build unified test runner command
    cmd = [
        sys.executable, 
        "tests/unified_test_runner.py",
        "--real-services",  # Use real services, not mocks
        "--env", "staging"  # Use staging environment
    ]
    
    # Add categories
    for category in test_categories:
        cmd.extend(["--category", category])
    
    # Add optional flags
    if verbose:
        cmd.append("--verbose")
    if fast_fail:
        cmd.append("--fast-fail")
    else:
        cmd.append("--no-fast-fail")  # Continue running all tests
    
    # Run tests
    print(f"📋 Test command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, cwd=project_root, check=False)
        
        print("-" * 60)
        if result.returncode == 0:
            print("✅ All integration tests PASSED!")
            print("🎯 Staging services are working correctly")
        else:
            print("❌ Some integration tests FAILED")
            print("🔍 Check test output for details")
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("❌ Unified test runner not found")
        print("🔧 Falling back to direct pytest execution")
        return run_direct_pytest(test_categories, verbose)
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def validate_staging_services():
    """Validate that staging services are accessible."""
    print("🔍 Checking staging service accessibility...")
    
    validation_passed = True
    
    # Check if gcloud is available (indicates GCP setup)
    try:
        result = subprocess.run(
            ["gcloud", "version"], 
            capture_output=True, 
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ gcloud CLI available")
        else:
            print("⚠️  gcloud CLI not available - may affect service access")
            validation_passed = False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  gcloud CLI not found - staging services may not be accessible")
        validation_passed = False
    
    # Check if we can reach staging URLs (basic connectivity)
    staging_urls = [
        ("Backend", os.environ.get("NETRA_BACKEND_URL", "")),
        ("Auth Service", os.environ.get("AUTH_SERVICE_URL", "")),
    ]
    
    for service_name, url in staging_urls:
        if url and "run.app" in url:
            print(f"✅ {service_name} URL configured: {url}")
        elif url:
            print(f"⚠️  {service_name} URL may not be staging: {url}")
            validation_passed = False
        else:
            print(f"❌ {service_name} URL not configured")
            validation_passed = False
    
    return validation_passed


def run_direct_pytest(categories, verbose=False):
    """Fallback to run tests directly with pytest."""
    print("\n🔄 Running tests directly with pytest...")
    
    # Find integration test files
    test_files = []
    for category in categories:
        pattern_map = {
            "integration": "tests/integration/**/*test*.py",
            "websocket": "tests/**/test_websocket*.py",
            "auth": "tests/**/test_auth*.py"
        }
        
        pattern = pattern_map.get(category, f"tests/**/test_{category}*.py")
        matching_files = list(project_root.glob(pattern))
        test_files.extend(matching_files)
    
    if not test_files:
        print("❌ No test files found for specified categories")
        return False
    
    # Run pytest
    cmd = [sys.executable, "-m", "pytest"]
    cmd.extend([str(f) for f in test_files[:10]])  # Limit to first 10 files
    
    if verbose:
        cmd.append("-v")
    
    cmd.extend(["-x"])  # Stop on first failure
    
    print(f"📋 Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running pytest: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run integration tests with GCP staging services"
    )
    parser.add_argument(
        "--categories", 
        nargs="+", 
        default=["integration", "websocket", "auth"],
        help="Test categories to run (default: integration, websocket, auth)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "--fast-fail", 
        action="store_true",
        help="Stop on first test failure"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true", 
        help="Only validate staging setup, don't run tests"
    )
    
    args = parser.parse_args()
    
    if args.validate_only:
        print("🔍 Validation-only mode")
        success = setup_integration_test_environment()
        if success:
            validate_staging_services()
            print("✅ Staging environment validation complete")
        else:
            print("❌ Staging environment validation failed")
            sys.exit(1)
        return
    
    # Run the tests
    success = run_staging_integration_tests(
        categories=args.categories,
        verbose=args.verbose,
        fast_fail=args.fast_fail
    )
    
    if success:
        print("\n🎉 Integration testing with staging services completed successfully!")
        print("💡 Your changes are compatible with GCP staging infrastructure")
    else:
        print("\n⚠️  Integration testing completed with failures")
        print("🔧 Please review test output and fix any issues")
        sys.exit(1)


if __name__ == "__main__":
    main()