from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""Clean up duplicate/incorrect ClickHouse secrets from GCP Secret Manager using SDK.

This script removes all the duplicate ClickHouse secrets that were created
with incorrect naming conventions, keeping only the canonical staging secrets.
"""

import sys
import os
from pathlib import Path
from typing import List, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from google.cloud import secretmanager
    from google.api_core import exceptions
except ImportError:
    print("[ERROR] google-cloud-secret-manager not installed")
    print("Run: pip install google-cloud-secret-manager")
    sys.exit(1)


def setup_auth():
    """Setup GCP authentication."""
    # Try to find service account key
    key_paths = [
        Path.home() / ".config/gcloud/application_default_credentials.json",
        Path.home() / "gcp-key.json",
        Path("netra-staging-key.json"),
    ]
    
    for key_path in key_paths:
        if key_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)
            print(f"[AUTH] Using credentials from: {key_path}")
            return True
    
    # Try default auth
    print("[AUTH] Using default GCP authentication")
    return True


def main():
    """Main cleanup function."""
    project_id = "701982941522"  # Staging project ID
    
    print("=" * 60)
    print("ClickHouse Staging Secrets Cleanup (SDK Version)")
    print("=" * 60)
    
    # Setup authentication
    if not setup_auth():
        print("[ERROR] Failed to setup authentication")
        return 1
    
    # Initialize client
    try:
        client = secretmanager.SecretManagerServiceClient()
        print("[OK] Secret Manager client initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize client: {e}")
        return 1
    
    # Define the ONLY correct ClickHouse secrets for staging
    correct_secrets = {
        "clickhouse-password-staging",
        "clickhouse-host-staging",
        "clickhouse-port-staging",
        "clickhouse-user-staging",
        "clickhouse-db-staging",
    }
    
    # List all secrets
    print("\n[INFO] Fetching all secrets from Secret Manager...")
    parent = f"projects/{project_id}"
    
    try:
        all_secrets = []
        request = secretmanager.ListSecretsRequest(parent=parent)
        page_result = client.list_secrets(request=request)
        
        for secret in page_result:
            secret_name = secret.name.split("/")[-1]
            all_secrets.append(secret_name)
        
        print(f"  Found {len(all_secrets)} total secrets")
    except Exception as e:
        print(f"[ERROR] Failed to list secrets: {e}")
        return 1
    
    # Find ClickHouse-related secrets
    clickhouse_secrets = [s for s in all_secrets if "clickhouse" in s.lower()]
    print(f"\n[FOUND] {len(clickhouse_secrets)} ClickHouse-related secrets:")
    
    secrets_to_delete = []
    for secret in sorted(clickhouse_secrets):
        if secret in correct_secrets:
            print(f"  [KEEP] {secret} (correct staging secret)")
        else:
            print(f"  [DELETE] {secret} (duplicate/incorrect)")
            secrets_to_delete.append(secret)
    
    if not secrets_to_delete:
        print("\n[OK] No duplicate secrets to delete!")
        return 0
    
    print(f"\n[WARNING] Preparing to delete {len(secrets_to_delete)} duplicate/incorrect secrets:")
    for secret in sorted(secrets_to_delete):
        print(f"  - {secret}")
    
    # Confirm deletion
    print("\n[WARNING] This will permanently delete the above secrets!")
    response = input("Continue with deletion? (yes/no): ")
    
    if response.lower() != "yes":
        print("[CANCELLED] Deletion cancelled")
        return 1
    
    # Delete the secrets
    print("\n[DELETING] Deleting duplicate secrets...")
    deleted_count = 0
    failed_count = 0
    
    for secret_name in secrets_to_delete:
        try:
            secret_path = f"{parent}/secrets/{secret_name}"
            request = secretmanager.DeleteSecretRequest(name=secret_path)
            client.delete_secret(request=request)
            print(f"  [DELETED] {secret_name}")
            deleted_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to delete {secret_name}: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Cleanup Summary:")
    print(f"  [DELETED]: {deleted_count} secrets")
    if failed_count > 0:
        print(f"  [FAILED]: {failed_count} secrets")
    print(f"  [REMAINING]: {len(correct_secrets)} correct secrets")
    print("=" * 60)
    
    # Verify remaining secrets
    print("\n[VERIFY] Verifying remaining ClickHouse secrets...")
    try:
        request = secretmanager.ListSecretsRequest(parent=parent)
        page_result = client.list_secrets(request=request)
        
        remaining_clickhouse = []
        for secret in page_result:
            secret_name = secret.name.split("/")[-1]
            if "clickhouse" in secret_name.lower():
                remaining_clickhouse.append(secret_name)
        
        print(f"\n[REMAINING] ClickHouse secrets ({len(remaining_clickhouse)}):")
        for secret in sorted(remaining_clickhouse):
            if secret in correct_secrets:
                print(f"  [OK] {secret} (correct)")
            else:
                print(f"  [WARNING] {secret} (unexpected - may need manual review)")
    except Exception as e:
        print(f"[ERROR] Failed to verify remaining secrets: {e}")
    
    if failed_count > 0:
        print("\n[ERROR] Some deletions failed - manual intervention may be required")
        return 1
    
    print("\n[SUCCESS] Cleanup completed successfully!")
    print("\nNext steps:")
    print("1. Run: python scripts/update_staging_clickhouse_secrets.py")
    print("2. To ensure the correct secrets have the right values")
    print("3. Restart staging services to pick up the cleaned configuration")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
