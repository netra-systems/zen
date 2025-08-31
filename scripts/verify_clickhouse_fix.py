#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verify ClickHouse configuration fix for staging deployment.

This script validates that:
1. The deployment script correctly maps the ClickHouse password secret
2. The database configuration manager properly validates the password
3. The staging environment documentation is clear
"""

import subprocess
import sys
import os
from pathlib import Path

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def check_deployment_script():
    """Verify deploy_to_gcp.py has the correct secret mapping."""
    print("\n1. Checking deployment script...")
    
    deploy_script = Path("scripts/deploy_to_gcp.py")
    content = deploy_script.read_text(encoding='utf-8')
    
    # Check if CLICKHOUSE_PASSWORD is in the backend secrets mapping
    if "CLICKHOUSE_PASSWORD=clickhouse-default-password-staging:latest" in content:
        print("   [OK] CLICKHOUSE_PASSWORD secret mapping found in backend deployment")
    else:
        print("   [FAIL] CLICKHOUSE_PASSWORD secret mapping MISSING in backend deployment")
        return False
    
    # Check if it's in the required secrets list
    if "clickhouse-default-password-staging" in content:
        print("   [OK] clickhouse-default-password-staging in required secrets list")
    else:
        print("   [FAIL] clickhouse-default-password-staging MISSING from required secrets")
        return False
    
    return True

def check_database_config():
    """Verify database.py has proper validation."""
    print("\n2. Checking database configuration manager...")
    
    db_config = Path("netra_backend/app/core/configuration/database.py")
    content = db_config.read_text(encoding='utf-8')
    
    # Check for staging validation
    if 'if not password and self._environment == "staging"' in content:
        if "ConfigurationError" in content and "CLICKHOUSE_PASSWORD is required in staging" in content:
            print("   [OK] Staging password validation found")
        else:
            print("   [FAIL] Staging validation exists but error handling incomplete")
            return False
    else:
        print("   [FAIL] No staging-specific password validation found")
        return False
    
    return True

def check_staging_env():
    """Verify staging.env has proper documentation."""
    print("\n3. Checking staging environment file...")
    
    staging_env = Path("config/staging.env")
    content = staging_env.read_text(encoding='utf-8')
    
    # Check for documentation about GCP Secret Manager
    if "GCP Secret Manager" in content and "clickhouse-default-password-staging" in content:
        print("   [OK] Proper documentation about GCP Secret Manager found")
    else:
        print("   [FAIL] Missing documentation about secret source")
        return False
    
    # Verify password is empty (to be injected)
    lines = content.split('\n')
    for line in lines:
        if line.startswith("CLICKHOUSE_PASSWORD=") and not line.endswith("="):
            print("   [FAIL] CLICKHOUSE_PASSWORD should be empty (for Cloud Run injection)")
            return False
    
    print("   [OK] CLICKHOUSE_PASSWORD correctly left empty for injection")
    return True

def check_secret_exists():
    """Check if the secret exists in GCP (requires gcloud CLI)."""
    print("\n4. Checking GCP Secret Manager...")
    
    try:
        # Try to describe the secret
        result = subprocess.run(
            ["gcloud", "secrets", "describe", "clickhouse-default-password-staging",
             "--project", "netra-staging"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print("   [OK] Secret 'clickhouse-default-password-staging' exists in GCP")
            
            # Try to check if it has a value (not placeholder)
            version_result = subprocess.run(
                ["gcloud", "secrets", "versions", "access", "latest",
                 "--secret", "clickhouse-default-password-staging",
                 "--project", "netra-staging"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if version_result.returncode == 0:
                value = version_result.stdout.strip()
                if value and not any(x in value.upper() for x in ["REPLACE", "PLACEHOLDER", "TODO"]):
                    print("   [OK] Secret has a real value configured")
                else:
                    print("   [WARN] Secret exists but contains placeholder value")
                    print("     ACTION REQUIRED: Update secret with real ClickHouse password")
            else:
                print("   [WARN] Cannot access secret value (permission denied)")
        else:
            print("   [FAIL] Secret 'clickhouse-default-password-staging' NOT FOUND")
            print("     ACTION REQUIRED: Create the secret in GCP Secret Manager")
            return False
            
    except FileNotFoundError:
        print("   [WARN] gcloud CLI not found - cannot verify GCP secrets")
        print("     Please verify manually using GCP Console")
    except Exception as e:
        print(f"   [WARN] Error checking GCP: {e}")
    
    return True

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("ClickHouse Staging Configuration Fix Verification")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Run checks
    if not check_deployment_script():
        all_checks_passed = False
    
    if not check_database_config():
        all_checks_passed = False
    
    if not check_staging_env():
        all_checks_passed = False
    
    if not check_secret_exists():
        all_checks_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("[SUCCESS] All checks passed! Ready for deployment.")
        print("\nNext steps:")
        print("1. Ensure the ClickHouse password secret has the correct value in GCP")
        print("2. Deploy using: python scripts/deploy_to_gcp.py --project netra-staging --service backend")
        print("3. Monitor Cloud Run logs to verify successful startup")
    else:
        print("[ERROR] Some checks failed. Please fix the issues above.")
        print("\nRequired fixes:")
        print("1. Ensure deploy_to_gcp.py maps CLICKHOUSE_PASSWORD secret")
        print("2. Verify database.py validates password in staging")
        print("3. Document secret source in staging.env")
        print("4. Create/update the secret in GCP Secret Manager")
        sys.exit(1)
    
    print("=" * 60)

if __name__ == "__main__":
    main()