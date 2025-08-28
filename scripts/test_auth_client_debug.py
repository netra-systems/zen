#!/usr/bin/env python3
"""
Debug the auth client validation issue
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set staging environment
os.environ['ENVIRONMENT'] = 'staging'
os.environ['AUTH_SERVICE_URL'] = 'https://auth.staging.netrasystems.ai'

import httpx
import json
from datetime import datetime

async def test_auth_client():
    """Test auth client directly"""
    
    print("=" * 60)
    print("AUTH CLIENT DEBUG TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # First get a fresh token from auth service
    auth_service_url = "https://auth.staging.netrasystems.ai"
    test_email = f"debug_{int(datetime.now().timestamp())}@example.com"
    test_password = "TestPassword123!"
    
    async with httpx.AsyncClient() as client:
        # Register user
        print("1. Registering test user...")
        response = await client.post(
            f"{auth_service_url}/auth/register",
            json={
                "email": test_email,
                "password": test_password,
                "confirm_password": test_password
            },
            timeout=10.0
        )
        if response.status_code != 201:
            print(f"   [FAIL] Registration failed: {response.text}")
            return
        print(f"   [OK] User registered")
        
        # Login
        print("\n2. Getting fresh token...")
        response = await client.post(
            f"{auth_service_url}/auth/login",
            json={
                "email": test_email,
                "password": test_password
            },
            timeout=10.0
        )
        if response.status_code != 200:
            print(f"   [FAIL] Login failed: {response.text}")
            return
        
        login_data = response.json()
        access_token = login_data.get("access_token")
        print(f"   [OK] Got token: {access_token[:50]}...")
        
        # Now test the auth client
        print("\n3. Testing auth client validation...")
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        
        auth_client = AuthServiceClient()
        print(f"   Auth service URL: {auth_client.settings.base_url}")
        print(f"   Service ID: {auth_client.service_id}")
        print(f"   Service Secret configured: {bool(auth_client.service_secret)}")
        
        # Test validation
        print("\n4. Calling validate_token_jwt...")
        try:
            result = await auth_client.validate_token_jwt(access_token)
            print(f"   Result: {result}")
            
            if result and result.get("valid"):
                print(f"   [OK] Token validated successfully")
                print(f"   User ID: {result.get('user_id')}")
                print(f"   Email: {result.get('email')}")
            else:
                print(f"   [FAIL] Token validation failed")
                print(f"   Result: {result}")
        except Exception as e:
            print(f"   [ERROR] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # Test direct remote validation
        print("\n5. Testing _validate_token_remote directly...")
        try:
            # Access private method for debugging
            result = await auth_client._validate_token_remote(access_token)
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   [ERROR] {type(e).__name__}: {e}")
        
        # Test manual validation request
        print("\n6. Testing manual validation request...")
        try:
            test_client = httpx.AsyncClient(
                base_url=auth_client.settings.base_url,
                timeout=httpx.Timeout(10.0)
            )
            
            headers = {}
            if auth_client.service_id and auth_client.service_secret:
                headers["X-Service-ID"] = auth_client.service_id
                headers["X-Service-Secret"] = auth_client.service_secret
            
            print(f"   Headers: {headers}")
            
            response = await test_client.post(
                "/auth/validate",
                json={"token": access_token},
                headers=headers
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            await test_client.aclose()
        except Exception as e:
            print(f"   [ERROR] {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    print("""
If validation is failing, check:

1. Auth service URL configuration in backend
2. Service authentication credentials (X-Service-ID, X-Service-Secret)
3. Network connectivity between backend and auth service
4. Circuit breaker state (might be open from previous failures)
5. Token format and encoding issues
""")

if __name__ == "__main__":
    asyncio.run(test_auth_client())