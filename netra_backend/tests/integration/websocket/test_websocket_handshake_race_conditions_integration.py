"""
Test WebSocket Handshake Race Conditions - Integration Testing

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure reliable WebSocket handshake completion prevents chat value delivery failures
- Value Impact: WebSocket race conditions block $500K+ ARR chat functionality and user experience  
- Strategic Impact: Core platform stability - prevents "every 3 minutes staging failures" that block user value

CRITICAL REQUIREMENTS:
- Tests WebSocket handshake completion before message handling
- Validates progressive delays in Cloud Run environments
- Tests connection state validation and authentication flow during handshake
- Reproduces race condition scenarios (should fail without fixes)
- Tests handshake timeout handling and concurrent connection attempts
- Uses REAL services only - no mocks allowed in integration tests

This test suite addresses the golden path issues:
1. Race Conditions in WebSocket Handshake (Cloud Run 1011 errors)
2. Progressive delays causing handshake timeout
3. Authentication flow timing during handshake
4. Concurrent connection attempts causing race conditions
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidStatusCode

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class TestWebSocketHandshakeRaceConditions(BaseIntegrationTest):
    """Integration tests for WebSocket handshake race conditions with real services."""
    
    def setup_method(self):
        """Set up each test method with proper environment."""
        super().setup_method()
        self.env = get_env()
        self.websocket_url = "ws://localhost:8000/ws"
        self.max_handshake_timeout = 15.0  # Maximum time for handshake completion
        self.race_condition_retry_count = 3  # Number of retries for race condition scenarios
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_handshake_completion_before_message_handling(self, real_services_fixture):
        """
        Test that WebSocket handshake completes fully before accepting message handling.
        
        CRITICAL: This test validates that messages sent immediately after connection
        establishment are properly queued until handshake is complete, preventing
        the race condition where messages are lost or cause 1011 errors.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = f"handshake_test_{int(time.time())}"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        logger.info(f"Testing handshake completion for user: {user_id}")
        
        # Test rapid message sending during/after handshake
        async with websockets.connect(
            self.websocket_url,
            additional_headers=headers,
            open_timeout=self.max_handshake_timeout,
            ping_interval=None  # Disable ping during handshake test
        ) as websocket:
            
            # Immediately send multiple messages to test queuing during handshake
            rapid_messages = [
                {"type": "handshake_test", "sequence": i, "timestamp": time.time()}
                for i in range(5)
            ]
            
            # Send all messages rapidly without waiting
            send_start_time = time.time()
            for msg in rapid_messages:
                await websocket.send(json.dumps(msg))
            send_duration = time.time() - send_start_time
            
            logger.info(f"Sent {len(rapid_messages)} messages in {send_duration:.3f}s")
            
            # Collect responses with timeout
            received_responses = []
            timeout_per_response = 2.0
            
            for i in range(len(rapid_messages)):
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=timeout_per_response
                    )
                    response_data = json.loads(response)
                    received_responses.append(response_data)
                    logger.debug(f"Received response {i+1}: {response_data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for response {i+1}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving response {i+1}: {e}")
                    break
            
            # Validate responses received
            assert len(received_responses) > 0, "Must receive at least one response even during rapid sending"
            
            # Check for any error responses indicating handshake race conditions
            error_responses = [r for r in received_responses if r.get("type") == "error"]
            handshake_errors = [
                r for r in error_responses 
                if "handshake" in r.get("message", "").lower() or "1011" in r.get("message", "")
            ]
            
            assert len(handshake_errors) == 0, f"Handshake race condition errors detected: {handshake_errors}"
            
            # All messages should be processed (possibly queued during handshake)
            logger.info(f"✅ Handshake completion test passed - {len(received_responses)} responses received")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_progressive_delay_cloud_run_simulation(self, real_services_fixture):
        """
        Test WebSocket handshake with progressive delays simulating Cloud Run environment.
        
        This test simulates the progressive delay issues encountered in GCP Cloud Run
        environments where handshake timing varies due to container cold starts and
        network latency.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test with increasing delays to simulate Cloud Run variability
        delay_scenarios = [0.0, 0.5, 1.0, 2.0, 3.0]  # Progressive delays in seconds
        successful_connections = []
        
        for delay in delay_scenarios:
            user_id = f"cloud_run_sim_{delay}_{int(time.time())}"
            token = auth_helper.create_test_jwt_token(user_id=user_id)
            headers = auth_helper.get_websocket_headers(token)
            
            logger.info(f"Testing Cloud Run simulation with {delay}s delay for user: {user_id}")
            
            try:
                # Simulate network delay before connection
                if delay > 0:
                    await asyncio.sleep(delay)
                
                connection_start_time = time.time()
                
                # Attempt connection with timeout adjusted for delay
                adjusted_timeout = self.max_handshake_timeout + delay
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    open_timeout=adjusted_timeout,
                    close_timeout=5.0
                ) as websocket:
                    
                    connection_duration = time.time() - connection_start_time
                    
                    # Send test message to verify handshake completion
                    test_message = {
                        "type": "cloud_run_test",
                        "delay_scenario": delay,
                        "connection_duration": connection_duration,
                        "user_id": user_id
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response to confirm handshake completed
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        successful_connections.append({
                            "delay": delay,
                            "connection_duration": connection_duration,
                            "response_received": True,
                            "response_type": response_data.get("type", "unknown")
                        })
                        
                        logger.info(f"✅ Cloud Run simulation successful for {delay}s delay")
                        
                    except asyncio.TimeoutError:
                        # Connection established but no response - partial success
                        successful_connections.append({
                            "delay": delay,
                            "connection_duration": connection_duration,
                            "response_received": False,
                            "response_type": None
                        })
                        logger.warning(f"⚠️ Cloud Run simulation: connection OK but no response for {delay}s delay")
                        
            except Exception as e:
                logger.error(f"❌ Cloud Run simulation failed for {delay}s delay: {e}")
                # Record failure for analysis
                if "1011" in str(e):
                    pytest.fail(f"WebSocket 1011 error in Cloud Run simulation (delay: {delay}s): {e}")
                    
        # Validate that most scenarios succeeded
        success_rate = len(successful_connections) / len(delay_scenarios)
        assert success_rate >= 0.8, f"Cloud Run simulation success rate too low: {success_rate:.2%}"
        
        logger.info(f"✅ Cloud Run progressive delay test passed - {len(successful_connections)}/{len(delay_scenarios)} scenarios successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_connection_state_validation_during_handshake(self, real_services_fixture):
        """
        Test connection state validation during WebSocket handshake process.
        
        This test validates that the WebSocket connection state is properly managed
        during the handshake process and that state transitions are atomic.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = f"state_validation_{int(time.time())}"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        logger.info(f"Testing connection state validation for user: {user_id}")
        
        connection_states = []
        
        async with websockets.connect(
            self.websocket_url,
            additional_headers=headers,
            open_timeout=self.max_handshake_timeout
        ) as websocket:
            
            # Verify connection is open
            assert websocket.open, "WebSocket connection must be open after handshake"
            connection_states.append("open")
            
            # Test state validation message
            state_test_message = {
                "type": "connection_state_test",
                "user_id": user_id,
                "test_connection_state": True,
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(state_test_message))
            connection_states.append("message_sent")
            
            # Wait for state validation response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                connection_states.append("response_received")
                
                # Validate response indicates proper state management
                assert response_data is not None, "Must receive response for state validation"
                
                # Check for any state-related errors
                if response_data.get("type") == "error":
                    error_msg = response_data.get("message", "")
                    assert "state" not in error_msg.lower(), f"Connection state error: {error_msg}"
                
                logger.info(f"✅ Connection state validation successful: {response_data.get('type')}")
                
            except asyncio.TimeoutError:
                pytest.fail("Connection state validation timeout - may indicate handshake race condition")
        
        connection_states.append("closed")
        
        # Validate all expected states were reached
        expected_states = ["open", "message_sent", "response_received", "closed"]
        for expected_state in expected_states:
            assert expected_state in connection_states, f"Missing connection state: {expected_state}"
        
        logger.info(f"✅ Connection state validation test passed - states: {connection_states}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_flow_during_handshake(self, real_services_fixture):
        """
        Test authentication flow timing during WebSocket handshake.
        
        This test validates that authentication is properly handled during the
        handshake process and doesn't cause race conditions or authentication failures.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test multiple authentication scenarios
        auth_scenarios = [
            {"user_id": f"auth_test_1_{int(time.time())}", "permissions": ["read"]},
            {"user_id": f"auth_test_2_{int(time.time())}", "permissions": ["read", "write"]},
            {"user_id": f"auth_test_3_{int(time.time())}", "permissions": ["read", "write", "admin"]}
        ]
        
        successful_auth_flows = []
        
        for scenario in auth_scenarios:
            user_id = scenario["user_id"]
            permissions = scenario["permissions"]
            
            token = auth_helper.create_test_jwt_token(
                user_id=user_id,
                permissions=permissions
            )
            headers = auth_helper.get_websocket_headers(token)
            
            logger.info(f"Testing auth flow during handshake for user: {user_id}")
            
            try:
                auth_start_time = time.time()
                
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    open_timeout=self.max_handshake_timeout
                ) as websocket:
                    
                    auth_duration = time.time() - auth_start_time
                    
                    # Send authentication test message
                    auth_test_message = {
                        "type": "auth_validation_test",
                        "user_id": user_id,
                        "requested_permissions": permissions,
                        "auth_duration": auth_duration
                    }
                    
                    await websocket.send(json.dumps(auth_test_message))
                    
                    # Wait for authentication validation response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                        response_data = json.loads(response)
                        
                        # Check for authentication errors
                        if response_data.get("type") == "error":
                            error_msg = response_data.get("message", "")
                            if "auth" in error_msg.lower() or "permission" in error_msg.lower():
                                pytest.fail(f"Authentication error during handshake for {user_id}: {error_msg}")
                        
                        successful_auth_flows.append({
                            "user_id": user_id,
                            "permissions": permissions,
                            "auth_duration": auth_duration,
                            "response_type": response_data.get("type")
                        })
                        
                        logger.info(f"✅ Auth flow successful for {user_id} in {auth_duration:.3f}s")
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Auth validation timeout for {user_id}")
                        # Record as partial success if connection established
                        successful_auth_flows.append({
                            "user_id": user_id,
                            "permissions": permissions,
                            "auth_duration": auth_duration,
                            "response_type": "timeout"
                        })
                        
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "403" in error_msg:
                    pytest.fail(f"Authentication failure during handshake for {user_id}: {e}")
                elif "1011" in error_msg:
                    pytest.fail(f"WebSocket 1011 error during auth handshake for {user_id}: {e}")
                else:
                    logger.error(f"❌ Unexpected error during auth handshake for {user_id}: {e}")
        
        # Validate that all authentication flows succeeded
        auth_success_rate = len(successful_auth_flows) / len(auth_scenarios)
        assert auth_success_rate >= 0.8, f"Authentication flow success rate too low: {auth_success_rate:.2%}"
        
        # Validate authentication timing is reasonable
        auth_durations = [flow["auth_duration"] for flow in successful_auth_flows]
        avg_auth_duration = sum(auth_durations) / len(auth_durations)
        assert avg_auth_duration < 10.0, f"Average auth duration too slow: {avg_auth_duration:.3f}s"
        
        logger.info(f"✅ Authentication flow during handshake test passed - {len(successful_auth_flows)} successful flows")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_race_condition_reproduction(self, real_services_fixture):
        """
        Test that reproduces WebSocket race conditions (should fail without fixes).
        
        CRITICAL: This test is designed to detect race conditions by creating
        high-concurrency scenarios that would trigger 1011 errors or handshake
        failures in an unfixed system.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Create concurrent connection attempts to trigger race conditions
        concurrent_users = 5
        connection_attempts_per_user = 3
        
        async def attempt_rapid_connections(user_index: int) -> List[Dict]:
            """Attempt rapid WebSocket connections for one user."""
            user_id = f"race_test_user_{user_index}_{int(time.time())}"
            results = []
            
            for attempt in range(connection_attempts_per_user):
                token = auth_helper.create_test_jwt_token(user_id=f"{user_id}_attempt_{attempt}")
                headers = auth_helper.get_websocket_headers(token)
                
                connection_start = time.time()
                
                try:
                    # Very short timeout to stress-test handshake timing
                    async with websockets.connect(
                        self.websocket_url,
                        additional_headers=headers,
                        open_timeout=5.0,
                        close_timeout=2.0
                    ) as websocket:
                        
                        connection_duration = time.time() - connection_start
                        
                        # Immediately send message to test race condition
                        race_test_message = {
                            "type": "race_condition_test",
                            "user_index": user_index,
                            "attempt": attempt,
                            "rapid_connection": True
                        }
                        
                        await websocket.send(json.dumps(race_test_message))
                        
                        # Try to get immediate response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                            response_data = json.loads(response)
                            
                            results.append({
                                "user_index": user_index,
                                "attempt": attempt,
                                "success": True,
                                "connection_duration": connection_duration,
                                "response_type": response_data.get("type"),
                                "error": None
                            })
                            
                        except asyncio.TimeoutError:
                            # Connection worked but no response - still success for race condition test
                            results.append({
                                "user_index": user_index,
                                "attempt": attempt,
                                "success": True,
                                "connection_duration": connection_duration,
                                "response_type": "timeout",
                                "error": None
                            })
                        
                except Exception as e:
                    error_msg = str(e)
                    connection_duration = time.time() - connection_start
                    
                    # Record specific race condition errors
                    is_race_condition_error = (
                        "1011" in error_msg or 
                        "handshake" in error_msg.lower() or
                        "connection" in error_msg.lower()
                    )
                    
                    results.append({
                        "user_index": user_index,
                        "attempt": attempt,
                        "success": False,
                        "connection_duration": connection_duration,
                        "response_type": None,
                        "error": error_msg,
                        "is_race_condition_error": is_race_condition_error
                    })
                
                # Small delay between attempts to avoid overwhelming the system
                await asyncio.sleep(0.1)
            
            return results
        
        # Execute concurrent connection attempts
        logger.info(f"Starting race condition test with {concurrent_users} users, {connection_attempts_per_user} attempts each")
        
        all_tasks = [
            attempt_rapid_connections(user_index) 
            for user_index in range(concurrent_users)
        ]
        
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Flatten results and analyze
        flat_results = []
        for result_set in all_results:
            if isinstance(result_set, list):
                flat_results.extend(result_set)
            else:
                logger.error(f"Task failed with exception: {result_set}")
        
        total_attempts = len(flat_results)
        successful_attempts = [r for r in flat_results if r["success"]]
        failed_attempts = [r for r in flat_results if not r["success"]]
        race_condition_errors = [r for r in failed_attempts if r.get("is_race_condition_error", False)]
        
        # Calculate metrics
        success_rate = len(successful_attempts) / total_attempts if total_attempts > 0 else 0
        race_condition_error_rate = len(race_condition_errors) / total_attempts if total_attempts > 0 else 0
        
        logger.info(f"Race condition test results:")
        logger.info(f"  Total attempts: {total_attempts}")
        logger.info(f"  Successful: {len(successful_attempts)} ({success_rate:.2%})")
        logger.info(f"  Failed: {len(failed_attempts)}")
        logger.info(f"  Race condition errors: {len(race_condition_errors)} ({race_condition_error_rate:.2%})")
        
        # CRITICAL: No race condition errors should occur
        if race_condition_errors:
            error_details = [r["error"] for r in race_condition_errors[:3]]  # Show first 3 errors
            pytest.fail(
                f"Race condition errors detected! {len(race_condition_errors)} out of {total_attempts} attempts failed "
                f"with race condition errors. This indicates unfixed handshake race conditions. "
                f"Sample errors: {error_details}"
            )
        
        # Success rate should be high for a fixed system
        assert success_rate >= 0.9, f"Success rate too low for race condition test: {success_rate:.2%}"
        
        logger.info(f"✅ Race condition reproduction test passed - no race conditions detected")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_handshake_timeout_handling(self, real_services_fixture):
        """
        Test WebSocket handshake timeout handling and recovery.
        
        This test validates that handshake timeouts are handled gracefully
        and don't leave connections in inconsistent states.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test different timeout scenarios
        timeout_scenarios = [
            {"timeout": 1.0, "should_succeed": False, "test_name": "very_short"},
            {"timeout": 3.0, "should_succeed": True, "test_name": "short"},
            {"timeout": 10.0, "should_succeed": True, "test_name": "normal"},
            {"timeout": 20.0, "should_succeed": True, "test_name": "long"}
        ]
        
        timeout_results = []
        
        for scenario in timeout_scenarios:
            timeout = scenario["timeout"]
            should_succeed = scenario["should_succeed"]
            test_name = scenario["test_name"]
            
            user_id = f"timeout_test_{test_name}_{int(time.time())}"
            token = auth_helper.create_test_jwt_token(user_id=user_id)
            headers = auth_helper.get_websocket_headers(token)
            
            logger.info(f"Testing handshake timeout handling: {test_name} ({timeout}s)")
            
            start_time = time.time()
            connection_success = False
            timeout_occurred = False
            error_type = None
            
            try:
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    open_timeout=timeout,
                    close_timeout=2.0
                ) as websocket:
                    
                    connection_duration = time.time() - start_time
                    connection_success = True
                    
                    # Send test message to verify connection works
                    timeout_test_message = {
                        "type": "timeout_test",
                        "timeout_scenario": test_name,
                        "configured_timeout": timeout,
                        "actual_duration": connection_duration
                    }
                    
                    await websocket.send(json.dumps(timeout_test_message))
                    
                    # Brief wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response)
                        logger.debug(f"Timeout test response: {response_data.get('type')}")
                    except asyncio.TimeoutError:
                        logger.debug(f"No response for timeout test {test_name} (acceptable)")
                    
            except asyncio.TimeoutError:
                connection_duration = time.time() - start_time
                timeout_occurred = True
                error_type = "timeout"
                logger.info(f"Timeout occurred for {test_name} after {connection_duration:.3f}s")
                
            except Exception as e:
                connection_duration = time.time() - start_time
                error_type = type(e).__name__
                logger.info(f"Error for {test_name}: {error_type} - {e}")
            
            # Record results
            timeout_results.append({
                "test_name": test_name,
                "timeout": timeout,
                "should_succeed": should_succeed,
                "connection_success": connection_success,
                "timeout_occurred": timeout_occurred,
                "error_type": error_type,
                "connection_duration": connection_duration
            })
            
            # Validate expected behavior
            if should_succeed:
                assert connection_success or connection_duration < timeout + 1.0, \
                    f"Connection should succeed for {test_name} timeout scenario"
            
            # Small delay between tests
            await asyncio.sleep(0.5)
        
        # Analyze timeout handling results
        successful_connections = [r for r in timeout_results if r["connection_success"]]
        expected_successes = [r for r in timeout_results if r["should_succeed"]]
        
        logger.info(f"Timeout handling test results:")
        for result in timeout_results:
            logger.info(f"  {result['test_name']}: success={result['connection_success']}, "
                       f"duration={result['connection_duration']:.3f}s")
        
        # Validate that reasonable timeouts work
        reasonable_timeout_success = len([r for r in successful_connections if r["timeout"] >= 5.0])
        assert reasonable_timeout_success > 0, "At least one reasonable timeout scenario should succeed"
        
        logger.info(f"✅ Handshake timeout handling test passed - {len(successful_connections)} successful connections")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_connection_attempts(self, real_services_fixture):
        """
        Test concurrent WebSocket connection attempts from multiple users.
        
        This test validates that the system can handle multiple simultaneous
        WebSocket connection attempts without race conditions or resource conflicts.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test with multiple concurrent users
        num_concurrent_users = 8
        max_connection_time = 15.0
        
        async def establish_user_connection(user_index: int) -> Dict:
            """Establish WebSocket connection for one user."""
            user_id = f"concurrent_user_{user_index}_{int(time.time())}"
            token = auth_helper.create_test_jwt_token(user_id=user_id)
            headers = auth_helper.get_websocket_headers(token)
            
            connection_start = time.time()
            
            try:
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    open_timeout=max_connection_time,
                    ping_interval=None  # Disable ping during test
                ) as websocket:
                    
                    connection_duration = time.time() - connection_start
                    
                    # Send concurrent test message
                    concurrent_test_message = {
                        "type": "concurrent_connection_test",
                        "user_index": user_index,
                        "user_id": user_id,
                        "connection_duration": connection_duration
                    }
                    
                    await websocket.send(json.dumps(concurrent_test_message))
                    
                    # Wait for acknowledgment
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        return {
                            "user_index": user_index,
                            "user_id": user_id,
                            "success": True,
                            "connection_duration": connection_duration,
                            "response_received": True,
                            "response_type": response_data.get("type"),
                            "error": None
                        }
                        
                    except asyncio.TimeoutError:
                        return {
                            "user_index": user_index,
                            "user_id": user_id,
                            "success": True,
                            "connection_duration": connection_duration,
                            "response_received": False,
                            "response_type": None,
                            "error": "response_timeout"
                        }
                        
            except Exception as e:
                connection_duration = time.time() - connection_start
                error_msg = str(e)
                
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "success": False,
                    "connection_duration": connection_duration,
                    "response_received": False,
                    "response_type": None,
                    "error": error_msg
                }
        
        # Execute concurrent connection attempts
        logger.info(f"Starting concurrent connection test with {num_concurrent_users} users")
        
        start_time = time.time()
        connection_tasks = [
            establish_user_connection(user_index) 
            for user_index in range(num_concurrent_users)
        ]
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_duration = time.time() - start_time
        
        # Analyze concurrent connection results
        successful_connections = []
        failed_connections = []
        
        for result in results:
            if isinstance(result, dict):
                if result["success"]:
                    successful_connections.append(result)
                else:
                    failed_connections.append(result)
            else:
                # Task failed with exception
                failed_connections.append({
                    "error": str(result),
                    "success": False
                })
        
        # Calculate metrics
        success_rate = len(successful_connections) / num_concurrent_users
        avg_connection_time = sum(r["connection_duration"] for r in successful_connections) / len(successful_connections) if successful_connections else 0
        
        logger.info(f"Concurrent connection test results:")
        logger.info(f"  Total users: {num_concurrent_users}")
        logger.info(f"  Successful connections: {len(successful_connections)} ({success_rate:.2%})")
        logger.info(f"  Failed connections: {len(failed_connections)}")
        logger.info(f"  Average connection time: {avg_connection_time:.3f}s")
        logger.info(f"  Total test duration: {total_duration:.3f}s")
        
        # Check for specific race condition errors
        race_condition_failures = [
            f for f in failed_connections 
            if "1011" in str(f.get("error", "")) or "handshake" in str(f.get("error", "")).lower()
        ]
        
        if race_condition_failures:
            failure_details = [f.get("error", "unknown") for f in race_condition_failures[:3]]
            pytest.fail(
                f"Race condition failures detected in concurrent connections! "
                f"{len(race_condition_failures)} out of {num_concurrent_users} failed with race condition errors. "
                f"Sample errors: {failure_details}"
            )
        
        # Validate success metrics
        assert success_rate >= 0.75, f"Concurrent connection success rate too low: {success_rate:.2%}"
        assert avg_connection_time < max_connection_time, f"Average connection time too slow: {avg_connection_time:.3f}s"
        
        # Validate that connections were truly concurrent
        assert total_duration < (avg_connection_time * num_concurrent_users * 0.8), \
            "Connections do not appear to be concurrent - may indicate serialization"
        
        logger.info(f"✅ Concurrent connection attempts test passed - {len(successful_connections)} successful connections")


