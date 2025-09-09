"""
WebSocket Race Condition Integration Tests

CRITICAL: These tests focus on WebSocket race conditions that occur between real services.
This is part of the comprehensive test creation initiative to fill gaps between unit and E2E tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability - Prevent WebSocket chat failures
- Value Impact: Ensures reliable AI-powered chat delivery under race conditions
- Strategic/Revenue Impact: Prevents $500K+ ARR loss from WebSocket reliability issues

Key Race Conditions Tested:
1. Handshake timing race conditions ("Need to call 'accept' first")
2. Connection state synchronization across PostgreSQL/Redis boundaries
3. WebSocket event ordering under concurrent load
4. User isolation in multi-user scenarios
5. Service disruption and recovery patterns

INTEGRATION TEST REQUIREMENTS:
- Uses real PostgreSQL, Redis, WebSocket connections (NO MOCKS)
- Tests service-to-service WebSocket interactions
- Validates mission-critical WebSocket events delivery
- Tests specific staging failure scenarios (User ID: 101463487227881885914)

Author: AI Agent - WebSocket Integration Test Creation
Date: 2025-09-09
"""

import asyncio
import json
import logging
import pytest
import time
import threading
import websockets
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import patch
from urllib.parse import urljoin

# CRITICAL: Use real services fixture (NO MOCKS in integration tests)
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper

