"""
Integration tests for WebSocket authentication protocol negotiation - DESIGNED TO FAIL INITIALLY

Purpose: Test real WebSocket connections with protocol arrays to reproduce authentication failures
Issue: Frontend sending ['jwt', token] instead of expected 'jwt.${token}' format  
Impact: WebSocket connection timeouts and authentication cascade failures in staging
Expected: These tests MUST FAIL initially to prove they detect the real issue

GitHub Issue: #171
Test Plan: /TEST_PLAN_WEBSOCKET_AUTH_PROTOCOL_MISMATCH.md

CRITICAL: Uses REAL SERVICES - no mocks for critical authentication flows
"""

import pytest
import asyncio
import base64
import json
import websockets
import ssl
from typing import List, Dict, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.docker_test_utility import DockerTestUtility
from test_framework.unified_docker_manager import UnifiedDockerManager

# Import authentication components
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService
from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
from netra_backend.app.auth_integration.auth import generate_access_token


class TestWebSocketAuthProtocolIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket authentication protocol - REAL SERVICES ONLY"""
    
    @classmethod
    async def asyncSetUpClass(cls):
        """Setup real services for integration testing"""
        await super().asyncSetUpClass()
        
        # Initialize Docker manager for real services
        cls.docker_manager = UnifiedDockerManager()
        cls.docker_utility = DockerTestUtility()
        
        # Start necessary services
        await cls.docker_utility.ensure_services_running([
            'backend', 
            'auth_service',
            'redis',
            'postgres'
        ])
        
        # Wait for services to be ready
        await cls.docker_utility.wait_for_service_health('backend', timeout=30)
        await cls.docker_utility.wait_for_service_health('auth_service', timeout=30)
        
        # Get service URLs
        cls.backend_host = cls.docker_utility.get_service_host('backend')
        cls.backend_port = cls.docker_utility.get_service_port('backend', 8000)
        cls.websocket_url = f"ws://{cls.backend_host}:{cls.backend_port}/ws"
        
        # Initialize authentication components
        cls.auth_service = UnifiedAuthenticationService()
        cls.context_extractor = WebSocketUserContextExtractor()
        
        # Create test tokens
        cls.test_user_payload = {
            "sub": "test_user_protocol_auth",
            "email": "test@netra.ai", 
            "exp": 9999999999,  # Far future
            "iat": 1000000000
        }
        
        # Generate real JWT token using production auth service
        cls.valid_jwt_token = await generate_access_token(
            user_id="test_user_protocol_auth",
            email="test@netra.ai"
        )
        
        # Create base64url encoded version for subprotocol
        cls.encoded_jwt_token = base64.urlsafe_b64encode(
            cls.valid_jwt_token.encode()
        ).decode().rstrip('=')
        
    @classmethod
    async def asyncTearDownClass(cls):
        """Cleanup after tests"""
        await super().asyncTearDownClass()
        # Services will be cleaned up by Docker manager
        
    async def create_websocket_connection(
        self, 
        subprotocols: List[str], 
        timeout: int = 10
    ) -> Optional[websockets.WebSocketClientProtocol]:
        """
        Create a WebSocket connection with specified subprotocols
        
        Args:
            subprotocols: List of subprotocol strings to send
            timeout: Connection timeout in seconds
            
        Returns:
            WebSocket connection or None if failed
        """
        try:
            # Create connection with real backend
            connection = await asyncio.wait_for(
                websockets.connect(
                    self.websocket_url,
                    subprotocols=subprotocols,
                    # Disable SSL verification for local testing
                    ssl=ssl.SSLContext() if self.websocket_url.startswith('wss') else None
                ),
                timeout=timeout
            )
            return connection
        except Exception as e:
            self.logger.error(f"WebSocket connection failed: {e}")
            return None

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.websocket_auth_protocol
    async def test_websocket_connection_with_correct_protocol_format(self):
        """
        Test WebSocket connection with correct protocol format
        
        Protocol: ['jwt-auth', 'jwt.base64url_encoded_token']  
        Expected: Successful connection and authentication
        
        DIFFICULTY: Medium (15 minutes)
        REAL SERVICES: Yes (Docker backend + real JWT)
        STATUS: Should PASS (validates correct implementation)
        """
        # Arrange: Create correct protocol format
        correct_subprotocols = ["jwt-auth", f"jwt.{self.encoded_jwt_token}"]
        
        # Act: Try to connect with correct format
        connection = await self.create_websocket_connection(correct_subprotocols)
        
        # Assert: Should successfully connect
        assert connection is not None, \
            "WebSocket connection should succeed with correct protocol format"
        
        try:
            # Verify connection is actually established
            await connection.ping()
            
            # Try to send a test message to verify authentication worked
            test_message = {
                "type": "ping",
                "data": {"message": "test_auth_verification"}
            }
            
            await connection.send(json.dumps(test_message))
            
            # Wait for response (with timeout)
            response = await asyncio.wait_for(connection.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            # Should get a response, indicating authentication worked
            assert response_data is not None, "Should receive response from authenticated connection"
            
        except asyncio.TimeoutError:
            pytest.fail("Connection timed out - authentication may have failed")
        except Exception as e:
            pytest.fail(f"Connection error after establishment: {e}")
        finally:
            if connection:
                await connection.close()

    @pytest.mark.integration  
    @pytest.mark.real_services
    @pytest.mark.websocket_auth_protocol
    @pytest.mark.bug_reproduction
    async def test_websocket_connection_with_incorrect_protocol_format_bug_reproduction(self):
        """
        Test WebSocket connection with incorrect protocol format (REPRODUCES CURRENT BUG)
        
        Protocol: ['jwt', 'base64url_encoded_token'] (as separate elements - current bug)
        Expected: Connection failure with NO_TOKEN error
        
        DIFFICULTY: Medium (15 minutes)
        REAL SERVICES: Yes (Docker backend + real JWT)
        STATUS: Should FAIL initially (connection times out), PASS after fix (proper error handling)
        """
        # Arrange: Create INCORRECT protocol format (reproduces bug)
        # Frontend is sending JWT as separate array element instead of 'jwt.token'
        incorrect_subprotocols = ["jwt", self.encoded_jwt_token]  # BUG FORMAT
        
        # Act: Try to connect with incorrect format
        connection = await self.create_websocket_connection(
            incorrect_subprotocols, 
            timeout=15  # Longer timeout to capture failure mode
        )
        
        # Assert: Connection should fail or timeout
        # THIS TEST IS DESIGNED TO FAIL INITIALLY (reproduces staging issue)
        if connection is None:
            # Connection failed immediately - expected with bug
            self.logger.info("Connection failed immediately - this reproduces the staging bug")
            return
        
        try:
            # If connection somehow succeeded, try to authenticate
            test_message = {
                "type": "ping", 
                "data": {"message": "test_bug_reproduction"}
            }
            
            await connection.send(json.dumps(test_message))
            
            # This should timeout because authentication should fail
            response = await asyncio.wait_for(connection.recv(), timeout=10.0)
            
            # If we get here, something is wrong - the bug isn't reproduced
            pytest.fail(
                "Connection unexpectedly succeeded with incorrect protocol format. "
                "This suggests the bug has been fixed or test is not reproducing correctly."
            )
            
        except asyncio.TimeoutError:
            # Expected behavior with the bug - connection hangs due to auth failure
            self.logger.info("Connection timeout - successfully reproduced authentication bug")
            pytest.fail(
                "Connection timed out as expected with incorrect protocol format. "
                "This reproduces the staging authentication bug."
            )
        except Exception as e:
            # Other connection errors are also expected with the bug
            self.logger.info(f"Connection error - reproduced bug: {e}")
            pytest.fail(f"Connection failed with error (reproduces bug): {e}")
        finally:
            if connection:
                await connection.close()

    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.websocket_auth_protocol
    async def test_websocket_handshake_timeout_reproduction(self):
        """
        Test reproduction of handshake timeout scenario from staging
        
        Simulates exact staging conditions causing handshake timeouts
        
        DIFFICULTY: High (25 minutes) 
        REAL SERVICES: Yes (Docker with GCP-like network conditions)
        STATUS: Should FAIL initially (timeout), PASS after fix
        """
        # Arrange: Test various problematic protocol combinations
        problematic_cases = [
            {
                "subprotocols": ["jwt", self.encoded_jwt_token],  # Main bug
                "description": "JWT token as separate array element",
                "expected_behavior": "timeout_or_failure"
            },
            {
                "subprotocols": ["jwt-auth", self.encoded_jwt_token],  # Missing jwt. prefix
                "description": "Missing jwt. prefix",
                "expected_behavior": "timeout_or_failure" 
            },
            {
                "subprotocols": ["Bearer", f"Bearer {self.valid_jwt_token}"],  # Wrong auth type
                "description": "Bearer token format (wrong type)",
                "expected_behavior": "timeout_or_failure"
            },
            {
                "subprotocols": [],  # No protocols at all
                "description": "No subprotocols provided",
                "expected_behavior": "immediate_failure"
            }
        ]
        
        for case in problematic_cases:
            self.logger.info(f"Testing handshake timeout for: {case['description']}")
            
            # Act: Try connection with problematic protocols
            start_time = asyncio.get_event_loop().time()
            
            connection = await self.create_websocket_connection(
                case["subprotocols"],
                timeout=20  # Long timeout to observe behavior
            )
            
            duration = asyncio.get_event_loop().time() - start_time
            
            if case["expected_behavior"] == "immediate_failure":
                # Should fail quickly
                assert connection is None, f"Expected immediate failure for: {case['description']}"
                assert duration < 5.0, f"Should fail quickly, took {duration}s"
            else:
                # Should timeout or fail after longer period
                if connection is not None:
                    try:
                        # If connected, try to use it - should timeout
                        await asyncio.wait_for(connection.recv(), timeout=5.0)
                        pytest.fail(
                            f"Unexpected success with {case['description']}. "
                            "This may indicate the bug is fixed or test needs adjustment."
                        )
                    except asyncio.TimeoutError:
                        # Expected - reproduces the staging timeout issue
                        self.logger.info(f"Successfully reproduced timeout for: {case['description']}")
                        pytest.fail(
                            f"Connection timeout reproduced for {case['description']} - this is the staging bug"
                        )
                    finally:
                        await connection.close()
                else:
                    # Connection failed - also reproduces the issue
                    self.logger.info(f"Connection failure reproduced for: {case['description']}")

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.websocket_auth_protocol
    async def test_message_routing_after_auth_failure_cascade(self):
        """
        Test message routing behavior after authentication failure
        
        Validates that auth failures don't cascade to message routing errors
        
        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes (full WebSocket + message routing stack)
        STATUS: Should FAIL initially (cascade failures), PASS after fix
        """
        # Arrange: Create connections - one good, one bad
        good_protocols = ["jwt-auth", f"jwt.{self.encoded_jwt_token}"]
        bad_protocols = ["jwt", self.encoded_jwt_token]  # Bug format
        
        # Track connections for cleanup
        connections = []
        
        try:
            # Act 1: Establish good connection first
            good_connection = await self.create_websocket_connection(good_protocols)
            if good_connection:
                connections.append(good_connection)
                
                # Verify good connection works
                await good_connection.send(json.dumps({
                    "type": "ping",
                    "data": {"test": "good_connection"}
                }))
                
                good_response = await asyncio.wait_for(
                    good_connection.recv(), 
                    timeout=5.0
                )
                assert good_response is not None, "Good connection should work"
            
            # Act 2: Try to establish bad connection (should fail)
            bad_connection = await self.create_websocket_connection(bad_protocols, timeout=10)
            
            if bad_connection:
                connections.append(bad_connection)
                
                try:
                    # This should fail or timeout
                    await bad_connection.send(json.dumps({
                        "type": "ping", 
                        "data": {"test": "bad_connection"}
                    }))
                    
                    bad_response = await asyncio.wait_for(
                        bad_connection.recv(),
                        timeout=8.0
                    )
                    
                    # If we get here, the bug isn't being reproduced
                    pytest.fail("Bad connection unexpectedly succeeded - bug may be fixed")
                    
                except asyncio.TimeoutError:
                    # Expected - bad connection times out
                    self.logger.info("Bad connection timed out as expected")
                    
            # Act 3: Verify good connection still works (no cascade failure)
            if good_connection:
                await good_connection.send(json.dumps({
                    "type": "ping",
                    "data": {"test": "verify_no_cascade"}
                }))
                
                try:
                    verify_response = await asyncio.wait_for(
                        good_connection.recv(),
                        timeout=5.0
                    )
                    
                    # This should work - no cascade failure
                    assert verify_response is not None, \
                        "Good connection should not be affected by bad connection failures"
                        
                except asyncio.TimeoutError:
                    pytest.fail(
                        "Cascade failure detected - bad auth failure affected good connection"
                    )
                    
        except Exception as e:
            # Any exceptions here indicate cascade failures or system instability
            pytest.fail(f"System instability or cascade failure detected: {e}")
            
        finally:
            # Cleanup all connections
            for conn in connections:
                if conn and not conn.closed:
                    await conn.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.websocket_auth_protocol
    async def test_concurrent_auth_protocol_scenarios(self):
        """
        Test concurrent WebSocket connections with different protocol formats
        
        Validates system behavior with mixed correct/incorrect protocol formats
        
        DIFFICULTY: High (20 minutes)
        REAL SERVICES: Yes (concurrent real connections)
        STATUS: Should FAIL initially (some connections fail), improve after fix
        """
        # Arrange: Create multiple connection scenarios
        connection_scenarios = [
            {
                "name": "correct_format",
                "protocols": ["jwt-auth", f"jwt.{self.encoded_jwt_token}"],
                "should_succeed": True
            },
            {
                "name": "bug_format_1", 
                "protocols": ["jwt", self.encoded_jwt_token],
                "should_succeed": False  # This is the bug
            },
            {
                "name": "bug_format_2",
                "protocols": ["jwt-auth", self.encoded_jwt_token],  # Missing jwt. prefix
                "should_succeed": False
            },
            {
                "name": "wrong_auth_type",
                "protocols": ["Bearer", f"Bearer {self.valid_jwt_token}"],
                "should_succeed": False
            }
        ]
        
        # Act: Create all connections concurrently
        connection_tasks = []
        for scenario in connection_scenarios:
            task = asyncio.create_task(
                self.create_websocket_connection(scenario["protocols"], timeout=15)
            )
            task.scenario = scenario  # Attach scenario info
            connection_tasks.append(task)
        
        # Wait for all connections to complete or timeout
        connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Analyze results
        successful_connections = []
        failed_connections = []
        
        for i, (task, result) in enumerate(zip(connection_tasks, connection_results)):
            scenario = task.scenario
            
            if isinstance(result, Exception):
                failed_connections.append({
                    "scenario": scenario["name"],
                    "error": str(result),
                    "expected_to_fail": not scenario["should_succeed"]
                })
            elif result is None:
                failed_connections.append({
                    "scenario": scenario["name"], 
                    "error": "Connection returned None",
                    "expected_to_fail": not scenario["should_succeed"]
                })
            else:
                successful_connections.append({
                    "scenario": scenario["name"],
                    "connection": result,
                    "expected_to_succeed": scenario["should_succeed"]
                })
        
        try:
            # Assert: Check if results match expectations
            success_count = len(successful_connections)
            failure_count = len(failed_connections)
            
            self.logger.info(f"Connection results: {success_count} successful, {failure_count} failed")
            
            # The bug should cause most connections to fail
            # Only the correct format should succeed
            expected_successes = sum(1 for s in connection_scenarios if s["should_succeed"])
            expected_failures = len(connection_scenarios) - expected_successes
            
            if success_count < expected_successes:
                # Some expected successes failed - indicates broader issues
                pytest.fail(
                    f"Expected {expected_successes} successful connections, got {success_count}. "
                    "This may indicate system instability beyond the protocol bug."
                )
            
            if success_count > expected_successes:
                # More successes than expected - bug may be fixed
                pytest.fail(
                    f"Expected {expected_successes} successful connections, got {success_count}. "
                    "This suggests the protocol bug has been fixed."
                )
            
            # Test message handling on successful connections
            for conn_info in successful_connections:
                connection = conn_info["connection"]
                scenario = conn_info["scenario"]
                
                try:
                    # Send test message
                    await connection.send(json.dumps({
                        "type": "ping",
                        "data": {"scenario": scenario}
                    }))
                    
                    # Should get response
                    response = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    assert response is not None, f"No response for {scenario}"
                    
                except asyncio.TimeoutError:
                    pytest.fail(f"Successful connection {scenario} timed out on message - cascade failure?")
                    
        finally:
            # Cleanup all successful connections
            for conn_info in successful_connections:
                if conn_info["connection"] and not conn_info["connection"].closed:
                    await conn_info["connection"].close()


class TestWebSocketUnifiedAuthIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket + unified auth service"""
    
    async def asyncSetUp(self):
        """Setup for each test"""
        await super().asyncSetUp()
        
        # Initialize services
        self.auth_service = UnifiedAuthenticationService()
        self.docker_utility = DockerTestUtility()
        
        # Ensure services are running
        await self.docker_utility.ensure_services_running(['backend', 'auth_service'])
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.websocket_unified_auth
    async def test_websocket_auth_with_real_jwt_tokens(self):
        """
        Test WebSocket authentication with real JWT tokens
        
        Uses actual JWT generation and validation services
        
        DIFFICULTY: Medium (15 minutes)
        REAL SERVICES: Yes (Auth service + JWT validator)
        STATUS: Should FAIL initially (protocol mismatch), PASS after fix
        """
        # Arrange: Generate real JWT token
        real_token = await generate_access_token(
            user_id="test_integration_user",
            email="integration@test.com"
        )
        
        encoded_token = base64.urlsafe_b64encode(real_token.encode()).decode().rstrip('=')
        
        # Test both correct and incorrect formats
        test_cases = [
            {
                "protocols": ["jwt-auth", f"jwt.{encoded_token}"],
                "should_work": True,
                "description": "Correct protocol format"
            },
            {
                "protocols": ["jwt", encoded_token],
                "should_work": False,
                "description": "Incorrect protocol format (bug)"
            }
        ]
        
        backend_url = f"ws://{self.docker_utility.get_service_host('backend')}:{self.docker_utility.get_service_port('backend', 8000)}/ws"
        
        for case in test_cases:
            self.logger.info(f"Testing: {case['description']}")
            
            try:
                # Act: Create connection
                connection = await asyncio.wait_for(
                    websockets.connect(backend_url, subprotocols=case["protocols"]),
                    timeout=10
                )
                
                if case["should_work"]:
                    # Should succeed - verify it works
                    await connection.send(json.dumps({"type": "ping"}))
                    response = await asyncio.wait_for(connection.recv(), timeout=5.0)
                    assert response is not None, "Should get response with correct format"
                else:
                    # Should fail - but if connection succeeded, it should timeout
                    await connection.send(json.dumps({"type": "ping"}))
                    
                    try:
                        response = await asyncio.wait_for(connection.recv(), timeout=8.0)
                        pytest.fail("Incorrect format unexpectedly worked")
                    except asyncio.TimeoutError:
                        # Expected timeout with incorrect format
                        pass
                        
                await connection.close()
                
            except Exception as e:
                if case["should_work"]:
                    pytest.fail(f"Correct format failed: {e}")
                else:
                    # Expected failure with incorrect format
                    self.logger.info(f"Expected failure with incorrect format: {e}")

    @pytest.mark.integration 
    @pytest.mark.real_services
    @pytest.mark.websocket_unified_auth
    async def test_websocket_auth_circuit_breaker_behavior(self):
        """
        Test circuit breaker behavior with repeated auth failures
        
        Validates circuit breaker doesn't trigger unnecessarily due to protocol issues
        
        DIFFICULTY: High (20 minutes)
        REAL SERVICES: Yes (full auth stack)
        STATUS: Should FAIL initially (unnecessary circuit breaking), improve after fix
        """
        # This test is complex and may require more setup
        # For now, we'll create a simplified version
        
        # Arrange: Generate token
        real_token = await generate_access_token(
            user_id="circuit_breaker_test",
            email="circuit@test.com"
        )
        encoded_token = base64.urlsafe_b64encode(real_token.encode()).decode().rstrip('=')
        
        backend_url = f"ws://{self.docker_utility.get_service_host('backend')}:{self.docker_utility.get_service_port('backend', 8000)}/ws"
        
        # Act: Make multiple failed attempts with incorrect protocol
        failure_count = 0
        max_attempts = 5
        
        for i in range(max_attempts):
            try:
                # Use incorrect protocol format
                connection = await asyncio.wait_for(
                    websockets.connect(backend_url, subprotocols=["jwt", encoded_token]),
                    timeout=8
                )
                
                await connection.send(json.dumps({"type": "ping"}))
                await asyncio.wait_for(connection.recv(), timeout=5.0)
                await connection.close()
                
            except Exception as e:
                failure_count += 1
                self.logger.info(f"Attempt {i+1} failed: {e}")
        
        # Assert: All should fail due to protocol issue
        assert failure_count == max_attempts, \
            f"Expected all {max_attempts} attempts to fail, got {failure_count} failures"
        
        # Now try with correct format - should still work (no circuit breaker)
        try:
            good_connection = await asyncio.wait_for(
                websockets.connect(backend_url, subprotocols=["jwt-auth", f"jwt.{encoded_token}"]),
                timeout=10
            )
            
            await good_connection.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(good_connection.recv(), timeout=5.0)
            
            assert response is not None, \
                "Correct protocol should work even after failures (no circuit breaker)"
                
            await good_connection.close()
            
        except Exception as e:
            pytest.fail(f"Circuit breaker may have triggered incorrectly: {e}")


# Test execution configuration
pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.authentication,
    pytest.mark.protocol_negotiation, 
    pytest.mark.real_services,
    pytest.mark.bug_reproduction
]


if __name__ == "__main__":
    # Allow running this file directly for quick testing
    pytest.main([__file__, "-v", "--tb=long", "-s"])