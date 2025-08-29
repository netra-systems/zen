#!/usr/bin/env python3
"""
Test GA4 connection and find property
"""

from google.analytics.admin import AnalyticsAdminServiceClient
from google.oauth2 import service_account
from pathlib import Path

# Load credentials
cred_path = Path(__file__).parent.parent / "gcp-staging-sa-key.json"

credentials = service_account.Credentials.from_service_account_file(
    str(cred_path),
    scopes=['https://www.googleapis.com/auth/analytics.edit']
)

client = AnalyticsAdminServiceClient(credentials=credentials)

print("Testing GA4 connection...")
print("="*60)

# The measurement ID we're looking for
TARGET_MEASUREMENT_ID = "G-522Q06C6M5"

try:
    # List accounts first
    print("\nAccounts:")
    accounts = client.list_accounts()
    
    for account in accounts:
        print(f"\nAccount: {account.display_name}")
        print(f"  Account ID: {account.name}")
    
    # List ALL properties - filter is REQUIRED
    print("\n" + "="*60)
    print("Properties:")
    
    # Use ancestor filter to list all properties under the account
    from google.analytics.admin_v1alpha.types import ListPropertiesRequest
    
    # Get first account to use in filter
    accounts_list = list(client.list_accounts())
    if not accounts_list:
        print("No accounts found!")
        exit(1)
    
    account_id = accounts_list[0].name  # e.g., "accounts/366597574"
    
    request = ListPropertiesRequest(
        filter=f"parent:{account_id}"
    )
    page_result = client.list_properties(request=request)
    
    found_property = None
    
    for response in page_result:
        print(f"\nProperty: {response.display_name}")
        print(f"  Property ID: {response.name}")
        print(f"  Time Zone: {response.time_zone}")
        
        # Check data streams for measurement ID
        try:
            streams = client.list_data_streams(parent=response.name)
            for stream in streams:
                if hasattr(stream, 'web_stream_data') and stream.web_stream_data:
                    measurement_id = stream.web_stream_data.measurement_id
                    print(f"  Measurement ID: {measurement_id}")
                    print(f"  Stream URL: {stream.web_stream_data.default_uri}")
                    
                    if measurement_id == TARGET_MEASUREMENT_ID:
                        found_property = response
                        print(f"  >>> FOUND TARGET PROPERTY! <<<")
        except Exception as e:
            print(f"  Could not get streams: {e}")
    
    print("\n" + "="*60)
    if found_property:
        print(f"SUCCESS! Found property with measurement ID {TARGET_MEASUREMENT_ID}")
        print(f"Property Name: {found_property.display_name}")
        print(f"Property Path: {found_property.name}")
        
        # Extract property ID and account ID
        property_id = found_property.name.split('/')[-1]
        print(f"\nExtracted Property ID: {property_id}")
        
        # Update the config file
        print("\nYou can update ga4_config.json with:")
        print(f'  "property_id": "{property_id}",')
        
    else:
        print(f"[WARNING] Could not find property with measurement ID {TARGET_MEASUREMENT_ID}")
        print("\nPossible issues:")
        print("1. The measurement ID is incorrect")
        print("2. The service account doesn't have access to this property")
        print("\nTo grant access:")
        print("1. Go to GA4 > Admin > Property Access Management")
        print("2. Add: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
        print("3. Grant Editor role")
        
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()