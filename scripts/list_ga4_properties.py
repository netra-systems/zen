#!/usr/bin/env python3
"""
List all GA4 properties accessible by the service account
"""

import json
from pathlib import Path
from google.analytics.admin import AnalyticsAdminServiceClient
from google.oauth2 import service_account

def list_properties():
    """List all accessible GA4 properties and their measurement IDs"""
    
    # Load credentials
    cred_path = Path(__file__).parent.parent / "gcp-staging-sa-key.json"
    
    credentials = service_account.Credentials.from_service_account_file(
        str(cred_path),
        scopes=['https://www.googleapis.com/auth/analytics.readonly']
    )
    
    client = AnalyticsAdminServiceClient(credentials=credentials)
    
    print("\n" + "="*60)
    print("GA4 PROPERTIES ACCESSIBLE BY SERVICE ACCOUNT")
    print("="*60)
    
    try:
        # List all accounts
        accounts = client.list_accounts()
        
        account_count = 0
        property_count = 0
        
        for account in accounts:
            account_count += 1
            print(f"\nAccount: {account.display_name}")
            print(f"  Account ID: {account.name}")
            
            # List all properties (filter by account doesn't work in this API version)
            properties = client.list_properties()
            
            for prop in properties:
                property_count += 1
                print(f"\n  Property: {prop.display_name}")
                print(f"    Property ID: {prop.name}")
                print(f"    Time Zone: {prop.time_zone}")
                print(f"    Industry: {prop.industry_category if hasattr(prop, 'industry_category') else 'N/A'}")
                
                # Try to get data streams to find measurement ID
                try:
                    data_streams = client.list_data_streams(parent=prop.name)
                    for stream in data_streams:
                        if hasattr(stream, 'web_stream_data') and stream.web_stream_data:
                            print(f"    Measurement ID: {stream.web_stream_data.measurement_id}")
                            print(f"    Stream URL: {stream.web_stream_data.default_uri}")
                        elif hasattr(stream, 'android_app_stream_data') and stream.android_app_stream_data:
                            print(f"    Android App: {stream.android_app_stream_data.package_name}")
                        elif hasattr(stream, 'ios_app_stream_data') and stream.ios_app_stream_data:
                            print(f"    iOS App: {stream.ios_app_stream_data.bundle_id}")
                except Exception as e:
                    print(f"    Could not list data streams: {e}")
        
        print(f"\n{'='*60}")
        print(f"Summary: Found {account_count} accounts with {property_count} properties")
        print("="*60)
        
        if property_count == 0:
            print("\n[WARNING] No properties found!")
            print("\nPossible reasons:")
            print("1. The service account doesn't have access to any GA4 properties")
            print("2. You need to grant Editor or Viewer access to the service account in GA4")
            print("\nTo grant access:")
            print("1. Go to GA4 > Admin > Property Access Management")
            print("2. Add user: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
            print("3. Grant Editor role")
            
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("1. The Google Analytics Admin API is enabled")
        print("2. The service account has proper permissions")

if __name__ == "__main__":
    list_properties()