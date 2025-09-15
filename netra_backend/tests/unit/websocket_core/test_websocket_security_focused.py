"""
Focused Security Unit Tests for WebSocketManager - Critical Isolation Tests

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
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.canonical_imports import FactoryInitializationError
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
        self.factory = WebSocketManager(max_managers_per_user=3)

    def teardown_method(self, method=None):
        """Teardown after each test method."""
        if hasattr(self, 'factory'):
            asyncio.run(self.factory.shutdown())
        super().teardown_method(method)

    def _create_user_context(self, user_id: str=None, websocket_client_id: str=None) -> UserExecutionContext:
        """Create test UserExecutionContext."""
        if user_id is None:
            user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        if websocket_client_id is None:
            websocket_client_id = f'ws_client_{uuid.uuid4().hex[:8]}'
        return UserExecutionContext(user_id=user_id, thread_id=f'thread_{uuid.uuid4().hex[:8]}', run_id=f'run_{uuid.uuid4().hex[:8]}', request_id=f'req_{uuid.uuid4().hex[:8]}', websocket_client_id=websocket_client_id)

    def _create_mock_connection(self, user_id: str, connection_id: str=None) -> WebSocketConnection:
        """Create mock WebSocket connection."""
        if connection_id is None:
            connection_id = f'conn_{uuid.uuid4().hex[:8]}'
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        return WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=mock_websocket, connected_at=datetime.now(timezone.utc), metadata={'test': True})

    def test_factory_initialization_creates_isolated_state(self):
        """Test factory creates isolated state containers."""
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0
        assert self.factory.max_managers_per_user == 3
        assert self.factory._factory_lock is not None

    @pytest.mark.asyncio
    async def test_factory_creates_isolated_managers_per_user(self):
        """CRITICAL: Test factory creates isolated managers for different users."""
        user1_context = self._create_user_context('user1')
        user2_context = self._create_user_context('user2')
        manager1 = await self.factory.create_manager(user1_context)
        manager2 = await self.factory.create_manager(user2_context)
        assert manager1 is not manager2
        assert manager1.user_context.user_id == 'user1'
        assert manager2.user_context.user_id == 'user2'
        assert manager1._connections is not manager2._connections
        assert manager1._connection_ids is not manager2._connection_ids

    @pytest.mark.asyncio
    async def test_factory_returns_same_manager_for_same_context(self):
        """Test factory returns existing manager for identical context."""
        user_context = self._create_user_context('same_user')
        manager1 = await self.factory.create_manager(user_context)
        manager2 = await self.factory.create_manager(user_context)
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_manager_validates_connection_user_ownership(self):
        """CRITICAL: Test manager validates connection belongs to correct user."""
        user_context = self._create_user_context('legitimate_user')
        manager = await self.factory.create_manager(user_context)
        wrong_user_connection = self._create_mock_connection('attacker_user')
        with pytest.raises(ValueError, match='does not match manager user_id'):
            await manager.add_connection(wrong_user_connection)
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_manager_accepts_correct_user_connections(self):
        """Test manager accepts connections for correct user."""
        user_context = self._create_user_context('correct_user')
        manager = await self.factory.create_manager(user_context)
        correct_connection = self._create_mock_connection('correct_user')
        await manager.add_connection(correct_connection)
        assert correct_connection.connection_id in manager._connections
        assert len(manager._connections) == 1

    @pytest.mark.asyncio
    async def test_messages_only_route_to_user_connections(self):
        """CRITICAL: Test messages only route to user's own connections."""
        user1_context = self._create_user_context('message_user1')
        user2_context = self._create_user_context('message_user2')
        manager1 = await self.factory.create_manager(user1_context)
        manager2 = await self.factory.create_manager(user2_context)
        conn1 = self._create_mock_connection('message_user1', 'conn1')
        conn2 = self._create_mock_connection('message_user2', 'conn2')
        await manager1.add_connection(conn1)
        await manager2.add_connection(conn2)
        message = {'type': 'test', 'data': 'user1_secret'}
        await manager1.send_to_user(message)
        conn1.websocket.send_json.assert_called_once()
        conn2.websocket.send_json.assert_not_called()
        sent_message = conn1.websocket.send_json.call_args[0][0]
        assert sent_message['data'] == 'user1_secret'

    @pytest.mark.asyncio
    async def test_concurrent_messages_maintain_isolation(self):
        """CRITICAL: Test concurrent messages maintain user isolation."""
        users = ['concurrent_user1', 'concurrent_user2', 'concurrent_user3']
        managers = {}
        connections = {}
        for user_id in users:
            context = self._create_user_context(user_id)
            manager = await self.factory.create_manager(context)
            connection = self._create_mock_connection(user_id)
            await manager.add_connection(connection)
            managers[user_id] = manager
            connections[user_id] = connection

        async def send_user_message(user_id: str):
            message = {'type': 'concurrent', 'secret': f'{user_id}_secret'}
            await managers[user_id].send_to_user(message)
        await asyncio.gather(*[send_user_message(user_id) for user_id in users])
        for user_id in users:
            conn = connections[user_id]
            conn.websocket.send_json.assert_called_once()
            sent_message = conn.websocket.send_json.call_args[0][0]
            assert sent_message['secret'] == f'{user_id}_secret'
            message_str = str(sent_message)
            for other_user in users:
                if other_user != user_id:
                    assert f'{other_user}_secret' not in message_str

    @pytest.mark.asyncio
    async def test_manager_cleanup_isolates_resources(self):
        """Test manager cleanup properly isolates resources."""
        user_context = self._create_user_context('cleanup_user')
        manager = await self.factory.create_manager(user_context)
        connection = self._create_mock_connection('cleanup_user')
        await manager.add_connection(connection)
        assert len(manager._connections) == 1
        isolation_key = self.factory._generate_isolation_key(user_context)
        result = await self.factory.cleanup_manager(isolation_key)
        assert result is True
        assert not manager._is_active
        assert len(manager._connections) == 0

    @pytest.mark.asyncio
    async def test_factory_shutdown_cleans_all_resources(self):
        """Test factory shutdown cleans all resources."""
        contexts = []
        for i in range(3):
            context = self._create_user_context(f'shutdown_user_{i}')
            contexts.append(context)
            await self.factory.create_manager(context)
        assert len(self.factory._active_managers) == 3
        await self.factory.shutdown()
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0

    @pytest.mark.asyncio
    async def test_factory_enforces_resource_limits(self):
        """Test factory enforces maximum managers per user."""
        user_id = 'resource_test_user'
        for i in range(self.factory.max_managers_per_user):
            context = self._create_user_context(user_id, f'ws_{i}')
            manager = await self.factory.create_manager(context)
            assert manager is not None
        excess_context = self._create_user_context(user_id, 'ws_excess')
        with pytest.raises(RuntimeError, match='maximum number'):
            await self.factory.create_manager(excess_context)

    @pytest.mark.asyncio
    async def test_manager_creation_validates_context_type(self):
        """Test manager creation validates UserExecutionContext type."""
        with pytest.raises(ValueError, match='must be a UserExecutionContext'):
            await self.factory.create_manager('invalid_context')
        with pytest.raises(ValueError, match='must be a UserExecutionContext'):
            await self.factory.create_manager({'user_id': 'test'})

    def test_manager_initialization_validates_context(self):
        """Test WebSocketManager validates context on initialization."""
        with pytest.raises(ValueError, match='must be a UserExecutionContext'):
            WebSocketManager('not_a_context')

    @pytest.mark.asyncio
    async def test_comprehensive_security_isolation(self):
        """COMPREHENSIVE: Test complete security isolation across all operations."""
        security_users = ['alice', 'bob', 'charlie']
        user_data = {}
        for user_id in security_users:
            context = self._create_user_context(user_id)
            manager = await self.factory.create_manager(context)
            connection = self._create_mock_connection(user_id)
            await manager.add_connection(connection)
            user_data[user_id] = {'context': context, 'manager': manager, 'connection': connection}
        sensitive_data = {'alice': {'secret': 'alice_password_123', 'credit_card': '1111-2222-3333-4444'}, 'bob': {'secret': 'bob_api_key_xyz', 'ssn': '123-45-6789'}, 'charlie': {'secret': 'charlie_token_abc', 'private': 'confidential_data'}}
        for user_id, data in sensitive_data.items():
            message = {'type': 'sensitive', 'payload': data}
            await user_data[user_id]['manager'].send_to_user(message)
        for user_id in security_users:
            connection = user_data[user_id]['connection']
            assert connection.websocket.send_json.call_count == 1
            sent_message = connection.websocket.send_json.call_args[0][0]
            user_secret = sensitive_data[user_id]['secret']
            assert user_secret in str(sent_message)
            for other_user, other_data in sensitive_data.items():
                if other_user != user_id:
                    other_secret = other_data['secret']
                    assert other_secret not in str(sent_message), f"SECURITY BREACH: {user_id} received {other_user}'s sensitive data"
        for user_id in security_users:
            manager = user_data[user_id]['manager']
            connections = manager.get_user_connections()
            for conn_id in connections:
                connection = manager.get_connection(conn_id)
                assert connection.user_id == user_id, f'SECURITY BREACH: Manager for {user_id} has connection for {connection.user_id}'
            for other_user in security_users:
                if other_user != user_id:
                    other_connection = user_data[other_user]['connection']
                    found = manager.get_connection(other_connection.connection_id)
                    assert found is None, f"SECURITY BREACH: Manager for {user_id} can access {other_user}'s connection"
        print(' PASS:  COMPREHENSIVE SECURITY VALIDATION PASSED - No cross-user contamination detected')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')