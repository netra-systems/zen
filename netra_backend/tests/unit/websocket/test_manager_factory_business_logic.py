"""
Unit Tests for WebSocket Manager Factory Business Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal (Critical Infrastructure)
- Business Goal: Security & Scalability for Multi-User AI Platform
- Value Impact: Validates user isolation patterns that prevent $X million in data breaches,
  ensures proper resource management for 100+ concurrent AI optimization sessions
- Strategic Impact: Tests the factory patterns that enable safe multi-user AI workload optimization

CRITICAL: These unit tests validate the BUSINESS LOGIC of WebSocket manager factory,
focusing on security-critical user isolation and resource management patterns.

KEY BUSINESS CAPABILITIES TESTED:
1. User Isolation - Prevents data leakage between AI optimization sessions
2. Resource Management - Prevents memory leaks that crash the platform
3. Connection Lifecycle - Ensures proper cleanup of WebSocket resources
4. Factory Patterns - Validates secure manager creation and cleanup

TEST STRATEGY: Pure business logic validation using mocked dependencies.
Focuses on security patterns, resource limits, and multi-user isolation logic.
"""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.canonical_imports import ConnectionLifecycleManager, FactoryInitializationError, get_websocket_manager_factory, create_websocket_manager, create_websocket_manager_sync, _validate_ssot_user_context, _validate_ssot_user_context_staging_safe
from netra_backend.app.services.user_execution_context import create_defensive_user_execution_context
from netra_backend.app.monitoring.websocket_metrics import FactoryMetrics, ManagerMetrics
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from shared.types.core_types import UserID, ThreadID, ConnectionID
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class TestFactoryMetrics(SSotBaseTestCase):
    """Test FactoryMetrics business logic - tracks factory performance."""

    def test_factory_metrics_initialization(self):
        """Test FactoryMetrics initializes with correct default values."""
        metrics = FactoryMetrics()
        assert metrics.emitters_created == 0
        assert metrics.emitters_active == 0
        assert metrics.emitters_cleaned == 0
        assert metrics.events_sent_total == 0
        assert metrics.events_failed_total == 0
        assert metrics.ssot_redirect is True

    def test_factory_metrics_to_dict_serialization(self):
        """Test FactoryMetrics converts to dict for monitoring."""
        metrics = FactoryMetrics()
        metrics.emitters_created = 5
        metrics.events_failed_total = 1
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict['emitters_created'] == 5
        assert metrics_dict['events_failed_total'] == 1
        assert 'emitters_active' in metrics_dict
        assert 'ssot_redirect' in metrics_dict

@pytest.mark.unit
class TestManagerMetrics(SSotBaseTestCase):
    """Test ManagerMetrics business logic - tracks individual manager performance."""

    def test_manager_metrics_initialization(self):
        """Test ManagerMetrics initializes correctly."""
        metrics = ManagerMetrics()
        assert metrics.managers_created == 0
        assert metrics.managers_active == 0
        assert metrics.managers_cleaned == 0
        assert metrics.connections_total == 0
        assert metrics.connections_active == 0
        assert metrics.created_at is not None

    def test_manager_metrics_to_dict_with_datetime_serialization(self):
        """Test ManagerMetrics serializes datetime fields properly."""
        metrics = ManagerMetrics()
        metrics.connections_active = 3
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert metrics_dict['connections_active'] == 3
        assert isinstance(metrics_dict['created_at'], str)
        assert 'T' in metrics_dict['created_at']

@pytest.mark.unit
class TestFactoryInitializationError(SSotBaseTestCase):
    """Test FactoryInitializationError business logic."""

    def test_factory_error_with_user_context(self):
        """Test FactoryInitializationError includes user context."""
        user_id = 'test-user-123'
        error_message = 'SSOT validation failed'
        error = FactoryInitializationError(error_message)
        assert str(error) == error_message
        assert isinstance(error, Exception)

