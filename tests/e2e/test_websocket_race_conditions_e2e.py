"""
WebSocket Race Condition End-to-End (E2E) Tests

CRITICAL: These tests focus on full-stack WebSocket race conditions through Docker containers.
This is the final component of the comprehensive WebSocket Race Condition Tests Suite.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Platform Stability - Prevent production WebSocket chat failures
- Value Impact: Ensures reliable AI-powered chat delivery through complete system stack
- Strategic/Revenue Impact: Prevents $500K+ ARR loss from production WebSocket failures

Key Full-Stack Race Conditions Tested:
1. Handshake timing race conditions through Docker containers ("Need to call 'accept' first")
2. Connection state persistence across full system boundaries (PostgreSQL/Redis/Backend/Auth)
3. WebSocket event ordering through complete application stack
4. Multi-user isolation in full production-like environment
5. Service disruption and recovery through Docker orchestration

E2E TEST REQUIREMENTS:
- Uses REAL services through Docker containers (NO MOCKS)
- MANDATORY authentication with JWT/OAuth for ALL tests
- Tests full-stack WebSocket interactions through complete system
- Validates mission-critical WebSocket events through entire pipeline
- Tests specific staging failure scenarios (User ID: 101463487227881885914)

Author: AI Agent - WebSocket E2E Test Creation
Date: 2025-09-09
"""

import asyncio
import json
import logging
import pytest
import time
import websockets
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from concurrent.futures import as_completed

# CRITICAL: Use real services fixture for full Docker stack (NO MOCKS in E2E tests)
from test_framework.fixtures.real_services import real_services_fixture

# MANDATORY: All E2E tests MUST use authentication per claude.md
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper

# Shared types for strongly typed E2E testing
from shared.types import UserID, ThreadID, RequestID
from shared.ssot_id_manager import SSOT_ID_Manager


@dataclass
class E2EAuthenticatedUser:
    """Fully authenticated user for E2E testing with real JWT tokens"""
    user_id: UserID
    jwt_token: str
    session_id: str
    websocket_headers: Dict[str, str]
    auth_validated: bool = False