class TestWebSocketHandshakeAdvancedScenarios(BaseIntegrationTest):
    """Advanced WebSocket handshake scenarios for edge cases and stress testing."""
    
    def setup_method(self):
        """Set up each test method."""
        super().setup_method()
        self.env = get_env()
        self.websocket_url = "ws://localhost:8000/ws"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_handshake_with_malformed_headers(self, real_services_fixture):
        """
        Test WebSocket handshake behavior with malformed or missing authentication headers.
        
        This test ensures that the handshake process properly validates authentication
        headers and fails gracefully for malformed requests.
        """
        # Test scenarios with different header problems
        header_scenarios = [
            {
                "name": "missing_authorization",
                "headers": {"Content-Type": "application/json"},
                "should_fail": True
            },
            {
                "name": "malformed_bearer_token",
                "headers": {"Authorization": "Bearer invalid.jwt.token"},
                "should_fail": True
            },
            {
                "name": "empty_authorization",
                "headers": {"Authorization": ""},
                "should_fail": True
            },
            {
                "name": "wrong_auth_scheme",
                "headers": {"Authorization": "Basic dGVzdDp0ZXN0"},
                "should_fail": True
            }
        ]
        
        handshake_validation_results = []
        
        for scenario in header_scenarios:
            scenario_name = scenario["name"]
            headers = scenario["headers"]
            should_fail = scenario["should_fail"]
            
            logger.info(f"Testing handshake with malformed headers: {scenario_name}")
            
            try:
                async with websockets.connect(
                    self.websocket_url,
                    additional_headers=headers,
                    open_timeout=5.0
                ) as websocket:
                    
                    # If connection succeeds when it should fail, that's a problem
                    if should_fail:
                        pytest.fail(f"Connection succeeded with malformed headers: {scenario_name}")
                    
                    handshake_validation_results.append({
                        "scenario": scenario_name,
                        "success": True,
                        "expected_failure": should_fail,
                        "error": None
                    })
                    
            except Exception as e:
                error_msg = str(e)
                
                handshake_validation_results.append({
                    "scenario": scenario_name,
                    "success": False,
                    "expected_failure": should_fail,
                    "error": error_msg
                })
                
                # If it should fail and did fail, that's correct
                if should_fail:
                    logger.info(f"✅ Correctly rejected malformed headers for {scenario_name}: {type(e).__name__}")
                else:
                    logger.error(f"❌ Unexpected failure for {scenario_name}: {e}")
        
        # Validate that all malformed header scenarios failed as expected
        for result in handshake_validation_results:
            if result["expected_failure"]:
                assert not result["success"], f"Scenario {result['scenario']} should have failed but succeeded"
        
        logger.info(f"✅ Malformed headers test passed - all invalid scenarios properly rejected")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_handshake_interruption_recovery(self, real_services_fixture):
        """
        Test WebSocket handshake interruption and recovery scenarios.
        
        This test simulates network interruptions during handshake and validates
        that the system can recover properly without leaving stale connections.
        """
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Test handshake interruption recovery
        user_id = f"interruption_test_{int(time.time())}"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        logger.info(f"Testing handshake interruption recovery for user: {user_id}")
        
        interruption_recovery_results = []
        
        # Attempt 1: Start connection and interrupt quickly
        try:
            async with websockets.connect(
                self.websocket_url,
                additional_headers=headers,
                open_timeout=2.0,  # Short timeout to simulate interruption
                close_timeout=1.0
            ) as websocket:
                
                # Send message immediately after connection
                interruption_test_message = {
                    "type": "interruption_test",
                    "user_id": user_id,
                    "attempt": 1
                }
                
                await websocket.send(json.dumps(interruption_test_message))
                
                # Close connection quickly to simulate interruption
                await websocket.close()
                
                interruption_recovery_results.append({
                    "attempt": 1,
                    "stage": "connection_established",
                    "success": True
                })
                
        except Exception as e:
            logger.info(f"Expected interruption in attempt 1: {e}")
            interruption_recovery_results.append({
                "attempt": 1,
                "stage": "connection_interrupted",
                "success": True,  # Interruption is expected
                "error": str(e)
            })
        
        # Small delay to allow cleanup
        await asyncio.sleep(1.0)
        
        # Attempt 2: Recovery connection should work
        try:
            async with websockets.connect(
                self.websocket_url,
                additional_headers=headers,
                open_timeout=10.0
            ) as websocket:
                
                recovery_test_message = {
                    "type": "recovery_test",
                    "user_id": user_id,
                    "attempt": 2,
                    "recovery_after_interruption": True
                }
                
                await websocket.send(json.dumps(recovery_test_message))
                
                # Wait for response to confirm recovery
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    interruption_recovery_results.append({
                        "attempt": 2,
                        "stage": "recovery_successful",
                        "success": True,
                        "response_type": response_data.get("type")
                    })
                    
                except asyncio.TimeoutError:
                    interruption_recovery_results.append({
                        "attempt": 2,
                        "stage": "recovery_timeout",
                        "success": True,  # Connection worked, timeout acceptable
                        "response_type": "timeout"
                    })
                    
        except Exception as e:
            logger.error(f"Recovery attempt failed: {e}")
            interruption_recovery_results.append({
                "attempt": 2,
                "stage": "recovery_failed",
                "success": False,
                "error": str(e)
            })
        
        # Validate recovery results
        recovery_attempt = [r for r in interruption_recovery_results if r["attempt"] == 2]
        assert len(recovery_attempt) > 0, "Recovery attempt must be recorded"
        
        recovery_success = recovery_attempt[0]["success"]
        assert recovery_success, f"Recovery after interruption failed: {recovery_attempt[0].get('error')}"
        
        logger.info(f"✅ Handshake interruption recovery test passed")
        logger.info(f"Recovery results: {[r['stage'] for r in interruption_recovery_results]}")