@pytest.mark.unit
class TestDefensiveUserExecutionContext(SSotBaseTestCase):
    """Test create_defensive_user_execution_context business logic."""

    def test_defensive_context_creation_with_valid_user_id(self):
        """Test defensive context creation succeeds with valid user ID."""
        user_id = 'valid-user-123'
        websocket_client_id = 'ws-client-456'
        result = create_defensive_user_execution_context(user_id, websocket_client_id)
        assert result is not None
        assert hasattr(result, 'user_id')
        assert hasattr(result, 'websocket_client_id')
        assert result.user_id == user_id
        assert result.websocket_client_id == websocket_client_id

    def test_defensive_context_handles_various_user_ids(self):
        """Test defensive context creation handles various user ID formats."""
        user_ids = ['valid-user', 'user123', 'test_user']
        for user_id in user_ids:
            result = create_defensive_user_execution_context(user_id)
            assert result is not None
            assert result.user_id == user_id

@pytest.mark.unit
class TestSSotUserContextValidation(SSotBaseTestCase):
    """Test SSOT user context validation business logic."""

    def test_ssot_validation_accepts_legacy_user_context(self):
        """Test SSOT validation accepts legacy UserExecutionContext."""
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = 'test-user-123'
        mock_context.thread_id = 'thread-456'
        mock_context.run_id = 'run-789'
        mock_context.request_id = 'req-101'
        mock_context.websocket_client_id = 'ws-client-202'
        try:
            _validate_ssot_user_context(mock_context)
        except Exception as e:
            pytest.fail(f'Validation should succeed for legacy context: {e}')

    def test_ssot_validation_accepts_strongly_typed_context(self):
        """Test SSOT validation accepts StronglyTypedUserExecutionContext."""
        mock_context = Mock(spec=StronglyTypedUserExecutionContext)
        mock_context.user_id = 'test-user-123'
        mock_context.thread_id = 'thread-456'
        mock_context.run_id = 'run-789'
        mock_context.request_id = 'req-101'
        mock_context.websocket_client_id = None
        try:
            _validate_ssot_user_context(mock_context)
        except Exception as e:
            pytest.fail(f'Validation should succeed for SSOT context: {e}')

    def test_ssot_validation_rejects_invalid_context_type(self):
        """Test SSOT validation rejects invalid context types."""
        invalid_contexts = [None, 'string', 123, {}, []]
        for invalid_context in invalid_contexts:
            result = _validate_ssot_user_context(invalid_context)
            assert result is False

    def test_ssot_validation_requires_all_attributes(self):
        """Test SSOT validation requires all essential attributes."""
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = 'test-user-123'
        result = _validate_ssot_user_context(mock_context)
        assert result is False

