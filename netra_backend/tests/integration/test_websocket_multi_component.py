"""Integration tests for WebSocket manager multi-component interactions.

CRITICAL: These tests verify REAL multi-component interactions for WebSocket
management without Docker dependencies. They test business-critical scenarios
where WebSocket events flow through multiple system components.

Business Value: Real-time user experience and agent communication.
"""

import asyncio
import pytest
import uuid
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.universal_registry import UniversalAgentRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.unified_id_manager import UnifiedIDManager
from shared.isolated_environment import IsolatedEnvironment


class MockWebSocket:
    """Mock WebSocket for testing without actual network connections."""
    
    def __init__(self, user_id: str = None):
        self.user_id = user_id or f"mock_user_{id(self)}"
        self.sent_messages = []
        self.is_closed = False
        self.client_state = "connected"
        
    async def send_json(self, data: Dict[str, Any]):
        """Mock sending JSON data."""
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
        self.sent_messages.append(data)
        
    async def send_text(self, data: str):
        """Mock sending text data."""
        if self.is_closed:
            raise RuntimeError("WebSocket is closed")
        self.sent_messages.append({"type": "text", "data": data})
        
    async def close(self):
        """Mock closing WebSocket."""
        self.is_closed = True
        self.client_state = "closed"


class TestWebSocketMultiComponentIntegration:
    """Integration tests for WebSocket manager with multiple components."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create unified WebSocket manager for testing."""
        return UnifiedWebSocketManager()
        
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock()
        llm_manager.get_llm = AsyncMock()
        llm_manager.get_llm.return_value = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    def agent_registry(self, mock_llm_manager):
        """Create agent registry with mock dependencies."""
        return AgentRegistry(mock_llm_manager)
        
    @pytest.fixture
    def user_contexts(self):
        """Create multiple user execution contexts for testing."""
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"integration_user_{i}",
                thread_id=f"integration_thread_{i}",
                request_id=f"integration_request_{i}",
                run_id=f"integration_run_{i}"
            )
            contexts.append(context)
        return contexts

    @pytest.mark.asyncio
    async def test_websocket_manager_agent_registry_integration(self, websocket_manager, agent_registry, user_contexts):
        """
        Test REAL integration between WebSocket manager and agent registry.
        
        This tests the interaction between:
        - UnifiedWebSocketManager (connection management)
        - AgentRegistry (agent lifecycle and user sessions)  
        - UserExecutionContext (user isolation)
        - MockWebSocket (connection simulation)
        
        Business scenario: Multiple users connect and receive real-time updates
        from their isolated agent sessions.
        """
        # PHASE 1: Set up WebSocket connections for multiple users
        connections = {}
        websockets = {}
        
        for context in user_contexts:
            # Create mock WebSocket for each user
            websocket = MockWebSocket(context.user_id)
            websockets[context.user_id] = websocket
            
            # Create WebSocket connection
            connection = WebSocketConnection(
                connection_id=f"conn_{context.user_id}_{uuid.uuid4().hex[:8]}",
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                thread_id=context.thread_id
            )
            connections[context.user_id] = connection
            
            # Add connection to manager
            await websocket_manager.add_connection(connection)
            
        # PHASE 2: Integrate WebSocket manager with agent registry
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Verify integration - registry should have WebSocket manager reference
        assert agent_registry.websocket_manager is websocket_manager, "Registry should reference WebSocket manager"
        
        # PHASE 3: Create user sessions and verify WebSocket propagation
        user_sessions = {}
        for context in user_contexts:
            user_session = await agent_registry.get_user_session(context.user_id)
            user_sessions[context.user_id] = user_session
            
            # Verify user session has WebSocket bridge after integration
            assert user_session._websocket_bridge is not None, f"User {context.user_id} should have WebSocket bridge"
        
        # PHASE 4: Test message delivery through integrated system
        test_events = [
            {"type": "agent_started", "data": {"agent": "triage", "status": "initializing"}},
            {"type": "tool_executing", "data": {"tool": "analysis", "progress": 50}},
            {"type": "agent_completed", "data": {"agent": "triage", "result": "analysis_complete"}}
        ]
        
        # Send events to each user and verify delivery
        for context in user_contexts:
            for event in test_events:
                await websocket_manager.emit_critical_event(context.user_id, event["type"], event["data"])
        
        # PHASE 5: Verify message delivery and isolation
        for context in user_contexts:
            websocket = websockets[context.user_id]
            sent_messages = websocket.sent_messages
            
            # Each user should receive exactly their messages
            assert len(sent_messages) == len(test_events), f"User {context.user_id} should receive all events"
            
            # Verify message content and isolation
            for i, expected_event in enumerate(test_events):
                received_message = sent_messages[i]
                assert received_message["type"] == expected_event["type"], "Event type should match"
                assert received_message["data"] == expected_event["data"], "Event data should match"
                assert received_message.get("critical") is True, "Critical events should be marked"
        
        # PHASE 6: Test user session cleanup and WebSocket disconnection
        for context in user_contexts:
            cleanup_result = await agent_registry.cleanup_user_session(context.user_id)
            assert cleanup_result["status"] == "cleaned", f"User {context.user_id} session should be cleaned"
            
        # Verify connections are still in WebSocket manager (cleanup doesn't auto-disconnect)
        for context in user_contexts:
            user_connections = websocket_manager.get_user_connections(context.user_id)
            assert len(user_connections) == 1, f"User {context.user_id} should still have WebSocket connection"

    @pytest.mark.asyncio
    async def test_websocket_manager_execution_context_lifecycle(self, websocket_manager, user_contexts):
        """
        Test REAL integration between WebSocket manager and execution context lifecycle.
        
        This tests the interaction between:
        - UnifiedWebSocketManager (message routing)
        - UserExecutionContext (request lifecycle)
        - UnifiedIDManager (ID generation and validation)
        - Connection lifecycle management
        
        Business scenario: User requests create contexts that manage WebSocket
        connections throughout their lifecycle.
        """
        # PHASE 1: Create connections with execution context integration
        id_manager = UnifiedIDManager()
        connections_by_context = {}
        
        for context in user_contexts:
            # Use UnifiedIDManager for proper ID generation
            connection_id = id_manager.generate_websocket_connection_id(context.user_id)
            
            # Create WebSocket connection tied to execution context
            websocket = MockWebSocket(context.user_id)
            connection = WebSocketConnection(
                connection_id=connection_id,
                user_id=context.user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                thread_id=context.thread_id,
                metadata={
                    "request_id": context.request_id,
                    "run_id": context.run_id,
                    "context_created_at": context.created_at.isoformat()
                }
            )
            
            connections_by_context[context.user_id] = {
                "connection": connection,
                "websocket": websocket,
                "context": context
            }
            
            # Add to WebSocket manager
            await websocket_manager.add_connection(connection)
        
        # PHASE 2: Test connection health and context association
        for user_id, conn_data in connections_by_context.items():
            context = conn_data["context"]
            
            # Verify connection health
            health = websocket_manager.get_connection_health(context.user_id)
            assert health["has_active_connections"] is True, f"User {user_id} should have active connections"
            assert health["total_connections"] == 1, f"User {user_id} should have exactly 1 connection"
            
            # Verify metadata association
            connection_detail = health["connections"][0]
            assert connection_detail["metadata"]["request_id"] == context.request_id, "Request ID should match"
            assert connection_detail["metadata"]["run_id"] == context.run_id, "Run ID should match"
        
        # PHASE 3: Test concurrent message delivery with context isolation
        async def send_context_messages(user_id: str, context: UserExecutionContext, message_count: int):
            """Send messages for a specific context."""
            messages_sent = []
            for i in range(message_count):
                message = {
                    "sequence": i,
                    "context_data": {
                        "user_id": context.user_id,
                        "thread_id": context.thread_id,
                        "request_id": context.request_id
                    },
                    "timestamp": datetime.now().isoformat()
                }
                await websocket_manager.send_to_user(user_id, message)
                messages_sent.append(message)
            return messages_sent
        
        # Send messages concurrently for all users
        tasks = []
        expected_messages = {}
        for user_id, conn_data in connections_by_context.items():
            context = conn_data["context"]
            task = send_context_messages(user_id, context, 5)  # 5 messages per user
            tasks.append(task)
            expected_messages[user_id] = task
        
        # Wait for all concurrent sends to complete
        all_sent_messages = await asyncio.gather(*tasks)
        
        # PHASE 4: Verify message delivery and context isolation
        for i, (user_id, conn_data) in enumerate(connections_by_context.items()):
            websocket = conn_data["websocket"]
            expected_for_user = await expected_messages[user_id]
            
            # Verify all messages received
            assert len(websocket.sent_messages) == 5, f"User {user_id} should receive 5 messages"
            
            # Verify message content and context isolation
            for j, received_msg in enumerate(websocket.sent_messages):
                expected_msg = expected_for_user[j]
                assert received_msg["sequence"] == expected_msg["sequence"], "Message sequence should match"
                assert received_msg["context_data"]["user_id"] == user_id, "Context user_id should match"
                
                # Verify no cross-contamination - each user should only see their own context data
                assert received_msg["context_data"]["user_id"] == conn_data["context"].user_id
                assert received_msg["context_data"]["thread_id"] == conn_data["context"].thread_id
        
        # PHASE 5: Test connection removal and context cleanup
        for user_id, conn_data in connections_by_context.items():
            connection = conn_data["connection"]
            
            # Test connection removal
            await websocket_manager.remove_connection(connection.connection_id)
            
            # Verify connection is removed
            remaining_connections = websocket_manager.get_user_connections(user_id)
            assert len(remaining_connections) == 0, f"User {user_id} should have no connections after removal"
            
            # Verify health reflects removal
            health = websocket_manager.get_connection_health(user_id)
            assert health["has_active_connections"] is False, f"User {user_id} should have no active connections"

    @pytest.mark.asyncio  
    async def test_websocket_error_recovery_multi_component_flow(self, websocket_manager, agent_registry, mock_llm_manager):
        """
        Test REAL error recovery flow across multiple WebSocket components.
        
        This tests the interaction between:
        - UnifiedWebSocketManager (error handling and recovery)
        - AgentRegistry (session management)
        - UserExecutionContext (isolation during errors)
        - Error recovery and message queuing
        
        Business scenario: When WebSocket connections fail, the system should
        queue messages and recover gracefully when connections are re-established.
        """
        # PHASE 1: Create user context and initial connection
        user_context = UserExecutionContext(
            user_id="error_recovery_user",
            thread_id="error_recovery_thread", 
            request_id="error_recovery_request",
            run_id="error_recovery_run"
        )
        
        # Create initial WebSocket connection
        initial_websocket = MockWebSocket(user_context.user_id)
        initial_connection = WebSocketConnection(
            connection_id=f"initial_conn_{uuid.uuid4().hex[:8]}",
            user_id=user_context.user_id,
            websocket=initial_websocket,
            connected_at=datetime.now()
        )
        
        await websocket_manager.add_connection(initial_connection)
        
        # PHASE 2: Set up agent registry integration
        agent_registry.set_websocket_manager(websocket_manager)
        user_session = await agent_registry.get_user_session(user_context.user_id)
        
        # PHASE 3: Simulate connection failure
        # Close the WebSocket to simulate failure
        await initial_websocket.close()
        initial_websocket.is_closed = True
        
        # Remove connection to simulate disconnection
        await websocket_manager.remove_connection(initial_connection.connection_id)
        
        # Verify no active connections
        assert not websocket_manager.is_connection_active(user_context.user_id), "User should have no active connections"
        
        # PHASE 4: Send messages while disconnected - they should be queued
        failed_messages = [
            {"type": "agent_started", "data": {"agent": "recovery_test", "status": "started"}},
            {"type": "tool_executing", "data": {"tool": "recovery_tool", "progress": 25}},
            {"type": "agent_thinking", "data": {"thought": "processing recovery scenario"}}
        ]
        
        for message in failed_messages:
            # These should be queued for recovery since no connection exists
            await websocket_manager.emit_critical_event(
                user_context.user_id, 
                message["type"], 
                message["data"]
            )
        
        # PHASE 5: Verify error statistics show failed messages
        error_stats = websocket_manager.get_error_statistics()
        assert error_stats["total_users_with_errors"] >= 1, "Should have users with errors"
        assert error_stats["total_queued_messages"] >= len(failed_messages), "Should have queued messages"
        
        # PHASE 6: Simulate reconnection
        recovery_websocket = MockWebSocket(user_context.user_id)
        recovery_connection = WebSocketConnection(
            connection_id=f"recovery_conn_{uuid.uuid4().hex[:8]}",
            user_id=user_context.user_id,
            websocket=recovery_websocket,
            connected_at=datetime.now(),
            metadata={"recovery_connection": True}
        )
        
        # Add recovery connection - this should trigger message recovery
        await websocket_manager.add_connection(recovery_connection)
        
        # PHASE 7: Wait for message recovery processing
        # Give the system time to process queued messages
        await asyncio.sleep(0.2)
        
        # PHASE 8: Verify message recovery
        # Recovery WebSocket should receive the queued messages
        recovered_messages = recovery_websocket.sent_messages
        
        # Should have received the queued messages (marked as recovered)
        assert len(recovered_messages) >= len(failed_messages), f"Should recover at least {len(failed_messages)} messages"
        
        # Verify messages are marked as recovered
        for recovered_msg in recovered_messages:
            assert recovered_msg.get("recovered") is True, "Recovered messages should be marked"
            assert "original_failure" in recovered_msg, "Should include original failure reason"
        
        # PHASE 9: Test ongoing message delivery after recovery
        post_recovery_message = {
            "type": "agent_completed",
            "data": {"agent": "recovery_test", "status": "completed", "post_recovery": True}
        }
        
        await websocket_manager.emit_critical_event(
            user_context.user_id,
            post_recovery_message["type"],
            post_recovery_message["data"]
        )
        
        # Should be delivered immediately (not queued)
        latest_messages = recovery_websocket.sent_messages
        last_message = latest_messages[-1]
        assert last_message["type"] == post_recovery_message["type"], "New messages should be delivered immediately"
        assert last_message["data"]["post_recovery"] is True, "Post-recovery message should be delivered"
        assert last_message.get("recovered") is not True, "New messages should not be marked as recovered"
        
        # PHASE 10: Verify system health after recovery
        final_error_stats = websocket_manager.get_error_statistics()
        assert websocket_manager.is_connection_active(user_context.user_id), "User should have active connection"
        
        # Clean up
        await agent_registry.cleanup_user_session(user_context.user_id)
        await websocket_manager.remove_connection(recovery_connection.connection_id)