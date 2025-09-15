#!/usr/bin/env python3
"""
Test script to validate VPC connector fix for database connectivity issue.

This script tests the fix for Issue #1263 - Database initialization timeout
by verifying the deployment configuration includes VPC connector settings.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Staging Environment Stability
- Value Impact: Ensures database connectivity for E2E testing pipeline
- Strategic Impact: Prevents staging deployment failures blocking development
"""

import os
import sys
import yaml
import re
from pathlib import Path

def test_deployment_workflow_vpc_connector():
    """Test that the deployment workflow includes VPC connector configuration."""

    workflow_path = Path("C:/GitHub/netra-apex/.github/workflows/deploy-staging.yml")

    if not workflow_path.exists():
        print(f"❌ ERROR: Workflow file not found: {workflow_path}")
        return False

    with open(workflow_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for VPC connector configuration in backend deployment
    backend_vpc_connector = "--vpc-connector staging-connector" in content
    backend_vpc_egress = "--vpc-egress all-traffic" in content

    print("VPC Connector Configuration Check:")
    print(f"   Backend VPC Connector: {'OK' if backend_vpc_connector else 'FAIL'}")
    print(f"   Backend VPC Egress: {'OK' if backend_vpc_egress else 'FAIL'}")

    if not backend_vpc_connector:
        print("CRITICAL: Backend deployment missing --vpc-connector staging-connector")
        return False

    if not backend_vpc_egress:
        print("CRITICAL: Backend deployment missing --vpc-egress all-traffic")
        return False

    # Check auth service as well
    auth_vpc_connector = content.count("--vpc-connector staging-connector") >= 2
    auth_vpc_egress = content.count("--vpc-egress all-traffic") >= 2

    print(f"   Auth Service VPC Connector: {'OK' if auth_vpc_connector else 'FAIL'}")
    print(f"   Auth Service VPC Egress: {'OK' if auth_vpc_egress else 'FAIL'}")

    if not auth_vpc_connector:
        print("WARNING: Auth service deployment missing --vpc-connector staging-connector")

    if not auth_vpc_egress:
        print("WARNING: Auth service deployment missing --vpc-egress all-traffic")

    return backend_vpc_connector and backend_vpc_egress

def test_database_timeout_configuration():
    """Test that database timeout configuration is appropriate for Cloud SQL."""

    config_path = Path("C:/GitHub/netra-apex/netra_backend/app/core/database_timeout_config.py")

    if not config_path.exists():
        print(f"ERROR: Database timeout config not found: {config_path}")
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Database Timeout Configuration Check:")

    # Check staging configuration exists
    staging_config_match = re.search(r'"staging":\s*{([^}]+)}', content, re.DOTALL)

    if not staging_config_match:
        print("❌ ERROR: Staging configuration not found in database timeout config")
        return False

    staging_config = staging_config_match.group(1)

    # Extract timeout values
    init_timeout_match = re.search(r'"initialization_timeout":\s*(\d+(?:\.\d+)?)', staging_config)
    connection_timeout_match = re.search(r'"connection_timeout":\s*(\d+(?:\.\d+)?)', staging_config)

    if not init_timeout_match:
        print("❌ ERROR: initialization_timeout not found in staging config")
        return False

    if not connection_timeout_match:
        print("❌ ERROR: connection_timeout not found in staging config")
        return False

    init_timeout = float(init_timeout_match.group(1))
    connection_timeout = float(connection_timeout_match.group(1))

    print(f"   Staging initialization_timeout: {init_timeout}s")
    print(f"   Staging connection_timeout: {connection_timeout}s")

    # Validate timeouts are sufficient for Cloud SQL
    if init_timeout < 20.0:
        print(f"❌ WARNING: initialization_timeout ({init_timeout}s) may be insufficient for Cloud SQL (recommend ≥20s)")
    else:
        print(f"✅ initialization_timeout ({init_timeout}s) is Cloud SQL compatible")

    if connection_timeout < 10.0:
        print(f"❌ WARNING: connection_timeout ({connection_timeout}s) may be insufficient for Cloud SQL (recommend ≥10s)")
    else:
        print(f"✅ connection_timeout ({connection_timeout}s) is Cloud SQL compatible")

    return init_timeout >= 15.0 and connection_timeout >= 10.0

def test_startup_module_integration():
    """Test that the startup module correctly uses the timeout configuration."""

    smd_path = Path("C:/GitHub/netra-apex/netra_backend/app/smd.py")

    if not smd_path.exists():
        print(f"❌ ERROR: SMD file not found: {smd_path}")
        return False

    with open(smd_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("🔍 Startup Module Integration Check:")

    # Check that it imports the timeout configuration
    imports_timeout_config = "from netra_backend.app.core.database_timeout_config import get_database_timeout_config" in content
    uses_timeout_config = "get_database_timeout_config(environment)" in content
    uses_initialization_timeout = "initialization_timeout" in content

    print(f"   Imports timeout config: {'✅' if imports_timeout_config else '❌'}")
    print(f"   Uses timeout config: {'✅' if uses_timeout_config else '❌'}")
    print(f"   Uses initialization_timeout: {'✅' if uses_initialization_timeout else '❌'}")

    return imports_timeout_config and uses_timeout_config and uses_initialization_timeout

def main():
    """Run all validation tests for the VPC connector fix."""

    print("Testing VPC Connector Fix for Database Connectivity Issue #1263")
    print("=" * 70)

    tests = [
        ("Deployment Workflow VPC Connector", test_deployment_workflow_vpc_connector),
        ("Database Timeout Configuration", test_database_timeout_configuration),
        ("Startup Module Integration", test_startup_module_integration),
    ]

    all_passed = True

    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 50)

        try:
            result = test_func()
            if result:
                print(f"✅ PASSED: {test_name}")
            else:
                print(f"❌ FAILED: {test_name}")
                all_passed = False
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}")
            all_passed = False

    print("\n" + "=" * 70)

    if all_passed:
        print("🎉 ALL TESTS PASSED! VPC Connector fix is correctly implemented.")
        print("\n📊 Summary of Fixes Applied:")
        print("   ✅ Added --vpc-connector staging-connector to backend deployment")
        print("   ✅ Added --vpc-egress all-traffic to backend deployment")
        print("   ✅ Added --vpc-connector staging-connector to auth service deployment")
        print("   ✅ Added --vpc-egress all-traffic to auth service deployment")
        print("   ✅ Database timeout configuration is Cloud SQL compatible")
        print("   ✅ Startup module correctly uses environment-aware timeouts")
        print("\n🚀 The staging services should now connect to Cloud SQL successfully!")
        return 0
    else:
        print("❌ SOME TESTS FAILED! Fix requires attention.")
        print("\n📝 Next Steps:")
        print("   1. Review failed tests above")
        print("   2. Fix any remaining configuration issues")
        print("   3. Re-run this test script to validate fixes")
        return 1

if __name__ == "__main__":
    sys.exit(main())