"""
Concurrent User WebSocket Connections Integration Tests - Phase 2

Tests concurrent WebSocket connections from multiple users to validate
user isolation, connection pool management, and system performance
under realistic multi-user load.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Support multiple simultaneous users without degradation
- Value Impact: Platform scales to serve concurrent users effectively
- Strategic Impact: Multi-tenant system reliability and user experience

CRITICAL: Uses REAL services (PostgreSQL, Redis, WebSocket connections)
No mocks in integration tests per CLAUDE.md standards.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.base_test_case import BaseIntegrationTest
from test_framework.websocket_helpers import (
    WebSocketTestHelpers,
    ensure_websocket_service_ready,
    establish_minimum_websocket_connections
)
from shared.isolated_environment import get_env
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.id_generation import UnifiedIdGenerator


class TestConcurrentUserWebSocketConnections(BaseIntegrationTest):
    """Integration tests for concurrent user WebSocket connections and isolation."""

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup test environment with real services."""
        self.services = real_services_fixture
        self.env = get_env()
        
        # Validate real services are available
        if not self.services["database_available"]:
            pytest.skip("Real database not available - required for integration testing")
            
        # Store service URLs
        self.backend_url = self.services["backend_url"]
        self.websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        
        # Generate base test identifiers
        self.test_session_id = f"concurrent_test_{int(time.time() * 1000)}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_connection_isolation(self, real_services_fixture):
        """Test that concurrent user connections maintain proper isolation."""
        start_time = time.time()
        
        # Ensure WebSocket service is ready
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Create multiple test users
        num_users = 5
        test_users = []
        user_connections = []
        user_events = {}
        
        for i in range(num_users):
            user_id = UserID(f"concurrent_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
            thread_id = ThreadID(f"concurrent_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
            test_users.append((user_id, thread_id))
            user_events[str(user_id)] = []
        
        try:
            # Phase 1: Establish concurrent connections
            for i, (user_id, thread_id) in enumerate(test_users):
                test_token = self._create_test_auth_token(user_id)
                headers = {"Authorization": f"Bearer {test_token}"}
                
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=headers,
                    user_id=str(user_id)
                )
                
                user_connections.append((websocket, user_id, thread_id))
            
            # Verify all connections established
            assert len(user_connections) == num_users, f"Should have {num_users} connections, got {len(user_connections)}"
            
            # Phase 2: Send user-specific requests concurrently
            async def send_user_specific_request(websocket, user_id, thread_id, user_index):
                """Send a user-specific request and collect initial response."""
                user_request = {
                    "type": "agent_request",
                    "agent_name": "isolation_test_agent",
                    "message": f"User {user_index} isolation test request",
                    "user_id": str(user_id),
                    "thread_id": str(thread_id),
                    "user_specific_data": {
                        "user_index": user_index,
                        "test_session": self.test_session_id,
                        "isolation_marker": f"user_{user_index}_unique_marker"
                    }
                }
                
                await WebSocketTestHelpers.send_test_message(websocket, user_request)
                
                # Collect initial response
                try:
                    response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=5.0)
                    response["user_index"] = user_index
                    user_events[str(user_id)].append(response)
                except Exception:
                    pass  # Some responses may be delayed
            
            # Send all user requests concurrently
            user_request_tasks = []
            for i, (websocket, user_id, thread_id) in enumerate(user_connections):
                task = send_user_specific_request(websocket, user_id, thread_id, i)
                user_request_tasks.append(task)
            
            await asyncio.gather(*user_request_tasks, return_exceptions=True)
            
            # Phase 3: Continue collecting events to verify isolation
            async def collect_user_events(websocket, user_id, collection_duration=8.0):
                """Collect events for a specific user."""
                collection_start = time.time()
                
                while time.time() - collection_start < collection_duration:
                    try:
                        event = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                        event["collection_time"] = time.time()
                        user_events[str(user_id)].append(event)
                        
                        # Stop collecting if agent completed
                        if event.get("type") == "agent_completed":
                            break
                            
                    except Exception:
                        # Timeout expected
                        break
            
            # Collect events from all users concurrently
            collection_tasks = []
            for websocket, user_id, _ in user_connections:
                task = collect_user_events(websocket, user_id)
                collection_tasks.append(task)
            
            await asyncio.gather(*collection_tasks, return_exceptions=True)
            
        finally:
            # Clean up all connections
            for websocket, _, _ in user_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 5.0, f"Concurrent user test took too little time: {test_duration:.2f}s"
        
        # Analyze user isolation
        total_events = sum(len(events) for events in user_events.values())
        assert total_events >= num_users, f"Should have received events from concurrent users, got {total_events}"
        
        # Verify user-specific data isolation
        for i, (user_id, _) in enumerate(test_users):
            user_id_str = str(user_id)
            user_event_list = user_events[user_id_str]
            
            if user_event_list:
                # Verify events belong to correct user
                for event in user_event_list:
                    event_user_id = event.get("user_id") or event.get("data", {}).get("user_id")
                    if event_user_id:
                        assert event_user_id == user_id_str, f"Event user_id mismatch: expected {user_id_str}, got {event_user_id}"
                    
                    # Verify user-specific markers haven't leaked
                    event_str = json.dumps(event)
                    for j in range(num_users):
                        if j != i:  # Check other users' markers don't appear
                            other_marker = f"user_{j}_unique_marker"
                            assert other_marker not in event_str, f"User {i} events contain other user's marker: {other_marker}"
        
        # Verify no cross-user event contamination
        user_markers = {}
        for i, (user_id, _) in enumerate(test_users):
            user_markers[str(user_id)] = f"user_{i}_unique_marker"
        
        for user_id_str, events in user_events.items():
            user_marker = user_markers[user_id_str]
            
            for event in events:
                event_content = json.dumps(event)
                
                # Should contain own marker (if present)
                # Should NOT contain other users' markers
                for other_user_id, other_marker in user_markers.items():
                    if other_user_id != user_id_str and other_marker in event_content:
                        assert False, f"User {user_id_str} events contaminated with marker from {other_user_id}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_high_concurrency_connection_pool_management(self, real_services_fixture):
        """Test connection pool management under high concurrent load."""
        start_time = time.time()
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Test with higher number of concurrent connections
        num_concurrent_connections = 12
        connection_results = {}
        active_connections = []
        
        try:
            # Phase 1: Establish connections in batches to avoid overwhelming
            batch_size = 4
            for batch_start in range(0, num_concurrent_connections, batch_size):
                batch_connections = []
                
                # Create batch of connections
                for i in range(batch_start, min(batch_start + batch_size, num_concurrent_connections)):
                    user_id = UserID(f"pool_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
                    thread_id = ThreadID(f"pool_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
                    
                    test_token = self._create_test_auth_token(user_id)
                    headers = {"Authorization": f"Bearer {test_token}"}
                    
                    try:
                        websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                            f"{self.websocket_url}/agent/{thread_id}",
                            headers=headers,
                            user_id=str(user_id),
                            timeout=8.0,  # Longer timeout for high concurrency
                            max_retries=2
                        )
                        
                        batch_connections.append((websocket, user_id, thread_id, i))
                        connection_results[i] = "connected"
                        
                    except Exception as e:
                        connection_results[i] = f"failed: {str(e)}"
                
                active_connections.extend(batch_connections)
                
                # Brief pause between batches to allow connection pool management
                await asyncio.sleep(0.5)
            
            # Verify connection establishment
            successful_connections = len([conn for conn in active_connections])
            assert successful_connections >= 8, f"Should have established at least 8 connections, got {successful_connections}"
            
            # Phase 2: Test connection pool under load
            async def stress_test_connection(websocket, user_id, thread_id, connection_index):
                """Apply load to a specific connection."""
                messages_sent = 0
                responses_received = 0
                
                try:
                    # Send multiple messages to stress connection pool
                    for msg_num in range(3):
                        stress_message = {
                            "type": "stress_test_message",
                            "user_id": str(user_id),
                            "thread_id": str(thread_id),
                            "connection_index": connection_index,
                            "message_number": msg_num,
                            "load_test": True
                        }
                        
                        await WebSocketTestHelpers.send_test_message(websocket, stress_message)
                        messages_sent += 1
                        
                        # Try to receive response
                        try:
                            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=2.0)
                            responses_received += 1
                        except Exception:
                            pass  # Responses may be delayed under load
                            
                        await asyncio.sleep(0.1)  # Brief pause between messages
                
                except Exception as e:
                    return {"connection_index": connection_index, "error": str(e), "messages_sent": messages_sent, "responses_received": responses_received}
                
                return {"connection_index": connection_index, "messages_sent": messages_sent, "responses_received": responses_received}
            
            # Apply concurrent load to all connections
            stress_tasks = []
            for websocket, user_id, thread_id, connection_index in active_connections:
                task = stress_test_connection(websocket, user_id, thread_id, connection_index)
                stress_tasks.append(task)
            
            stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
            
            # Phase 3: Test connection pool recovery
            await asyncio.sleep(2.0)  # Allow pool to stabilize
            
            # Send final health check messages
            health_check_results = []
            for websocket, user_id, thread_id, connection_index in active_connections[:5]:  # Test subset
                try:
                    health_check = {
                        "type": "connection_health_check",
                        "user_id": str(user_id),
                        "connection_index": connection_index
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, health_check)
                    
                    # Try to get health response
                    try:
                        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                        health_check_results.append({"connection_index": connection_index, "healthy": True})
                    except Exception:
                        health_check_results.append({"connection_index": connection_index, "healthy": False})
                        
                except Exception as e:
                    health_check_results.append({"connection_index": connection_index, "error": str(e)})
            
        finally:
            # Clean up all active connections
            for websocket, _, _, _ in active_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 4.0, f"High concurrency test took too little time: {test_duration:.2f}s"
        
        # Analyze connection pool performance
        successful_connections = len([result for result in connection_results.values() if result == "connected"])
        connection_success_rate = successful_connections / num_concurrent_connections
        
        # Should handle majority of connections successfully
        assert connection_success_rate >= 0.6, f"Connection success rate too low: {connection_success_rate:.2f}"
        
        # Analyze stress test results
        valid_stress_results = [r for r in stress_results if isinstance(r, dict) and "messages_sent" in r]
        
        if valid_stress_results:
            total_messages_sent = sum(r["messages_sent"] for r in valid_stress_results)
            total_responses = sum(r["responses_received"] for r in valid_stress_results)
            
            assert total_messages_sent >= len(valid_stress_results), "Should have sent messages from each connection"
            
            # Response rate may be lower under high load, but should have some responses
            response_rate = total_responses / max(total_messages_sent, 1)
            assert response_rate >= 0.3, f"Response rate too low under load: {response_rate:.2f}"
        
        # Analyze health check results
        if health_check_results:
            healthy_connections = len([r for r in health_check_results if r.get("healthy", False)])
            health_rate = healthy_connections / len(health_check_results)
            
            # Most connections should recover and respond to health checks
            assert health_rate >= 0.6, f"Health check recovery rate too low: {health_rate:.2f}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_data_isolation_under_concurrent_load(self, real_services_fixture):
        """Test user data isolation when multiple users access data simultaneously."""
        start_time = time.time()
        
        db_session = self.services["db"]
        if not db_session:
            pytest.skip("Real database session not available")
        
        # Create test users with specific data
        num_users = 6
        user_data_sets = []
        user_connections = []
        
        for i in range(num_users):
            user_id = UserID(f"isolation_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
            thread_id = ThreadID(f"isolation_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
            
            user_data = {
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "user_index": i,
                "sensitive_data": f"private_user_{i}_data_{int(time.time())}",
                "user_preferences": {
                    "theme": f"theme_{i}",
                    "notification_level": f"level_{i}",
                    "private_setting": f"private_{i}_{uuid4().hex[:8]}"
                }
            }
            
            user_data_sets.append(user_data)
        
        try:
            # Phase 1: Establish connections and create user-specific data
            for user_data in user_data_sets:
                user_id = UserID(user_data["user_id"])
                thread_id = ThreadID(user_data["thread_id"])
                
                test_token = self._create_test_auth_token(user_id)
                headers = {"Authorization": f"Bearer {test_token}"}
                
                websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                    f"{self.websocket_url}/agent/{thread_id}",
                    headers=headers,
                    user_id=str(user_id)
                )
                
                user_connections.append((websocket, user_data))
            
            # Phase 2: Concurrent data operations
            async def perform_user_data_operations(websocket, user_data):
                """Perform data operations specific to a user."""
                operations_performed = []
                
                try:
                    # Create user-specific data
                    create_data_request = {
                        "type": "create_user_data",
                        "user_id": user_data["user_id"],
                        "thread_id": user_data["thread_id"],
                        "data_payload": user_data["user_preferences"],
                        "sensitive_marker": user_data["sensitive_data"]
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, create_data_request)
                    operations_performed.append("create_data")
                    
                    # Wait briefly
                    await asyncio.sleep(0.5)
                    
                    # Query user-specific data
                    query_data_request = {
                        "type": "query_user_data",
                        "user_id": user_data["user_id"],
                        "thread_id": user_data["thread_id"],
                        "include_sensitive": True
                    }
                    
                    await WebSocketTestHelpers.send_test_message(websocket, query_data_request)
                    operations_performed.append("query_data")
                    
                    # Collect responses
                    user_responses = []
                    for _ in range(4):  # Collect multiple responses
                        try:
                            response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=3.0)
                            user_responses.append(response)
                        except Exception:
                            break
                    
                    return {
                        "user_index": user_data["user_index"],
                        "operations_performed": operations_performed,
                        "responses_received": len(user_responses),
                        "responses": user_responses
                    }
                    
                except Exception as e:
                    return {
                        "user_index": user_data["user_index"],
                        "error": str(e),
                        "operations_performed": operations_performed
                    }
            
            # Execute concurrent data operations
            operation_tasks = []
            for websocket, user_data in user_connections:
                task = perform_user_data_operations(websocket, user_data)
                operation_tasks.append(task)
            
            operation_results = await asyncio.gather(*operation_tasks, return_exceptions=True)
            
            # Wait for database operations to complete
            await asyncio.sleep(2.0)
            
        finally:
            # Clean up connections
            for websocket, _ in user_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Verify database isolation
        isolation_query = """
        SELECT user_id, data_content, sensitive_data, created_at
        FROM user_isolated_data 
        WHERE user_id = ANY(:user_ids)
        ORDER BY user_id, created_at
        """
        
        user_ids = [user_data["user_id"] for user_data in user_data_sets]
        
        result = await db_session.execute(isolation_query, {"user_ids": user_ids})
        database_records = result.fetchall()
        
        # Verify test characteristics
        test_duration = time.time() - start_time
        assert test_duration > 3.0, f"Data isolation test took too little time: {test_duration:.2f}s"
        
        # Analyze operation results
        valid_results = [r for r in operation_results if isinstance(r, dict) and "user_index" in r]
        
        # Should have results from most users
        assert len(valid_results) >= num_users * 0.7, f"Should have operation results from most users, got {len(valid_results)}"
        
        # Verify no cross-user data leakage in responses
        for result in valid_results:
            user_index = result["user_index"]
            user_responses = result.get("responses", [])
            
            for response in user_responses:
                response_content = json.dumps(response)
                
                # Check that other users' sensitive data doesn't appear
                for other_user_data in user_data_sets:
                    other_index = other_user_data["user_index"]
                    if other_index != user_index:
                        other_sensitive = other_user_data["sensitive_data"]
                        other_private_setting = other_user_data["user_preferences"].get("private_setting", "")
                        
                        assert other_sensitive not in response_content, f"User {user_index} response contains user {other_index} sensitive data"
                        assert other_private_setting not in response_content, f"User {user_index} response contains user {other_index} private setting"
        
        # Verify database isolation
        if database_records:
            user_record_count = {}
            for record in database_records:
                user_id = record.user_id
                user_record_count[user_id] = user_record_count.get(user_id, 0) + 1
                
                # Verify record belongs to correct user
                user_found = False
                for user_data in user_data_sets:
                    if user_data["user_id"] == user_id:
                        user_found = True
                        # Verify sensitive data isolation in database
                        record_content = str(record.data_content) + str(record.sensitive_data)
                        
                        # Should contain own data
                        own_sensitive = user_data["sensitive_data"]
                        
                        # Should NOT contain other users' data
                        for other_user_data in user_data_sets:
                            if other_user_data["user_id"] != user_id:
                                other_sensitive = other_user_data["sensitive_data"]
                                assert other_sensitive not in record_content, f"Database record for {user_id} contains other user's sensitive data"
                        
                        break
                
                assert user_found, f"Database record for unknown user: {user_id}"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_connection_limits_and_throttling(self, real_services_fixture):
        """Test WebSocket connection limits and throttling under rapid connection attempts."""
        start_time = time.time()
        
        if not await ensure_websocket_service_ready(self.backend_url):
            pytest.skip("WebSocket service not ready")
        
        # Test rapid connection attempts to trigger throttling
        rapid_connection_attempts = 15
        connection_results = []
        successful_connections = []
        
        try:
            # Phase 1: Rapid connection attempts (should trigger rate limiting)
            for i in range(rapid_connection_attempts):
                user_id = UserID(f"rapid_user_{i}_{UnifiedIdGenerator.generate_user_id()}")
                thread_id = ThreadID(f"rapid_thread_{i}_{UnifiedIdGenerator.generate_thread_id()}")
                
                test_token = self._create_test_auth_token(user_id)
                headers = {"Authorization": f"Bearer {test_token}"}
                
                connection_start = time.time()
                
                try:
                    websocket = await WebSocketTestHelpers.create_test_websocket_connection(
                        f"{self.websocket_url}/agent/{thread_id}",
                        headers=headers,
                        user_id=str(user_id),
                        timeout=3.0,  # Shorter timeout for rapid attempts
                        max_retries=1
                    )
                    
                    connection_duration = time.time() - connection_start
                    successful_connections.append((websocket, user_id, thread_id))
                    
                    connection_results.append({
                        "attempt": i,
                        "status": "success",
                        "duration": connection_duration,
                        "user_id": str(user_id)
                    })
                    
                except Exception as e:
                    connection_duration = time.time() - connection_start
                    connection_results.append({
                        "attempt": i,
                        "status": "failed",
                        "duration": connection_duration,
                        "error": str(e)[:100],  # Truncate long errors
                        "user_id": str(user_id)
                    })
                
                # Very brief pause between rapid attempts
                await asyncio.sleep(0.05)
            
            # Phase 2: Test established connections under load
            if successful_connections:
                # Send messages through established connections
                message_results = []
                
                async def test_established_connection(websocket, user_id, thread_id):
                    """Test an established connection."""
                    try:
                        test_message = {
                            "type": "connection_load_test",
                            "user_id": str(user_id),
                            "thread_id": str(thread_id),
                            "test_data": "load_testing_established_connection"
                        }
                        
                        message_start = time.time()
                        await WebSocketTestHelpers.send_test_message(websocket, test_message)
                        
                        response = await WebSocketTestHelpers.receive_test_message(websocket, timeout=4.0)
                        message_duration = time.time() - message_start
                        
                        return {
                            "user_id": str(user_id),
                            "status": "success",
                            "duration": message_duration
                        }
                        
                    except Exception as e:
                        return {
                            "user_id": str(user_id),
                            "status": "failed",
                            "error": str(e)[:100]
                        }
                
                # Test subset of established connections
                test_connections = successful_connections[:8]  # Limit to avoid overwhelming
                connection_test_tasks = []
                
                for websocket, user_id, thread_id in test_connections:
                    task = test_established_connection(websocket, user_id, thread_id)
                    connection_test_tasks.append(task)
                
                message_results = await asyncio.gather(*connection_test_tasks, return_exceptions=True)
            
        finally:
            # Clean up all successful connections
            for websocket, _, _ in successful_connections:
                await WebSocketTestHelpers.close_test_connection(websocket)
        
        # Analyze connection limiting and throttling
        test_duration = time.time() - start_time
        assert test_duration > 2.0, f"Connection limiting test took too little time: {test_duration:.2f}s"
        
        # Analyze connection attempt results
        successful_attempts = len([r for r in connection_results if r["status"] == "success"])
        failed_attempts = len([r for r in connection_results if r["status"] == "failed"])
        
        # Should have some successful connections
        assert successful_attempts >= 3, f"Should have some successful connections, got {successful_attempts}"
        
        # Under rapid attempts, expect some failures (rate limiting)
        total_attempts = successful_attempts + failed_attempts
        failure_rate = failed_attempts / total_attempts if total_attempts > 0 else 0
        
        # Either should handle all connections (robust system) or show throttling (protective system)
        # Both are acceptable behaviors
        assert failure_rate <= 0.8, f"Failure rate too high, may indicate system issues: {failure_rate:.2f}"
        
        # Analyze connection durations for throttling indicators
        successful_results = [r for r in connection_results if r["status"] == "success"]
        if len(successful_results) >= 3:
            connection_durations = [r["duration"] for r in successful_results]
            
            # Later connections might take longer (throttling)
            early_durations = connection_durations[:3]
            late_durations = connection_durations[-3:]
            
            avg_early = sum(early_durations) / len(early_durations)
            avg_late = sum(late_durations) / len(late_durations)
            
            # Throttling might cause later connections to take longer
            # This is acceptable and expected behavior
            if avg_late > avg_early * 2:
                # Evidence of throttling - this is good system behavior
                assert avg_late < 10.0, "Even throttled connections should complete within reasonable time"
        
        # Analyze established connection performance
        if successful_connections and 'message_results' in locals():
            valid_message_results = [r for r in message_results if isinstance(r, dict) and "status" in r]
            
            if valid_message_results:
                successful_messages = len([r for r in valid_message_results if r["status"] == "success"])
                message_success_rate = successful_messages / len(valid_message_results)
                
                # Established connections should perform well
                assert message_success_rate >= 0.7, f"Established connection performance too low: {message_success_rate:.2f}"

    def _create_test_auth_token(self, user_id: UserID) -> str:
        """Create test authentication token for integration testing."""
        import base64
        
        payload = {
            "user_id": str(user_id),
            "email": f"test_{user_id}@example.com",
            "iat": int(time.time()),
            "exp": int(time.time() + 3600),
            "test_mode": True
        }
        
        token_data = base64.b64encode(json.dumps(payload).encode()).decode()
        return f"test.{token_data}.signature"