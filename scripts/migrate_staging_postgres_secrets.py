#!/usr/bin/env python3
"""
Migrate staging PostgreSQL secrets from URL format to individual variables.

This script creates/updates individual PostgreSQL secrets in GCP Secret Manager
for staging environment to use individual variables instead of DATABASE_URL.

Usage:
    python scripts/migrate_staging_postgres_secrets.py
"""

import subprocess
import sys
import json
from pathlib import Path


class PostgreSQLSecretsMigrator:
    """Migrates PostgreSQL secrets to individual variables in GCP."""
    
    def __init__(self, project_id="netra-staging"):
        self.project_id = project_id
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        
    def create_or_update_secret(self, secret_name, secret_value):
        """Create or update a secret in GCP Secret Manager."""
        try:
            # Check if secret exists
            cmd = [self.gcloud_cmd, "secrets", "describe", secret_name, 
                   f"--project={self.project_id}", "--format=json"]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=(sys.platform == "win32"))
            
            if result.returncode != 0:
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
                print(f"[SUCCESS] {secret_name}")
                return True
            else:
                print(f"[FAILED] {secret_name}: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] {secret_name}: {e}")
            return False
    
    def migrate_postgres_secrets(self):
        """Migrate PostgreSQL configuration to individual secrets."""
        print("\n=== Migrating PostgreSQL Secrets to Individual Variables ===\n")
        
        # Define the staging PostgreSQL configuration
        postgres_secrets = {
            "postgres-host-staging": "/cloudsql/netra-staging:us-central1:staging-shared-postgres",
            "postgres-port-staging": "5432",
            "postgres-db-staging": "netra_dev",
            "postgres-user-staging": "postgres",
            "postgres-password-staging": "DTprdt5KoQXlEG4Gh9lF"
        }
        
        print("Creating/updating the following PostgreSQL secrets:")
        for name, value in postgres_secrets.items():
            if "password" in name:
                print(f"  {name}: ***")
            else:
                print(f"  {name}: {value}")
        
        confirm = input("\nProceed with migration? (yes/no): ").lower()
        
        if confirm != "yes":
            print("Migration cancelled.")
            return
        
        print("\nMigrating secrets...")
        success_count = 0
        fail_count = 0
        
        for secret_name, secret_value in postgres_secrets.items():
            if self.create_or_update_secret(secret_name, secret_value):
                success_count += 1
            else:
                fail_count += 1
        
        print(f"\n=== Migration Complete ===")
        print(f"Success: {success_count}")
        print(f"Failed: {fail_count}")
        
        if fail_count == 0:
            print("\nAll PostgreSQL secrets successfully migrated!")
            print("\nThe system will now construct PostgreSQL URLs from these individual variables:")
            print("  - For async connections: postgresql+asyncpg://...")
            print("  - For sync connections: postgresql://...")
            print("  - Cloud SQL Unix socket connections will be properly formatted")
        else:
            print(f"\nWarning: {fail_count} secrets failed to migrate. Please check the errors above.")
        
        return fail_count == 0


def main():
    """Main entry point."""
    migrator = PostgreSQLSecretsMigrator()
    
    print("PostgreSQL Secrets Migration Tool")
    print("==================================")
    print("\nThis tool will create/update individual PostgreSQL secrets in GCP")
    print("to replace the monolithic #removed-legacywith individual variables.")
    print("\nTarget project: netra-staging")
    
    if migrator.migrate_postgres_secrets():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())