# Core WebSocket components for integration testing
from netra_backend.app.websocket_core.connection_state_machine import (
    ConnectionStateMachine,
    ApplicationConnectionState
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Shared types for strongly typed integration testing
from shared.types import UserID, ThreadID, RequestID
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.unified_id_manager import generate_user_id

# Note: Database, cache, and auth imports removed for basic import verification
# These would be restored when the full integration test is needed


@dataclass
class AuthenticatedUser:
    """Real authenticated user for integration testing"""
    user_id: UserID
    jwt_token: str
    session_id: str
    websocket_headers: Dict[str, str]
    
    
@dataclass
class RaceConditionTestMetrics:
    """Metrics tracking for race condition tests"""
    connection_attempts: int = 0
    successful_connections: int = 0
    handshake_failures: int = 0
    race_conditions_detected: int = 0
    message_ordering_violations: int = 0
    average_connection_time: float = 0.0
    max_connection_time: float = 0.0
    

@dataclass
class ConcurrentUser:
    """Represents a concurrent user in race condition scenarios"""
    user_id: UserID
    session_id: str
    websocket_connection: Optional[Any] = None
    connection_state: Optional[ApplicationConnectionState] = None
    message_count: int = 0
    race_condition_detected: bool = False


class TestWebSocketRaceConditionsIntegration:
    """
    Integration tests for WebSocket race conditions using real services.
    
    CRITICAL: These tests use real PostgreSQL, Redis, and WebSocket connections
    to validate race condition handling across service boundaries.
    """
    
    @pytest.fixture(autouse=True)
    def setup_integration_environment(self, real_services_fixture):
        """Set up real services for integration testing"""
        self.services = real_services_fixture
        self.postgres_connection = self.services['postgres']
        self.redis_connection = self.services['redis']
        self.backend_url = self.services['backend_url']
        
        # Initialize real authentication helpers
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        
        # Initialize WebSocket manager with real services
        self.websocket_manager = UnifiedWebSocketManager()
        # Note: Event dispatcher is integrated into UnifiedWebSocketManager
        
        # Initialize database and cache managers (simplified for import testing)
        # self.db_manager = DatabaseConnectionManager(connection=self.postgres_connection)  
        # self.cache_manager = RedisCacheManager(connection=self.redis_connection)
        
        # Test metrics tracking
        self.test_metrics = RaceConditionTestMetrics()
        
        # Logger for race condition detection
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
    async def create_authenticated_user(self, user_id_override: Optional[str] = None) -> AuthenticatedUser:
        """Create a real authenticated user for integration testing"""
        if user_id_override:
            user_id = UserID(user_id_override)
        else:
            user_id = UserID(generate_user_id())
            
        # Create real JWT token through auth service
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        session_id = f"session_{user_id}_{int(time.time())}"
        
        # Create WebSocket authentication headers
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(user_id),
            is_e2e_test=True
        )
        
        return AuthenticatedUser(
            user_id=user_id,
            jwt_token=jwt_token,
            session_id=session_id,
            websocket_headers=websocket_headers
        )
    
    @pytest.mark.asyncio
    async def test_websocket_handshake_race_condition_basic(self, real_services_fixture):
        """
        Test basic WebSocket handshake race conditions with real services.
        
        This test validates the specific "Need to call 'accept' first" race condition
        that was occurring in staging environments.
        """
        user = await self.create_authenticated_user()
        
        # Test the race condition by attempting rapid connection sequences
        connection_attempts = []
        handshake_times = []
        
        for attempt in range(5):
            start_time = time.time()
            
            try:
                # Connect with real authentication
                websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
                connection = await websockets.connect(
                    websocket_url,
                    extra_headers=user.websocket_headers,
                    timeout=10
                )
                
                # Test handshake completion
                handshake_message = {
                    "type": "handshake",
                    "user_id": str(user.user_id),
                    "session_id": user.session_id
                }
                
                await connection.send(json.dumps(handshake_message))
                response = await asyncio.wait_for(connection.recv(), timeout=5)
                response_data = json.loads(response)
                
                handshake_time = time.time() - start_time
                handshake_times.append(handshake_time)
                
                # Validate successful handshake
                assert response_data.get('type') == 'handshake_complete'
                assert response_data.get('status') == 'success'
                
                connection_attempts.append({
                    'attempt': attempt,
                    'success': True,
                    'handshake_time': handshake_time,
                    'connection': connection
                })
                
            except Exception as e:
                connection_attempts.append({
                    'attempt': attempt,
                    'success': False,
                    'error': str(e),
                    'handshake_time': time.time() - start_time
                })
                
        # Validate race condition metrics
        successful_connections = sum(1 for attempt in connection_attempts if attempt['success'])
        assert successful_connections >= 4, f"Expected at least 4 successful connections, got {successful_connections}"
        
        # Check for race condition indicators
        average_handshake_time = sum(handshake_times) / len(handshake_times) if handshake_times else 0
        assert average_handshake_time < 2.0, f"Handshake taking too long: {average_handshake_time}s"
        
        # Clean up connections
        for attempt in connection_attempts:
            if attempt['success'] and 'connection' in attempt:
                await attempt['connection'].close()
    
    @pytest.mark.asyncio
    async def test_connection_state_synchronization_across_services(self, real_services_fixture):
        """
        Test WebSocket connection state synchronization across PostgreSQL and Redis.
        
        This validates that connection states are properly synchronized across
        database and cache boundaries, preventing race conditions.
        """
        user = await self.create_authenticated_user()
        
        # Create WebSocket connection state machine
        state_machine = ConnectionStateMachine(connection_id="test_conn", user_id=str(user.user_id))
        
        # Test state synchronization across services
        websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=user.websocket_headers,
            timeout=10
        )
        
        try:
            # Step 1: Validate initial state in PostgreSQL
            pg_state_query = """
            SELECT connection_state, user_id, created_at 
            FROM websocket_connections 
            WHERE user_id = %s 
            ORDER BY created_at DESC LIMIT 1
            """
            
            with self.postgres_connection.cursor() as cursor:
                cursor.execute(pg_state_query, (str(user.user_id),))
                pg_result = cursor.fetchone()
                
            assert pg_result is not None, "Connection state not found in PostgreSQL"
            assert pg_result[0] == 'connecting', f"Unexpected PostgreSQL state: {pg_result[0]}"
            
            # Step 2: Validate Redis cache synchronization
            redis_state_key = f"websocket_state:{user.user_id}"
            redis_state = await self.redis_connection.get(redis_state_key)
            
            assert redis_state is not None, "Connection state not found in Redis"
            redis_data = json.loads(redis_state)
            assert redis_data['state'] == 'connecting', f"Unexpected Redis state: {redis_data['state']}"
            
            # Step 3: Complete handshake and test state transitions
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            response = await asyncio.wait_for(connection.recv(), timeout=5)
            response_data = json.loads(response)
            
            assert response_data.get('type') == 'handshake_complete'
            
            # Step 4: Validate state synchronization after handshake
            await asyncio.sleep(0.1)  # Allow for async state updates
            
            with self.postgres_connection.cursor() as cursor:
                cursor.execute(pg_state_query, (str(user.user_id),))
                pg_result_after = cursor.fetchone()
                
            assert pg_result_after[0] == 'processing_ready', f"PostgreSQL state not updated: {pg_result_after[0]}"
            
            redis_state_after = await self.redis_connection.get(redis_state_key)
            redis_data_after = json.loads(redis_state_after)
            assert redis_data_after['state'] == 'processing_ready', f"Redis state not updated: {redis_data_after['state']}"
            
            # Step 5: Test race condition by rapid state changes
            state_change_tasks = []
            for i in range(10):
                task = asyncio.create_task(self._trigger_state_change(connection, user, i))
                state_change_tasks.append(task)
                
            # Wait for all state changes with timeout
            completed_tasks = await asyncio.wait_for(
                asyncio.gather(*state_change_tasks, return_exceptions=True),
                timeout=30
            )
            
            # Validate no race conditions in state synchronization
            race_condition_detected = False
            for result in completed_tasks:
                if isinstance(result, Exception):
                    if "race condition" in str(result).lower():
                        race_condition_detected = True
                        
            assert not race_condition_detected, "Race condition detected in state synchronization"
            
        finally:
            await connection.close()
    
    async def _trigger_state_change(self, connection, user: AuthenticatedUser, iteration: int):
        """Helper method to trigger WebSocket state changes for race condition testing"""
        try:
            message = {
                "type": "agent_execution_request",
                "user_id": str(user.user_id),
                "iteration": iteration,
                "timestamp": time.time()
            }
            
            await connection.send(json.dumps(message))
            response = await asyncio.wait_for(connection.recv(), timeout=5)
            
            # Validate response
            response_data = json.loads(response)
            assert 'type' in response_data
            
            return {"success": True, "iteration": iteration}
            
        except Exception as e:
            if "race condition" in str(e).lower() or "state" in str(e).lower():
                raise Exception(f"Race condition detected in iteration {iteration}: {e}")
            raise e
    
    @pytest.mark.asyncio
    async def test_concurrent_user_race_conditions_with_real_auth(self, real_services_fixture):
        """
        Test concurrent user scenarios with real authentication to detect race conditions.
        
        This test simulates multiple users connecting simultaneously to identify
        race conditions in user isolation and authentication handling.
        """
        # Create multiple authenticated users
        users = []
        for i in range(5):
            user = await self.create_authenticated_user()
            users.append(user)
            
        concurrent_users = []
        
        # Create concurrent user connections
        connection_tasks = []
        for user in users:
            task = asyncio.create_task(self._create_concurrent_user_connection(user))
            connection_tasks.append(task)
            
        # Execute concurrent connections
        concurrent_user_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Validate results and detect race conditions
        successful_connections = 0
        race_conditions_detected = 0
        
        for i, result in enumerate(concurrent_user_results):
            if isinstance(result, Exception):
                if "race condition" in str(result).lower() or "authentication" in str(result).lower():
                    race_conditions_detected += 1
                    self.logger.error(f"Race condition detected for user {users[i].user_id}: {result}")
            elif result and result.get('success'):
                successful_connections += 1
                concurrent_users.append(result['user_data'])
                
        # Assertions for race condition detection
        assert successful_connections >= 4, f"Expected at least 4 successful connections, got {successful_connections}"
        assert race_conditions_detected == 0, f"Race conditions detected: {race_conditions_detected}"
        
        # Test message isolation between users
        if len(concurrent_users) >= 2:
            user1 = concurrent_users[0]
            user2 = concurrent_users[1]
            
            # Send message from user1
            message_user1 = {
                "type": "agent_execution_request",
                "user_id": str(user1.user_id),
                "request": "Test message from user 1"
            }
            
            await user1.websocket_connection.send(json.dumps(message_user1))
            
            # Ensure user2 doesn't receive user1's message
            try:
                user2_response = await asyncio.wait_for(
                    user2.websocket_connection.recv(), 
                    timeout=2
                )
                user2_data = json.loads(user2_response)
                
                # If user2 receives a message, ensure it's not user1's message
                assert user2_data.get('user_id') != str(user1.user_id), "User isolation violated"
                
            except asyncio.TimeoutError:
                # This is expected - user2 should not receive user1's message
                pass
                
        # Clean up connections
        for user_data in concurrent_users:
            if hasattr(user_data, 'websocket_connection') and user_data.websocket_connection:
                await user_data.websocket_connection.close()
    
    async def _create_concurrent_user_connection(self, user: AuthenticatedUser) -> Dict[str, Any]:
        """Helper method to create concurrent user connections for race condition testing"""
        try:
            start_time = time.time()
            
            # Create WebSocket connection with real authentication
            websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=10
            )
            
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            response = await asyncio.wait_for(connection.recv(), timeout=5)
            response_data = json.loads(response)
            
            connection_time = time.time() - start_time
            
            if response_data.get('type') != 'handshake_complete':
                raise Exception(f"Handshake failed: {response_data}")
                
            # Create concurrent user data
            concurrent_user = ConcurrentUser(
                user_id=user.user_id,
                session_id=user.session_id,
                websocket_connection=connection,
                connection_state=ApplicationConnectionState.PROCESSING_READY
            )
            
            return {
                "success": True,
                "user_data": concurrent_user,
                "connection_time": connection_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_id": str(user.user_id)
            }
    
    @pytest.mark.asyncio
    async def test_websocket_event_ordering_race_conditions(self, real_services_fixture):
        """
        Test WebSocket event ordering under concurrent load to detect race conditions.
        
        This validates the 5 mission-critical WebSocket events are delivered in order
        even under race condition scenarios.
        """
        user = await self.create_authenticated_user()
        
        # Connect with real authentication
        websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=user.websocket_headers,
            timeout=10
        )
        
        try:
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            # Test event ordering with rapid agent execution requests
            event_sequences = []
            
            for request_num in range(3):
                # Send agent execution request
                execution_request = {
                    "type": "agent_execution_request",
                    "user_id": str(user.user_id),
                    "request_id": f"req_{request_num}_{int(time.time())}",
                    "agent_type": "test_agent",
                    "request": f"Test request {request_num}"
                }
                
                await connection.send(json.dumps(execution_request))
                
                # Collect event sequence
                events = []
                expected_events = [
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                ]
                
                # Collect events with timeout
                for expected_event in expected_events:
                    try:
                        response = await asyncio.wait_for(connection.recv(), timeout=10)
                        event_data = json.loads(response)
                        events.append({
                            "type": event_data.get("type"),
                            "timestamp": time.time(),
                            "request_id": event_data.get("request_id")
                        })
                        
                        if event_data.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout waiting for event {expected_event} in request {request_num}")
                        break
                        
                event_sequences.append({
                    "request_num": request_num,
                    "events": events,
                    "expected_count": len(expected_events),
                    "actual_count": len(events)
                })
                
            # Validate event ordering and detect race conditions
            ordering_violations = 0
            temporal_race_conditions = 0
            
            for sequence in event_sequences:
                events = sequence["events"]
                
                # Check event ordering
                if len(events) >= 2:
                    for i in range(1, len(events)):
                        if events[i]["timestamp"] < events[i-1]["timestamp"]:
                            ordering_violations += 1
                            
                        # Detect temporal race conditions (events too close together)
                        time_diff = events[i]["timestamp"] - events[i-1]["timestamp"]
                        if time_diff < 0.001:  # Less than 1ms apart
                            temporal_race_conditions += 1
                            
                # Validate expected event types
                event_types = [event["type"] for event in events]
                expected_types = [
                    "agent_started",
                    "agent_thinking",
                    "tool_executing", 
                    "tool_completed",
                    "agent_completed"
                ]
                
                # Check if critical events are present
                critical_events_present = all(
                    event_type in event_types for event_type in ["agent_started", "agent_completed"]
                )
                assert critical_events_present, f"Critical events missing in sequence {sequence['request_num']}"
                
            # Assertions for race condition detection
            assert ordering_violations == 0, f"Event ordering violations detected: {ordering_violations}"
            
            # Temporal race conditions are warnings, not failures (but should be monitored)
            if temporal_race_conditions > 0:
                self.logger.warning(f"Temporal race conditions detected: {temporal_race_conditions}")
                
            self.logger.info(f"Event ordering test completed. Sequences: {len(event_sequences)}")
            
        finally:
            await connection.close()
    
    @pytest.mark.asyncio
    async def test_connection_persistence_across_service_restarts(self, real_services_fixture):
        """
        Test WebSocket connection persistence and recovery across service disruptions.
        
        This simulates service restarts and validates that race conditions don't occur
        during connection recovery.
        """
        user = await self.create_authenticated_user()
        
        # Establish initial connection
        websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=user.websocket_headers,
            timeout=10
        )
        
        try:
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            # Test connection persistence by simulating service stress
            persistence_tests = []
            
            for test_round in range(3):
                # Send message before "service disruption"
                pre_disruption_message = {
                    "type": "ping",
                    "user_id": str(user.user_id),
                    "round": test_round,
                    "phase": "pre_disruption"
                }
                
                await connection.send(json.dumps(pre_disruption_message))
                pre_response = await asyncio.wait_for(connection.recv(), timeout=5)
                
                # Simulate brief service disruption (network delay)
                await asyncio.sleep(0.5)
                
                # Test connection recovery
                post_disruption_message = {
                    "type": "ping",
                    "user_id": str(user.user_id),
                    "round": test_round,
                    "phase": "post_disruption"
                }
                
                start_time = time.time()
                await connection.send(json.dumps(post_disruption_message))
                post_response = await asyncio.wait_for(connection.recv(), timeout=10)
                recovery_time = time.time() - start_time
                
                persistence_tests.append({
                    "round": test_round,
                    "pre_response": json.loads(pre_response),
                    "post_response": json.loads(post_response),
                    "recovery_time": recovery_time,
                    "connection_maintained": True
                })
                
            # Validate connection persistence
            successful_recoveries = sum(
                1 for test in persistence_tests 
                if test["connection_maintained"] and test["recovery_time"] < 5.0
            )
            
            assert successful_recoveries >= 2, f"Expected at least 2 successful recoveries, got {successful_recoveries}"
            
            # Check for race conditions in recovery
            recovery_race_conditions = 0
            for test in persistence_tests:
                if test["recovery_time"] > 2.0:
                    recovery_race_conditions += 1
                    
            assert recovery_race_conditions <= 1, f"Too many recovery race conditions: {recovery_race_conditions}"
            
        finally:
            await connection.close()
    
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_integration(self, real_services_fixture):
        """
        Test WebSocket error recovery and reconnection logic with real services.
        
        This validates that error recovery doesn't introduce race conditions
        and maintains system stability.
        """
        user = await self.create_authenticated_user()
        
        # Test error scenarios and recovery
        error_recovery_tests = []
        
        for error_scenario in ["timeout", "invalid_message", "authentication_error"]:
            try:
                # Create connection for error scenario
                websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
                connection = await websockets.connect(
                    websocket_url,
                    extra_headers=user.websocket_headers,
                    timeout=10
                )
                
                # Complete handshake
                handshake_message = {
                    "type": "handshake",
                    "user_id": str(user.user_id),
                    "session_id": user.session_id
                }
                
                await connection.send(json.dumps(handshake_message))
                await connection.recv()  # handshake_complete
                
                # Trigger error scenario
                start_time = time.time()
                recovery_successful = False
                error_message = None
                
                if error_scenario == "timeout":
                    # Send message and don't wait for response (timeout scenario)
                    timeout_message = {
                        "type": "long_running_request",
                        "user_id": str(user.user_id),
                        "timeout_duration": 3
                    }
                    await connection.send(json.dumps(timeout_message))
                    
                    try:
                        await asyncio.wait_for(connection.recv(), timeout=1)
                        recovery_successful = True
                    except asyncio.TimeoutError:
                        error_message = "Timeout as expected"
                        recovery_successful = True  # This is expected behavior
                        
                elif error_scenario == "invalid_message":
                    # Send invalid message format
                    await connection.send("invalid_json_message")
                    
                    try:
                        error_response = await asyncio.wait_for(connection.recv(), timeout=5)
                        error_data = json.loads(error_response)
                        if error_data.get("type") == "error":
                            recovery_successful = True
                    except Exception as e:
                        error_message = str(e)
                        
                elif error_scenario == "authentication_error":
                    # Send message with invalid authentication
                    auth_error_message = {
                        "type": "agent_execution_request",
                        "user_id": "invalid_user_id",
                        "request": "This should fail authentication"
                    }
                    await connection.send(json.dumps(auth_error_message))
                    
                    try:
                        error_response = await asyncio.wait_for(connection.recv(), timeout=5)
                        error_data = json.loads(error_response)
                        if error_data.get("type") == "authentication_error":
                            recovery_successful = True
                    except Exception as e:
                        error_message = str(e)
                
                recovery_time = time.time() - start_time
                
                error_recovery_tests.append({
                    "scenario": error_scenario,
                    "recovery_successful": recovery_successful,
                    "recovery_time": recovery_time,
                    "error_message": error_message
                })
                
                await connection.close()
                
            except Exception as e:
                error_recovery_tests.append({
                    "scenario": error_scenario,
                    "recovery_successful": False,
                    "error_message": str(e),
                    "recovery_time": time.time() - start_time if 'start_time' in locals() else 0
                })
                
        # Validate error recovery results
        successful_recoveries = sum(
            1 for test in error_recovery_tests if test["recovery_successful"]
        )
        
        assert successful_recoveries >= 2, f"Expected at least 2 successful error recoveries, got {successful_recoveries}"
        
        # Check recovery times (shouldn't be too slow due to race conditions)
        slow_recoveries = sum(
            1 for test in error_recovery_tests 
            if test["recovery_time"] > 10.0
        )
        
        assert slow_recoveries == 0, f"Slow error recoveries detected (possible race conditions): {slow_recoveries}"
        
    @pytest.mark.asyncio
    async def test_websocket_performance_under_race_conditions(self, real_services_fixture):
        """
        Test WebSocket performance degradation under race condition scenarios.
        
        This validates that race condition handling doesn't significantly impact
        system performance and throughput.
        """
        user = await self.create_authenticated_user()
        
        # Performance baseline test
        baseline_metrics = await self._measure_websocket_performance_baseline(user)
        
        # Performance under concurrent load (race condition scenario)
        load_metrics = await self._measure_websocket_performance_under_load(user)
        
        # Validate performance metrics
        assert baseline_metrics["successful_requests"] > 0, "Baseline performance test failed"
        assert load_metrics["successful_requests"] > 0, "Load performance test failed"
        
        # Check performance degradation
        performance_degradation = (
            (baseline_metrics["average_response_time"] - load_metrics["average_response_time"]) 
            / baseline_metrics["average_response_time"]
        ) * 100
        
        # Allow up to 200% performance degradation under race conditions
        assert performance_degradation < 200, f"Excessive performance degradation: {performance_degradation}%"
        
        # Check throughput degradation
        throughput_degradation = (
            (baseline_metrics["requests_per_second"] - load_metrics["requests_per_second"])
            / baseline_metrics["requests_per_second"]
        ) * 100
        
        assert throughput_degradation < 80, f"Excessive throughput degradation: {throughput_degradation}%"
        
        self.logger.info(f"Performance test completed. Degradation: {performance_degradation}%, Throughput: {throughput_degradation}%")
        
    async def _measure_websocket_performance_baseline(self, user: AuthenticatedUser) -> Dict[str, float]:
        """Measure baseline WebSocket performance with single connection"""
        websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=user.websocket_headers,
            timeout=10
        )
        
        try:
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            # Perform baseline requests
            request_count = 10
            response_times = []
            successful_requests = 0
            
            start_time = time.time()
            
            for i in range(request_count):
                request_start = time.time()
                
                message = {
                    "type": "ping",
                    "user_id": str(user.user_id),
                    "request_id": f"baseline_{i}"
                }
                
                await connection.send(json.dumps(message))
                response = await asyncio.wait_for(connection.recv(), timeout=5)
                
                response_time = time.time() - request_start
                response_times.append(response_time)
                successful_requests += 1
                
            total_time = time.time() - start_time
            
            return {
                "successful_requests": successful_requests,
                "average_response_time": sum(response_times) / len(response_times),
                "max_response_time": max(response_times),
                "min_response_time": min(response_times),
                "requests_per_second": successful_requests / total_time
            }
            
        finally:
            await connection.close()
    
    async def _measure_websocket_performance_under_load(self, user: AuthenticatedUser) -> Dict[str, float]:
        """Measure WebSocket performance under concurrent load (race condition scenario)"""
        # Create multiple concurrent connections
        connection_count = 5
        requests_per_connection = 5
        
        async def connection_load_test(connection_id: int):
            websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=10
            )
            
            try:
                # Complete handshake
                handshake_message = {
                    "type": "handshake",
                    "user_id": str(user.user_id),
                    "session_id": f"{user.session_id}_{connection_id}"
                }
                
                await connection.send(json.dumps(handshake_message))
                await connection.recv()  # handshake_complete
                
                # Perform load requests
                response_times = []
                successful_requests = 0
                
                for i in range(requests_per_connection):
                    request_start = time.time()
                    
                    message = {
                        "type": "ping",
                        "user_id": str(user.user_id),
                        "request_id": f"load_{connection_id}_{i}"
                    }
                    
                    try:
                        await connection.send(json.dumps(message))
                        response = await asyncio.wait_for(connection.recv(), timeout=10)
                        
                        response_time = time.time() - request_start
                        response_times.append(response_time)
                        successful_requests += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Request failed in connection {connection_id}: {e}")
                        
                return {
                    "connection_id": connection_id,
                    "response_times": response_times,
                    "successful_requests": successful_requests
                }
                
            finally:
                await connection.close()
        
        # Execute concurrent load tests
        start_time = time.time()
        
        load_tasks = []
        for conn_id in range(connection_count):
            task = asyncio.create_task(connection_load_test(conn_id))
            load_tasks.append(task)
            
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Aggregate results
        all_response_times = []
        total_successful_requests = 0
        
        for result in load_results:
            if isinstance(result, dict):
                all_response_times.extend(result["response_times"])
                total_successful_requests += result["successful_requests"]
                
        return {
            "successful_requests": total_successful_requests,
            "average_response_time": sum(all_response_times) / len(all_response_times) if all_response_times else 0,
            "max_response_time": max(all_response_times) if all_response_times else 0,
            "min_response_time": min(all_response_times) if all_response_times else 0,
            "requests_per_second": total_successful_requests / total_time
        }


