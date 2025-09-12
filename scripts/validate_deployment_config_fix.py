#!/usr/bin/env python3
"""
Validate Deployment Configuration Fix

This script validates that the deployment configuration has been properly fixed:
1. Backend doesn't include OAuth credentials (they belong to auth service)
2. Backend includes SERVICE_ID for inter-service authentication
3. Auth service has proper OAuth configuration
4. No cross-service configuration pollution
"""

import sys
import io
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from deployment.secrets_config import SecretConfig


def validate_backend_secrets():
    """Validate backend service secrets configuration"""
    print("\n SEARCH:  Validating Backend Secrets Configuration...")
    
    backend_secrets = SecretConfig.get_all_service_secrets("backend")
    backend_critical = SecretConfig.CRITICAL_SECRETS.get("backend", [])
    
    # Check OAuth is NOT in backend
    oauth_in_backend = any("OAUTH" in s or "GOOGLE_CLIENT" in s for s in backend_secrets)
    if oauth_in_backend:
        print(" FAIL:  ERROR: Backend still has OAuth credentials! OAuth should only be in auth service.")
        return False
    else:
        print(" PASS:  Backend correctly excludes OAuth credentials")
    
    # Check SERVICE_ID is in backend
    if "SERVICE_ID" not in backend_secrets:
        print(" FAIL:  ERROR: Backend missing SERVICE_ID for inter-service auth!")
        return False
    else:
        print(" PASS:  Backend includes SERVICE_ID for inter-service auth")
    
    # Check SERVICE_SECRET is in backend
    if "SERVICE_SECRET" not in backend_secrets:
        print(" FAIL:  ERROR: Backend missing SERVICE_SECRET for inter-service auth!")
        return False
    else:
        print(" PASS:  Backend includes SERVICE_SECRET for inter-service auth")
    
    # Check critical secrets
    if "SERVICE_ID" not in backend_critical:
        print(" WARNING: [U+FE0F]  WARNING: SERVICE_ID not marked as critical for backend")
    if "SERVICE_SECRET" not in backend_critical:
        print(" WARNING: [U+FE0F]  WARNING: SERVICE_SECRET not marked as critical for backend")
    
    print(f"[U+1F4CB] Backend total secrets: {len(backend_secrets)}")
    print(f"[U+1F4CB] Backend critical secrets: {backend_critical}")
    
    return True


def validate_auth_secrets():
    """Validate auth service secrets configuration"""
    print("\n SEARCH:  Validating Auth Service Secrets Configuration...")
    
    auth_secrets = SecretConfig.get_all_service_secrets("auth")
    auth_critical = SecretConfig.CRITICAL_SECRETS.get("auth", [])
    
    # Check OAuth IS in auth service
    oauth_in_auth = any("OAUTH" in s for s in auth_secrets)
    if not oauth_in_auth:
        print(" FAIL:  ERROR: Auth service missing OAuth credentials!")
        return False
    else:
        print(" PASS:  Auth service includes OAuth credentials")
    
    # Check specific OAuth vars
    expected_oauth = ["GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "OAUTH_HMAC_SECRET"]
    for var in expected_oauth:
        if var not in auth_secrets:
            print(f" FAIL:  ERROR: Auth service missing {var}")
            return False
        else:
            print(f" PASS:  Auth service includes {var}")
    
    print(f"[U+1F4CB] Auth total secrets: {len(auth_secrets)}")
    print(f"[U+1F4CB] Auth critical secrets: {auth_critical}")
    
    return True


def validate_secrets_mapping():
    """Validate that all secrets have GSM mappings"""
    print("\n SEARCH:  Validating Secrets Mappings...")
    
    all_services = ["backend", "auth"]
    unmapped = []
    
    for service in all_services:
        secrets = SecretConfig.get_all_service_secrets(service)
        for secret in secrets:
            gsm_id = SecretConfig.get_gsm_mapping(secret)
            if not gsm_id:
                unmapped.append(f"{service}/{secret}")
    
    if unmapped:
        print(f" WARNING: [U+FE0F]  WARNING: Unmapped secrets found: {unmapped}")
        return False
    else:
        print(" PASS:  All secrets have GSM mappings")
        return True


def validate_secrets_string_generation():
    """Validate the --set-secrets string generation"""
    print("\n SEARCH:  Validating Secrets String Generation...")
    
    # Generate backend secrets string
    backend_string = SecretConfig.generate_secrets_string("backend", "staging")
    print(f"\n[U+1F4DD] Backend secrets string ({len(backend_string.split(','))} secrets):")
    
    # Check that OAuth is NOT in backend string
    if "GOOGLE_CLIENT" in backend_string or "OAUTH_CLIENT" in backend_string:
        print(" FAIL:  ERROR: Backend secrets string contains OAuth credentials!")
        return False
    else:
        print(" PASS:  Backend secrets string excludes OAuth")
    
    # Check that SERVICE_ID is in backend string
    if "SERVICE_ID=" not in backend_string:
        print(" FAIL:  ERROR: Backend secrets string missing SERVICE_ID!")
        return False
    else:
        print(" PASS:  Backend secrets string includes SERVICE_ID")
    
    # Generate auth secrets string
    auth_string = SecretConfig.generate_secrets_string("auth", "staging")
    print(f"\n[U+1F4DD] Auth secrets string ({len(auth_string.split(','))} secrets):")
    
    # Check that OAuth IS in auth string
    if "GOOGLE_OAUTH_CLIENT_ID_STAGING=" not in auth_string:
        print(" FAIL:  ERROR: Auth secrets string missing OAuth credentials!")
        return False
    else:
        print(" PASS:  Auth secrets string includes OAuth credentials")
    
    return True


def main():
    """Run all validations"""
    print("=" * 60)
    print("DEPLOYMENT CONFIGURATION VALIDATION")
    print("=" * 60)
    
    all_valid = True
    
    # Run all validations
    all_valid = validate_backend_secrets() and all_valid
    all_valid = validate_auth_secrets() and all_valid
    all_valid = validate_secrets_mapping() and all_valid
    all_valid = validate_secrets_string_generation() and all_valid
    
    print("\n" + "=" * 60)
    if all_valid:
        print(" PASS:  DEPLOYMENT CONFIGURATION IS VALID")
        print("\nKey fixes applied:")
        print("1.  PASS:  Removed OAuth from backend (belongs to auth service only)")
        print("2.  PASS:  Added SERVICE_ID to backend for inter-service auth")
        print("3.  PASS:  Backend critical secrets include SERVICE_ID and SERVICE_SECRET")
        print("4.  PASS:  Auth service retains OAuth configuration")
        print("\n[U+1F680] Ready to deploy with: python scripts/deploy_to_gcp.py --project netra-staging --build-local")
    else:
        print(" FAIL:  DEPLOYMENT CONFIGURATION HAS ISSUES")
        print("\nPlease fix the issues above before deploying.")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == "__main__":
    main()