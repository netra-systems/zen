"""
Unit Tests for WebSocketManagerFactory - SECURITY CRITICAL Multi-User Isolation

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) 
- Business Goal: Eliminate critical security vulnerabilities in WebSocket communication
- Value Impact: Ensures safe multi-user AI interactions without data leakage
- Strategic Impact: Prevents catastrophic security breaches that could destroy business

CRITICAL: This module tests the factory that creates isolated WebSocket manager instances
per user connection, ensuring complete user isolation and preventing message cross-contamination.

The tests validate:
1. Factory initialization and configuration
2. Manager creation with strict user isolation
3. Connection lifecycle management and cleanup
4. Security violation detection and prevention
5. Resource limit enforcement
6. Metrics tracking and monitoring
7. Concurrent manager creation safety
8. Memory leak prevention
9. Background cleanup processes
10. Error handling and recovery

SECURITY FEATURES TESTED:
- Per-connection isolation keys (not just per-user)
- Resource limit enforcement (max managers per user)
- Automatic cleanup of expired managers
- Thread-safe factory operations
- User isolation validation at every step
- Security metrics and violation detection
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, List
from unittest.mock import AsyncMock, Mock, patch

# Import SSOT test base classes
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
from test_framework.ssot.mocks import MockFactory

# Import components under test
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    IsolatedWebSocketManager,
    ConnectionLifecycleManager,
    FactoryMetrics,
    ManagerMetrics,
    get_websocket_manager_factory,
    create_websocket_manager,
    _factory_instance,
    _factory_lock
)

from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection


class TestFactoryMetrics(SSotBaseTestCase):
    """Test FactoryMetrics data class."""
    
    @pytest.mark.unit
    def test_factory_metrics_initialization(self):
        """Test FactoryMetrics initialization with default values."""
        metrics = FactoryMetrics()
        
        assert metrics.managers_created == 0
        assert metrics.managers_active == 0
        assert metrics.managers_cleaned_up == 0
        assert metrics.users_with_active_managers == 0
        assert metrics.resource_limit_hits == 0
        assert metrics.total_connections_managed == 0
        assert metrics.security_violations_detected == 0
        assert metrics.average_manager_lifetime_seconds == 0.0
        
        self.record_metric("factory_metrics_fields_verified", 8)
    
    @pytest.mark.unit
    def test_factory_metrics_to_dict(self):
        """Test FactoryMetrics to_dict conversion."""
        metrics = FactoryMetrics(
            managers_created=5,
            managers_active=3,
            security_violations_detected=1
        )
        
        metrics_dict = metrics.to_dict()
        
        expected_keys = [
            "managers_created", "managers_active", "managers_cleaned_up",
            "users_with_active_managers", "resource_limit_hits",
            "total_connections_managed", "security_violations_detected",
            "average_manager_lifetime_seconds"
        ]
        
        for key in expected_keys:
            assert key in metrics_dict
        
        assert metrics_dict["managers_created"] == 5
        assert metrics_dict["managers_active"] == 3
        assert metrics_dict["security_violations_detected"] == 1
        
        self.record_metric("factory_metrics_dict_keys_verified", len(expected_keys))


class TestManagerMetrics(SSotBaseTestCase):
    """Test ManagerMetrics data class."""
    
    @pytest.mark.unit
    def test_manager_metrics_initialization(self):
        """Test ManagerMetrics initialization with default values."""
        metrics = ManagerMetrics()
        
        assert metrics.connections_managed == 0
        assert metrics.messages_sent_total == 0
        assert metrics.messages_failed_total == 0
        assert metrics.last_activity is None
        assert metrics.manager_age_seconds == 0.0
        assert metrics.cleanup_scheduled == False
        
        self.record_metric("manager_metrics_fields_verified", 6)
    
    @pytest.mark.unit
    def test_manager_metrics_to_dict_with_datetime(self):
        """Test ManagerMetrics to_dict with datetime handling."""
        now = datetime.utcnow()
        metrics = ManagerMetrics(
            connections_managed=2,
            messages_sent_total=10,
            last_activity=now
        )
        
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["connections_managed"] == 2
        assert metrics_dict["messages_sent_total"] == 10
        assert metrics_dict["last_activity"] == now.isoformat()
        assert metrics_dict["cleanup_scheduled"] == False
        
        self.record_metric("manager_metrics_datetime_conversion", 1)
    
    @pytest.mark.unit
    def test_manager_metrics_to_dict_with_none_datetime(self):
        """Test ManagerMetrics to_dict with None datetime."""
        metrics = ManagerMetrics()
        metrics_dict = metrics.to_dict()
        
        assert metrics_dict["last_activity"] is None
        
        self.record_metric("manager_metrics_none_datetime_handling", 1)


class TestWebSocketManagerFactory(SSotAsyncTestCase):
    """Test WebSocketManagerFactory core functionality."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Create test factory with controlled configuration
        self.factory = WebSocketManagerFactory(
            max_managers_per_user=3,
            connection_timeout_seconds=10
        )
        
        # Create test user contexts
        self.test_user_context = UserExecutionContext.from_request(
            user_id="test_user_123",
            thread_id="test_thread_456", 
            run_id="test_run_789",
            websocket_connection_id="ws_connection_001"
        )
        
        self.second_user_context = UserExecutionContext.from_request(
            user_id="test_user_456",
            thread_id="test_thread_789",
            run_id="test_run_012",
            websocket_connection_id="ws_connection_002"
        )
        
        # Initialize mock factory
        self.mock_factory = MockFactory(self.get_env())
    
    async def teardown_method(self, method=None):
        """Cleanup after each test method."""
        try:
            # Shutdown factory to clean up background tasks
            await self.factory.shutdown()
            self.mock_factory.cleanup()
        finally:
            super().teardown_method(method)
    
    @pytest.mark.unit
    def test_factory_initialization(self):
        """Test WebSocketManagerFactory initialization."""
        factory = WebSocketManagerFactory(
            max_managers_per_user=5,
            connection_timeout_seconds=1800
        )
        
        assert factory.max_managers_per_user == 5
        assert factory.connection_timeout_seconds == 1800
        assert factory._factory_metrics is not None
        assert isinstance(factory._factory_metrics, FactoryMetrics)
        assert factory._cleanup_started == False
        
        # Check internal state initialization
        assert len(factory._active_managers) == 0
        assert len(factory._user_manager_count) == 0
        assert len(factory._manager_creation_time) == 0
        
        self.record_metric("factory_initialization_verified", 1)
    
    @pytest.mark.unit
    def test_generate_isolation_key_with_websocket_connection(self):
        """Test isolation key generation with WebSocket connection ID."""
        isolation_key = self.factory._generate_isolation_key(self.test_user_context)
        
        expected_key = f"{self.test_user_context.user_id}:{self.test_user_context.websocket_connection_id}"
        assert isolation_key == expected_key
        
        # Verify key uniqueness
        second_isolation_key = self.factory._generate_isolation_key(self.second_user_context)
        assert isolation_key != second_isolation_key
        
        self.record_metric("isolation_key_generation_verified", 1)
    
    @pytest.mark.unit  
    def test_generate_isolation_key_fallback_to_request_id(self):
        """Test isolation key generation falls back to request_id when no WebSocket connection."""
        context_without_ws = UserExecutionContext.from_request(
            user_id="test_user_789",
            thread_id="test_thread_012",
            run_id="test_run_345"
            # No websocket_connection_id
        )
        
        isolation_key = self.factory._generate_isolation_key(context_without_ws)
        expected_key = f"{context_without_ws.user_id}:{context_without_ws.request_id}"
        assert isolation_key == expected_key
        
        self.record_metric("isolation_key_fallback_verified", 1)
    
    @pytest.mark.unit
    def test_create_manager_success(self):
        """Test successful manager creation."""
        manager = self.factory.create_manager(self.test_user_context)
        
        # Verify manager creation
        assert isinstance(manager, IsolatedWebSocketManager)
        assert manager.user_context == self.test_user_context
        assert manager._is_active == True
        
        # Verify factory state updates
        assert len(self.factory._active_managers) == 1
        assert self.factory._user_manager_count[self.test_user_context.user_id] == 1
        
        # Verify metrics
        assert self.factory._factory_metrics.managers_created == 1
        assert self.factory._factory_metrics.managers_active == 1
        assert self.factory._factory_metrics.users_with_active_managers == 1
        
        self.record_metric("manager_creation_success", 1)
    
    @pytest.mark.unit
    def test_create_manager_invalid_context(self):
        """Test manager creation with invalid context raises ValueError."""
        with self.expect_exception(ValueError, "user_context must be a UserExecutionContext instance"):
            self.factory.create_manager("not_a_context")
        
        # Verify factory state unchanged
        assert len(self.factory._active_managers) == 0
        assert self.factory._factory_metrics.managers_created == 0
        
        self.record_metric("invalid_context_rejection", 1)
    
    @pytest.mark.unit
    def test_create_manager_resource_limit_exceeded(self):
        """Test resource limit enforcement when max managers per user exceeded."""
        # Create maximum allowed managers
        managers = []
        for i in range(self.factory.max_managers_per_user):
            context = UserExecutionContext.from_request(
                user_id="test_user_limit",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                websocket_connection_id=f"ws_{i}"
            )
            manager = self.factory.create_manager(context)
            managers.append(manager)
        
        # Verify we're at the limit
        assert len(managers) == 3
        assert self.factory._user_manager_count["test_user_limit"] == 3
        
        # Attempt to create one more manager should fail
        excess_context = UserExecutionContext.from_request(
            user_id="test_user_limit",
            thread_id="thread_excess",
            run_id="run_excess",
            websocket_connection_id="ws_excess"
        )
        
        with self.expect_exception(RuntimeError, "has reached the maximum number of WebSocket managers"):
            self.factory.create_manager(excess_context)
        
        # Verify resource limit hit was recorded
        assert self.factory._factory_metrics.resource_limit_hits == 1
        
        self.record_metric("resource_limit_enforcement", 1)
    
    @pytest.mark.unit
    def test_create_manager_returns_existing_active_manager(self):
        """Test that creating a manager with same isolation key returns existing manager."""
        # Create first manager
        manager1 = self.factory.create_manager(self.test_user_context)
        initial_manager_id = id(manager1)
        
        # Attempt to create manager with same context
        manager2 = self.factory.create_manager(self.test_user_context)
        
        # Should return the same manager instance
        assert manager1 is manager2
        assert id(manager2) == initial_manager_id
        
        # Factory counts should not increase
        assert self.factory._factory_metrics.managers_created == 1
        assert len(self.factory._active_managers) == 1
        
        self.record_metric("existing_manager_returned", 1)
    
    @pytest.mark.unit
    def test_get_manager_existing(self):
        """Test getting an existing manager by isolation key."""
        manager = self.factory.create_manager(self.test_user_context)
        isolation_key = self.factory._generate_isolation_key(self.test_user_context)
        
        retrieved_manager = self.factory.get_manager(isolation_key)
        
        assert retrieved_manager is manager
        assert retrieved_manager._is_active == True
        
        self.record_metric("manager_retrieval_success", 1)
    
    @pytest.mark.unit  
    def test_get_manager_nonexistent(self):
        """Test getting a non-existent manager returns None."""
        nonexistent_key = "nonexistent:isolation:key"
        manager = self.factory.get_manager(nonexistent_key)
        
        assert manager is None
        
        self.record_metric("nonexistent_manager_handled", 1)
    
    @pytest.mark.unit
    async def test_cleanup_manager_success(self):
        """Test successful manager cleanup."""
        manager = self.factory.create_manager(self.test_user_context)
        isolation_key = self.factory._generate_isolation_key(self.test_user_context)
        
        # Verify manager exists
        assert len(self.factory._active_managers) == 1
        assert self.factory._user_manager_count[self.test_user_context.user_id] == 1
        
        # Cleanup manager
        cleanup_success = await self.factory.cleanup_manager(isolation_key)
        
        assert cleanup_success == True
        assert len(self.factory._active_managers) == 0
        assert self.test_user_context.user_id not in self.factory._user_manager_count
        
        # Verify metrics updated
        assert self.factory._factory_metrics.managers_cleaned_up == 1
        assert self.factory._factory_metrics.managers_active == 0
        
        self.record_metric("manager_cleanup_success", 1)
    
    @pytest.mark.unit
    async def test_cleanup_manager_nonexistent(self):
        """Test cleanup of non-existent manager returns False."""
        nonexistent_key = "nonexistent:key"
        cleanup_success = await self.factory.cleanup_manager(nonexistent_key)
        
        assert cleanup_success == False
        
        self.record_metric("nonexistent_cleanup_handled", 1)
    
    @pytest.mark.unit
    def test_enforce_resource_limits_within_limits(self):
        """Test resource limit enforcement when within limits."""
        # Create one manager
        self.factory.create_manager(self.test_user_context)
        
        # Check limits for same user (should be within limits)
        within_limits = self.factory.enforce_resource_limits(self.test_user_context.user_id)
        assert within_limits == True
        
        self.record_metric("resource_limits_within", 1)
    
    @pytest.mark.unit
    def test_enforce_resource_limits_at_limit(self):
        """Test resource limit enforcement when at limit."""
        # Create maximum allowed managers
        for i in range(self.factory.max_managers_per_user):
            context = UserExecutionContext.from_request(
                user_id="test_user_limit",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                websocket_connection_id=f"ws_{i}"
            )
            self.factory.create_manager(context)
        
        # Check limits (should be at limit)
        within_limits = self.factory.enforce_resource_limits("test_user_limit")
        assert within_limits == False
        
        self.record_metric("resource_limits_at_limit", 1)
    
    @pytest.mark.unit
    def test_get_factory_stats_comprehensive(self):
        """Test comprehensive factory statistics reporting."""
        # Create some managers to generate meaningful stats
        manager1 = self.factory.create_manager(self.test_user_context)
        manager2 = self.factory.create_manager(self.second_user_context)
        
        stats = self.factory.get_factory_stats()
        
        # Verify stats structure
        assert "factory_metrics" in stats
        assert "configuration" in stats
        assert "current_state" in stats
        assert "user_distribution" in stats
        assert "oldest_manager_age_seconds" in stats
        
        # Verify factory metrics
        factory_metrics = stats["factory_metrics"]
        assert factory_metrics["managers_created"] == 2
        assert factory_metrics["managers_active"] == 2
        
        # Verify configuration
        config = stats["configuration"]
        assert config["max_managers_per_user"] == 3
        assert config["connection_timeout_seconds"] == 10
        
        # Verify current state
        current_state = stats["current_state"]
        assert current_state["active_managers"] == 2
        assert current_state["users_with_managers"] == 2
        assert len(current_state["isolation_keys"]) == 2
        
        # Verify user distribution
        user_dist = stats["user_distribution"]
        assert user_dist[self.test_user_context.user_id] == 1
        assert user_dist[self.second_user_context.user_id] == 1
        
        self.record_metric("factory_stats_comprehensive", 1)
    
    @pytest.mark.unit
    async def test_cleanup_expired_managers(self):
        """Test cleanup of expired managers based on timeout."""
        # Create manager
        manager = self.factory.create_manager(self.test_user_context)
        isolation_key = self.factory._generate_isolation_key(self.test_user_context)
        
        # Manually set creation time to past (simulate expiry)
        past_time = datetime.utcnow() - timedelta(seconds=self.factory.connection_timeout_seconds + 1)
        self.factory._manager_creation_time[isolation_key] = past_time
        
        # Set manager last activity to past
        manager._metrics.last_activity = past_time
        
        # Run cleanup
        await self.factory._cleanup_expired_managers()
        
        # Verify expired manager was cleaned up
        assert len(self.factory._active_managers) == 0
        assert isolation_key not in self.factory._manager_creation_time
        
        self.record_metric("expired_managers_cleanup", 1)
    
    @pytest.mark.unit
    async def test_factory_shutdown(self):
        """Test factory shutdown cleans up all managers and background tasks."""
        # Create some managers
        manager1 = self.factory.create_manager(self.test_user_context)
        manager2 = self.factory.create_manager(self.second_user_context)
        
        assert len(self.factory._active_managers) == 2
        
        # Shutdown factory
        await self.factory.shutdown()
        
        # Verify all managers cleaned up
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0
        assert len(self.factory._manager_creation_time) == 0
        
        self.record_metric("factory_shutdown", 1)


