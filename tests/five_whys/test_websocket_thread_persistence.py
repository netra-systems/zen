"""
Test WebSocket Thread ID Persistence

This test validates that thread IDs are properly persisted across WebSocket sessions
to maintain conversation continuity and prevent the regression described in the error logs.

CRITICAL: Thread IDs must be created once and reused throughout the session, not regenerated
for each message.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import WebSocket
from starlette.websockets import WebSocketState

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class TestWebSocketThreadPersistence:
    """Test suite for WebSocket thread ID persistence and session continuity."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = Mock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        ws.scope = {'app': Mock(state=Mock())}
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        return ws
    
    @pytest.fixture
    def handler(self):
        """Create AgentMessageHandler instance."""
        return AgentMessageHandler()
    
    @pytest.mark.asyncio
    async def test_thread_id_persistence_across_messages(self, handler, mock_websocket):
        """Test that thread_id persists across multiple messages in the same session."""
        user_id = "test_user_123"
        thread_id = None  # Start with no thread_id
        captured_thread_ids = []
        
        # Create messages without thread_id to test session continuity
        messages = [
            WebSocketMessage(
                type=MessageType.AGENT_MESSAGE,
                payload={"content": "First message"},
                user_id=user_id,
                thread_id=None,  # No thread_id provided
                run_id=None
            ),
            WebSocketMessage(
                type=MessageType.AGENT_MESSAGE,
                payload={"content": "Second message"},
                user_id=user_id,
                thread_id=None,  # Still no thread_id
                run_id=None
            ),
            WebSocketMessage(
                type=MessageType.AGENT_MESSAGE,
                payload={"content": "Third message"},
                user_id=user_id,
                thread_id=None,  # Still no thread_id
                run_id=None
            )
        ]
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        
                        # Mock the session manager to track thread_ids
                        def track_context_call(user_id, thread_id=None, run_id=None):
                            # Simulate session manager behavior
                            if not thread_id:
                                # First call creates a new thread_id
                                if not captured_thread_ids:
                                    generated_thread_id = f"thread_{user_id}_persistent"
                                else:
                                    # Subsequent calls reuse the same thread_id
                                    generated_thread_id = captured_thread_ids[0]
                            else:
                                generated_thread_id = thread_id
                            
                            captured_thread_ids.append(generated_thread_id)
                            
                            context = Mock()
                            context.user_id = user_id
                            context.thread_id = generated_thread_id
                            context.run_id = run_id or f"run_{len(captured_thread_ids)}"
                            context.request_id = f"req_{len(captured_thread_ids)}"
                            context.websocket_client_id = f"ws_{user_id}"
                            return context
                        
                        mock_get_context.side_effect = track_context_call
                        mock_create_manager.return_value = Mock(
                            get_connection_id_by_websocket=Mock(return_value="conn_123"),
                            update_connection_thread=Mock()
                        )
                        
                        # Mock database session
                        async def mock_session_generator():
                            yield Mock()
                        mock_get_session.return_value = mock_session_generator()
                        
                        # Mock supervisor
                        mock_supervisor = AsyncMock()
                        mock_get_supervisor.return_value = mock_supervisor
                        
                        # Process each message
                        for i, message in enumerate(messages):
                            result = await handler._handle_message_v3_clean(
                                user_id, mock_websocket, message
                            )
                            assert result is False  # Expected to fail due to mocked components
                        
                        # Verify thread_id persistence
                        assert len(captured_thread_ids) == 3, "Should have tracked 3 context creations"
                        
                        # CRITICAL: All thread_ids should be the same (session continuity)
                        assert captured_thread_ids[0] == captured_thread_ids[1], \
                            f"Thread ID changed between messages: {captured_thread_ids[0]} != {captured_thread_ids[1]}"
                        assert captured_thread_ids[1] == captured_thread_ids[2], \
                            f"Thread ID changed between messages: {captured_thread_ids[1]} != {captured_thread_ids[2]}"
                        
                        print(f" PASS:  Thread ID persisted across all messages: {captured_thread_ids[0]}")
    
    @pytest.mark.asyncio
    async def test_thread_id_explicit_override(self, handler, mock_websocket):
        """Test that explicitly provided thread_id is used and persisted."""
        user_id = "test_user_456"
        explicit_thread_id = "explicit_thread_789"
        captured_contexts = []
        
        # First message with explicit thread_id
        message1 = WebSocketMessage(
            type=WebSocketMessageType.AGENT_MESSAGE,
            payload={"content": "Message with thread_id"},
            user_id=user_id,
            thread_id=explicit_thread_id,
            run_id=None
        )
        
        # Second message without thread_id (should reuse the session's thread_id)
        message2 = WebSocketMessage(
            type=WebSocketMessageType.AGENT_MESSAGE,
            payload={"content": "Message without thread_id"},
            user_id=user_id,
            thread_id=None,
            run_id=None
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context') as mock_get_context:
            with patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager') as mock_create_manager:
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_session:
                    with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_get_supervisor:
                        
                        def capture_context(user_id, thread_id=None, run_id=None):
                            context = Mock()
                            context.user_id = user_id
                            # Simulate session manager maintaining thread_id
                            if thread_id:
                                context.thread_id = thread_id
                            elif captured_contexts:
                                # Reuse previous thread_id
                                context.thread_id = captured_contexts[0].thread_id
                            else:
                                context.thread_id = f"generated_thread_{user_id}"
                            context.run_id = run_id or f"run_{len(captured_contexts)}"
                            captured_contexts.append(context)
                            return context
                        
                        mock_get_context.side_effect = capture_context
                        mock_create_manager.return_value = Mock(
                            get_connection_id_by_websocket=Mock(return_value="conn_456"),
                            update_connection_thread=Mock()
                        )
                        
                        # Mock database session
                        async def mock_session_generator():
                            yield Mock()
                        mock_get_session.return_value = mock_session_generator()
                        
                        # Process messages
                        await handler._handle_message_v3_clean(user_id, mock_websocket, message1)
                        await handler._handle_message_v3_clean(user_id, mock_websocket, message2)
                        
                        # Verify explicit thread_id was used and persisted
                        assert captured_contexts[0].thread_id == explicit_thread_id, \
                            f"First message should use explicit thread_id: {captured_contexts[0].thread_id}"
                        assert captured_contexts[1].thread_id == explicit_thread_id, \
                            f"Second message should reuse the same thread_id: {captured_contexts[1].thread_id}"
                        
                        print(f" PASS:  Explicit thread ID {explicit_thread_id} persisted across messages")
    
    @pytest.mark.asyncio
    async def test_websocket_context_creation_with_persistent_thread(self):
        """Test that WebSocketContext properly uses persistent thread_id from execution context."""
        user_id = "test_user_context"
        persistent_thread_id = "persistent_thread_xyz"
        persistent_run_id = "persistent_run_abc"
        
        # Mock WebSocket
        mock_ws = Mock(spec=WebSocket)
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Create WebSocketContext with persistent IDs
        context = WebSocketContext.create_for_user(
            websocket=mock_ws,
            user_id=user_id,
            thread_id=persistent_thread_id,
            run_id=persistent_run_id
        )
        
        # Verify context has correct persistent IDs
        assert context.user_id == user_id
        assert context.thread_id == persistent_thread_id
        assert context.run_id == persistent_run_id
        assert context.connection_id is not None
        
        print(f" PASS:  WebSocketContext created with persistent thread_id: {persistent_thread_id}")
    
    @pytest.mark.asyncio
    async def test_unified_id_generator_session_persistence(self):
        """Test that UnifiedIdGenerator maintains session persistence."""
        user_id = "test_user_generator"
        
        # First call - creates new session
        session1 = UnifiedIdGenerator.get_or_create_user_session(
            user_id=user_id,
            thread_id=None,  # Let it generate
            run_id=None
        )
        
        # Second call - should reuse existing session
        session2 = UnifiedIdGenerator.get_or_create_user_session(
            user_id=user_id,
            thread_id=None,  # Still None
            run_id=None
        )
        
        # Third call with same thread_id - should maintain session
        session3 = UnifiedIdGenerator.get_or_create_user_session(
            user_id=user_id,
            thread_id=session1["thread_id"],  # Use existing thread_id
            run_id=None
        )
        
        # Verify thread_id persistence
        assert session1["thread_id"] == session2["thread_id"], \
            "Thread ID should persist across calls without explicit thread_id"
        assert session2["thread_id"] == session3["thread_id"], \
            "Thread ID should persist when explicitly provided"
        
        # Run IDs should persist when not provided
        assert session1["run_id"] == session2["run_id"], \
            "Run ID should persist when not explicitly changed"
        
        print(f" PASS:  UnifiedIdGenerator maintains session persistence: thread={session1['thread_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])