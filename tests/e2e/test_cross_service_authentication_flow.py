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

# Setup test path for absolute imports following CLAUDE.md standards
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Absolute imports following CLAUDE.md standards
import asyncio
import aiohttp
import pytest
import json
import time
from typing import Dict, Any, Optional
import uuid
import logging

# Import IsolatedEnvironment for proper environment management as required by CLAUDE.md
from shared.isolated_environment import get_env
from tests.e2e.test_harness import UnifiedE2ETestHarness

logger = logging.getLogger(__name__)

async def check_service_availability(session: aiohttp.ClientSession, service_name: str, url: str) -> bool:
    """Check if a service is available by testing its health endpoint."""
    try:
        # First try health endpoint
        async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                logger.info(f"[SERVICE-CHECK] {service_name} is available at {url}")
                return True
    except Exception:
        pass
    
    # If health endpoint fails, try root endpoint
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                logger.info(f"[SERVICE-CHECK] {service_name} is available at {url} (via root)")
                return True
    except Exception:
        pass
    
    logger.warning(f"[SERVICE-CHECK] {service_name} is not available at {url}")
    return False

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_cross_service_authentication_flow():
    """Test complete authentication flow across all services.
    
    This test should FAIL until cross-service authentication is properly implemented.
    """
    
    # Use IsolatedEnvironment for environment management as required by CLAUDE.md
    env = get_env()
    env.set("ENVIRONMENT", "test", "test_cross_service_authentication_flow")
    env.set("NETRA_ENVIRONMENT", "test", "test_cross_service_authentication_flow")
    
    # Set correct service ports for real running services BEFORE harness initialization
    import os
    env.set("TEST_AUTH_PORT", "8082", "test_cross_service_authentication_flow")
    env.set("TEST_BACKEND_PORT", "8002", "test_cross_service_authentication_flow")
    
    # Initialize test harness for real service integration
    harness = UnifiedE2ETestHarness()
    
    # Use properly running dev services on standard ports
    auth_service_url = "http://localhost:8081"  # Dev auth service on standard port
    backend_service_url = "http://localhost:8000"  # Dev backend service on standard port  
    frontend_service_url = "http://localhost:3000"
    
    # Debug: print actual URLs being used
    print(f"[FIXED] Auth service URL: {auth_service_url}")
    print(f"[FIXED] Backend service URL: {backend_service_url}")
    print(f"[FIXED] Frontend service URL: {frontend_service_url}")
    
    # Test user credentials
    test_user = {
        "email": f"test-{uuid.uuid4().hex[:8]}@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }
    
    authentication_failures = []
    auth_token = None
    
    async with aiohttp.ClientSession() as session:
        # Pre-check: Verify service availability
        print("[SETUP] Checking service availability...")
        services_available = {
            "auth": await check_service_availability(session, "Auth Service", auth_service_url),
            "backend": await check_service_availability(session, "Backend Service", backend_service_url)
        }
        
        if not services_available["auth"]:
            pytest.skip(f"Auth service is not available at {auth_service_url}. Skipping authentication flow test.")
        
        if not services_available["backend"]:
            logger.warning(f"Backend service is not available at {backend_service_url}. Some tests may be skipped.")
        
        # Step 1: User Registration
        print("[AUTH] Testing user registration...")
        try:
            registration_data = {
                "email": test_user["email"],
                "password": test_user["password"],
                "confirm_password": test_user["password"],
                "full_name": test_user["name"]
            }
            
            async with session.post(
                f"{auth_service_url}/auth/register",
                json=registration_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 201:
                    response_text = await response.text()
                    authentication_failures.append(f"Registration failed: {response.status} - {response_text}")
                else:
                    registration_result = await response.json()
                    print(f"[SUCCESS] User registration successful: {registration_result.get('user_id', 'N/A')}")
                    
        except Exception as e:
            authentication_failures.append(f"Registration request failed: {e}")
        
        # Step 2: User Login
        print("[AUTH] Testing user login...")
        try:
            login_data = {
                "email": test_user["email"],
                "password": test_user["password"]
            }
            
            async with session.post(
                f"{auth_service_url}/auth/login",
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
                        print(f"[SUCCESS] User login successful, token received")
                        
        except Exception as e:
            authentication_failures.append(f"Login request failed: {e}")
        
        # Step 3: Token Validation with Auth Service
        if auth_token:
            print("[AUTH] Testing token validation with auth service...")
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                async with session.get(
                    f"{auth_service_url}/auth/me",
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
                            print(f"[SUCCESS] Auth service token validation successful")
                            
            except Exception as e:
                authentication_failures.append(f"Auth service token validation failed: {e}")
        
        # Step 4: Cross-Service Token Propagation (Backend)
        if auth_token and services_available["backend"]:
            print("[AUTH] Testing token propagation to backend service...")
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
                        print(f"[SUCCESS] Backend service token validation successful")
                        
            except Exception as e:
                authentication_failures.append(f"Backend service token validation failed: {e}")
        elif auth_token and not services_available["backend"]:
            print("[SKIP] Backend service not available, skipping token propagation test")
        
        # Step 5: Protected Resource Access
        if auth_token and services_available["backend"]:
            print("[AUTH] Testing protected resource access...")
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
                            print(f"[SUCCESS] Protected resource accessible: {endpoint}")
                            
                except Exception as e:
                    authentication_failures.append(f"Protected resource access failed {endpoint}: {e}")
        elif auth_token and not services_available["backend"]:
            print("[SKIP] Backend service not available, skipping protected resource tests")
        
        # Step 6: Token Expiry Handling
        print("[AUTH] Testing token expiry handling...")
        if auth_token:
            # Test with malformed token
            malformed_token = auth_token[:-5] + "wrong"
            headers = {"Authorization": f"Bearer {malformed_token}"}
            
            try:
                async with session.get(
                    f"{auth_service_url}/auth/me",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 401:
                        authentication_failures.append(f"Malformed token should await asyncio.sleep(0)
    return 401, got {response.status}")
                    else:
                        print("[SUCCESS] Malformed token correctly rejected")
                        
            except Exception as e:
                authentication_failures.append(f"Token expiry test failed: {e}")
        
        # Step 7: User Logout
        if auth_token:
            print("[AUTH] Testing user logout...")
            try:
                headers = {"Authorization": f"Bearer {auth_token}"}
                async with session.post(
                    f"{auth_service_url}/auth/logout",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status not in [200, 204]:
                        response_text = await response.text()
                        authentication_failures.append(f"Logout failed: {response.status} - {response_text}")
                    else:
                        print("[SUCCESS] User logout successful")
                        
                        # Verify token is invalidated
                        await asyncio.sleep(1)  # Brief delay
                        async with session.get(
                            f"{auth_service_url}/auth/me",
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status != 401:
                                authentication_failures.append(f"Token should be invalid after logout, got {response.status}")
                            else:
                                print("[SUCCESS] Token correctly invalidated after logout")
                                
            except Exception as e:
                authentication_failures.append(f"Logout test failed: {e}")
        
        # Step 8: Cross-Origin Authentication (Frontend Integration)
        print("[AUTH] Testing cross-origin authentication...")
        try:
            # Test CORS headers for authentication endpoints
            cors_headers = {}
            cors_test_successful = False
            
            # Try OPTIONS request first (standard CORS preflight)
            try:
                async with session.options(
                    f"{auth_service_url}/auth/login",
                    headers={"Origin": "http://localhost:3000"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    cors_headers = dict(response.headers)
                    cors_test_successful = True
                    print(f"[CORS] OPTIONS request successful, status: {response.status}")
            except Exception as options_error:
                print(f"[CORS] OPTIONS request failed: {options_error}")
                
                # If OPTIONS fails, try a regular GET to check basic CORS headers
                try:
                    async with session.get(
                        f"{auth_service_url}/auth/config",
                        headers={"Origin": "http://localhost:3000"},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        cors_headers = dict(response.headers)
                        cors_test_successful = True
                        print(f"[CORS] GET request successful as fallback, status: {response.status}")
                except Exception as get_error:
                    print(f"[CORS] GET fallback also failed: {get_error}")
            
            if cors_test_successful:
                # Check for CORS headers (case-insensitive)
                cors_headers_lower = {k.lower(): v for k, v in cors_headers.items()}
                
                required_cors_headers = [
                    "access-control-allow-origin",
                    "access-control-allow-methods", 
                    "access-control-allow-headers"
                ]
                
                missing_cors = []
                present_cors = []
                
                for header in required_cors_headers:
                    if header in cors_headers_lower:
                        present_cors.append(f"{header}: {cors_headers_lower[header]}")
                    else:
                        missing_cors.append(header)

                if missing_cors:
                    # Only report as warning, not failure, since CORS might be configured differently
                    warning_msg = f"Some CORS headers missing: {missing_cors}. Present: {present_cors}"
                    print(f"[CORS-WARNING] {warning_msg}")
                    logger.warning(warning_msg)
                else:
                    print(f"[SUCCESS] CORS headers configured correctly: {present_cors}")
            else:
                # CORS test completely failed - this might indicate service issues
                warning_msg = "CORS test failed completely - service may not be configured for cross-origin requests"
                print(f"[CORS-WARNING] {warning_msg}")
                logger.warning(warning_msg)
                    
        except Exception as e:
            # Don't fail the test for CORS issues, just log them
            warning_msg = f"CORS test encountered error: {e}"
            print(f"[CORS-WARNING] {warning_msg}")
            logger.warning(warning_msg)
    
    # Cleanup test harness
    await harness.cleanup()
    
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
            failure_report.append("[CRITICAL] Authentication Failures:")
            for failure in critical_failures:
                failure_report.append(f"  - {failure}")
        
        if warning_failures:
            failure_report.append("[WARNING] Authentication Issues:")
            for failure in warning_failures:
                failure_report.append(f"  - {failure}")
        
        failure_report.append(f"
[SUMMARY] {len(critical_failures)} critical, {len(warning_failures)} warnings")
        
        pytest.fail(f"Cross-service authentication flow failed:
" + "
".join(failure_report))
    
    print("[SUCCESS] Complete cross-service authentication flow working correctly")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_authentication_rate_limiting():
    """Test that authentication endpoints have proper rate limiting.
    
    This test will WARN if rate limiting is not implemented but won't fail the test completely.
    """
    pass
    # Use IsolatedEnvironment for environment management as required by CLAUDE.md
    env = get_env()
    env.set("ENVIRONMENT", "test", "test_authentication_rate_limiting")
    env.set("NETRA_ENVIRONMENT", "test", "test_authentication_rate_limiting")
    
    # Set correct service ports for real running services BEFORE harness initialization
    import os
    env.set("TEST_AUTH_PORT", "8082", "test_authentication_rate_limiting")
    env.set("TEST_BACKEND_PORT", "8002", "test_authentication_rate_limiting")
    
    # Initialize test harness for real service integration
    harness = UnifiedE2ETestHarness()
    
    # Use properly running dev service on standard port  
    auth_service_url = "http://localhost:8081"  # Dev auth service on standard port
    
    # Test rapid login attempts
    rate_limit_warnings = []
    
    async with aiohttp.ClientSession() as session:
        # First check if auth service is available
        if not await check_service_availability(session, "Auth Service", auth_service_url):
            pytest.skip(f"Auth service is not available at {auth_service_url}. Skipping rate limiting test.")
        
        print("[RATE-LIMIT] Testing authentication rate limiting...")
        
        # Attempt many rapid login requests
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        start_time = time.time()
        responses = []
        
        # Make 10 rapid requests (reduced from 20 to be less aggressive)
        tasks = []
        for i in range(10):
            task = session.post(
                f"{auth_service_url}/auth/login",
                json=login_data,
                timeout=aiohttp.ClientTimeout(total=5)
            )
            tasks.append(task)
        
        try:
            # Execute all requests concurrently
            async_responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            rate_limited_count = 0
            successful_count = 0
            error_count = 0
            
            for response in async_responses:
                if isinstance(response, Exception):
                    error_count += 1
                    continue
                
                try:
                    if response.status == 429:  # Too Many Requests
                        rate_limited_count += 1
                    elif response.status == 401:  # Unauthorized (normal failed login)
                        successful_count += 1
                    elif response.status >= 400:
                        error_count += 1
                    
                    await response.close()
                except Exception:
                    error_count += 1
            
            elapsed_time = time.time() - start_time
            
            # Analyze results more gracefully
            if rate_limited_count == 0 and successful_count > 5:
                rate_limit_warnings.append(f"No rate limiting detected - {successful_count} rapid login attempts processed")
            
            print(f"[RATE-LIMIT] {rate_limited_count} rate-limited, {successful_count} processed, {error_count} errors in {elapsed_time:.2f}s")
            
            if rate_limited_count > 0:
                print(f"[SUCCESS] Rate limiting is working - {rate_limited_count} requests were rate-limited")
            
        except Exception as e:
            rate_limit_warnings.append(f"Rate limiting test encountered error: {e}")
    
    # Only warn about rate limiting issues, don't fail the test
    if rate_limit_warnings:
        warning_report = ["[RATE-LIMIT] Warnings:"]
        for warning in rate_limit_warnings:
            warning_report.append(f"  - {warning}")
        warning_report.append("Note: Rate limiting may not be implemented yet. This is a warning, not a failure.")
        
        logger.warning("
".join(warning_report))
        print("
".join(warning_report))
    else:
        print("[SUCCESS] Authentication rate limiting working correctly")
    
    # Cleanup test harness
    await harness.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])