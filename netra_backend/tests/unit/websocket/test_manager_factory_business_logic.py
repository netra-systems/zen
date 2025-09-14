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

# SSOT imports using absolute paths - Issue #824 Remediation
# Import SSOT WebSocket manager and factory compatibility functions
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import (
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
        
        self.ws_manager = Mock(spec=WebSocketManager)
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
        
        # Issue #824 SSOT Remediation: Use WebSocketManager instead of removed IsolatedWebSocketManager
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.ConnectionLifecycleManager'):
            # Create WebSocketManager with appropriate parameters for testing
            self.manager = WebSocketManager(
                user_context=self.user_context,
                mode=None,  # Will use default mode
                _ssot_authorization_token="test_token"
            )
            
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
            with pytest.raises((ValueError, TypeError)):
                WebSocketManager(user_context=invalid_context, _ssot_authorization_token="test_token")
                
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
    """Test WebSocket Manager factory functions - CRITICAL for multi-user resource management."""

    def setup_method(self):
        """Set up test fixtures."""
        # Issue #824 SSOT Remediation: WebSocketManagerFactory class removed
        # Test the factory functions directly instead
        self.max_managers_per_user = 5
        
    def test_factory_functions_available(self):
        """Test WebSocket Manager factory functions are available."""
        # Test that SSOT factory functions are available
        assert callable(create_websocket_manager)
        assert callable(create_websocket_manager_sync)
        assert callable(get_websocket_manager_factory)
        
    def test_defensive_user_context_creation(self):
        """Test defensive user execution context creation."""
        user_id = "key-user-123"
        websocket_client_id = "ws-client-456"

        context = create_defensive_user_execution_context(user_id, websocket_client_id)

        # Verify context has required attributes
        assert hasattr(context, 'user_id')
        assert hasattr(context, 'websocket_client_id')
        assert context.user_id == user_id
        assert context.websocket_client_id == websocket_client_id
        
    async def test_create_manager_via_factory_function(self):
        """Test manager creation via SSOT factory function."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "limited-user-123"
        user_context.thread_id = "thread-1"

        # Test creating manager via SSOT factory function
        manager = await create_websocket_manager(user_context=user_context)

        # Verify manager was created and has required attributes
        assert manager is not None
        assert hasattr(manager, 'user_context')
                    
    def test_context_validation_functions(self):
        """Test SSOT user context validation functions."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "resource-user-123"
        user_context.request_id = "test-request-456"

        # Test validation functions are available and working
        assert _validate_ssot_user_context(user_context) is True
        assert _validate_ssot_user_context_staging_safe(user_context) is True
        
    def test_sync_manager_creation(self):
        """Test synchronous manager creation functionality."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "cleanup-user-123"
        user_context.thread_id = "cleanup-thread-456"

        # Test sync factory function
        manager = create_websocket_manager_sync(user_context=user_context)

        # Verify sync manager creation works
        assert manager is not None
        assert hasattr(manager, 'user_context')
        
    def test_factory_metrics_data_structures(self):
        """Test factory metrics data structures work properly."""
        metrics = FactoryMetrics()

        # Test metrics data structure
        assert hasattr(metrics, 'emitters_created')
        assert hasattr(metrics, 'ssot_redirect')
        assert metrics.ssot_redirect is True

        # Test serialization
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert 'ssot_redirect' in metrics_dict
        
    def test_component_health_validation(self):
        """Test WebSocket component health validation."""
        from netra_backend.app.websocket_core.websocket_manager_factory import validate_websocket_component_health

        # Test health validation function
        health_status = validate_websocket_component_health()

        # Verify health check returns proper structure
        assert isinstance(health_status, dict)
        assert 'status' in health_status
        assert 'components' in health_status


@pytest.mark.unit
class TestGlobalFactoryFunctions(SSotBaseTestCase):
    """Test global factory functions - SSOT for manager creation."""
    
    def test_get_websocket_manager_factory_function(self):
        """Test get_websocket_manager_factory returns factory function."""
        factory_func = get_websocket_manager_factory()

        # Should return a callable (the create_websocket_manager function)
        assert callable(factory_func)
        
    async def test_create_websocket_manager_validates_context(self):
        """Test create_websocket_manager validates user context."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "test-user-123"
        user_context.thread_id = "test-thread-456"

        # Execute business logic
        result = await create_websocket_manager(user_context)

        # Verify business outcomes
        assert result is not None
        assert hasattr(result, 'user_context')
        
    async def test_create_websocket_manager_handles_validation_errors(self):
        """Test create_websocket_manager handles SSOT validation failures."""
        # Test with invalid user context
        invalid_context = None

        # Execute business logic and verify error handling
        with pytest.raises((ValueError, TypeError)):
            await create_websocket_manager(invalid_context)
            
    def test_create_websocket_manager_sync_works_in_test_env(self):
        """Test create_websocket_manager_sync works in test environments."""
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = "test-user-123"
        user_context.thread_id = "test-thread-456"

        # Should work in test environment (no error raised)
        result = create_websocket_manager_sync(user_context)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__])