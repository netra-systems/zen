#!/usr/bin/env python3
"""
Test staging configuration after simplification.
Verifies that staging will load secrets from Google Secret Manager only.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_no_staging_env_file():
    """Verify .env.staging has been removed."""
    staging_env_path = project_root / ".env.staging"
    if staging_env_path.exists():
        print("ERROR: .env.staging still exists - should be deleted!")
        print("   This file causes precedence issues with Google Secret Manager")
        return False
    print("PASS: .env.staging correctly removed")
    return True


def test_main_app_skips_env_loading():
    """Test that main app skips .env loading in staging."""
    # Check the backend main.py has the right logic
    backend_main_path = project_root / "netra_backend" / "app" / "main.py"
    
    with open(backend_main_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "environment in ['staging', 'production', 'prod']" in content and \
       "skipping all .env file loading (using GSM)" in content:
        print("PASS: Backend app correctly configured to skip .env loading in staging")
        return True
    else:
        print("FAIL: Backend app not properly configured to skip .env loading")
        return False


def test_auth_service_skips_env_loading():
    """Test that auth service skips .env loading in staging."""
    # Check the auth service main.py has the right logic
    auth_main_path = project_root / "auth_service" / "main.py"
    
    with open(auth_main_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "environment in ['staging', 'production', 'prod']" in content:
        print("PASS: Auth service correctly configured to skip .env loading in staging")
        return True
    else:
        print("FAIL: Auth service not properly configured to skip .env loading")
        return False


def test_deployment_script_configuration():
    """Test that deployment script has all necessary env vars."""
    deploy_script_path = project_root / "scripts" / "deploy_to_gcp.py"
    
    with open(deploy_script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_configs = [
        '"ENVIRONMENT": "staging"',
        '"JWT_ALGORITHM": "HS256"',
        '"oauth-hmac-secret-staging"',
        '--set-secrets',
        'POSTGRES_PASSWORD=postgres-password-staging',
        'JWT_SECRET_KEY=jwt-secret-key-staging',
        'GOOGLE_CLIENT_ID=google-client-id-staging',
    ]
    
    missing = []
    for config in required_configs:
        if config not in content:
            missing.append(config)
    
    if missing:
        print(f"FAIL: Deployment script missing configurations: {missing}")
        return False
    
    print("PASS: Deployment script has all necessary configurations")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("STAGING CONFIGURATION SIMPLIFICATION TEST")
    print("=" * 60)
    print("\nVerifying staging is configured to use Google Secret Manager only...\n")
    
    tests = [
        ("No .env.staging file", test_no_staging_env_file),
        ("Backend skips .env loading", test_main_app_skips_env_loading),
        ("Auth service skips .env loading", test_auth_service_skips_env_loading),
        ("Deployment script configuration", test_deployment_script_configuration),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nTesting: {test_name}")
        try:
            results.append(test_func())
        except Exception as e:
            print(f"FAIL: Test failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all(results):
        print("\nSUCCESS: All tests passed! Staging is correctly simplified.")
        print("\nConfiguration summary:")
        print("  - No .env.staging file (deleted)")
        print("  - All secrets come from Google Secret Manager")
        print("  - Non-secret config in deployment script as env vars")
        print("  - Apps skip .env loading when ENVIRONMENT=staging")
        return 0
    else:
        print(f"\nFAILURE: {len([r for r in results if not r])} tests failed.")
        print("\nWARNING: Fix the issues above before deploying to staging.")
        return 1


if __name__ == "__main__":
    sys.exit(main())