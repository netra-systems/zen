#!/usr/bin/env python3
"""
Update staging secrets for GCP deployment.
This script updates critical secrets in GCP Secret Manager for staging environment.

Usage:
    python scripts/update_staging_secrets.py --check  # Check current values
    python scripts/update_staging_secrets.py --update # Update secrets
"""

import subprocess
import sys
import json
import argparse
from pathlib import Path


class StagingSecretsManager:
    """Manages staging secrets in GCP Secret Manager."""
    
    def __init__(self, project_id="netra-staging"):
        self.project_id = project_id
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        
    def check_secret(self, secret_name):
        """Check if a secret exists and get its current value."""
        try:
            # Check if secret exists
            cmd = [self.gcloud_cmd, "secrets", "describe", secret_name, 
                   f"--project={self.project_id}", "--format=json"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=(sys.platform == "win32"))
            
            if result.returncode != 0:
                return None, "Secret does not exist"
            
            # Get current value
            cmd = [self.gcloud_cmd, "secrets", "versions", "access", "latest",
                   f"--secret={secret_name}", f"--project={self.project_id}"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=(sys.platform == "win32"))
            
            if result.returncode == 0:
                value = result.stdout.strip()
                # Mask sensitive parts
                if "postgresql://" in value:
                    parts = value.split("@")
                    if len(parts) > 1:
                        masked = f"{parts[0].split(':')[0]}:****@{parts[1]}"
                        return value, masked
                return value, value[:50] + "..." if len(value) > 50 else value
            else:
                return None, "Failed to access secret value"
                
        except Exception as e:
            return None, str(e)
    
    def update_secret(self, secret_name, secret_value):
        """Update or create a secret in GCP Secret Manager."""
        try:
            # Check if secret exists
            exists, _ = self.check_secret(secret_name)
            
            if exists is None:
                # Create new secret
                print(f"Creating new secret: {secret_name}")
                cmd = [self.gcloud_cmd, "secrets", "create", secret_name,
                       "--data-file=-", f"--project={self.project_id}"]
            else:
                # Add new version to existing secret
                print(f"Updating existing secret: {secret_name}")
                cmd = [self.gcloud_cmd, "secrets", "versions", "add", secret_name,
                       "--data-file=-", f"--project={self.project_id}"]
            
            result = subprocess.run(cmd, input=secret_value, text=True, 
                                  capture_output=True, shell=(sys.platform == "win32"))
            
            if result.returncode == 0:
                print(f"[SUCCESS] Successfully updated {secret_name}")
                return True
            else:
                print(f"[FAILED] Failed to update {secret_name}: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error updating {secret_name}: {e}")
            return False
    
    def get_required_secrets(self):
        """Get the list of required secrets and their recommended values."""
        return {
            "postgres-host-staging": {
                "description": "PostgreSQL host (use /cloudsql/... for Cloud SQL)",
                "format": "/cloudsql/PROJECT:REGION:INSTANCE or hostname",
                "example": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
                "notes": "Use Unix socket path for Cloud SQL, or hostname for TCP connection"
            },
            "postgres-port-staging": {
                "description": "PostgreSQL port (omit for Unix socket)",
                "format": "Port number (5432 default)",
                "example": "5432",
                "notes": "Not needed when using Unix socket for Cloud SQL"
            },
            "postgres-db-staging": {
                "description": "PostgreSQL database name",
                "format": "Database name",
                "example": "netra_dev",
                "notes": "The database to connect to"
            },
            "postgres-user-staging": {
                "description": "PostgreSQL username",
                "format": "Username",
                "example": "postgres",
                "notes": "Database user for authentication"
            },
            "postgres-password-staging": {
                "description": "PostgreSQL password",
                "format": "Password string",
                "example": "DTprdt5KoQXlEG4Gh9lF",
                "notes": "Database password for authentication"
            },
            "clickhouse-url-staging": {
                "description": "ClickHouse HTTP endpoint URL",
                "format": "http://HOST:PORT or https://HOST:PORT",
                "example": "https://clickhouse.staging.netrasystems.ai:8443",
                "notes": "Leave empty to disable ClickHouse in staging"
            },
            "jwt-secret-key-staging": {
                "description": "JWT signing secret (64+ characters)",
                "format": "Random string of 64+ characters",
                "example": "Generate with: openssl rand -hex 32",
                "notes": "Must be the same for backend and auth services"
            },
            "jwt-secret-staging": {
                "description": "JWT secret for auth service",
                "format": "Same as jwt-secret-key-staging",
                "example": "Should match jwt-secret-key-staging",
                "notes": "Auth service uses this name"
            },
            "service-secret-staging": {
                "description": "Inter-service authentication secret",
                "format": "Random string of 32+ characters",
                "example": "Generate with: openssl rand -hex 16",
                "notes": "Used for service-to-service authentication"
            }
        }
    
    def check_all_secrets(self):
        """Check all required secrets."""
        print("\n=== Checking Staging Secrets ===\n")
        
        secrets = self.get_required_secrets()
        missing = []
        existing = []
        
        for secret_name, info in secrets.items():
            value, display = self.check_secret(secret_name)
            
            if value is None:
                missing.append(secret_name)
                print(f"[X] {secret_name}: NOT FOUND")
                print(f"  Description: {info['description']}")
                print(f"  Format: {info['format']}")
                print(f"  Example: {info['example']}")
            else:
                existing.append(secret_name)
                print(f"[OK] {secret_name}: {display}")
                
                # Check for common issues
                if secret_name == "database-url-staging":
                    if "localhost" in value:
                        print("  WARNING: Using localhost, should use Cloud SQL socket")
                    if "sslmode=" in value and "/cloudsql/" in value:
                        print("  WARNING: sslmode not needed for Unix socket connections")
                    if "postgres:6K8LHm" in value:
                        print("  WARNING: Using default password, may need to update")
                        
                elif secret_name in ["jwt-secret-key-staging", "jwt-secret-staging"]:
                    if len(value) < 64:
                        print(f"  WARNING: Secret too short ({len(value)} chars), should be 64+")
                        
                elif secret_name == "clickhouse-url-staging":
                    if not value or value == "":
                        print("  INFO: ClickHouse disabled (empty URL)")
            print()
        
        print(f"\nSummary: {len(existing)} existing, {len(missing)} missing")
        
        if missing:
            print("\nMissing secrets that need to be created:")
            for secret in missing:
                print(f"  - {secret}")
        
        return existing, missing
    
    def interactive_update(self):
        """Interactively update secrets."""
        print("\n=== Update Staging Secrets ===\n")
        
        secrets_to_update = {
            "postgres-host-staging": None,
            "postgres-port-staging": None,
            "postgres-db-staging": None,
            "postgres-user-staging": None,
            "postgres-password-staging": None,
            "jwt-secret-key-staging": None,
            "jwt-secret-staging": None,
            "service-secret-staging": None,
        }
        
        print("Enter new values for secrets (press Enter to skip):\n")
        
        for secret_name in secrets_to_update:
            current, display = self.check_secret(secret_name)
            info = self.get_required_secrets().get(secret_name, {})
            
            print(f"\n{secret_name}:")
            print(f"  Current: {display if current else 'NOT SET'}")
            print(f"  Format: {info.get('format', 'N/A')}")
            print(f"  Example: {info.get('example', 'N/A')}")
            
            new_value = input("  New value (or Enter to skip): ").strip()
            
            if new_value:
                secrets_to_update[secret_name] = new_value
        
        # Confirm updates
        updates = {k: v for k, v in secrets_to_update.items() if v}
        
        if not updates:
            print("\nNo updates to perform.")
            return
        
        print("\n=== Confirm Updates ===\n")
        for secret_name, value in updates.items():
            masked = value[:30] + "..." if len(value) > 30 else value
            print(f"  {secret_name}: {masked}")
        
        confirm = input("\nProceed with updates? (yes/no): ").lower()
        
        if confirm == "yes":
            print("\nUpdating secrets...")
            for secret_name, value in updates.items():
                self.update_secret(secret_name, value)
        else:
            print("\nUpdate cancelled.")


def main():
    parser = argparse.ArgumentParser(description="Manage staging secrets in GCP")
    parser.add_argument("--check", action="store_true", help="Check current secret values")
    parser.add_argument("--update", action="store_true", help="Update secrets interactively")
    parser.add_argument("--project", default="netra-staging", help="GCP project ID")
    
    args = parser.parse_args()
    
    if not args.check and not args.update:
        parser.print_help()
        print("\nPlease specify --check or --update")
        return 1
    
    manager = StagingSecretsManager(project_id=args.project)
    
    if args.check:
        manager.check_all_secrets()
    
    if args.update:
        manager.interactive_update()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())