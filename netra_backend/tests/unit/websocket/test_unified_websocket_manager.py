"""
Comprehensive Unit Test Suite for UnifiedWebSocketManager - 100% Coverage Target

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure WebSocket Chat Infrastructure ($75K+ MRR protection)
- Value Impact: WebSocket events enable substantive chat interactions - the core business value
- Strategic Impact: MISSION CRITICAL - Without reliable WebSocket events, users abandon platform

This test suite ensures 100% coverage of UnifiedWebSocketManager, the SSOT for WebSocket
connection management that enables the 5 critical agent events:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results delivery
5. agent_completed - Final response notification

CRITICAL COVERAGE AREAS (per CLAUDE.md requirements):
- Connection lifecycle (add/remove with thread safety)
- Message sending with serialization safety (_serialize_message_safely)
- User-specific locks for race condition prevention
- Error recovery and queued message handling
- Background task monitoring and health checks
- Connection health diagnostics and validation
- Multi-user isolation and security
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

# Import test framework following CLAUDE.md guidance
import unittest
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import system under test 
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
    RegistryCompat,
    _serialize_message_safely
)

# Test models and enums for serialization testing
class TestWebSocketState(Enum):
    """Test enum for WebSocketState serialization testing."""
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3


class TestPydanticModel:
    """Test Pydantic-like model for serialization testing."""
    
    def __init__(self, field1: str, timestamp: datetime):
        self.field1 = field1
        self.timestamp = timestamp
    
    def model_dump(self, mode: str = None):
        """Mock Pydantic model_dump method."""
        return {
            "field1": self.field1,
            "timestamp": self.timestamp.isoformat() if mode == 'json' else str(self.timestamp)
        }


@pytest.fixture
async def websocket_manager():
    """Create UnifiedWebSocketManager instance for testing."""
    manager = UnifiedWebSocketManager()
    yield manager
    # Cleanup
    await manager.shutdown_background_monitoring()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    websocket = Mock()
    websocket.send_json = AsyncMock()
    websocket.client_state = TestWebSocketState.OPEN
    return websocket


@pytest.fixture
def sample_connection(mock_websocket):
    """Create sample WebSocket connection for testing."""
    return WebSocketConnection(
        connection_id="conn_12345",
        user_id="user_67890",
        websocket=mock_websocket,
        connected_at=datetime.now(),
        metadata={"test": "metadata"}
    )


class TestUnifiedWebSocketManagerUnit(SSotAsyncTestCase, unittest.TestCase):
    """Comprehensive unit tests for UnifiedWebSocketManager."""
    
    def setup_method(self, method):
        """Setup method for each test."""
        super().setup_method(method)
        # Use IsolatedEnvironment per CLAUDE.md requirements  
        self.env = get_env()
        self.env.set("ENVIRONMENT", "test", source="websocket_unit_test")
        self.env.set("WEBSOCKET_TIMEOUT", "5", source="websocket_unit_test")
        # Initialize manager for each test
        self.manager = UnifiedWebSocketManager()
    
    def teardown_method(self, method):
        """Cleanup method for each test."""
        # Use pytest-asyncio to handle async cleanup
        if hasattr(self, 'manager'):
            import asyncio
            try:
                # Try to run cleanup in existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule cleanup as a task
                    asyncio.create_task(self.manager.shutdown_background_monitoring())
                else:
                    # Run cleanup synchronously
                    loop.run_until_complete(self.manager.shutdown_background_monitoring())
            except RuntimeError:
                # Create new loop if needed
                asyncio.run(self.manager.shutdown_background_monitoring())
        super().teardown_method(method)
    
    # ============================================================================
    # CONNECTION MANAGEMENT TESTS - Core functionality
    # ============================================================================
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_add_connection_basic(self):
        """Test basic connection addition."""
        # Create test connection
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection(
            connection_id="test_conn",
            user_id="test_user",
            websocket=websocket,
            connected_at=datetime.now()
        )
        
        # Add connection
        await self.manager.add_connection(connection)
        
        # Verify connection was added
        retrieved = self.manager.get_connection("test_conn")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.connection_id, "test_conn")
        self.assertEqual(retrieved.user_id, "test_user")
        
        # Verify user connections
        user_connections = self.manager.get_user_connections("test_user")
        self.assertEqual(len(user_connections), 1)
        self.assertIn("test_conn", user_connections)
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_add_connection_with_metadata(self):
        """Test connection addition with metadata."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection(
            connection_id="meta_conn",
            user_id="meta_user", 
            websocket=websocket,
            connected_at=datetime.now(),
            metadata={"client_type": "web", "version": "1.0"}
        )
        
        await self.manager.add_connection(connection)
        
        retrieved = self.manager.get_connection("meta_conn")
        self.assertEqual(retrieved.metadata["client_type"], "web")
        self.assertEqual(retrieved.metadata["version"], "1.0")
    
    @pytest.mark.asyncio
    async def test_add_multiple_connections_same_user(self):
        """Test adding multiple connections for the same user."""
        websocket1 = Mock()
        websocket1.send_json = AsyncMock()
        websocket2 = Mock() 
        websocket2.send_json = AsyncMock()
        
        connection1 = WebSocketConnection("conn1", "user1", websocket1, datetime.now())
        connection2 = WebSocketConnection("conn2", "user1", websocket2, datetime.now())
        
        await self.manager.add_connection(connection1)
        await self.manager.add_connection(connection2)
        
        user_connections = self.manager.get_user_connections("user1")
        self.assertEqual(len(user_connections), 2)
        self.assertIn("conn1", user_connections)
        self.assertIn("conn2", user_connections)
    
    @pytest.mark.asyncio
    async def test_remove_connection_basic(self):
        """Test basic connection removal."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("remove_conn", "remove_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        self.assertIsNotNone(self.manager.get_connection("remove_conn"))
        
        await self.manager.remove_connection("remove_conn")
        self.assertIsNone(self.manager.get_connection("remove_conn"))
        
        user_connections = self.manager.get_user_connections("remove_user")
        self.assertEqual(len(user_connections), 0)
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_connection(self):
        """Test removing a connection that doesn't exist."""
        # Should not raise an exception
        await self.manager.remove_connection("nonexistent_conn")
    
    @pytest.mark.asyncio
    async def test_remove_one_of_multiple_connections(self):
        """Test removing one connection when user has multiple."""
        websocket1 = Mock()
        websocket1.send_json = AsyncMock()
        websocket2 = Mock()
        websocket2.send_json = AsyncMock()
        
        connection1 = WebSocketConnection("multi1", "multi_user", websocket1, datetime.now())
        connection2 = WebSocketConnection("multi2", "multi_user", websocket2, datetime.now())
        
        await self.manager.add_connection(connection1)
        await self.manager.add_connection(connection2)
        
        # Remove one connection
        await self.manager.remove_connection("multi1")
        
        # Verify only one removed
        self.assertIsNone(self.manager.get_connection("multi1"))
        self.assertIsNotNone(self.manager.get_connection("multi2"))
        
        user_connections = self.manager.get_user_connections("multi_user")
        self.assertEqual(len(user_connections), 1)
        self.assertIn("multi2", user_connections)
    
    # ============================================================================
    # THREAD SAFETY AND CONCURRENCY TESTS 
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_user_specific_locks_creation(self):
        """Test user-specific lock creation for thread safety."""
        # Get locks for different users
        lock1 = await self.manager._get_user_connection_lock("user1")
        lock2 = await self.manager._get_user_connection_lock("user2")
        lock1_again = await self.manager._get_user_connection_lock("user1")
        
        # Verify different users get different locks
        self.assertIsNot(lock1, lock2)
        
        # Verify same user gets same lock
        self.assertIs(lock1, lock1_again)
    
    @pytest.mark.asyncio
    async def test_concurrent_connection_management(self):
        """Test concurrent connection operations are thread-safe."""
        websockets = [Mock() for _ in range(10)]
        for ws in websockets:
            ws.send_json = AsyncMock()
        
        connections = [
            WebSocketConnection(f"concurrent_{i}", "concurrent_user", websockets[i], datetime.now())
            for i in range(10)
        ]
        
        # Add connections concurrently
        tasks = [self.manager.add_connection(conn) for conn in connections]
        await asyncio.gather(*tasks)
        
        # Verify all connections were added
        user_connections = self.manager.get_user_connections("concurrent_user")
        self.assertEqual(len(user_connections), 10)
        
        # Remove connections concurrently
        remove_tasks = [self.manager.remove_connection(f"concurrent_{i}") for i in range(10)]
        await asyncio.gather(*remove_tasks)
        
        # Verify all connections were removed
        user_connections = self.manager.get_user_connections("concurrent_user")
        self.assertEqual(len(user_connections), 0)
    
    # ============================================================================
    # MESSAGE SENDING TESTS - Critical for WebSocket events
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_send_to_user_basic(self):
        """Test basic message sending to user."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("msg_conn", "msg_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        test_message = {"type": "test_message", "data": "hello"}
        await self.manager.send_to_user("msg_user", test_message)
        
        websocket.send_json.assert_called_once()
        sent_message = websocket.send_json.call_args[0][0]
        self.assertEqual(sent_message["type"], "test_message")
        self.assertEqual(sent_message["data"], "hello")
    
    @pytest.mark.asyncio
    async def test_send_to_user_no_connections(self):
        """Test sending message when user has no connections."""
        test_message = {"type": "startup_test", "data": "test"}
        
        # This should not raise an exception, but should log and store for recovery
        await self.manager.send_to_user("nonexistent_user", test_message)
        
        # Verify message was stored for recovery
        self.assertIn("nonexistent_user", self.manager._message_recovery_queue)
    
    @pytest.mark.asyncio
    async def test_send_to_user_websocket_failure(self):
        """Test handling WebSocket send failure."""
        websocket = Mock()
        websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))
        connection = WebSocketConnection("fail_conn", "fail_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        test_message = {"type": "agent_started", "data": "test"}
        await self.manager.send_to_user("fail_user", test_message)
        
        # Verify message was stored for recovery
        self.assertIn("fail_user", self.manager._message_recovery_queue)
    
    @pytest.mark.asyncio
    async def test_send_to_user_multiple_connections(self):
        """Test sending message to user with multiple connections."""
        websocket1 = Mock()
        websocket1.send_json = AsyncMock()
        websocket2 = Mock()
        websocket2.send_json = AsyncMock()
        
        connection1 = WebSocketConnection("multi_conn1", "multi_user", websocket1, datetime.now())
        connection2 = WebSocketConnection("multi_conn2", "multi_user", websocket2, datetime.now())
        
        await self.manager.add_connection(connection1)
        await self.manager.add_connection(connection2)
        
        test_message = {"type": "broadcast_test", "data": "hello all"}
        await self.manager.send_to_user("multi_user", test_message)
        
        # Verify message sent to both connections
        websocket1.send_json.assert_called_once()
        websocket2.send_json.assert_called_once()
        
        # Verify message content
        for ws in [websocket1, websocket2]:
            sent_message = ws.send_json.call_args[0][0]
            self.assertEqual(sent_message["type"], "broadcast_test")
            self.assertEqual(sent_message["data"], "hello all")
    
    @pytest.mark.asyncio
    async def test_send_to_thread_compatibility(self):
        """Test send_to_thread compatibility method."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("thread_conn", "thread_123", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        test_message = {"type": "thread_message", "data": "thread test"}
        result = await self.manager.send_to_thread("thread_123", test_message)
        
        self.assertTrue(result)
        websocket.send_json.assert_called_once()
    
    # ============================================================================
    # CRITICAL EVENT EMISSION TESTS - Mission critical for chat value
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_emit_critical_event_basic(self):
        """Test basic critical event emission."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("event_conn", "event_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        await self.manager.emit_critical_event(
            "event_user",
            "agent_started", 
            {"agent_name": "TestAgent", "run_id": "run_123"}
        )
        
        websocket.send_json.assert_called_once()
        sent_message = websocket.send_json.call_args[0][0]
        self.assertEqual(sent_message["type"], "agent_started")
        self.assertIn("timestamp", sent_message)
        self.assertTrue(sent_message["critical"])
    
    @pytest.mark.asyncio
    async def test_emit_critical_event_validation(self):
        """Test critical event parameter validation."""
        # Empty user_id should raise ValueError
        with self.assertRaises(ValueError):
            await self.manager.emit_critical_event("", "agent_started", {})
        
        # Empty event_type should raise ValueError  
        with self.assertRaises(ValueError):
            await self.manager.emit_critical_event("test_user", "", {})
    
    @patch('shared.isolated_environment.get_env')
    @pytest.mark.asyncio
    async def test_emit_critical_event_staging_retry(self, mock_get_env):
        """Test critical event retry logic in staging environment."""
        # Mock staging environment
        mock_env = Mock()
        mock_env.get.return_value = "staging"
        mock_get_env.return_value = mock_env
        
        # No connections initially - should trigger retry logic
        await self.manager.emit_critical_event(
            "staging_user",
            "agent_started",
            {"test": "data"}
        )
        
        # Verify message was stored for recovery
        self.assertIn("staging_user", self.manager._message_recovery_queue)
    
    # ============================================================================
    # CONNECTION HEALTH AND DIAGNOSTICS TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_is_connection_active_true(self):
        """Test is_connection_active returns True for active connection."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("active_conn", "active_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        self.assertTrue(self.manager.is_connection_active("active_user"))
    
    @pytest.mark.asyncio
    async def test_is_connection_active_false(self):
        """Test is_connection_active returns False for no connections."""
        self.assertFalse(self.manager.is_connection_active("nonexistent_user"))
    
    @pytest.mark.asyncio
    async def test_is_connection_active_invalid_websocket(self):
        """Test is_connection_active with invalid WebSocket."""
        connection = WebSocketConnection("invalid_conn", "invalid_user", None, datetime.now())
        await self.manager.add_connection(connection)
        
        self.assertFalse(self.manager.is_connection_active("invalid_user"))
    
    @pytest.mark.asyncio
    async def test_get_connection_health(self):
        """Test detailed connection health information."""
        websocket1 = Mock()
        websocket1.send_json = AsyncMock()
        websocket2 = None  # Invalid websocket
        
        connection1 = WebSocketConnection("health1", "health_user", websocket1, datetime.now())
        connection2 = WebSocketConnection("health2", "health_user", websocket2, datetime.now())
        
        await self.manager.add_connection(connection1)
        await self.manager.add_connection(connection2)
        
        health = self.manager.get_connection_health("health_user")
        
        self.assertEqual(health["user_id"], "health_user")
        self.assertEqual(health["total_connections"], 2)
        self.assertEqual(health["active_connections"], 1)
        self.assertTrue(health["has_active_connections"])
        self.assertEqual(len(health["connections"]), 2)
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test connection statistics."""
        # Add test connections
        websocket1 = Mock()
        websocket1.send_json = AsyncMock()
        websocket2 = Mock()
        websocket2.send_json = AsyncMock()
        
        connection1 = WebSocketConnection("stats1", "stats_user1", websocket1, datetime.now())
        connection2 = WebSocketConnection("stats2", "stats_user2", websocket2, datetime.now())
        
        await self.manager.add_connection(connection1)
        await self.manager.add_connection(connection2)
        
        stats = self.manager.get_stats()
        
        self.assertEqual(stats["total_connections"], 2)
        self.assertEqual(stats["unique_users"], 2)
        self.assertEqual(stats["connections_by_user"]["stats_user1"], 1)
        self.assertEqual(stats["connections_by_user"]["stats_user2"], 1)
    
    # ============================================================================
    # WAIT FOR CONNECTION TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_wait_for_connection_success(self):
        """Test wait_for_connection succeeds when connection is established."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("wait_conn", "wait_user", websocket, datetime.now())
        
        # Start wait task
        wait_task = asyncio.create_task(
            self.manager.wait_for_connection("wait_user", timeout=2.0, check_interval=0.1)
        )
        
        # Add connection after small delay
        await asyncio.sleep(0.2)
        await self.manager.add_connection(connection)
        
        # Wait should succeed
        result = await wait_task
        self.assertTrue(result)
    
    @pytest.mark.asyncio
    async def test_wait_for_connection_timeout(self):
        """Test wait_for_connection times out when no connection."""
        result = await self.manager.wait_for_connection("timeout_user", timeout=0.2)
        self.assertFalse(result)
    
    @pytest.mark.asyncio
    async def test_wait_for_connection_immediate(self):
        """Test wait_for_connection succeeds immediately if connection exists."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("immediate_conn", "immediate_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        result = await self.manager.wait_for_connection("immediate_user", timeout=1.0)
        self.assertTrue(result)
    
    # ============================================================================
    # LEGACY COMPATIBILITY TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_connect_user_compatibility(self):
        """Test legacy connect_user method."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        
        conn_info = await self.manager.connect_user("compat_user", websocket)
        
        self.assertEqual(conn_info.user_id, "compat_user")
        self.assertIsNotNone(conn_info.connection_id)
        self.assertEqual(conn_info.websocket, websocket)
        
        # Verify connection was added to registry
        self.assertIn(conn_info.connection_id, self.manager.connection_registry)
    
    @pytest.mark.asyncio
    async def test_disconnect_user_compatibility(self):
        """Test legacy disconnect_user method."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        
        conn_info = await self.manager.connect_user("disconnect_user", websocket)
        
        # Verify connection exists
        self.assertTrue(self.manager.is_connection_active("disconnect_user"))
        
        # Disconnect user
        await self.manager.disconnect_user("disconnect_user", websocket)
        
        # Verify connection removed
        self.assertFalse(self.manager.is_connection_active("disconnect_user"))
        self.assertNotIn(conn_info.connection_id, self.manager.connection_registry)
    
    @pytest.mark.asyncio
    async def test_find_connection_compatibility(self):
        """Test legacy find_connection method."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        
        conn_info = await self.manager.connect_user("find_user", websocket)
        
        found = await self.manager.find_connection("find_user", websocket)
        
        self.assertEqual(found.user_id, "find_user") 
        self.assertEqual(found.connection_id, conn_info.connection_id)
        self.assertEqual(found.websocket, websocket)
    
    @pytest.mark.asyncio
    async def test_connect_to_job_compatibility(self):
        """Test legacy connect_to_job method."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        
        conn_info = await self.manager.connect_to_job(websocket, "job_123")
        
        self.assertIn("job_123", conn_info.user_id)
        self.assertEqual(conn_info.job_id, "job_123")
        
        # Verify room manager setup
        self.assertIsNotNone(self.manager.core.room_manager)
        self.assertIn("job_123", self.manager.core.room_manager.rooms)
    
    # ============================================================================
    # ERROR RECOVERY AND MESSAGE QUEUING TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_message_recovery_queue_storage(self):
        """Test failed message storage in recovery queue."""
        test_message = {"type": "test", "data": "recovery_test"}
        
        await self.manager._store_failed_message(
            "recovery_user", 
            test_message,
            "test_failure"
        )
        
        # Verify message stored
        self.assertIn("recovery_user", self.manager._message_recovery_queue)
        stored_messages = self.manager._message_recovery_queue["recovery_user"]
        self.assertEqual(len(stored_messages), 1)
        self.assertEqual(stored_messages[0]["type"], "test")
        self.assertEqual(stored_messages[0]["failure_reason"], "test_failure")
    
    @pytest.mark.asyncio
    async def test_message_recovery_queue_limit(self):
        """Test recovery queue size limit."""
        # Fill queue beyond limit
        for i in range(60):  # Exceeds max_queue_size of 50
            await self.manager._store_failed_message(
                "queue_user",
                {"type": "test", "data": f"message_{i}"},
                "test_failure"
            )
        
        # Verify queue was trimmed to limit
        stored_messages = self.manager._message_recovery_queue["queue_user"]
        self.assertEqual(len(stored_messages), 50)
        
        # Verify newest messages kept (should have message_10 to message_59)
        first_message = stored_messages[0]
        self.assertEqual(first_message["data"], "message_10")
    
    @pytest.mark.asyncio
    async def test_process_queued_messages(self):
        """Test processing of queued messages when connection established."""
        # Store some failed messages
        for i in range(3):
            await self.manager._store_failed_message(
                "process_user",
                {"type": "queued", "data": f"msg_{i}"},
                "connection_failed"
            )
        
        # Add connection
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("process_conn", "process_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        # Process queued messages should be called automatically
        # Give it time to process
        await asyncio.sleep(0.1)
        
        # Verify messages were sent
        self.assertEqual(websocket.send_json.call_count, 3)
    
    # ============================================================================
    # BACKGROUND MONITORING TESTS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_start_monitored_background_task(self):
        """Test starting background tasks with monitoring."""
        task_executed = asyncio.Event()
        
        async def test_task():
            task_executed.set()
        
        task_name = await self.manager.start_monitored_background_task("test_task", test_task)
        
        self.assertEqual(task_name, "test_task")
        self.assertIn("test_task", self.manager._background_tasks)
        
        # Wait for task execution
        await asyncio.wait_for(task_executed.wait(), timeout=2.0)
    
    @pytest.mark.asyncio
    async def test_stop_background_task(self):
        """Test stopping background task."""
        async def long_running_task():
            await asyncio.sleep(10)  # Long running task
        
        task_name = await self.manager.start_monitored_background_task(
            "stop_test", long_running_task
        )
        
        # Stop the task
        result = await self.manager.stop_background_task(task_name)
        
        self.assertTrue(result)
        self.assertNotIn(task_name, self.manager._background_tasks)
    
    @pytest.mark.asyncio
    async def test_get_background_task_status(self):
        """Test getting background task status."""
        async def status_test_task():
            await asyncio.sleep(0.1)
        
        await self.manager.start_monitored_background_task("status_test", status_test_task)
        
        status = self.manager.get_background_task_status()
        
        self.assertTrue(status["monitoring_enabled"])
        self.assertEqual(status["total_tasks"], 1)
        self.assertIn("status_test", status["tasks"])
    
    @pytest.mark.asyncio
    async def test_monitoring_health_status(self):
        """Test comprehensive monitoring health status."""
        health_status = await self.manager.get_monitoring_health_status()
        
        self.assertIn("monitoring_enabled", health_status)
        self.assertIn("task_health", health_status)
        self.assertIn("overall_health", health_status)
        self.assertIn("alerts", health_status)
        
        # Verify overall health structure
        overall_health = health_status["overall_health"]
        self.assertIn("score", overall_health)
        self.assertIn("status", overall_health)
    
    @pytest.mark.asyncio
    async def test_enable_background_monitoring(self):
        """Test enabling background monitoring after disable."""
        # First disable monitoring
        await self.manager.shutdown_background_monitoring()
        
        # Re-enable monitoring
        result = await self.manager.enable_background_monitoring()
        
        self.assertTrue(result["monitoring_enabled"])
        self.assertTrue(result["health_check_reset"])
    
    # ============================================================================
    # FIVE WHYS ROOT CAUSE PREVENTION METHODS
    # ============================================================================
    
    @pytest.mark.asyncio
    async def test_get_connection_id_by_websocket(self):
        """Test Five Whys critical method for connection ID lookup."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("five_whys_conn", "five_whys_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        # Find connection by websocket
        found_id = self.manager.get_connection_id_by_websocket(websocket)
        
        self.assertEqual(found_id, "five_whys_conn")
    
    @pytest.mark.asyncio
    async def test_get_connection_id_by_websocket_not_found(self):
        """Test connection ID lookup with non-existent websocket."""
        websocket = Mock()
        
        found_id = self.manager.get_connection_id_by_websocket(websocket)
        
        self.assertIsNone(found_id)
    
    @pytest.mark.asyncio
    async def test_update_connection_thread(self):
        """Test Five Whys critical method for thread association."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        connection = WebSocketConnection("thread_conn", "thread_user", websocket, datetime.now())
        
        await self.manager.add_connection(connection)
        
        # Update thread association
        result = self.manager.update_connection_thread("thread_conn", "new_thread_123")
        
        self.assertTrue(result)
        
        # Verify thread ID was updated
        updated_connection = self.manager.get_connection("thread_conn")
        self.assertEqual(updated_connection.thread_id, "new_thread_123")
    
    @pytest.mark.asyncio
    async def test_update_connection_thread_not_found(self):
        """Test thread update with non-existent connection."""
        result = self.manager.update_connection_thread("nonexistent", "thread_123")
        
        self.assertFalse(result)


class TestSerializeMessageSafely(unittest.TestCase):
    """Unit tests for _serialize_message_safely function."""
    
    def test_serialize_dict_already_serializable(self):
        """Test serialization of already JSON-serializable dict."""
        data = {"key": "value", "number": 42}
        result = _serialize_message_safely(data)
        
        self.assertEqual(result, data)
    
    def test_serialize_websocket_state_enum(self):
        """Test TestWebSocketState enum serialization (generic enum behavior)."""
        # TestWebSocketState is a test enum, not a real WebSocketState
        # It should behave like a generic enum and return its value
        result = _serialize_message_safely(TestWebSocketState.OPEN)
        
        # Should return the enum value for test enums
        self.assertEqual(result, 1)
    
    def test_serialize_generic_enum(self):
        """Test generic enum serialization."""
        result = _serialize_message_safely(TestWebSocketState.CLOSED)
        self.assertEqual(result, 3)  # Should use .value for generic enums
    
    def test_serialize_pydantic_model(self):
        """Test Pydantic model serialization."""
        timestamp = datetime.now()
        model = TestPydanticModel("test_value", timestamp)
        
        result = _serialize_message_safely(model)
        
        self.assertEqual(result["field1"], "test_value")
        self.assertEqual(result["timestamp"], timestamp.isoformat())
    
    def test_serialize_datetime(self):
        """Test datetime serialization."""
        dt = datetime.now()
        result = _serialize_message_safely(dt)
        
        self.assertEqual(result, dt.isoformat())
    
    def test_serialize_list(self):
        """Test list serialization."""
        data = ["string", 42, TestWebSocketState.OPEN]
        result = _serialize_message_safely(data)
        
        self.assertEqual(result[0], "string")
        self.assertEqual(result[1], 42)
        self.assertEqual(result[2], 1)  # TestWebSocketState.OPEN has value 1
    
    def test_serialize_set(self):
        """Test set serialization (converted to list)."""
        data = {"item1", "item2", "item3"}
        result = _serialize_message_safely(data)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertIn("item1", result)
    
    def test_serialize_dict_with_enum_keys(self):
        """Test dict with enum keys serialization."""
        data = {TestWebSocketState.OPEN: "connected", "normal_key": "value"}
        result = _serialize_message_safely(data)
        
        self.assertIn("open", result)  # Enum key converted
        self.assertEqual(result["open"], "connected")
        self.assertEqual(result["normal_key"], "value")
    
    def test_serialize_complex_nested(self):
        """Test complex nested data structure."""
        data = {
            "user": "test_user",
            "state": TestWebSocketState.CONNECTING,
            "connections": [
                {"id": "conn1", "active": True},
                {"id": "conn2", "active": False}
            ],
            "metadata": {
                "timestamp": datetime.now(),
                "tags": {"urgent", "retry"}
            }
        }
        
        result = _serialize_message_safely(data)
        
        self.assertEqual(result["user"], "test_user")
        self.assertEqual(result["state"], 0)  # TestWebSocketState.CONNECTING has value 0
        self.assertIsInstance(result["connections"], list)
        self.assertEqual(len(result["connections"]), 2)
        self.assertIsInstance(result["metadata"]["timestamp"], str)
        self.assertIsInstance(result["metadata"]["tags"], list)
    
    def test_serialize_fallback_string(self):
        """Test fallback to string for unserializable objects."""
        class UnserializableClass:
            def __str__(self):
                return "unserializable_object"
        
        obj = UnserializableClass()
        
        with patch('netra_backend.app.websocket_core.unified_manager.logger') as mock_logger:
            result = _serialize_message_safely(obj)
            
            self.assertEqual(result, "unserializable_object")
            # Should log warning about fallback
            mock_logger.warning.assert_called()
    
    def test_serialize_basic_types(self):
        """Test serialization of basic JSON-compatible types."""
        test_cases = [
            ("string", "string"),
            (42, 42), 
            (3.14, 3.14),
            (True, True),
            (None, None)
        ]
        
        for input_val, expected in test_cases:
            result = _serialize_message_safely(input_val)
            self.assertEqual(result, expected)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])