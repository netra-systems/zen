"""Test thread loading and WebSocket room management regression.

This test ensures that:
1. Users join thread rooms when sending messages with thread_id
2. switch_thread messages properly manage room membership
3. Thread messages are properly broadcast to room members
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment


import pytest

try:
    from netra_backend.app.services.message_handlers import MessageHandlerService
    from netra_backend.app.services.thread_service import ThreadService
    from netra_backend.app.websocket_core import get_websocket_manager as get_unified_manager
except ImportError:
    pytest.skip("Required modules have been removed or have missing dependencies", allow_module_level=True)
manager = get_unified_manager()

@pytest.mark.asyncio
async def test_user_joins_thread_room_on_message():
    """Test that users join thread room when sending message with thread_id."""
    # Setup
    # Mock: Generic component isolation for controlled unit testing
    supervisor_mock = MagicNone  # TODO: Use real service instance
    thread_service = ThreadService()
    handler = MessageHandlerService(supervisor_mock, thread_service)
    
    user_id = "test-user-123"
    thread_id = "test-thread-456"
    payload = {
        "text": "Test message",
        "references": [],
        "thread_id": thread_id
    }
    
    # Mock database session and thread
    # Mock: Session isolation for controlled testing without external state
    db_session = AsyncNone  # TODO: Use real service instance
    # Mock: Service component isolation for predictable testing behavior
    thread_mock = MagicMock(id=thread_id)
    
    # Mock the thread service methods
    with patch.object(handler, '_setup_thread_and_run', return_value=(thread_mock, None)):
        with patch.object(handler, '_process_user_message', return_value=None):
            with patch.object(manager.broadcasting, 'join_room') as join_room_mock:
                # Execute
                await handler.handle_user_message(user_id, payload, db_session)
                
                # Verify room joining was called
                join_room_mock.assert_called_once_with(user_id, thread_id)
@pytest.mark.asyncio
async def test_switch_thread_manages_room_membership():
    """Test that switch_thread properly manages room membership."""
    # Setup
    # Mock: Generic component isolation for controlled unit testing
    supervisor_mock = MagicNone  # TODO: Use real service instance
    thread_service = ThreadService()
    handler = MessageHandlerService(supervisor_mock, thread_service)
    
    user_id = "test-user-123"
    new_thread_id = "new-thread-789"
    payload = {"thread_id": new_thread_id}
    
    # Mock broadcasting methods
    with patch.object(manager.broadcasting, 'leave_all_rooms') as leave_mock:
        with patch.object(manager.broadcasting, 'join_room') as join_mock:
            # Execute
            await handler.handle_switch_thread(user_id, payload, None)
            
            # Verify room management
            leave_mock.assert_called_once_with(user_id)
            join_mock.assert_called_once_with(user_id, new_thread_id)
@pytest.mark.asyncio
async def test_switch_thread_requires_thread_id():
    """Test that switch_thread validates thread_id is provided."""
    # Setup
    # Mock: Generic component isolation for controlled unit testing
    supervisor_mock = MagicNone  # TODO: Use real service instance
    thread_service = ThreadService()
    handler = MessageHandlerService(supervisor_mock, thread_service)
    
    user_id = "test-user-123"
    payload = {}  # Missing thread_id
    
    # Mock send_error
    with patch.object(manager, 'send_error') as error_mock:
        # Execute
        await handler.handle_switch_thread(user_id, payload, None)
        
        # Verify error was sent
        error_mock.assert_called_once_with(user_id, "Thread ID required")
@pytest.mark.asyncio
async def test_websocket_broadcasts_to_thread_room():
    """Test that WebSocket messages are broadcast to thread room members."""
    thread_id = "test-thread-123"
    user1_id = "user-1"
    user2_id = "user-2"
    
    # Mock room manager to return users in room
    with patch.object(manager.core.room_manager, 'get_room_connections', 
                     return_value=[user1_id, user2_id]):
        with patch.object(manager.broadcasting, '_send_to_single_user', return_value=True) as send_mock:
            # Execute broadcast with valid message type
            message = {"type": "agent_update", "payload": {"message": "test message"}}
            result = await manager.send_to_thread(thread_id, message)
            
            # Verify both users received message
            assert result is True
            assert send_mock.call_count == 2
@pytest.mark.asyncio
async def test_thread_room_isolation():
    """Test that messages to one thread don't reach users in other threads."""
    thread1_id = "thread-1"
    thread2_id = "thread-2"
    user1_id = "user-1"
    user2_id = "user-2"
    
    # Mock room manager - user1 in thread1, user2 in thread2
    async def get_connections(room_id):
        if room_id == thread1_id:
            return [user1_id]
        elif room_id == thread2_id:
            return [user2_id]
        return []
    
    with patch.object(manager.core.room_manager, 'get_room_connections', 
                     side_effect=get_connections):
        with patch.object(manager.broadcasting, '_send_to_single_user', return_value=True) as send_mock:
            # Send to thread1 with valid message type
            message = {"type": "agent_update", "payload": {"message": "thread1 message"}}
            await manager.send_to_thread(thread1_id, message)
            
            # Verify only user1 received message
            assert send_mock.call_count == 1
            # Check the user_id argument (first argument to _send_to_single_user)
            assert send_mock.call_args[0][0] == user1_id