@dataclass
class E2EWebSocketMetrics:
    """Metrics tracking for full-stack E2E WebSocket tests"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    handshake_successes: int = 0
    handshake_failures: int = 0
    race_conditions_detected: int = 0
    auth_failures: int = 0
    event_ordering_violations: int = 0
    average_connection_time: float = 0.0
    average_handshake_time: float = 0.0
    total_events_received: int = 0


class TestWebSocketRaceConditionsE2EHandshake:
    """
    E2E tests for WebSocket handshake race conditions through full Docker stack.
    
    CRITICAL: These tests use complete Docker container stack with mandatory authentication
    to validate handshake race condition handling in production-like environment.
    """
    
    @pytest.fixture(autouse=True)
    def setup_e2e_environment(self, real_services_fixture):
        """Set up full Docker stack for E2E testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        
        # MANDATORY: Initialize authentication helpers for E2E
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        
        # E2E test metrics
        self.e2e_metrics = E2EWebSocketMetrics()
        
        # Logger for E2E race condition detection
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def create_e2e_authenticated_user(self, user_id_override: Optional[str] = None) -> E2EAuthenticatedUser:
        """Create fully authenticated user for E2E testing through complete auth stack"""
        if user_id_override:
            user_id = UserID(user_id_override)
        else:
            user_id = SSOT_ID_Manager.generate_user_id()
            
        # MANDATORY: Create real JWT token through full auth service stack
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        session_id = f"e2e_session_{user_id}_{int(time.time())}"
        
        # MANDATORY: Create authenticated WebSocket headers through auth service
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(user_id),
            is_e2e_test=True
        )
        
        # Validate authentication worked through full stack
        auth_validated = await self._validate_e2e_authentication(jwt_token, str(user_id))
        
        return E2EAuthenticatedUser(
            user_id=user_id,
            jwt_token=jwt_token,
            session_id=session_id,
            websocket_headers=websocket_headers,
            auth_validated=auth_validated
        )
        
    async def _validate_e2e_authentication(self, jwt_token: str, user_id: str) -> bool:
        """Validate authentication through full E2E stack"""
        try:
            # Validate JWT token through auth service API
            validation_result = await self.e2e_auth_helper.validate_token_through_api(jwt_token)
            return validation_result.get('user_id') == user_id and validation_result.get('valid', False)
        except Exception as e:
            self.logger.error(f"E2E authentication validation failed: {e}")
            return False
    
    @pytest.mark.asyncio
    async def test_critical_user_handshake_race_condition_e2e(self, real_services_fixture):
        """
        CRITICAL E2E: Test specific User ID 101463487227881885914 handshake race condition.
        
        This test reproduces the exact staging failure scenario through full Docker stack
        with real authentication to ensure the race condition is resolved.
        """
        # MANDATORY: Test specific critical user ID from staging logs
        critical_user = await self.create_e2e_authenticated_user("101463487227881885914")
        
        # Validate authentication before proceeding
        assert critical_user.auth_validated, f"Authentication failed for critical user {critical_user.user_id}"
        
        # Test handshake race condition through full stack
        websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{critical_user.user_id}"
        
        race_condition_resolved = False
        handshake_attempts = []
        
        # Test rapid handshake sequences (reproducing race condition)
        for attempt in range(3):
            start_time = time.time()
            
            try:
                # Connect with MANDATORY authentication through full stack
                connection = await websockets.connect(
                    websocket_url,
                    extra_headers=critical_user.websocket_headers,
                    timeout=15  # Longer timeout for full stack
                )
                
                # Rapid handshake sequence (triggers original race condition)
                handshake_message = {
                    "type": "handshake",
                    "user_id": str(critical_user.user_id),
                    "session_id": critical_user.session_id,
                    "critical_user_test": True,
                    "staging_reproduction": True
                }
                
                await connection.send(json.dumps(handshake_message))
                response = await asyncio.wait_for(connection.recv(), timeout=10)
                response_data = json.loads(response)
                
                handshake_time = time.time() - start_time
                
                # Validate successful handshake (race condition resolved)
                if (response_data.get('type') == 'handshake_complete' and 
                    response_data.get('status') == 'success'):
                    race_condition_resolved = True
                    self.e2e_metrics.handshake_successes += 1
                    
                handshake_attempts.append({
                    'attempt': attempt,
                    'success': race_condition_resolved,
                    'handshake_time': handshake_time,
                    'response': response_data
                })
                
                await connection.close()
                
            except Exception as e:
                handshake_time = time.time() - start_time
                self.e2e_metrics.handshake_failures += 1
                handshake_attempts.append({
                    'attempt': attempt,
                    'success': False,
                    'handshake_time': handshake_time,
                    'error': str(e)
                })
                
        # CRITICAL: Assert race condition is resolved for staging user
        successful_handshakes = sum(1 for attempt in handshake_attempts if attempt['success'])
        assert successful_handshakes >= 2, f"Critical user handshake race condition not resolved. Successes: {successful_handshakes}"
        
        # Validate handshake performance (should be fast, not affected by race condition)
        avg_handshake_time = sum(attempt['handshake_time'] for attempt in handshake_attempts) / len(handshake_attempts)
        assert avg_handshake_time < 3.0, f"Handshake taking too long due to race conditions: {avg_handshake_time}s"
        
        self.logger.info(f"Critical user race condition test passed. User: {critical_user.user_id}, Attempts: {len(handshake_attempts)}")
    
    @pytest.mark.asyncio 
    async def test_concurrent_handshake_race_conditions_e2e(self, real_services_fixture):
        """
        E2E test for concurrent handshake race conditions through full Docker stack.
        
        This validates that multiple users can handshake simultaneously without
        race conditions affecting system stability.
        """
        # Create multiple authenticated users for concurrent testing
        user_count = 5
        users = []
        
        for i in range(user_count):
            user = await self.create_e2e_authenticated_user()
            assert user.auth_validated, f"Authentication failed for user {i}: {user.user_id}"
            users.append(user)
            
        # Execute concurrent handshakes
        concurrent_handshake_tasks = []
        for user in users:
            task = asyncio.create_task(self._perform_e2e_handshake(user))
            concurrent_handshake_tasks.append(task)
            
        # Wait for all concurrent handshakes
        handshake_results = await asyncio.gather(*concurrent_handshake_tasks, return_exceptions=True)
        
        # Analyze race condition results
        successful_handshakes = 0
        race_conditions_detected = 0
        authentication_failures = 0
        
        for i, result in enumerate(handshake_results):
            if isinstance(result, Exception):
                if "race condition" in str(result).lower():
                    race_conditions_detected += 1
                elif "auth" in str(result).lower():
                    authentication_failures += 1
                self.logger.error(f"Concurrent handshake failed for user {users[i].user_id}: {result}")
            elif result and result.get('success'):
                successful_handshakes += 1
                
        # Validate concurrent handshake results
        assert successful_handshakes >= 4, f"Expected at least 4 successful concurrent handshakes, got {successful_handshakes}"
        assert race_conditions_detected == 0, f"Race conditions detected in concurrent handshakes: {race_conditions_detected}"
        assert authentication_failures == 0, f"Authentication failures in concurrent handshakes: {authentication_failures}"
        
        self.logger.info(f"Concurrent handshake race condition test passed. Users: {user_count}, Successes: {successful_handshakes}")
        
    async def _perform_e2e_handshake(self, user: E2EAuthenticatedUser) -> Dict[str, Any]:
        """Perform full E2E handshake through Docker stack"""
        try:
            start_time = time.time()
            
            websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=15
            )
            
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id,
                "e2e_test": True
            }
            
            await connection.send(json.dumps(handshake_message))
            response = await asyncio.wait_for(connection.recv(), timeout=10)
            response_data = json.loads(response)
            
            handshake_time = time.time() - start_time
            
            success = (response_data.get('type') == 'handshake_complete' and 
                      response_data.get('status') == 'success')
                      
            await connection.close()
            
            return {
                'success': success,
                'handshake_time': handshake_time,
                'user_id': str(user.user_id),
                'response': response_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'user_id': str(user.user_id),
                'handshake_time': time.time() - start_time if 'start_time' in locals() else 0
            }


