#!/usr/bin/env python3
"""Update the PostgreSQL password secret to the correct value."""

import subprocess
import sys

def update_password_secret():
    """Update the postgres-password-staging secret with the correct password."""
    
    # The correct password from the staging database URL
    correct_password = "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"
    secret_name = "postgres-password-staging"
    project = "netra-staging"
    
    print(f"Updating {secret_name} with the correct password...")
    
    # First, delete the existing secret version if it exists
    try:
        # Create new version with correct password
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "add", secret_name,
             "--data-file=-", "--project", project],
            input=correct_password.encode(),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f" PASS:  Successfully updated {secret_name}")
            return True
        else:
            print(f" FAIL:  Failed to update {secret_name}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f" FAIL:  Error updating secret: {e}")
        return False

if __name__ == "__main__":
    success = update_password_secret()
    sys.exit(0 if success else 1)