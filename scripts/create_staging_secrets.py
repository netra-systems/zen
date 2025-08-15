#!/usr/bin/env python3
"""Create staging secrets in Google Secret Manager.

This script creates the required staging secrets by copying from production
secrets or using provided values.
"""

import subprocess
import sys
import json
from typing import Dict, Optional

# Required secrets for staging environment
REQUIRED_SECRETS = [
    "gemini-api-key-staging",
    "google-client-id-staging", 
    "google-client-secret-staging",
    "jwt-secret-key-staging",
    "fernet-key-staging",
    "langfuse-secret-key-staging",
    "langfuse-public-key-staging",
    "clickhouse-default-password-staging",
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
    if len(sys.argv) < 2:
        print("Usage: python create_staging_secrets.py <project-id>")
        print("Example: python create_staging_secrets.py netra-staging")
        sys.exit(1)
    
    project_id = sys.argv[1]
    
    print(f"Creating staging secrets in project: {project_id}")
    print("=" * 60)
    
    # Check and create required secrets
    missing_required = []
    created_secrets = []
    
    for secret_name in REQUIRED_SECRETS:
        if check_secret_exists(project_id, secret_name):
            print(f"✓ {secret_name} already exists")
        else:
            print(f"✗ {secret_name} is missing")
            missing_required.append(secret_name)
    
    if missing_required:
        print("\n" + "=" * 60)
        print("Creating missing required secrets...")
        print("Attempting to copy from production secrets...")
        
        for secret_name in missing_required:
            # Try to get from production
            prod_value = get_production_secret(project_id, secret_name)
            
            if prod_value:
                if create_secret(project_id, secret_name, prod_value):
                    print(f"✓ Created {secret_name} from production")
                    created_secrets.append(secret_name)
                else:
                    print(f"✗ Failed to create {secret_name}")
            else:
                # For critical secrets, provide instructions
                if "jwt-secret-key" in secret_name:
                    print(f"⚠ {secret_name}: Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
                elif "fernet-key" in secret_name:
                    print(f"⚠ {secret_name}: Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
                else:
                    print(f"⚠ {secret_name}: Must be manually configured")
    
    # Summary
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
    
    print("\nNext steps:")
    print("1. Apply terraform changes: cd terraform/staging/shared-infrastructure && terraform apply")
    print("2. Redeploy Cloud Run service to pick up IAM changes")
    print("3. Verify secrets are loading correctly in logs")


if __name__ == "__main__":
    main()