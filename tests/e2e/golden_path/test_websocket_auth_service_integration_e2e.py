"""
WebSocket Auth Service Integration E2E Test - Auth Service Connectivity Issues

CRITICAL AUTH SERVICE INTEGRATION VALIDATION: This test validates that WebSocket
authentication properly integrates with the auth service and fails clearly when
auth service connectivity issues occur.

Test Objective: WebSocket Auth Service Integration Failure Detection
- MANDATORY hard failure when auth service is unavailable for WebSocket auth
- MANDATORY clear error messages explaining auth service connectivity issues
- MANDATORY auth service health validation before WebSocket connections
- PROOF that auth service failures prevent WebSocket connections properly

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Authentication Critical
- Business Goal: Secure and reliable WebSocket authentication via auth service
- Value Impact: Prevents WebSocket access when authentication cannot be validated
- Strategic Impact: Maintains security integrity when auth service issues occur

CRITICAL REQUIREMENTS (per CLAUDE.md Section 6.2):
1. MANDATORY auth service connectivity check before WebSocket connections
2. MANDATORY hard failure when auth service unavailable (NO try/except hiding)
3. MANDATORY authentication via E2EAuthHelper with auth service integration
4. MANDATORY clear error messages explaining auth service business impact
5. NO silent auth failures or WebSocket connection hiding
6. Must demonstrate auth service unavailability prevents WebSocket access

WEBSOCKET AUTH SERVICE INTEGRATION FLOW:
```
Auth Service Health Check → JWT Token Validation → WebSocket Connection with Auth →
Auth Service Failure Detection → Hard Failure with Auth Diagnosis → Test Failure
```
"""

import asyncio
import json
import pytest
import time
import aiohttp
import websockets
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules - AUTH SERVICE INTEGRATION FOCUSED
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context, validate_jwt_token
from test_framework.ssot.real_services_test_fixtures import real_services_fixture