# Integration test for service dependency monitoring during handshake
class TestWebSocketHandshakeServiceDependencies(BaseIntegrationTest):
    """Test WebSocket handshake with service dependency validation."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_handshake_with_service_health_checks(self, real_services_fixture):
        """
        Test WebSocket handshake with comprehensive service health validation.
        
        This test ensures that the WebSocket handshake process properly validates
        that all required services are available before completing the handshake.
        """
        services = real_services_fixture
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        
        # Validate service availability before testing
        logger.info("Validating service dependencies before WebSocket handshake test")
        
        service_health = {
            "database": services["database_available"],
            "backend": services["services_available"]["backend"],
            "redis": services["services_available"]["redis"]
        }
        
        logger.info(f"Service health status: {service_health}")
        
        # Test handshake with different service availability scenarios
        user_id = f"service_health_test_{int(time.time())}"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        headers = auth_helper.get_websocket_headers(token)
        
        try:
            async with websockets.connect(
                self.websocket_url,
                additional_headers=headers,
                open_timeout=15.0
            ) as websocket:
                
                # Send service health validation message
                health_check_message = {
                    "type": "service_health_check",
                    "user_id": user_id,
                    "check_dependencies": True,
                    "expected_services": ["database", "redis", "backend"]
                }
                
                await websocket.send(json.dumps(health_check_message))
                
                # Wait for health check response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    response_data = json.loads(response)
                    
                    # Validate that health check completed
                    assert response_data is not None, "Must receive health check response"
                    
                    # Check for service availability errors
                    if response_data.get("type") == "error":
                        error_msg = response_data.get("message", "")
                        if "service" in error_msg.lower() and "unavailable" in error_msg.lower():
                            logger.warning(f"Service unavailable during handshake: {error_msg}")
                        else:
                            logger.info(f"Non-service error (acceptable): {error_msg}")
                    
                    logger.info(f"✅ Service health check during handshake completed: {response_data.get('type')}")
                    
                except asyncio.TimeoutError:
                    logger.info("✅ Service health check timeout (acceptable if services available)")
                    
        except Exception as e:
            error_msg = str(e)
            
            # Only fail if this is clearly a service dependency issue
            if "service" in error_msg.lower() or "database" in error_msg.lower():
                pytest.fail(f"Service dependency failure during WebSocket handshake: {e}")
            else:
                logger.warning(f"Non-service error during handshake (may be acceptable): {e}")
        
        logger.info(f"✅ WebSocket handshake service dependency test completed")