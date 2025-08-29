#!/usr/bin/env python3
"""
Check GA4 access and list properties
"""

import json
from pathlib import Path
from google.analytics.admin import AnalyticsAdminServiceClient
from google.oauth2 import service_account

def check_access():
    """Check GA4 access"""
    
    # Load credentials
    cred_path = Path(__file__).parent.parent / "gcp-staging-sa-key.json"
    
    credentials = service_account.Credentials.from_service_account_file(
        str(cred_path),
        scopes=['https://www.googleapis.com/auth/analytics.edit']
    )
    
    client = AnalyticsAdminServiceClient(credentials=credentials)
    
    print("\n" + "="*60)
    print("GA4 ACCESS CHECK")
    print("="*60)
    
    try:
        # First, list accounts to verify access
        print("\nListing accounts...")
        accounts = list(client.list_accounts())
        print(f"Found {len(accounts)} accounts")
        
        for account in accounts:
            print(f"\nAccount: {account.display_name}")
            print(f"  ID: {account.name}")
        
        # Now try to list all properties without filter
        print("\nListing all properties...")
        all_properties = []
        
        # Use the pager to list properties
        for prop in client.list_properties():
            all_properties.append(prop)
            print(f"\nProperty: {prop.display_name}")
            print(f"  Property Path: {prop.name}")
            print(f"  Time Zone: {prop.time_zone}")
            
            # Get data streams for this property
            try:
                print("  Data Streams:")
                for stream in client.list_data_streams(parent=prop.name):
                    if hasattr(stream, 'web_stream_data') and stream.web_stream_data:
                        print(f"    - Web Stream: {stream.display_name}")
                        print(f"      Measurement ID: {stream.web_stream_data.measurement_id}")
                        print(f"      URL: {stream.web_stream_data.default_uri}")
            except Exception as e:
                print(f"    Error getting streams: {e}")
        
        print(f"\n{'='*60}")
        print(f"Total properties found: {len(all_properties)}")
        
        if len(all_properties) == 0:
            print("\n[WARNING] No properties accessible!")
            print("\nTo grant access:")
            print("1. Go to GA4 > Admin > Property Access Management")
            print("2. Add: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
            print("3. Grant Editor role")
        
    except Exception as e:
        print(f"\nError: {e}")
        print(f"\nError type: {type(e).__name__}")

if __name__ == "__main__":
    check_access()