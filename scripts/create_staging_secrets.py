#!/usr/bin/env python3
"""Create staging secrets in Google Secret Manager.

This script creates the required staging secrets by copying from production
secrets or using provided values.
"""

import json
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# Required secrets for staging environment
REQUIRED_SECRETS = [
    "gemini-api-key-staging",
    "google-oauth-client-id-staging", 
    "google-oauth-client-secret-staging",
    "jwt-secret-key-staging",
    "fernet-key-staging",
    "langfuse-secret-key-staging",
    "langfuse-public-key-staging",
    "clickhouse-password-staging",
]

# Optional secrets
OPTIONAL_SECRETS = [
    "anthropic-api-key-staging",
    "openai-api-key-staging",
    "cohere-api-key-staging",
    "mistral-api-key-staging",
    "redis-default-staging",
    "slack-webhook-url-staging",
    "sendgrid-api-key-staging",
    "sentry-dsn-staging",
]


def check_secret_exists(project_id: str, secret_name: str) -> bool:
    """Check if a secret exists in Secret Manager."""
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "describe", secret_name, "--project", project_id],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking secret {secret_name}: {e}")
        return False


def create_secret(project_id: str, secret_name: str, secret_value: str) -> bool:
    """Create a secret in Secret Manager."""
    try:
        # Create the secret
        result = subprocess.run(
            ["gcloud", "secrets", "create", secret_name, "--project", project_id],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print(f"Failed to create secret {secret_name}: {result.stderr}")
            return False
        
        # Add the secret version
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "add", secret_name, 
             "--data-file=-", "--project", project_id],
            input=secret_value,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            print(f"Failed to add version to secret {secret_name}: {result.stderr}")
            return False
            
        return True
    except Exception as e:
        print(f"Error creating secret {secret_name}: {e}")
        return False


def get_production_secret(project_id: str, secret_name: str) -> Optional[str]:
    """Get a secret value from production (without -staging suffix)."""
    prod_secret_name = secret_name.replace("-staging", "")
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest",
             "--secret", prod_secret_name, "--project", project_id],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        print(f"Error getting production secret {prod_secret_name}: {e}")
        return None


def main():
    """Main function."""
    project_id = _validate_arguments()
    missing_required, created_secrets = _check_existing_secrets(project_id)
    if missing_required:
        created_secrets = _create_missing_secrets(project_id, missing_required, created_secrets)
    _print_summary(missing_required, created_secrets)
    _print_next_steps()

def _validate_arguments() -> str:
    """Validate command line arguments and return project ID."""
    if len(sys.argv) < 2:
        print("Usage: python create_staging_secrets.py <project-id>")
        print("Example: python create_staging_secrets.py netra-staging")
        sys.exit(1)
    return sys.argv[1]

def _check_existing_secrets(project_id: str) -> Tuple[List[str], List[str]]:
    """Check which secrets exist and return missing ones."""
    print(f"Creating staging secrets in project: {project_id}")
    print("=" * 60)
    missing_required = []
    for secret_name in REQUIRED_SECRETS:
        if check_secret_exists(project_id, secret_name):
            print(f"[U+2713] {secret_name} already exists")
        else:
            print(f"[U+2717] {secret_name} is missing")
            missing_required.append(secret_name)
    return missing_required, []

def _create_missing_secrets(project_id: str, missing_required: List[str], created_secrets: List[str]) -> List[str]:
    """Create missing secrets from production or provide instructions."""
    print("\n" + "=" * 60)
    print("Creating missing required secrets...")
    print("Attempting to copy from production secrets...")
    for secret_name in missing_required:
        prod_value = get_production_secret(project_id, secret_name)
        if prod_value:
            if create_secret(project_id, secret_name, prod_value):
                print(f"[U+2713] Created {secret_name} from production")
                created_secrets.append(secret_name)
            else:
                print(f"[U+2717] Failed to create {secret_name}")
        else:
            _provide_manual_instructions(secret_name)
    return created_secrets

def _provide_manual_instructions(secret_name: str):
    """Provide manual instructions for critical secrets."""
    if "jwt-secret-key" in secret_name:
        print(f" WARNING:  {secret_name}: Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    elif "fernet-key" in secret_name:
        print(f" WARNING:  {secret_name}: Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    else:
        print(f" WARNING:  {secret_name}: Must be manually configured")

def _print_summary(missing_required: List[str], created_secrets: List[str]):
    """Print summary of created secrets."""
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"Created {len(created_secrets)} secrets")
    if missing_required:
        still_missing = [s for s in missing_required if s not in created_secrets]
        if still_missing:
            print(f"Still missing {len(still_missing)} required secrets:")
            for secret in still_missing:
                print(f"  - {secret}")
            print("\nTo manually create a secret:")
            print("echo 'YOUR_SECRET_VALUE' | gcloud secrets create SECRET_NAME --data-file=- --project PROJECT_ID")
    else:
        print("All required secrets are configured!")

def _print_next_steps():
    """Print next steps for deployment."""
    print("\nNext steps:")
    print("1. Apply terraform changes: cd terraform/staging/shared-infrastructure && terraform apply")
    print("2. Redeploy Cloud Run service to pick up IAM changes")
    print("3. Verify secrets are loading correctly in logs")


if __name__ == "__main__":
    main()