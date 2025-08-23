#!/usr/bin/env python3
"""
Test script for authentication flow end-to-end
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from netra_backend.app.clients.auth_client import auth_client


async def test_auth_flow():
    """Test the complete auth flow"""
    print("🔐 Testing Authentication Flow")
    print("=" * 50)
    
    # Test 1: Dev login to get tokens
    print("\n1. Testing dev login...")
    try:
        # Create a dev login request
        login_request = type('LoginRequest', (), {
            'email': 'dev@example.com',
            'password': None
        })()
        
        login_result = await auth_client.login(login_request)
        if login_result:
            print(f"✅ Login successful!")
            print(f"   Access token: {login_result.access_token[:50]}...")
            print(f"   User ID: {login_result.user_id}")
            print(f"   Role: {login_result.role}")
            
            # Test 2: Token validation
            print("\n2. Testing token validation...")
            validation_result = await auth_client.validate_token_jwt(login_result.access_token)
            if validation_result and validation_result.get("valid"):
                print("✅ Token validation successful!")
                print(f"   User ID: {validation_result.get('user_id')}")
                print(f"   Email: {validation_result.get('email')}")
                print(f"   Permissions: {validation_result.get('permissions')}")
            else:
                print("❌ Token validation failed")
                print(f"   Result: {validation_result}")
        else:
            print("❌ Login failed")
            
    except Exception as e:
        print(f"❌ Auth flow test failed: {e}")
        import traceback
        traceback.print_exc()

    # Test 3: Auth service health
    print("\n3. Testing auth service health...")
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8080/auth/health")
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Auth service health check passed!")
                print(f"   Status: {health_data.get('status')}")
                print(f"   Redis connected: {health_data.get('redis_connected')}")
                print(f"   Database connected: {health_data.get('database_connected')}")
            else:
                print(f"❌ Auth service health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Auth service health check failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
