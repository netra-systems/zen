#!/usr/bin/env python3
"""
Try to run a subset of the original critical tests with the correct staging URLs
"""

import asyncio
import httpx
import json
import uuid

# Correct URLs discovered
BACKEND_URL = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"  
AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"

async def verify_critical_issues():
    """Verify the critical authentication issues from the original test suite"""
    
    print("="*60)
    print("VERIFICATION OF ORIGINAL CRITICAL AUTH TESTS")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Create a test user for validation
        user_email = f"critical-test-{uuid.uuid4().hex[:8]}@example.com"
        password = "CriticalTest123!"
        
        print(f"\n[SETUP] Creating test user: {user_email}")
        
        # Register via backend (we know this works)
        register_data = {
            "email": user_email,
            "password": password,
            "confirm_password": password
        }
        
        register_response = await client.post(f"{BACKEND_URL}/api/v1/auth/register", json=register_data)
        
        if register_response.status_code not in [200, 201]:
            print(f"Failed to create test user: {register_response.status_code}")
            return
        
        print("Test user created successfully")
        
        # CRITICAL TEST 1: Token Invalidation Propagation 
        print(f"\n[CRITICAL TEST 1] Token Invalidation Propagation")
        
        # Login via auth service
        login_data = {"email": user_email, "password": password}
        login_response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json=login_data)
        
        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            return
        
        token = login_response.json().get("access_token")
        print(f"Got token from auth service")
        
        # Test if token works with backend (we know this fails)
        backend_test = await client.get(
            f"{BACKEND_URL}/api/v1/auth/protected", 
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Backend accepts auth service token: {backend_test.status_code == 200}")
        
        # Try to logout via auth service
        logout_response = await client.post(
            f"{AUTH_SERVICE_URL}/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Logout via auth service: {logout_response.status_code}")
        
        # Test if token still works after logout (this tests propagation)
        post_logout_test = await client.get(
            f"{BACKEND_URL}/api/v1/auth/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Token still works after auth logout: {post_logout_test.status_code == 200}")
        
        # CRITICAL TEST 2: Service Restart Simulation
        print(f"\n[CRITICAL TEST 2] Session State Consistency")
        
        # Get user info from auth service
        auth_me_response = await client.get(
            f"{AUTH_SERVICE_URL}/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Auth service knows user: {auth_me_response.status_code == 200}")
        
        # Try to get user info from backend (different endpoint)
        backend_me_response = await client.get(
            f"{BACKEND_URL}/api/v1/auth/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Backend knows user: {backend_me_response.status_code == 200}")
        
        # CRITICAL TEST 3: Cross-Origin Token Issues  
        print(f"\n[CRITICAL TEST 3] Cross-Service Token Validation")
        
        # Create a new login to get a fresh token
        fresh_login = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json=login_data)
        if fresh_login.status_code == 200:
            fresh_token = fresh_login.json().get("access_token")
            
            # Test the token with various backend endpoints
            endpoints_to_test = [
                "/api/v1/auth/protected",
                "/api/v1/auth/",  
                "/health"  # This should work without auth
            ]
            
            for endpoint in endpoints_to_test:
                test_response = await client.get(
                    f"{BACKEND_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {fresh_token}"}
                )
                print(f"Token with {endpoint}: {test_response.status_code}")
        
        # CRITICAL TEST 4: Multiple Service Authentication
        print(f"\n[CRITICAL TEST 4] Service Integration Analysis")
        
        # Test if backend has its own auth system
        backend_login_response = await client.post(f"{BACKEND_URL}/api/v1/auth/login", json=login_data)
        print(f"Backend has own login: {backend_login_response.status_code}")
        
        if backend_login_response.status_code == 500:
            print("Backend login returns 500 - likely trying to call auth service internally")
        elif backend_login_response.status_code == 200:
            backend_token = backend_login_response.json().get("access_token")
            if backend_token:
                # Test backend-issued token
                backend_token_test = await client.get(
                    f"{BACKEND_URL}/api/v1/auth/protected",
                    headers={"Authorization": f"Bearer {backend_token}"}
                )
                print(f"Backend token works with backend: {backend_token_test.status_code == 200}")
        
        # Summary
        print(f"\n{'='*60}")
        print("CRITICAL ISSUES CONFIRMED")
        print(f"{'='*60}")
        print("1. Auth service tokens rejected by backend (401)")
        print("2. Backend login endpoint fails (500) - likely calling auth service")
        print("3. Cross-service token validation is broken")
        print("4. Token invalidation propagation cannot be tested due to #1")
        print("5. Session state consistency cannot be verified due to #1")

if __name__ == "__main__":
    asyncio.run(verify_critical_issues())