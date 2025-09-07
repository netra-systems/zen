"""
WebSocket 403 Bug Fix - GCP Secret Manager Update

This script fixes the WebSocket authentication issue by ensuring the GCP Secret Manager
contains the correct JWT secret that matches what the tests and local environment expect.

CRITICAL FIX: Updates 'jwt-secret-staging' in GCP Secret Manager to match config/staging.env
This ensures WebSocket authentication works correctly in staging deployment.
"""

import subprocess
import sys
import os
from pathlib import Path

def get_expected_jwt_secret():
    """Get the expected JWT secret from config/staging.env"""
    config_path = Path(__file__).parent / "config" / "staging.env"
    
    if not config_path.exists():
        print(f"[X] config/staging.env not found at: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        for line in f:
            if line.startswith('JWT_SECRET_STAGING='):
                secret = line.split('=', 1)[1].strip()
                return secret
    
    print("[X] JWT_SECRET_STAGING not found in config/staging.env")
    return None


def check_gcp_secret(project_id, secret_name):
    """Check if a GCP secret exists and get its current value"""
    print(f"[INFO] Checking GCP secret: {secret_name}")
    
    # Check if secret exists
    result = subprocess.run([
        "gcloud", "secrets", "describe", secret_name,
        "--project", project_id
    ], capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        print(f"[INFO] Secret '{secret_name}' does not exist in project '{project_id}'")
        return None, False
    
    # Get current value
    result = subprocess.run([
        "gcloud", "secrets", "versions", "access", "latest",
        "--secret", secret_name, "--project", project_id
    ], capture_output=True, text=True, shell=True)
    
    if result.returncode == 0:
        current_value = result.stdout.strip()
        print(f"[INFO] Secret '{secret_name}' exists (length: {len(current_value)})")
        return current_value, True
    else:
        print(f"[INFO] Cannot access secret '{secret_name}': {result.stderr}")
        return None, True  # Exists but can't access


def create_gcp_secret(project_id, secret_name, secret_value):
    """Create a new GCP secret"""
    print(f"[INFO] Creating GCP secret: {secret_name}")
    
    # Create the secret
    result = subprocess.run([
        "gcloud", "secrets", "create", secret_name,
        "--project", project_id
    ], capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        print(f"[X] Failed to create secret: {result.stderr}")
        return False
    
    # Add the secret value
    result = subprocess.run([
        "gcloud", "secrets", "versions", "add", secret_name,
        "--data-file=-", "--project", project_id
    ], input=secret_value.encode(), capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        print(f"[X] Failed to add secret version: {result.stderr}")
        return False
    
    print(f"[OK] Created secret '{secret_name}' with correct value")
    return True


def update_gcp_secret(project_id, secret_name, secret_value):
    """Update an existing GCP secret with a new version"""
    print(f"[INFO] Updating GCP secret: {secret_name}")
    
    result = subprocess.run([
        "gcloud", "secrets", "versions", "add", secret_name,
        "--data-file=-", "--project", project_id
    ], input=secret_value.encode(), capture_output=True, text=True, shell=True)
    
    if result.returncode != 0:
        print(f"[X] Failed to update secret: {result.stderr}")
        return False
    
    print(f"[OK] Updated secret '{secret_name}' with correct value")
    return True


def fix_websocket_403_gcp_secret(project_id="netra-staging"):
    """
    Fix WebSocket 403 authentication by updating GCP Secret Manager
    """
    print("=" * 80)
    print("WEBSOCKET 403 BUG FIX - GCP Secret Manager Update")
    print("=" * 80)
    
    # Step 1: Get expected JWT secret
    print("\n[STEP 1] Getting expected JWT secret from config/staging.env...")
    expected_secret = get_expected_jwt_secret()
    if not expected_secret:
        print("[X] Cannot proceed without expected JWT secret")
        return False
    
    print(f"[OK] Expected JWT secret: {expected_secret[:20]}... (length: {len(expected_secret)})")
    
    # Step 2: Check current GCP secret
    print(f"\n[STEP 2] Checking current GCP secret in project '{project_id}'...")
    current_value, exists = check_gcp_secret(project_id, "jwt-secret-staging")
    
    # Step 3: Compare values and update if needed
    print("\n[STEP 3] Comparing and updating secret if needed...")
    
    if not exists:
        # Secret doesn't exist - create it
        print("[INFO] Secret doesn't exist, creating new secret...")
        success = create_gcp_secret(project_id, "jwt-secret-staging", expected_secret)
    elif current_value is None:
        # Secret exists but can't access - try to update anyway
        print("[INFO] Cannot access current secret value, updating anyway...")
        success = update_gcp_secret(project_id, "jwt-secret-staging", expected_secret)
    elif current_value != expected_secret:
        # Secret exists but has wrong value
        print(f"[INFO] Secret mismatch detected:")
        print(f"  Current: {current_value[:20]}... (length: {len(current_value)})")
        print(f"  Expected: {expected_secret[:20]}... (length: {len(expected_secret)})")
        print("[INFO] Updating secret with correct value...")
        success = update_gcp_secret(project_id, "jwt-secret-staging", expected_secret)
    else:
        # Secret is already correct
        print("[OK] GCP secret already has the correct value!")
        success = True
    
    # Step 4: Verify the fix
    if success:
        print("\n[STEP 4] Verifying the fix...")
        updated_value, _ = check_gcp_secret(project_id, "jwt-secret-staging")
        
        if updated_value == expected_secret:
            print("[OK] GCP secret now has the correct value!")
            print("\n[SOLUTION IMPLEMENTED]")
            print("The jwt-secret-staging secret in GCP Secret Manager has been updated")
            print("to match the value in config/staging.env.")
            print("")
            print("This fixes the WebSocket 403 authentication issue by ensuring:")
            print("1. Tests create JWT tokens with the same secret as staging deployment")
            print("2. Backend UserContextExtractor validates tokens with the same secret")
            print("3. Both JWT_SECRET_STAGING and JWT_SECRET_KEY get the same value")
            print("")
            print("Next steps:")
            print("1. Redeploy the staging backend to pick up the updated secret")
            print("2. Run staging WebSocket tests to verify the fix")
            return True
        else:
            print("[X] Verification failed - secret doesn't match expected value")
            return False
    else:
        print("\n[X] Failed to update GCP secret")
        return False


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        project_id = "netra-staging"
    
    print(f"Project ID: {project_id}")
    
    # Check if gcloud is available
    result = subprocess.run(["gcloud", "--version"], capture_output=True, shell=True)
    if result.returncode != 0:
        print("[X] gcloud CLI not found. Please install Google Cloud SDK.")
        sys.exit(1)
    
    # Run the fix
    success = fix_websocket_403_gcp_secret(project_id)
    
    if success:
        print("\n" + "=" * 80)
        print("[SUCCESS] WebSocket 403 authentication bug fix completed!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80) 
        print("[FAILED] WebSocket 403 authentication bug fix failed!")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()