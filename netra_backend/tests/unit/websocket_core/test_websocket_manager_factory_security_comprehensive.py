"""
Comprehensive Security Unit Tests for WebSocketManagerFactory - CRITICAL SECURITY MISSION

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent user message cross-contamination in multi-user AI chat
- Value Impact: CRITICAL SECURITY - Ensures user isolation in WebSocket communications
- Strategic Impact: Foundation security for real-time AI interactions

MISSION CRITICAL: These tests prevent the most serious security vulnerability:
user message cross-contamination between different users in AI chat sessions.

Target Classes:
- WebSocketManagerFactory (Line 1153): Factory pattern for isolated instances
- IsolatedWebSocketManager (Line 581): Per-connection manager with private state  
- ConnectionLifecycleManager (Line 391): Connection lifecycle and cleanup

Test Categories:
1. Factory Pattern Tests: Creation, retrieval, cleanup of isolated managers
2. User Isolation Tests: No cross-contamination between users
3. Connection Lifecycle Tests: Proper registration, cleanup, health monitoring
4. Security Tests: Message routing isolation, memory leak prevention
5. Concurrency Tests: Multiple users simultaneously 
6. WebSocket Event Tests: Proper event routing per user

CRITICAL COVERAGE REQUIREMENTS:
- 100% line coverage of all three classes
- Tests detect user message cross-contamination vulnerabilities
- Tests validate proper resource cleanup 
- All concurrency and isolation scenarios covered
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, List, Set, Any, Optional
import logging
import weakref
import gc

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager, 
    ConnectionLifecycleManager,
    FactoryMetrics,
    ManagerMetrics,
    FactoryInitializationError,
    get_websocket_manager_factory,
    create_websocket_manager,
    create_defensive_user_execution_context,
    _validate_ssot_user_context,
    _validate_ssot_user_context_staging_safe
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol


class TestWebSocketManagerFactoryComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for WebSocketManagerFactory.
    
    CRITICAL: Factory pattern ensures isolated manager instances per user connection,
    preventing message cross-contamination vulnerabilities.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.factory = WebSocketManagerFactory(max_managers_per_user=3, connection_timeout_seconds=300)
        self.user_contexts = []  # Track created contexts for cleanup
    
    def teardown_method(self, method=None):
        """Teardown and cleanup after each test method."""
        # Cleanup any created managers
        if hasattr(self, 'factory'):
            asyncio.run(self.factory.shutdown())
        super().teardown_method(method)
    
    def _create_test_user_context(self, user_id: Optional[str] = None, websocket_client_id: Optional[str] = None) -> UserExecutionContext:
        """Create a test UserExecutionContext with proper validation."""
        if user_id is None:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        if websocket_client_id is None:
            websocket_client_id = f"ws_client_{uuid.uuid4().hex[:8]}"
        
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            websocket_client_id=websocket_client_id
        )
        self.user_contexts.append(context)
        return context
    
    # === FACTORY PATTERN TESTS ===
    
    def test_factory_initialization_sets_correct_defaults(self):
        """Test factory initializes with correct default configuration."""
        factory = WebSocketManagerFactory()
        
        assert factory.max_managers_per_user == 5  # Default
        assert factory.connection_timeout_seconds == 1800  # 30 minutes default
        assert len(factory._active_managers) == 0
        assert len(factory._user_manager_count) == 0
        assert len(factory._manager_creation_time) == 0
        assert factory._factory_lock is not None
        assert isinstance(factory._factory_metrics, FactoryMetrics)
        assert factory._cleanup_started is False
    
    def test_factory_initialization_respects_custom_parameters(self):
        """Test factory initialization with custom parameters."""
        factory = WebSocketManagerFactory(max_managers_per_user=10, connection_timeout_seconds=600)
        
        assert factory.max_managers_per_user == 10
        assert factory.connection_timeout_seconds == 600
        
        # Verify metrics initialized
        assert factory._factory_metrics.managers_created == 0
        assert factory._factory_metrics.managers_active == 0
    
    @pytest.mark.asyncio
    async def test_create_manager_returns_isolated_instance(self):
        """Test factory creates isolated manager instances."""
        user_context = self._create_test_user_context()
        
        # Act
        manager = await self.factory.create_manager(user_context)
        
        # Assert
        assert isinstance(manager, IsolatedWebSocketManager)
        assert manager.user_context == user_context
        assert manager._is_active is True
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
        
        # Verify factory tracking
        assert len(self.factory._active_managers) == 1
        assert self.factory._user_manager_count[user_context.user_id] == 1
        assert self.factory._factory_metrics.managers_created == 1
        assert self.factory._factory_metrics.managers_active == 1
    
    @pytest.mark.asyncio
    async def test_create_manager_generates_unique_isolation_keys(self):
        """Test factory generates unique isolation keys for different contexts."""
        user_context1 = self._create_test_user_context("user1", "client1")
        user_context2 = self._create_test_user_context("user1", "client2")  # Same user, different client
        user_context3 = self._create_test_user_context("user2", "client3")  # Different user
        
        # Create managers
        manager1 = await self.factory.create_manager(user_context1)
        manager2 = await self.factory.create_manager(user_context2)
        manager3 = await self.factory.create_manager(user_context3)
        
        # Assert all are different instances
        assert manager1 is not manager2
        assert manager2 is not manager3
        assert manager1 is not manager3
        
        # Verify isolation keys are different
        key1 = self.factory._generate_isolation_key(user_context1)
        key2 = self.factory._generate_isolation_key(user_context2)
        key3 = self.factory._generate_isolation_key(user_context3)
        
        assert key1 != key2  # Same user, different clients
        assert key2 != key3  # Different users
        assert key1 != key3  # Different users
        
        # Verify factory tracking
        assert len(self.factory._active_managers) == 3
        assert self.factory._user_manager_count["user1"] == 2  # Two managers for user1
        assert self.factory._user_manager_count["user2"] == 1  # One manager for user2
    
    @pytest.mark.asyncio
    async def test_create_manager_returns_existing_for_same_isolation_key(self):
        """Test factory returns existing manager for identical isolation key."""
        user_context = self._create_test_user_context()
        
        # Create first manager
        manager1 = await self.factory.create_manager(user_context)
        
        # Create second manager with same context (should return existing)
        manager2 = await self.factory.create_manager(user_context)
        
        # Assert same instance returned
        assert manager1 is manager2
        
        # Verify factory tracking didn't double-count
        assert len(self.factory._active_managers) == 1
        assert self.factory._user_manager_count[user_context.user_id] == 1
        assert self.factory._factory_metrics.managers_created == 1  # Only one created
    
    def test_get_websocket_manager_factory_returns_singleton(self):
        """Test get_websocket_manager_factory returns singleton instance."""
        factory1 = get_websocket_manager_factory()
        factory2 = get_websocket_manager_factory()
        
        assert factory1 is factory2
        assert isinstance(factory1, WebSocketManagerFactory)


class TestIsolatedWebSocketManagerComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for IsolatedWebSocketManager.
    
    CRITICAL: Tests user isolation, message routing, and connection management
    to prevent cross-user contamination vulnerabilities.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.user_context = self._create_test_user_context()
        self.manager = IsolatedWebSocketManager(self.user_context)
        self.mock_connections = []
    
    def teardown_method(self, method=None):
        """Cleanup after each test method."""
        if hasattr(self, 'manager'):
            asyncio.run(self.manager.cleanup_all_connections())
        super().teardown_method(method)
    
    def _create_test_user_context(self, user_id: str = None) -> UserExecutionContext:
        """Create test UserExecutionContext."""
        if user_id is None:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            websocket_client_id=f"ws_client_{uuid.uuid4().hex[:8]}"
        )
    
    def _create_mock_websocket_connection(self, user_id: str = None, connection_id: str = None) -> WebSocketConnection:
        """Create mock WebSocket connection for testing."""
        if user_id is None:
            user_id = self.user_context.user_id
        if connection_id is None:
            connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.close = AsyncMock()
        mock_websocket.client_state = "CONNECTED"  # Mock WebSocketState
        
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc),
            metadata={"test": True}
        )
        self.mock_connections.append(connection)
        return connection
    
    # === INITIALIZATION TESTS ===
    
    def test_manager_initialization_creates_isolated_state(self):
        """Test IsolatedWebSocketManager initializes with completely isolated state."""
        assert self.manager.user_context == self.user_context
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        assert self.manager._is_active is True
        
        # Verify private state containers
        assert isinstance(self.manager._connections, dict)
        assert isinstance(self.manager._connection_ids, set)
        assert isinstance(self.manager._message_recovery_queue, list)
        assert self.manager._connection_error_count == 0
        
        # Verify metrics initialized
        assert isinstance(self.manager._metrics, ManagerMetrics)
        assert self.manager._metrics.connections_managed == 0
        
        # Verify lifecycle manager created
        assert isinstance(self.manager._lifecycle_manager, ConnectionLifecycleManager)
    
    def test_manager_initialization_validates_user_context(self):
        """Test manager validates UserExecutionContext on initialization."""
        with pytest.raises(ValueError, match="user_context must be a UserExecutionContext"):
            IsolatedWebSocketManager("not_a_context")
    
    def test_manager_implements_websocket_protocol(self):
        """Test manager implements WebSocketManagerProtocol interface."""
        assert isinstance(self.manager, WebSocketManagerProtocol)
        
        # Check protocol methods exist
        assert hasattr(self.manager, 'add_connection')
        assert hasattr(self.manager, 'remove_connection')
        assert hasattr(self.manager, 'get_connection')
        assert hasattr(self.manager, 'is_connection_active')
        assert hasattr(self.manager, 'send_to_user')
        assert hasattr(self.manager, 'get_connection_health')
        assert hasattr(self.manager, 'send_to_thread')
    
    # === CRITICAL SECURITY ISOLATION TESTS ===
    
    @pytest.mark.asyncio
    async def test_add_connection_validates_user_ownership(self):
        """CRITICAL: Test add_connection validates connection belongs to correct user."""
        # Create connection for different user
        wrong_user_connection = self._create_mock_websocket_connection("different_user")
        
        # Should raise security violation error
        with pytest.raises(ValueError, match="does not match manager user_id"):
            await self.manager.add_connection(wrong_user_connection)
        
        # Verify no state contamination
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        assert self.manager._metrics.connections_managed == 0
    
    @pytest.mark.asyncio
    async def test_send_to_user_routes_to_user_connections_only(self):
        """CRITICAL: Test send_to_user routes messages only to user's connections."""
        # Add connections for this user
        conn1 = self._create_mock_websocket_connection(self.user_context.user_id, "user_conn_1")
        conn2 = self._create_mock_websocket_connection(self.user_context.user_id, "user_conn_2")
        
        await self.manager.add_connection(conn1)
        await self.manager.add_connection(conn2)
        
        # Send message
        test_message = {"type": "test_message", "data": "user_data"}
        await self.manager.send_to_user(test_message)
        
        # Verify message sent to user's connections only
        conn1.websocket.send_json.assert_called_once()
        conn2.websocket.send_json.assert_called_once()
        
        # Check message content
        sent_args = conn1.websocket.send_json.call_args[0][0]
        assert sent_args["type"] == "test_message"
        assert sent_args["data"] == "user_data"
    
    def test_get_connection_health_enforces_user_isolation(self):
        """CRITICAL: Test get_connection_health enforces user isolation."""
        # Request health for different user
        health = self.manager.get_connection_health("different_user")
        
        assert health["error"] == "user_isolation_violation"
        assert "Cannot get health for different user" in health["message"]
        assert health["user_id"] == "different_user"


