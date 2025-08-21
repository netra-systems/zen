"""
Agent service thread operations tests.

Tests WebSocket message handling for thread operations including
history, creation, switching, deletion, and listing.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from unittest.mock import AsyncMock

# Add project root to path

from netra_backend.tests.helpers.test_agent_orchestration_pytest_fixtures import agent_service, mock_supervisor
from netra_backend.tests.helpers.test_agent_orchestration_assertions import (

# Add project root to path
    setup_websocket_message, assert_thread_operations_handled
)


class TestAgentServiceThreadOperations:
    """Test WebSocket message handling for thread operations."""
    async def test_thread_history_handling(self, agent_service):
        """Test thread history message handling."""
        user_id = "user_history"
        message = setup_websocket_message("get_thread_history", {})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_thread_history.assert_called_with(user_id, None)
    async def test_create_thread_handling(self, agent_service):
        """Test create thread message handling."""
        user_id = "user_create"
        payload = {"name": "New Thread"}
        message = setup_websocket_message("create_thread", payload)
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_create_thread.assert_called_with(user_id, payload, None)
    async def test_switch_thread_handling(self, agent_service):
        """Test switch thread message handling."""
        user_id = "user_switch"
        payload = {"thread_id": "thread_123"}
        message = setup_websocket_message("switch_thread", payload)
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_switch_thread.assert_called_with(user_id, payload, None)
    async def test_delete_thread_handling(self, agent_service):
        """Test delete thread message handling."""
        user_id = "user_delete"
        payload = {"thread_id": "thread_456"}
        message = setup_websocket_message("delete_thread", payload)
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_delete_thread.assert_called_with(user_id, payload, None)
    async def test_list_threads_handling(self, agent_service):
        """Test list threads message handling."""
        user_id = "user_list"
        message = setup_websocket_message("list_threads", {})
        
        await agent_service.handle_websocket_message(user_id, message)
        
        agent_service.message_handler.handle_list_threads.assert_called_with(user_id, None)
    async def test_all_thread_operations_batch(self, agent_service):
        """Test all thread operations in batch."""
        user_id = "user_batch"
        
        operations = [
            ("get_thread_history", {}),
            ("create_thread", {"name": "New Thread"}),
            ("switch_thread", {"thread_id": "thread_123"}),
            ("delete_thread", {"thread_id": "thread_456"}),
            ("list_threads", {})
        ]
        
        for message_type, payload in operations:
            message = setup_websocket_message(message_type, payload)
            await agent_service.handle_websocket_message(user_id, message)
        
        self._verify_all_handlers_called(agent_service, user_id, operations)
    
    def _verify_all_handlers_called(self, agent_service, user_id, operations):
        """Verify all thread operation handlers were called."""
        for message_type, payload in operations:
            handler_name = self._get_handler_name(message_type)
            handler_method = getattr(agent_service.message_handler, handler_name)
            
            if message_type in ["get_thread_history", "list_threads"]:
                handler_method.assert_called_with(user_id, None)
            else:
                handler_method.assert_called_with(user_id, payload, None)
    
    def _get_handler_name(self, message_type):
        """Get handler method name for message type."""
        method_map = {
            "get_thread_history": "handle_thread_history",
            "create_thread": "handle_create_thread",
            "switch_thread": "handle_switch_thread", 
            "delete_thread": "handle_delete_thread",
            "list_threads": "handle_list_threads"
        }
        return method_map.get(message_type, f"handle_{message_type}")
    async def test_websocket_message_handling_json_error(self, agent_service):
        """Test WebSocket message handling with JSON decode error."""
        user_id = "user_json_error"
        invalid_message = "invalid json {broken"
        
        # Should handle JSON error gracefully without raising exception
        await agent_service.handle_websocket_message(user_id, invalid_message)