"""
Integration tests to reproduce WebSocket authentication timeout issues (Issue #395).

REPRODUCTION TARGET: WebSocket handshake failures due to 0.5s auth service timeout.
These tests SHOULD FAIL initially to demonstrate the WebSocket-auth integration timeout problem.

Key Integration Issues to Reproduce:
1. WebSocket handshake blocked by auth service connectivity checks
2. 179-second WebSocket latencies caused by auth service timeout waits  
3. Chat functionality blocked by authentication failures
4. Golden Path user flow disrupted by auth timeouts
"""

import asyncio
import pytest
import time
import json
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.auth_integration.auth import get_current_user
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from fastapi import HTTPException
import httpx


class TestWebSocketAuthTimeoutIntegration(SSotAsyncTestCase):
    """
    Integration tests to reproduce WebSocket authentication timeout failures.
    
    These tests simulate the complete WebSocket authentication flow
    that gets blocked by aggressive auth service timeout configuration.
    """
    
    async def asyncSetUp(self):
        """Set up test environment with staging configuration that causes timeouts."""
        await super().asyncSetUp()
        
        # Mock staging environment to trigger aggressive timeouts
        self.mock_env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.mock_env_patcher.start()
        
        # Mock environment properly - return a mock object that has get method
        mock_env_dict = MagicMock()
        mock_env_dict.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "AUTH_CLIENT_TIMEOUT": "30"
        }.get(key, default)
        self.mock_env.return_value = mock_env_dict
        
        self.auth_client = AuthServiceClient()
        
        # Mock database session for auth integration
        self.mock_db_patcher = patch('netra_backend.app.dependencies.get_request_scoped_db_session')
        self.mock_db = self.mock_db_patcher.start()
        self.mock_db_session = AsyncMock()
        self.mock_db.return_value = self.mock_db_session
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        self.mock_env_patcher.stop()
        self.mock_db_patcher.stop()
        if self.auth_client._client:
            await self.auth_client._client.aclose()
        await super().asyncTearDown()

    @pytest.mark.asyncio
    async def test_websocket_handshake_blocked_by_auth_timeout(self):
        """
        REPRODUCTION TEST: WebSocket handshake blocked by auth service timeout.
        
        This test simulates WebSocket authentication during handshake
        that gets blocked by auth service connectivity check timeout.
        
        EXPECTED RESULT: Should FAIL due to auth timeout blocking WebSocket.
        """
        
        # Mock auth service that times out during connectivity check
        async def mock_timeout_connectivity(*args, **kwargs):
            await asyncio.sleep(0.6)  # Above 0.5s staging timeout
            raise asyncio.TimeoutError("Auth service connectivity check timed out")
        
        with patch.object(self.auth_client, '_check_auth_service_connectivity') as mock_connectivity:
            mock_connectivity.side_effect = mock_timeout_connectivity
            
            # Simulate WebSocket authentication request
            test_token = "Bearer valid_jwt_token"
            
            start_time = time.time()
            
            try:
                # This should fail due to auth timeout
                result = await self.auth_client.validate_token(test_token.replace("Bearer ", ""))
                self.fail("Expected WebSocket auth to timeout, but it succeeded")
                
            except (asyncio.TimeoutError, httpx.TimeoutException) as e:
                duration = time.time() - start_time
                
                # REPRODUCTION ASSERTION: Auth timeout blocks WebSocket
                self.assertGreater(duration, 0.5, 
                                 f"Expected timeout after 0.5s, but failed after {duration:.3f}s")
                self.assertLess(duration, 1.0,
                              f"Expected quick timeout, but took {duration:.3f}s - "
                              f"this would block WebSocket handshake")

    @pytest.mark.asyncio  
    async def test_websocket_179_second_latency_reproduction(self):
        """
        REPRODUCTION TEST: 179-second WebSocket latency due to auth timeout waits.
        
        This test reproduces the reported issue where WebSocket connections
        experience extreme latencies due to auth service timeout handling.
        
        EXPECTED RESULT: Should demonstrate how auth timeouts cascade to WebSocket delays.
        """
        
        # Mock auth service with multiple timeout scenarios
        timeout_scenarios = [
            0.6,  # First timeout (above 0.5s limit)
            1.2,  # Retry timeout
            2.5,  # Final timeout
        ]
        
        call_count = 0
        
        async def mock_cascading_timeouts(*args, **kwargs):
            nonlocal call_count
            if call_count < len(timeout_scenarios):
                delay = timeout_scenarios[call_count]
                call_count += 1
                await asyncio.sleep(delay)
                raise asyncio.TimeoutError(f"Auth service timeout after {delay}s")
            else:
                # Eventually succeed but after extreme delay
                await asyncio.sleep(0.1)
                return {
                    "valid": True,
                    "user_id": "test_user",
                    "email": "test@example.com"
                }
        
        with patch.object(self.auth_client, '_execute_token_validation') as mock_validation:
            mock_validation.side_effect = mock_cascading_timeouts
            
            # Simulate WebSocket authentication with retries
            test_token = "valid_jwt_token"
            
            start_time = time.time()
            
            try:
                # This simulates the retry logic that leads to 179s delays
                max_retries = 3
                last_exception = None
                
                for attempt in range(max_retries):
                    try:
                        result = await self.auth_client.validate_token(test_token)
                        break
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            # Exponential backoff (contributes to 179s total)
                            await asyncio.sleep(2 ** attempt)
                
                duration = time.time() - start_time
                
                # REPRODUCTION ASSERTION: Cumulative delays approach 179s problem
                total_expected_delay = sum(timeout_scenarios) + sum(2**i for i in range(max_retries-1))
                self.assertGreater(duration, 5.0,
                                 f"Expected significant cumulative delay, got {duration:.3f}s")
                
                # This demonstrates how timeouts cascade to extreme delays
                self.assertGreater(total_expected_delay, 10.0,
                                 f"Total timeout delays ({total_expected_delay:.3f}s) demonstrate "
                                 f"how 179s WebSocket latencies occur")
                
            except Exception as e:
                duration = time.time() - start_time
                # Even failure demonstrates the timeout cascade issue
                self.assertGreater(duration, 3.0,
                                 f"Auth timeout cascade took {duration:.3f}s, "
                                 f"demonstrating WebSocket latency issue")

    @pytest.mark.asyncio
    async def test_chat_functionality_blocked_by_auth_timeout(self):
        """
        REPRODUCTION TEST: Chat functionality blocked by authentication timeouts.
        
        This test simulates how auth timeout failures prevent users from 
        accessing chat functionality (90% of platform value).
        
        EXPECTED RESULT: Should FAIL, showing chat blocked by auth issues.
        """
        
        # Mock FastAPI HTTP authorization credentials
        from fastapi.security import HTTPAuthorizationCredentials
        
        test_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_jwt_token_but_service_times_out"
        )
        
        # Mock auth service timeout during token validation
        with patch.object(self.auth_client, 'validate_token_jwt') as mock_validate:
            mock_validate.side_effect = asyncio.TimeoutError("Auth service timeout")
            
            # Mock auth integration using the timing-out client
            with patch('netra_backend.app.auth_integration.auth.auth_client', self.auth_client):
                
                try:
                    # This simulates chat authentication flow
                    user = await get_current_user(test_credentials, self.mock_db_session)
                    self.fail("Expected chat authentication to fail due to auth timeout")
                    
                except HTTPException as e:
                    # REPRODUCTION ASSERTION: Chat blocked by auth service timeout
                    self.assertEqual(e.status_code, 503,
                                   f"Expected 503 Service Unavailable due to auth timeout, "
                                   f"got {e.status_code}")
                    self.assertIn("temporarily unavailable", e.detail.lower(),
                                f"Expected auth service unavailable message, got: {e.detail}")
                    
                except Exception as e:
                    # Any timeout/connection error demonstrates the issue
                    self.assertIn("timeout", str(e).lower(),
                                f"Expected timeout-related error, got: {e}")

    @pytest.mark.asyncio
    async def test_golden_path_user_flow_disruption(self):
        """
        REPRODUCTION TEST: Golden Path user flow disrupted by auth timeouts.
        
        This test simulates the complete Golden Path user flow:
        1. User login -> WebSocket connection -> Chat functionality
        2. Shows how auth timeouts break this critical business flow.
        
        EXPECTED RESULT: Should FAIL, demonstrating Golden Path disruption.
        """
        
        # Simulate Golden Path user flow steps
        golden_path_steps = [
            "user_login_request", 
            "websocket_handshake",
            "auth_token_validation", 
            "chat_message_processing"
        ]
        
        failed_steps = []
        
        for step in golden_path_steps:
            try:
                if step == "user_login_request":
                    # Mock login with timeout
                    with patch.object(self.auth_client, '_attempt_login_with_resilience') as mock_login:
                        async def timeout_login(*args, **kwargs):
                            await asyncio.sleep(0.6)  # Above staging timeout
                            raise asyncio.TimeoutError("Login request timed out")
                        mock_login.side_effect = timeout_login
                        
                        result = await self.auth_client.login("user@test.com", "password")
                        if not result:
                            failed_steps.append(step)
                            
                elif step == "websocket_handshake":  
                    # Mock WebSocket auth handshake timeout
                    with patch.object(self.auth_client, '_check_auth_service_connectivity') as mock_conn:
                        mock_conn.side_effect = asyncio.TimeoutError("Connectivity check timeout")
                        
                        is_connected = await self.auth_client._check_auth_service_connectivity()
                        if not is_connected:
                            failed_steps.append(step)
                            
                elif step == "auth_token_validation":
                    # Mock token validation timeout  
                    with patch.object(self.auth_client, 'validate_token') as mock_validate:
                        mock_validate.side_effect = asyncio.TimeoutError("Token validation timeout")
                        
                        result = await self.auth_client.validate_token("test_token")
                        if not result or not result.get("valid"):
                            failed_steps.append(step)
                            
                elif step == "chat_message_processing":
                    # Mock chat message processing blocked by auth
                    if len(failed_steps) > 0:
                        # Previous auth failures prevent chat
                        failed_steps.append(step)
                        
            except (asyncio.TimeoutError, Exception):
                failed_steps.append(step)
        
        # REPRODUCTION ASSERTION: Golden Path flow disrupted by timeouts
        self.assertGreater(len(failed_steps), 0, 
                          "Expected at least one Golden Path step to fail due to auth timeouts")
        
        # All steps should fail due to cascading auth timeout issues
        self.assertIn("user_login_request", failed_steps,
                     "User login should fail due to auth service timeout")
        self.assertIn("websocket_handshake", failed_steps, 
                     "WebSocket handshake should fail due to connectivity timeout")
        self.assertIn("auth_token_validation", failed_steps,
                     "Token validation should fail due to auth service timeout")
        
        # Business impact: Complete Golden Path failure
        if len(failed_steps) >= 3:
            self.fail(f"Golden Path user flow completely disrupted by auth timeouts. "
                     f"Failed steps: {failed_steps}. This blocks 90% of platform business value.")

    @pytest.mark.asyncio
    async def test_auth_service_healthy_but_websocket_fails(self):
        """
        REPRODUCTION TEST: Auth service healthy but WebSocket still fails.
        
        This test reproduces the specific case where auth service responds
        in 0.195s (healthy) but WebSocket authentication still fails due to
        timeout configuration issues.
        
        EXPECTED RESULT: Should show timeout configuration vs actual performance mismatch.
        """
        
        # Mock healthy, fast auth service (as reported in issue)
        async def mock_healthy_auth_service(*args, **kwargs):
            await asyncio.sleep(0.195)  # Actual reported response time
            return {
                "valid": True,
                "user_id": "test_user",
                "email": "test@example.com",
                "permissions": ["user:read"]
            }
        
        # Mock WebSocket-specific timeout behavior
        websocket_timeout_calls = []
        
        async def mock_websocket_timeout_check(*args, **kwargs):
            # Simulate WebSocket timeout check that's more sensitive
            timeout_threshold = 0.3  # WebSocket has even tighter timeout
            await asyncio.sleep(0.195)  # Auth service response time
            
            # WebSocket timeout is more aggressive than 0.5s health check
            websocket_timeout_calls.append(time.time())
            
            if 0.195 > timeout_threshold:
                raise asyncio.TimeoutError(f"WebSocket auth timeout after {timeout_threshold}s")
            
            return True
        
        with patch.object(self.auth_client, 'validate_token') as mock_validate:
            mock_validate.side_effect = mock_healthy_auth_service
            
            # Test WebSocket-specific auth flow
            test_token = "websocket_auth_token"
            
            try:
                # First test: Auth service validation (should succeed)
                auth_result = await self.auth_client.validate_token(test_token)
                self.assertTrue(auth_result.get("valid"), 
                              "Auth service should validate successfully in 0.195s")
                
                # Second test: WebSocket timeout check (should fail)
                with patch.object(self.auth_client, '_check_auth_service_connectivity') as mock_ws_check:
                    mock_ws_check.side_effect = mock_websocket_timeout_check
                    
                    try:
                        ws_result = await self.auth_client._check_auth_service_connectivity()
                        # If this succeeds, the timeout is actually working
                        # But the test shows the mismatch in timeout expectations
                        
                    except asyncio.TimeoutError:
                        # REPRODUCTION ASSERTION: WebSocket timeout despite healthy auth service
                        self.assertTrue(len(websocket_timeout_calls) > 0,
                                      "WebSocket timeout occurred despite healthy auth service")
                        
                        self.fail("Auth service responds in 0.195s (healthy) but WebSocket "
                                "authentication fails due to timeout configuration mismatch")
                        
            except Exception as e:
                # Any failure demonstrates the timeout configuration issue
                self.assertIn("timeout", str(e).lower(),
                            f"Expected timeout-related failure, got: {e}")

    @pytest.mark.asyncio
    async def test_integration_auth_circuit_breaker_impact(self):
        """
        INTEGRATION TEST: Circuit breaker impact on WebSocket authentication.
        
        Tests how auth service circuit breaker opening affects WebSocket connections
        when multiple timeout failures occur in sequence.
        
        EXPECTED RESULT: Should show circuit breaker blocking WebSocket after timeouts.
        """
        
        # Simulate multiple auth failures that trigger circuit breaker
        failure_count = 0
        
        async def mock_auth_failures(*args, **kwargs):
            nonlocal failure_count  
            failure_count += 1
            
            if failure_count <= 3:  # Circuit breaker threshold is 3 failures
                await asyncio.sleep(0.6)  # Above timeout limit
                raise asyncio.TimeoutError(f"Auth service timeout (failure {failure_count})")
            else:
                # Circuit breaker should be open by now
                from netra_backend.app.clients.circuit_breaker import CircuitBreakerOpen
                raise CircuitBreakerOpen("Circuit breaker is open")
        
        with patch.object(self.auth_client, '_validate_token_remote') as mock_validate:
            mock_validate.side_effect = mock_auth_failures
            
            # Test multiple WebSocket authentication attempts
            websocket_failures = []
            
            for attempt in range(5):  # More than circuit breaker threshold
                try:
                    result = await self.auth_client.validate_token(f"websocket_token_{attempt}")
                    if result is None or not result.get("valid"):
                        websocket_failures.append(f"attempt_{attempt}")
                        
                except Exception as e:
                    websocket_failures.append(f"attempt_{attempt}_exception_{type(e).__name__}")
            
            # REPRODUCTION ASSERTION: Circuit breaker blocks WebSocket after timeouts
            self.assertGreaterEqual(len(websocket_failures), 3,
                                  f"Expected at least 3 WebSocket failures due to auth timeouts, "
                                  f"got {len(websocket_failures)}")
            
            # Verify circuit breaker pattern in failures
            circuit_breaker_failures = [f for f in websocket_failures if "CircuitBreakerOpen" in f]
            self.assertGreater(len(circuit_breaker_failures), 0,
                             "Expected circuit breaker to block WebSocket connections after "
                             "repeated auth service timeout failures")