class TestConnectionLifecycleManagerComprehensive(SSotAsyncTestCase):
    """
    Comprehensive unit tests for ConnectionLifecycleManager.
    
    CRITICAL: Tests connection lifecycle management, health monitoring,
    and automatic cleanup to prevent resource leaks.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.user_context = self._create_test_user_context()
        self.mock_ws_manager = Mock(spec=IsolatedWebSocketManager)
        self.mock_ws_manager.user_context = self.user_context
        self.mock_ws_manager.get_connection = Mock(return_value=None)
        self.mock_ws_manager.remove_connection = AsyncMock()
        self.lifecycle_manager = ConnectionLifecycleManager(self.user_context, self.mock_ws_manager)
    
    def teardown_method(self, method=None):
        """Cleanup after each test method."""
        if hasattr(self, 'lifecycle_manager'):
            asyncio.run(self.lifecycle_manager.force_cleanup_all())
        super().teardown_method(method)
    
    def _create_test_user_context(self, user_id: str = None) -> UserExecutionContext:
        """Create test UserExecutionContext."""
        if user_id is None:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}",
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            websocket_client_id=f"ws_client_{uuid.uuid4().hex[:8]}"
        )
    
    def _create_mock_connection(self, user_id: str = None, connection_id: str = None) -> WebSocketConnection:
        """Create mock WebSocket connection for testing."""
        if user_id is None:
            user_id = self.user_context.user_id
        if connection_id is None:
            connection_id = f"conn_{uuid.uuid4().hex[:8]}"
        
        mock_websocket = AsyncMock()
        return WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
    
    # === INITIALIZATION TESTS ===
    
    def test_lifecycle_manager_initialization(self):
        """Test ConnectionLifecycleManager initializes correctly."""
        assert self.lifecycle_manager.user_context == self.user_context
        assert self.lifecycle_manager.ws_manager == self.mock_ws_manager
        assert isinstance(self.lifecycle_manager._managed_connections, set)
        assert isinstance(self.lifecycle_manager._connection_health, dict)
        assert len(self.lifecycle_manager._managed_connections) == 0
        assert len(self.lifecycle_manager._connection_health) == 0
        assert self.lifecycle_manager._is_active is True
    
    # === CONNECTION REGISTRATION TESTS ===
    
    def test_register_connection_validates_user_ownership(self):
        """CRITICAL: Test register_connection validates connection belongs to user."""
        # Create connection for different user
        wrong_user_conn = self._create_mock_connection("different_user")
        
        # Should raise security violation
        with pytest.raises(ValueError, match="does not match context user_id"):
            self.lifecycle_manager.register_connection(wrong_user_conn)
        
        # Verify no state contamination
        assert len(self.lifecycle_manager._managed_connections) == 0
        assert len(self.lifecycle_manager._connection_health) == 0
    
    def test_register_connection_accepts_correct_user(self):
        """Test register_connection accepts connections for correct user."""
        connection = self._create_mock_connection(self.user_context.user_id)
        
        self.lifecycle_manager.register_connection(connection)
        
        # Verify registration
        assert connection.connection_id in self.lifecycle_manager._managed_connections
        assert connection.connection_id in self.lifecycle_manager._connection_health
        
        # Verify health timestamp
        health_time = self.lifecycle_manager._connection_health[connection.connection_id]
        assert isinstance(health_time, datetime)
        assert (datetime.utcnow() - health_time).total_seconds() < 1  # Recent


class TestWebSocketFactorySecurityIsolation(SSotAsyncTestCase):
    """
    CRITICAL SECURITY TESTS: User Message Cross-Contamination Prevention
    
    These tests validate the most important security requirement:
    Messages from one user MUST NEVER be delivered to another user.
    """
    
    def setup_method(self, method=None):
        """Setup for security isolation tests."""
        super().setup_method(method)
        self.factory = WebSocketManagerFactory(max_managers_per_user=5)
        self.user_contexts = {}
        self.managers = {}
        self.mock_connections = {}
    
    def teardown_method(self, method=None):
        """Cleanup after security tests."""
        if hasattr(self, 'factory'):
            asyncio.run(self.factory.shutdown())
        super().teardown_method(method)
    
    def _create_user_setup(self, user_id: str) -> tuple:
        """Create complete user setup with context, manager, and connection."""
        context = UserExecutionContext(
            user_id=user_id,
            thread_id=f"thread_{user_id}",
            run_id=f"run_{user_id}",
            request_id=f"req_{user_id}",
            websocket_client_id=f"ws_{user_id}"
        )
        
        # Create mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.client_state = "CONNECTED"
        
        connection = WebSocketConnection(
            connection_id=f"conn_{user_id}",
            user_id=user_id,
            websocket=mock_websocket,
            connected_at=datetime.now(timezone.utc)
        )
        
        self.user_contexts[user_id] = context
        self.mock_connections[user_id] = connection
        
        return context, connection
    
    @pytest.mark.asyncio
    async def test_complete_user_isolation_no_cross_contamination(self):
        """CRITICAL: Test complete isolation - no message cross-contamination between users."""
        # Setup multiple users
        users = ["alice", "bob", "charlie"]
        managers = {}
        
        for user_id in users:
            context, connection = self._create_user_setup(user_id)
            
            # Create isolated manager for each user
            manager = await self.factory.create_manager(context)
            await manager.add_connection(connection)
            
            managers[user_id] = manager
        
        # Send messages to each user
        messages = {
            "alice": {"type": "private", "secret": "alice_secret_data", "user": "alice"},
            "bob": {"type": "private", "secret": "bob_secret_data", "user": "bob"},
            "charlie": {"type": "private", "secret": "charlie_secret_data", "user": "charlie"}
        }
        
        # Send messages
        for user_id, message in messages.items():
            await managers[user_id].send_to_user(message)
        
        # CRITICAL VERIFICATION: Each user only received their own message
        for user_id in users:
            connection = self.mock_connections[user_id]
            
            # Verify exactly one message sent to this user
            assert connection.websocket.send_json.call_count == 1
            
            # Get the actual message sent
            sent_message = connection.websocket.send_json.call_args[0][0]
            
            # CRITICAL: Message content must match only this user's message
            assert sent_message["secret"] == f"{user_id}_secret_data"
            assert sent_message["user"] == user_id
            
            # CRITICAL: Must not contain other users' data
            for other_user in users:
                if other_user != user_id:
                    assert f"{other_user}_secret_data" not in str(sent_message)
                    assert sent_message["user"] != other_user
    
    @pytest.mark.asyncio
    async def test_concurrent_user_operations_maintain_isolation(self):
        """CRITICAL: Test concurrent operations maintain complete user isolation."""
        # Setup users
        users = ["user1", "user2", "user3", "user4", "user5"]
        managers = {}
        
        for user_id in users:
            context, connection = self._create_user_setup(user_id)
            manager = await self.factory.create_manager(context)
            await manager.add_connection(connection)
            managers[user_id] = manager
        
        # Define concurrent message sending tasks
        async def send_user_messages(user_id: str, message_count: int):
            """Send multiple messages for a user."""
            manager = managers[user_id]
            for i in range(message_count):
                message = {
                    "type": "concurrent_test",
                    "user_id": user_id,
                    "message_id": i,
                    "sensitive_data": f"SECRET_{user_id}_{i}"
                }
                await manager.send_to_user(message)
        
        # Run concurrent message sending
        tasks = [send_user_messages(user_id, 10) for user_id in users]
        await asyncio.gather(*tasks)
        
        # CRITICAL VERIFICATION: Each user only received their own messages
        for user_id in users:
            connection = self.mock_connections[user_id]
            
            # Should have received exactly 10 messages
            assert connection.websocket.send_json.call_count == 10
            
            # Verify all messages belong to this user only
            for call_args in connection.websocket.send_json.call_args_list:
                sent_message = call_args[0][0]
                
                # CRITICAL: Message must be for this user
                assert sent_message["user_id"] == user_id
                assert f"SECRET_{user_id}_" in sent_message["sensitive_data"]
                
                # CRITICAL: Must not contain other users' secrets
                for other_user in users:
                    if other_user != user_id:
                        assert f"SECRET_{other_user}_" not in sent_message["sensitive_data"]
    
    @pytest.mark.asyncio
    async def test_manager_factory_prevents_connection_hijacking(self):
        """CRITICAL: Test factory prevents connection hijacking attempts."""
        # Setup legitimate user
        legit_context, legit_connection = self._create_user_setup("legitimate_user")
        legit_manager = await self.factory.create_manager(legit_context)
        await legit_manager.add_connection(legit_connection)
        
        # Setup attacker trying to hijack connection
        attacker_context, _ = self._create_user_setup("attacker_user")
        attacker_manager = await self.factory.create_manager(attacker_context)
        
        # CRITICAL: Attacker tries to add legitimate user's connection to their manager
        with pytest.raises(ValueError, match="does not match manager user_id"):
            await attacker_manager.add_connection(legit_connection)
        
        # Verify legitimate user's connection remains isolated
        assert len(legit_manager._connections) == 1
        assert len(attacker_manager._connections) == 0
        
        # Verify legitimate user can still receive messages
        test_message = {"type": "test", "data": "legitimate_data"}
        await legit_manager.send_to_user(test_message)
        
        legit_connection.websocket.send_json.assert_called_once()
        sent_message = legit_connection.websocket.send_json.call_args[0][0]
        assert sent_message["data"] == "legitimate_data"


class TestWebSocketFactoryGlobalFunctions(SSotAsyncTestCase):
    """
    Test global factory functions and validation utilities.
    """
    
    def test_create_defensive_user_execution_context_creates_valid_context(self):
        """Test create_defensive_user_execution_context creates valid context."""
        user_id = "defensive_test_user"
        client_id = "defensive_client"
        
        context = create_defensive_user_execution_context(user_id, client_id)
        
        assert isinstance(context, UserExecutionContext)
        assert context.user_id == user_id
        assert context.websocket_client_id == client_id
        assert context.thread_id is not None
        assert context.run_id is not None
        assert context.request_id is not None
    
    def test_create_defensive_user_execution_context_validates_user_id(self):
        """Test create_defensive_user_execution_context validates user_id."""
        with pytest.raises(ValueError, match="user_id must be non-empty string"):
            create_defensive_user_execution_context("")
        
        with pytest.raises(ValueError, match="user_id must be non-empty string"):
            create_defensive_user_execution_context(None)
        
        with pytest.raises(ValueError, match="user_id must be non-empty string"):
            create_defensive_user_execution_context("   ")
    
    def test_validate_ssot_user_context_validates_type(self):
        """Test _validate_ssot_user_context validates correct type."""
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            request_id="test_request",
            websocket_client_id="test_client"
        )
        
        # Should not raise
        _validate_ssot_user_context(valid_context)
        
        # Invalid type should raise
        with pytest.raises(ValueError, match="SSOT VIOLATION"):
            _validate_ssot_user_context({"user_id": "test"})
    
    @pytest.mark.asyncio
    async def test_create_websocket_manager_validates_and_creates(self):
        """Test create_websocket_manager validates context and creates manager."""
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request",
            websocket_client_id="test_client"
        )
        
        manager = await create_websocket_manager(context)
        
        assert isinstance(manager, IsolatedWebSocketManager)
        assert manager.user_context == context
        assert manager._is_active is True
    
    @pytest.mark.asyncio
    async def test_create_websocket_manager_handles_validation_errors(self):
        """Test create_websocket_manager handles validation errors gracefully."""
        invalid_context = "not_a_context"
        
        with pytest.raises(FactoryInitializationError, match="SSOT validation failed"):
            await create_websocket_manager(invalid_context)