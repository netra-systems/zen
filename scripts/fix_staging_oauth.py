#!/usr/bin/env python3
"""
Fix OAuth configuration for staging environment - Non-interactive version.
Automatically copies development OAuth credentials to staging configuration.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def fix_oauth_credentials():
    """Copy development OAuth credentials to staging configuration."""
    print("Fixing OAuth credentials for staging environment...")
    
    # Load development credentials
    dev_env = project_root / ".env"
    staging_env = project_root / ".env.staging"
    
    if not dev_env.exists():
        print("ERROR: .env file not found")
        return False
        
    if not staging_env.exists():
        print("ERROR: .env.staging file not found")
        return False
    
    # Read development credentials
    client_id = None
    client_secret = None
    
    with open(dev_env, 'r') as f:
        for line in f:
            if line.startswith("GOOGLE_CLIENT_ID="):
                client_id = line.split("=", 1)[1].strip()
            elif line.startswith("GOOGLE_CLIENT_SECRET="):
                client_secret = line.split("=", 1)[1].strip()
                
    if not client_id or not client_secret:
        print("ERROR: Could not find OAuth credentials in .env file")
        return False
        
    print(f"Found OAuth credentials:")
    print(f"  Client ID: {client_id[:20]}...")
    print(f"  Client Secret: {client_secret[:10]}...")
    
    # Update staging environment
    with open(staging_env, 'r') as f:
        lines = f.readlines()
    
    updated = False
    with open(staging_env, 'w') as f:
        for line in lines:
            if line.startswith("GOOGLE_CLIENT_ID="):
                f.write(f"GOOGLE_CLIENT_ID={client_id}\n")
                print("Updated GOOGLE_CLIENT_ID in .env.staging")
                updated = True
            elif line.startswith("GOOGLE_CLIENT_SECRET="):
                f.write(f"GOOGLE_CLIENT_SECRET={client_secret}\n")
                print("Updated GOOGLE_CLIENT_SECRET in .env.staging")
                updated = True
            else:
                f.write(line)
                
    if updated:
        print("\nSUCCESS: OAuth credentials updated in .env.staging")
        print("\nIMPORTANT: You must add these redirect URIs to Google Console:")
        print("  1. Go to: https://console.cloud.google.com/apis/credentials")
        print("  2. Select OAuth 2.0 Client ID:", client_id[:40])
        print("  3. Add these Authorized redirect URIs:")
        print("     - https://app.staging.netrasystems.ai/auth/callback")
        print("     - https://auth.staging.netrasystems.ai/auth/callback")
        print("     - https://api.staging.netrasystems.ai/auth/callback")
        print("     - http://localhost:3000/auth/callback (for local testing)")
        print("  4. Save the changes")
        return True
    else:
        print("ERROR: Failed to update .env.staging")
        return False


if __name__ == "__main__":
    success = fix_oauth_credentials()
    sys.exit(0 if success else 1)