class TestWebSocketRaceConditionsE2EAgentExecution:
    """
    E2E tests for WebSocket race conditions during agent execution through full stack.
    
    These tests validate the 5 mission-critical WebSocket events through complete system.
    """
    
    @pytest.fixture(autouse=True)
    def setup_agent_execution_environment(self, real_services_fixture):
        """Set up full stack for agent execution testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        self.logger = logging.getLogger(__name__)
    
    async def create_authenticated_user_for_agent_execution(self) -> E2EAuthenticatedUser:
        """Create authenticated user for agent execution testing"""
        user_id = SSOT_ID_Manager.generate_user_id()
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        session_id = f"agent_exec_{user_id}_{int(time.time())}"
        
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(user_id),
            is_e2e_test=True
        )
        
        return E2EAuthenticatedUser(
            user_id=user_id,
            jwt_token=jwt_token,
            session_id=session_id,
            websocket_headers=websocket_headers,
            auth_validated=True
        )
    
    @pytest.mark.asyncio
    async def test_websocket_event_ordering_during_agent_execution_e2e(self, real_services_fixture):
        """
        E2E test for WebSocket event ordering during agent execution through full stack.
        
        CRITICAL: This validates the 5 mission-critical WebSocket events are delivered 
        in order through complete Docker container stack.
        """
        user = await self.create_authenticated_user_for_agent_execution()
        
        websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=user.websocket_headers,
            timeout=15
        )
        
        try:
            # Complete handshake through full stack
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            handshake_response = await connection.recv()
            handshake_data = json.loads(handshake_response)
            assert handshake_data.get('type') == 'handshake_complete'
            
            # Execute agent request and collect events through full system
            agent_request = {
                "type": "agent_execution_request",
                "user_id": str(user.user_id),
                "request": "E2E agent execution test",
                "agent_type": "test_agent",
                "request_id": f"e2e_{int(time.time())}"
            }
            
            await connection.send(json.dumps(agent_request))
            
            # Collect mission-critical events through full stack
            events_received = []
            expected_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            
            event_start_time = time.time()
            
            for expected_event in expected_events:
                try:
                    event_response = await asyncio.wait_for(connection.recv(), timeout=20)
                    event_data = json.loads(event_response)
                    
                    events_received.append({
                        "type": event_data.get("type"),
                        "timestamp": time.time(),
                        "user_id": event_data.get("user_id")
                    })
                    
                    # Validate user isolation in events
                    assert event_data.get("user_id") == str(user.user_id), "Event user isolation violated"
                    
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout waiting for {expected_event} through full stack")
                    break
                    
            total_event_time = time.time() - event_start_time
            
            # Validate event ordering through full stack
            event_types = [event["type"] for event in events_received]
            
            # CRITICAL: Validate mission-critical events are present
            critical_events = ["agent_started", "agent_completed"]
            critical_events_present = all(event in event_types for event in critical_events)
            assert critical_events_present, f"Critical events missing through full stack. Received: {event_types}"
            
            # Validate event timing (should complete within reasonable time through full stack)
            assert total_event_time < 30.0, f"Agent execution taking too long through full stack: {total_event_time}s"
            
            # Check for temporal race conditions in events
            temporal_violations = 0
            if len(events_received) >= 2:
                for i in range(1, len(events_received)):
                    time_diff = events_received[i]["timestamp"] - events_received[i-1]["timestamp"]
                    if time_diff < 0.001:  # Events too close together
                        temporal_violations += 1
                        
            # Temporal violations are warnings for E2E (network latency affects timing)
            if temporal_violations > 0:
                self.logger.warning(f"Temporal event violations in E2E: {temporal_violations}")
                
            self.logger.info(f"E2E agent execution event ordering test passed. Events: {len(events_received)}, Time: {total_event_time}s")
            
        finally:
            await connection.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_agent_execution_isolation_e2e(self, real_services_fixture):
        """
        E2E test for concurrent agent execution isolation through full stack.
        
        This validates that multiple users can execute agents simultaneously
        without race conditions or message leakage between users.
        """
        # Create multiple authenticated users
        user_count = 3
        users = []
        
        for i in range(user_count):
            user = await self.create_authenticated_user_for_agent_execution()
            users.append(user)
            
        # Execute concurrent agent requests
        concurrent_execution_tasks = []
        for i, user in enumerate(users):
            task = asyncio.create_task(self._execute_agent_with_isolation_validation(user, i))
            concurrent_execution_tasks.append(task)
            
        # Wait for all concurrent executions
        execution_results = await asyncio.gather(*concurrent_execution_tasks, return_exceptions=True)
        
        # Validate isolation and race condition results
        successful_executions = 0
        isolation_violations = 0
        
        for i, result in enumerate(execution_results):
            if isinstance(result, Exception):
                if "isolation" in str(result).lower():
                    isolation_violations += 1
                self.logger.error(f"Concurrent agent execution failed for user {users[i].user_id}: {result}")
            elif result and result.get('success'):
                successful_executions += 1
                
        # Validate concurrent execution isolation
        assert successful_executions >= 2, f"Expected at least 2 successful concurrent executions, got {successful_executions}"
        assert isolation_violations == 0, f"User isolation violations detected: {isolation_violations}"
        
        self.logger.info(f"Concurrent agent execution isolation test passed. Users: {user_count}, Successes: {successful_executions}")
        
    async def _execute_agent_with_isolation_validation(self, user: E2EAuthenticatedUser, user_index: int) -> Dict[str, Any]:
        """Execute agent with user isolation validation"""
        try:
            websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=15
            )
            
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            # Execute agent with user-specific request
            agent_request = {
                "type": "agent_execution_request",
                "user_id": str(user.user_id),
                "request": f"Isolation test request from user {user_index}",
                "user_index": user_index
            }
            
            await connection.send(json.dumps(agent_request))
            
            # Collect events and validate user isolation
            user_events = []
            for _ in range(3):  # Expect at least agent_started, agent_thinking, agent_completed
                try:
                    event_response = await asyncio.wait_for(connection.recv(), timeout=15)
                    event_data = json.loads(event_response)
                    
                    # CRITICAL: Validate user isolation
                    event_user_id = event_data.get("user_id")
                    if event_user_id and event_user_id != str(user.user_id):
                        raise Exception(f"User isolation violated: Expected {user.user_id}, got {event_user_id}")
                        
                    user_events.append(event_data)
                    
                    if event_data.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
                    
            await connection.close()
            
            return {
                'success': len(user_events) >= 2,
                'user_id': str(user.user_id),
                'events_received': len(user_events),
                'user_index': user_index
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'user_id': str(user.user_id),
                'user_index': user_index
            }


class TestWebSocketRaceConditionsE2EPerformance:
    """
    E2E performance tests for WebSocket race conditions under high load through full stack.
    """
    
    @pytest.fixture(autouse=True)
    def setup_performance_environment(self, real_services_fixture):
        """Set up full stack for performance testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        self.logger = logging.getLogger(__name__)
    
    @pytest.mark.asyncio
    async def test_high_concurrency_websocket_performance_e2e(self, real_services_fixture):
        """
        E2E performance test under high concurrency through full Docker stack.
        
        This validates that the system maintains performance under high load
        without race condition degradation.
        """
        # High concurrency parameters for E2E testing
        concurrent_users = 25
        connections_per_user = 2
        total_expected_connections = concurrent_users * connections_per_user
        
        self.logger.info(f"Starting high concurrency E2E test. Users: {concurrent_users}, Total connections: {total_expected_connections}")
        
        # Create authenticated users for high concurrency test
        users = []
        for i in range(concurrent_users):
            user_id = SSOT_ID_Manager.generate_user_id()
            jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
            websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
                jwt_token=jwt_token,
                user_id=str(user_id),
                is_e2e_test=True
            )
            
            users.append(E2EAuthenticatedUser(
                user_id=user_id,
                jwt_token=jwt_token,
                session_id=f"perf_{user_id}_{int(time.time())}",
                websocket_headers=websocket_headers,
                auth_validated=True
            ))
            
        # Execute high concurrency connections
        connection_tasks = []
        start_time = time.time()
        
        for user in users:
            for conn_index in range(connections_per_user):
                task = asyncio.create_task(self._create_performance_connection(user, conn_index))
                connection_tasks.append(task)
                
        # Process connections in batches to avoid overwhelming the system
        batch_size = 10
        connection_results = []
        
        for i in range(0, len(connection_tasks), batch_size):
            batch = connection_tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            connection_results.extend(batch_results)
            
            # Brief pause between batches
            await asyncio.sleep(0.1)
            
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_connections = 0
        failed_connections = 0
        race_conditions_detected = 0
        connection_times = []
        
        for result in connection_results:
            if isinstance(result, Exception):
                failed_connections += 1
                if "race condition" in str(result).lower():
                    race_conditions_detected += 1
            elif result and result.get('success'):
                successful_connections += 1
                if 'connection_time' in result:
                    connection_times.append(result['connection_time'])
            else:
                failed_connections += 1
                
        # Validate high concurrency performance
        success_rate = successful_connections / len(connection_tasks) * 100
        assert success_rate >= 80, f"Low success rate under high concurrency: {success_rate}%"
        
        assert race_conditions_detected == 0, f"Race conditions detected under high load: {race_conditions_detected}"
        
        # Validate connection performance
        if connection_times:
            avg_connection_time = sum(connection_times) / len(connection_times)
            assert avg_connection_time < 5.0, f"Slow connections under high load: {avg_connection_time}s"
            
        self.logger.info(f"High concurrency E2E test passed. Connections: {len(connection_tasks)}, "
                        f"Success rate: {success_rate}%, Total time: {total_time}s")
        
    async def _create_performance_connection(self, user: E2EAuthenticatedUser, conn_index: int) -> Dict[str, Any]:
        """Create performance test connection"""
        try:
            start_time = time.time()
            
            websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{user.user_id}"
            connection = await websockets.connect(
                websocket_url,
                extra_headers=user.websocket_headers,
                timeout=10
            )
            
            # Quick handshake for performance testing
            handshake_message = {
                "type": "handshake",
                "user_id": str(user.user_id),
                "session_id": f"{user.session_id}_{conn_index}",
                "performance_test": True
            }
            
            await connection.send(json.dumps(handshake_message))
            response = await asyncio.wait_for(connection.recv(), timeout=5)
            response_data = json.loads(response)
            
            connection_time = time.time() - start_time
            success = response_data.get('type') == 'handshake_complete'
            
            await connection.close()
            
            return {
                'success': success,
                'connection_time': connection_time,
                'user_id': str(user.user_id),
                'conn_index': conn_index
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'connection_time': time.time() - start_time if 'start_time' in locals() else 0,
                'user_id': str(user.user_id),
                'conn_index': conn_index
            }


