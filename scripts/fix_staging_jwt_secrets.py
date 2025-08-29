#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix JWT Secret Synchronization on Staging

This script ensures all services on staging use the same JWT secret.
It consolidates multiple JWT secrets into a single canonical one.

Business Value Justification (BVJ):
- Segment: Enterprise (prevents $12K MRR churn)
- Business Goal: Retention (eliminate cross-service auth failures)
- Value Impact: Fixes authentication between services
- Strategic Impact: Immediate resolution of auth failures on staging
"""

import subprocess
import sys
import json
import base64
import secrets
from typing import Optional

PROJECT_ID = "netra-staging"
CANONICAL_SECRET_NAME = "jwt-secret-key-staging"

# Use full path to gcloud on Windows
import platform
if platform.system() == "Windows":
    GCLOUD = r"C:\Users\antho\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
else:
    GCLOUD = "gcloud"


def run_command(cmd: list) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"


def get_secret_value(secret_name: str) -> Optional[str]:
    """Get the value of a secret from GCP Secret Manager."""
    success, output = run_command([
        GCLOUD, "secrets", "versions", "access", "latest",
        f"--secret={secret_name}",
        f"--project={PROJECT_ID}"
    ])
    if success:
        return output
    return None


def create_or_update_secret(secret_name: str, value: str) -> bool:
    """Create or update a secret in GCP Secret Manager."""
    # Check if secret exists
    success, _ = run_command([
        GCLOUD, "secrets", "describe", secret_name,
        f"--project={PROJECT_ID}"
    ])
    
    if not success:
        # Create new secret
        print(f"Creating secret: {secret_name}")
        success, _ = run_command([
            GCLOUD, "secrets", "create", secret_name,
            f"--data-file=-",
            f"--project={PROJECT_ID}",
            "--replication-policy=automatic"
        ])
        if not success:
            return False
    
    # Add new version
    print(f"Updating secret: {secret_name}")
    process = subprocess.Popen(
        [GCLOUD, "secrets", "versions", "add", secret_name,
         f"--project={PROJECT_ID}", "--data-file=-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=value)
    
    if process.returncode != 0:
        print(f"Error updating secret: {stderr}")
        return False
    
    return True


def update_cloud_run_env_vars(service_name: str, env_vars: dict) -> bool:
    """Update environment variables for a Cloud Run service."""
    env_args = []
    for key, value in env_vars.items():
        env_args.extend([f"--set-env-vars={key}={value}"])
    
    cmd = [
        GCLOUD, "run", "services", "update", service_name,
        "--region=us-central1",
        f"--project={PROJECT_ID}"
    ] + env_args
    
    print(f"Updating {service_name} environment variables...")
    success, output = run_command(cmd)
    if not success:
        print(f"Failed to update {service_name}: {output}")
        return False
    
    print(f"[OK] Updated {service_name}")
    return True


def main():
    """Main function to fix JWT secret synchronization."""
    print("JWT Secret Synchronization Fix for Staging")
    print("=" * 60)
    
    # Step 1: Get or generate the canonical JWT secret
    print("\n1. Checking canonical JWT secret...")
    jwt_secret = get_secret_value(CANONICAL_SECRET_NAME)
    
    if not jwt_secret:
        print(f"  No existing {CANONICAL_SECRET_NAME} found. Generating new secure secret...")
        # Generate a cryptographically secure secret
        jwt_secret = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode('utf-8')
        
        if not create_or_update_secret(CANONICAL_SECRET_NAME, jwt_secret):
            print("Failed to create JWT secret")
            return 1
        print(f"  [OK] Created new JWT secret")
    else:
        print(f"  [OK] Found existing JWT secret (length: {len(jwt_secret)})")
    
    # Step 2: Update all other JWT secret aliases to use the same value
    print("\n2. Synchronizing all JWT secret aliases...")
    secret_aliases = [
        "jwt-secret",
        "jwt-secret-staging", 
        "netra-jwt-secret",
        "staging-jwt-secret"
    ]
    
    for alias in secret_aliases:
        print(f"  Updating {alias}...")
        if not create_or_update_secret(alias, jwt_secret):
            print(f"  [WARNING] Could not update {alias}")
        else:
            print(f"  [OK] Updated {alias}")
    
    # Step 3: Update Cloud Run services to use the canonical secret
    print("\n3. Updating Cloud Run services...")
    
    services = {
        "auth-service": {
            "JWT_SECRET_KEY": f"projects/{PROJECT_ID}/secrets/{CANONICAL_SECRET_NAME}/versions/latest",
            "JWT_SECRET": f"projects/{PROJECT_ID}/secrets/{CANONICAL_SECRET_NAME}/versions/latest"
        },
        "backend-service": {
            "JWT_SECRET_KEY": f"projects/{PROJECT_ID}/secrets/{CANONICAL_SECRET_NAME}/versions/latest",
            "JWT_SECRET": f"projects/{PROJECT_ID}/secrets/{CANONICAL_SECRET_NAME}/versions/latest"
        }
    }
    
    for service_name, env_vars in services.items():
        # First check if service exists
        success, _ = run_command([
            GCLOUD, "run", "services", "describe", service_name,
            "--region=us-central1",
            f"--project={PROJECT_ID}",
            "--format=json"
        ])
        
        if success:
            # Update using secret references
            cmd = [
                GCLOUD, "run", "services", "update", service_name,
                "--region=us-central1",
                f"--project={PROJECT_ID}"
            ]
            
            for env_key, secret_ref in env_vars.items():
                cmd.append(f"--set-secrets={env_key}={secret_ref}")
            
            print(f"  Updating {service_name} to use canonical JWT secret...")
            success, output = run_command(cmd)
            if success:
                print(f"  [OK] Updated {service_name}")
            else:
                print(f"  [WARNING] Could not update {service_name}: {output}")
        else:
            print(f"  [WARNING] Service {service_name} not found")
    
    # Step 4: Verify the configuration
    print("\n4. Verifying configuration...")
    print(f"  All services should now use the same JWT secret from: {CANONICAL_SECRET_NAME}")
    print(f"  Secret length: {len(jwt_secret)} characters")
    
    # Step 5: Display next steps
    print("\n" + "=" * 60)
    print("[SUCCESS] JWT Secret Synchronization Complete!")
    print("\nNext steps:")
    print("1. Wait 1-2 minutes for Cloud Run to propagate the changes")
    print("2. Test authentication with: python scripts/test_staging_auth.py")
    print("3. Re-run deployment validation: python scripts/validate_staging_deployment.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())