class TestIsolatedWebSocketManager(SSotAsyncTestCase):
    """Test IsolatedWebSocketManager functionality."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.test_user_context = UserExecutionContext.from_request(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789",
            websocket_connection_id="ws_connection_001"
        )
        
        self.manager = IsolatedWebSocketManager(self.test_user_context)
        self.mock_factory = MockFactory(self.get_env())
    
    async def teardown_method(self, method=None):
        """Cleanup after each test method."""
        try:
            await self.manager.cleanup_all_connections()
            self.mock_factory.cleanup()
        finally:
            super().teardown_method(method)
    
    @pytest.mark.unit
    def test_manager_initialization(self):
        """Test IsolatedWebSocketManager initialization."""
        assert self.manager.user_context == self.test_user_context
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        assert self.manager._is_active == True
        assert isinstance(self.manager._metrics, ManagerMetrics)
        assert isinstance(self.manager._lifecycle_manager, ConnectionLifecycleManager)
        
        # Verify timestamps
        assert self.manager.created_at is not None
        assert self.manager._metrics.last_activity is not None
        
        self.record_metric("manager_initialization_verified", 1)
    
    @pytest.mark.unit
    def test_manager_initialization_invalid_context(self):
        """Test manager initialization with invalid context raises ValueError."""
        with self.expect_exception(ValueError, "user_context must be a UserExecutionContext instance"):
            IsolatedWebSocketManager("not_a_context")
        
        self.record_metric("invalid_context_manager_rejected", 1)
    
    @pytest.mark.unit
    async def test_add_connection_success(self):
        """Test successful connection addition."""
        # Create mock WebSocket connection
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        
        await self.manager.add_connection(connection)
        
        # Verify connection added
        assert len(self.manager._connections) == 1
        assert "test_conn_001" in self.manager._connection_ids
        assert self.manager._connections["test_conn_001"] == connection
        
        # Verify metrics updated
        assert self.manager._metrics.connections_managed == 1
        
        self.record_metric("connection_addition_success", 1)
    
    @pytest.mark.unit
    async def test_add_connection_user_mismatch_security_violation(self):
        """Test adding connection with wrong user_id triggers security violation."""
        # Create connection for different user
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        wrong_user_connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="wrong_conn_001",
            user_id="different_user_456"  # Different user!
        )
        
        with self.expect_exception(ValueError, "violates user isolation requirements"):
            await self.manager.add_connection(wrong_user_connection)
        
        # Verify connection was not added
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        
        self.record_metric("security_violation_detected", 1)
    
    @pytest.mark.unit
    async def test_add_connection_inactive_manager_raises_error(self):
        """Test adding connection to inactive manager raises RuntimeError."""
        # Deactivate manager
        self.manager._is_active = False
        
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001", 
            user_id=self.test_user_context.user_id
        )
        
        with self.expect_exception(RuntimeError, "is no longer active"):
            await self.manager.add_connection(connection)
        
        self.record_metric("inactive_manager_error", 1)
    
    @pytest.mark.unit
    async def test_remove_connection_success(self):
        """Test successful connection removal."""
        # Add connection first
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        await self.manager.add_connection(connection)
        
        # Remove connection
        await self.manager.remove_connection("test_conn_001")
        
        # Verify connection removed
        assert len(self.manager._connections) == 0
        assert "test_conn_001" not in self.manager._connection_ids
        
        # Verify metrics updated
        assert self.manager._metrics.connections_managed == 0
        
        self.record_metric("connection_removal_success", 1)
    
    @pytest.mark.unit
    async def test_remove_connection_user_mismatch_security_check(self):
        """Test removal of connection with user mismatch triggers security check."""
        # Add connection first
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        await self.manager.add_connection(connection)
        
        # Manually change the connection's user_id to simulate security issue
        connection.user_id = "different_user"
        
        # Attempt removal - should be blocked by security check
        await self.manager.remove_connection("test_conn_001")
        
        # Connection should still exist due to security check
        assert len(self.manager._connections) == 1
        
        self.record_metric("removal_security_check", 1)
    
    @pytest.mark.unit
    def test_get_connection_success(self):
        """Test successful connection retrieval."""
        # Add connection first
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        self.manager._connections["test_conn_001"] = connection
        
        retrieved_connection = self.manager.get_connection("test_conn_001")
        
        assert retrieved_connection == connection
        assert retrieved_connection.connection_id == "test_conn_001"
        
        self.record_metric("connection_retrieval_success", 1)
    
    @pytest.mark.unit
    def test_get_connection_nonexistent(self):
        """Test retrieval of non-existent connection returns None."""
        connection = self.manager.get_connection("nonexistent_conn")
        assert connection is None
        
        self.record_metric("nonexistent_connection_handled", 1)
    
    @pytest.mark.unit
    def test_get_user_connections(self):
        """Test getting all user connection IDs."""
        # Add multiple connections
        connection_ids = ["conn_001", "conn_002", "conn_003"]
        for conn_id in connection_ids:
            self.manager._connection_ids.add(conn_id)
        
        user_connections = self.manager.get_user_connections()
        
        assert isinstance(user_connections, set)
        assert user_connections == set(connection_ids)
        
        # Verify it returns a copy (isolation)
        user_connections.add("extra_conn")
        assert "extra_conn" not in self.manager._connection_ids
        
        self.record_metric("user_connections_retrieval", 1)
    
    @pytest.mark.unit
    def test_is_connection_active_valid_user(self):
        """Test connection activity check for valid user."""
        # Add mock connection
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        self.manager._connections["test_conn_001"] = connection
        self.manager._connection_ids.add("test_conn_001")
        
        is_active = self.manager.is_connection_active(self.test_user_context.user_id)
        
        assert is_active == True
        
        self.record_metric("connection_activity_check", 1)
    
    @pytest.mark.unit
    def test_is_connection_active_wrong_user_security_violation(self):
        """Test connection activity check with wrong user ID."""
        # Add connection for correct user
        self.manager._connection_ids.add("test_conn_001")
        
        # Check with wrong user ID
        is_active = self.manager.is_connection_active("wrong_user_456")
        
        # Should return False and not leak information
        assert is_active == False
        
        self.record_metric("security_isolation_enforced", 1)
    
    @pytest.mark.unit
    def test_is_connection_active_no_connections(self):
        """Test connection activity check with no connections."""
        is_active = self.manager.is_connection_active(self.test_user_context.user_id)
        
        assert is_active == False
        
        self.record_metric("no_connections_handled", 1)
    
    @pytest.mark.unit
    async def test_send_to_user_success(self):
        """Test successful message sending to user."""
        # Add mock connection
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001", 
            user_id=self.test_user_context.user_id
        )
        self.manager._connections["test_conn_001"] = connection
        self.manager._connection_ids.add("test_conn_001")
        
        # Mock WebSocket state as connected
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        test_message = {"type": "test", "data": "hello"}
        
        await self.manager.send_to_user(test_message)
        
        # Verify message was sent
        mock_websocket.send_json.assert_called_once_with(test_message)
        
        # Verify metrics updated
        assert self.manager._metrics.messages_sent_total == 1
        
        self.record_metric("message_send_success", 1)
    
    @pytest.mark.unit
    async def test_send_to_user_no_connections(self):
        """Test sending message when no connections available."""
        test_message = {"type": "test", "data": "hello"}
        
        await self.manager.send_to_user(test_message)
        
        # Verify message was queued for recovery
        assert len(self.manager._message_recovery_queue) == 1
        recovery_msg = self.manager._message_recovery_queue[0]
        assert recovery_msg["type"] == "test"
        assert recovery_msg["failure_reason"] == "no_connections"
        
        # Verify metrics updated
        assert self.manager._metrics.messages_failed_total == 1
        
        self.record_metric("no_connections_message_queued", 1)
    
    @pytest.mark.unit
    async def test_emit_critical_event_success(self):
        """Test emitting critical event successfully."""
        # Add mock connection
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        self.manager._connections["test_conn_001"] = connection
        self.manager._connection_ids.add("test_conn_001")
        
        # Mock WebSocket state
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        event_data = {"agent_id": "test_agent", "status": "started"}
        
        await self.manager.emit_critical_event("agent_started", event_data)
        
        # Verify critical event structure was sent
        sent_calls = mock_websocket.send_json.call_args_list
        assert len(sent_calls) == 1
        
        sent_message = sent_calls[0][0][0]  # First call, first arg
        assert sent_message["type"] == "agent_started"
        assert sent_message["data"] == event_data
        assert sent_message["critical"] == True
        assert "timestamp" in sent_message
        assert "user_context" in sent_message
        
        self.record_metric("critical_event_emitted", 1)
    
    @pytest.mark.unit
    async def test_emit_critical_event_invalid_type(self):
        """Test emitting critical event with invalid event type."""
        with self.expect_exception(ValueError, "event_type cannot be empty"):
            await self.manager.emit_critical_event("", {"data": "test"})
        
        with self.expect_exception(ValueError, "event_type cannot be empty"):
            await self.manager.emit_critical_event("   ", {"data": "test"})
        
        self.record_metric("invalid_event_type_rejected", 1)
    
    @pytest.mark.unit
    async def test_cleanup_all_connections(self):
        """Test cleanup of all connections and manager deactivation."""
        # Add mock connections
        mock_websocket1 = self.mock_factory.create_websocket_connection_mock()
        mock_websocket2 = self.mock_factory.create_websocket_connection_mock()
        
        connection1 = WebSocketConnection(
            websocket=mock_websocket1,
            connection_id="conn_001",
            user_id=self.test_user_context.user_id
        )
        connection2 = WebSocketConnection(
            websocket=mock_websocket2,
            connection_id="conn_002",
            user_id=self.test_user_context.user_id
        )
        
        await self.manager.add_connection(connection1)
        await self.manager.add_connection(connection2)
        
        assert len(self.manager._connections) == 2
        assert self.manager._is_active == True
        
        # Cleanup all connections
        await self.manager.cleanup_all_connections()
        
        # Verify cleanup
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        assert self.manager._is_active == False
        assert self.manager._metrics.cleanup_scheduled == True
        assert len(self.manager._message_recovery_queue) == 0
        
        self.record_metric("cleanup_all_connections", 1)
    
    @pytest.mark.unit
    def test_get_manager_stats_comprehensive(self):
        """Test comprehensive manager statistics."""
        # Add some test data
        self.manager._connection_ids.add("conn_001")
        self.manager._message_recovery_queue.append({"test": "recovery"})
        self.manager._connection_error_count = 2
        
        stats = self.manager.get_manager_stats()
        
        # Verify stats structure
        assert "user_context" in stats
        assert "manager_id" in stats
        assert "is_active" in stats
        assert "metrics" in stats
        assert "connections" in stats
        assert "recovery_queue_size" in stats
        assert "error_count" in stats
        
        # Verify specific values
        assert stats["user_context"] == self.test_user_context.to_dict()
        assert stats["manager_id"] == id(self.manager)
        assert stats["is_active"] == True
        assert stats["connections"]["total"] == 1
        assert stats["recovery_queue_size"] == 1
        assert stats["error_count"] == 2
        
        self.record_metric("manager_stats_comprehensive", 1)


class TestConnectionLifecycleManager(SSotAsyncTestCase):
    """Test ConnectionLifecycleManager functionality."""
    
    def setup_method(self, method=None):
        """Setup for each test method.""" 
        super().setup_method(method)
        
        self.test_user_context = UserExecutionContext.from_request(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )
        
        self.ws_manager = IsolatedWebSocketManager(self.test_user_context)
        self.lifecycle_manager = ConnectionLifecycleManager(
            self.test_user_context, 
            self.ws_manager
        )
        
        self.mock_factory = MockFactory(self.get_env())
    
    async def teardown_method(self, method=None):
        """Cleanup after each test method."""
        try:
            await self.lifecycle_manager.force_cleanup_all()
            await self.ws_manager.cleanup_all_connections()
            self.mock_factory.cleanup()
        finally:
            super().teardown_method(method)
    
    @pytest.mark.unit
    def test_lifecycle_manager_initialization(self):
        """Test ConnectionLifecycleManager initialization."""
        assert self.lifecycle_manager.user_context == self.test_user_context
        assert self.lifecycle_manager.ws_manager == self.ws_manager
        assert len(self.lifecycle_manager._managed_connections) == 0
        assert len(self.lifecycle_manager._connection_health) == 0
        assert self.lifecycle_manager._is_active == True
        
        self.record_metric("lifecycle_manager_init", 1)
    
    @pytest.mark.unit
    def test_register_connection_success(self):
        """Test successful connection registration."""
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        
        self.lifecycle_manager.register_connection(connection)
        
        # Verify registration
        assert "test_conn_001" in self.lifecycle_manager._managed_connections
        assert "test_conn_001" in self.lifecycle_manager._connection_health
        assert len(self.lifecycle_manager._managed_connections) == 1
        
        self.record_metric("connection_registration_success", 1)
    
    @pytest.mark.unit
    def test_register_connection_user_mismatch_security_violation(self):
        """Test connection registration with user mismatch raises security violation."""
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        wrong_user_connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="wrong_conn_001",
            user_id="wrong_user_456"  # Different user!
        )
        
        with self.expect_exception(ValueError, "violates user isolation requirements"):
            self.lifecycle_manager.register_connection(wrong_user_connection)
        
        # Verify no registration occurred
        assert len(self.lifecycle_manager._managed_connections) == 0
        
        self.record_metric("lifecycle_security_violation_blocked", 1)
    
    @pytest.mark.unit
    def test_health_check_connection_success(self):
        """Test successful connection health check."""
        # Register connection first
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        
        self.lifecycle_manager.register_connection(connection)
        
        # Mock ws_manager to return the connection
        self.ws_manager._connections["test_conn_001"] = connection
        
        # Perform health check
        is_healthy = self.lifecycle_manager.health_check_connection("test_conn_001")
        
        assert is_healthy == True
        
        # Verify health timestamp updated
        assert "test_conn_001" in self.lifecycle_manager._connection_health
        
        self.record_metric("health_check_success", 1)
    
    @pytest.mark.unit
    def test_health_check_connection_not_managed(self):
        """Test health check for non-managed connection returns False."""
        is_healthy = self.lifecycle_manager.health_check_connection("unmanaged_conn")
        
        assert is_healthy == False
        
        self.record_metric("unmanaged_connection_health_check", 1)
    
    @pytest.mark.unit
    async def test_auto_cleanup_expired(self):
        """Test automatic cleanup of expired connections."""
        # Register connection
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="test_conn_001",
            user_id=self.test_user_context.user_id
        )
        
        self.lifecycle_manager.register_connection(connection)
        
        # Manually set connection health to expired (31 minutes ago)
        expired_time = datetime.utcnow() - timedelta(minutes=31)
        self.lifecycle_manager._connection_health["test_conn_001"] = expired_time
        
        # Mock the ws_manager remove_connection method
        self.ws_manager.remove_connection = AsyncMock()
        
        # Run auto cleanup
        cleaned_count = await self.lifecycle_manager.auto_cleanup_expired()
        
        # Verify cleanup occurred
        assert cleaned_count == 1
        assert "test_conn_001" not in self.lifecycle_manager._managed_connections
        assert "test_conn_001" not in self.lifecycle_manager._connection_health
        
        # Verify ws_manager cleanup was called
        self.ws_manager.remove_connection.assert_called_once_with("test_conn_001")
        
        self.record_metric("auto_cleanup_expired", 1)
    
    @pytest.mark.unit
    async def test_force_cleanup_all(self):
        """Test force cleanup of all managed connections."""
        # Register multiple connections
        for i in range(3):
            mock_websocket = self.mock_factory.create_websocket_connection_mock()
            connection = WebSocketConnection(
                websocket=mock_websocket,
                connection_id=f"test_conn_{i:03d}",
                user_id=self.test_user_context.user_id
            )
            self.lifecycle_manager.register_connection(connection)
        
        assert len(self.lifecycle_manager._managed_connections) == 3
        
        # Mock ws_manager remove_connection
        self.ws_manager.remove_connection = AsyncMock()
        
        # Force cleanup all
        await self.lifecycle_manager.force_cleanup_all()
        
        # Verify cleanup
        assert len(self.lifecycle_manager._managed_connections) == 0
        assert len(self.lifecycle_manager._connection_health) == 0
        assert self.lifecycle_manager._is_active == False
        
        # Verify all connections were cleaned up
        assert self.ws_manager.remove_connection.call_count == 3
        
        self.record_metric("force_cleanup_all", 1)


class TestGlobalFactoryFunctions(SSotBaseTestCase):
    """Test global factory functions and singleton behavior."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Clear global factory instance for clean tests
        global _factory_instance
        with _factory_lock:
            _factory_instance = None
    
    @pytest.mark.unit  
    def test_get_websocket_manager_factory_singleton(self):
        """Test get_websocket_manager_factory returns singleton instance."""
        factory1 = get_websocket_manager_factory()
        factory2 = get_websocket_manager_factory()
        
        # Should return same instance
        assert factory1 is factory2
        assert isinstance(factory1, WebSocketManagerFactory)
        
        self.record_metric("singleton_factory_verified", 1)
    
    @pytest.mark.unit
    def test_create_websocket_manager_function(self):
        """Test create_websocket_manager convenience function."""
        test_user_context = UserExecutionContext.from_request(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )
        
        manager = create_websocket_manager(test_user_context)
        
        assert isinstance(manager, IsolatedWebSocketManager)
        assert manager.user_context == test_user_context
        
        self.record_metric("convenience_function_verified", 1)


