#!/usr/bin/env python3
"""
Verification script for GCP deployment environment variables.
Ensures all required environment variables are properly configured for each service.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Set

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def verify_deployment_config() -> bool:
    """Verify that all required environment variables are configured in deployment script."""
    
    deployment_script = project_root / "scripts" / "deploy_to_gcp.py"
    
    print("Verifying GCP Deployment Environment Variables Configuration")
    print("=" * 60)
    
    # Read deployment script
    with open(deployment_script, 'r', encoding='utf-8') as f:
        code = f.read()
    
    all_checks_passed = True
    
    # 1. Check Backend Service Configuration
    print("\n[CHECK] Backend Service Environment Variables:")
    backend_required = {
        "ENVIRONMENT": "staging",
        "PYTHONUNBUFFERED": "1",
        "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
        "FRONTEND_URL": "https://app.staging.netrasystems.ai",
        "FORCE_HTTPS": "true",
        "GCP_PROJECT_ID": "self.project_id"  # CRITICAL
    }
    
    backend_start = code.find('name="backend"')
    backend_end = code.find('ServiceConfig(', backend_start + 1)
    backend_section = code[backend_start:backend_end] if backend_end > 0 else code[backend_start:backend_start+1000]
    
    for var, expected_value in backend_required.items():
        if var in backend_section:
            print(f"  [OK] {var}: Configured")
            if var == "GCP_PROJECT_ID" and "self.project_id" in backend_section:
                print(f"     -> Will be set to deployment project ID dynamically")
        else:
            print(f"  [FAIL] {var}: MISSING")
            all_checks_passed = False
    
    # 2. Check Auth Service Configuration
    print("\n[CHECK] Auth Service Environment Variables:")
    auth_required = {
        "ENVIRONMENT": "staging",
        "PYTHONUNBUFFERED": "1",
        "FRONTEND_URL": "https://app.staging.netrasystems.ai",
        "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
        "JWT_ALGORITHM": "HS256",
        "REDIS_DISABLED": "false",
        "FORCE_HTTPS": "true",
        "GCP_PROJECT_ID": "self.project_id"  # CRITICAL
    }
    
    auth_start = code.find('name="auth"')
    auth_end = code.find('ServiceConfig(', auth_start + 1)
    auth_section = code[auth_start:auth_end] if auth_end > 0 else code[auth_start:auth_start+1000]
    
    for var, expected_value in auth_required.items():
        if var in auth_section:
            print(f"  [OK] {var}: Configured")
            if var == "GCP_PROJECT_ID" and "self.project_id" in auth_section:
                print(f"     -> Will be set to deployment project ID dynamically")
        else:
            print(f"  [FAIL] {var}: MISSING")
            all_checks_passed = False
    
    # 3. Check Secret Manager Integration
    print("\n[CHECK] Secret Manager Configuration:")
    backend_secrets = [
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD",
        "JWT_SECRET_KEY", "SECRET_KEY", "OPENAI_API_KEY", "FERNET_KEY", "GEMINI_API_KEY",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
        "SERVICE_SECRET", "REDIS_URL", "REDIS_PASSWORD", "ANTHROPIC_API_KEY"
    ]
    
    backend_secrets_start = code.find('if service.name == "backend":')
    backend_secrets_end = code.find('elif service.name == "auth":', backend_secrets_start)
    backend_secrets_section = code[backend_secrets_start:backend_secrets_end]
    
    missing_secrets = []
    for secret in backend_secrets:
        # Check if secret is referenced in the --set-secrets command
        secret_pattern = f"{secret}="
        if secret_pattern in backend_secrets_section:
            print(f"  [OK] {secret}: Configured in backend")
        else:
            print(f"  [FAIL] {secret}: MISSING in backend")
            missing_secrets.append(secret)
            all_checks_passed = False
    
    # 4. Check Cloud SQL Configuration
    print("\n[CHECK] Cloud SQL Configuration:")
    if "--add-cloudsql-instances" in backend_secrets_section:
        print("  [OK] Cloud SQL instances configured for backend")
        if "staging-shared-postgres" in backend_secrets_section:
            print("  [OK] Staging shared postgres instance configured")
        else:
            print("  [FAIL] Staging shared postgres instance MISSING")
            all_checks_passed = False
    else:
        print("  [FAIL] Cloud SQL configuration MISSING for backend")
        all_checks_passed = False
    
    # 5. Check OAuth Validation
    print("\n[CHECK] OAuth Validation:")
    if "_validate_oauth_configuration" in code:
        print("  [OK] OAuth validation method present")
        if "DEPLOYMENT ABORTED - OAuth validation failed" in code:
            print("  [OK] OAuth validation failure handling present")
        else:
            print("  [WARN] OAuth validation failure handling weak")
    else:
        print("  [FAIL] OAuth validation method MISSING")
        all_checks_passed = False
    
    # 6. Check JWT Secret Consistency
    print("\n[CHECK] JWT Secret Consistency:")
    setup_secrets_start = code.find('def setup_secrets')
    setup_secrets_end = code.find('def ', setup_secrets_start + 1)
    setup_secrets_section = code[setup_secrets_start:setup_secrets_end]
    
    if 'jwt_secret_value =' in setup_secrets_section:
        print("  [OK] JWT secret value defined once")
        if '"jwt-secret-key-staging": jwt_secret_value' in setup_secrets_section and \
           '"jwt-secret-staging": jwt_secret_value' in setup_secrets_section:
            print("  [OK] JWT secrets use same value for both services")
        else:
            print("  [FAIL] JWT secrets NOT using same value")
            all_checks_passed = False
    else:
        print("  [FAIL] JWT secret value not properly defined")
        all_checks_passed = False
    
    # 7. Verify Project ID Usage
    print("\n[CHECK] Project ID Configuration:")
    if "__init__(self, project_id:" in code:
        print("  [OK] Project ID parameter accepted")
        if "self.project_id = project_id" in code:
            print("  [OK] Project ID stored as instance variable")
            if '"GCP_PROJECT_ID": self.project_id' in code:
                print("  [OK] GCP_PROJECT_ID uses dynamic project ID")
                print(f"     -> Will be 'netra-staging' when deploying to staging")
                print(f"     -> Will be 'netra-production' when deploying to production")
            else:
                print("  [FAIL] GCP_PROJECT_ID not using dynamic project ID")
                all_checks_passed = False
        else:
            print("  [FAIL] Project ID not stored properly")
            all_checks_passed = False
    else:
        print("  [FAIL] Project ID parameter not accepted in __init__")
        all_checks_passed = False
    
    # Final Summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("[SUCCESS] ALL CHECKS PASSED - Deployment configuration is correct!")
        print("\nWhen deploying with: python scripts/deploy_to_gcp.py --project netra-staging")
        print("  -> GCP_PROJECT_ID will be set to: netra-staging")
        print("  -> This enables secret loading in GCP environment")
    else:
        print("[ERROR] SOME CHECKS FAILED - Please fix the issues above")
        print("\nCRITICAL: GCP_PROJECT_ID must be set for secret loading to work!")
    
    return all_checks_passed


if __name__ == "__main__":
    success = verify_deployment_config()
    sys.exit(0 if success else 1)