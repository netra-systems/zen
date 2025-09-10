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

# SSOT imports using absolute paths
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    ConnectionLifecycleManager,
    FactoryMetrics,
    ManagerMetrics,
    FactoryInitializationError,
    get_websocket_manager_factory,
    create_websocket_manager,
    create_websocket_manager_sync,
    create_defensive_user_execution_context,
    _validate_ssot_user_context,
    _validate_ssot_user_context_staging_safe
)

# Import WebSocketManager (replacement for removed IsolatedWebSocketManager)
from netra_backend.app.websocket_core.unified_manager import WebSocketManager as IsolatedWebSocketManager
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
        
        assert metrics.managers_created == 0
        assert metrics.managers_active == 0
        assert metrics.managers_cleaned_up == 0
        assert metrics.users_with_active_managers == 0
        assert metrics.resource_limit_hits == 0
        assert metrics.total_connections_managed == 0
        assert metrics.security_violations_detected == 0
        assert metrics.average_manager_lifetime_seconds == 0.0
        
    def test_factory_metrics_to_dict_serialization(self):
        """Test FactoryMetrics converts to dict for monitoring."""
        metrics = FactoryMetrics()
        metrics.managers_created = 5
        metrics.security_violations_detected = 1
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["managers_created"] == 5
        assert metrics_dict["security_violations_detected"] == 1
        assert "managers_active" in metrics_dict
        assert "resource_limit_hits" in metrics_dict


@pytest.mark.unit
class TestManagerMetrics(SSotBaseTestCase):
    """Test ManagerMetrics business logic - tracks individual manager performance."""
    
    def test_manager_metrics_initialization(self):
        """Test ManagerMetrics initializes correctly."""
        metrics = ManagerMetrics()
        
        assert metrics.connections_managed == 0
        assert metrics.messages_sent_total == 0
        assert metrics.messages_failed_total == 0
        assert metrics.last_activity is None
        assert metrics.manager_age_seconds == 0.0
        assert metrics.cleanup_scheduled is False
        
    def test_manager_metrics_to_dict_with_datetime_serialization(self):
        """Test ManagerMetrics serializes datetime fields properly."""
        metrics = ManagerMetrics()
        metrics.last_activity = datetime.utcnow()
        metrics.connections_managed = 3
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert metrics_dict["connections_managed"] == 3
        assert isinstance(metrics_dict["last_activity"], str)  # ISO format
        assert "T" in metrics_dict["last_activity"]  # ISO datetime format


@pytest.mark.unit
class TestFactoryInitializationError(SSotBaseTestCase):
    """Test FactoryInitializationError business logic."""
    
    def test_factory_error_with_user_context(self):
        """Test FactoryInitializationError includes user context."""
        user_id = "test-user-123"
        error_code = "SSOT_VALIDATION_FAILED"
        details = {"validation_error": "user_id_missing"}
        
        error = FactoryInitializationError(
            "SSOT validation failed",
            user_id=user_id,
            error_code=error_code,
            details=details
        )
        
        assert str(error) == "SSOT validation failed"
        assert error.user_id == user_id
        assert error.error_code == error_code
        assert error.details == details


@pytest.mark.unit
class TestDefensiveUserExecutionContext(SSotBaseTestCase):
    """Test create_defensive_user_execution_context business logic."""
    
    def test_defensive_context_creation_with_valid_user_id(self):
        """Test defensive context creation succeeds with valid user ID."""
        user_id = "valid-user-123"
        websocket_client_id = "ws-client-456"
        
        with patch('netra_backend.app.services.user_execution_context.UserExecutionContext.from_websocket_request') as mock_factory:
            mock_context = Mock(spec=UserExecutionContext)
            mock_factory.return_value = mock_context
            
            result = create_defensive_user_execution_context(user_id, websocket_client_id)
            
            assert result == mock_context
            mock_factory.assert_called_once_with(
                user_id=user_id,
                websocket_client_id=websocket_client_id,
                operation="websocket_factory"
            )
            
    def test_defensive_context_raises_on_invalid_user_id(self):
        """Test defensive context creation fails with invalid user ID."""
        invalid_user_ids = ["", None, "  ", 123, []]
        
        for invalid_id in invalid_user_ids:
            with pytest.raises(ValueError, match="user_id must be non-empty string"):
                create_defensive_user_execution_context(invalid_id)