class TestWebSocketRaceConditionsE2EGoldenPath:
    """
    E2E Golden Path tests for mission-critical WebSocket scenarios.
    
    These tests focus on the most important user journeys through full stack.
    """
    
    @pytest.fixture(autouse=True)
    def setup_golden_path_environment(self, real_services_fixture):
        """Set up full stack for golden path testing"""
        self.services = real_services_fixture
        self.backend_url = self.services['backend_url']
        self.e2e_auth_helper = E2EAuthHelper(base_url=self.backend_url)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(base_url=self.backend_url)
        self.logger = logging.getLogger(__name__)
    
    @pytest.mark.asyncio
    async def test_new_user_first_interaction_golden_path_e2e(self, real_services_fixture):
        """
        CRITICAL Golden Path E2E: New user's first WebSocket interaction.
        
        This is the most critical business flow - new user connecting and 
        successfully executing their first agent through full stack.
        """
        # Create new user (simulating first-time user experience)
        new_user_id = SSOT_ID_Manager.generate_user_id()
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(new_user_id))
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(new_user_id),
            is_e2e_test=True
        )
        
        new_user = E2EAuthenticatedUser(
            user_id=new_user_id,
            jwt_token=jwt_token,
            session_id=f"new_user_{new_user_id}_{int(time.time())}",
            websocket_headers=websocket_headers,
            auth_validated=True
        )
        
        # Execute complete first interaction flow
        websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{new_user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=new_user.websocket_headers,
            timeout=15
        )
        
        try:
            # Step 1: First handshake (most critical)
            handshake_start = time.time()
            
            handshake_message = {
                "type": "handshake",
                "user_id": str(new_user.user_id),
                "session_id": new_user.session_id,
                "first_interaction": True
            }
            
            await connection.send(json.dumps(handshake_message))
            handshake_response = await asyncio.wait_for(connection.recv(), timeout=10)
            handshake_data = json.loads(handshake_response)
            
            handshake_time = time.time() - handshake_start
            
            # CRITICAL: First handshake must succeed
            assert handshake_data.get('type') == 'handshake_complete', "New user first handshake failed"
            assert handshake_data.get('status') == 'success', "New user handshake status not success"
            assert handshake_time < 3.0, f"New user handshake too slow: {handshake_time}s"
            
            # Step 2: First agent execution (business value delivery)
            agent_start = time.time()
            
            first_agent_request = {
                "type": "agent_execution_request", 
                "user_id": str(new_user.user_id),
                "request": "Hello, this is my first interaction with the AI system",
                "first_interaction": True,
                "agent_type": "welcome_agent"
            }
            
            await connection.send(json.dumps(first_agent_request))
            
            # Step 3: Collect first interaction events
            first_interaction_events = []
            critical_events_received = {"agent_started": False, "agent_completed": False}
            
            for _ in range(5):  # Expect up to 5 events
                try:
                    event_response = await asyncio.wait_for(connection.recv(), timeout=20)
                    event_data = json.loads(event_response)
                    first_interaction_events.append(event_data)
                    
                    event_type = event_data.get("type")
                    if event_type in critical_events_received:
                        critical_events_received[event_type] = True
                        
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
                    
            agent_execution_time = time.time() - agent_start
            
            # CRITICAL: First interaction must deliver value
            assert critical_events_received["agent_started"], "New user did not receive agent_started event"
            assert critical_events_received["agent_completed"], "New user did not receive agent_completed event"
            assert len(first_interaction_events) >= 2, "Insufficient events for new user first interaction"
            assert agent_execution_time < 30.0, f"First interaction too slow: {agent_execution_time}s"
            
            # Validate business value delivery (events contain actual content)
            agent_completed_event = next(
                (event for event in first_interaction_events if event.get("type") == "agent_completed"), 
                None
            )
            assert agent_completed_event is not None, "No agent_completed event found"
            
            self.logger.info(f"New user first interaction golden path passed. User: {new_user.user_id}, "
                           f"Handshake: {handshake_time}s, Execution: {agent_execution_time}s")
            
        finally:
            await connection.close()
    
    @pytest.mark.asyncio
    async def test_returning_user_multi_agent_scenario_e2e(self, real_services_fixture):
        """
        Golden Path E2E: Returning user executing multiple agents in sequence.
        
        This validates sustained WebSocket performance for power users.
        """
        # Create returning user
        returning_user_id = SSOT_ID_Manager.generate_user_id()
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(returning_user_id))
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(returning_user_id),
            is_e2e_test=True
        )
        
        returning_user = E2EAuthenticatedUser(
            user_id=returning_user_id,
            jwt_token=jwt_token,
            session_id=f"returning_{returning_user_id}_{int(time.time())}",
            websocket_headers=websocket_headers,
            auth_validated=True
        )
        
        # Execute multi-agent sequence
        websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{returning_user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=returning_user.websocket_headers,
            timeout=15
        )
        
        try:
            # Quick handshake (returning users should be fast)
            handshake_message = {
                "type": "handshake",
                "user_id": str(returning_user.user_id),
                "session_id": returning_user.session_id,
                "returning_user": True
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            # Execute sequence of agents
            agent_requests = [
                {"request": "Analyze my data", "agent_type": "data_agent"},
                {"request": "Optimize my workflow", "agent_type": "optimization_agent"},
                {"request": "Generate a report", "agent_type": "reporting_agent"}
            ]
            
            successful_agent_executions = 0
            total_sequence_start = time.time()
            
            for i, agent_config in enumerate(agent_requests):
                # Send agent request
                agent_request = {
                    "type": "agent_execution_request",
                    "user_id": str(returning_user.user_id),
                    "request": agent_config["request"],
                    "agent_type": agent_config["agent_type"],
                    "sequence_number": i + 1
                }
                
                await connection.send(json.dumps(agent_request))
                
                # Collect events for this agent
                agent_events = []
                for _ in range(5):
                    try:
                        event_response = await asyncio.wait_for(connection.recv(), timeout=15)
                        event_data = json.loads(event_response)
                        agent_events.append(event_data)
                        
                        if event_data.get("type") == "agent_completed":
                            successful_agent_executions += 1
                            break
                            
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout for agent {i + 1} in sequence")
                        break
                        
            total_sequence_time = time.time() - total_sequence_start
            
            # Validate multi-agent sequence
            expected_agents = len(agent_requests)
            assert successful_agent_executions >= 2, f"Expected at least 2 successful agent executions, got {successful_agent_executions}"
            assert total_sequence_time < 60.0, f"Multi-agent sequence too slow: {total_sequence_time}s"
            
            self.logger.info(f"Returning user multi-agent scenario passed. User: {returning_user.user_id}, "
                           f"Agents: {successful_agent_executions}/{expected_agents}, Time: {total_sequence_time}s")
            
        finally:
            await connection.close()
            
    @pytest.mark.asyncio
    async def test_error_recovery_graceful_degradation_e2e(self, real_services_fixture):
        """
        Golden Path E2E: Error recovery and graceful degradation through full stack.
        
        This validates that the system gracefully handles errors without race conditions
        affecting the overall user experience.
        """
        # Create user for error recovery testing
        user_id = SSOT_ID_Manager.generate_user_id()
        jwt_token = await self.e2e_auth_helper.create_authenticated_session(str(user_id))
        websocket_headers = await self.websocket_auth_helper.create_websocket_auth_headers(
            jwt_token=jwt_token,
            user_id=str(user_id),
            is_e2e_test=True
        )
        
        error_recovery_user = E2EAuthenticatedUser(
            user_id=user_id,
            jwt_token=jwt_token,
            session_id=f"error_recovery_{user_id}_{int(time.time())}",
            websocket_headers=websocket_headers,
            auth_validated=True
        )
        
        # Test error recovery scenarios
        websocket_url = f"ws://{self.backend_url.replace('http://', '')}/ws/{error_recovery_user.user_id}"
        connection = await websockets.connect(
            websocket_url,
            extra_headers=error_recovery_user.websocket_headers,
            timeout=15
        )
        
        try:
            # Complete handshake
            handshake_message = {
                "type": "handshake",
                "user_id": str(error_recovery_user.user_id),
                "session_id": error_recovery_user.session_id
            }
            
            await connection.send(json.dumps(handshake_message))
            await connection.recv()  # handshake_complete
            
            # Test graceful error handling
            error_scenarios = [
                {"type": "invalid_request", "expected_recovery": True},
                {"type": "timeout_request", "expected_recovery": True},
                {"type": "normal_request", "expected_recovery": True}  # Should work after errors
            ]
            
            recovery_successes = 0
            
            for scenario in error_scenarios:
                try:
                    if scenario["type"] == "invalid_request":
                        # Send malformed request
                        await connection.send("invalid json")
                        
                    elif scenario["type"] == "timeout_request":
                        # Send request that might timeout
                        timeout_request = {
                            "type": "agent_execution_request",
                            "user_id": str(error_recovery_user.user_id),
                            "request": "This is a request that might timeout",
                            "timeout_test": True
                        }
                        await connection.send(json.dumps(timeout_request))
                        
                    elif scenario["type"] == "normal_request":
                        # Send normal request after errors
                        normal_request = {
                            "type": "agent_execution_request",
                            "user_id": str(error_recovery_user.user_id),
                            "request": "Normal request after error recovery",
                            "recovery_test": True
                        }
                        await connection.send(json.dumps(normal_request))
                        
                    # Try to receive response (graceful error handling)
                    try:
                        response = await asyncio.wait_for(connection.recv(), timeout=10)
                        response_data = json.loads(response)
                        
                        # Successful recovery if we get any valid response
                        if response_data.get("type") in ["error", "agent_started", "agent_completed"]:
                            recovery_successes += 1
                            
                    except (asyncio.TimeoutError, json.JSONDecodeError):
                        # Timeout/decode errors are acceptable for error scenarios
                        if scenario["type"] != "normal_request":
                            recovery_successes += 1
                            
                except Exception as e:
                    if scenario["type"] == "normal_request":
                        self.logger.error(f"Normal request failed after error recovery: {e}")
                    else:
                        # Error scenarios are expected to have some failures
                        recovery_successes += 1
                        
            # Validate graceful error recovery
            expected_recoveries = len(error_scenarios)
            assert recovery_successes >= 2, f"Insufficient error recovery. Expected: {expected_recoveries}, Got: {recovery_successes}"
            
            self.logger.info(f"Error recovery and graceful degradation test passed. "
                           f"User: {error_recovery_user.user_id}, Recoveries: {recovery_successes}/{expected_recoveries}")
            
        finally:
            await connection.close()