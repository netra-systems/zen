#!/usr/bin/env python3
"""
Test authentication functionality on the backend service in staging
"""

import asyncio
import httpx
import json
import uuid
from typing import Dict, Any
from shared.isolated_environment import IsolatedEnvironment

BACKEND_URL = "https://api.staging.netrasystems.ai"

async def test_backend_auth_flow():
    """Test the complete auth flow using backend service endpoints"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 80)
        print("STAGING BACKEND AUTHENTICATION FLOW TEST")
        print("=" * 80)
        
        # Test auth config endpoint
        print("\n[1] Testing auth config endpoint")
        try:
            config_response = await client.get(f"{BACKEND_URL}/api/v1/auth/config")
            print(f"Auth config: {config_response.status_code}")
            if config_response.status_code == 200:
                config_data = config_response.json()
                print(f"Config data: {config_data}")
        except Exception as e:
            print(f"Config error: {e}")
        
        # Test registration
        print("\n[2] Testing user registration")
        user_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        
        register_payload = {
            "email": user_email,
            "password": password,
            "confirm_password": password
        }
        
        try:
            register_response = await client.post(
                f"{BACKEND_URL}/api/v1/auth/register",
                json=register_payload
            )
            print(f"Registration: {register_response.status_code}")
            if register_response.status_code in [200, 201]:
                print("Registration successful!")
                register_data = register_response.json()
                print(f"Registration data: {register_data}")
            else:
                print(f"Registration failed: {register_response.text}")
                return
        except Exception as e:
            print(f"Registration error: {e}")
            return
        
        # Test login
        print("\n[3] Testing user login")
        login_payload = {
            "email": user_email,
            "password": password
        }
        
        try:
            login_response = await client.post(
                f"{BACKEND_URL}/api/v1/auth/login",
                json=login_payload
            )
            print(f"Login: {login_response.status_code}")
            if login_response.status_code == 200:
                login_data = login_response.json()
                print("Login successful!")
                print(f"Login data keys: {list(login_data.keys())}")
                
                token = login_data.get("access_token")
                if not token:
                    print("No access_token in login response")
                    return
                
                print(f"Token length: {len(token)}")
                print(f"Token starts with: {token[:20]}...")
                
            else:
                print(f"Login failed: {login_response.text}")
                return
        except Exception as e:
            print(f"Login error: {e}")
            return
        
        # Test protected endpoint
        print("\n[4] Testing protected endpoint")
        try:
            protected_response = await client.get(
                f"{BACKEND_URL}/api/v1/auth/protected",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Protected endpoint: {protected_response.status_code}")
            if protected_response.status_code == 200:
                protected_data = protected_response.json()
                print(f"Protected data: {protected_data}")
            else:
                print(f"Protected endpoint failed: {protected_response.text}")
        except Exception as e:
            print(f"Protected endpoint error: {e}")
        
        # Test concurrent logins (race condition test)
        print("\n[5] Testing concurrent login race condition")
        async def concurrent_login():
            try:
                response = await client.post(
                    f"{BACKEND_URL}/api/v1/auth/login",
                    json=login_payload
                )
                return response
            except Exception as e:
                return e
        
        # Launch 5 concurrent login attempts
        tasks = [concurrent_login() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_logins = 0
        tokens = []
        
        for i, result in enumerate(results):
            if hasattr(result, 'status_code'):
                print(f"  Concurrent login {i+1}: {result.status_code}")
                if result.status_code == 200:
                    successful_logins += 1
                    try:
                        token_data = result.json()
                        if 'access_token' in token_data:
                            tokens.append(token_data['access_token'])
                    except:
                        pass
            else:
                print(f"  Concurrent login {i+1}: ERROR - {result}")
        
        print(f"\nConcurrent login results: {successful_logins}/{len(results)} successful")
        print(f"Tokens collected: {len(tokens)}")
        
        if len(tokens) > 1:
            unique_tokens = set(tokens)
            print(f"Unique tokens: {len(unique_tokens)}")
            if len(unique_tokens) < len(tokens):
                print("WARNING: Duplicate tokens detected - possible race condition")
            else:
                print("All tokens are unique - good!")
        
        # Test logout
        print("\n[6] Testing logout")
        try:
            logout_response = await client.post(
                f"{BACKEND_URL}/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Logout: {logout_response.status_code}")
            if logout_response.status_code in [200, 204]:
                print("Logout successful!")
            else:
                print(f"Logout response: {logout_response.text}")
        except Exception as e:
            print(f"Logout error: {e}")
        
        # Test token validation after logout
        print("\n[7] Testing token validation after logout")
        try:
            post_logout_response = await client.get(
                f"{BACKEND_URL}/api/v1/auth/protected",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Post-logout protected access: {post_logout_response.status_code}")
            if post_logout_response.status_code == 401:
                print("Good: Token invalidated after logout")
            elif post_logout_response.status_code == 200:
                print("WARNING: Token still valid after logout")
            else:
                print(f"Unexpected response: {post_logout_response.text}")
        except Exception as e:
            print(f"Post-logout test error: {e}")
        
        # Test malformed tokens
        print("\n[8] Testing malformed token handling")
        malformed_tokens = [
            "invalid-token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            "",
            "Bearer invalid",
        ]
        
        for i, bad_token in enumerate(malformed_tokens):
            try:
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/auth/protected",
                    headers={"Authorization": f"Bearer {bad_token}"}
                )
                print(f"  Malformed token {i+1}: {response.status_code}")
                if response.status_code != 401:
                    print(f"    WARNING: Expected 401, got {response.status_code}")
            except Exception as e:
                print(f"  Malformed token {i+1}: ERROR - {e}")

if __name__ == "__main__":
    asyncio.run(test_backend_auth_flow())