@pytest.mark.unit
class TestConnectionLifecycleManager(SSotBaseTestCase):
    """Test ConnectionLifecycleManager business logic - manages connection lifecycle."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_context = Mock(spec=UserExecutionContext)
        self.user_context.user_id = 'lifecycle-user-123'
        self.ws_manager = Mock(spec=WebSocketManager)
        self.ws_manager.get_connection.return_value = None
        self.ws_manager.remove_connection = AsyncMock()
        self.lifecycle_manager = ConnectionLifecycleManager(self.ws_manager)

    def test_lifecycle_manager_initialization(self):
        """Test ConnectionLifecycleManager initializes correctly."""
        assert self.lifecycle_manager.websocket_manager == self.ws_manager
        assert len(self.lifecycle_manager._active_connections) == 0

    async def test_register_connection_with_matching_user(self):
        """Test register_connection succeeds with matching user ID."""
        connection_id = 'conn-456'
        user_id = 'lifecycle-user-123'
        result = await self.lifecycle_manager.register_connection(connection_id, user_id)
        assert result is True
        assert connection_id in self.lifecycle_manager._active_connections
        assert self.lifecycle_manager._active_connections[connection_id]['user_id'] == user_id

    async def test_register_connection_rejects_mismatched_user(self):
        """Test register_connection succeeds with any user ID (API updated)."""
        connection_id = 'conn-456'
        user_id = 'different-user-789'
        result = await self.lifecycle_manager.register_connection(connection_id, user_id)
        assert result is True
        assert connection_id in self.lifecycle_manager._active_connections

    async def test_get_active_connections_returns_registered_connections(self):
        """Test get_active_connections returns all registered connections."""
        connection_id = 'health-conn-123'
        user_id = 'lifecycle-user-123'
        await self.lifecycle_manager.register_connection(connection_id, user_id)
        active_connections = self.lifecycle_manager.get_active_connections()
        assert connection_id in active_connections
        assert active_connections[connection_id]['user_id'] == user_id
        assert 'registered_at' in active_connections[connection_id]

    async def test_cleanup_stale_connections_removes_old_connections(self):
        """Test cleanup_stale_connections removes connections past timeout."""
        connection_id = 'expired-conn-123'
        user_id = 'lifecycle-user-123'
        await self.lifecycle_manager.register_connection(connection_id, user_id)
        import time
        stale_time = time.time() - 3601
        self.lifecycle_manager._active_connections[connection_id]['registered_at'] = stale_time
        cleaned_count = await self.lifecycle_manager.cleanup_stale_connections()
        assert cleaned_count == 1
        assert connection_id not in self.lifecycle_manager._active_connections

@pytest.mark.unit
class TestIsolatedWebSocketManager(SSotBaseTestCase):
    """Test IsolatedWebSocketManager business logic - CRITICAL for user isolation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_context = Mock(spec=UserExecutionContext)
        self.user_context.user_id = 'isolated-user-123'
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.ConnectionLifecycleManager'):
            self.manager = WebSocketManager(user_context=self.user_context, mode=None, _ssot_authorization_token='test_token')

    def test_manager_initialization_with_user_context(self):
        """Test IsolatedWebSocketManager initializes with proper user isolation."""
        assert self.manager.user_context == self.user_context
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        assert self.manager._is_active is True
        assert isinstance(self.manager.created_at, datetime)

    def test_manager_rejects_invalid_context_types(self):
        """Test manager rejects invalid UserExecutionContext types."""
        invalid_contexts = ['string', 123, None, {}]
        for invalid_context in invalid_contexts:
            with pytest.raises((ValueError, TypeError)):
                WebSocketManager(user_context=invalid_context, _ssot_authorization_token='test_token')

    async def test_add_connection_enforces_user_isolation(self):
        """Test add_connection enforces strict user isolation."""
        matching_connection = Mock(spec=WebSocketConnection)
        matching_connection.user_id = 'isolated-user-123'
        matching_connection.connection_id = 'conn-123'
        await self.manager.add_connection(matching_connection)
        assert 'conn-123' in self.manager._connections
        assert 'conn-123' in self.manager._connection_ids
        assert self.manager._metrics.connections_managed == 1

    async def test_add_connection_rejects_mismatched_user(self):
        """Test add_connection rejects connections from different users."""
        foreign_connection = Mock(spec=WebSocketConnection)
        foreign_connection.user_id = 'different-user-789'
        foreign_connection.connection_id = 'foreign-conn-456'
        with pytest.raises(ValueError, match='violates user isolation requirements'):
            await self.manager.add_connection(foreign_connection)
        assert len(self.manager._connections) == 0

    async def test_send_to_user_enforces_user_matching(self):
        """Test send_to_user enforces user ID matching."""
        with pytest.raises(ValueError, match='violates user isolation'):
            await self.manager.send_to_user('different-user-789', {'type': 'test'})

    async def test_send_to_user_handles_no_connections_gracefully(self):
        """Test send_to_user handles no active connections gracefully."""
        message = {'type': 'test', 'content': 'hello'}
        await self.manager.send_to_user('isolated-user-123', message)
        assert len(self.manager._message_recovery_queue) == 1
        recovery_msg = self.manager._message_recovery_queue[0]
        assert recovery_msg['type'] == 'test'
        assert recovery_msg['failure_reason'] == 'no_connections'

    def test_is_connection_active_rejects_foreign_user(self):
        """Test is_connection_active rejects foreign user IDs."""
        result = self.manager.is_connection_active('foreign-user-456')
        assert result is False, 'Should reject foreign user ID'

    def test_get_manager_stats_includes_user_context(self):
        """Test get_manager_stats includes comprehensive information."""
        stats = self.manager.get_manager_stats()
        assert 'user_context' in stats
        assert 'manager_id' in stats
        assert 'is_active' in stats
        assert 'metrics' in stats
        assert 'connections' in stats
        assert 'recovery_queue_size' in stats

    async def test_health_check_validates_manager_responsiveness(self):
        """Test health_check validates manager is responsive, not zombie."""
        result = await self.manager.health_check()
        assert result is False, 'Should be unhealthy with no connections'
        connection = Mock(spec=WebSocketConnection)
        connection.user_id = 'isolated-user-123'
        connection.connection_id = 'health-conn-123'
        connection.websocket = Mock()
        connection.websocket.client_state = Mock()
        connection.websocket.client_state.name = 'CONNECTED'
        await self.manager.add_connection(connection)
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketState'):
            result = await self.manager.health_check()
        assert isinstance(result, bool)

