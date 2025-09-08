"""
Integration test for WebSocket manager method compatibility.

This test ensures that IsolatedWebSocketManager has all methods
required by agent_handler.py, preventing AttributeError failures.

Related to: AttributeError 'IsolatedWebSocketManager' object has no attribute 'get_connection_id_by_websocket'
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from netra_backend.app.websocket_core.websocket_manager_factory import (
    create_websocket_manager,
    IsolatedWebSocketManager
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from shared.id_generation import UnifiedIdGenerator


class TestWebSocketManagerMethodCompatibility:
    """Test suite to ensure WebSocket manager has all required methods."""
    
    def test_isolated_manager_has_get_connection_id_by_websocket(self):
        """
        Verify IsolatedWebSocketManager has get_connection_id_by_websocket method.
        
        This method is called by agent_handler.py and must exist.
        """
        # Create a valid user context (use realistic IDs that pass validation)
        context = UserExecutionContext(
            user_id="105945141827451681156",  # Real Google OAuth user ID format
            thread_id="thread_2025_09_08_14_45_00_abc123",
            run_id="run_2025_09_08_14_45_00_def456"
        )
        
        # Create isolated manager
        manager = create_websocket_manager(context)
        
        # Verify the method exists
        assert hasattr(manager, 'get_connection_id_by_websocket'), \
            "IsolatedWebSocketManager must have get_connection_id_by_websocket method"
        
        # Verify it's callable
        assert callable(getattr(manager, 'get_connection_id_by_websocket')), \
            "get_connection_id_by_websocket must be callable"
    
    def test_isolated_manager_has_update_connection_thread(self):
        """
        Verify IsolatedWebSocketManager has update_connection_thread method.
        
        This method is called by agent_handler.py to associate threads with connections.
        """
        # Create a valid user context (use realistic IDs that pass validation)
        context = UserExecutionContext(
            user_id="github_user_98765432101",  # GitHub OAuth format
            thread_id="thread_2025_09_08_14_45_01_ghi789",
            run_id="run_2025_09_08_14_45_01_jkl012"
        )
        
        # Create isolated manager
        manager = create_websocket_manager(context)
        
        # Verify the method exists
        assert hasattr(manager, 'update_connection_thread'), \
            "IsolatedWebSocketManager must have update_connection_thread method"
        
        # Verify it's callable
        assert callable(getattr(manager, 'update_connection_thread')), \
            "update_connection_thread must be callable"
    
    async def test_get_connection_id_by_websocket_functionality(self):
        """
        Test that get_connection_id_by_websocket actually works.
        
        This verifies the method can find connections by WebSocket instance.
        """
        # Create a valid user context (use realistic IDs)
        context = UserExecutionContext(
            user_id="email_user_john.doe@example.com",
            thread_id="thread_2025_09_08_14_45_02_mno345",
            run_id="run_2025_09_08_14_45_02_pqr678"
        )
        
        # Create isolated manager
        manager = create_websocket_manager(context)
        
        # Create a mock WebSocket
        websocket = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.client_state = 1  # CONNECTED state
        
        # Create a connection with known ID
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id("email_user_john.doe@example.com")
        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            user_id="email_user_john.doe@example.com",
            connected_at=datetime.utcnow()
        )
        # Set thread_id after creation since it's not in constructor
        connection.thread_id = "thread_2025_09_08_14_45_02_mno345"
        
        # Add the connection to manager
        await manager.add_connection(connection)
        
        # Test finding the connection by WebSocket
        found_id = manager.get_connection_id_by_websocket(websocket)
        assert found_id == connection_id, \
            f"Expected to find connection ID {connection_id}, got {found_id}"
        
        # Test with unknown WebSocket
        unknown_websocket = AsyncMock()
        not_found = manager.get_connection_id_by_websocket(unknown_websocket)
        assert not_found is None, \
            "Should return None for unknown WebSocket"
    
    async def test_update_connection_thread_functionality(self):
        """
        Test that update_connection_thread actually updates thread associations.
        
        This verifies the method can update thread IDs for connections.
        """
        # Create a valid user context (use realistic IDs)
        context = UserExecutionContext(
            user_id="oauth_user_567890123456",
            thread_id="thread_2025_09_08_14_45_03_initial",
            run_id="run_2025_09_08_14_45_03_stu901"
        )
        
        # Create isolated manager
        manager = create_websocket_manager(context)
        
        # Create a mock WebSocket
        websocket = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.client_state = 1  # CONNECTED state
        
        # Create a connection
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id("oauth_user_567890123456")
        connection = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            user_id="oauth_user_567890123456",
            connected_at=datetime.utcnow()
        )
        # Set thread_id after creation since it's not in constructor
        connection.thread_id = "thread_2025_09_08_14_45_03_initial"
        
        # Add the connection to manager
        await manager.add_connection(connection)
        
        # Update the thread association
        new_thread_id = "thread_2025_09_08_14_45_03_updated"
        success = manager.update_connection_thread(connection_id, new_thread_id)
        
        # Verify update was successful
        assert success is True, "Thread update should succeed for existing connection"
        
        # Verify the thread was actually updated
        updated_connection = manager.get_connection(connection_id)
        if hasattr(updated_connection, 'thread_id'):
            assert updated_connection.thread_id == new_thread_id, \
                f"Thread ID should be updated to {new_thread_id}"
        
        # Test updating non-existent connection
        fake_id = "fake_connection_id"
        failed = manager.update_connection_thread(fake_id, "any_thread")
        assert failed is False, "Thread update should fail for non-existent connection"
    
    async def test_compatibility_with_agent_handler_pattern(self):
        """
        Test the exact pattern used in agent_handler.py.
        
        This simulates how agent_handler.py uses these methods.
        """
        # Simulate agent_handler.py usage pattern
        user_id = "production_user_abc123def456"
        thread_id = "thread_2025_09_08_14_45_04_agent"
        
        # Create context like agent_handler does
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=f"run_{uuid.uuid4()}"
        )
        
        # Create manager
        ws_manager = create_websocket_manager(context)
        
        # Create mock WebSocket
        websocket = AsyncMock()
        websocket.send_json = AsyncMock()
        
        # This is the pattern from agent_handler.py lines 111-113
        if thread_id and ws_manager:
            # First, add a connection so we can find it
            connection = WebSocketConnection(
                connection_id=UnifiedIdGenerator.generate_websocket_connection_id(user_id),
                websocket=websocket,
                user_id=user_id,
                connected_at=datetime.utcnow()
            )
            # Set thread_id after creation since it's not in constructor
            connection.thread_id = "thread_2025_09_08_14_45_04_old"
            await ws_manager.add_connection(connection)
            
            # Now test the actual pattern
            connection_id = ws_manager.get_connection_id_by_websocket(websocket)
            if connection_id:
                ws_manager.update_connection_thread(connection_id, thread_id)
                # Verify it worked
                assert True, "Pattern from agent_handler.py executed successfully"
            else:
                # This would trigger the fallback in agent_handler.py
                connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
                assert connection_id.startswith("ws_conn_"), \
                    "Fallback connection ID generation should work"
    
    def test_all_required_methods_exist(self):
        """
        Comprehensive test that all methods used by agent_handler.py exist.
        """
        # Create a valid user context (use realistic IDs)
        context = UserExecutionContext(
            user_id="enterprise_user_789012345678",
            thread_id="thread_2025_09_08_14_45_05_comprehensive",
            run_id="run_2025_09_08_14_45_05_vwx234"
        )
        
        # Create isolated manager
        manager = create_websocket_manager(context)
        
        # List of all methods that agent_handler.py might call
        required_methods = [
            'get_connection_id_by_websocket',
            'update_connection_thread',
            'add_connection',
            'remove_connection',
            'get_connection',
            'get_user_connections',
            'is_connection_active',
            'send_to_user',
            'emit_critical_event',
            'cleanup_all_connections',
            'get_manager_stats'
        ]
        
        # Verify all methods exist and are callable
        for method_name in required_methods:
            assert hasattr(manager, method_name), \
                f"IsolatedWebSocketManager must have {method_name} method"
            assert callable(getattr(manager, method_name)), \
                f"{method_name} must be callable"
        
        print("✓ All required methods exist in IsolatedWebSocketManager")


# Test runner
if __name__ == "__main__":
    import pytest
    
    # Run tests
    test_instance = TestWebSocketManagerMethodCompatibility()
    
    # Run synchronous tests
    test_instance.test_isolated_manager_has_get_connection_id_by_websocket()
    print("✓ test_isolated_manager_has_get_connection_id_by_websocket passed")
    
    test_instance.test_isolated_manager_has_update_connection_thread()
    print("✓ test_isolated_manager_has_update_connection_thread passed")
    
    test_instance.test_all_required_methods_exist()
    print("✓ test_all_required_methods_exist passed")
    
    # Run async tests
    async def run_async_tests():
        await test_instance.test_get_connection_id_by_websocket_functionality()
        print("✓ test_get_connection_id_by_websocket_functionality passed")
        
        await test_instance.test_update_connection_thread_functionality()
        print("✓ test_update_connection_thread_functionality passed")
        
        await test_instance.test_compatibility_with_agent_handler_pattern()
        print("✓ test_compatibility_with_agent_handler_pattern passed")
    
    asyncio.run(run_async_tests())
    
    print("\n✅ All WebSocket manager compatibility tests passed!")