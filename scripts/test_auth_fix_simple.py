#!/usr/bin/env python3
"""
Simple test script to validate Auth Service integration fixes for GCP staging.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env

async def test_auth_service_config():
    """Test auth service configuration with the fixes."""
    print("Testing Auth Service Configuration Fixes")
    print("=" * 50)
    
    # Set up test environment similar to staging
    env = get_env()
    env.set("ENVIRONMENT", "staging", "test_auth_fix")
    env.set("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai", "test_auth_fix")
    env.set("AUTH_SERVICE_ENABLED", "true", "test_auth_fix") 
    env.set("SERVICE_ID", "netra-backend", "test_auth_fix")
    env.set("SERVICE_SECRET", "test-secret-32-characters-or-more", "test_auth_fix")
    
    print("Environment Configuration:")
    print(f"   ENVIRONMENT: {env.get('ENVIRONMENT')}")
    print(f"   AUTH_SERVICE_URL: {env.get('AUTH_SERVICE_URL')}")
    print(f"   AUTH_SERVICE_ENABLED: {env.get('AUTH_SERVICE_ENABLED')}")
    print(f"   SERVICE_ID: {env.get('SERVICE_ID')}")
    print(f"   SERVICE_SECRET: {'[SET]' if env.get('SERVICE_SECRET') else '[NOT SET]'}")
    print()

    # Test auth service settings initialization
    try:
        from netra_backend.app.clients.auth_client_cache import AuthServiceSettings
        settings = AuthServiceSettings()
        
        print("Auth Service Settings:")
        print(f"   Base URL: {settings.base_url}")
        print(f"   Enabled: {settings.enabled}")
        print(f"   Service ID: {settings.service_id}")
        print(f"   Service Secret Configured: {settings.is_service_secret_configured()}")
        print()
        
        # Validate the configuration
        if settings.enabled and settings.service_id and settings.is_service_secret_configured():
            print("SUCCESS: All auth service settings configured correctly!")
            return True
        else:
            print("ERROR: Auth service configuration incomplete")
            return False
        
    except Exception as e:
        print(f"ERROR: Failed to initialize auth service settings: {e}")
        return False

async def test_connectivity():
    """Test basic connectivity to auth service."""
    print("Testing Auth Service Connectivity")
    print("=" * 50)
    
    try:
        import httpx
        auth_url = "https://auth.staging.netrasystems.ai"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{auth_url}/health")
            
            if response.status_code == 200:
                print("SUCCESS: Auth service health endpoint is reachable")
                return True
            else:
                print(f"ERROR: Health endpoint returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"ERROR: Connectivity test failed: {e}")
        return False

def print_fix_summary():
    """Display summary of the fixes applied."""
    print("\nAuth Service Integration Fixes Applied")
    print("=" * 50)
    print("1. Added SERVICE_ID environment variable:")
    print("   - Backend: SERVICE_ID=netra-backend")
    print("   - Auth Service: SERVICE_ID=auth-service")
    print("2. Added AUTH_SERVICE_ENABLED=true for backend")
    print("3. Verified AUTH_SERVICE_URL configuration")
    print("4. Service secrets configured via GCP Secret Manager")
    print()
    print("Expected Impact:")
    print("- Eliminates 'Auth service is required for token validation' errors")
    print("- Enables proper service-to-service authentication")
    print("- Allows token validation to work in staging environment")

async def main():
    """Main test function."""
    print("Auth Service Integration Fix Validation")
    print("=" * 50)
    
    config_ok = await test_auth_service_config()
    connectivity_ok = await test_connectivity()
    
    print("\nTest Results Summary")
    print("=" * 50)
    print(f"Configuration Test: {'PASS' if config_ok else 'FAIL'}")
    print(f"Connectivity Test: {'PASS' if connectivity_ok else 'FAIL'}")
    
    if config_ok and connectivity_ok:
        print("\nSUCCESS: All tests passed! The fixes should resolve the auth service integration issues.")
    else:
        print("\nWARNING: Some tests failed. Review the issues above before deployment.")
    
    print_fix_summary()
    
    return config_ok and connectivity_ok

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)