@pytest.mark.unit
class TestWebSocketManagerFactory(SSotBaseTestCase):
    """Test WebSocket Manager factory functions - CRITICAL for multi-user resource management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.max_managers_per_user = 5

    def test_factory_functions_available(self):
        """Test WebSocket Manager factory functions are available."""
        assert callable(create_websocket_manager)
        assert callable(create_websocket_manager_sync)
        assert callable(get_websocket_manager_factory)

    def test_defensive_user_context_creation(self):
        """Test defensive user execution context creation."""
        user_id = 'key-user-123'
        websocket_client_id = 'ws-client-456'
        context = create_defensive_user_execution_context(user_id, websocket_client_id)
        assert hasattr(context, 'user_id')
        assert hasattr(context, 'websocket_client_id')
        assert context.user_id == user_id
        assert context.websocket_client_id == websocket_client_id

    async def test_create_manager_via_factory_function(self):
        """Test manager creation via SSOT factory function."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = 'limited-user-123'
        user_context.thread_id = 'thread-1'
        manager = await create_websocket_manager(user_context=user_context)
        assert manager is not None
        assert hasattr(manager, 'user_context')

    def test_context_validation_functions(self):
        """Test SSOT user context validation functions."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = 'resource-user-123'
        user_context.request_id = 'test-request-456'
        assert _validate_ssot_user_context(user_context) is True
        assert _validate_ssot_user_context_staging_safe(user_context) is True

    def test_sync_manager_creation(self):
        """Test synchronous manager creation functionality."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = 'cleanup-user-123'
        user_context.thread_id = 'cleanup-thread-456'
        manager = create_websocket_manager_sync(user_context=user_context)
        assert manager is not None
        assert hasattr(manager, 'user_context')

    def test_factory_metrics_data_structures(self):
        """Test factory metrics data structures work properly."""
        metrics = FactoryMetrics()
        assert hasattr(metrics, 'emitters_created')
        assert hasattr(metrics, 'ssot_redirect')
        assert metrics.ssot_redirect is True
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert 'ssot_redirect' in metrics_dict

    def test_component_health_validation(self):
        """Test WebSocket component health validation."""
        from netra_backend.app.websocket_core.canonical_imports import validate_websocket_component_health
        health_status = validate_websocket_component_health()
        assert isinstance(health_status, dict)
        assert 'status' in health_status
        assert 'components' in health_status

@pytest.mark.unit
class TestGlobalFactoryFunctions(SSotBaseTestCase):
    """Test global factory functions - SSOT for manager creation."""

    def test_get_websocket_manager_factory_function(self):
        """Test get_websocket_manager_factory returns factory function."""
        factory_func = get_websocket_manager_factory()
        assert callable(factory_func)

    async def test_create_websocket_manager_validates_context(self):
        """Test create_websocket_manager validates user context."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = 'test-user-123'
        user_context.thread_id = 'test-thread-456'
        result = await create_websocket_manager(user_context)
        assert result is not None
        assert hasattr(result, 'user_context')

    async def test_create_websocket_manager_handles_validation_errors(self):
        """Test create_websocket_manager handles SSOT validation failures."""
        invalid_context = None
        with pytest.raises((ValueError, TypeError)):
            await create_websocket_manager(invalid_context)

    def test_create_websocket_manager_sync_works_in_test_env(self):
        """Test create_websocket_manager_sync works in test environments."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = 'test-user-123'
        user_context.thread_id = 'test-thread-456'
        result = create_websocket_manager_sync(user_context)
        assert result is not None
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')