@pytest.mark.unit 
class TestSSotUserContextValidation(SSotBaseTestCase):
    """Test SSOT user context validation business logic."""
    
    def test_ssot_validation_accepts_legacy_user_context(self):
        """Test SSOT validation accepts legacy UserExecutionContext."""
        # Create mock legacy UserExecutionContext
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "test-user-123"
        mock_context.thread_id = "thread-456"
        mock_context.run_id = "run-789"
        mock_context.request_id = "req-101"
        mock_context.websocket_client_id = "ws-client-202"
        
        # Should not raise exception
        try:
            _validate_ssot_user_context(mock_context)
        except Exception as e:
            pytest.fail(f"Validation should succeed for legacy context: {e}")
            
    def test_ssot_validation_accepts_strongly_typed_context(self):
        """Test SSOT validation accepts StronglyTypedUserExecutionContext."""
        # Create mock SSOT UserExecutionContext
        mock_context = Mock(spec=StronglyTypedUserExecutionContext)
        mock_context.user_id = "test-user-123"
        mock_context.thread_id = "thread-456"
        mock_context.run_id = "run-789"
        mock_context.request_id = "req-101"
        mock_context.websocket_client_id = None  # Can be None
        
        # Should not raise exception
        try:
            _validate_ssot_user_context(mock_context)
        except Exception as e:
            pytest.fail(f"Validation should succeed for SSOT context: {e}")
            
    def test_ssot_validation_rejects_invalid_context_type(self):
        """Test SSOT validation rejects invalid context types."""
        invalid_contexts = [None, "string", 123, {}, []]
        
        for invalid_context in invalid_contexts:
            with pytest.raises(ValueError, match="TYPE VALIDATION FAILED"):
                _validate_ssot_user_context(invalid_context)
                
    def test_ssot_validation_requires_all_attributes(self):
        """Test SSOT validation requires all essential attributes."""
        # Create incomplete context
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "test-user-123"
        # Missing other required attributes
        
        with pytest.raises(ValueError, match="SSOT CONTEXT INCOMPLETE"):
            _validate_ssot_user_context(mock_context)


