#!/usr/bin/env python3
"""
Get numeric container ID for GTM
"""

import json
import sys
import os
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
                          'google-auth', 'google-api-python-client'])
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

def main():
    # Find credentials
    creds_path = 'gcp-staging-sa-key.json'
    if not Path(creds_path).exists():
        creds_path = str(Path.home() / '.config' / 'gcloud' / 'application_default_credentials.json')
    
    # Authenticate
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=['https://www.googleapis.com/auth/tagmanager.readonly']
    )
    
    service = build('tagmanager', 'v2', credentials=credentials)
    
    # Get container details
    account_id = "6310197060"
    public_id = "GTM-WKP28PNQ"
    
    # List containers
    containers = service.accounts().containers().list(
        parent=f"accounts/{account_id}"
    ).execute()
    
    for container in containers.get('container', []):
        if container.get('publicId') == public_id:
            numeric_id = container.get('containerId')
            print(f"Public ID: {public_id}")
            print(f"Numeric ID: {numeric_id}")
            print(f"Account ID: {account_id}")
            
            # Update config
            config_path = Path(__file__).parent / 'gtm_config.json'
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            config['numeric_container_id'] = numeric_id
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\nUpdated gtm_config.json with numeric_container_id: {numeric_id}")
            return numeric_id
    
    print(f"Container {public_id} not found")
    return None

if __name__ == "__main__":
    main()