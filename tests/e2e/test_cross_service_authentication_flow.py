"""
E2E Test: Cross-Service Authentication Flow

This test validates that authentication flows work correctly across all services
including token generation, validation, and propagation.

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Secure user authentication and authorization
- Value Impact: Ensures users can securely access all platform features
- Strategic/Revenue Impact: Authentication failures block user engagement and conversion
"""

import asyncio
import aiohttp
import pytest
import json
import time
from typing import Dict, Any, Optional
import uuid

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cross_service_authentication_flow():
    """Test complete authentication flow across all services.
    
    This test should FAIL until cross-service authentication is properly implemented.
    """
    
    # Test configuration
    auth_service_url = "http://localhost:8001"
    backend_service_url = "http://localhost:8000"
    frontend_service_url = "http://localhost:3000"
    
    # Test user credentials
    test_user = {
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }
    
    authentication_failures = []
    auth_token = None
    
    async with aiohttp.ClientSession() as session:
        # Step 1: User Registration
        print("🔐 Testing user registration...")
        try:
            registration_data = {
                "email": test_user["email"],
                "password": test_user["password"],
                "name": test_user["name"]
            }
            
            async with session.post(
                f"{auth_service_url}/register",
                json=registration_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 201:
                    response_text = await response.text()
                    authentication_failures.append(f"Registration failed: {response.status} - {response_text}")
                else:
                    registration_result = await response.json()
                    print(f"✅ User registration successful: {registration_result.get('user_id', 'N/A')}")
                    
        except Exception as e:
            authentication_failures.append(f"Registration request failed: {e}")
        
        # Step 2: User Login
        print("🔐 Testing user login...")
        try:
            login_data = {
                "email": test_user["email"],
                "password": test_user["password"]
            }
            
            async with session.post(
                f"{auth_service_url}/login",
                json=login_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    response_text = await response.text()
                    authentication_failures.append(f"Login failed: {response.status} - {response_text}")
                else:
                    login_result = await response.json()
                    auth_token = login_result.get("access_token")
                    if not auth_token:
                        authentication_failures.append("Login response missing access_token")
                    else:
                        print(f"✅ User login successful, token received")
                        
        except Exception as e:
            authentication_failures.append(f"Login request failed: {e}")
        
        # Step 3: Token Validation with Auth Service
        if auth_token:
            print("🔍 Testing token validation with auth service...")
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                async with session.get(
                    f"{auth_service_url}/me",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        authentication_failures.append(f"Auth service token validation failed: {response.status} - {response_text}")
                    else:
                        user_info = await response.json()
                        if user_info.get("email") != test_user["email"]:
                            authentication_failures.append(f"Token validation returned wrong user: {user_info.get('email')}")
                        else:
                            print(f"✅ Auth service token validation successful")
                            
            except Exception as e:
                authentication_failures.append(f"Auth service token validation failed: {e}")
        
        # Step 4: Cross-Service Token Propagation (Backend)
        if auth_token:
            print("🔗 Testing token propagation to backend service...")
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                async with session.get(
                    f"{backend_service_url}/api/user/profile",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        response_text = await response.text()
                        authentication_failures.append(f"Backend token validation failed: {response.status} - {response_text}")
                    else:
                        profile_info = await response.json()
                        print(f"✅ Backend service token validation successful")
                        
            except Exception as e:
                authentication_failures.append(f"Backend service token validation failed: {e}")
        
        # Step 5: Protected Resource Access
        if auth_token:
            print("📚 Testing protected resource access...")
            protected_endpoints = [
                f"{backend_service_url}/api/threads",
                f"{backend_service_url}/api/user/settings",
                f"{backend_service_url}/api/agents"
            ]
            
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            for endpoint in protected_endpoints:
                try:
                    async with session.get(
                        endpoint,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 401:
                            authentication_failures.append(f"Unauthorized access to {endpoint}")
                        elif response.status == 404:
                            # Endpoint might not exist, which is acceptable
                            pass
                        elif response.status >= 400:
                            response_text = await response.text()
                            authentication_failures.append(f"Protected resource error {endpoint}: {response.status} - {response_text}")
                        else:
                            print(f"✅ Protected resource accessible: {endpoint}")
                            
                except Exception as e:
                    authentication_failures.append(f"Protected resource access failed {endpoint}: {e}")
        
        # Step 6: Token Expiry Handling
        print("⏰ Testing token expiry handling...")
        if auth_token:
            # Test with malformed token
            malformed_token = auth_token[:-5] + "wrong"
            headers = {"Authorization": f"Bearer {malformed_token}"}
            
            try:
                async with session.get(
                    f"{auth_service_url}/me",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 401:
                        authentication_failures.append(f"Malformed token should return 401, got {response.status}")
                    else:
                        print("✅ Malformed token correctly rejected")
                        
            except Exception as e:
                authentication_failures.append(f"Token expiry test failed: {e}")
        
        # Step 7: User Logout
        if auth_token:
            print("🚪 Testing user logout...")
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                async with session.post(
                    f"{auth_service_url}/logout",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status not in [200, 204]:
                        response_text = await response.text()
                        authentication_failures.append(f"Logout failed: {response.status} - {response_text}")
                    else:
                        print("✅ User logout successful")
                        
                        # Verify token is invalidated
                        await asyncio.sleep(1)  # Brief delay
                        async with session.get(
                            f"{auth_service_url}/me",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status != 401:
                                authentication_failures.append(f"Token should be invalid after logout, got {response.status}")
                            else:
                                print("✅ Token correctly invalidated after logout")
                                
            except Exception as e:
                authentication_failures.append(f"Logout test failed: {e}")
        
        # Step 8: Cross-Origin Authentication (Frontend Integration)
        print("🌐 Testing cross-origin authentication...")
        try:
            # Test CORS headers for authentication endpoints
            async with session.options(
                f"{auth_service_url}/login",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                cors_headers = dict(response.headers)
                required_cors_headers = [
                    "Access-Control-Allow-Origin",
                    "Access-Control-Allow-Methods", 
                    "Access-Control-Allow-Headers"
                ]
                
                missing_cors = []
                for header in required_cors_headers:
                    if header not in cors_headers:
                        missing_cors.append(header)
                
                if missing_cors:
                    authentication_failures.append(f"Missing CORS headers: {missing_cors}")
                else:
                    print("✅ CORS headers configured correctly")
                    
        except Exception as e:
            authentication_failures.append(f"CORS test failed: {e}")
    
    # Analyze authentication flow results
    critical_failures = []
    warning_failures = []
    
    for failure in authentication_failures:
        if any(critical in failure.lower() for critical in ["registration failed", "login failed", "token validation failed"]):
            critical_failures.append(failure)
        else:
            warning_failures.append(failure)
    
    # Report results
    if critical_failures or warning_failures:
        failure_report = []
        
        if critical_failures:
            failure_report.append("🚨 Critical Authentication Failures:")
            for failure in critical_failures:
                failure_report.append(f"  - {failure}")
        
        if warning_failures:
            failure_report.append("⚠️ Authentication Warnings:")
            for failure in warning_failures:
                failure_report.append(f"  - {failure}")
        
        failure_report.append(f"\n📊 Summary: {len(critical_failures)} critical, {len(warning_failures)} warnings")
        
        pytest.fail(f"Cross-service authentication flow failed:\n" + "\n".join(failure_report))
    
    print("✅ Complete cross-service authentication flow working correctly")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_authentication_rate_limiting():
    """Test that authentication endpoints have proper rate limiting.
    
    This test should FAIL until rate limiting is properly implemented.
    """
    auth_service_url = "http://localhost:8001"
    
    # Test rapid login attempts
    rate_limit_failures = []
    
    async with aiohttp.ClientSession() as session:
        print("🚦 Testing authentication rate limiting...")
        
        # Attempt many rapid login requests
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        start_time = time.time()
        responses = []
        
        # Make 20 rapid requests
        tasks = []
        for i in range(20):
            task = session.post(
                f"{auth_service_url}/login",
                json=login_data,
                timeout=aiohttp.ClientTimeout(total=5)
            )
            tasks.append(task)
        
        try:
            # Execute all requests concurrently
            async_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            rate_limited_count = 0
            successful_count = 0
            
            for response in async_responses:
                if isinstance(response, Exception):
                    continue
                
                try:
                    if response.status == 429:  # Too Many Requests
                        rate_limited_count += 1
                    elif response.status == 401:  # Unauthorized (normal failed login)
                        successful_count += 1
                    
                    await response.close()
                except Exception:
                    pass
            
            elapsed_time = time.time() - start_time
            
            if rate_limited_count == 0:
                rate_limit_failures.append("No rate limiting detected for login attempts")
            
            if successful_count > 10:  # Should not allow this many rapid attempts
                rate_limit_failures.append(f"Too many rapid login attempts allowed: {successful_count}")
            
            print(f"📊 Rate limiting test: {rate_limited_count} rate-limited, {successful_count} processed in {elapsed_time:.2f}s")
            
        except Exception as e:
            rate_limit_failures.append(f"Rate limiting test failed: {e}")
    
    if rate_limit_failures:
        failure_report = ["🚦 Rate Limiting Failures:"]
        for failure in rate_limit_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"Authentication rate limiting failed:\n" + "\n".join(failure_report))
    
    print("✅ Authentication rate limiting working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])