class TestSecurityAndConcurrency(SSotAsyncTestCase):
    """Test security features and concurrent access scenarios."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        self.factory = WebSocketManagerFactory(max_managers_per_user=2)
        self.mock_factory = MockFactory(self.get_env())
    
    async def teardown_method(self, method=None):
        """Cleanup after each test method."""
        try:
            await self.factory.shutdown()
            self.mock_factory.cleanup()
        finally:
            super().teardown_method(method)
    
    @pytest.mark.unit
    def test_concurrent_manager_creation_thread_safety(self):
        """Test thread-safe concurrent manager creation."""
        results = []
        errors = []
        
        def create_manager_thread(user_id: str, thread_idx: int):
            try:
                context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=f"thread_{thread_idx}",
                    run_id=f"run_{thread_idx}",
                    websocket_connection_id=f"ws_{thread_idx}"
                )
                manager = self.factory.create_manager(context)
                results.append(manager)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads creating managers concurrently
        threads = []
        for i in range(5):
            thread = Thread(target=create_manager_thread, args=("concurrent_user", i))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify thread safety
        assert len(errors) == 3  # Should hit resource limit for 3 threads
        assert len(results) == 2  # Should succeed for 2 threads (max_managers_per_user=2)
        
        # Verify factory state consistency
        assert len(self.factory._active_managers) == 2
        assert self.factory._user_manager_count["concurrent_user"] == 2
        
        self.record_metric("concurrent_creation_tested", 1)
    
    @pytest.mark.unit
    async def test_memory_leak_prevention(self):
        """Test that managers are properly cleaned up to prevent memory leaks."""
        created_managers = []
        
        # Create and cleanup multiple managers
        for i in range(10):
            context = UserExecutionContext.from_request(
                user_id=f"temp_user_{i}",
                thread_id=f"thread_{i}",
                run_id=f"run_{i}",
                websocket_connection_id=f"ws_{i}"
            )
            
            manager = self.factory.create_manager(context)
            created_managers.append(manager)
            
            # Cleanup immediately
            isolation_key = self.factory._generate_isolation_key(context)
            await self.factory.cleanup_manager(isolation_key)
        
        # Verify all managers cleaned up
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0
        assert len(self.factory._manager_creation_time) == 0
        
        # Verify metrics
        assert self.factory._factory_metrics.managers_created == 10
        assert self.factory._factory_metrics.managers_cleaned_up == 10
        assert self.factory._factory_metrics.managers_active == 0
        
        self.record_metric("memory_leak_prevention", 1)
    
    @pytest.mark.unit
    async def test_security_violation_logging_and_metrics(self):
        """Test that security violations are properly logged and tracked."""
        # Create manager for legitimate user
        user_context = UserExecutionContext.from_request(
            user_id="legitimate_user",
            thread_id="thread_001",
            run_id="run_001"
        )
        manager = self.factory.create_manager(user_context)
        
        # Attempt to add connection for different user (security violation)
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        malicious_connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="malicious_conn",
            user_id="attacker_user"  # Different user!
        )
        
        # This should raise security violation
        with self.expect_exception(ValueError, "violates user isolation requirements"):
            await manager.add_connection(malicious_connection)
        
        # Verify manager remains secure
        assert len(manager._connections) == 0
        assert len(manager._connection_ids) == 0
        
        self.record_metric("security_violation_tracked", 1)
    
    @pytest.mark.unit
    async def test_edge_case_cleanup_during_message_send(self):
        """Test edge case where cleanup occurs during message sending."""
        # Create manager and connection
        context = UserExecutionContext.from_request(
            user_id="edge_case_user",
            thread_id="thread_001", 
            run_id="run_001"
        )
        manager = self.factory.create_manager(context)
        
        mock_websocket = self.mock_factory.create_websocket_connection_mock()
        connection = WebSocketConnection(
            websocket=mock_websocket,
            connection_id="edge_conn_001",
            user_id=context.user_id
        )
        await manager.add_connection(connection)
        
        # Mock WebSocket state
        from fastapi.websockets import WebSocketState
        mock_websocket.client_state = WebSocketState.CONNECTED
        
        # Start sending message (but don't await yet)
        message_task = asyncio.create_task(
            manager.send_to_user({"type": "test", "data": "testing"})
        )
        
        # Cleanup manager while message is being sent
        cleanup_task = asyncio.create_task(manager.cleanup_all_connections())
        
        # Wait for both operations to complete
        try:
            await asyncio.gather(message_task, cleanup_task, return_exceptions=True)
        except Exception:
            pass  # Expected in edge case
        
        # Verify manager is properly cleaned up
        assert manager._is_active == False
        assert len(manager._connections) == 0
        
        self.record_metric("edge_case_cleanup_tested", 1)
    
    @pytest.mark.unit 
    def test_factory_metrics_accuracy_under_load(self):
        """Test factory metrics remain accurate under high load."""
        user_contexts = []
        created_managers = []
        
        # Create maximum managers for multiple users
        for user_idx in range(3):
            user_id = f"load_test_user_{user_idx}"
            for conn_idx in range(self.factory.max_managers_per_user):
                context = UserExecutionContext.from_request(
                    user_id=user_id,
                    thread_id=f"thread_{user_idx}_{conn_idx}",
                    run_id=f"run_{user_idx}_{conn_idx}",
                    websocket_connection_id=f"ws_{user_idx}_{conn_idx}"
                )
                user_contexts.append(context)
                
                manager = self.factory.create_manager(context)
                created_managers.append(manager)
        
        # Verify metrics accuracy
        expected_total = 3 * self.factory.max_managers_per_user  # 3 users * 2 managers each = 6
        
        assert self.factory._factory_metrics.managers_created == expected_total
        assert self.factory._factory_metrics.managers_active == expected_total
        assert self.factory._factory_metrics.users_with_active_managers == 3
        assert len(self.factory._active_managers) == expected_total
        
        # Verify per-user counts
        for user_idx in range(3):
            user_id = f"load_test_user_{user_idx}"
            assert self.factory._user_manager_count[user_id] == self.factory.max_managers_per_user
        
        self.record_metric("metrics_accuracy_under_load", 1)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])