@pytest.mark.unit
class TestConnectionLifecycleManager(SSotBaseTestCase):
    """Test ConnectionLifecycleManager business logic - manages connection lifecycle."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_context = Mock(spec=UserExecutionContext)
        self.user_context.user_id = "lifecycle-user-123"
        
        self.ws_manager = Mock(spec=IsolatedWebSocketManager)
        self.ws_manager.get_connection.return_value = None
        self.ws_manager.remove_connection = AsyncMock()
        
        self.lifecycle_manager = ConnectionLifecycleManager(
            self.user_context, 
            self.ws_manager
        )
        
    def test_lifecycle_manager_initialization(self):
        """Test ConnectionLifecycleManager initializes correctly."""
        assert self.lifecycle_manager.user_context == self.user_context
        assert self.lifecycle_manager.ws_manager == self.ws_manager
        assert len(self.lifecycle_manager._managed_connections) == 0
        assert len(self.lifecycle_manager._connection_health) == 0
        
    def test_register_connection_with_matching_user(self):
        """Test register_connection succeeds with matching user ID."""
        # Create mock connection
        connection = Mock(spec=WebSocketConnection)
        connection.user_id = "lifecycle-user-123"  # Matches context
        connection.connection_id = "conn-456"
        
        # Execute business logic
        self.lifecycle_manager.register_connection(connection)
        
        # Verify business outcomes
        assert "conn-456" in self.lifecycle_manager._managed_connections
        assert "conn-456" in self.lifecycle_manager._connection_health
        assert isinstance(self.lifecycle_manager._connection_health["conn-456"], datetime)
        
    def test_register_connection_rejects_mismatched_user(self):
        """Test register_connection rejects connection from different user."""
        # Create mock connection with different user ID
        connection = Mock(spec=WebSocketConnection)
        connection.user_id = "different-user-789"  # Different from context
        connection.connection_id = "conn-456"
        
        # Execute business logic and verify security violation
        with pytest.raises(ValueError, match="violates user isolation requirements"):
            self.lifecycle_manager.register_connection(connection)
            
    def test_health_check_updates_last_seen_time(self):
        """Test health_check_connection updates connection health tracking."""
        # Register connection first
        connection = Mock(spec=WebSocketConnection)
        connection.user_id = "lifecycle-user-123"
        connection.connection_id = "health-conn-123"
        connection.websocket = Mock()
        
        self.lifecycle_manager.register_connection(connection)
        self.ws_manager.get_connection.return_value = connection
        
        initial_health_time = self.lifecycle_manager._connection_health["health-conn-123"]
        
        # Wait a small amount to ensure time difference
        import time
        time.sleep(0.01)
        
        # Execute business logic
        result = self.lifecycle_manager.health_check_connection("health-conn-123")
        
        # Verify business outcomes
        assert result is True
        updated_health_time = self.lifecycle_manager._connection_health["health-conn-123"]
        assert updated_health_time > initial_health_time
        
    async def test_auto_cleanup_expired_removes_old_connections(self):
        """Test auto_cleanup_expired removes connections past timeout."""
        # Register connection
        connection = Mock(spec=WebSocketConnection)
        connection.user_id = "lifecycle-user-123"
        connection.connection_id = "expired-conn-123"
        
        self.lifecycle_manager.register_connection(connection)
        
        # Artificially age the connection
        cutoff_time = datetime.utcnow() - timedelta(minutes=31)  # Older than 30-minute timeout
        self.lifecycle_manager._connection_health["expired-conn-123"] = cutoff_time
        
        # Execute business logic
        cleaned_count = await self.lifecycle_manager.auto_cleanup_expired()
        
        # Verify business outcomes
        assert cleaned_count == 1
        assert "expired-conn-123" not in self.lifecycle_manager._managed_connections
        assert "expired-conn-123" not in self.lifecycle_manager._connection_health
        self.ws_manager.remove_connection.assert_called_once_with("expired-conn-123")


@pytest.mark.unit
class TestIsolatedWebSocketManager(SSotBaseTestCase):
    """Test IsolatedWebSocketManager business logic - CRITICAL for user isolation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_context = Mock(spec=UserExecutionContext)
        self.user_context.user_id = "isolated-user-123"
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.ConnectionLifecycleManager'):
            self.manager = IsolatedWebSocketManager(self.user_context)
            
    def test_manager_initialization_with_user_context(self):
        """Test IsolatedWebSocketManager initializes with proper user isolation."""
        assert self.manager.user_context == self.user_context
        assert len(self.manager._connections) == 0
        assert len(self.manager._connection_ids) == 0
        assert self.manager._is_active is True
        assert isinstance(self.manager.created_at, datetime)
        
    def test_manager_rejects_invalid_context_types(self):
        """Test manager rejects invalid UserExecutionContext types."""
        invalid_contexts = ["string", 123, None, {}]
        
        for invalid_context in invalid_contexts:
            with pytest.raises(ValueError, match="user_context must be a UserExecutionContext"):
                IsolatedWebSocketManager(invalid_context)
                
    async def test_add_connection_enforces_user_isolation(self):
        """Test add_connection enforces strict user isolation."""
        # Create connection with matching user ID
        matching_connection = Mock(spec=WebSocketConnection)
        matching_connection.user_id = "isolated-user-123"  # Matches manager
        matching_connection.connection_id = "conn-123"
        
        # Execute business logic
        await self.manager.add_connection(matching_connection)
        
        # Verify business outcomes
        assert "conn-123" in self.manager._connections
        assert "conn-123" in self.manager._connection_ids
        assert self.manager._metrics.connections_managed == 1
        
    async def test_add_connection_rejects_mismatched_user(self):
        """Test add_connection rejects connections from different users."""
        # Create connection with different user ID
        foreign_connection = Mock(spec=WebSocketConnection)
        foreign_connection.user_id = "different-user-789"
        foreign_connection.connection_id = "foreign-conn-456"
        
        # Execute business logic and verify security violation
        with pytest.raises(ValueError, match="violates user isolation requirements"):
            await self.manager.add_connection(foreign_connection)
            
        # Verify no connection was added
        assert len(self.manager._connections) == 0
        
    async def test_send_to_user_enforces_user_matching(self):
        """Test send_to_user enforces user ID matching."""
        # Try to send to different user
        with pytest.raises(ValueError, match="violates user isolation"):
            await self.manager.send_to_user("different-user-789", {"type": "test"})
            
    async def test_send_to_user_handles_no_connections_gracefully(self):
        """Test send_to_user handles no active connections gracefully."""
        # No connections added
        message = {"type": "test", "content": "hello"}
        
        # Execute business logic
        await self.manager.send_to_user("isolated-user-123", message)
        
        # Verify message queued for recovery
        assert len(self.manager._message_recovery_queue) == 1
        recovery_msg = self.manager._message_recovery_queue[0]
        assert recovery_msg["type"] == "test"
        assert recovery_msg["failure_reason"] == "no_connections"
        
    def test_is_connection_active_rejects_foreign_user(self):
        """Test is_connection_active rejects foreign user IDs."""
        result = self.manager.is_connection_active("foreign-user-456")
        
        assert result is False, "Should reject foreign user ID"
        
    def test_get_manager_stats_includes_user_context(self):
        """Test get_manager_stats includes comprehensive information."""
        stats = self.manager.get_manager_stats()
        
        assert "user_context" in stats
        assert "manager_id" in stats
        assert "is_active" in stats
        assert "metrics" in stats
        assert "connections" in stats
        assert "recovery_queue_size" in stats
        
    async def test_health_check_validates_manager_responsiveness(self):
        """Test health_check validates manager is responsive, not zombie."""
        # Manager should be healthy when newly created
        result = await self.manager.health_check()
        
        assert result is False, "Should be unhealthy with no connections"
        
        # Add a connection and test again
        connection = Mock(spec=WebSocketConnection)
        connection.user_id = "isolated-user-123"
        connection.connection_id = "health-conn-123"
        connection.websocket = Mock()
        connection.websocket.client_state = Mock()
        connection.websocket.client_state.name = "CONNECTED"
        
        await self.manager.add_connection(connection)
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.WebSocketState'):
            result = await self.manager.health_check()
            
        # Health should improve with connections
        assert isinstance(result, bool)


