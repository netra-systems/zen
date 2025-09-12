#!/usr/bin/env python3
"""Clean up duplicate/incorrect ClickHouse secrets from GCP Secret Manager.

This script removes all the duplicate ClickHouse secrets that were created
with incorrect naming conventions, keeping only the canonical staging secrets.
"""

import subprocess
import json
import sys
from typing import List, Set


def get_all_secrets(project_id: str) -> List[str]:
    """Get all secrets from GCP Secret Manager."""
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "list", f"--project={project_id}", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        secrets = json.loads(result.stdout)
        return [secret["name"].split("/")[-1] for secret in secrets]
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to list secrets: {e}")
        return []


def delete_secret(project_id: str, secret_name: str) -> bool:
    """Delete a secret from GCP Secret Manager."""
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "delete", secret_name, 
             f"--project={project_id}", "--quiet"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  [DELETED] {secret_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Failed to delete {secret_name}: {e}")
        return False


def main():
    """Main cleanup function."""
    project_id = "701982941522"  # Staging project ID
    
    print("=" * 60)
    print("ClickHouse Staging Secrets Cleanup")
    print("=" * 60)
    
    # Define the ONLY correct ClickHouse secrets for staging
    correct_secrets = {
        "clickhouse-password-staging",
        "clickhouse-host-staging",
        "clickhouse-port-staging",
        "clickhouse-user-staging",
        "clickhouse-db-staging",
    }
    
    # Define patterns for incorrect secrets to remove
    incorrect_patterns = [
        # Secrets without -staging suffix
        "clickhouse-host",
        "clickhouse-port",
        "clickhouse-user",
        "clickhouse-password",
        "clickhouse-database",
        "clickhouse-db",
        "clickhouse-secure",
        "clickhouse-url",
        
        # Native connection variants
        "clickhouse-native-host",
        "clickhouse-native-port",
        
        # HTTPS variants
        "clickhouse-https-url",
        "clickhouse-https-host",
        "clickhouse-https-port",
        
        # Uppercase variants
        "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_HOST",
        "CLICKHOUSE_PORT",
        "CLICKHOUSE_USER",
        "CLICKHOUSE_DB",
        "CLICKHOUSE_SECURE",
        
        # Any other clickhouse variants not in correct_secrets
    ]
    
    print("\n[INFO] Fetching all secrets from Secret Manager...")
    all_secrets = get_all_secrets(project_id)
    
    if not all_secrets:
        print(" FAIL:  Could not fetch secrets")
        return 1
    
    print(f"  Found {len(all_secrets)} total secrets")
    
    # Find ClickHouse-related secrets
    clickhouse_secrets = [s for s in all_secrets if "clickhouse" in s.lower()]
    print(f"\n[FOUND] {len(clickhouse_secrets)} ClickHouse-related secrets:")
    for secret in sorted(clickhouse_secrets):
        if secret in correct_secrets:
            print(f"  [KEEP] {secret} (correct staging secret)")
        else:
            print(f"  [DELETE] {secret} (duplicate/incorrect)")
    
    # Identify secrets to delete
    secrets_to_delete = []
    for secret in clickhouse_secrets:
        if secret not in correct_secrets:
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
    
    for secret in secrets_to_delete:
        if delete_secret(project_id, secret):
            deleted_count += 1
        else:
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
    remaining_secrets = get_all_secrets(project_id)
    remaining_clickhouse = [s for s in remaining_secrets if "clickhouse" in s.lower()]
    
    print(f"\n[REMAINING] ClickHouse secrets ({len(remaining_clickhouse)}):")
    for secret in sorted(remaining_clickhouse):
        if secret in correct_secrets:
            print(f"  [OK] {secret} (correct)")
        else:
            print(f"  [WARNING] {secret} (unexpected - may need manual review)")
    
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