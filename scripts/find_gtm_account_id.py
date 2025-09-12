from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Find GTM Account ID
Helper script to find your Google Tag Manager Account ID
"""

import json
import sys
import os
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 
                          'google-auth', 'google-auth-oauthlib', 
                          'google-auth-httplib2', 'google-api-python-client'])
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

def find_service_account_key():
    """Find service account key file"""
    possible_paths = [
        'netra-staging-sa-key.json',
        'secrets/netra-staging-sa-key.json',
        '../secrets/netra-staging-sa-key.json',
    ]
    
    env_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if env_path:
        possible_paths.insert(0, env_path)
    
    for path in possible_paths:
        if Path(path).exists():
            return str(Path(path).absolute())
    
    return None

def find_account_id(container_id='GTM-WKP28PNQ'):
    """Find account ID for a given container ID"""
    
    # Find credentials
    creds_path = find_service_account_key()
    if not creds_path:
        print("Service account key not found!")
        print("\nPlease ensure netra-staging-sa-key.json is in one of these locations:")
        print("  - Current directory")
        print("  - secrets/ directory")
        print("  - Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
        return None
    
    print(f"Using credentials: {creds_path}")
    
    try:
        # Authenticate
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/tagmanager.readonly']
        )
        
        service = build('tagmanager', 'v2', credentials=credentials)
        
        # List all accounts
        print("\nSearching for GTM accounts...")
        accounts_response = service.accounts().list().execute()
        
        if 'account' not in accounts_response:
            print("No GTM accounts found for this service account!")
            print("\nMake sure the service account has access to your GTM account:")
            print("1. Go to Google Tag Manager")
            print("2. Admin > User Management")
            print("3. Add: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
            return None
        
        # Search for container in each account
        for account in accounts_response['account']:
            account_id = account['accountId']
            account_name = account.get('name', 'Unknown')
            
            print(f"\nChecking account: {account_name} (ID: {account_id})")
            
            # List containers in this account
            containers_response = service.accounts().containers().list(
                parent=f"accounts/{account_id}"
            ).execute()
            
            if 'container' in containers_response:
                for container in containers_response['container']:
                    container_public_id = container.get('publicId', '')
                    container_name = container.get('name', 'Unknown')
                    
                    print(f"  Found container: {container_name} ({container_public_id})")
                    
                    if container_public_id == container_id:
                        print(f"\n[U+2713] FOUND YOUR CONTAINER!")
                        print(f"  Account ID: {account_id}")
                        print(f"  Account Name: {account_name}")
                        print(f"  Container ID: {container_public_id}")
                        print(f"  Container Name: {container_name}")
                        
                        # Update config file
                        update_config(account_id)
                        
                        return account_id
        
        print(f"\nContainer {container_id} not found in any accessible accounts!")
        print("\nPossible issues:")
        print("1. Service account doesn't have access to the GTM account")
        print("2. Container ID is incorrect")
        print("3. Container has been deleted")
        
    except HttpError as e:
        print(f"API Error: {e}")
        if 'User does not have permission' in str(e):
            print("\nThe service account needs permission to access GTM.")
            print("Add it in GTM: Admin > User Management")
    except Exception as e:
        print(f"Error: {e}")
    
    return None

def update_config(account_id):
    """Update the config file with the correct account ID"""
    config_path = Path(__file__).parent / 'gtm_config.json'
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        config['account_id'] = account_id
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n[U+2713] Updated gtm_config.json with account ID: {account_id}")

def main():
    print("="*50)
    print("GTM ACCOUNT ID FINDER")
    print("="*50)
    
    container_id = input("\nEnter your GTM Container ID (default: GTM-WKP28PNQ): ").strip()
    if not container_id:
        container_id = "GTM-WKP28PNQ"
    
    account_id = find_account_id(container_id)
    
    if account_id:
        print("\n" + "="*50)
        print("SUCCESS!")
        print("="*50)
        print(f"Your GTM Account ID is: {account_id}")
        print("\nConfiguration has been updated automatically.")
        print("You can now run: python scripts/run_gtm_setup.py")
    else:
        print("\n" + "="*50)
        print("MANUAL STEPS REQUIRED")
        print("="*50)
        print("1. Go to https://tagmanager.google.com")
        print("2. Click on your container")
        print("3. Look at the URL - it will contain the account ID")
        print("4. Update gtm_config.json with the correct account_id")

if __name__ == "__main__":
    main()
