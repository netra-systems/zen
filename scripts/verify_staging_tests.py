#!/usr/bin/env python
"""
Verify Staging Configuration Integration Tests

This script verifies that the staging configuration tests are properly
set up and can be discovered by the test runner.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path

def verify_test_files():
    """Verify all test files exist."""
    test_dir = PROJECT_ROOT / "app" / "tests" / "integration" / "staging_config"
    
    expected_files = [
        "__init__.py",
        "base.py",
        "test_secret_manager_integration.py",
        "test_terraform_deployment_consistency.py",
        "test_cloud_sql_proxy.py",
        "test_staging_startup.py",
        "test_environment_precedence.py",
        "test_multi_service_secrets.py",
        "test_redis_lifecycle.py",
        "test_database_migrations.py",
        "test_health_checks.py",
        "test_websocket_load_balancer.py",
        "test_cors_configuration.py",
        "test_llm_integration.py",
        "test_deployment_rollback.py",
        "test_observability_pipeline.py",
        "test_resource_limits.py"
    ]
    
    print("=" * 80)
    print("STAGING CONFIGURATION TEST VERIFICATION")
    print("=" * 80)
    
    print(f"\n[DIR] Test Directory: {test_dir}")
    
    if not test_dir.exists():
        print(f"[ERROR] Test directory does not exist!")
        return False
    
    print(f"[OK] Test directory exists\n")
    
    print("[INFO] Checking test files:")
    missing_files = []
    
    for file in expected_files:
        file_path = test_dir / file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"  [OK] {file} ({size:,} bytes)")
        else:
            print(f"  [MISSING] {file}")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n[ERROR] Missing {len(missing_files)} files")
        return False
    
    print(f"\n[OK] All {len(expected_files)} test files present")
    return True

def verify_test_runner_config():
    """Verify test runner configuration includes staging tests."""
    config_file = PROJECT_ROOT / "test_framework" / "test_config.py"
    
    print("\n[INFO] Checking test runner configuration:")
    
    if not config_file.exists():
        print(f"[ERROR] Test config file not found: {config_file}")
        return False
    
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Check for staging test level configurations
    staging_configs = [
        '"staging"',
        '"staging-quick"'
    ]
    
    found_configs = []
    for config in staging_configs:
        if config in content:
            found_configs.append(config.strip('"'))
            print(f"  [OK] Test level: {config.strip('\"')}")
    
    if not found_configs:
        print("  [ERROR] No staging test levels found in configuration")
        return False
    
    # Check for GCP staging environment function
    if "configure_gcp_staging_environment" in content:
        print("  [OK] GCP staging environment configuration function present")
    else:
        print("  [ERROR] GCP staging environment configuration function missing")
        return False
    
    return True

def verify_test_discovery():
    """Verify tests can be discovered by test runner."""
    print("\n[INFO] Testing test discovery:")
    
    try:
        from test_framework.test_discovery import TestDiscovery
        
        discovery = TestDiscovery(PROJECT_ROOT)
        all_tests = discovery.discover_tests()
        
        # Check if staging_config tests are discovered
        staging_tests = []
        for category, tests in all_tests.items():
            for test in tests:
                if "staging_config" in str(test):
                    staging_tests.append(test)
        
        if staging_tests:
            print(f"  [OK] Discovered {len(staging_tests)} staging configuration tests")
            
            # Show sample of discovered tests
            print("\n  Sample discovered tests:")
            for test in staging_tests[:5]:
                test_name = str(test).split('/')[-1]
                print(f"    - {test_name}")
            
            if len(staging_tests) > 5:
                print(f"    ... and {len(staging_tests) - 5} more")
        else:
            print("  [ERROR] No staging configuration tests discovered")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Error during test discovery: {e}")
        return False
    
    return True

def print_usage_instructions():
    """Print instructions for running staging tests."""
    print("\n" + "=" * 80)
    print("HOW TO RUN STAGING TESTS")
    print("=" * 80)
    
    print("\n[1] Quick staging validation (2-3 minutes):")
    print("  python unified_test_runner.py --level staging-quick")
    
    print("\n[2] Full staging configuration tests (10-15 minutes):")
    print("  python unified_test_runner.py --level staging")
    
    print("\n[3] Run with explicit GCP staging environment:")
    print("  python unified_test_runner.py --level staging --env staging")
    
    print("\n[PREREQUISITES]:")
    print("  1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
    print("  2. Set GCP_PROJECT_ID (defaults to 'netra-ai-staging')")
    print("  3. Ensure GCP credentials have necessary permissions")
    
    print("\n[IMPORTANT]:")
    print("  - Tests require access to real GCP staging resources")
    print("  - Some tests may be skipped if resources are not available")
    print("  - Run from project root directory")

def main():
    """Main verification process."""
    success = True
    
    # Verify test files
    if not verify_test_files():
        success = False
    
    # Verify test runner configuration
    if not verify_test_runner_config():
        success = False
    
    # Verify test discovery
    if not verify_test_discovery():
        success = False
    
    # Print summary
    print("\n" + "=" * 80)
    if success:
        print("[SUCCESS] VERIFICATION SUCCESSFUL")
        print("All staging configuration tests are properly set up")
        print_usage_instructions()
    else:
        print("[FAILED] VERIFICATION FAILED")
        print("Some issues were found with staging configuration tests")
        print("Please review the errors above")
    print("=" * 80)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())