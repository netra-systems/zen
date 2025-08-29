#!/usr/bin/env python3
"""
Simplified GTM Setup Runner
Uses existing service account credentials to configure GTM
"""

import json
import os
import sys
from pathlib import Path
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'google-auth',
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.warning(f"Missing packages: {', '.join(missing_packages)}")
        logger.info("Installing required packages...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install'] + missing_packages
        )
        logger.info("Packages installed successfully")

def get_service_account_key_path():
    """Find the service account key file"""
    # Check common locations
    possible_paths = [
        Path('netra-staging-sa-key.json'),
        Path('secrets/netra-staging-sa-key.json'),
        Path('../secrets/netra-staging-sa-key.json'),
        Path.home() / '.config' / 'gcloud' / 'netra-staging-sa-key.json',
        Path('/etc/secrets/netra-staging-sa-key.json'),
    ]
    
    # Check environment variable
    env_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if env_path:
        possible_paths.insert(0, Path(env_path))
    
    # Find first existing path
    for path in possible_paths:
        if path.exists():
            logger.info(f"Found service account key at: {path}")
            return str(path.absolute())
    
    # If not found, prompt user
    logger.warning("Service account key not found in default locations")
    manual_path = input("Enter path to netra-staging-sa-key.json: ").strip()
    if Path(manual_path).exists():
        return str(Path(manual_path).absolute())
    else:
        raise FileNotFoundError(f"Service account key not found at: {manual_path}")

def load_config():
    """Load GTM configuration"""
    config_path = Path(__file__).parent / 'gtm_config.json'
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        return json.load(f)

def run_gtm_setup():
    """Run the GTM setup with existing service account"""
    # Check dependencies
    check_dependencies()
    
    # Load configuration
    config = load_config()
    logger.info("Configuration loaded successfully")
    
    # Find service account key
    sa_key_path = get_service_account_key_path()
    
    # Build command
    cmd = [
        sys.executable,
        str(Path(__file__).parent / 'gtm_api_setup.py'),
        '--account-id', config['account_id'],
        '--container-id', config['container_id'],
        '--credentials', sa_key_path,
        '--workspace', config['workspace_name']
    ]
    
    # Add GA4 ID if available
    if config.get('ga4_measurement_id') and config['ga4_measurement_id'] != 'G-XXXXXXXXXX':
        cmd.extend(['--ga4-id', config['ga4_measurement_id']])
    
    # Add publish flag if configured
    if config.get('auto_publish', False):
        cmd.append('--publish')
    
    logger.info("Starting GTM configuration...")
    logger.info(f"Account ID: {config['account_id']}")
    logger.info(f"Container ID: {config['container_id']}")
    logger.info(f"Service Account: {config['service_account_email']}")
    
    # Run the setup
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        
        if result.returncode == 0:
            logger.info("GTM setup completed successfully!")
            
            # Show next steps
            print("\n" + "="*50)
            print("NEXT STEPS:")
            print("="*50)
            print("1. Log into Google Tag Manager: https://tagmanager.google.com")
            print(f"2. Select container: {config['container_id']}")
            print("3. Review the workspace changes")
            print("4. Test in Preview mode")
            print("5. Publish when ready")
            print("\nIMPORTANT:")
            print(f"- Update GA4 Measurement ID in gtm_config.json (currently: {config.get('ga4_measurement_id', 'Not set')})")
            print("- Verify all variables are capturing data correctly")
            print("- Test events in Google Analytics real-time view")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"GTM setup failed: {e}")
        if e.stderr:
            logger.error(f"Error details: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

def main():
    """Main entry point"""
    print("="*50)
    print("NETRA GTM CONFIGURATION TOOL")
    print("="*50)
    print("\nThis tool will configure Google Tag Manager with:")
    print("- All required variables for event tracking")
    print("- Triggers for authentication, engagement, and conversion events")
    print("- Google Analytics 4 tags for complete integration")
    print("\nUsing service account: netra-staging-deploy@netra-staging.iam.gserviceaccount.com")
    print("-"*50)
    
    response = input("\nProceed with configuration? (y/n): ").strip().lower()
    if response != 'y':
        print("Configuration cancelled")
        sys.exit(0)
    
    run_gtm_setup()

if __name__ == "__main__":
    main()