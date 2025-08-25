#!/usr/bin/env python3
"""Update the PostgreSQL password secret using Google Cloud SDK."""

import sys
from google.cloud import secretmanager

def update_password_secret():
    """Update the postgres-password-staging secret with the correct password."""
    
    # The correct password from the staging database URL
    correct_password = "qNdlZRHu(Mlc#)6K8LHm-lYi[7sc}25K"
    secret_name = "postgres-password-staging"
    project = "netra-staging"
    
    print(f"Updating {secret_name} with the correct password...")
    
    try:
        # Create the Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        
        # Build the resource name of the secret
        parent = f"projects/{project}/secrets/{secret_name}"
        
        # Add a new version with the correct password
        response = client.add_secret_version(
            request={
                "parent": parent,
                "payload": {"data": correct_password.encode("UTF-8")},
            }
        )
        
        print(f"Successfully updated {secret_name}")
        print(f"Created version: {response.name}")
        return True
            
    except Exception as e:
        print(f"Error updating secret: {e}")
        return False

if __name__ == "__main__":
    success = update_password_secret()
    sys.exit(0 if success else 1)