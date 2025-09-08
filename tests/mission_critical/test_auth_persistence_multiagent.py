"""
Mission Critical Test: Authentication Persistence in Multi-Agent Workflows

Tests that authentication context is properly maintained across:
1. Agent handoffs
2. WebSocket reconnections
3. Token refreshes during agent execution
4. Concurrent multi-user agent operations
"""

import asyncio
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestAuthPersistenceMultiAgent:
    """Test suite for authentication persistence across multi-agent workflows."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        return ws
    
    @pytest.fixture
    def valid_token(self):
        """Generate a valid JWT token for testing."""
        payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")
    
    @pytest.fixture
    def user_contexts(self, valid_token) -> Dict[str, UserExecutionContext]:
        """Create multiple user contexts for testing concurrent operations."""
        contexts = {}
        for i in range(3):
            user_id = f"user_{i}"
            contexts[user_id] = UserExecutionContext(
                user_id=user_id,
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                websocket_connection_id=f"ws_conn_{i}",
                metadata={"auth_token": valid_token}
            )
        return contexts
    
    @pytest.mark.asyncio
    async def test_auth_persistence_during_agent_handoff(self, mock_websocket, valid_token):
        """Test that auth context persists when handing off between agents."""
        # Setup
        user_id = "test-user-123"
        thread_id = "thread-456"
        
        # Create initial context with auth
        initial_context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id="run-001",
            websocket_connection_id="ws-001",
            metadata={"auth_token": valid_token}
        )
        
        # Import and test the agent handler pattern without triggering singleton
        with patch('netra_backend.app.websocket_core.agent_handler.AgentMessageHandler') as MockHandler:
            # Simulate agent handoff
            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_supervisor:
                mock_supervisor.return_value = AsyncMock()
                
                handler = MockHandler.return_value
                handler._handle_message_v3_clean = AsyncMock(return_value=True)
            
            # First agent message
            message1 = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={
                    "thread_id": thread_id,
                    "agent_name": "data_agent",
                    "content": "Analyze data"
                },
                thread_id=thread_id
            )
            
            # Process with v3 pattern enabled
            with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
                result1 = await handler._handle_message_v3_clean(user_id, mock_websocket, message1)
            
            assert result1 is True
            
            # Verify supervisor was created with proper context
            mock_supervisor.assert_called()
            call_args = mock_supervisor.call_args
            ws_context = call_args.kwargs['context']
            assert ws_context.user_id == user_id
            assert ws_context.thread_id == thread_id
            
            # Second agent message (handoff)
            message2 = WebSocketMessage(
                type=MessageType.USER_MESSAGE,
                payload={
                    "thread_id": thread_id,
                    "content": "Now optimize the results"
                },
                thread_id=thread_id
            )
            
            result2 = await handler._handle_message_v3_clean(user_id, mock_websocket, message2)
            assert result2 is True
            
            # Verify auth context was preserved
            second_call_args = mock_supervisor.call_args
            ws_context2 = second_call_args.kwargs['context']
            assert ws_context2.user_id == user_id  # Same user
            assert ws_context2.thread_id == thread_id  # Same thread
    
    @pytest.mark.asyncio
    async def test_concurrent_users_auth_isolation(self, mock_websocket, user_contexts):
        """Test that concurrent users maintain separate auth contexts."""
        results = {}
        
        async def process_user_message(user_id: str, context: UserExecutionContext):
            """Process a message for a specific user."""
            handler = AgentMessageHandler(AsyncMock(), mock_websocket)
            
            message = WebSocketMessage(
                type=MessageType.START_AGENT,
                payload={
                    "thread_id": context.thread_id,
                    "agent_name": "test_agent",
                    "content": f"Process for {user_id}"
                },
                thread_id=context.thread_id
            )
            
            with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_sup:
                mock_sup.return_value = AsyncMock()
                
                with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
                    result = await handler._handle_message_v3_clean(user_id, mock_websocket, message)
                
                # Capture the context used
                call_args = mock_sup.call_args
                ws_context = call_args.kwargs['context']
                results[user_id] = {
                    'success': result,
                    'context_user_id': ws_context.user_id,
                    'context_thread_id': ws_context.thread_id
                }
        
        # Process all users concurrently
        tasks = [
            process_user_message(user_id, context)
            for user_id, context in user_contexts.items()
        ]
        await asyncio.gather(*tasks)
        
        # Verify each user maintained separate context
        for user_id, context in user_contexts.items():
            assert results[user_id]['success'] is True
            assert results[user_id]['context_user_id'] == user_id
            assert results[user_id]['context_thread_id'] == context.thread_id
        
        # Verify no cross-contamination
        user_ids = list(user_contexts.keys())
        for i, user_id in enumerate(user_ids):
            for j, other_user_id in enumerate(user_ids):
                if i != j:
                    assert results[user_id]['context_user_id'] != results[other_user_id]['context_user_id']
                    assert results[user_id]['context_thread_id'] != results[other_user_id]['context_thread_id']
    
    @pytest.mark.asyncio
    async def test_token_refresh_during_agent_execution(self, mock_websocket):
        """Test that token refresh during agent execution maintains context."""
        user_id = "refresh-test-user"
        thread_id = "refresh-thread"
        
        # Create token that will expire soon
        soon_expiry = datetime.utcnow() + timedelta(seconds=30)
        expiring_token = jwt.encode({
            "sub": user_id,
            "exp": soon_expiry,
            "iat": datetime.utcnow()
        }, "test-secret", algorithm="HS256")
        
        # New refreshed token
        refreshed_token = jwt.encode({
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(hours=1),
            "iat": datetime.utcnow()
        }, "test-secret", algorithm="HS256")
        
        handler = AgentMessageHandler(AsyncMock(), mock_websocket)
        
        # Start agent execution
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "thread_id": thread_id,
                "agent_name": "long_running_agent",
                "content": "Process large dataset"
            },
            thread_id=thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_sup:
            mock_sup.return_value = AsyncMock()
            
            # Simulate token refresh mid-execution
            async def simulate_refresh(*args, **kwargs):
                # Return refreshed token after a delay
                await asyncio.sleep(0.1)
                return refreshed_token
            
            with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
                with patch('netra_backend.app.auth.unified_auth_service.refreshToken', side_effect=simulate_refresh):
                    result = await handler._handle_message_v3_clean(user_id, mock_websocket, message)
            
            assert result is True
            
            # Verify context maintained user identity
            call_args = mock_sup.call_args
            ws_context = call_args.kwargs['context']
            assert ws_context.user_id == user_id
            assert ws_context.thread_id == thread_id
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_preserves_auth(self, mock_websocket, valid_token):
        """Test that WebSocket reconnection preserves authentication state."""
        user_id = "reconnect-user"
        thread_id = "reconnect-thread"
        connection_id_1 = "ws-conn-001"
        connection_id_2 = "ws-conn-002"
        
        handler = AgentMessageHandler(AsyncMock(), mock_websocket)
        
        # First connection
        message1 = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "thread_id": thread_id,
                "agent_name": "test_agent",
                "content": "Start processing"
            },
            thread_id=thread_id
        )
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_websocket_scoped_supervisor') as mock_sup:
            mock_sup.return_value = AsyncMock()
            
            with patch.dict('os.environ', {'USE_WEBSOCKET_SUPERVISOR_V3': 'true'}):
                # First connection
                with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr:
                    mock_ws_mgr.return_value.get_connection_id_by_websocket.return_value = connection_id_1
                    result1 = await handler._handle_message_v3_clean(user_id, mock_websocket, message1)
                
                assert result1 is True
                
                # Simulate disconnection and reconnection
                await asyncio.sleep(0.1)
                
                # Second connection (after reconnect)
                message2 = WebSocketMessage(
                    type=MessageType.USER_MESSAGE,
                    payload={
                        "thread_id": thread_id,
                        "content": "Continue processing after reconnect"
                    },
                    thread_id=thread_id
                )
                
                with patch('netra_backend.app.websocket_core.get_websocket_manager') as mock_ws_mgr:
                    mock_ws_mgr.return_value.get_connection_id_by_websocket.return_value = connection_id_2
                    result2 = await handler._handle_message_v3_clean(user_id, mock_websocket, message2)
                
                assert result2 is True
                
                # Verify auth context preserved across reconnection
                calls = mock_sup.call_args_list
                assert len(calls) == 2
                
                # Check both connections maintained same user/thread
                for call in calls:
                    ws_context = call.kwargs['context']
                    assert ws_context.user_id == user_id
                    assert ws_context.thread_id == thread_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])