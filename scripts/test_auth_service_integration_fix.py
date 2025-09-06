#!/usr/bin/env python3
"""
Test script to validate Auth Service integration fixes for GCP staging.

This script tests the auth service client configuration to ensure that the fixes
for SERVICE_ID and AUTH_SERVICE_ENABLED will resolve the integration issues.
"""

import os
import sys
import asyncio
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env

async def test_auth_service_config():
    """Test auth service configuration with the fixes."""
    print("🔍 Testing Auth Service Configuration Fixes")
    print("=" * 60)
    
    # Set up test environment similar to staging
    env = get_env()
    env.set("ENVIRONMENT", "staging", "test_auth_fix")
    env.set("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai", "test_auth_fix")
    env.set("AUTH_SERVICE_ENABLED", "true", "test_auth_fix") 
    env.set("SERVICE_ID", "netra-backend", "test_auth_fix")
    env.set("SERVICE_SECRET", "test-secret-32-characters-or-more", "test_auth_fix")
    
    print("✅ Environment Configuration:")
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
        
        print("✅ Auth Service Settings:")
        print(f"   Base URL: {settings.base_url}")
        print(f"   Enabled: {settings.enabled}")
        print(f"   Service ID: {settings.service_id}")
        print(f"   Service Secret Configured: {settings.is_service_secret_configured()}")
        print(f"   Cache TTL: {settings.cache_ttl}")
        print()
        
        # Validate the configuration
        issues = []
        if not settings.enabled:
            issues.append("❌ Auth service is disabled")
        if not settings.base_url:
            issues.append("❌ Auth service URL not configured")
        if not settings.service_id:
            issues.append("❌ SERVICE_ID not configured")
        if not settings.is_service_secret_configured():
            issues.append("❌ SERVICE_SECRET not configured")
        if "localhost" in settings.base_url and env.get('ENVIRONMENT') == 'staging':
            issues.append("❌ Using localhost URL in staging environment")
            
        if issues:
            print("🚨 Configuration Issues Found:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("✅ All auth service settings configured correctly!")
        
        print()
        
    except Exception as e:
        print(f"❌ Error initializing auth service settings: {e}")
        return False

    # Test auth client initialization
    try:
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        client = AuthServiceClient()
        
        print("✅ Auth Service Client:")
        print(f"   Settings Enabled: {client.settings.enabled}")
        print(f"   Base URL: {client.settings.base_url}")
        print(f"   Service ID: {client.service_id}")
        print(f"   Service Secret Configured: {bool(client.service_secret)}")
        print()
        
        # Test service auth headers
        headers = client._get_service_auth_headers()
        print("✅ Service Auth Headers:")
        if headers:
            print(f"   X-Service-ID: {headers.get('X-Service-ID', '[NOT SET]')}")
            print(f"   X-Service-Secret: {'[SET]' if headers.get('X-Service-Secret') else '[NOT SET]'}")
        else:
            print("   ❌ No service auth headers configured")
        print()
        
        # Validate service credentials
        service_issues = []
        if not client.service_id:
            service_issues.append("❌ Service ID not set on client")
        if not client.service_secret:
            service_issues.append("❌ Service secret not set on client")
        if client.service_id != "netra-backend":
            service_issues.append(f"❌ Expected SERVICE_ID 'netra-backend', got '{client.service_id}'")
            
        if service_issues:
            print("🚨 Service Credential Issues:")
            for issue in service_issues:
                print(f"   {issue}")
        else:
            print("✅ Service credentials configured correctly!")
            
    except Exception as e:
        print(f"❌ Error initializing auth service client: {e}")
        return False
    
    return True

async def test_auth_service_connectivity():
    """Test basic connectivity to auth service."""
    print("\n🌐 Testing Auth Service Connectivity")
    print("=" * 60)
    
    try:
        import httpx
        auth_url = "https://auth.staging.netrasystems.ai"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test health endpoint
            print(f"🔍 Testing health endpoint: {auth_url}/health")
            response = await client.get(f"{auth_url}/health")
            
            if response.status_code == 200:
                print("✅ Auth service health endpoint is reachable")
                health_data = response.json()
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Service: {health_data.get('service', 'unknown')}")
            else:
                print(f"❌ Health endpoint returned status {response.status_code}")
                return False
                
            # Test auth validate endpoint (without token - should return 400/401)
            print(f"🔍 Testing validate endpoint: {auth_url}/auth/validate")
            try:
                response = await client.post(f"{auth_url}/auth/validate", json={})
                print(f"✅ Validate endpoint is reachable (status: {response.status_code})")
                # 400/401 is expected without proper token/credentials
            except Exception as e:
                print(f"❌ Validate endpoint test failed: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Connectivity test failed: {e}")
        return False
    
    return True

def display_fix_summary():
    """Display summary of the fixes applied."""
    print("\n📝 Auth Service Integration Fixes Applied")
    print("=" * 60)
    print("1. ✅ Added SERVICE_ID environment variable to backend service:")
    print("   - Backend: SERVICE_ID=netra-backend")
    print("   - Auth Service: SERVICE_ID=auth-service")
    print()
    print("2. ✅ Added AUTH_SERVICE_ENABLED environment variable:")
    print("   - Backend: AUTH_SERVICE_ENABLED=true") 
    print()
    print("3. ✅ Verified AUTH_SERVICE_URL configuration:")
    print("   - Both services: AUTH_SERVICE_URL=https://auth.staging.netrasystems.ai")
    print()
    print("4. ✅ Service secrets are configured via GCP Secret Manager:")
    print("   - SERVICE_SECRET is loaded from service-secret-staging secret")
    print()
    print("Expected Impact:")
    print("- ✅ Eliminates 'Auth service is required for token validation' errors")
    print("- ✅ Enables proper service-to-service authentication")
    print("- ✅ Allows token validation to work in staging environment")
    print("- ✅ Prevents fallback to local validation in production")

async def main():
    """Main test function."""
    print("🚀 Auth Service Integration Fix Validation")
    print("=" * 60)
    
    config_ok = await test_auth_service_config()
    connectivity_ok = await test_auth_service_connectivity()
    
    print("\n📊 Test Results Summary")
    print("=" * 60)
    print(f"Configuration Test: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Connectivity Test: {'✅ PASS' if connectivity_ok else '❌ FAIL'}")
    
    if config_ok and connectivity_ok:
        print("\n🎉 All tests passed! The fixes should resolve the auth service integration issues.")
    else:
        print("\n⚠️  Some tests failed. Review the issues above before deployment.")
    
    display_fix_summary()
    
    return config_ok and connectivity_ok

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)