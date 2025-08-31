#!/usr/bin/env python3
"""Debug auth service environment loading."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_auth_environment():
    """Debug what environment variables the auth service sees."""
    
    # Clear and set test environment
    for key in list(os.environ.keys()):
        if 'JWT' in key:
            del os.environ[key]
    
    os.environ['ENVIRONMENT'] = 'staging'
    os.environ['JWT_SECRET_STAGING'] = 'TEST_STAGING_SECRET_86_CHARS'
    os.environ['JWT_SECRET_KEY'] = 'TEST_KEY_SECRET_43_CHARS'
    
    print("🔍 Auth Service Environment Debug")
    print("=" * 50)
    
    # Test direct OS environment
    print("1. Direct OS Environment:")
    print(f"   ENVIRONMENT: {os.environ.get('ENVIRONMENT')}")
    print(f"   JWT_SECRET_STAGING: '{os.environ.get('JWT_SECRET_STAGING', 'NOT_SET')}'")
    print(f"   JWT_SECRET_KEY: '{os.environ.get('JWT_SECRET_KEY', 'NOT_SET')}'")
    
    # Test what get_env() returns
    print("\n2. Auth Service get_env():")
    try:
        from auth_service.auth_core.isolated_environment import get_env
        
        env_manager = get_env()
        env_val = env_manager.get("ENVIRONMENT", "default")
        staging_secret = env_manager.get("JWT_SECRET_STAGING", "NOT_SET")  
        key_secret = env_manager.get("JWT_SECRET_KEY", "NOT_SET")
        
        print(f"   ENVIRONMENT: '{env_val}'")
        print(f"   JWT_SECRET_STAGING: '{staging_secret}'")
        print(f"   JWT_SECRET_KEY: '{key_secret}'")
        
    except Exception as e:
        print(f"   Error loading get_env(): {e}")
    
    # Test auth service secret loader logic step by step
    print("\n3. Auth Service Secret Loader Logic:")
    try:
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        # Import get_env from auth service context
        from auth_service.auth_core.isolated_environment import get_env
        
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        print(f"   Environment detected: '{env}'")
        
        if env == "staging":
            secret = env_manager.get("JWT_SECRET_STAGING")
            print(f"   JWT_SECRET_STAGING lookup result: '{secret}'")
            print(f"   JWT_SECRET_STAGING truthy: {bool(secret)}")
            
            if secret:
                print("   ✅ Would use JWT_SECRET_STAGING")
            else:
                print("   ❌ JWT_SECRET_STAGING not found, falling back")
                secret = env_manager.get("JWT_SECRET_KEY")
                print(f"   JWT_SECRET_KEY fallback result: '{secret}'")
        
    except Exception as e:
        print(f"   Error in auth service logic: {e}")

if __name__ == "__main__":
    debug_auth_environment()