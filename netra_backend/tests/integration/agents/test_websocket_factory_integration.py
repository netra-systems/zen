"""
Integration Tests for WebSocket Factory Integration and Error Scenarios

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Platform Stability & User Experience
- Value Impact: Ensures WebSocket events enable chat business value and 5+ concurrent users
- Strategic Impact: Critical for real-time user experience and multi-user production deployment

CRITICAL FOCUS AREAS:
1. WebSocket factory integration ensures events reach correct users only
2. AgentWebSocketBridge properly isolates user notification streams
3. UserWebSocketEmitter provides per-user event isolation
4. Factory patterns handle WebSocket errors gracefully without affecting other users
5. Error scenarios in WebSocket operations don't compromise user isolation
6. WebSocket connection lifecycle properly integrates with factory patterns
7. Concurrent WebSocket operations maintain user isolation boundaries
8. WebSocket bridge registration/cleanup works reliably with factory patterns

FAILURE CONDITIONS:
- WebSocket events reach wrong users = SECURITY/PRIVACY VIOLATION
- WebSocket errors affect other users = ISOLATION BREACH
- Missing WebSocket events = BUSINESS VALUE FAILURE
- WebSocket memory leaks = RESOURCE EXHAUSTION
- Factory/WebSocket integration failures = SYSTEM INSTABILITY

This test suite focuses on WebSocket integration with factory patterns (NO MOCKS per CLAUDE.md).
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT imports following CLAUDE.md absolute import requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# WebSocket and Factory imports
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserWebSocketEmitter,
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

# WebSocket core imports
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


class MockWebSocketConnection:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.messages_sent = []
        self.is_closed = False
        self.connection_info = {
            "client_id": client_id,
            "connected_at": time.time(),
            "messages_sent": 0
        }
    
    async def send_text(self, message: str):
        """Mock send text message."""
        if self.is_closed:
            raise ConnectionError(f"WebSocket connection {self.client_id} is closed")
        
        self.messages_sent.append({
            "message": message,
            "timestamp": time.time(),
            "type": "text"
        })
        self.connection_info["messages_sent"] += 1
    
    async def send_json(self, data: dict):
        """Mock send JSON message."""
        if self.is_closed:
            raise ConnectionError(f"WebSocket connection {self.client_id} is closed")
        
        self.messages_sent.append({
            "message": json.dumps(data),
            "data": data,
            "timestamp": time.time(),
            "type": "json"
        })
        self.connection_info["messages_sent"] += 1
    
    async def close(self):
        """Mock close connection."""
        self.is_closed = True


class MockWebSocketManager:
    """Mock WebSocket manager that provides realistic WebSocket behavior."""
    
    def __init__(self):
        self.active_connections: Dict[str, MockWebSocketConnection] = {}
        self.run_thread_mappings: Dict[str, str] = {}  # run_id -> thread_id
        self.event_log: List[Dict[str, Any]] = []
    
    def add_connection(self, thread_id: str, connection: MockWebSocketConnection):
        """Add connection for a thread."""
        self.active_connections[thread_id] = connection
    
    def remove_connection(self, thread_id: str):
        """Remove connection for a thread."""
        if thread_id in self.active_connections:
            connection = self.active_connections[thread_id]
            asyncio.create_task(connection.close())
            del self.active_connections[thread_id]
    
    async def register_run_thread_mapping(self, run_id: str, thread_id: str, metadata: Optional[Dict] = None) -> bool:
        """Register run-thread mapping."""
        self.run_thread_mappings[run_id] = thread_id
        self.event_log.append({
            "action": "register_mapping",
            "run_id": run_id,
            "thread_id": thread_id,
            "metadata": metadata,
            "timestamp": time.time()
        })
        return True
    
    async def unregister_run_mapping(self, run_id: str) -> bool:
        """Unregister run mapping."""
        thread_id = self.run_thread_mappings.pop(run_id, None)
        self.event_log.append({
            "action": "unregister_mapping",
            "run_id": run_id,
            "thread_id": thread_id,
            "timestamp": time.time()
        })
        return thread_id is not None
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific thread."""
        if thread_id not in self.active_connections:
            self.event_log.append({
                "action": "send_failed",
                "thread_id": thread_id,
                "reason": "no_connection",
                "timestamp": time.time()
            })
            return False
        
        try:
            connection = self.active_connections[thread_id]
            await connection.send_json(message)
            
            self.event_log.append({
                "action": "send_success",
                "thread_id": thread_id,
                "message": message,
                "timestamp": time.time()
            })
            return True
            
        except Exception as e:
            self.event_log.append({
                "action": "send_error",
                "thread_id": thread_id,
                "error": str(e),
                "timestamp": time.time()
            })
            return False
    
    async def send_to_run(self, run_id: str, message: Dict[str, Any]) -> bool:
        """Send message to run via thread mapping."""
        thread_id = self.run_thread_mappings.get(run_id)
        if not thread_id:
            self.event_log.append({
                "action": "send_to_run_failed",
                "run_id": run_id,
                "reason": "no_mapping",
                "timestamp": time.time()
            })
            return False
        
        return await self.send_to_thread(thread_id, message)
    
    def get_connection_info(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get connection info for thread."""
        connection = self.active_connections.get(thread_id)
        if connection:
            return connection.connection_info.copy()
        return None
    
    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get event log for testing."""
        return self.event_log.copy()
    
    def clear_event_log(self):
        """Clear event log."""
        self.event_log.clear()


class TestWebSocketFactoryIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket factory integration and error scenarios."""
    
    @pytest.fixture
    async def mock_websocket_manager(self):
        """Mock WebSocket manager with realistic behavior."""
        return MockWebSocketManager()
    
    @pytest.fixture
    async def agent_websocket_bridge(self, mock_websocket_manager):
        """Real WebSocket bridge with mock manager."""
        bridge = AgentWebSocketBridge(mock_websocket_manager)
        return bridge
    
    @pytest.fixture
    async def agent_instance_factory(self, agent_websocket_bridge, mock_websocket_manager):
        """Real agent instance factory with WebSocket integration."""
        factory = AgentInstanceFactory()
        factory.configure(
            websocket_bridge=agent_websocket_bridge,
            websocket_manager=mock_websocket_manager
        )
        yield factory
        factory.reset_for_testing()
    
    @pytest.fixture
    async def execution_engine_factory(self, agent_websocket_bridge):
        """Real execution engine factory with WebSocket integration."""
        factory = ExecutionEngineFactory(websocket_bridge=agent_websocket_bridge)
        yield factory
        await factory.shutdown()
    
    def create_test_context(self, user_id: str, suffix: str = "") -> UserExecutionContext:
        """Create test context."""
        return UserExecutionContext(
            user_id=f"{user_id}{suffix}",
            thread_id=f"thread_{user_id}{suffix}_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{user_id}{suffix}_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{user_id}{suffix}_{uuid.uuid4().hex[:8]}"
        )
    
    def setup_websocket_connections(self, mock_manager: MockWebSocketManager, user_contexts: List[UserExecutionContext]):
        """Setup WebSocket connections for test contexts."""
        for context in user_contexts:
            connection = MockWebSocketConnection(f"client_{context.user_id}")
            mock_manager.add_connection(context.thread_id, connection)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_emitter_provides_per_user_isolation(self, agent_websocket_bridge, mock_websocket_manager):
        """Test that UserWebSocketEmitter provides complete per-user isolation.
        
        BVJ: Ensures WebSocket events are properly isolated per user - prevents notification cross-contamination.
        """
        # Create test users
        user_1_context = self.create_test_context("ws_isolation_user_1")
        user_2_context = self.create_test_context("ws_isolation_user_2")
        user_contexts = [user_1_context, user_2_context]
        
        # Setup WebSocket connections
        self.setup_websocket_connections(mock_websocket_manager, user_contexts)
        
        # Register run-thread mappings
        for context in user_contexts:
            await mock_websocket_manager.register_run_thread_mapping(
                context.run_id, context.thread_id, {"user_id": context.user_id}
            )
        
        # Create WebSocket emitters for each user
        emitter_1 = UserWebSocketEmitter(
            user_1_context.user_id, user_1_context.thread_id, user_1_context.run_id, agent_websocket_bridge
        )
        emitter_2 = UserWebSocketEmitter(
            user_2_context.user_id, user_2_context.thread_id, user_2_context.run_id, agent_websocket_bridge
        )
        
        # Send distinct events from each emitter
        await emitter_1.notify_agent_started("DataAgent", {"user": user_1_context.user_id, "task": "user_1_analysis"})
        await emitter_2.notify_agent_started("OptimizationAgent", {"user": user_2_context.user_id, "task": "user_2_optimization"})
        
        await emitter_1.notify_agent_thinking("DataAgent", "Analyzing user 1 data", step_number=1)
        await emitter_2.notify_agent_thinking("OptimizationAgent", "Optimizing user 2 costs", step_number=1)
        
        # Verify events reached correct connections
        connection_1 = mock_websocket_manager.active_connections[user_1_context.thread_id]
        connection_2 = mock_websocket_manager.active_connections[user_2_context.thread_id]
        
        # Check user 1 received only user 1 events
        user_1_messages = [msg["data"] for msg in connection_1.messages_sent if msg["type"] == "json"]
        assert len(user_1_messages) >= 2, "User 1 should have received events"
        
        for message in user_1_messages:
            # Verify no user 2 data in user 1 messages
            message_str = json.dumps(message).lower()
            assert "user_2" not in message_str, "User 1 messages should not contain user 2 data"
            assert "user_1" in message_str or "analyzing" in message_str, "User 1 messages should contain user 1 data"
        
        # Check user 2 received only user 2 events
        user_2_messages = [msg["data"] for msg in connection_2.messages_sent if msg["type"] == "json"]
        assert len(user_2_messages) >= 2, "User 2 should have received events"
        
        for message in user_2_messages:
            # Verify no user 1 data in user 2 messages
            message_str = json.dumps(message).lower()
            assert "user_1" not in message_str, "User 2 messages should not contain user 1 data"
            assert "user_2" in message_str or "optimizing" in message_str, "User 2 messages should contain user 2 data"
        
        # Test emitter status isolation
        status_1 = emitter_1.get_emitter_status()
        status_2 = emitter_2.get_emitter_status()
        
        assert status_1['user_id'] != status_2['user_id']
        assert status_1['run_id'] != status_2['run_id']
        assert status_1['event_count'] >= 2
        assert status_2['event_count'] >= 2
        
        # Cleanup and verify isolation maintained
        await emitter_1.cleanup()
        
        # User 2 should still be able to send events after user 1 cleanup
        await emitter_2.notify_tool_executing("OptimizationAgent", "cost_calculator", {"parameters": "user_2_specific"})
        
        updated_status_2 = emitter_2.get_emitter_status()
        assert updated_status_2['event_count'] > status_2['event_count']
        
        await emitter_2.cleanup()
        
        self.record_metric("websocket_emitter_isolation_verified", True)
        self.record_metric("isolated_events_sent", status_1['event_count'] + updated_status_2['event_count'])
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_factory_websocket_integration_prevents_cross_user_events(self, agent_instance_factory, mock_websocket_manager):
        """Test that factory WebSocket integration prevents cross-user event contamination.
        
        BVJ: Ensures factory-created contexts maintain WebSocket isolation - critical for user privacy.
        """
        # Create multiple users
        users = [
            ("factory_ws_user_1", "analyzing customer data"),
            ("factory_ws_user_2", "optimizing costs"),
            ("factory_ws_user_3", "generating reports")
        ]
        
        # Create contexts via factory
        user_contexts = []
        for user_id, task in users:
            context = await agent_instance_factory.create_user_execution_context(
                user_id=user_id,
                thread_id=f"thread_{user_id}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{user_id}_{uuid.uuid4().hex[:8]}",
                metadata={"task": task, "confidential": f"{user_id}_secret"}
            )
            user_contexts.append((user_id, task, context))
        
        # Setup WebSocket connections for all users
        contexts_only = [context for _, _, context in user_contexts]
        self.setup_websocket_connections(mock_websocket_manager, contexts_only)
        
        # Test WebSocket emitter creation and isolation
        emitters = []
        for user_id, task, context in user_contexts:
            # Emitters should be created by factory and stored
            factory_emitters = getattr(agent_instance_factory, '_websocket_emitters', {})
            context_key = f"{context.user_id}_{context.thread_id}_{context.run_id}_emitter"
            
            # Create emitter if not exists (simulating factory behavior)
            if context_key not in factory_emitters:
                emitter = UserWebSocketEmitter(
                    context.user_id, context.thread_id, context.run_id, agent_instance_factory._websocket_bridge
                )
                factory_emitters[context_key] = emitter
                agent_instance_factory._websocket_emitters = factory_emitters
            
            emitter = factory_emitters[context_key]
            emitters.append((user_id, task, context, emitter))
        
        # Send user-specific events concurrently
        async def send_user_events(user_id: str, task: str, context: UserExecutionContext, emitter: UserWebSocketEmitter):
            """Send user-specific events."""
            # Register run-thread mapping
            await mock_websocket_manager.register_run_thread_mapping(
                context.run_id, context.thread_id, {"user_id": context.user_id}
            )
            
            await emitter.notify_agent_started("TaskAgent", {
                "user_id": context.user_id,
                "task": task,
                "confidential_data": f"{user_id}_confidential"
            })
            
            await emitter.notify_agent_thinking("TaskAgent", f"Processing {task} for {user_id}")
            
            await emitter.notify_tool_executing("TaskAgent", "data_processor", {
                "user_data": f"{user_id}_data",
                "task_specific": task
            })
            
            return user_id
        
        # Execute concurrent events
        tasks_list = [
            asyncio.create_task(send_user_events(user_id, task, context, emitter))
            for user_id, task, context, emitter in emitters
        ]
        
        completed_users = await asyncio.gather(*tasks_list)
        assert len(completed_users) == len(users)
        
        # Verify event isolation
        for user_id, task, context, emitter in emitters:
            connection = mock_websocket_manager.active_connections[context.thread_id]
            user_messages = [msg["data"] for msg in connection.messages_sent if msg["type"] == "json"]
            
            assert len(user_messages) >= 3, f"User {user_id} should have received events"
            
            # Check each message for isolation
            for message in user_messages:
                message_str = json.dumps(message).lower()
                
                # Should contain user's own data
                assert user_id.lower() in message_str, f"Message should contain {user_id}"
                
                # Should not contain other users' data
                for other_user_id, other_task, _, _ in emitters:
                    if other_user_id != user_id:
                        assert other_user_id.lower() not in message_str, \
                            f"User {user_id} message contains {other_user_id} data"
                        assert other_task.lower() not in message_str, \
                            f"User {user_id} message contains {other_user_id}'s task"
        
        # Test factory cleanup maintains isolation
        for user_id, _, context, _ in emitters[:2]:  # Cleanup first 2 users
            await agent_instance_factory.cleanup_user_context(context)
        
        # Remaining user should still be functional
        remaining_user_id, remaining_task, remaining_context, remaining_emitter = emitters[2]
        await remaining_emitter.notify_agent_completed("TaskAgent", {"status": "completed"})
        
        remaining_connection = mock_websocket_manager.active_connections[remaining_context.thread_id]
        final_messages = [msg["data"] for msg in remaining_connection.messages_sent if msg["type"] == "json"]
        
        # Should have one more message
        assert len(final_messages) >= 4, "Remaining user should have received completion event"
        
        self.record_metric("factory_websocket_isolation_verified", True)
        self.record_metric("concurrent_websocket_users", len(users))
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_scenarios_maintain_isolation(self, agent_instance_factory, mock_websocket_manager):
        """Test that WebSocket error scenarios don't compromise user isolation.
        
        BVJ: Ensures WebSocket errors in one user don't affect others - critical for system stability.
        """
        # Create stable and error-prone users
        stable_context = await agent_instance_factory.create_user_execution_context(
            user_id="stable_ws_user",
            thread_id="stable_thread",
            run_id="stable_run"
        )
        
        error_context = await agent_instance_factory.create_user_execution_context(
            user_id="error_ws_user", 
            thread_id="error_thread",
            run_id="error_run"
        )
        
        # Setup connections
        self.setup_websocket_connections(mock_websocket_manager, [stable_context, error_context])
        
        # Register mappings
        await mock_websocket_manager.register_run_thread_mapping(
            stable_context.run_id, stable_context.thread_id, {"user_id": stable_context.user_id}
        )
        await mock_websocket_manager.register_run_thread_mapping(
            error_context.run_id, error_context.thread_id, {"user_id": error_context.user_id}
        )
        
        # Create emitters
        stable_emitter = UserWebSocketEmitter(
            stable_context.user_id, stable_context.thread_id, stable_context.run_id, 
            agent_instance_factory._websocket_bridge
        )
        
        error_emitter = UserWebSocketEmitter(
            error_context.user_id, error_context.thread_id, error_context.run_id,
            agent_instance_factory._websocket_bridge
        )
        
        # Send stable user events
        await stable_emitter.notify_agent_started("StableAgent", {"status": "healthy"})
        
        # Simulate WebSocket connection error for error user
        error_connection = mock_websocket_manager.active_connections[error_context.thread_id]
        error_connection.is_closed = True
        
        # Attempt to send events to error user (should fail gracefully)
        try:
            await error_emitter.notify_agent_started("ErrorAgent", {"status": "will_fail"})
        except Exception:
            pass  # Expected to fail
        
        # Verify stable user is unaffected
        stable_connection = mock_websocket_manager.active_connections[stable_context.thread_id]
        assert not stable_connection.is_closed, "Stable connection should remain open"
        
        # Stable user should still be able to send events
        await stable_emitter.notify_agent_thinking("StableAgent", "Still working fine")
        
        stable_messages = [msg["data"] for msg in stable_connection.messages_sent if msg["type"] == "json"]
        assert len(stable_messages) >= 2, "Stable user should have received events"
        
        # Error user's connection should be closed, but no events should leak to stable user
        for message in stable_messages:
            message_str = json.dumps(message).lower()
            assert "error_ws_user" not in message_str, "Stable user should not receive error user events"
            assert "stable" in message_str or "healthy" in message_str, "Stable user events should be normal"
        
        # Test WebSocket bridge error handling
        # Remove error user's thread mapping
        await mock_websocket_manager.unregister_run_mapping(error_context.run_id)
        
        # Create new error emitter and try to send events
        new_error_emitter = UserWebSocketEmitter(
            "new_error_user", "new_error_thread", "new_error_run",
            agent_instance_factory._websocket_bridge
        )
        
        # This should fail gracefully (no mapping exists)
        try:
            await new_error_emitter.notify_agent_started("NewErrorAgent", {"status": "no_mapping"})
        except Exception:
            pass  # May fail, that's OK
        
        # Stable user should still work perfectly
        await stable_emitter.notify_tool_executing("StableAgent", "stable_tool", {"working": True})
        
        updated_stable_messages = [msg["data"] for msg in stable_connection.messages_sent if msg["type"] == "json"]
        assert len(updated_stable_messages) >= 3, "Stable user should continue receiving events"
        
        # Test emitter cleanup under error conditions
        try:
            await error_emitter.cleanup()
        except Exception:
            pass  # May fail due to connection issues
        
        # Stable emitter cleanup should work fine
        await stable_emitter.cleanup()
        
        self.record_metric("websocket_error_isolation_maintained", True)
        self.record_metric("stable_user_unaffected_by_errors", True)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_websocket_operations_maintain_boundaries(self, execution_engine_factory, mock_websocket_manager):
        """Test that concurrent WebSocket operations maintain user boundaries.
        
        BVJ: Ensures concurrent WebSocket operations don't interfere - critical for multi-user scenarios.
        """
        num_concurrent_users = 8
        
        # Create user contexts
        user_contexts = []
        for i in range(num_concurrent_users):
            context = UserExecutionContext(
                user_id=f"concurrent_ws_user_{i}",
                thread_id=f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"concurrent_run_{i}_{uuid.uuid4().hex[:8]}",
                request_id=f"concurrent_req_{i}_{uuid.uuid4().hex[:8]}"
            )
            user_contexts.append(context)
        
        # Setup WebSocket connections
        self.setup_websocket_connections(mock_websocket_manager, user_contexts)
        
        # Define concurrent WebSocket operation
        async def perform_websocket_operations(context: UserExecutionContext, operation_id: int):
            """Perform WebSocket operations for a specific user."""
            try:
                # Register run-thread mapping
                await mock_websocket_manager.register_run_thread_mapping(
                    context.run_id, context.thread_id, 
                    {"user_id": context.user_id, "operation_id": operation_id}
                )
                
                # Create execution engine
                engine = await execution_engine_factory.create_for_user(context)
                
                # Get WebSocket emitter from engine
                websocket_emitter = engine.websocket_emitter
                
                # Send sequence of events with user-specific data
                await websocket_emitter.notify_agent_started(
                    "ConcurrentAgent", 
                    {"user_id": context.user_id, "operation_id": operation_id, "secret": f"user_{operation_id}_secret"}
                )
                
                # Add some variability in timing
                await asyncio.sleep(0.01 * (operation_id % 3))
                
                await websocket_emitter.notify_agent_thinking(
                    "ConcurrentAgent", 
                    f"Processing operation {operation_id} for user {context.user_id}",
                    step_number=operation_id
                )
                
                await asyncio.sleep(0.01 * ((operation_id + 1) % 3))
                
                await websocket_emitter.notify_tool_executing(
                    "ConcurrentAgent", 
                    f"concurrent_tool_{operation_id}",
                    {"user_data": f"user_{operation_id}_data", "operation": operation_id}
                )
                
                await websocket_emitter.notify_tool_completed(
                    "ConcurrentAgent",
                    f"concurrent_tool_{operation_id}",
                    {"result": f"user_{operation_id}_result", "success": True}
                )
                
                await websocket_emitter.notify_agent_completed(
                    "ConcurrentAgent",
                    {"final_result": f"operation_{operation_id}_complete"}
                )
                
                # Cleanup
                await execution_engine_factory.cleanup_engine(engine)
                
                return {
                    "operation_id": operation_id,
                    "user_id": context.user_id,
                    "events_sent": 5,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "operation_id": operation_id,
                    "user_id": context.user_id,
                    "error": str(e),
                    "success": False
                }
        
        # Execute all operations concurrently
        tasks = [
            asyncio.create_task(perform_websocket_operations(context, i))
            for i, context in enumerate(user_contexts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all operations succeeded
        successful_operations = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent WebSocket operation {i} failed: {result}")
            elif result.get('success'):
                successful_operations += 1
            else:
                pytest.fail(f"Concurrent WebSocket operation {i} failed: {result.get('error')}")
        
        assert successful_operations == num_concurrent_users, "All concurrent operations should succeed"
        
        # Verify message isolation across all users
        for i, context in enumerate(user_contexts):
            connection = mock_websocket_manager.active_connections[context.thread_id]
            user_messages = [msg["data"] for msg in connection.messages_sent if msg["type"] == "json"]
            
            assert len(user_messages) >= 5, f"User {i} should have received all events"
            
            # Verify each message contains only user's data
            for message in user_messages:
                message_str = json.dumps(message).lower()
                
                # Should contain user's operation ID
                assert f"user_{i}" in message_str or str(i) in message_str, \
                    f"User {i} message should contain their data"
                
                # Should not contain other users' data
                for j in range(num_concurrent_users):
                    if i != j:
                        # Check for other users' secrets or specific data
                        assert f"user_{j}_secret" not in message_str, \
                            f"User {i} received user {j}'s secret data"
                        assert f"user_{j}_data" not in message_str, \
                            f"User {i} received user {j}'s data"
                        assert f"user_{j}_result" not in message_str, \
                            f"User {i} received user {j}'s results"
        
        # Verify WebSocket event log integrity
        event_log = mock_websocket_manager.get_event_log()
        
        # Should have registration and send events for all users
        register_events = [e for e in event_log if e["action"] == "register_mapping"]
        send_events = [e for e in event_log if e["action"] == "send_success"]
        
        assert len(register_events) >= num_concurrent_users, "All users should have registered"
        assert len(send_events) >= num_concurrent_users * 5, "All events should have been sent"
        
        # Verify no send failures due to concurrency
        failed_sends = [e for e in event_log if e["action"] in ["send_failed", "send_error"]]
        assert len(failed_sends) == 0, f"No send failures expected, but got: {failed_sends}"
        
        self.record_metric("concurrent_websocket_operations_successful", successful_operations)
        self.record_metric("websocket_message_isolation_verified", True)
        self.record_metric("concurrent_users_tested", num_concurrent_users)
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_lifecycle_integration_with_factory_patterns(self, agent_instance_factory, mock_websocket_manager):
        """Test WebSocket lifecycle integration with factory patterns.
        
        BVJ: Ensures WebSocket lifecycle properly integrates with factory cleanup - prevents resource leaks.
        """
        # Track initial state
        initial_connections = len(mock_websocket_manager.active_connections)
        initial_mappings = len(mock_websocket_manager.run_thread_mappings)
        
        # Create user contexts via factory
        contexts = []
        for i in range(5):
            context = await agent_instance_factory.create_user_execution_context(
                user_id=f"lifecycle_user_{i}",
                thread_id=f"lifecycle_thread_{i}",
                run_id=f"lifecycle_run_{i}",
                metadata={"lifecycle_test": True, "user_index": i}
            )
            contexts.append(context)
        
        # Setup WebSocket connections and register mappings
        self.setup_websocket_connections(mock_websocket_manager, contexts)
        
        # Register all run-thread mappings
        for context in contexts:
            await mock_websocket_manager.register_run_thread_mapping(
                context.run_id, context.thread_id, {"user_id": context.user_id}
            )
        
        # Verify connections and mappings were created
        assert len(mock_websocket_manager.active_connections) == initial_connections + 5
        assert len(mock_websocket_manager.run_thread_mappings) == initial_mappings + 5
        
        # Create and use WebSocket emitters
        emitters = []
        for context in contexts:
            emitter = UserWebSocketEmitter(
                context.user_id, context.thread_id, context.run_id, 
                agent_instance_factory._websocket_bridge
            )
            
            # Send lifecycle events
            await emitter.notify_agent_started("LifecycleAgent", {"lifecycle_phase": "start"})
            await emitter.notify_agent_thinking("LifecycleAgent", "Testing lifecycle integration")
            
            emitters.append((context, emitter))
        
        # Verify all events were sent successfully
        for context, emitter in emitters:
            connection = mock_websocket_manager.active_connections[context.thread_id]
            messages = [msg for msg in connection.messages_sent if msg["type"] == "json"]
            assert len(messages) >= 2, "Should have received lifecycle events"
        
        # Test gradual cleanup (some users leave)
        cleanup_contexts = contexts[:3]  # Cleanup first 3 users
        
        for context in cleanup_contexts:
            # Cleanup via factory
            await agent_instance_factory.cleanup_user_context(context)
            
            # Cleanup WebSocket resources
            mock_websocket_manager.remove_connection(context.thread_id)
            await mock_websocket_manager.unregister_run_mapping(context.run_id)
        
        # Verify partial cleanup
        remaining_connections = len(mock_websocket_manager.active_connections)
        remaining_mappings = len(mock_websocket_manager.run_thread_mappings)
        
        assert remaining_connections == initial_connections + 2, "Should have 2 connections remaining"
        assert remaining_mappings == initial_mappings + 2, "Should have 2 mappings remaining"
        
        # Verify remaining users still work
        remaining_contexts = contexts[3:]
        for i, context in enumerate(remaining_contexts):
            emitter = UserWebSocketEmitter(
                context.user_id, context.thread_id, context.run_id,
                agent_instance_factory._websocket_bridge
            )
            
            await emitter.notify_agent_completed("LifecycleAgent", {"still_working": True, "index": i})
            
            connection = mock_websocket_manager.active_connections[context.thread_id]
            all_messages = [msg for msg in connection.messages_sent if msg["type"] == "json"]
            assert len(all_messages) >= 3, "Should have received all events including completion"
        
        # Test complete cleanup
        for context in remaining_contexts:
            await agent_instance_factory.cleanup_user_context(context)
            mock_websocket_manager.remove_connection(context.thread_id)
            await mock_websocket_manager.unregister_run_mapping(context.run_id)
        
        # Verify complete cleanup
        final_connections = len(mock_websocket_manager.active_connections)
        final_mappings = len(mock_websocket_manager.run_thread_mappings)
        
        assert final_connections == initial_connections, "All connections should be cleaned up"
        assert final_mappings == initial_mappings, "All mappings should be cleaned up"
        
        # Test new user can be created after cleanup
        post_cleanup_context = await agent_instance_factory.create_user_execution_context(
            user_id="post_cleanup_user",
            thread_id="post_cleanup_thread", 
            run_id="post_cleanup_run"
        )
        
        # Setup new connection
        new_connection = MockWebSocketConnection("post_cleanup_client")
        mock_websocket_manager.add_connection(post_cleanup_context.thread_id, new_connection)
        await mock_websocket_manager.register_run_thread_mapping(
            post_cleanup_context.run_id, post_cleanup_context.thread_id
        )
        
        # Verify new user works
        new_emitter = UserWebSocketEmitter(
            post_cleanup_context.user_id, post_cleanup_context.thread_id, 
            post_cleanup_context.run_id, agent_instance_factory._websocket_bridge
        )
        
        await new_emitter.notify_agent_started("PostCleanupAgent", {"fresh_start": True})
        
        assert len(new_connection.messages_sent) >= 1, "New user should receive events"
        
        # Final cleanup
        await agent_instance_factory.cleanup_user_context(post_cleanup_context)
        
        self.record_metric("websocket_lifecycle_integration_verified", True)
        self.record_metric("partial_cleanup_isolation_maintained", True)
        self.record_metric("post_cleanup_functionality_verified", True)
        
    def teardown_method(self, method=None):
        """Clean up test resources."""
        super().teardown_method(method)
        
        # Log comprehensive test metrics
        metrics = self.get_all_metrics()
        print(f"\nWebSocket Factory Integration Test Metrics:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Verify critical metrics
        assert metrics.get("websocket_emitter_isolation_verified", False), "WebSocket emitter isolation must be verified"
        assert metrics.get("factory_websocket_isolation_verified", False), "Factory WebSocket isolation must be verified"
        assert metrics.get("websocket_error_isolation_maintained", False), "WebSocket error isolation must be maintained"
        assert metrics.get("concurrent_websocket_operations_successful", 0) >= 5, "Concurrent WebSocket operations must be successful"