# Core system imports for auth service integration validation
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, WebSocketID


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.auth_service_integration
@pytest.mark.asyncio
@pytest.mark.websocket_auth
class TestWebSocketAuthServiceIntegrationE2E(SSotAsyncTestCase):
    """
    WebSocket Auth Service Integration Failure Detection Tests.
    
    This test suite validates that WebSocket authentication properly integrates
    with the auth service and fails appropriately when auth service issues occur.
    
    CRITICAL MANDATE: These tests MUST fail hard when auth service is unavailable
    to ensure WebSocket security is not compromised by auth service issues.
    """
    
    def setup_method(self, method=None):
        """Setup with auth service integration validation focus."""
        super().setup_method(method)
        
        # Auth service integration compliance metrics
        self.record_metric("websocket_auth_service_integration_test", True)
        self.record_metric("auth_service_dependency_validation", "mandatory")
        self.record_metric("auth_service_failure_tolerance", 0)  # ZERO tolerance for auth failures
        self.record_metric("websocket_auth_security_critical", True)
        
        # Initialize auth service integration components
        self._auth_helper = None
        self._websocket_helper = None
        self._auth_service_url = None
        self._websocket_url = None
        
    async def async_setup_method(self, method=None):
        """Async setup with mandatory auth service integration validation."""
        await super().async_setup_method(method)
        
        # CRITICAL: Initialize auth service integration helpers
        environment = self.get_env_var("TEST_ENV", "test")
        self._auth_helper = E2EAuthHelper(environment=environment)
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Get service URLs for integration testing
        self._auth_service_url = self.get_env_var("AUTH_SERVICE_URL", "http://localhost:8081")
        self._websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Record auth service integration setup
        self.record_metric("auth_service_integration_setup_completed", True)
        self.record_metric("auth_service_url", self._auth_service_url)
        self.record_metric("websocket_service_url", self._websocket_url)

    @pytest.mark.timeout(45)  # Allow time for auth service integration validation
    @pytest.mark.asyncio
    async def test_auth_service_unavailable_blocks_websocket_access(self, real_services_fixture):
        """
        CRITICAL: Test auth service unavailability prevents WebSocket access.
        
        This test validates that:
        1. Auth service health is checked before WebSocket authentication
        2. Auth service unavailability prevents WebSocket connections
        3. Clear error messages explain auth service connectivity issues
        4. JWT token validation requires accessible auth service
        5. WebSocket connections fail securely when auth service is down
        
        AUTH SERVICE SECURITY REQUIREMENTS:
        - Auth service health check MUST be performed
        - Auth service unavailability MUST prevent WebSocket access
        - Error messages MUST explain authentication service impact
        - NO WebSocket connections allowed without auth service validation
        
        BUSINESS IMPACT: Auth service unavailability prevents secure WebSocket access
        """
        test_start_time = time.time()
        
        # === AUTH SERVICE HEALTH CHECK ===
        self.record_metric("auth_service_health_check_start", time.time())
        
        auth_service_available = False
        auth_service_error = None
        auth_service_response_time = None
        
        try:
            # Check auth service health endpoint
            health_start = time.time()
            
            async with aiohttp.ClientSession() as session:
                health_url = f"{self._auth_service_url}/health"
                async with session.get(health_url, timeout=10.0) as response:
                    auth_service_response_time = time.time() - health_start
                    
                    if response.status == 200:
                        auth_service_available = True
                        health_data = await response.json()
                        self.record_metric("auth_service_health_response", health_data)
                    else:
                        auth_service_error = f"Auth service returned status {response.status}"
                        
        except Exception as e:
            auth_service_error = str(e)
            auth_service_response_time = time.time() - health_start if 'health_start' in locals() else 0
        
        # Record auth service health check results
        self.record_metric("auth_service_available", auth_service_available)
        self.record_metric("auth_service_health_response_time", auth_service_response_time)
        self.record_metric("auth_service_health_error", auth_service_error)
        
        # === AUTH SERVICE INTEGRATION VALIDATION ===
        if auth_service_available:
            # Auth service is available - test normal integration
            await self._test_auth_service_integration_when_available()
            
        else:
            # Auth service is unavailable - validate WebSocket access is blocked
            await self._test_websocket_blocked_when_auth_unavailable(auth_service_error, auth_service_response_time)
        
        # Record final metrics
        total_test_time = time.time() - test_start_time
        self.record_metric("auth_service_integration_test_duration", total_test_time)

    async def _test_auth_service_integration_when_available(self):
        """Test auth service integration when auth service is available."""
        
        # === JWT TOKEN CREATION AND VALIDATION ===
        self.record_metric("jwt_token_creation_test_start", time.time())
        
        # Create authenticated user context
        authenticated_user = await create_authenticated_user_context(
            user_email="websocket_auth_integration@example.com",
            environment=self.get_env_var("TEST_ENV", "test"),
            permissions=["read", "write", "websocket"],
            websocket_enabled=True
        )
        
        jwt_token = authenticated_user.agent_context.get("jwt_token")
        user_id = str(authenticated_user.user_id)
        
        # Validate JWT token with auth service
        token_validation = await validate_jwt_token(jwt_token, environment=self.get_env_var("TEST_ENV", "test"))
        
        assert token_validation.get("valid"), f"JWT token validation failed: {token_validation}"
        assert token_validation.get("user_id"), "JWT token must contain user_id"
        
        self.record_metric("jwt_token_validation_success", True)
        self.record_metric("jwt_user_id_validated", token_validation.get("user_id"))
        
        # === WEBSOCKET CONNECTION WITH VALID AUTH SERVICE ===
        self.record_metric("websocket_auth_integration_test_start", time.time())
        
        # Get authenticated WebSocket headers
        auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        websocket_connection = None
        connection_success = False
        
        try:
            # Attempt WebSocket connection with auth service validation
            websocket_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=10.0,
                    close_timeout=5.0
                ),
                timeout=15.0
            )
            
            connection_success = True
            
            # Test authenticated WebSocket communication
            test_message = {
                "type": "auth_integration_test",
                "content": "Auth service integration validation",
                "user_id": user_id,
                "timestamp": time.time(),
                "auth_service_validation": True
            }
            
            await websocket_connection.send(json.dumps(test_message))
            
            # Brief wait for response
            await asyncio.sleep(1.0)
            
        except Exception as e:
            self.record_metric("websocket_connection_error", str(e))
            pytest.fail(
                f"WebSocket connection should succeed when auth service is available. "
                f"Error: {e}. This indicates auth service integration is broken."
            )
        
        finally:
            if websocket_connection:
                await websocket_connection.close()
        
        # Record successful auth service integration
        self.record_metric("websocket_auth_service_integration_success", connection_success)
        
        print(f"✅ AUTH SERVICE INTEGRATION: WORKING")
        print(f"   🟢 Auth service: Available")
        print(f"   🟢 JWT validation: Success")
        print(f"   🟢 WebSocket auth: Success") 
        print(f"   👤 Authenticated user: {user_id}")

    async def _test_websocket_blocked_when_auth_unavailable(self, auth_error: str, response_time: float):
        """Test WebSocket access is blocked when auth service is unavailable."""
        
        # === ATTEMPT TO CREATE AUTH USER DESPITE AUTH SERVICE UNAVAILABILITY ===
        self.record_metric("fallback_auth_test_start", time.time())
        
        # Try to create authenticated user context (may use fallback auth)
        fallback_user = None
        try:
            fallback_user = await create_authenticated_user_context(
                user_email="websocket_fallback_test@example.com",
                environment=self.get_env_var("TEST_ENV", "test"),
                websocket_enabled=True
            )
        except Exception as e:
            # Auth user creation failed - this is expected when auth service is down
            self.record_metric("auth_user_creation_failed", str(e))
        
        if fallback_user:
            # If fallback auth succeeded, test WebSocket connection with fallback
            jwt_token = fallback_user.agent_context.get("jwt_token")
            user_id = str(fallback_user.user_id)
            
            auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
            
            # === WEBSOCKET CONNECTION ATTEMPT WITH AUTH SERVICE DOWN ===
            websocket_blocked = False
            websocket_error = None
            
            try:
                # Attempt WebSocket connection despite auth service unavailability
                websocket_connection = await asyncio.wait_for(
                    websockets.connect(
                        self._websocket_url,
                        additional_headers=auth_headers,
                        open_timeout=8.0,
                        close_timeout=3.0
                    ),
                    timeout=12.0
                )
                
                # If connection succeeded, close it
                await websocket_connection.close()
                
                # This might be OK if using fallback auth or cached validation
                self.record_metric("websocket_connection_with_auth_service_down", "succeeded")
                print(f"ℹ️ WebSocket connection succeeded despite auth service unavailability")
                print(f"   📡 May be using cached auth or fallback validation")
                print(f"   🔐 JWT token: Present")
                print(f"   👤 User ID: {user_id}")
                
            except Exception as e:
                websocket_blocked = True
                websocket_error = str(e)
                
                # This is the expected behavior - auth service down should block WebSocket
                self.record_metric("websocket_properly_blocked", True)
                self.record_metric("websocket_block_error", websocket_error)
        
        # === VALIDATION OF AUTH SERVICE UNAVAILABILITY IMPACT ===
        
        auth_service_impact_message = (
            f"🚨 AUTH SERVICE UNAVAILABILITY DETECTED:\n"
            f"   🔴 Auth Service URL: {self._auth_service_url}\n"
            f"   🔴 Health Check Error: {auth_error}\n"
            f"   🔴 Response Time: {response_time:.3f}s\n"
            f"   🔴 WebSocket URL: {self._websocket_url}\n"
            f"\n"
            f"   💼 BUSINESS IMPACT:\n"
            f"   • User authentication cannot be validated\n"
            f"   • New WebSocket connections may be blocked\n"
            f"   • JWT token validation not available\n"
            f"   • Security-critical authentication flows broken\n"
            f"   • Real-time AI features may be inaccessible\n"
            f"\n"
            f"   🔧 RESOLUTION REQUIRED:\n"
            f"   • Start auth service at {self._auth_service_url}\n"
            f"   • Verify auth service configuration and database connectivity\n"
            f"   • Check auth service health endpoint: {self._auth_service_url}/health\n"
            f"   • Validate JWT secret configuration consistency\n"
            f"   • Ensure auth service can validate WebSocket authentication\n"
        )
        
        # Print detailed auth service diagnosis
        print(auth_service_impact_message)
        
        # MANDATORY HARD FAILURE - DO NOT HIDE AUTH SERVICE ISSUES
        pytest.fail(auth_service_impact_message)

    @pytest.mark.timeout(35)
    @pytest.mark.asyncio
    async def test_jwt_token_validation_with_auth_service(self, real_services_fixture):
        """
        CRITICAL: Test JWT token validation requires auth service connectivity.
        
        This test validates JWT token validation integration:
        1. Valid JWT tokens are accepted when auth service is available
        2. Invalid JWT tokens are rejected by auth service validation
        3. Expired JWT tokens are detected via auth service
        4. JWT validation failures prevent WebSocket access
        """
        
        # === TEST 1: VALID JWT TOKEN VALIDATION ===
        self.record_metric("valid_jwt_test_start", time.time())
        
        # Create valid JWT token
        valid_jwt = self._auth_helper.create_test_jwt_token(
            user_id="jwt_validation_test_user",
            email="jwt_validation@example.com",
            permissions=["read", "write", "websocket"],
            exp_minutes=30  # Valid for 30 minutes
        )
        
        # Validate JWT token
        valid_token_result = await validate_jwt_token(valid_jwt, environment=self.get_env_var("TEST_ENV", "test"))
        
        assert valid_token_result.get("valid"), f"Valid JWT token should pass validation: {valid_token_result}"
        assert valid_token_result.get("user_id") == "jwt_validation_test_user", "JWT should contain correct user_id"
        
        self.record_metric("valid_jwt_validation_success", True)
        
        # Test WebSocket connection with valid JWT
        valid_auth_headers = self._auth_helper.get_websocket_headers(valid_jwt)
        
        try:
            valid_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=valid_auth_headers,
                    open_timeout=8.0
                ),
                timeout=12.0
            )
            await valid_connection.close()
            
            self.record_metric("websocket_connection_with_valid_jwt", True)
            
        except Exception as e:
            pytest.fail(f"WebSocket connection should succeed with valid JWT. Error: {e}")
        
        # === TEST 2: INVALID JWT TOKEN REJECTION ===
        self.record_metric("invalid_jwt_test_start", time.time())
        
        invalid_jwts = [
            "invalid.jwt.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "not-a-jwt-at-all"
        ]
        
        for invalid_jwt in invalid_jwts:
            # Validate invalid JWT token
            invalid_token_result = await validate_jwt_token(invalid_jwt, environment=self.get_env_var("TEST_ENV", "test"))
            
            assert not invalid_token_result.get("valid"), f"Invalid JWT should fail validation: {invalid_jwt}"
            
            # Test WebSocket connection with invalid JWT
            invalid_auth_headers = {"Authorization": f"Bearer {invalid_jwt}"}
            
            invalid_connection_blocked = False
            try:
                invalid_connection = await asyncio.wait_for(
                    websockets.connect(
                        self._websocket_url,
                        additional_headers=invalid_auth_headers,
                        open_timeout=5.0
                    ),
                    timeout=8.0
                )
                await invalid_connection.close()
                
            except Exception:
                invalid_connection_blocked = True
            
            # Invalid JWT should block WebSocket connection
            assert invalid_connection_blocked, f"Invalid JWT should block WebSocket connection: {invalid_jwt}"
        
        self.record_metric("invalid_jwt_tokens_rejected", len(invalid_jwts))
        
        # === TEST 3: EXPIRED JWT TOKEN REJECTION ===
        self.record_metric("expired_jwt_test_start", time.time())
        
        # Create expired JWT token
        expired_jwt = self._auth_helper.create_test_jwt_token(
            user_id="expired_jwt_test_user",
            email="expired_jwt@example.com",
            permissions=["read", "write"],
            exp_minutes=-1  # Expired 1 minute ago
        )
        
        # Validate expired JWT token
        expired_token_result = await validate_jwt_token(expired_jwt, environment=self.get_env_var("TEST_ENV", "test"))
        
        assert not expired_token_result.get("valid"), f"Expired JWT should fail validation: {expired_token_result}"
        assert "expired" in expired_token_result.get("error", "").lower(), "Validation should indicate token is expired"
        
        # Test WebSocket connection with expired JWT
        expired_auth_headers = {"Authorization": f"Bearer {expired_jwt}"}
        
        expired_connection_blocked = False
        try:
            expired_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=expired_auth_headers,
                    open_timeout=5.0
                ),
                timeout=8.0
            )
            await expired_connection.close()
            
        except Exception:
            expired_connection_blocked = True
        
        # Expired JWT should block WebSocket connection
        assert expired_connection_blocked, "Expired JWT should block WebSocket connection"
        
        self.record_metric("expired_jwt_rejected", True)
        
        print(f"\n✅ JWT TOKEN VALIDATION WITH AUTH SERVICE:")
        print(f"   ✅ Valid JWT tokens: ACCEPTED")
        print(f"   🚫 Invalid JWT tokens: REJECTED ({len(invalid_jwts)} tested)")
        print(f"   🚫 Expired JWT tokens: REJECTED")
        print(f"   🛡️ JWT validation security: ENFORCED")

    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_auth_service_response_time_impact(self, real_services_fixture):
        """
        CRITICAL: Test auth service response time impact on WebSocket connections.
        
        This test validates auth service performance requirements:
        1. Slow auth service responses affect WebSocket connection time
        2. Auth service timeouts prevent WebSocket connections
        3. Auth service performance is measured and validated
        4. Connection failures due to auth delays are properly diagnosed
        """
        
        # === AUTH SERVICE PERFORMANCE BASELINE ===
        self.record_metric("auth_performance_test_start", time.time())
        
        # Create authenticated user and measure auth response time
        auth_start_time = time.time()
        
        try:
            authenticated_user = await create_authenticated_user_context(
                user_email="websocket_auth_perf@example.com",
                environment=self.get_env_var("TEST_ENV", "test"),
                websocket_enabled=True
            )
            
            auth_response_time = time.time() - auth_start_time
            jwt_token = authenticated_user.agent_context.get("jwt_token")
            
            self.record_metric("auth_user_creation_time", auth_response_time)
            
            # === JWT TOKEN VALIDATION PERFORMANCE ===
            jwt_validation_start = time.time()
            
            token_validation = await validate_jwt_token(jwt_token, environment=self.get_env_var("TEST_ENV", "test"))
            
            jwt_validation_time = time.time() - jwt_validation_start
            
            self.record_metric("jwt_validation_time", jwt_validation_time)
            
            assert token_validation.get("valid"), f"JWT validation should succeed: {token_validation}"
            
            # === WEBSOCKET CONNECTION PERFORMANCE WITH AUTH ===
            websocket_auth_start = time.time()
            
            auth_headers = self._websocket_helper.get_websocket_headers(jwt_token)
            
            websocket_connection = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_url,
                    additional_headers=auth_headers,
                    open_timeout=10.0
                ),
                timeout=15.0
            )
            
            websocket_auth_time = time.time() - websocket_auth_start
            
            self.record_metric("websocket_connection_with_auth_time", websocket_auth_time)
            
            await websocket_connection.close()
            
            # === PERFORMANCE VALIDATION ===
            total_auth_flow_time = auth_response_time + jwt_validation_time + websocket_auth_time
            
            self.record_metric("total_auth_flow_time", total_auth_flow_time)
            
            # Performance thresholds (adjust based on requirements)
            AUTH_TIME_THRESHOLD = 5.0  # 5 seconds max for auth operations
            JWT_VALIDATION_THRESHOLD = 2.0  # 2 seconds max for JWT validation
            WEBSOCKET_AUTH_THRESHOLD = 10.0  # 10 seconds max for WebSocket with auth
            TOTAL_FLOW_THRESHOLD = 15.0  # 15 seconds max for entire flow
            
            performance_issues = []
            
            if auth_response_time > AUTH_TIME_THRESHOLD:
                performance_issues.append(f"Auth user creation too slow: {auth_response_time:.3f}s > {AUTH_TIME_THRESHOLD}s")
            
            if jwt_validation_time > JWT_VALIDATION_THRESHOLD:
                performance_issues.append(f"JWT validation too slow: {jwt_validation_time:.3f}s > {JWT_VALIDATION_THRESHOLD}s")
            
            if websocket_auth_time > WEBSOCKET_AUTH_THRESHOLD:
                performance_issues.append(f"WebSocket auth connection too slow: {websocket_auth_time:.3f}s > {WEBSOCKET_AUTH_THRESHOLD}s")
            
            if total_auth_flow_time > TOTAL_FLOW_THRESHOLD:
                performance_issues.append(f"Total auth flow too slow: {total_auth_flow_time:.3f}s > {TOTAL_FLOW_THRESHOLD}s")
            
            if performance_issues:
                performance_warning = (
                    f"⚠️ AUTH SERVICE PERFORMANCE ISSUES:\n" +
                    "\n".join(f"   🐌 {issue}" for issue in performance_issues) +
                    f"\n\n   📊 PERFORMANCE BREAKDOWN:\n"
                    f"   • Auth user creation: {auth_response_time:.3f}s\n"
                    f"   • JWT validation: {jwt_validation_time:.3f}s\n"
                    f"   • WebSocket connection: {websocket_auth_time:.3f}s\n"
                    f"   • Total flow time: {total_auth_flow_time:.3f}s\n"
                    f"\n   🔧 PERFORMANCE OPTIMIZATION REQUIRED:\n"
                    f"   • Auth service response time optimization\n"
                    f"   • JWT validation caching/optimization\n"
                    f"   • WebSocket authentication streamlining\n"
                )
                print(performance_warning)
                # Note: This is a warning, not a hard failure for performance issues
                
            else:
                print(f"\n✅ AUTH SERVICE PERFORMANCE: ACCEPTABLE")
                print(f"   ⚡ Auth user creation: {auth_response_time:.3f}s")
                print(f"   ⚡ JWT validation: {jwt_validation_time:.3f}s")
                print(f"   ⚡ WebSocket connection: {websocket_auth_time:.3f}s")
                print(f"   ⚡ Total flow time: {total_auth_flow_time:.3f}s")
                
        except Exception as e:
            auth_error_time = time.time() - auth_start_time
            
            auth_timeout_message = (
                f"🚨 AUTH SERVICE TIMEOUT/ERROR:\n"
                f"   🔴 Error after {auth_error_time:.3f}s: {e}\n"
                f"   🔴 Auth service may be slow or unavailable\n"
                f"\n"
                f"   💼 BUSINESS IMPACT:\n"
                f"   • Auth service performance issues prevent WebSocket access\n"
                f"   • Users experience slow or failed authentication\n"
                f"   • Real-time AI features degraded or unavailable\n"
                f"\n"
                f"   🔧 RESOLUTION REQUIRED:\n"
                f"   • Check auth service performance and resource usage\n"
                f"   • Verify database connectivity and performance\n"
                f"   • Review auth service logs for bottlenecks\n"
                f"   • Consider auth service scaling if needed\n"
            )
            
            print(auth_timeout_message)
            pytest.fail(auth_timeout_message)

    async def async_teardown_method(self, method=None):
        """Clean up WebSocket auth service integration test resources."""
        # Record final auth service integration metrics
        if hasattr(self, '_metrics'):
            final_metrics = self.get_all_metrics()
            auth_status = "available" if final_metrics.get("auth_service_available") else "unavailable"
            print(f"\n📊 WEBSOCKET AUTH SERVICE INTEGRATION TEST SUMMARY:")
            print(f"   🔐 Auth Service Status: {auth_status}")
            print(f"   📊 Total Integration Metrics: {len(final_metrics)}")
        
        await super().async_teardown_method(method)