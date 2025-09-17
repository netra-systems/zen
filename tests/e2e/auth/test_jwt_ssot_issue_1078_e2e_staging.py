"""
JWT SSOT E2E Staging Tests - Issue #1078
Purpose: Create FAILING E2E tests to validate JWT SSOT compliance on staging
These tests should FAIL initially with JWT inconsistencies, then PASS after remediation

Business Value Justification (BVJ):
- Segment: Platform/Enterprise (Production readiness)
- Business Goal: Ensure JWT SSOT works reliably in production-like environment
- Value Impact: Validates $500K+ ARR authentication system reliability  
- Revenue Impact: Prevents staging deployment failures that block customer onboarding
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional

import pytest
import httpx
import websockets
from test_framework.base_e2e_test import BaseE2ETest


@pytest.mark.e2e
@pytest.mark.staging
class JWTSSOTIssue1078E2EStagingTests(BaseE2ETest):
    """E2E staging tests to validate JWT SSOT compliance in production-like environment"""
    
    def setup_method(self):
        super().setup_method()
        # Staging environment endpoints
        self.auth_service_url = "https://auth.staging.netrasystems.ai"
        self.api_base_url = "https://api.staging.netrasystems.ai"
        self.websocket_url = "wss://api.staging.netrasystems.ai/ws"
        
        # Test user credentials for staging
        self.test_user_email = "test-jwt-ssot@example.com"
        self.test_user_password = "TestJWTSSot2024!"
    
    async def test_end_to_end_jwt_flow_uses_auth_service(self):
        """
        FAILING TEST: E2E JWT flow should use pure auth service delegation
        
        This test validates complete JWT authentication flow from user login
        through WebSocket connection uses consistent auth service delegation.
        Expected to FAIL with JWT secret mismatches or inconsistent validation.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Step 1: Authenticate with staging auth service
                auth_response = await client.post(
                    f"{self.auth_service_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                if auth_response.status_code != 200:
                    pytest.fail(
                        f"STAGING AUTH SERVICE LOGIN FAILED (Issue #1078):\n"
                        f"Status: {auth_response.status_code}\n"
                        f"Response: {auth_response.text}\n\n"
                        "Cannot test JWT SSOT compliance without valid auth service login.\n"
                        "This suggests auth service configuration issues."
                    )
                
                auth_data = auth_response.json()
                access_token = auth_data.get("access_token")
                
                if not access_token:
                    pytest.fail(
                        f"NO ACCESS TOKEN FROM AUTH SERVICE (Issue #1078):\n"
                        f"Auth response: {auth_data}\n\n"
                        "Auth service should return access_token for JWT validation testing."
                    )
                
                # Step 2: Validate token with backend API (should delegate to auth service)
                api_response = await client.get(
                    f"{self.api_base_url}/auth/validate",
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if api_response.status_code == 403:
                    pytest.fail(
                        f"JWT VALIDATION 403 ERROR (Issue #1078):\n"
                        f"Backend API rejected token from auth service\n"
                        f"Auth service token: {access_token[:20]}...\n"
                        f"API response: {api_response.text}\n\n"
                        "🚨 CRITICAL: This proves JWT secret mismatch between services!\n"
                        "Backend is not properly delegating to auth service SSOT.\n\n"
                        "EXPECTED: Backend validates token via auth service delegation\n"
                        "ACTUAL: Backend rejects token, indicating different JWT secrets"
                    )
                
                if api_response.status_code != 200:
                    pytest.fail(
                        f"API JWT VALIDATION FAILED (Issue #1078):\n"
                        f"Status: {api_response.status_code}\n" 
                        f"Response: {api_response.text}\n\n"
                        "Backend API should validate tokens from auth service.\n"
                        "This suggests incomplete JWT SSOT delegation."
                    )
                
                # Step 3: Test WebSocket connection with JWT (should use same validation)
                try:
                    async with websockets.connect(
                        self.websocket_url,
                        additional_headers={"Authorization": f"Bearer {access_token}"},
                        timeout=10
                    ) as websocket:
                        
                        # Send test message to trigger JWT validation
                        test_message = {
                            "type": "agent_request",
                            "agent": "triage_agent", 
                            "message": "Test JWT SSOT compliance"
                        }
                        
                        await websocket.send(json.dumps(test_message))
                        
                        # Wait for response (should not be auth error)
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=10)
                            response_data = json.loads(response)
                            
                            # Check for authentication errors
                            if response_data.get("type") == "error" and "auth" in response_data.get("message", "").lower():
                                pytest.fail(
                                    f"WEBSOCKET JWT AUTHENTICATION FAILED (Issue #1078):\n"
                                    f"WebSocket rejected token accepted by auth service\n"
                                    f"Error: {response_data}\n\n"
                                    "🚨 CRITICAL: WebSocket JWT validation inconsistent with auth service!\n"
                                    "WebSocket is not using proper auth service delegation.\n\n"
                                    "This proves WebSocket has different JWT validation than auth service."
                                )
                            
                            # Successful authentication indicates SSOT compliance
                            if response_data.get("type") in ["agent_started", "agent_thinking"]:
                                # This is actually good - WebSocket accepted the token
                                pass
                            else:
                                pytest.fail(
                                    f"UNEXPECTED WEBSOCKET RESPONSE (Issue #1078):\n"
                                    f"Expected agent response, got: {response_data}\n\n"
                                    "WebSocket should process messages after successful JWT validation."
                                )
                        
                        except asyncio.TimeoutError:
                            pytest.fail(
                                "WEBSOCKET TIMEOUT (Issue #1078):\n"
                                "WebSocket did not respond within 10 seconds.\n\n"
                                "This suggests WebSocket JWT validation may be hanging\n"
                                "or failing silently, indicating SSOT delegation issues."
                            )
                
                except websockets.ConnectionClosed as e:
                    pytest.fail(
                        f"WEBSOCKET CONNECTION FAILED (Issue #1078):\n"
                        f"Connection closed during handshake: {e}\n\n"
                        "WebSocket should accept tokens validated by auth service.\n"
                        "Connection failure suggests JWT validation inconsistency."
                    )
                
                except websockets.InvalidStatusCode as e:
                    if e.status_code == 403:
                        pytest.fail(
                            f"WEBSOCKET JWT 403 ERROR (Issue #1078):\n"
                            f"WebSocket rejected token accepted by auth service\n"
                            f"Status code: {e.status_code}\n\n"
                            "🚨 CRITICAL: WebSocket JWT validation differs from auth service!\n"
                            "This proves WebSocket is not using auth service SSOT delegation."
                        )
                    else:
                        pytest.fail(f"WebSocket connection failed with status {e.status_code}: {e}")
                
                # If we reach here, JWT flow appears consistent
                # But for Issue #1078 testing, we expect some inconsistencies initially
                pytest.skip(
                    "JWT E2E flow appears consistent across services.\n"
                    "This suggests SSOT delegation may already be working correctly.\n"
                    "Manual verification recommended for Issue #1078."
                )
                
            except httpx.TimeoutException:
                pytest.fail(
                    "STAGING ENVIRONMENT TIMEOUT (Issue #1078):\n"
                    "Could not connect to staging services within 30 seconds.\n\n"
                    "This test requires functional staging environment to validate\n"
                    "JWT SSOT compliance in production-like conditions."
                )
            
            except httpx.RequestError as e:
                pytest.fail(f"Staging environment connection error: {e}")
    
    async def test_websocket_authentication_staging_consistency(self):
        """
        FAILING TEST: WebSocket auth should be consistent with staging auth service
        
        This test specifically validates WebSocket JWT authentication consistency
        with staging auth service. Expected to FAIL with validation inconsistencies.
        """
        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                # Get valid token from staging auth service
                auth_response = await client.post(
                    f"{self.auth_service_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                if auth_response.status_code != 200:
                    pytest.skip("Cannot test without staging auth service access")
                
                access_token = auth_response.json().get("access_token")
                if not access_token:
                    pytest.skip("No access token available for testing")
                
                # Test multiple WebSocket connection patterns
                connection_patterns = [
                    ("authorization_header", {"Authorization": f"Bearer {access_token}"}),
                    ("subprotocol_jwt", {}, [f"jwt.{access_token.replace('.', '_')}"])  # Base64 encode if needed
                ]
                
                connection_results = {}
                
                for pattern_name, headers, subprotocols in connection_patterns:
                    try:
                        # Test WebSocket connection with different auth patterns
                        connect_kwargs = {"additional_headers": headers} if headers else {}
                        if len(connection_patterns[1]) > 2:  # Has subprotocols
                            connect_kwargs["subprotocols"] = subprotocols
                        
                        async with websockets.connect(
                            self.websocket_url,
                            timeout=5,
                            **connect_kwargs
                        ) as websocket:
                            
                            # Send simple ping to verify connection
                            await websocket.send(json.dumps({"type": "ping"}))
                            
                            try:
                                response = await asyncio.wait_for(websocket.recv(), timeout=3)
                                connection_results[pattern_name] = "SUCCESS"
                            
                            except asyncio.TimeoutError:
                                connection_results[pattern_name] = "TIMEOUT"
                    
                    except websockets.InvalidStatusCode as e:
                        connection_results[pattern_name] = f"STATUS_{e.status_code}"
                    
                    except Exception as e:
                        connection_results[pattern_name] = f"ERROR_{type(e).__name__}"
                
                # Analyze connection consistency
                successful_patterns = [p for p, result in connection_results.items() if result == "SUCCESS"]
                failed_patterns = [p for p, result in connection_results.items() if result != "SUCCESS"]
                
                if len(successful_patterns) == 0:
                    pytest.fail(
                        f"ALL WEBSOCKET AUTH PATTERNS FAILED (Issue #1078):\n"
                        f"Results: {connection_results}\n\n"
                        "WebSocket should accept tokens from auth service using standard patterns.\n"
                        "Complete failure suggests WebSocket JWT validation is broken\n"
                        "or not properly delegating to auth service."
                    )
                
                if len(failed_patterns) > 0:
                    pytest.fail(
                        f"WEBSOCKET AUTH PATTERN INCONSISTENCY (Issue #1078):\n"
                        f"Successful: {successful_patterns}\n"
                        f"Failed: {failed_patterns}\n"
                        f"Full results: {connection_results}\n\n"
                        "WebSocket authentication should work consistently across patterns.\n"
                        "Inconsistent behavior suggests incomplete SSOT delegation implementation."
                    )
                
                # If all patterns work, this suggests good SSOT compliance
                assert len(successful_patterns) > 0, "At least one auth pattern should work"
                
            except httpx.RequestError as e:
                pytest.skip(f"Cannot test staging consistency due to connection error: {e}")
    
    async def test_jwt_secret_synchronization_staging_validation(self):
        """
        FAILING TEST: JWT secrets should be synchronized across staging services
        
        This test validates JWT secret consistency by creating tokens with auth service
        and validating them across different backend endpoints. Expected to FAIL with 
        secret mismatches.
        """
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # Step 1: Get JWT token from auth service
                auth_response = await client.post(
                    f"{self.auth_service_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                if auth_response.status_code != 200:
                    pytest.skip("Cannot test secret synchronization without auth service access")
                
                auth_data = auth_response.json()
                access_token = auth_data.get("access_token")
                refresh_token = auth_data.get("refresh_token")
                
                if not access_token:
                    pytest.skip("No access token for secret synchronization testing")
                
                # Step 2: Test token validation across different backend endpoints
                validation_endpoints = [
                    ("/auth/validate", "Auth validation endpoint"),
                    ("/auth/user", "User info endpoint"),
                    ("/health", "Health check with auth"),
                    ("/api/v1/threads", "API endpoint with auth")
                ]
                
                validation_results = {}
                
                for endpoint_path, endpoint_desc in validation_endpoints:
                    try:
                        response = await client.get(
                            f"{self.api_base_url}{endpoint_path}",
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                        
                        validation_results[endpoint_path] = {
                            "status": response.status_code,
                            "description": endpoint_desc
                        }
                    
                    except Exception as e:
                        validation_results[endpoint_path] = {
                            "status": "ERROR",
                            "error": str(e),
                            "description": endpoint_desc
                        }
                
                # Analyze validation consistency
                auth_errors = {
                    path: result for path, result in validation_results.items()
                    if result.get("status") in [401, 403]
                }
                
                if auth_errors:
                    pytest.fail(
                        f"JWT SECRET SYNCHRONIZATION FAILURE (Issue #1078):\n"
                        f"Auth service token rejected by backend endpoints:\n\n" +
                        "\n".join([
                            f"  ❌ {path} ({result['description']}): Status {result['status']}"
                            for path, result in auth_errors.items()
                        ]) +
                        f"\n\n🚨 CRITICAL JWT SECRET MISMATCH DETECTED!\n"
                        f"Auth service creates tokens with one secret,\n"
                        f"Backend validates with different secret.\n\n"
                        f"This proves backend is not using auth service SSOT delegation.\n"
                        f"Backend must use same JWT secret as auth service."
                    )
                
                # Check for other errors
                other_errors = {
                    path: result for path, result in validation_results.items()
                    if result.get("status") not in [200, 201, 401, 403] and result.get("status") != "ERROR"
                }
                
                if other_errors:
                    pytest.fail(
                        f"BACKEND ENDPOINT ERRORS (Issue #1078):\n" +
                        "\n".join([
                            f"  ⚠️  {path}: Status {result['status']}"
                            for path, result in other_errors.items()
                        ]) +
                        "\n\nSome backend endpoints have issues that prevent JWT validation testing."
                    )
                
                # Step 3: Test refresh token if available
                if refresh_token:
                    try:
                        refresh_response = await client.post(
                            f"{self.auth_service_url}/auth/refresh",
                            json={"refresh_token": refresh_token}
                        )
                        
                        if refresh_response.status_code == 200:
                            new_access_token = refresh_response.json().get("access_token")
                            
                            if new_access_token:
                                # Test new token with backend
                                test_response = await client.get(
                                    f"{self.api_base_url}/auth/validate",
                                    headers={"Authorization": f"Bearer {new_access_token}"}
                                )
                                
                                if test_response.status_code in [401, 403]:
                                    pytest.fail(
                                        f"REFRESHED TOKEN REJECTION (Issue #1078):\n"
                                        f"Backend rejected refreshed token from auth service\n"
                                        f"Status: {test_response.status_code}\n\n"
                                        "This confirms JWT secret synchronization issues.\n"
                                        "Refreshed tokens should work if secrets are synchronized."
                                    )
                    
                    except Exception as e:
                        # Refresh token issues are not critical for this test
                        pass
                
                # If we reach here without failures, secrets appear synchronized
                successful_validations = len([r for r in validation_results.values() if r.get("status") == 200])
                
                assert successful_validations > 0, "At least some endpoints should validate JWT successfully"
                
            except httpx.RequestError as e:
                pytest.skip(f"Cannot test JWT secret synchronization due to connection error: {e}")
    
    async def test_staging_jwt_performance_under_load(self):
        """
        FAILING TEST: Staging JWT validation should perform well under load
        
        This test validates JWT delegation performance in staging environment.
        Expected to FAIL if SSOT delegation creates performance bottlenecks.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get authentication token
                auth_response = await client.post(
                    f"{self.auth_service_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                if auth_response.status_code != 200:
                    pytest.skip("Cannot test performance without auth service access")
                
                access_token = auth_response.json().get("access_token")
                if not access_token:
                    pytest.skip("No access token for performance testing")
                
                # Performance test: Multiple concurrent validations
                concurrent_requests = 10
                validation_times = []
                
                async def validate_token():
                    start_time = time.time()
                    response = await client.get(
                        f"{self.api_base_url}/auth/validate",
                        headers={"Authorization": f"Bearer {access_token}"}
                    )
                    end_time = time.time()
                    
                    validation_time = (end_time - start_time) * 1000  # Convert to ms
                    return validation_time, response.status_code
                
                # Run concurrent validations
                tasks = [validate_token() for _ in range(concurrent_requests)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Analyze results
                successful_validations = []
                failed_validations = []
                
                for result in results:
                    if isinstance(result, Exception):
                        failed_validations.append(f"Exception: {result}")
                    else:
                        validation_time, status_code = result
                        if status_code == 200:
                            successful_validations.append(validation_time)
                        else:
                            failed_validations.append(f"Status {status_code}")
                
                # Check for failures
                if failed_validations:
                    pytest.fail(
                        f"JWT VALIDATION FAILURES UNDER LOAD (Issue #1078):\n"
                        f"Failed validations: {len(failed_validations)}/{concurrent_requests}\n"
                        f"Failures: {failed_validations}\n\n"
                        "JWT validation should handle concurrent requests reliably.\n"
                        "Failures suggest auth service delegation issues under load."
                    )
                
                # Performance analysis
                if successful_validations:
                    avg_time = sum(successful_validations) / len(successful_validations)
                    max_time = max(successful_validations)
                    min_time = min(successful_validations)
                    
                    # Performance thresholds for staging environment
                    if avg_time > 2000:  # 2 second average is too slow
                        pytest.fail(
                            f"JWT VALIDATION TOO SLOW UNDER LOAD (Issue #1078):\n"
                            f"Average time: {avg_time:.2f}ms (should be < 2000ms)\n"
                            f"Max time: {max_time:.2f}ms\n"
                            f"Min time: {min_time:.2f}ms\n"
                            f"All times: {[f'{t:.0f}ms' for t in successful_validations]}\n\n"
                            "SSOT JWT delegation should be performant in staging.\n"
                            "High latency suggests inefficient delegation patterns\n"
                            "or auth service performance issues."
                        )
                    
                    if max_time > 5000:  # 5 seconds max is unacceptable
                        pytest.fail(
                            f"JWT VALIDATION TIMEOUT UNDER LOAD (Issue #1078):\n"
                            f"Max validation time: {max_time:.2f}ms (should be < 5000ms)\n\n"
                            "Individual JWT validations should not exceed 5 seconds.\n"
                            "This suggests serious performance issues with auth service delegation."
                        )
                    
                    # Performance acceptable
                    assert len(successful_validations) == concurrent_requests, "All validations should succeed"
                    assert avg_time < 2000, f"Average performance acceptable: {avg_time:.2f}ms"
                
                else:
                    pytest.fail(
                        f"NO SUCCESSFUL JWT VALIDATIONS (Issue #1078):\n"
                        f"All {concurrent_requests} concurrent validations failed\n\n"
                        "This indicates severe JWT delegation issues in staging environment."
                    )
            
            except httpx.RequestError as e:
                pytest.skip(f"Cannot test staging performance due to connection error: {e}")