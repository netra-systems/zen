#!/usr/bin/env python3
"""
Simple GA4 property check with proper filter
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

print("Checking GA4 access...")

# List accounts
accounts = list(client.list_accounts())
print(f"\nFound {len(accounts)} accounts:")
for acc in accounts:
    print(f"  - {acc.display_name} ({acc.name})")

# Try to get a specific property if we know the ID
# Or list with proper filter
try:
    # List properties for the account we found
    if accounts:
        account_name = accounts[0].name
        # Try different filter formats
        filters_to_try = [
            f"parent:{account_name}",
            f"ancestor:{account_name}",
            account_name,
            ""  # Empty filter as last resort
        ]
        
        for filter_str in filters_to_try:
            try:
                print(f"\nTrying filter: '{filter_str}'")
                if filter_str:
                    props = list(client.list_properties(filter=filter_str))
                else:
                    props = list(client.list_properties())
                print(f"  Found {len(props)} properties")
                for prop in props:
                    print(f"    - {prop.display_name}")
                    # Get measurement ID
                    try:
                        streams = list(client.list_data_streams(parent=prop.name))
                        for stream in streams:
                            if hasattr(stream, 'web_stream_data') and stream.web_stream_data:
                                print(f"      Measurement ID: {stream.web_stream_data.measurement_id}")
                    except:
                        pass
                if props:
                    break
            except Exception as e:
                print(f"  Failed: {str(e)[:100]}")
                
except Exception as e:
    print(f"\nFinal error: {e}")

print("\nNote: If no properties found, you need to:")
print("1. Go to GA4 Admin > Property Access Management")
print("2. Add: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
print("3. Grant Editor role")