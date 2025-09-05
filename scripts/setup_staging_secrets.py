#!/usr/bin/env python3
"""
Setup critical Google Secret Manager secrets for staging environment.

This script ensures all required secrets exist in GSM for the staging deployment.
It creates missing secrets with appropriate default values.

Usage:
    python scripts/setup_staging_secrets.py --project netra-staging
    
IMPORTANT: Update the placeholder values with your actual credentials before deploying.
"""

import os
import sys
import subprocess
import json
import argparse
import secrets
import base64
from typing import Dict, Optional


class StagingSecretSetup:
    """Manages creation and validation of staging GSM secrets."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        
    def check_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists in GSM."""
        try:
            result = subprocess.run(
                [self.gcloud_cmd, "secrets", "describe", secret_name, 
                 "--project", self.project_id],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def create_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create a secret in GSM."""
        try:
            # First create the secret
            result = subprocess.run(
                [self.gcloud_cmd, "secrets", "create", secret_name,
                 "--replication-policy", "automatic",
                 "--project", self.project_id],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0 and "already exists" not in result.stderr:
                print(f"   ❌ Failed to create secret {secret_name}: {result.stderr}")
                return False
            
            # Then add the secret value
            result = subprocess.run(
                [self.gcloud_cmd, "secrets", "versions", "add", secret_name,
                 "--data-file", "-", "--project", self.project_id],
                input=secret_value,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                print(f"   ✅ Created secret: {secret_name}")
                return True
            else:
                print(f"   ❌ Failed to add version to {secret_name}: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error creating secret {secret_name}: {e}")
            return False
    
    def generate_secure_secret(self, length: int = 32) -> str:
        """Generate a cryptographically secure secret."""
        return secrets.token_urlsafe(length)
    
    def generate_fernet_key(self) -> str:
        """Generate a valid Fernet encryption key."""
        from cryptography.fernet import Fernet
        return Fernet.generate_key().decode('utf-8')
    
    def setup_required_secrets(self) -> bool:
        """Setup all required secrets for staging environment."""
        print(f"\n🔐 Setting up GSM secrets for {self.project_id}...")
        
        # Define all required secrets with their default values
        # IMPORTANT: Replace placeholder values with actual credentials
        required_secrets = {
            # Database configuration (for Cloud SQL)
            "postgres-host-staging": f"/cloudsql/{self.project_id}:us-central1:staging-shared-postgres",
            "postgres-port-staging": "5432",
            "postgres-db-staging": "netra_staging",
            "postgres-user-staging": "netra_user",
            "postgres-password-staging": self.generate_secure_secret(),  # Generate secure password
            
            # Authentication secrets
            "jwt-secret-staging": self.generate_secure_secret(64),  # Longer for JWT
            "secret-key-staging": self.generate_secure_secret(64),
            "service-secret-staging": self.generate_secure_secret(32),
            "service-id-staging": "staging-service-001",
            "fernet-key-staging": self.generate_fernet_key(),
            
            # Redis configuration (update with your Memorystore IP)
            "redis-host-staging": "10.0.0.100",  # REPLACE with actual Memorystore IP
            "redis-port-staging": "6379",
            "redis-password-staging": "",  # Leave empty if Redis doesn't require auth
            
            # OAuth (optional - update with your Google OAuth credentials)
            "google-oauth-client-id-staging": "YOUR_OAUTH_CLIENT_ID.apps.googleusercontent.com",
            "google-oauth-client-secret-staging": "YOUR_OAUTH_CLIENT_SECRET",
            "oauth-hmac-secret-staging": self.generate_secure_secret(32),
            
            # AI Services (optional - add your API keys)
            "openai-api-key-staging": "sk-YOUR_OPENAI_API_KEY",
            "anthropic-api-key-staging": "sk-ant-YOUR_ANTHROPIC_KEY",
            "gemini-api-key-staging": "YOUR_GEMINI_API_KEY",
            
            # Analytics (optional)
            "clickhouse-password-staging": "YOUR_CLICKHOUSE_PASSWORD"
        }
        
        created_count = 0
        existing_count = 0
        failed_count = 0
        
        for secret_name, default_value in required_secrets.items():
            if self.check_secret_exists(secret_name):
                print(f"   ✓ Secret already exists: {secret_name}")
                existing_count += 1
            else:
                # Check if this is a placeholder that needs updating
                if any(placeholder in default_value.upper() for placeholder in ["YOUR_", "REPLACE", "TODO"]):
                    print(f"   ⚠️ Secret needs configuration: {secret_name}")
                    print(f"      Please update with actual value")
                    # Create with placeholder for now
                    if self.create_secret(secret_name, default_value):
                        created_count += 1
                    else:
                        failed_count += 1
                else:
                    # Create with generated secure value
                    if self.create_secret(secret_name, default_value):
                        created_count += 1
                    else:
                        failed_count += 1
        
        print(f"\n📊 Secret Setup Summary:")
        print(f"   ✅ Already existing: {existing_count}")
        print(f"   ✅ Newly created: {created_count}")
        if failed_count > 0:
            print(f"   ❌ Failed to create: {failed_count}")
        
        # Save the generated values to a local file for reference (DO NOT COMMIT)
        if created_count > 0:
            config_file = f"staging_secrets_{self.project_id}.json"
            with open(config_file, 'w') as f:
                json.dump({
                    "project": self.project_id,
                    "secrets_created": created_count,
                    "note": "CRITICAL: Update placeholder values in GSM before deployment",
                    "required_updates": [
                        "redis-host-staging: Set to your Cloud Memorystore IP",
                        "postgres-password-staging: Ensure matches your Cloud SQL password",
                        "OAuth credentials: Add your Google OAuth client ID and secret",
                        "API keys: Add your OpenAI/Anthropic/Gemini keys if using AI features"
                    ]
                }, f, indent=2)
            print(f"\n💾 Configuration saved to {config_file}")
            print(f"   ⚠️ DO NOT commit this file to git!")
        
        return failed_count == 0
    
    def validate_critical_secrets(self) -> bool:
        """Validate that critical secrets have non-placeholder values."""
        print("\n🔍 Validating critical secrets...")
        
        critical_secrets = [
            "postgres-host-staging",
            "postgres-user-staging", 
            "postgres-password-staging",
            "postgres-db-staging",
            "jwt-secret-staging",
            "secret-key-staging",
            "service-secret-staging"
        ]
        
        all_valid = True
        for secret_name in critical_secrets:
            try:
                result = subprocess.run(
                    [self.gcloud_cmd, "secrets", "versions", "access", "latest",
                     "--secret", secret_name, "--project", self.project_id],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    value = result.stdout.strip()
                    # Check for placeholders
                    if any(placeholder in value.upper() for placeholder in ["YOUR_", "REPLACE", "TODO", "PLACEHOLDER"]):
                        print(f"   ⚠️ {secret_name}: Contains placeholder value")
                        all_valid = False
                    else:
                        print(f"   ✅ {secret_name}: Valid")
                else:
                    print(f"   ❌ {secret_name}: Not found")
                    all_valid = False
                    
            except Exception as e:
                print(f"   ❌ {secret_name}: Error accessing - {e}")
                all_valid = False
        
        return all_valid


def main():
    parser = argparse.ArgumentParser(description="Setup GSM secrets for staging environment")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing secrets")
    args = parser.parse_args()
    
    setup = StagingSecretSetup(args.project)
    
    if args.validate_only:
        if setup.validate_critical_secrets():
            print("\n✅ All critical secrets are properly configured")
            sys.exit(0)
        else:
            print("\n❌ Some critical secrets need configuration")
            print("\n📝 Next steps:")
            print("1. Update placeholder values in GSM")
            print("2. Run deployment: python scripts/deploy_to_gcp.py --project netra-staging --build-local")
            sys.exit(1)
    else:
        if setup.setup_required_secrets():
            print("\n✅ Secret setup completed successfully")
            
            if setup.validate_critical_secrets():
                print("\n🎉 Staging environment is ready for deployment!")
                print("\n📝 Next step:")
                print("   python scripts/deploy_to_gcp.py --project netra-staging --build-local")
            else:
                print("\n⚠️ Some secrets still need configuration")
                print("Please update placeholder values before deployment")
        else:
            print("\n❌ Secret setup failed")
            sys.exit(1)


if __name__ == "__main__":
    main()