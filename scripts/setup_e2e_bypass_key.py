#!/usr/bin/env python3
"""
Setup E2E Bypass Key for Staging Environment

This script helps set up the E2E authentication bypass key in Google Secrets Manager
for the staging environment. It generates a secure key and stores it properly.

Usage:
    python scripts/setup_E2E_OAUTH_SIMULATION_KEY.py [--project PROJECT_ID]
"""

import os
import sys
import secrets
import argparse
import subprocess
import json
from typing import Optional


def generate_secure_key(length: int = 32) -> str:
    """Generate a cryptographically secure random key."""
    return secrets.token_hex(length)


def check_gcloud_auth() -> bool:
    """Check if gcloud is authenticated."""
    try:
        # Try to use gcloud.cmd on Windows, gcloud on Unix
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        result = subprocess.run(
            [gcloud_cmd, "auth", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        accounts = json.loads(result.stdout)
        # Check if any account is ACTIVE or if we have accounts at all
        has_active = any(acc.get("status") == "ACTIVE" for acc in accounts)
        has_accounts = len(accounts) > 0
        return has_active or has_accounts
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return False


def secret_exists(project_id: str, secret_name: str) -> bool:
    """Check if a secret already exists in Google Secrets Manager."""
    try:
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        result = subprocess.run(
            [gcloud_cmd, "secrets", "describe", secret_name, f"--project={project_id}"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        print("ERROR: gcloud CLI not found. Please install Google Cloud SDK.")
        sys.exit(1)


def create_secret(project_id: str, secret_name: str, secret_value: str) -> bool:
    """Create a new secret in Google Secrets Manager."""
    try:
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        # Create the secret
        result = subprocess.run(
            [gcloud_cmd, "secrets", "create", secret_name, f"--project={project_id}", "--replication-policy=automatic"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Failed to create secret: {result.stderr}")
            return False
        
        # Add the secret version with the value
        result = subprocess.run(
            [gcloud_cmd, "secrets", "versions", "add", secret_name, f"--project={project_id}", "--data-file=-"],
            input=secret_value,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Failed to add secret version: {result.stderr}")
            return False
        
        return True
        
    except FileNotFoundError:
        print("ERROR: gcloud CLI not found. Please install Google Cloud SDK.")
        return False


def update_secret(project_id: str, secret_name: str, secret_value: str) -> bool:
    """Update an existing secret in Google Secrets Manager."""
    try:
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        result = subprocess.run(
            [gcloud_cmd, "secrets", "versions", "add", secret_name, f"--project={project_id}", "--data-file=-"],
            input=secret_value,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Failed to update secret: {result.stderr}")
            return False
        
        return True
        
    except FileNotFoundError:
        print("ERROR: gcloud CLI not found. Please install Google Cloud SDK.")
        return False


def grant_secret_access(project_id: str, secret_name: str, service_account: str) -> bool:
    """Grant a service account access to read the secret."""
    try:
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        member = f"serviceAccount:{service_account}"
        result = subprocess.run(
            [
                gcloud_cmd, "secrets", "add-iam-policy-binding", secret_name,
                f"--project={project_id}",
                "--role=roles/secretmanager.secretAccessor",
                f"--member={member}"
            ],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("ERROR: gcloud CLI not found. Please install Google Cloud SDK.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Setup E2E bypass key for staging environment")
    parser.add_argument(
        "--project",
        default="netra-staging",
        help="GCP project ID (default: netra-staging)"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing secret instead of creating new one"
    )
    parser.add_argument(
        "--key",
        help="Use specific key value instead of generating one"
    )
    parser.add_argument(
        "--grant-access",
        action="store_true",
        help="Grant service accounts access to the secret"
    )
    
    args = parser.parse_args()
    
    # Check gcloud authentication
    if not check_gcloud_auth():
        print("ERROR: Not authenticated with gcloud. Please run:")
        print("  gcloud auth login")
        sys.exit(1)
    
    secret_name = "e2e-bypass-key"
    project_id = args.project
    
    # Check if secret exists
    exists = secret_exists(project_id, secret_name)
    
    if exists and not args.update:
        print(f"Secret '{secret_name}' already exists in project '{project_id}'.")
        print("Use --update flag to update it.")
        sys.exit(1)
    
    if not exists and args.update:
        print(f"Secret '{secret_name}' does not exist in project '{project_id}'.")
        print("Remove --update flag to create it.")
        sys.exit(1)
    
    # Generate or use provided key
    if args.key:
        bypass_key = args.key
        print("Using provided key.")
    else:
        bypass_key = generate_secure_key()
        print(f"Generated new secure key: {bypass_key}")
    
    # Create or update secret
    if exists:
        print(f"Updating secret '{secret_name}' in project '{project_id}'...")
        success = update_secret(project_id, secret_name, bypass_key)
    else:
        print(f"Creating secret '{secret_name}' in project '{project_id}'...")
        success = create_secret(project_id, secret_name, bypass_key)
    
    if not success:
        print("Failed to create/update secret.")
        sys.exit(1)
    
    print("Secret successfully created/updated!")
    
    # Grant access to service accounts if requested
    if args.grant_access:
        service_accounts = [
            f"staging-auth-service@{project_id}.iam.gserviceaccount.com",
            f"staging-backend@{project_id}.iam.gserviceaccount.com",
            f"cloud-run-service@{project_id}.iam.gserviceaccount.com"
        ]
        
        print("\nGranting access to service accounts...")
        for sa in service_accounts:
            if grant_secret_access(project_id, secret_name, sa):
                print(f"  [U+2713] Granted access to {sa}")
            else:
                print(f"  [U+2717] Failed to grant access to {sa}")
    
    # Print usage instructions
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nTo use this key in your E2E tests:")
    print(f"  export E2E_OAUTH_SIMULATION_KEY='{bypass_key}'")
    print(f"  export ENVIRONMENT=staging")
    print(f"  export STAGING_AUTH_URL=https://api.staging.netrasystems.ai")
    print("\nOr add to your .env file:")
    print(f"  E2E_OAUTH_SIMULATION_KEY={bypass_key}")
    print("\nTest the OAUTH SIMULATION:")
    print(f"  python tests/e2e/staging_auth_bypass.py")
    print("\n" + "="*60)
    
    # Save key to local file for reference (git-ignored)
    key_file = ".e2e-bypass-key"
    with open(key_file, "w") as f:
        f.write(bypass_key)
    print(f"\nKey saved to {key_file} (git-ignored) for local reference.")


if __name__ == "__main__":
    main()