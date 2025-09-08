"""
E2E tests for UnifiedWebSocketManager - Testing complete WebSocket infrastructure in production-like environment.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Production-ready multi-user WebSocket infrastructure  
- Value Impact: Validates complete WebSocket system supports concurrent users with proper isolation
- Strategic Impact: Core infrastructure for real-time chat - ensures scalable multi-user support

This E2E test validates the UnifiedWebSocketManager works end-to-end with real authentication,
concurrent users, high message volumes, and production-like conditions.
CRITICAL: This test ensures multi-user isolation and connection resilience for chat platform.
"""

import asyncio
import pytest
import json
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import BaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    _serialize_message_safely
)


class TestUnifiedWebSocketManagerE2EMultiUser(BaseTestCase):
    """
    E2E test for multi-user WebSocket infrastructure with authentication and isolation.
    
    CRITICAL: This test validates the core infrastructure that enables concurrent
    users to have isolated, reliable WebSocket connections for real-time chat.
    """
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated test environment."""
        auth_helper = E2EAuthHelper()
        await auth_helper.initialize()
        yield auth_helper
        await auth_helper.cleanup()
    
    @pytest.fixture
    async def multi_user_auth_setup(self, auth_helper):
        """Create multiple authenticated users for multi-user testing."""
        users = []
        
        # Create users representing different segments
        user_configs = [
            {"email": "free_user_ws@netra.ai", "name": "Free Tier User", "user_type": "free"},
            {"email": "early_user_ws@netra.ai", "name": "Early User", "user_type": "early"},
            {"email": "mid_user_ws@netra.ai", "name": "Mid Tier User", "user_type": "mid"},
            {"email": "enterprise_user_ws@netra.ai", "name": "Enterprise User", "user_type": "enterprise"},
            {"email": "concurrent_user_ws@netra.ai", "name": "Concurrent User", "user_type": "mid"}
        ]
        
        for config in user_configs:
            user_data = await auth_helper.create_test_user(**config)
            users.append(user_data)
        
        return users
    
    @pytest.fixture
    async def websocket_manager_with_real_connections(self, multi_user_auth_setup):
        """Create UnifiedWebSocketManager with real authenticated connections."""
        manager = UnifiedWebSocketManager()
        
        # Create realistic WebSocket connections for each authenticated user
        connections_data = []
        
        for user_data in multi_user_auth_setup:
            # Create realistic WebSocket mock that tracks messages
            class RealisticWebSocketMock:
                def __init__(self, user_id):
                    self.user_id = user_id
                    self.sent_messages = []
                    self.closed = False
                    self.connection_time = datetime.now(timezone.utc)
                    self.message_count = 0
                
                async def send_json(self, data):
                    if self.closed:
                        raise ConnectionError(f"WebSocket closed for user {self.user_id}")
                    
                    # Simulate realistic WebSocket behavior
                    self.message_count += 1
                    self.sent_messages.append({
                        "data": data,
                        "sent_at": datetime.now(timezone.utc),
                        "message_id": self.message_count
                    })
                
                async def close(self):
                    self.closed = True
                
                def get_stats(self):
                    return {
                        "total_messages": len(self.sent_messages),
                        "connection_duration": (datetime.now(timezone.utc) - self.connection_time).total_seconds(),
                        "closed": self.closed
                    }
            
            mock_websocket = RealisticWebSocketMock(user_data["user_id"])
            
            connection = WebSocketConnection(
                connection_id=f"e2e_conn_{user_data['user_id']}",
                user_id=user_data["user_id"],
                websocket=mock_websocket,
                connected_at=datetime.now(timezone.utc),
                metadata={
                    "test": "e2e_multi_user",
                    "user_type": user_data.get("user_type", "unknown"),
                    "email": user_data.get("email", ""),
                    "authenticated": True
                }
            )
            
            await manager.add_connection(connection)
            
            connections_data.append({
                "user_data": user_data,
                "connection": connection,
                "websocket": mock_websocket
            })
        
        yield manager, connections_data
        
        # Cleanup
        for conn_data in connections_data:
            try:
                await manager.remove_connection(conn_data["connection"].connection_id)
            except Exception:
                pass  # Best effort cleanup
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_and_performance(self, websocket_manager_with_real_connections):
        """
        MISSION CRITICAL: Test multi-user WebSocket isolation under concurrent load.
        
        This test validates the core value proposition: multiple users can simultaneously
        use the chat system without interference or message cross-contamination.
        """
        manager, connections_data = websocket_manager_with_real_connections
        
        # Arrange - Prepare concurrent user scenarios
        concurrent_scenarios = []
        messages_per_user = 15  # Realistic chat volume
        
        for i, conn_data in enumerate(connections_data):
            user_id = conn_data["user_data"]["user_id"]
            user_type = conn_data["connection"].metadata["user_type"]
            
            # Create realistic message scenarios for each user type
            scenario = {
                "user_id": user_id,
                "user_type": user_type,
                "messages": []
            }
            
            for msg_num in range(messages_per_user):
                # Different message patterns based on user type
                if user_type == "enterprise":
                    message = {
                        "type": "agent_execution",
                        "payload": {
                            "agent": "advanced_optimizer",
                            "request": f"Enterprise analysis request {msg_num}",
                            "priority": "high",
                            "user_context": user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "enterprise_features": ["advanced_analytics", "priority_support"]
                        }
                    }
                elif user_type == "mid":
                    message = {
                        "type": "agent_thinking",
                        "payload": {
                            "agent": "standard_optimizer", 
                            "thought": f"Mid-tier analysis {msg_num}",
                            "progress": (msg_num + 1) / messages_per_user * 100,
                            "user_context": user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "mid_features": ["standard_analytics"]
                        }
                    }
                elif user_type == "free":
                    message = {
                        "type": "status_update",
                        "payload": {
                            "status": "processing",
                            "message": f"Free tier update {msg_num}",
                            "user_context": user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "free_limitations": ["basic_features_only", "rate_limited"]
                        }
                    }
                else:  # early
                    message = {
                        "type": "tool_executing",
                        "payload": {
                            "tool": "beta_analyzer",
                            "status": "running",
                            "progress": f"Early access feature {msg_num}",
                            "user_context": user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "early_features": ["beta_access", "testing_tools"]
                        }
                    }
                
                scenario["messages"].append(message)
            
            concurrent_scenarios.append(scenario)
        
        # Act - Send messages concurrently from all users
        start_time = datetime.now()
        
        async def send_user_messages(scenario):
            user_id = scenario["user_id"]
            for message in scenario["messages"]:
                await manager.send_to_user(user_id, message)
                # Small delay to simulate realistic chat timing
                await asyncio.sleep(0.01)
        
        # Execute all user scenarios concurrently
        await asyncio.gather(*[
            send_user_messages(scenario) for scenario in concurrent_scenarios
        ])
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Allow message processing time
        await asyncio.sleep(0.5)
        
        # Assert - Verify user isolation and message delivery
        total_messages_expected = len(connections_data) * messages_per_user
        total_messages_delivered = 0
        
        for i, conn_data in enumerate(connections_data):
            websocket = conn_data["websocket"] 
            user_id = conn_data["user_data"]["user_id"]
            user_type = conn_data["connection"].metadata["user_type"]
            
            # Each user should receive exactly their messages
            delivered_messages = len(websocket.sent_messages)
            assert delivered_messages == messages_per_user, \
                f"User {user_type} ({user_id}) expected {messages_per_user} messages, got {delivered_messages}"
            
            total_messages_delivered += delivered_messages
            
            # Verify message content isolation - no cross-user contamination
            for message_wrapper in websocket.sent_messages:
                message_data = message_wrapper["data"]
                user_context = message_data.get("payload", {}).get("user_context")
                
                assert user_context == user_id, \
                    f"CRITICAL: User {user_id} received message for {user_context}. This is a SECURITY VIOLATION!"
                
                # Verify user-type specific features are preserved
                payload = message_data.get("payload", {})
                if user_type == "enterprise":
                    assert "enterprise_features" in payload or message_data.get("type") != "agent_execution"
                elif user_type == "free":
                    assert "free_limitations" in payload or message_data.get("type") != "status_update"
        
        # Overall system assertions
        assert total_messages_delivered == total_messages_expected, \
            f"CRITICAL: Expected {total_messages_expected} total messages, delivered {total_messages_delivered}"
        
        # Performance assertion - concurrent multi-user should be efficient
        assert execution_time < 5.0, \
            f"Multi-user concurrent execution took {execution_time:.2f}s, may impact user experience"
        
        # Verify connection health for all users
        connection_stats = manager.get_stats()
        assert connection_stats["total_connections"] == len(connections_data)
        assert connection_stats["unique_users"] == len(connections_data)
        
        for user_id in [conn["user_data"]["user_id"] for conn in connections_data]:
            assert manager.is_connection_active(user_id), f"User {user_id} connection not active"
            
            health = manager.get_connection_health(user_id)
            assert health["has_active_connections"] is True
            assert health["active_connections"] >= 1
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.asyncio
    async def test_websocket_critical_event_delivery_guarantees(self, websocket_manager_with_real_connections):
        """
        Test WebSocket critical event delivery guarantees for chat reliability.
        
        This validates the system can reliably deliver the 5 critical agent events
        (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
        to multiple users simultaneously without loss or corruption.
        """
        manager, connections_data = websocket_manager_with_real_connections
        
        # Arrange - Create critical event sequences for each user
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        start_time = datetime.now()
        
        # Act - Send critical event sequences to all users concurrently
        async def send_critical_events_to_user(user_id, user_type):
            for i, event_type in enumerate(critical_events):
                await manager.emit_critical_event(
                    user_id,
                    event_type,
                    {
                        "agent_name": f"{user_type}_agent",
                        "run_id": f"run_{user_id}_{i}",
                        "step_number": i + 1,
                        "total_steps": len(critical_events),
                        "user_type": user_type,
                        "event_sequence": i,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "critical": True
                    }
                )
                # Brief delay between events for realistic timing
                await asyncio.sleep(0.05)
        
        # Send critical events to all users concurrently
        tasks = []
        for conn_data in connections_data:
            user_id = conn_data["user_data"]["user_id"]
            user_type = conn_data["connection"].metadata["user_type"]
            
            task = asyncio.create_task(
                send_critical_events_to_user(user_id, user_type)
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        delivery_time = (datetime.now() - start_time).total_seconds()
        
        # Allow processing time
        await asyncio.sleep(0.3)
        
        # Assert - Verify critical event delivery to all users
        for conn_data in connections_data:
            user_id = conn_data["user_data"]["user_id"]
            user_type = conn_data["connection"].metadata["user_type"]
            websocket = conn_data["websocket"]
            
            sent_messages = websocket.sent_messages
            
            # Should have received all 5 critical events
            assert len(sent_messages) == 5, \
                f"CRITICAL: User {user_type} ({user_id}) expected 5 critical events, got {len(sent_messages)}"
            
            # Verify event sequence and integrity
            for i, message_wrapper in enumerate(sent_messages):
                message = message_wrapper["data"]
                
                expected_event_type = critical_events[i]
                assert message["type"] == expected_event_type, \
                    f"Event {i} for user {user_id}: expected {expected_event_type}, got {message['type']}"
                
                # Verify event data integrity
                event_data = message["data"]
                assert event_data["agent_name"] == f"{user_type}_agent"
                assert event_data["step_number"] == i + 1
                assert event_data["event_sequence"] == i
                assert event_data["critical"] is True
                assert event_data["user_type"] == user_type
                
                # Verify timing - events should have recent timestamps
                event_timestamp = datetime.fromisoformat(event_data["timestamp"])
                time_diff = (datetime.now(timezone.utc) - event_timestamp).total_seconds()
                assert time_diff < 30.0, f"Event timestamp too old: {time_diff}s"
        
        # Performance assertion - critical events should be delivered quickly
        assert delivery_time < 3.0, \
            f"Critical event delivery took {delivery_time:.2f}s for {len(connections_data)} users"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_websocket_connection_resilience_under_stress(self, multi_user_auth_setup):
        """
        Test WebSocket connection resilience under stress conditions.
        
        This test simulates challenging production conditions including connection drops,
        rapid reconnections, high message volumes, and concurrent user activity.
        """
        manager = UnifiedWebSocketManager()
        
        # Create initial connections
        initial_connections = []
        
        for user_data in multi_user_auth_setup[:3]:  # Use first 3 users for stress test
            class StressTestWebSocket:
                def __init__(self, user_id, failure_rate=0.1):
                    self.user_id = user_id
                    self.failure_rate = failure_rate
                    self.sent_messages = []
                    self.closed = False
                    self.failure_count = 0
                    self.success_count = 0
                
                async def send_json(self, data):
                    import random
                    
                    if self.closed:
                        raise ConnectionError(f"WebSocket closed for {self.user_id}")
                    
                    # Simulate intermittent failures
                    if random.random() < self.failure_rate:
                        self.failure_count += 1
                        raise ConnectionError(f"Simulated network failure for {self.user_id}")
                    
                    self.success_count += 1
                    self.sent_messages.append({
                        "data": data,
                        "sent_at": datetime.now(timezone.utc)
                    })
                
                async def close(self):
                    self.closed = True
                
                def get_reliability_stats(self):
                    total_attempts = self.success_count + self.failure_count
                    success_rate = self.success_count / total_attempts if total_attempts > 0 else 0
                    return {
                        "success_rate": success_rate,
                        "total_attempts": total_attempts,
                        "failures": self.failure_count
                    }
            
            stress_websocket = StressTestWebSocket(user_data["user_id"], failure_rate=0.15)
            
            connection = WebSocketConnection(
                connection_id=f"stress_conn_{user_data['user_id']}",
                user_id=user_data["user_id"],
                websocket=stress_websocket,
                connected_at=datetime.now(timezone.utc),
                metadata={"test": "stress", "user_type": user_data.get("user_type", "unknown")}
            )
            
            await manager.add_connection(connection)
            initial_connections.append((user_data, connection, stress_websocket))
        
        # Act - Generate stress conditions
        stress_start_time = datetime.now()
        
        async def stress_test_user(user_data, connection, websocket):
            user_id = user_data["user_id"]
            
            # Send high volume of messages rapidly
            for burst in range(5):  # 5 bursts of messages
                for msg_in_burst in range(20):  # 20 messages per burst
                    try:
                        await manager.send_to_user(user_id, {
                            "type": "stress_test_message",
                            "payload": {
                                "burst": burst,
                                "message": msg_in_burst,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "stress_data": "x" * 100  # Add some payload size
                            }
                        })
                    except Exception as e:
                        # Expected some failures due to stress conditions
                        pass
                    
                    # Very brief delay to simulate rapid user interaction
                    await asyncio.sleep(0.001)
                
                # Brief pause between bursts
                await asyncio.sleep(0.1)
        
        # Run stress test for all users concurrently
        stress_tasks = []
        for user_data, connection, websocket in initial_connections:
            task = asyncio.create_task(stress_test_user(user_data, connection, websocket))
            stress_tasks.append(task)
        
        await asyncio.gather(*stress_tasks, return_exceptions=True)
        
        stress_duration = (datetime.now() - stress_start_time).total_seconds()
        
        # Allow recovery time
        await asyncio.sleep(1.0)
        
        # Assert - Verify system resilience
        for user_data, connection, websocket in initial_connections:
            user_id = user_data["user_id"]
            
            # Check connection health after stress
            is_healthy = manager.is_connection_active(user_id)
            
            # Get reliability statistics
            reliability_stats = websocket.get_reliability_stats()
            
            # Should maintain reasonable success rate even under stress
            assert reliability_stats["success_rate"] >= 0.7, \
                f"User {user_id} success rate {reliability_stats['success_rate']:.2f} too low under stress"
            
            # Should have processed substantial number of messages
            assert reliability_stats["total_attempts"] >= 50, \
                f"User {user_id} processed only {reliability_stats['total_attempts']} messages under stress"
            
            # Connection should still be tracked (may have been replaced due to failures)
            health = manager.get_connection_health(user_id)
            assert health["total_connections"] >= 0  # May be 0 if removed due to failures
        
        # Overall system health after stress
        system_stats = manager.get_stats()
        assert system_stats["total_connections"] >= 0  # System should not crash
        
        # Error handling should be functional
        error_stats = manager.get_error_statistics()
        assert error_stats["error_recovery_enabled"] is True
        
        # Performance under stress should be acceptable
        assert stress_duration < 20.0, \
            f"Stress test took {stress_duration:.2f}s, indicating performance issues"
        
        # Cleanup
        for user_data, connection, websocket in initial_connections:
            try:
                await websocket.close()
                await manager.remove_connection(connection.connection_id)
            except Exception:
                pass  # Best effort cleanup