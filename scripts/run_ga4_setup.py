#!/usr/bin/env python3
"""
GA4 Setup Runner - Wrapper script for GA4 automation
Handles package installation and executes GA4 configuration
"""

import subprocess
import sys
import os
from pathlib import Path

def check_and_install_packages():
    """Check if required packages are installed and install if missing"""
    required_packages = [
        ('google-analytics-admin', 'google.analytics.admin'),
        ('google-auth', 'google.auth')
    ]
    
    packages_to_install = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"[OK] {package_name} is installed")
        except ImportError:
            print(f"[MISSING] {package_name} is not installed")
            packages_to_install.append(package_name)
    
    if packages_to_install:
        print("\nInstalling required packages...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", *packages_to_install
            ])
            print("[OK] Packages installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install packages: {e}")
            return False
    
    return True

def check_credentials():
    """Check if service account credentials file exists"""
    # Check multiple possible locations
    possible_paths = [
        Path("netra-staging-sa-key.json"),
        Path("scripts/netra-staging-sa-key.json"),
        Path(__file__).parent / "netra-staging-sa-key.json",
        Path.home() / "netra-staging-sa-key.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"[OK] Found credentials at: {path}")
            return True
    
    print("\n[WARNING] Service account key file not found!")
    print("\nTo set up GA4 automation, you need:")
    print("1. A service account with GA4 Editor access")
    print("2. The service account key file (netra-staging-sa-key.json)")
    print("\nExpected locations:")
    for path in possible_paths:
        print(f"  - {path}")
    
    print("\nTo create a service account:")
    print("1. Go to Google Cloud Console")
    print("2. Navigate to IAM & Admin > Service Accounts")
    print("3. Create or use existing: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
    print("4. Create a JSON key and save as 'netra-staging-sa-key.json'")
    print("5. Grant the service account Editor access to your GA4 property")
    
    return False

def check_configuration():
    """Check if GA4 configuration file exists"""
    config_path = Path(__file__).parent / "ga4_config.json"
    
    if not config_path.exists():
        print("\n[ERROR] Configuration file not found: ga4_config.json")
        return False
    
    print(f"[OK] Configuration file found: {config_path}")
    
    # Load and display key configuration
    import json
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("\nConfiguration Summary:")
    print(f"  - Measurement ID: {config['ga4_property']['measurement_id']}")
    print(f"  - Property Name: {config['ga4_property']['property_name']}")
    print(f"  - Service Account: {config['service_account']['email']}")
    print(f"  - Custom Dimensions: {len(config['custom_dimensions']['user_scoped']) + len(config['custom_dimensions']['event_scoped'])}")
    print(f"  - Custom Metrics: {len(config['custom_metrics'])}")
    print(f"  - Conversion Events: {len(config['conversion_events'])}")
    print(f"  - Audiences: {len(config['audiences'])}")
    
    return True

def run_ga4_setup():
    """Execute the GA4 automation script"""
    script_path = Path(__file__).parent / "ga4_automation.py"
    
    if not script_path.exists():
        print(f"\n[ERROR] GA4 automation script not found: {script_path}")
        return False
    
    print(f"\n{'='*60}")
    print("RUNNING GA4 AUTOMATION")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"\n[ERROR] Error running GA4 automation: {e}")
        return False

def main():
    """Main execution"""
    print(f"\n{'='*60}")
    print("GA4 AUTOMATION SETUP RUNNER")
    print(f"{'='*60}")
    
    # Step 1: Check and install packages
    print("\n1. Checking Python packages...")
    if not check_and_install_packages():
        print("\n[ERROR] Failed to install required packages")
        sys.exit(1)
    
    # Step 2: Check credentials
    print("\n2. Checking service account credentials...")
    if not check_credentials():
        print("\n[ERROR] Credentials not found. Please set up service account first.")
        sys.exit(1)
    
    # Step 3: Check configuration
    print("\n3. Checking GA4 configuration...")
    if not check_configuration():
        print("\n[ERROR] Configuration file not found")
        sys.exit(1)
    
    # Step 4: Confirm before running
    print(f"\n{'='*60}")
    print("READY TO CONFIGURE GA4")
    print(f"{'='*60}")
    print("\nThis will:")
    print("  - Create custom dimensions and metrics")
    print("  - Mark conversion events")
    print("  - Configure data retention")
    print("  - Set up audiences (some manual steps required)")
    
    response = input("\nProceed with GA4 configuration? (y/n): ")
    if response.lower() != 'y':
        print("Configuration cancelled.")
        return
    
    # Step 5: Run the automation
    if run_ga4_setup():
        print(f"\n{'='*60}")
        print("[SUCCESS] GA4 SETUP COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print("\nNext steps:")
        print("1. Log into GA4 and verify configurations")
        print("2. Complete manual audience creation")
        print("3. Configure enhanced measurement settings")
        print("4. Set up custom reports as needed")
    else:
        print(f"\n{'='*60}")
        print("[ERROR] GA4 setup encountered errors")
        print(f"{'='*60}")
        print("\nPlease review the error messages above and:")
        print("1. Verify service account has Editor access to GA4")
        print("2. Check that measurement ID is correct")
        print("3. Ensure you have necessary API quotas")
        sys.exit(1)

if __name__ == "__main__":
    main()