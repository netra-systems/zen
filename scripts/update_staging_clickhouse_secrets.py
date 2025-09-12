"""Update staging ClickHouse secrets in GCP Secret Manager.

This script updates the staging ClickHouse configuration to use the correct
values instead of placeholders or incorrect references.

Correct ClickHouse configuration for staging:
- Host (HTTPS): https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud
- Host (Native): xedvrr4c3r.us-central1.gcp.clickhouse.cloud
- Port: 8443 (HTTPS)
- User: default
- Password: 6a_z1t0qQ1.ET
- Database: default
- Secure: True
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from google.cloud import secretmanager
from gcp_auth_config import GCPAuthConfig


class StagingClickHouseSecretsUpdater:
    """Updates ClickHouse secrets in staging GCP Secret Manager."""
    
    def __init__(self):
        """Initialize the secrets updater."""
        self.project_id = "701982941522"  # Staging project ID
        self.client = None
        
    def setup_client(self) -> bool:
        """Setup GCP Secret Manager client."""
        print("[U+1F510] Setting up GCP Secret Manager client...")
        
        # Ensure authentication is set up
        if not GCPAuthConfig.ensure_authentication():
            print(" FAIL:  Failed to set up GCP authentication")
            return False
        
        try:
            self.client = secretmanager.SecretManagerServiceClient()
            print(" PASS:  Secret Manager client initialized")
            return True
        except Exception as e:
            print(f" FAIL:  Failed to create Secret Manager client: {e}")
            return False
    
    def create_or_update_secret(self, secret_id: str, secret_value: str) -> bool:
        """Create or update a secret in Secret Manager."""
        parent = f"projects/{self.project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"
        
        try:
            # Check if secret exists
            try:
                self.client.get_secret(request={"name": secret_path})
                secret_exists = True
                print(f"  [U+1F4DD] Secret '{secret_id}' exists, will update")
            except Exception:
                secret_exists = False
                print(f"  [U+2795] Secret '{secret_id}' does not exist, will create")
            
            if not secret_exists:
                # Create the secret
                request = {
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}}
                }
                self.client.create_secret(request=request)
                print(f"   PASS:  Created secret '{secret_id}'")
            
            # Add a new version with the value
            request = {
                "parent": secret_path,
                "payload": {"data": secret_value.encode("UTF-8")}
            }
            version = self.client.add_secret_version(request=request)
            print(f"   PASS:  Updated secret '{secret_id}' with new value")
            
            # Destroy old versions to prevent confusion
            self._destroy_old_versions(secret_path, version.name)
            
            return True
            
        except Exception as e:
            print(f"   FAIL:  Failed to update secret '{secret_id}': {e}")
            return False
    
    def _destroy_old_versions(self, secret_path: str, current_version_name: str) -> None:
        """Destroy old versions of a secret."""
        try:
            # List all versions
            versions = self.client.list_secret_versions(request={"parent": secret_path})
            
            for version in versions:
                # Skip current version and already destroyed versions
                if version.name == current_version_name or version.state != secretmanager.SecretVersion.State.ENABLED:
                    continue
                
                # Destroy old version
                try:
                    self.client.destroy_secret_version(request={"name": version.name})
                    print(f"    [U+1F5D1][U+FE0F] Destroyed old version: {version.name.split('/')[-1]}")
                except Exception as e:
                    print(f"     WARNING: [U+FE0F] Could not destroy version {version.name.split('/')[-1]}: {e}")
                    
        except Exception as e:
            print(f"   WARNING: [U+FE0F] Could not cleanup old versions: {e}")
    
    def update_clickhouse_secrets(self) -> bool:
        """Update all ClickHouse-related secrets."""
        print("\n[U+1F4E6] Updating ClickHouse secrets for staging...")
        
        # Define the correct ClickHouse configuration
        # Using only the canonical staging secret names as defined in secret_mappings.py
        clickhouse_secrets = {
            "clickhouse-password-staging": "6a_z1t0qQ1.ET",
            "clickhouse-host-staging": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "clickhouse-port-staging": "8443",
            "clickhouse-user-staging": "default",
            "clickhouse-db-staging": "default",
        }
        
        success = True
        updated_count = 0
        failed_count = 0
        
        for secret_id, secret_value in clickhouse_secrets.items():
            print(f"\n CYCLE:  Updating secret: {secret_id}")
            if self.create_or_update_secret(secret_id, secret_value):
                updated_count += 1
            else:
                failed_count += 1
                success = False
        
        print(f"\n CHART:  Summary:")
        print(f"   PASS:  Successfully updated: {updated_count} secrets")
        if failed_count > 0:
            print(f"   FAIL:  Failed to update: {failed_count} secrets")
        
        return success
    
    def verify_secrets(self) -> bool:
        """Verify that secrets were correctly updated."""
        print("\n SEARCH:  Verifying ClickHouse secrets...")
        
        expected_values = {
            "clickhouse-host-staging": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "clickhouse-password-staging": "6a_z1t0qQ1.ET",
            "clickhouse-port-staging": "8443",
            "clickhouse-user-staging": "default",
            "clickhouse-db-staging": "default"
        }
        
        all_correct = True
        
        for secret_id, expected_value in expected_values.items():
            try:
                secret_path = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
                response = self.client.access_secret_version(request={"name": secret_path})
                actual_value = response.payload.data.decode("UTF-8")
                
                if actual_value == expected_value:
                    print(f"   PASS:  {secret_id}: Correct")
                else:
                    print(f"   FAIL:  {secret_id}: Incorrect (expected '{expected_value}', got '{actual_value}')")
                    all_correct = False
                    
            except Exception as e:
                print(f"   FAIL:  {secret_id}: Failed to verify - {e}")
                all_correct = False
        
        return all_correct
    
    def run(self) -> bool:
        """Main execution flow."""
        print("=" * 60)
        print("[U+1F680] ClickHouse Staging Secrets Updater")
        print("=" * 60)
        
        # Setup client
        if not self.setup_client():
            return False
        
        # Update secrets
        if not self.update_clickhouse_secrets():
            print("\n FAIL:  Some secrets failed to update")
            return False
        
        # Verify secrets
        if not self.verify_secrets():
            print("\n WARNING: [U+FE0F] Verification found issues")
            return False
        
        print("\n" + "=" * 60)
        print(" PASS:  ClickHouse staging secrets successfully updated!")
        print("=" * 60)
        
        print("\n[U+1F4DD] Next steps:")
        print("1. Restart staging services to pick up new secrets")
        print("2. Test ClickHouse connectivity with: python scripts/test_staging_clickhouse.py")
        print("3. Monitor staging logs for any connection issues")
        
        return True


def main():
    """Main entry point."""
    updater = StagingClickHouseSecretsUpdater()
    success = updater.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()