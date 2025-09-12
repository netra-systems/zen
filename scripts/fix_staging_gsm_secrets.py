#!/usr/bin/env python3
"""
Fix staging GSM secrets - Create the ACTUAL secrets that the deployment expects.

The deployment script uses --set-secrets which expects these exact GSM secret names
to exist. This script ensures they exist with proper values.

Usage:
    python scripts/fix_staging_gsm_secrets.py --project netra-staging --create
"""

import os
import sys
import subprocess
import argparse
import json


def check_secret_exists(secret_name: str, project: str) -> tuple[bool, str]:
    """Check if a secret exists and get its value."""
    gcloud = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
    
    # Check if secret exists
    result = subprocess.run(
        [gcloud, "secrets", "describe", secret_name, "--project", project],
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode != 0:
        return False, None
    
    # Get the current value
    result = subprocess.run(
        [gcloud, "secrets", "versions", "access", "latest",
         "--secret", secret_name, "--project", project],
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode == 0:
        return True, result.stdout.strip()
    return True, None


def create_or_update_secret(secret_name: str, value: str, project: str) -> bool:
    """Create or update a secret in GSM."""
    gcloud = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
    
    exists, _ = check_secret_exists(secret_name, project)
    
    if not exists:
        # Create the secret
        result = subprocess.run(
            [gcloud, "secrets", "create", secret_name,
             "--replication-policy", "automatic",
             "--project", project],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0 and "already exists" not in result.stderr:
            print(f" FAIL:  Failed to create {secret_name}: {result.stderr}")
            return False
    
    # Add a new version with the value
    result = subprocess.run(
        [gcloud, "secrets", "versions", "add", secret_name,
         "--data-file", "-", "--project", project],
        input=value,
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode == 0:
        print(f" PASS:  Set {secret_name}")
        return True
    else:
        print(f" FAIL:  Failed to set {secret_name}: {result.stderr}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fix staging GSM secrets")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--create", action="store_true", help="Create missing secrets")
    parser.add_argument("--check-only", action="store_true", help="Only check, don't create")
    args = parser.parse_args()
    
    print(f"\n SEARCH:  Checking GSM secrets for {args.project}...\n")
    
    # Define the REQUIRED secrets based on deployment/secrets_config.py
    required_secrets = {
        # Database - CRITICAL for DatabaseURLBuilder
        "postgres-host-staging": f"/cloudsql/{args.project}:us-central1:staging-shared-postgres",
        "postgres-port-staging": "5432",
        "postgres-db-staging": "netra_staging",
        "postgres-user-staging": "netra_user",
        "postgres-password-staging": "CHANGE_ME_SECURE_PASSWORD",  # Must be updated
        
        # Authentication - CRITICAL
        "jwt-secret-staging": "CHANGE_ME_SECURE_JWT_SECRET_64_CHARS_MIN",
        "jwt-secret-key-staging": "CHANGE_ME_SECURE_JWT_SECRET_KEY_64_CHARS_MIN", 
        "secret-key-staging": "CHANGE_ME_SECURE_SECRET_KEY_64_CHARS_MIN",
        "service-secret-staging": "CHANGE_ME_SECURE_SERVICE_SECRET",
        "service-id-staging": "staging-service-001",
        "fernet-key-staging": "CHANGE_ME_VALID_FERNET_KEY",  # Must be valid Fernet key
        
        # Redis
        "redis-host-staging": "10.0.0.1",  # CHANGE to actual Memorystore IP
        "redis-port-staging": "6379",
        "redis-url-staging": "redis://10.0.0.1:6379",  # CHANGE IP
        "redis-password-staging": "",  # Leave empty if no auth
        
        # OAuth (optional but needed for OAuth login)
        "google-oauth-client-id-staging": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "google-oauth-client-secret-staging": "YOUR_CLIENT_SECRET",
        "oauth-hmac-secret-staging": "CHANGE_ME_SECURE_HMAC_SECRET",
        
        # AI Services (optional)
        "openai-api-key-staging": "sk-YOUR_KEY",
        "anthropic-api-key-staging": "sk-ant-YOUR_KEY",
        "gemini-api-key-staging": "YOUR_KEY",
        
        # Analytics (optional)
        "clickhouse-password-staging": "YOUR_CLICKHOUSE_PASSWORD"
    }
    
    missing = []
    needs_update = []
    good = []
    
    for secret_name, default_value in required_secrets.items():
        exists, current_value = check_secret_exists(secret_name, args.project)
        
        if not exists:
            print(f" FAIL:  MISSING: {secret_name}")
            missing.append(secret_name)
        elif current_value and ("CHANGE_ME" in current_value or "YOUR_" in current_value):
            print(f" WARNING: [U+FE0F]  NEEDS UPDATE: {secret_name} (has placeholder value)")
            needs_update.append(secret_name)
        elif current_value:
            print(f" PASS:  EXISTS: {secret_name}")
            good.append(secret_name)
        else:
            print(f" WARNING: [U+FE0F]  EMPTY: {secret_name}")
            needs_update.append(secret_name)
    
    print(f"\n CHART:  Summary:")
    print(f"   PASS:  Good: {len(good)}")
    print(f"   FAIL:  Missing: {len(missing)}")
    print(f"   WARNING: [U+FE0F]  Needs update: {len(needs_update)}")
    
    if args.create and (missing or needs_update):
        print(f"\n[U+1F527] Creating/updating secrets...\n")
        
        for secret_name in missing:
            default_value = required_secrets[secret_name]
            create_or_update_secret(secret_name, default_value, args.project)
        
        print(f"\n WARNING: [U+FE0F]  CRITICAL: Update these secrets with real values:")
        print(f"  1. postgres-password-staging: Your Cloud SQL password")
        print(f"  2. redis-host-staging: Your Memorystore IP address")
        print(f"  3. JWT/SECRET keys: Generate secure random values")
        print(f"  4. OAuth credentials: Your Google OAuth app credentials")
        
        print(f"\nExample commands to update:")
        print(f'echo "your-actual-password" | gcloud secrets versions add postgres-password-staging --data-file=- --project={args.project}')
        print(f'echo "10.x.x.x" | gcloud secrets versions add redis-host-staging --data-file=- --project={args.project}')
        
    elif not args.create and missing:
        print(f"\n FAIL:  Missing secrets found! Run with --create to create them:")
        print(f"  python scripts/fix_staging_gsm_secrets.py --project {args.project} --create")
    
    if not missing and not needs_update:
        print(f"\n CELEBRATION:  All secrets are properly configured!")
        print(f"\nYou can now deploy:")
        print(f"  python scripts/deploy_to_gcp.py --project {args.project} --build-local")


if __name__ == "__main__":
    main()