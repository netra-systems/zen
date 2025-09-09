#!/usr/bin/env python3
"""
Final Critical Authentication Cross-System E2E Tests for Staging Environment

Uses the correct auth service endpoints discovered from the backend config.
"""

import asyncio
import httpx
import json
import uuid
import time
from datetime import datetime

# Correct endpoints discovered from backend config
BACKEND_URL = "https://api.staging.netrasystems.ai"
AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"

class StagingAuthTests:
    """Authentication tests for staging environment with real endpoints"""
    
    def __init__(self):
        self.results = []
    
    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "!"
        print(f"{status_symbol} {test_name}: {status} - {details}")
    
    async def test_auth_service_availability(self):
        """Test 1: Auth service availability"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(f"{AUTH_SERVICE_URL}/auth/health")
                if response.status_code == 200:
                    health_data = response.json()
                    self.log_result("Auth Service Availability", "PASS", f"Health check: {health_data}")
                else:
                    self.log_result("Auth Service Availability", "FAIL", f"Health check failed: {response.status_code}")
            except Exception as e:
                self.log_result("Auth Service Availability", "ERROR", str(e))
    
    async def test_complete_auth_flow(self):
        """Test 2: Complete authentication flow"""
        user_email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        password = "TestPassword123!"  # Meet password requirements
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Register user with auth service
                register_payload = {
                    "email": user_email,
                    "password": password,
                    "confirm_password": password
                }
                
                # Try different registration endpoints
                registration_urls = [
                    f"{AUTH_SERVICE_URL}/auth/register",
                    f"{BACKEND_URL}/api/v1/auth/register"
                ]
                
                registered = False
                for reg_url in registration_urls:
                    try:
                        register_response = await client.post(reg_url, json=register_payload)
                        if register_response.status_code in [200, 201]:
                            self.log_result("User Registration", "PASS", f"Registered via {reg_url}")
                            registered = True
                            break
                        else:
                            print(f"Registration attempt {reg_url}: {register_response.status_code}")
                    except Exception as e:
                        print(f"Registration attempt {reg_url}: ERROR - {e}")
                
                if not registered:
                    self.log_result("User Registration", "FAIL", "Could not register user with any endpoint")
                    return None
                
                # Login with auth service
                login_payload = {
                    "email": user_email,
                    "password": password
                }
                
                login_response = await client.post(f"{AUTH_SERVICE_URL}/auth/login", json=login_payload)
                
                if login_response.status_code == 200:
                    login_data = login_response.json()
                    token = login_data.get("access_token")
                    self.log_result("User Login", "PASS", f"Got token: {token[:20]}..." if token else "No token")
                    return token
                else:
                    self.log_result("User Login", "FAIL", f"Login failed: {login_response.status_code} - {login_response.text}")
                    return None
                    
            except Exception as e:
                self.log_result("Complete Auth Flow", "ERROR", str(e))
                return None
    
    async def test_cross_service_token_validation(self, token):
        """Test 3: Cross-service token validation"""
        if not token:
            self.log_result("Cross-Service Token Validation", "SKIP", "No token available")
            return
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Test token with backend protected endpoint
                backend_response = await client.get(
                    f"{BACKEND_URL}/api/v1/auth/protected",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if backend_response.status_code == 200:
                    self.log_result("Cross-Service Token Validation", "PASS", "Token valid in backend")
                else:
                    self.log_result("Cross-Service Token Validation", "FAIL", 
                                  f"Backend rejected token: {backend_response.status_code}")
                
                # Test token with auth service
                auth_response = await client.get(
                    f"{AUTH_SERVICE_URL}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                print(f"Auth service verification: {auth_response.status_code}")
                
            except Exception as e:
                self.log_result("Cross-Service Token Validation", "ERROR", str(e))
    
    async def test_concurrent_login_race_condition(self):
        """Test 4: Concurrent login race condition"""
        user_email = f"race-{uuid.uuid4().hex[:8]}@example.com"
        password = "RaceTest123!"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # First register the user
                register_payload = {
                    "email": user_email,
                    "password": password,
                    "confirm_password": password
                }
                
                # Try backend registration first
                register_response = await client.post(
                    f"{BACKEND_URL}/api/v1/auth/register",
                    json=register_payload
                )
                
                if register_response.status_code not in [200, 201]:
                    self.log_result("Race Condition Test Setup", "FAIL", "Could not register test user")
                    return
                
                # Concurrent login function
                async def login_attempt():
                    try:
                        response = await client.post(
                            f"{AUTH_SERVICE_URL}/auth/login",
                            json={"email": user_email, "password": password}
                        )
                        return response
                    except Exception as e:
                        return e
                
                # Launch 5 concurrent login attempts
                tasks = [login_attempt() for _ in range(5)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful_tokens = []
                for result in results:
                    if hasattr(result, 'status_code') and result.status_code == 200:
                        try:
                            token_data = result.json()
                            if 'access_token' in token_data:
                                successful_tokens.append(token_data['access_token'])
                        except:
                            continue
                
                # Analyze results
                if len(successful_tokens) == 0:
                    self.log_result("Concurrent Login Race", "FAIL", "No successful logins")
                elif len(successful_tokens) == 1:
                    self.log_result("Concurrent Login Race", "PASS", "Single token issued correctly")
                else:
                    unique_tokens = set(successful_tokens)
                    if len(unique_tokens) < len(successful_tokens):
                        self.log_result("Concurrent Login Race", "CRITICAL", 
                                      f"Duplicate tokens: {len(successful_tokens)} total, {len(unique_tokens)} unique")
                    else:
                        self.log_result("Concurrent Login Race", "WARN", 
                                      f"Multiple unique tokens: {len(successful_tokens)}")
                
            except Exception as e:
                self.log_result("Concurrent Login Race", "ERROR", str(e))
    
    async def test_token_invalidation(self, token):
        """Test 5: Token invalidation"""
        if not token:
            self.log_result("Token Invalidation", "SKIP", "No token available")
            return
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Verify token works first
                initial_response = await client.get(
                    f"{BACKEND_URL}/api/v1/auth/protected",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if initial_response.status_code != 200:
                    self.log_result("Token Invalidation", "SKIP", "Token already invalid")
                    return
                
                # Attempt logout
                logout_response = await client.post(
                    f"{AUTH_SERVICE_URL}/auth/logout",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                print(f"Logout response: {logout_response.status_code}")
                
                # Test token after logout
                post_logout_response = await client.get(
                    f"{BACKEND_URL}/api/v1/auth/protected",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if post_logout_response.status_code == 401:
                    self.log_result("Token Invalidation", "PASS", "Token properly invalidated")
                else:
                    self.log_result("Token Invalidation", "FAIL", 
                                  f"Token still valid after logout: {post_logout_response.status_code}")
                
            except Exception as e:
                self.log_result("Token Invalidation", "ERROR", str(e))
    
    async def test_malformed_token_handling(self):
        """Test 6: Malformed token handling"""
        malformed_tokens = [
            "invalid-token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid.signature",
            "",
            "Bearer",
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            all_rejected = True
            
            for token in malformed_tokens:
                try:
                    # Test with backend
                    backend_response = await client.get(
                        f"{BACKEND_URL}/api/v1/auth/protected",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    # Test with auth service
                    auth_response = await client.get(
                        f"{AUTH_SERVICE_URL}/auth/verify",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    if backend_response.status_code != 401 or auth_response.status_code != 401:
                        all_rejected = False
                        print(f"Malformed token '{token[:10]}' - Backend: {backend_response.status_code}, Auth: {auth_response.status_code}")
                        
                except Exception as e:
                    print(f"Error testing malformed token: {e}")
            
            if all_rejected:
                self.log_result("Malformed Token Handling", "PASS", "All malformed tokens properly rejected")
            else:
                self.log_result("Malformed Token Handling", "FAIL", "Some malformed tokens were accepted")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("STAGING AUTHENTICATION E2E TEST RESULTS SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        critical = sum(1 for r in self.results if r['status'] == 'CRITICAL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        skipped = sum(1 for r in self.results if r['status'] == 'SKIP')
        
        print(f"Total Tests: {len(self.results)}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"! Errors: {errors}")
        print(f"🔥 Critical: {critical}")
        print(f"⚠ Warnings: {warnings}")
        print(f"- Skipped: {skipped}")
        
        print(f"\nAuth Service URL: {AUTH_SERVICE_URL}")
        print(f"Backend URL: {BACKEND_URL}")
        
        if failed > 0 or critical > 0:
            print(f"\n🚨 CRITICAL ISSUES FOUND:")
            for result in self.results:
                if result['status'] in ['FAIL', 'CRITICAL']:
                    print(f"  - {result['test']}: {result['details']}")
        
        return failed + critical == 0

async def run_all_tests():
    """Run all staging authentication tests"""
    tester = StagingAuthTests()
    
    print("=" * 80)
    print("STAGING AUTHENTICATION CROSS-SYSTEM E2E TESTS")
    print("=" * 80)
    
    # Test 1: Service availability
    await tester.test_auth_service_availability()
    
    # Test 2: Complete auth flow and get token
    token = await tester.test_complete_auth_flow()
    
    # Test 3: Cross-service token validation
    await tester.test_cross_service_token_validation(token)
    
    # Test 4: Concurrent login race condition
    await tester.test_concurrent_login_race_condition()
    
    # Test 5: Token invalidation
    await tester.test_token_invalidation(token)
    
    # Test 6: Malformed token handling
    await tester.test_malformed_token_handling()
    
    # Print summary
    success = tester.print_summary()
    return success

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    if not success:
        exit(1)