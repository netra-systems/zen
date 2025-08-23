#!/usr/bin/env python3
"""
Complete Staging Secrets Creation Script
Creates all required secrets for staging deployment with proper values.
"""

import subprocess
import sys
import os
from typing import Dict, Optional


class StagingSecretsCreator:
    """Creates all required staging secrets."""
    
    def __init__(self, project_id: str = "netra-staging"):
        self.project_id = project_id
        
    def create_all_secrets(self) -> bool:
        """Create all required staging secrets."""
        print("🔐 CREATING STAGING SECRETS")
        print("=" * 50)
        
        # Generate secure values
        secrets = self._generate_secret_values()
        
        success = True
        for secret_name, secret_value in secrets.items():
            print(f"\n📝 Creating secret: {secret_name}")
            
            if not self._create_secret(secret_name, secret_value):
                success = False
                
        if success:
            print("\n✅ ALL SECRETS CREATED SUCCESSFULLY")
            print("\n🚀 Ready for deployment:")
            print(f"python scripts/deploy_to_gcp.py --project {self.project_id} --build-local --run-checks")
        else:
            print("\n❌ SOME SECRETS FAILED TO CREATE")
            print("Check the errors above and retry")
            
        return success
        
    def _generate_secret_values(self) -> Dict[str, str]:
        """Generate secure values for all secrets."""
        # Generate secure random values
        jwt_secret = self._generate_secure_key(32)
        session_secret = self._generate_secure_key(32)
        fernet_key = self._generate_fernet_key()
        
        # IMPORTANT: These need to be replaced with real values
        secrets = {
            "database-url-staging": "postgresql://netra_user:REPLACE_WITH_REAL_DB_PASSWORD@34.132.142.103:5432/netra?sslmode=require",
            "jwt-secret-key-staging": jwt_secret,
            "session-secret-key-staging": session_secret,
            "fernet-key-staging": fernet_key,
            "openai-api-key-staging": "sk-REPLACE_WITH_REAL_OPENAI_API_KEY_FOR_STAGING",
            "jwt-secret-staging": jwt_secret  # Auth service uses same JWT key
        }
        
        return secrets
        
    def _generate_secure_key(self, length: int = 32) -> str:
        """Generate a secure random key."""
        try:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        except ImportError:
            # Fallback using os.urandom
            import base64
            return base64.b64encode(os.urandom(length)).decode()[:length]
            
    def _generate_fernet_key(self) -> str:
        """Generate a Fernet encryption key."""
        try:
            from cryptography.fernet import Fernet
            return Fernet.generate_key().decode()
        except ImportError:
            print("⚠️ cryptography not installed, using base64 key")
            import base64
            return base64.urlsafe_b64encode(os.urandom(32)).decode()
            
    def _create_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create a single secret in Secret Manager."""
        try:
            # Check if secret already exists
            result = subprocess.run(
                ["gcloud", "secrets", "describe", secret_name, "--project", self.project_id],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode == 0:
                print(f"  ⚠️ Secret {secret_name} already exists, adding new version...")
                cmd = [
                    "gcloud", "secrets", "versions", "add", secret_name,
                    "--data-file=-", "--project", self.project_id
                ]
            else:
                print(f"  🆕 Creating new secret {secret_name}...")
                # Create the secret first
                create_result = subprocess.run(
                    ["gcloud", "secrets", "create", secret_name, "--project", self.project_id],
                    capture_output=True, text=True, check=False
                )
                
                if create_result.returncode != 0:
                    print(f"  ❌ Failed to create secret: {create_result.stderr}")
                    return False
                    
                cmd = [
                    "gcloud", "secrets", "versions", "add", secret_name,
                    "--data-file=-", "--project", self.project_id
                ]
            
            # Add the secret value
            result = subprocess.run(
                cmd, input=secret_value.encode(), capture_output=True, text=True, check=False
            )
            
            if result.returncode == 0:
                print(f"  ✅ Secret {secret_name} created/updated successfully")
                return True
            else:
                print(f"  ❌ Failed to add secret value: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"  ❌ Error creating secret {secret_name}: {e}")
            return False
            
    def validate_secrets(self) -> bool:
        """Validate that all secrets were created successfully."""
        print("\n🔍 VALIDATING CREATED SECRETS")
        print("=" * 30)
        
        required_secrets = [
            "database-url-staging",
            "jwt-secret-key-staging", 
            "session-secret-key-staging",
            "fernet-key-staging",
            "openai-api-key-staging",
            "jwt-secret-staging"
        ]
        
        all_exist = True
        for secret in required_secrets:
            try:
                result = subprocess.run(
                    ["gcloud", "secrets", "describe", secret, "--project", self.project_id],
                    capture_output=True, text=True, check=False
                )
                
                if result.returncode == 0:
                    print(f"✅ {secret}")
                else:
                    print(f"❌ {secret} (missing)")
                    all_exist = False
                    
            except Exception as e:
                print(f"❌ {secret} (error: {e})")
                all_exist = False
                
        return all_exist
        
    def print_manual_fixes_needed(self):
        """Print what needs to be manually fixed."""
        print("\n🔧 MANUAL FIXES REQUIRED")
        print("=" * 30)
        print("1. Replace database password:")
        print("   gcloud secrets versions add database-url-staging --data-file=- --project=netra-staging")
        print("   Input: postgresql://netra_user:REAL_PASSWORD@34.132.142.103:5432/netra?sslmode=require")
        print()
        print("2. Replace OpenAI API key:")
        print("   gcloud secrets versions add openai-api-key-staging --data-file=- --project=netra-staging")  
        print("   Input: sk-YOUR_REAL_OPENAI_API_KEY")
        print()
        print("3. Optional: Add Google OAuth credentials (if needed):")
        print("   gcloud secrets create google-client-id-staging --data-file=- --project=netra-staging")
        print("   gcloud secrets create google-client-secret-staging --data-file=- --project=netra-staging")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create all staging secrets")
    parser.add_argument("--project", default="netra-staging", help="GCP Project ID")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing secrets")
    args = parser.parse_args()
    
    creator = StagingSecretsCreator(args.project)
    
    if args.validate_only:
        success = creator.validate_secrets()
    else:
        success = creator.create_all_secrets()
        if success:
            creator.validate_secrets()
            
        creator.print_manual_fixes_needed()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()