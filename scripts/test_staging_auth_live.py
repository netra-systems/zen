#!/usr/bin/env python3
"""
Test authentication flow on staging with fresh tokens
"""
import asyncio
import httpx
import json
from datetime import datetime
import time
import base64

async def test_auth_flow():
    """Test complete authentication flow on staging"""
    
    print("=" * 60)
    print("STAGING AUTHENTICATION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Test credentials
    test_email = f"test_{int(time.time())}@example.com"
    test_password = "TestPassword123!"
    
    auth_service_url = "https://auth.staging.netrasystems.ai"
    backend_url = "https://api.staging.netrasystems.ai"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Register a new user
        print("1. Registering new user...")
        print(f"   Email: {test_email}")
        
        try:
            response = await client.post(
                f"{auth_service_url}/auth/register",
                json={
                    "email": test_email,
                    "password": test_password,
                    "confirm_password": test_password
                },
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 201:
                print("   [OK] User registered successfully")
                register_data = response.json()
                print(f"   User ID: {register_data.get('user_id')}")
            else:
                print(f"   [FAIL] Registration failed")
                print(f"   Response: {response.text}")
                return
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        print()
        
        # Step 2: Login to get JWT token
        print("2. Logging in to get JWT token...")
        
        try:
            response = await client.post(
                f"{auth_service_url}/auth/login",
                json={
                    "email": test_email,
                    "password": test_password
                },
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   [OK] Login successful")
                login_data = response.json()
                access_token = login_data.get("access_token")
                refresh_token = login_data.get("refresh_token")
                print(f"   Access token received: {access_token[:50]}...")
                
                # Decode JWT to check expiry
                parts = access_token.split('.')
                if len(parts) == 3:
                    payload_raw = parts[1]
                    # Add padding if needed
                    padding = 4 - len(payload_raw) % 4
                    if padding != 4:
                        payload_raw += '=' * padding
                    try:
                        payload_decoded = base64.urlsafe_b64decode(payload_raw)
                        payload = json.loads(payload_decoded)
                        exp_time = payload.get('exp', 0)
                        iat_time = payload.get('iat', 0)
                        lifetime = exp_time - iat_time if exp_time and iat_time else 0
                        print(f"   Token lifetime: {lifetime} seconds")
                        print(f"   Expires at: {datetime.fromtimestamp(exp_time)}")
                    except Exception as e:
                        print(f"   Could not decode token: {e}")
            else:
                print(f"   [FAIL] Login failed")
                print(f"   Response: {response.text}")
                return
        except Exception as e:
            print(f"   [ERROR] {e}")
            return
        
        print()
        
        # Step 3: Validate token directly with auth service
        print("3. Validating token with auth service...")
        
        try:
            response = await client.post(
                f"{auth_service_url}/auth/validate",
                json={"token": access_token},
                headers={"Content-Type": "application/json"},
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   [OK] Token validated successfully")
                validation_data = response.json()
                print(f"   User ID: {validation_data.get('user_id')}")
                print(f"   Email: {validation_data.get('email')}")
            else:
                print(f"   [FAIL] Validation failed")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        print()
        
        # Step 4: Test backend API with token
        print("4. Testing backend API with token...")
        
        try:
            response = await client.get(
                f"{backend_url}/api/threads",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                },
                params={"limit": 10, "offset": 0},
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   [OK] Backend accepted token")
                data = response.json()
                print(f"   Threads count: {len(data.get('threads', []))}")
            elif response.status_code == 401:
                print("   [FAIL] Backend rejected token (401)")
                print(f"   Response: {response.text}")
                print("\n   Headers received:")
                for key, value in response.headers.items():
                    if key.lower().startswith(('x-', 'www-')):
                        print(f"     {key}: {value}")
            elif response.status_code == 403:
                print("   [WARNING] Backend returned 403 - Forbidden")
                print("   This might be expected if the user lacks permissions")
                print(f"   Response: {response.text}")
            else:
                print(f"   [FAIL] Unexpected status code: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        print()
        
        # Step 5: Test WebSocket endpoint
        print("5. Testing WebSocket endpoint authentication...")
        
        try:
            ws_url = f"wss://api.staging.netrasystems.ai/ws"
            # Note: httpx doesn't support WebSocket, so we'll test the HTTP upgrade
            response = await client.get(
                f"{backend_url}/ws",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Version": "13",
                    "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="
                },
                timeout=10.0
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 426:
                print("   [OK] WebSocket upgrade required (expected)")
            elif response.status_code == 401:
                print("   [FAIL] WebSocket auth failed")
                print(f"   Response: {response.text}")
            else:
                print(f"   Status code: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        print()
        
        # Step 6: Test health endpoints
        print("6. Testing service health endpoints...")
        
        for service_name, url in [
            ("Auth Service", f"{auth_service_url}/health"),
            ("Backend", f"{backend_url}/health"),
        ]:
            try:
                response = await client.get(url, timeout=5.0)
                print(f"   {service_name}: {response.status_code}")
                if response.status_code == 200:
                    print(f"     [OK] Service healthy")
            except Exception as e:
                print(f"   {service_name}: [ERROR] {e}")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
If authentication is failing at step 4 (Backend API), check:

1. Backend Service Configuration:
   - SERVICE_SECRET environment variable is set correctly
   - AUTH_SERVICE_URL points to https://auth.staging.netrasystems.ai
   
2. Auth Service Communication:
   - Backend can reach auth service (network/firewall)
   - Service-to-service authentication is configured
   
3. Token Validation:
   - Token format and claims are correct
   - Backend is using correct validation endpoint
   
4. User Database:
   - User exists in backend database
   - User permissions are set correctly
""")

if __name__ == "__main__":
    asyncio.run(test_auth_flow())