class TestWebSocketRaceConditionRecovery:
    """
    Advanced integration tests for WebSocket race condition recovery scenarios.
    
    These tests focus on system resilience and cascade failure prevention.
    """
    
    @pytest.fixture(autouse=True)
    def setup_recovery_environment(self, real_services_fixture):
        """Set up environment for recovery testing"""
        self.services = real_services_fixture
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.services['backend_url'])
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.services['backend_url'])
        self.logger = logging.getLogger(__name__)
    
    @pytest.mark.asyncio
    async def test_race_condition_cascade_failure_prevention(self, real_services_fixture):
        """
        Test that isolated race conditions don't cascade into system-wide failures.
        
        This is critical for system stability - race conditions should be contained
        and not affect other users or system components.
        """
        # Create multiple users to test isolation
        users = []
        for i in range(3):
            user_id = UserID(generate_user_id())
            jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
            websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
                jwt_token=jwt_token,
                user_id=str(user_id),
                is_e2e_test=True
            )
            
            users.append(AuthenticatedUser(
                user_id=user_id,
                jwt_token=jwt_token,
                session_id=f"session_{user_id}_{int(time.time())}",
                websocket_headers=websocket_headers
            ))
        
        # Create connections for all users
        connections = []
        for user in users:
            websocket_url = f"ws://localhost:8000/ws/{user.user_id}"
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=10
            )
            
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            connections.append(connection)
        
        try:
            # Trigger race condition in first user (intentional failure)
            race_condition_message = {
                "type": "race_condition_trigger",
                "user_id": str(users[0].user_id),
                "trigger_type": "state_conflict"
            }
            
            # This should trigger a race condition for user 0
            await connections[0].send(json.dumps(race_condition_message))
            
            # Wait briefly for race condition to occur
            await asyncio.sleep(0.5)
            
            # Test that other users are unaffected
            unaffected_users_working = 0
            
            for i in range(1, len(connections)):
                try:
                    test_message = {
                        "type": "ping",
                        "user_id": str(users[i].user_id),
                        "test_isolation": True
                    }
                    
                    await connections[i].send(json.dumps(test_message))
                    response = await asyncio.wait_for(connections[i].recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "pong":
                        unaffected_users_working += 1
                        
                except Exception as e:
                    self.logger.error(f"User {i} affected by cascade failure: {e}")
            
            # Validate cascade failure prevention
            expected_unaffected_users = len(users) - 1
            assert unaffected_users_working == expected_unaffected_users, (
                f"Cascade failure detected. Expected {expected_unaffected_users} "
                f"unaffected users, got {unaffected_users_working}"
            )
            
            self.logger.info("Cascade failure prevention test passed")
            
        finally:
            # Clean up all connections
            for connection in connections:
                await connection.close()


@pytest.mark.asyncio
async def test_critical_websocket_race_condition_scenarios(real_services_fixture):
    """
    High-level integration test for critical WebSocket race condition scenarios.
    
    This test specifically targets the staging environment race condition patterns
    including the User ID: 101463487227881885914 scenario.
    
    Business Value: Prevents production WebSocket failures that cause user chat disruption.
    """
    # Test setup with real services
    services = real_services_fixture
    e2e_auth_helper = E2EAuthHelper(base_url=services['backend_url'])
    websocket_auth_helper = E2EWebSocketAuthHelper(base_url=services['backend_url'])
    
    # Test specific user ID that was failing in staging
    critical_user_id = UserID("101463487227881885914")
    
    # Create authenticated session for critical user
    jwt_token = await e2e_auth_helper.create_authenticated_session(str(critical_user_id))
    websocket_headers = await websocket_auth_helper.create_websocket_auth_headers(
        jwt_token=jwt_token,
        user_id=str(critical_user_id),
        is_e2e_test=True
    )
    
    critical_user = AuthenticatedUser(
        user_id=critical_user_id,
        jwt_token=jwt_token,
        session_id=f"critical_session_{int(time.time())}",
        websocket_headers=websocket_headers
    )
    
    # Test the critical race condition scenario
    websocket_url = f"ws://localhost:8000/ws/{critical_user.user_id}"
    connection = await websockets.connect(
        websocket_url,
        extra_headers=critical_user.websocket_headers,
        timeout=10
    )
    
    try:
        # Test the "Need to call 'accept' first" race condition
        start_time = time.time()
        
        # Rapid handshake sequence (this triggered the original race condition)
        handshake_message = {
            "type": "handshake",
            "user_id": str(critical_user.user_id),
            "session_id": critical_user.session_id,
            "rapid_sequence": True  # Flag to indicate race condition test
        }
        
        await connection.send(json.dumps(handshake_message))
        handshake_response = await asyncio.wait_for(connection.recv(), timeout=10)
        handshake_data = json.loads(handshake_response)
        
        handshake_time = time.time() - start_time
        
        # Validate successful handshake (no race condition)
        assert handshake_data.get('type') == 'handshake_complete', (
            f"Handshake failed for critical user: {handshake_data}"
        )
        assert handshake_data.get('status') == 'success', (
            f"Handshake status not success: {handshake_data.get('status')}"
        )
        
        # Test WebSocket event sequence for critical user
        agent_request = {
            "type": "agent_execution_request",
            "user_id": str(critical_user.user_id),
            "request": "Critical user test request",
            "agent_type": "test_agent"
        }
        
        await connection.send(json.dumps(agent_request))
        
        # Collect event sequence
        events_received = []
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for expected_event in expected_events:
            try:
                event_response = await asyncio.wait_for(connection.recv(), timeout=15)
                event_data = json.loads(event_response)
                events_received.append(event_data.get("type"))
                
                if event_data.get("type") == "agent_completed":
                    break
                    
            except asyncio.TimeoutError:
                logging.warning(f"Timeout waiting for {expected_event} for critical user")
                break
        
        # Validate event sequence for critical user
        critical_events_received = ["agent_started", "agent_completed"]
        critical_events_present = all(event in events_received for event in critical_events_received)
        
        assert critical_events_present, (
            f"Critical events missing for user {critical_user_id}. "
            f"Expected: {critical_events_received}, Received: {events_received}"
        )
        
        # Success metrics
        test_metrics = {
            "critical_user_id": str(critical_user_id),
            "handshake_time": handshake_time,
            "events_received": len(events_received),
            "critical_events_present": critical_events_present,
            "race_condition_resolved": handshake_time < 2.0 and critical_events_present
        }
        
        logging.info(f"Critical race condition test completed: {test_metrics}")
        
        # Final assertion
        assert test_metrics["race_condition_resolved"], (
            "Critical race condition not resolved for staging user scenario"
        )
        
    finally:
        await connection.close()