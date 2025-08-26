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
        print("🔐 Setting up GCP Secret Manager client...")
        
        # Ensure authentication is set up
        if not GCPAuthConfig.ensure_authentication():
            print("❌ Failed to set up GCP authentication")
            return False
        
        try:
            self.client = secretmanager.SecretManagerServiceClient()
            print("✅ Secret Manager client initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to create Secret Manager client: {e}")
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
                print(f"  📝 Secret '{secret_id}' exists, will update")
            except Exception:
                secret_exists = False
                print(f"  ➕ Secret '{secret_id}' does not exist, will create")
            
            if not secret_exists:
                # Create the secret
                request = {
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}}
                }
                self.client.create_secret(request=request)
                print(f"  ✅ Created secret '{secret_id}'")
            
            # Add a new version with the value
            request = {
                "parent": secret_path,
                "payload": {"data": secret_value.encode("UTF-8")}
            }
            version = self.client.add_secret_version(request=request)
            print(f"  ✅ Updated secret '{secret_id}' with new value")
            
            # Destroy old versions to prevent confusion
            self._destroy_old_versions(secret_path, version.name)
            
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to update secret '{secret_id}': {e}")
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
                    print(f"    🗑️ Destroyed old version: {version.name.split('/')[-1]}")
                except Exception as e:
                    print(f"    ⚠️ Could not destroy version {version.name.split('/')[-1]}: {e}")
                    
        except Exception as e:
            print(f"  ⚠️ Could not cleanup old versions: {e}")
    
    def update_clickhouse_secrets(self) -> bool:
        """Update all ClickHouse-related secrets."""
        print("\n📦 Updating ClickHouse secrets for staging...")
        
        # Define the correct ClickHouse configuration
        clickhouse_secrets = {
            # Individual ClickHouse secrets
            "clickhouse-host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "clickhouse-port": "8443",
            "clickhouse-user": "default",
            "clickhouse-password": "6a_z1t0qQ1.ET",
            "clickhouse-database": "default",
            "clickhouse-secure": "true",
            
            # Native connection settings
            "clickhouse-native-host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "clickhouse-native-port": "9440",  # Native secure port
            
            # HTTPS connection settings
            "clickhouse-https-url": "https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443",
            "clickhouse-https-host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "clickhouse-https-port": "8443",
            
            # Composite URL for convenience
            "clickhouse-url": "clickhouse://default:6a_z1t0qQ1.ET@xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443/default?secure=true",
            
            # Alternative name mappings (for backward compatibility)
            "CLICKHOUSE_PASSWORD": "6a_z1t0qQ1.ET",
            "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "CLICKHOUSE_PORT": "8443",
            "CLICKHOUSE_USER": "default",
            "CLICKHOUSE_DB": "default",
            "CLICKHOUSE_SECURE": "true"
        }
        
        success = True
        updated_count = 0
        failed_count = 0
        
        for secret_id, secret_value in clickhouse_secrets.items():
            print(f"\n🔄 Updating secret: {secret_id}")
            if self.create_or_update_secret(secret_id, secret_value):
                updated_count += 1
            else:
                failed_count += 1
                success = False
        
        print(f"\n📊 Summary:")
        print(f"  ✅ Successfully updated: {updated_count} secrets")
        if failed_count > 0:
            print(f"  ❌ Failed to update: {failed_count} secrets")
        
        return success
    
    def verify_secrets(self) -> bool:
        """Verify that secrets were correctly updated."""
        print("\n🔍 Verifying ClickHouse secrets...")
        
        expected_values = {
            "clickhouse-host": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "clickhouse-password": "6a_z1t0qQ1.ET",
            "clickhouse-port": "8443",
            "clickhouse-user": "default",
            "clickhouse-database": "default"
        }
        
        all_correct = True
        
        for secret_id, expected_value in expected_values.items():
            try:
                secret_path = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
                response = self.client.access_secret_version(request={"name": secret_path})
                actual_value = response.payload.data.decode("UTF-8")
                
                if actual_value == expected_value:
                    print(f"  ✅ {secret_id}: Correct")
                else:
                    print(f"  ❌ {secret_id}: Incorrect (expected '{expected_value}', got '{actual_value}')")
                    all_correct = False
                    
            except Exception as e:
                print(f"  ❌ {secret_id}: Failed to verify - {e}")
                all_correct = False
        
        return all_correct
    
    def run(self) -> bool:
        """Main execution flow."""
        print("=" * 60)
        print("🚀 ClickHouse Staging Secrets Updater")
        print("=" * 60)
        
        # Setup client
        if not self.setup_client():
            return False
        
        # Update secrets
        if not self.update_clickhouse_secrets():
            print("\n❌ Some secrets failed to update")
            return False
        
        # Verify secrets
        if not self.verify_secrets():
            print("\n⚠️ Verification found issues")
            return False
        
        print("\n" + "=" * 60)
        print("✅ ClickHouse staging secrets successfully updated!")
        print("=" * 60)
        
        print("\n📝 Next steps:")
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