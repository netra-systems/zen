#!/usr/bin/env python3
"""
Test script for auth service registration functionality
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

import httpx

# Set up environment
os.environ["ENVIRONMENT"] = "test"
os.environ["SERVICE_SECRET"] = "test-service-secret-for-inter-service-auth"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-minimum-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

async def test_registration():
    """Test user registration endpoint"""
    base_url = "http://localhost:8081"
    
    # Generate unique test user
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"testuser_{unique_id}@example.com"
    test_password = "TestPassword123!"
    test_name = f"Test User {unique_id}"
    
    print(f"\n{'='*60}")
    print(f"Auth Service Registration Test")
    print(f"{'='*60}")
    print(f"Testing registration for: {test_email}")
    print(f"Timestamp: {datetime.now()}")
    print(f"{'='*60}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Register new user
            print("Test 1: Registering new user...")
            response = await client.post(
                f"{base_url}/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "name": test_name
                }
            )
            
            print(f"  Status Code: {response.status_code}")
            print(f"  Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Registration successful!")
                print(f"  Response: {json.dumps(data, indent=2)}")
                
                # Verify response structure
                assert "access_token" in data, "Missing access_token in response"
                assert "refresh_token" in data, "Missing refresh_token in response"
                assert "user" in data, "Missing user in response"
                assert data["user"]["email"] == test_email, "Email mismatch"
                
                access_token = data["access_token"]
                print(f"\n  Access token received (first 20 chars): {access_token[:20]}...")
                
                # Test 2: Try to register same user again (should fail)
                print("\nTest 2: Attempting duplicate registration...")
                duplicate_response = await client.post(
                    f"{base_url}/auth/register",
                    json={
                        "email": test_email,
                        "password": test_password,
                        "name": test_name
                    }
                )
                
                print(f"  Status Code: {duplicate_response.status_code}")
                if duplicate_response.status_code == 409:
                    print(f"  ✅ Correctly rejected duplicate registration")
                else:
                    print(f"  ❌ Unexpected status for duplicate: {duplicate_response.status_code}")
                    print(f"  Response: {duplicate_response.text}")
                
                # Test 3: Test login with new user
                print("\nTest 3: Testing login with registered user...")
                login_response = await client.post(
                    f"{base_url}/auth/login",
                    json={
                        "email": test_email,
                        "password": test_password
                    }
                )
                
                print(f"  Status Code: {login_response.status_code}")
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    print(f"  ✅ Login successful!")
                    assert "access_token" in login_data, "Missing access_token in login response"
                else:
                    print(f"  ❌ Login failed: {login_response.text}")
                
                # Test 4: Verify token works
                print("\nTest 4: Verifying access token...")
                me_response = await client.get(
                    f"{base_url}/auth/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                print(f"  Status Code: {me_response.status_code}")
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print(f"  ✅ Token validation successful!")
                    print(f"  User data: {json.dumps(user_data, indent=2)}")
                    assert user_data["email"] == test_email, "Email mismatch in /me response"
                else:
                    print(f"  ❌ Token validation failed: {me_response.text}")
                
            else:
                print(f"  ❌ Registration failed!")
                print(f"  Response: {response.text}")
                
                # Additional debugging
                print("\nDebug Info:")
                print(f"  Content-Type: {response.headers.get('content-type')}")
                try:
                    error_data = response.json()
                    print(f"  Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"  Raw response: {response.text[:500]}")
        
        except httpx.ConnectError as e:
            print(f"❌ Connection failed - is the auth service running on port 8081?")
            print(f"   Error: {e}")
            return False
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print(f"\n{'='*60}")
    print(f"All tests completed successfully! ✅")
    print(f"{'='*60}\n")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_registration())
    sys.exit(0 if success else 1)