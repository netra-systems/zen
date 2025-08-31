#!/usr/bin/env python3
"""
Verify OAuth configuration is properly set up for development.
Tests that credentials are loaded correctly and validates format.
"""
import os
import sys
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def verify_oauth_configuration():
    """Verify OAuth is properly configured for development."""
    print("Verifying OAuth Configuration for Development")
    print("=" * 60)
    
    # Set environment to development
    os.environ["ENVIRONMENT"] = "development"
    
    try:
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        from auth_service.auth_core.config import AuthConfig
        
        # Test 1: Check credential loading
        print("\n1. Testing credential loading...")
        print("-" * 40)
        
        client_id = AuthSecretLoader.get_google_client_id()
        client_secret = AuthSecretLoader.get_google_client_secret()
        
        # Validate client ID format
        if client_id:
            if re.match(r'^\d{12}-[a-z0-9]{32}\.apps\.googleusercontent\.com$', client_id):
                print(f"  [OK] Client ID format valid")
                print(f"       ID: {client_id[:20]}...{client_id[-20:]}")
            else:
                print(f"  [WARN] Client ID format may be incorrect")
                print(f"       ID: {client_id}")
        else:
            print(f"  [ERROR] No Client ID found")
            return False
        
        # Validate client secret format
        if client_secret:
            if client_secret.startswith("GOCSPX-") and len(client_secret) > 20:
                print(f"  [OK] Client Secret format valid")
                print(f"       Secret: {client_secret[:10]}... (length: {len(client_secret)})")
            else:
                print(f"  [WARN] Client Secret format may be incorrect")
        else:
            print(f"  [ERROR] No Client Secret found")
            return False
        
        # Test 2: Check AuthConfig
        print("\n2. Testing AuthConfig...")
        print("-" * 40)
        
        env = AuthConfig.get_environment()
        print(f"  Environment: {env}")
        
        config_client_id = AuthConfig.get_google_client_id()
        config_client_secret = AuthConfig.get_google_client_secret()
        
        if config_client_id == client_id:
            print(f"  [OK] AuthConfig returns same Client ID")
        else:
            print(f"  [ERROR] AuthConfig Client ID mismatch")
            return False
            
        if config_client_secret == client_secret:
            print(f"  [OK] AuthConfig returns same Client Secret")
        else:
            print(f"  [ERROR] AuthConfig Client Secret mismatch")
            return False
        
        # Test 3: Check frontend/backend URLs
        print("\n3. Testing URL configuration...")
        print("-" * 40)
        
        frontend_url = AuthConfig.get_frontend_url()
        auth_service_url = AuthConfig.get_auth_service_url()
        
        print(f"  Frontend URL: {frontend_url}")
        print(f"  Auth Service URL: {auth_service_url}")
        
        if env == "development":
            expected_frontend = "http://localhost:3000"
            expected_auth = "http://localhost:8081"
            
            if frontend_url == expected_frontend:
                print(f"  [OK] Frontend URL correct for development")
            else:
                print(f"  [WARN] Frontend URL unexpected: {frontend_url}")
                
            if auth_service_url == expected_auth:
                print(f"  [OK] Auth Service URL correct for development")
            else:
                print(f"  [WARN] Auth Service URL unexpected: {auth_service_url}")
        
        # Test 4: Verify environment variables
        print("\n4. Checking environment variables...")
        print("-" * 40)
        
        from shared.isolated_environment import get_env
        env_manager = get_env()
        
        oauth_vars = {
            "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "Development-specific Client ID",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": "Development-specific Secret",
            "GOOGLE_CLIENT_ID": "Generic fallback Client ID",
            "GOOGLE_CLIENT_SECRET": "Generic fallback Secret"
        }
        
        for var_name, description in oauth_vars.items():
            value = env_manager.get(var_name)
            if value:
                if "SECRET" in var_name:
                    print(f"  [OK] {var_name}: {'*' * 10} (set)")
                else:
                    print(f"  [OK] {var_name}: {value[:30]}... (set)")
            else:
                print(f"  [MISSING] {var_name}: Not set ({description})")
        
        # Summary
        print("\n" + "=" * 60)
        print("[SUCCESS] OAuth configuration verified successfully!")
        print("=" * 60)
        print("\nOAuth is ready for use in development environment.")
        print("\nExpected redirect URIs in Google Console:")
        print("  - http://localhost:3000/auth/callback")
        print("\nTo test OAuth flow:")
        print("  1. Run: python scripts/dev_launcher.py")
        print("  2. Navigate to: http://localhost:3000/login")
        print("  3. Click 'Login with Google'")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] OAuth verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = verify_oauth_configuration()
    sys.exit(0 if success else 1)