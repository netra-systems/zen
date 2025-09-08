"""
Focused Security Unit Tests for WebSocketManagerFactory - Critical Isolation Tests

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent user message cross-contamination in multi-user AI chat
- Value Impact: CRITICAL SECURITY - Ensures user isolation in WebSocket communications
- Strategic Impact: Foundation security for real-time AI interactions

MISSION CRITICAL: These focused tests validate the most critical security requirements:
1. Factory creates isolated manager instances per user
2. No message cross-contamination between users  
3. User context validation prevents connection hijacking
4. Proper cleanup prevents memory leaks
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock

# Import the base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the target classes
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    FactoryInitializationError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection


class TestWebSocketSecurityFocused(SSotAsyncTestCase):
    """
    Focused security tests for WebSocket factory isolation.
    
    CRITICAL: These tests validate the core security requirements.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.factory = WebSocketManagerFactory(max_managers_per_user=3)
    
    def teardown_method(self, method=None):
        """Teardown after each test method."""
        if hasattr(self, 'factory'):
            asyncio.run(self.factory.shutdown())
        super().teardown_method(method)
    
    def _create_user_context(self, user_id: str = None, websocket_client_id: str = None) -> UserExecutionContext:
        """Create test UserExecutionContext."""
        if user_id is None:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        if websocket_client_id is None:
            websocket_client_id = f"ws_client_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            websocket_client_id=websocket_client_id
        )
    
    def _create_mock_connection(self, user_id: str, connection_id: str = None) -> WebSocketConnection:
        """Create mock WebSocket connection."""
        if connection_id is None:
            connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        return WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": True}
        )
    
    # === FACTORY ISOLATION TESTS ===
    
    def test_factory_initialization_creates_isolated_state(self):
        """Test factory creates isolated state containers."""
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0
        assert self.factory.max_managers_per_user == 3
        assert self.factory._factory_lock is not None
    
    @pytest.mark.asyncio
    async def test_factory_creates_isolated_managers_per_user(self):
        """CRITICAL: Test factory creates isolated managers for different users."""
        # Create contexts for two users
        user1_context = self._create_user_context("user1")
        user2_context = self._create_user_context("user2")
        
        # Create managers
        manager1 = await self.factory.create_manager(user1_context)
        manager2 = await self.factory.create_manager(user2_context)
        
        # Verify managers are separate instances
        assert manager1 is not manager2
        assert manager1.user_context.user_id == "user1"
        assert manager2.user_context.user_id == "user2"
        
        # Verify internal state isolation
        assert manager1._connections is not manager2._connections
        assert manager1._connection_ids is not manager2._connection_ids
    
    @pytest.mark.asyncio
    async def test_factory_returns_same_manager_for_same_context(self):
        """Test factory returns existing manager for identical context."""
        user_context = self._create_user_context("same_user")
        
        # Create manager twice with same context
        manager1 = await self.factory.create_manager(user_context)
        manager2 = await self.factory.create_manager(user_context)
        
        # Should return same instance
        assert manager1 is manager2
    
    # === USER ISOLATION SECURITY TESTS ===
    
    @pytest.mark.asyncio
    async def test_manager_validates_connection_user_ownership(self):
        """CRITICAL: Test manager validates connection belongs to correct user."""
        user_context = self._create_user_context("legitimate_user")
        manager = await self.factory.create_manager(user_context)
        
        # Create connection for different user
        wrong_user_connection = self._create_mock_connection("attacker_user")
        
        # Should raise security violation
        with pytest.raises(ValueError, match="does not match manager user_id"):
            await manager.add_connection(wrong_user_connection)
        
        # Verify no state contamination
        assert len(manager._connections) == 0
    
    @pytest.mark.asyncio
    async def test_manager_accepts_correct_user_connections(self):
        """Test manager accepts connections for correct user."""
        user_context = self._create_user_context("correct_user")
        manager = await self.factory.create_manager(user_context)
        
        # Create connection for correct user
        correct_connection = self._create_mock_connection("correct_user")
        
        # Should accept without error
        await manager.add_connection(correct_connection)
        
        # Verify connection added
        assert correct_connection.connection_id in manager._connections
        assert len(manager._connections) == 1
    
    # === MESSAGE ISOLATION TESTS ===
    
    @pytest.mark.asyncio
    async def test_messages_only_route_to_user_connections(self):
        """CRITICAL: Test messages only route to user's own connections."""
        # Setup two users with managers and connections
        user1_context = self._create_user_context("message_user1")
        user2_context = self._create_user_context("message_user2")
        
        manager1 = await self.factory.create_manager(user1_context)
        manager2 = await self.factory.create_manager(user2_context)
        
        conn1 = self._create_mock_connection("message_user1", "conn1")
        conn2 = self._create_mock_connection("message_user2", "conn2")
        
        await manager1.add_connection(conn1)
        await manager2.add_connection(conn2)
        
        # Send message to user1
        message = {"type": "test", "data": "user1_secret"}
        await manager1.send_to_user(message)
        
        # Verify only user1's connection received message
        conn1.websocket.send_json.assert_called_once()
        conn2.websocket.send_json.assert_not_called()
        
        # Verify message content
        sent_message = conn1.websocket.send_json.call_args[0][0]
        assert sent_message["data"] == "user1_secret"
    
    @pytest.mark.asyncio 
    async def test_concurrent_messages_maintain_isolation(self):
        """CRITICAL: Test concurrent messages maintain user isolation."""
        # Setup multiple users
        users = ["concurrent_user1", "concurrent_user2", "concurrent_user3"]
        managers = {}
        connections = {}
        
        for user_id in users:
            context = self._create_user_context(user_id)
            manager = await self.factory.create_manager(context)
            connection = self._create_mock_connection(user_id)
            
            await manager.add_connection(connection)
            
            managers[user_id] = manager
            connections[user_id] = connection
        
        # Send messages concurrently
        async def send_user_message(user_id: str):
            message = {"type": "concurrent", "secret": f"{user_id}_secret"}
            await managers[user_id].send_to_user(message)
        
        # Execute concurrent sends
        await asyncio.gather(*[send_user_message(user_id) for user_id in users])
        
        # Verify each user only received their own message
        for user_id in users:
            conn = connections[user_id]
            conn.websocket.send_json.assert_called_once()
            
            # Get sent message and verify it's user-specific
            sent_message = conn.websocket.send_json.call_args[0][0]
            assert sent_message["secret"] == f"{user_id}_secret"
            
            # Verify no other user's data is present
            message_str = str(sent_message)
            for other_user in users:
                if other_user != user_id:
                    assert f"{other_user}_secret" not in message_str
    
    # === CLEANUP AND RESOURCE MANAGEMENT TESTS ===
    
    @pytest.mark.asyncio
    async def test_manager_cleanup_isolates_resources(self):
        """Test manager cleanup properly isolates resources."""
        user_context = self._create_user_context("cleanup_user")
        manager = await self.factory.create_manager(user_context)
        
        # Add connection
        connection = self._create_mock_connection("cleanup_user")
        await manager.add_connection(connection)
        
        # Verify connection exists
        assert len(manager._connections) == 1
        
        # Cleanup manager
        isolation_key = self.factory._generate_isolation_key(user_context)
        result = await self.factory.cleanup_manager(isolation_key)
        
        # Verify cleanup
        assert result is True
        assert not manager._is_active
        assert len(manager._connections) == 0
    
    @pytest.mark.asyncio
    async def test_factory_shutdown_cleans_all_resources(self):
        """Test factory shutdown cleans all resources."""
        # Create multiple managers
        contexts = []
        for i in range(3):
            context = self._create_user_context(f"shutdown_user_{i}")
            contexts.append(context)
            await self.factory.create_manager(context)
        
        # Verify managers created
        assert len(self.factory._active_managers) == 3
        
        # Shutdown factory
        await self.factory.shutdown()
        
        # Verify complete cleanup
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0
    
    # === RESOURCE LIMIT TESTS ===
    
    @pytest.mark.asyncio
    async def test_factory_enforces_resource_limits(self):
        """Test factory enforces maximum managers per user."""
        user_id = "resource_test_user"
        
        # Create managers up to limit
        for i in range(self.factory.max_managers_per_user):
            context = self._create_user_context(user_id, f"ws_{i}")
            manager = await self.factory.create_manager(context)
            assert manager is not None
        
        # Attempt to exceed limit
        excess_context = self._create_user_context(user_id, "ws_excess")
        with pytest.raises(RuntimeError, match="maximum number"):
            await self.factory.create_manager(excess_context)
    
    # === ERROR HANDLING TESTS ===
    
    @pytest.mark.asyncio
    async def test_manager_creation_validates_context_type(self):
        """Test manager creation validates UserExecutionContext type."""
        # Invalid context type should raise error
        with pytest.raises(ValueError, match="must be a UserExecutionContext"):
            await self.factory.create_manager("invalid_context")
        
        with pytest.raises(ValueError, match="must be a UserExecutionContext"):
            await self.factory.create_manager({"user_id": "test"})
    
    def test_manager_initialization_validates_context(self):
        """Test IsolatedWebSocketManager validates context on initialization."""
        # Invalid context should raise error
        with pytest.raises(ValueError, match="must be a UserExecutionContext"):
            IsolatedWebSocketManager("not_a_context")
    
    # === COMPREHENSIVE SECURITY VALIDATION ===
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_isolation(self):
        """COMPREHENSIVE: Test complete security isolation across all operations."""
        # Setup multiple users with full context
        security_users = ["alice", "bob", "charlie"]
        user_data = {}
        
        for user_id in security_users:
            context = self._create_user_context(user_id)
            manager = await self.factory.create_manager(context)
            connection = self._create_mock_connection(user_id)
            
            await manager.add_connection(connection)
            
            user_data[user_id] = {
                "context": context,
                "manager": manager,
                "connection": connection
            }
        
        # Test 1: Send different sensitive messages to each user
        sensitive_data = {
            "alice": {"secret": "alice_password_123", "credit_card": "1111-2222-3333-4444"},
            "bob": {"secret": "bob_api_key_xyz", "ssn": "123-45-6789"},
            "charlie": {"secret": "charlie_token_abc", "private": "confidential_data"}
        }
        
        for user_id, data in sensitive_data.items():
            message = {"type": "sensitive", "payload": data}
            await user_data[user_id]["manager"].send_to_user(message)
        
        # Test 2: Verify complete isolation
        for user_id in security_users:
            connection = user_data[user_id]["connection"]
            
            # Each user should have received exactly one message
            assert connection.websocket.send_json.call_count == 1
            
            # Get the message
            sent_message = connection.websocket.send_json.call_args[0][0]
            
            # Verify user only received their own sensitive data
            user_secret = sensitive_data[user_id]["secret"]
            assert user_secret in str(sent_message)
            
            # CRITICAL: Verify no other users' sensitive data is present
            for other_user, other_data in sensitive_data.items():
                if other_user != user_id:
                    other_secret = other_data["secret"]
                    assert other_secret not in str(sent_message), (
                        f"SECURITY BREACH: {user_id} received {other_user}'s sensitive data"
                    )
        
        # Test 3: Verify connection isolation
        for user_id in security_users:
            manager = user_data[user_id]["manager"]
            
            # Manager should only have connections for its user
            connections = manager.get_user_connections()
            for conn_id in connections:
                connection = manager.get_connection(conn_id)
                assert connection.user_id == user_id, (
                    f"SECURITY BREACH: Manager for {user_id} has connection for {connection.user_id}"
                )
            
            # Manager should not access other users' connections
            for other_user in security_users:
                if other_user != user_id:
                    other_connection = user_data[other_user]["connection"]
                    found = manager.get_connection(other_connection.connection_id)
                    assert found is None, (
                        f"SECURITY BREACH: Manager for {user_id} can access {other_user}'s connection"
                    )
        
        print("✅ COMPREHENSIVE SECURITY VALIDATION PASSED - No cross-user contamination detected")


# Helper function for easy test execution
if __name__ == "__main__":
    pytest.main([__file__, "-v"])