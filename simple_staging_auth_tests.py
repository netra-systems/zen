#!/usr/bin/env python3
"""
Simple staging authentication tests without Unicode issues
"""

import asyncio
import httpx
import json
import uuid
import time

BACKEND_URL = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"

async def test_all():
    """Run comprehensive staging auth tests"""
    results = []
    
    print("="*60)
    print("STAGING AUTHENTICATION TESTS")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Auth service health
        print("\n[TEST 1] Auth Service Health")
        try:
            response = await client.get(f"{AUTH_SERVICE_URL}/auth/health")
            print(f"Auth health: {response.status_code}")
            if response.status_code == 200:
                print(f"Health data: {response.json()}")
            results.append(("Auth Health", response.status_code == 200))
        except Exception as e:
            print(f"Auth health error: {e}")
            results.append(("Auth Health", False))
        
        # Test 2: Backend auth config
        print("\n[TEST 2] Backend Auth Config")
        try:
            response = await client.get(f"{BACKEND_URL}/api/v1/auth/config")
            print(f"Backend config: {response.status_code}")
            if response.status_code == 200:
                config = response.json()
                print(f"Auth endpoints configured: {len(config.get('endpoints', {}))}")
                results.append(("Backend Config", True))
            else:
                results.append(("Backend Config", False))
        except Exception as e:
            print(f"Backend config error: {e}")
            results.append(("Backend Config", False))
        
        # Test 3: User registration flow
        print("\n[TEST 3] User Registration")
        user_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPass123!"
        
        register_data = {
            "email": user_email,
            "password": password,
            "confirm_password": password
        }
        
        # Try backend registration
        try:
            response = await client.post(f"{BACKEND_URL}/api/v1/auth/register", json=register_data)
            print(f"Backend registration: {response.status_code}")
            if response.status_code in [200, 201]:
                print("Registration successful via backend")
                registered = True
            else:
                print(f"Registration error: {response.text[:200]}")
                registered = False
            results.append(("Registration", registered))
        except Exception as e:
            print(f"Registration error: {e}")
            results.append(("Registration", False))
            registered = False
        
        # Test 4: Login flow
        print("\n[TEST 4] User Login")
        if registered:
            try:
                login_data = {"email": user_email, "password": password}
                
                # Try auth service login
                response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json=login_data)
                print(f"Auth service login: {response.status_code}")
                
                if response.status_code == 200:
                    token_data = response.json()
                    token = token_data.get("access_token")
                    if token:
                        print(f"Got token: {len(token)} chars")
                        results.append(("Login", True))
                    else:
                        print("No access token in response")
                        results.append(("Login", False))
                        token = None
                else:
                    print(f"Login failed: {response.text[:200]}")
                    results.append(("Login", False))
                    token = None
                    
                # Also try backend login
                backend_login_response = await client.post(f"{BACKEND_URL}/api/v1/auth/login", json=login_data)
                print(f"Backend login: {backend_login_response.status_code}")
                
            except Exception as e:
                print(f"Login error: {e}")
                results.append(("Login", False))
                token = None
        else:
            print("Skipping login - registration failed")
            results.append(("Login", False))
            token = None
        
        # Test 5: Token validation
        print("\n[TEST 5] Cross-Service Token Validation")
        if token:
            try:
                # Test with backend
                response = await client.get(
                    f"{BACKEND_URL}/api/v1/auth/protected",
                    headers={"Authorization": f"Bearer {token}"}
                )
                print(f"Backend token validation: {response.status_code}")
                backend_valid = response.status_code == 200
                
                # Test with auth service
                response = await client.get(
                    f"{AUTH_SERVICE_URL}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )
                print(f"Auth service token verification: {response.status_code}")
                auth_valid = response.status_code == 200
                
                results.append(("Token Validation", backend_valid and auth_valid))
                
            except Exception as e:
                print(f"Token validation error: {e}")
                results.append(("Token Validation", False))
        else:
            print("Skipping - no token available")
            results.append(("Token Validation", False))
        
        # Test 6: Concurrent login race condition
        print("\n[TEST 6] Concurrent Login Race Condition")
        if registered:
            try:
                login_data = {"email": user_email, "password": password}
                
                async def login_attempt():
                    try:
                        response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json=login_data)
                        return response
                    except:
                        return None
                
                # 5 concurrent attempts
                tasks = [login_attempt() for _ in range(5)]
                concurrent_results = await asyncio.gather(*tasks)
                
                successful = 0
                tokens = []
                
                for result in concurrent_results:
                    if result and result.status_code == 200:
                        successful += 1
                        try:
                            token_data = result.json()
                            if 'access_token' in token_data:
                                tokens.append(token_data['access_token'])
                        except:
                            pass
                
                print(f"Concurrent logins: {successful}/5 successful")
                print(f"Tokens collected: {len(tokens)}")
                
                if len(tokens) > 1:
                    unique_tokens = set(tokens)
                    print(f"Unique tokens: {len(unique_tokens)}")
                    if len(unique_tokens) < len(tokens):
                        print("WARNING: Duplicate tokens detected!")
                        results.append(("Race Condition", False))
                    else:
                        results.append(("Race Condition", True))
                else:
                    results.append(("Race Condition", True))
                
            except Exception as e:
                print(f"Race condition test error: {e}")
                results.append(("Race Condition", False))
        else:
            print("Skipping - no registered user")
            results.append(("Race Condition", False))
        
        # Test 7: Invalid token handling
        print("\n[TEST 7] Invalid Token Handling")
        try:
            invalid_tokens = ["invalid", "eyJ.invalid.token", ""]
            all_rejected = True
            
            for invalid_token in invalid_tokens:
                if invalid_token:  # Skip empty token
                    response = await client.get(
                        f"{BACKEND_URL}/api/v1/auth/protected",
                        headers={"Authorization": f"Bearer {invalid_token}"}
                    )
                    if response.status_code != 401:
                        all_rejected = False
                        print(f"Invalid token '{invalid_token}' accepted: {response.status_code}")
            
            if all_rejected:
                print("All invalid tokens properly rejected")
                results.append(("Invalid Token Handling", True))
            else:
                results.append(("Invalid Token Handling", False))
                
        except Exception as e:
            print(f"Invalid token test error: {e}")
            results.append(("Invalid Token Handling", False))
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:30} {status}")
        if success:
            passed += 1
    
    print(f"\nPassed: {passed}/{total}")
    print(f"Auth Service: {AUTH_SERVICE_URL}")
    print(f"Backend:      {BACKEND_URL}")
    
    if passed < total:
        print(f"\nFAILED TESTS: {total - passed}")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(test_all())
    if not success:
        exit(1)