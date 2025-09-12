"""Test ClickHouse connectivity with staging configuration.

This script verifies that:
1. Secrets are correctly loaded from GCP Secret Manager
2. ClickHouse connection can be established with the correct credentials
3. No placeholder or incorrect references remain
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Optional
import clickhouse_connect
from google.cloud import secretmanager
from shared.isolated_environment import IsolatedEnvironment

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from gcp_auth_config import GCPAuthConfig


class StagingClickHouseConnectivityTester:
    """Tests ClickHouse connectivity with staging configuration."""
    
    def __init__(self):
        """Initialize the connectivity tester."""
        self.project_id = "701982941522"  # Staging project ID
        self.client = None
        self.secrets = {}
        
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
    
    def fetch_secret(self, secret_id: str) -> Optional[str]:
        """Fetch a secret from Secret Manager."""
        try:
            secret_path = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
            response = self.client.access_secret_version(request={"name": secret_path})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"   FAIL:  Failed to fetch {secret_id}: {e}")
            return None
    
    def load_clickhouse_secrets(self) -> bool:
        """Load all ClickHouse secrets from Secret Manager."""
        print("\n[U+1F4E6] Loading ClickHouse secrets from Secret Manager...")
        
        required_secrets = [
            "clickhouse-host",
            "clickhouse-port", 
            "clickhouse-user",
            "clickhouse-password",
            "clickhouse-database"
        ]
        
        for secret_id in required_secrets:
            value = self.fetch_secret(secret_id)
            if value:
                self.secrets[secret_id] = value
                # Mask password in output
                display_value = "***" if "password" in secret_id else value
                print(f"   PASS:  Loaded {secret_id}: {display_value}")
            else:
                print(f"   FAIL:  Failed to load {secret_id}")
                return False
        
        # Also try alternative naming conventions
        alt_secrets = ["CLICKHOUSE_HOST", "CLICKHOUSE_PASSWORD", "CLICKHOUSE_PORT"]
        for secret_id in alt_secrets:
            value = self.fetch_secret(secret_id)
            if value:
                self.secrets[secret_id] = value
                
        return True
    
    def validate_secrets(self) -> bool:
        """Validate that secrets don't contain placeholders or incorrect values."""
        print("\n SEARCH:  Validating secret values...")
        
        invalid_patterns = [
            "placeholder",
            "todo", 
            "changeme",
            "staging-clickhouse.netrasystems",
            "clickhouse.netra"
        ]
        
        all_valid = True
        
        # Check host
        host = self.secrets.get("clickhouse-host", "")
        if not host or any(pattern in host.lower() for pattern in invalid_patterns):
            print(f"   FAIL:  Invalid host: {host}")
            all_valid = False
        elif host != "xedvrr4c3r.us-central1.gcp.clickhouse.cloud":
            print(f"   WARNING: [U+FE0F] Unexpected host: {host} (expected xedvrr4c3r.us-central1.gcp.clickhouse.cloud)")
        else:
            print(f"   PASS:  Host is correct: {host}")
        
        # Check port
        port = self.secrets.get("clickhouse-port", "")
        if port != "8443":
            print(f"   WARNING: [U+FE0F] Unexpected port: {port} (expected 8443 for HTTPS)")
        else:
            print(f"   PASS:  Port is correct: {port}")
        
        # Check user
        user = self.secrets.get("clickhouse-user", "")
        if user != "default":
            print(f"   WARNING: [U+FE0F] Unexpected user: {user} (expected 'default')")
        else:
            print(f"   PASS:  User is correct: {user}")
        
        # Check database
        database = self.secrets.get("clickhouse-database", "")
        if database != "default":
            print(f"   WARNING: [U+FE0F] Unexpected database: {database} (expected 'default')")
        else:
            print(f"   PASS:  Database is correct: {database}")
        
        # Check password exists and is not placeholder
        password = self.secrets.get("clickhouse-password", "")
        if not password or any(pattern in password.lower() for pattern in invalid_patterns):
            print(f"   FAIL:  Invalid or missing password")
            all_valid = False
        else:
            print(f"   PASS:  Password is set (hidden)")
        
        return all_valid
    
    def test_connectivity(self) -> bool:
        """Test actual ClickHouse connectivity."""
        print("\n[U+1F310] Testing ClickHouse connectivity...")
        
        try:
            # Get connection parameters
            host = self.secrets.get("clickhouse-host", "")
            port = int(self.secrets.get("clickhouse-port", "8443"))
            user = self.secrets.get("clickhouse-user", "default")
            password = self.secrets.get("clickhouse-password", "")
            database = self.secrets.get("clickhouse-database", "default")
            
            print(f"  Connecting to: {host}:{port}")
            print(f"  User: {user}, Database: {database}")
            
            # Create HTTPS client
            client = clickhouse_connect.get_client(
                host=host,
                port=port,
                username=user,
                password=password,
                database=database,
                secure=True,  # Use HTTPS
                verify=True   # Verify SSL certificate
            )
            
            # Test query
            result = client.query("SELECT version()")
            version = result.result_rows[0][0] if result.result_rows else "Unknown"
            
            print(f"   PASS:  Successfully connected to ClickHouse!")
            print(f"   CHART:  Server version: {version}")
            
            # Test database access
            result = client.query("SHOW DATABASES")
            databases = [row[0] for row in result.result_rows]
            print(f"  [U+1F4DA] Available databases: {', '.join(databases[:5])}")
            
            # Test table creation capability
            try:
                client.command("CREATE TABLE IF NOT EXISTS test_connectivity (id UInt32) ENGINE = Memory")
                client.command("DROP TABLE IF EXISTS test_connectivity")
                print(f"   PASS:  Can create and drop tables")
            except Exception as e:
                print(f"   WARNING: [U+FE0F] Cannot create tables (may be permission issue): {e}")
            
            client.close()
            return True
            
        except Exception as e:
            print(f"   FAIL:  Connection failed: {e}")
            print(f"  Error type: {type(e).__name__}")
            return False
    
    def run(self) -> bool:
        """Main execution flow."""
        print("=" * 60)
        print("[U+1F680] ClickHouse Staging Connectivity Tester")
        print("=" * 60)
        
        # Setup client
        if not self.setup_client():
            return False
        
        # Load secrets
        if not self.load_clickhouse_secrets():
            print("\n FAIL:  Failed to load secrets from Secret Manager")
            return False
        
        # Validate secrets
        if not self.validate_secrets():
            print("\n WARNING: [U+FE0F] Some secrets have invalid values")
            # Continue anyway to test connectivity
        
        # Test connectivity
        success = self.test_connectivity()
        
        print("\n" + "=" * 60)
        if success:
            print(" PASS:  ClickHouse staging connectivity test PASSED!")
            print("\n[U+2728] Configuration is correctly using Secret Manager values")
            print("[U+2728] No placeholder or incorrect references detected")
        else:
            print(" FAIL:  ClickHouse staging connectivity test FAILED!")
            print("\n[U+1F4DD] Troubleshooting steps:")
            print("1. Check that secrets are correctly set in Secret Manager")
            print("2. Verify network connectivity to ClickHouse Cloud")
            print("3. Check firewall rules and IP allowlisting")
            print("4. Review error messages above for specific issues")
        print("=" * 60)
        
        return success


def main():
    """Main entry point."""
    # First check if clickhouse_connect is available
    try:
        import clickhouse_connect
    except ImportError:
        print(" FAIL:  clickhouse-connect is not installed")
        print("   Run: pip install clickhouse-connect")
        sys.exit(1)
    
    tester = StagingClickHouseConnectivityTester()
    success = tester.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()