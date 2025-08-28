#!/usr/bin/env python3
"""
Test backend's auth service configuration
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_backend_auth_config():
    """Test backend's auth configuration and debug token validation"""
    
    print("=" * 60)
    print("BACKEND AUTH CONFIGURATION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    backend_url = "https://api.staging.netrasystems.ai"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Check backend health
        print("1. Checking backend health...")
        try:
            response = await client.get(
                f"{backend_url}/health",
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   [OK] Backend healthy")
                print(f"   Environment: {health_data.get('environment', 'unknown')}")
                print(f"   Version: {health_data.get('version', 'unknown')}")
                
                # Check if health endpoint exposes auth config (it shouldn't in production)
                if 'auth_service_url' in health_data:
                    print(f"   Auth Service URL: {health_data['auth_service_url']}")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        print()
        
        # Step 2: Try to get configuration (if exposed - dev only)
        print("2. Checking if configuration endpoint exists...")
        try:
            response = await client.get(
                f"{backend_url}/api/config",
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                config_data = response.json()
                print(f"   [WARNING] Config endpoint exposed (should be dev only)")
                if 'auth_service_url' in config_data:
                    print(f"   Auth Service URL: {config_data['auth_service_url']}")
            elif response.status_code == 404:
                print(f"   [OK] Config endpoint not exposed (expected in staging/prod)")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        print()
        
        # Step 3: Test auth error response headers for clues
        print("3. Testing auth error response for debug info...")
        try:
            # Try with an invalid token to see error response
            response = await client.get(
                f"{backend_url}/api/threads",
                headers={
                    "Authorization": "Bearer invalid_token_for_testing",
                    "Accept": "application/json"
                },
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print(f"   [OK] Got 401 as expected")
                error_data = response.json() if response.text else {}
                
                # Check error message for clues
                if 'message' in error_data:
                    print(f"   Error message: {error_data['message']}")
                if 'details' in error_data:
                    print(f"   Error details: {error_data['details']}")
                
                # Check headers for debug info
                for header in ['x-auth-service-url', 'x-auth-error', 'x-environment']:
                    if header in response.headers:
                        print(f"   {header}: {response.headers[header]}")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        print()
        
        # Step 4: Test with a specific debug endpoint if it exists
        print("4. Testing debug endpoints...")
        for endpoint in ["/api/debug/auth", "/api/admin/auth-status", "/debug/auth"]:
            try:
                response = await client.get(
                    f"{backend_url}{endpoint}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    print(f"   [FOUND] {endpoint}")
                    debug_data = response.json()
                    if 'auth_service_url' in debug_data:
                        print(f"   Auth Service URL: {debug_data['auth_service_url']}")
                    if 'service_id' in debug_data:
                        print(f"   Service ID: {debug_data['service_id']}")
                    if 'service_secret_configured' in debug_data:
                        print(f"   Service Secret Configured: {debug_data['service_secret_configured']}")
                    break
            except:
                pass
    
    print()
    print("=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print("""
Based on the backend's response patterns, we can infer:

1. If the backend is misconfigured, it likely:
   - Has wrong AUTH_SERVICE_URL environment variable
   - Missing SERVICE_SECRET for service-to-service auth
   - Network connectivity issues to auth service

2. Common staging issues:
   - Auth service URL should be: https://auth.staging.netrasystems.ai
   - Backend might be trying to use internal Cloud Run URL
   - Service authentication credentials may be missing

3. To fix:
   - Ensure AUTH_SERVICE_URL env var is set correctly
   - Verify SERVICE_SECRET is configured (if required)
   - Check network connectivity between services
""")

if __name__ == "__main__":
    asyncio.run(test_backend_auth_config())