@pytest.mark.unit
class TestWebSocketManagerFactory(SSotBaseTestCase):
    """Test WebSocketManagerFactory business logic - CRITICAL for multi-user resource management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.factory = WebSocketManagerFactory(max_managers_per_user=5)
        
    def test_factory_initialization_with_configuration(self):
        """Test WebSocketManagerFactory initializes with proper configuration."""
        assert self.factory.max_managers_per_user == 5
        assert self.factory.connection_timeout_seconds == 1800  # 30 minutes
        assert len(self.factory._active_managers) == 0
        assert len(self.factory._user_manager_count) == 0
        assert isinstance(self.factory._factory_metrics, FactoryMetrics)
        
    def test_generate_isolation_key_uses_thread_id(self):
        """Test _generate_isolation_key creates consistent keys using thread_id."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "key-user-123"
        user_context.thread_id = "thread-456"
        
        key1 = self.factory._generate_isolation_key(user_context)
        key2 = self.factory._generate_isolation_key(user_context)
        
        # Keys should be consistent
        assert key1 == key2
        assert key1 == "key-user-123:thread-456"
        
    async def test_create_manager_enforces_resource_limits(self):
        """Test create_manager enforces per-user resource limits."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "limited-user-123"
        user_context.thread_id = "thread-1"
        
        # Create managers up to limit
        managers = []
        for i in range(5):  # Max limit
            user_context.thread_id = f"thread-{i}"
            with patch('netra_backend.app.websocket_core.websocket_manager_factory._validate_ssot_user_context_staging_safe'):
                manager = await self.factory.create_manager(user_context)
                managers.append(manager)
                
        # Verify all managers created
        assert len(managers) == 5
        assert self.factory._user_manager_count["limited-user-123"] == 5
        
        # Next creation should trigger resource limit
        user_context.thread_id = "thread-6"
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory._validate_ssot_user_context_staging_safe'):
            with patch.object(self.factory, '_emergency_cleanup_user_managers', return_value=0):
                with pytest.raises(RuntimeError, match="maximum number of WebSocket managers"):
                    await self.factory.create_manager(user_context)
                    
    def test_enforce_resource_limits_business_logic(self):
        """Test enforce_resource_limits validates user resource usage."""
        user_id = "resource-user-123"
        
        # User within limits
        assert self.factory.enforce_resource_limits(user_id) is True
        
        # Simulate user at limit
        self.factory._user_manager_count[user_id] = 5
        assert self.factory.enforce_resource_limits(user_id) is False
        
    async def test_cleanup_manager_removes_tracking(self):
        """Test cleanup_manager removes all tracking references."""
        # Create manager first
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "cleanup-user-123"
        user_context.thread_id = "cleanup-thread-456"
        
        isolation_key = "cleanup-user-123:cleanup-thread-456"
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory._validate_ssot_user_context_staging_safe'):
            manager = await self.factory.create_manager(user_context)
            
        # Verify manager created and tracked
        assert isolation_key in self.factory._active_managers
        assert self.factory._user_manager_count["cleanup-user-123"] == 1
        
        # Execute cleanup
        result = await self.factory.cleanup_manager(isolation_key)
        
        # Verify cleanup business outcomes
        assert result is True
        assert isolation_key not in self.factory._active_managers
        assert self.factory._user_manager_count.get("cleanup-user-123", 0) == 0
        assert self.factory._factory_metrics.managers_cleaned_up == 1
        
    def test_get_factory_stats_comprehensive_metrics(self):
        """Test get_factory_stats returns comprehensive factory metrics."""
        stats = self.factory.get_factory_stats()
        
        assert "factory_metrics" in stats
        assert "configuration" in stats
        assert "current_state" in stats
        assert "user_distribution" in stats
        assert "oldest_manager_age_seconds" in stats
        
        # Verify configuration details
        config = stats["configuration"]
        assert config["max_managers_per_user"] == 5
        assert config["connection_timeout_seconds"] == 1800
        
    async def test_emergency_cleanup_removes_unhealthy_managers(self):
        """Test _emergency_cleanup_user_managers removes unhealthy managers."""
        user_id = "emergency-user-123"
        
        # Create several managers for the user
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = user_id
        
        with patch('netra_backend.app.websocket_core.websocket_manager_factory._validate_ssot_user_context_staging_safe'):
            for i in range(3):
                user_context.thread_id = f"emergency-thread-{i}"
                await self.factory.create_manager(user_context)
                
        # Verify managers created
        assert self.factory._user_manager_count[user_id] == 3
        
        # Mock health check to make managers appear unhealthy
        with patch.object(IsolatedWebSocketManager, 'health_check', return_value=False):
            cleaned_count = await self.factory._emergency_cleanup_user_managers(user_id)
            
        # Verify emergency cleanup business outcomes
        assert cleaned_count > 0
        final_count = self.factory._user_manager_count.get(user_id, 0)
        assert final_count < 3, "Some managers should have been cleaned up"


@pytest.mark.unit
class TestGlobalFactoryFunctions(SSotBaseTestCase):
    """Test global factory functions - SSOT for manager creation."""
    
    def test_get_websocket_manager_factory_singleton(self):
        """Test get_websocket_manager_factory returns singleton."""
        factory1 = get_websocket_manager_factory()
        factory2 = get_websocket_manager_factory()
        
        assert factory1 is factory2, "Should return singleton instance"
        assert isinstance(factory1, WebSocketManagerFactory)
        
    @patch('netra_backend.app.websocket_core.websocket_manager_factory._validate_ssot_user_context_staging_safe')
    @patch('netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager_factory')
    async def test_create_websocket_manager_validates_context(self, mock_get_factory, mock_validate):
        """Test create_websocket_manager validates user context."""
        # Setup
        mock_factory = Mock()
        mock_manager = Mock(spec=IsolatedWebSocketManager)
        mock_factory.create_manager.return_value = mock_manager
        mock_get_factory.return_value = mock_factory
        
        user_context = Mock(spec=UserExecutionContext)
        
        # Execute business logic
        result = await create_websocket_manager(user_context)
        
        # Verify business outcomes
        mock_validate.assert_called_once_with(user_context)
        mock_factory.create_manager.assert_called_once_with(user_context)
        assert result == mock_manager
        
    @patch('netra_backend.app.websocket_core.websocket_manager_factory._validate_ssot_user_context_staging_safe')
    async def test_create_websocket_manager_handles_validation_errors(self, mock_validate):
        """Test create_websocket_manager handles SSOT validation failures."""
        # Setup validation failure
        mock_validate.side_effect = ValueError("SSOT validation failed")
        user_context = Mock(spec=UserExecutionContext)
        
        # Execute business logic and verify error handling
        with pytest.raises(FactoryInitializationError, match="SSOT validation failed"):
            await create_websocket_manager(user_context)
            
    def test_create_websocket_manager_sync_restricted_to_test_env(self):
        """Test create_websocket_manager_sync is restricted to test environments."""
        user_context = Mock(spec=UserExecutionContext)
        
        # Mock production environment
        with patch('shared.isolated_environment.get_env') as mock_get_env:
            mock_env = Mock()
            mock_env.get.return_value = "production"
            mock_get_env.return_value = mock_env
            
            # Should raise error in production
            with pytest.raises(RuntimeError, match="restricted to test environments"):
                create_websocket_manager_sync(user_context)


if __name__ == "__main__":
    pytest.main([__file__])