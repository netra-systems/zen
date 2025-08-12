#!/usr/bin/env python3
"""Test configuration loading with detailed logging for debugging staging issues."""

import os
import sys
import json
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_config_loading():
    """Test configuration loading with detailed output."""
    
    print("=" * 80)
    print("Configuration Loading Test")
    print("=" * 80)
    
    # Print environment info
    print("\n[INFO] Environment Variables:")
    env_vars = [
        "ENVIRONMENT",
        "K_SERVICE",
        "K_REVISION",
        "GCP_PROJECT_ID",
        "GCP_PROJECT_ID_NUMERICAL_STAGING",
        "SECRET_MANAGER_PROJECT_ID",
        "LOAD_SECRETS",
        "PR_NUMBER",
        "GEMINI_API_KEY",
        "JWT_SECRET_KEY",
        "FERNET_KEY"
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var or "PASSWORD" in var:
                display_value = f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
            else:
                display_value = value
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: <not set>")
    
    print("\n" + "=" * 80)
    print("Loading configuration...")
    print("=" * 80 + "\n")
    
    try:
        # Import config (this will trigger the loading process)
        from app.config import settings, get_config
        
        # Reload to get fresh config with logging
        from app.config import reload_config
        reload_config()
        
        # Get the config
        config = get_config()
        
        print("\n[SUCCESS] Configuration loaded successfully!")
        
        # Check critical configurations
        print("\n[CRITICAL] Configuration Status:")
        
        # Check LLM configs
        if hasattr(config, 'llm_configs'):
            print("\n  LLM Configurations:")
            for name, llm_config in config.llm_configs.items():
                if llm_config and hasattr(llm_config, 'api_key'):
                    has_key = bool(llm_config.api_key)
                    status = "OK" if has_key else "MISSING"
                    print(f"    {name}: {status} {'API key configured' if has_key else 'No API key'}")
        
        # Check auth configs
        print("\n  Authentication:")
        jwt_configured = bool(getattr(config, 'jwt_secret_key', None))
        fernet_configured = bool(getattr(config, 'fernet_key', None))
        print(f"    JWT Secret: {'OK - Configured' if jwt_configured else 'MISSING'}")
        print(f"    Fernet Key: {'OK - Configured' if fernet_configured else 'MISSING'}")
        
        # Check OAuth config
        if hasattr(config, 'oauth_config'):
            oauth = config.oauth_config
            client_id = bool(getattr(oauth, 'client_id', None))
            client_secret = bool(getattr(oauth, 'client_secret', None))
            print(f"\n  OAuth Configuration:")
            print(f"    Client ID: {'OK - Configured' if client_id else 'MISSING'}")
            print(f"    Client Secret: {'OK - Configured' if client_secret else 'MISSING'}")
        
        # Check database config
        if hasattr(config, 'database_url'):
            db_url = config.database_url
            if db_url:
                # Parse and mask sensitive parts
                if "@" in db_url:
                    parts = db_url.split("@")
                    masked_url = f"{parts[0].split('://')[0]}://***@{parts[1]}"
                else:
                    masked_url = db_url
                print(f"\n  Database:")
                print(f"    URL: {masked_url}")
        
        print("\n" + "=" * 80)
        print("[SUCCESS] All configuration checks completed")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Configuration loading failed: {e}")
        print("\n[DEBUG] Full error details:")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set some test environment variables if running locally
    if not os.environ.get("ENVIRONMENT"):
        print("[INFO] No ENVIRONMENT set, using test values for local testing")
        os.environ["ENVIRONMENT"] = "development"
        os.environ["LOG_LEVEL"] = "DEBUG"
    
    success = test_config_loading()
    sys.exit(0 if success else 1)