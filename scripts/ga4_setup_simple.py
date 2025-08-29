#!/usr/bin/env python3
"""
Simplified GA4 Setup - Lists what needs to be configured
"""

import json
from pathlib import Path
from google.analytics.admin import AnalyticsAdminServiceClient
from google.oauth2 import service_account

def main():
    # Load configuration
    config_path = Path(__file__).parent / "ga4_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Load credentials
    cred_path = Path(__file__).parent.parent / "gcp-staging-sa-key.json"
    credentials = service_account.Credentials.from_service_account_file(
        str(cred_path),
        scopes=['https://www.googleapis.com/auth/analytics.edit']
    )
    
    client = AnalyticsAdminServiceClient(credentials=credentials)
    
    print("\n" + "="*60)
    print("GA4 CONFIGURATION SUMMARY")
    print("="*60)
    
    property_path = f"properties/{config['ga4_property']['property_id']}"
    print(f"\nProperty: {config['ga4_property']['property_name']}")
    print(f"Property ID: {property_path}")
    print(f"Measurement ID: {config['ga4_property']['measurement_id']}")
    
    # Check existing configurations
    print("\n" + "="*60)
    print("CURRENT STATUS")
    print("="*60)
    
    # List existing custom dimensions
    try:
        existing_dims = list(client.list_custom_dimensions(parent=property_path))
        print(f"\nExisting Custom Dimensions: {len(existing_dims)}")
        for dim in existing_dims:
            print(f"  - {dim.display_name} ({dim.parameter_name})")
    except Exception as e:
        print(f"Could not list dimensions: {e}")
    
    # List existing custom metrics
    try:
        existing_metrics = list(client.list_custom_metrics(parent=property_path))
        print(f"\nExisting Custom Metrics: {len(existing_metrics)}")
        for metric in existing_metrics:
            print(f"  - {metric.display_name} ({metric.parameter_name})")
    except Exception as e:
        print(f"Could not list metrics: {e}")
    
    # List existing conversion events
    try:
        existing_conversions = list(client.list_conversion_events(parent=property_path))
        print(f"\nExisting Conversion Events: {len(existing_conversions)}")
        for conv in existing_conversions:
            if not conv.deletable:  # Skip default events
                continue
            print(f"  - {conv.event_name}")
    except Exception as e:
        print(f"Could not list conversions: {e}")
    
    print("\n" + "="*60)
    print("CONFIGURATION TO BE APPLIED")
    print("="*60)
    
    # Custom Dimensions
    print(f"\nCustom Dimensions to Create: {len(config['custom_dimensions']['user_scoped']) + len(config['custom_dimensions']['event_scoped'])}")
    print("\nUser-Scoped Dimensions:")
    for dim in config['custom_dimensions']['user_scoped']:
        print(f"  - {dim['display_name']} ({dim['parameter_name']})")
    
    print("\nEvent-Scoped Dimensions:")
    for dim in config['custom_dimensions']['event_scoped']:
        print(f"  - {dim['display_name']} ({dim['parameter_name']})")
    
    # Custom Metrics
    print(f"\nCustom Metrics to Create: {len(config['custom_metrics'])}")
    for metric in config['custom_metrics']:
        print(f"  - {metric['display_name']} ({metric['parameter_name']}) - {metric['measurement_unit']}")
    
    # Conversion Events
    print(f"\nConversion Events to Mark: {len(config['conversion_events'])}")
    for event in config['conversion_events']:
        print(f"  - {event}")
    
    # Audiences
    print(f"\nAudiences to Create: {len(config['audiences'])}")
    for audience in config['audiences']:
        print(f"  - {audience['display_name']}: {audience['description']}")
    
    print("\n" + "="*60)
    print("MANUAL CONFIGURATION REQUIRED IN GA4 UI")
    print("="*60)
    
    print("\n1. CUSTOM DIMENSIONS:")
    print("   Go to Admin > Custom definitions > Custom dimensions")
    print("   Click 'Create custom dimension' for each dimension listed above")
    
    print("\n2. CUSTOM METRICS:")
    print("   Go to Admin > Custom definitions > Custom metrics")
    print("   Click 'Create custom metric' for each metric listed above")
    
    print("\n3. CONVERSION EVENTS:")
    print("   Go to Admin > Events > Conversions")
    print("   Mark each event as conversion")
    
    print("\n4. AUDIENCES:")
    print("   Go to Admin > Audiences")
    print("   Create each audience with the filters specified")
    
    print("\n5. ENHANCED MEASUREMENT:")
    print("   Go to Admin > Data Streams > Web Stream")
    print("   Enable all enhanced measurement features")
    
    print("\n6. DATA RETENTION:")
    print("   Go to Admin > Data Settings > Data Retention")
    print("   Set to 14 months")
    
    print("\n" + "="*60)
    print("Configuration file saved at: scripts/ga4_config.json")
    print("Documentation saved at: scripts/GA4_AUTOMATION_REPORT.md")
    print("="*60)

if __name__ == "__main__":
    main()