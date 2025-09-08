"""
Test WebSocket Factory SSOT Validation and Exception Handling

This test module validates the critical fixes implemented to prevent
1011 WebSocket errors caused by SSOT UserExecutionContext validation failures
in the WebSocket factory pattern.

CRITICAL FIXES TESTED:
1. SSOT UserExecutionContext type validation  
2. Comprehensive exception handling in factory creation
3. Emergency WebSocket manager fallback patterns
4. Graceful degradation when factory initialization fails
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from typing import Any, Dict

from netra_backend.app.websocket_core.websocket_manager_factory import (
    create_websocket_manager,
    FactoryInitializationError,
    _validate_ssot_user_context,
    get_websocket_manager_factory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.logging_config import central_logger


logger = central_logger.get_logger(__name__)


class TestSSOTUserContextValidation:
    """Test SSOT UserExecutionContext validation that prevents 1011 errors."""
    
    def test_valid_ssot_user_context_passes_validation(self):
        """Test that valid SSOT UserExecutionContext passes validation."""
        # Create valid SSOT UserExecutionContext
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id="ws_connection_abc"
        )
        
        # Should not raise any exception
        _validate_ssot_user_context(user_context)
    
    def test_wrong_type_raises_ssot_violation(self):
        """Test that non-SSOT UserExecutionContext types raise SSOT violation."""
        # Create mock object that's not the SSOT UserExecutionContext
        class FakeUserExecutionContext:
            def __init__(self):
                self.user_id = "test_user"
                self.thread_id = "test_thread"
                self.run_id = "test_run"
                self.websocket_client_id = "test_ws"
        
        fake_context = FakeUserExecutionContext()
        
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(fake_context)
        
        error_message = str(exc_info.value)
        assert "SSOT VIOLATION" in error_message
        assert "Expected netra_backend.app.services.user_execution_context.UserExecutionContext" in error_message
        assert "incomplete SSOT migration" in error_message.lower()
    
    def test_missing_required_attributes_raises_error(self):
        """Test that missing required attributes raise validation error."""
        # Create UserExecutionContext without required fields
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456", 
            run_id="run_789"
            # Missing websocket_client_id is OK, but other fields must be present
        )
        
        # Manually remove a required attribute to test validation
        delattr(user_context, 'thread_id')
        
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(user_context)
        
        error_message = str(exc_info.value)
        assert "SSOT CONTEXT INCOMPLETE" in error_message
        assert "thread_id" in error_message
    
    def test_empty_string_attributes_raise_error(self):
        """Test that empty string attributes raise validation error."""
        user_context = UserExecutionContext(
            user_id="",  # Empty string should fail
            thread_id="thread_456",
            run_id="run_789"
        )
        
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(user_context)
        
        error_message = str(exc_info.value)
        assert "SSOT CONTEXT VALIDATION FAILED" in error_message
        assert "user_id must be non-empty string" in error_message
    
    def test_none_values_for_required_fields_raise_error(self):
        """Test that None values for required fields raise validation error."""
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789"
        )
        
        # Manually set a required field to None
        object.__setattr__(user_context, 'user_id', None)
        
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(user_context)
        
        error_message = str(exc_info.value)
        assert "SSOT CONTEXT INCOMPLETE" in error_message
        assert "user_id (is None)" in error_message
    
    def test_websocket_client_id_can_be_none(self):
        """Test that websocket_client_id can be None without raising error."""
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id=None  # This should be allowed
        )
        
        # Should not raise any exception
        _validate_ssot_user_context(user_context)
    
    def test_websocket_client_id_empty_string_raises_error(self):
        """Test that empty string websocket_client_id raises error."""
        user_context = UserExecutionContext(
            user_id="test_user_123", 
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id=""  # Empty string should fail
        )
        
        with pytest.raises(ValueError) as exc_info:
            _validate_ssot_user_context(user_context)
        
        error_message = str(exc_info.value)
        assert "SSOT CONTEXT VALIDATION FAILED" in error_message
        assert "websocket_client_id must be None or non-empty string" in error_message


class TestWebSocketFactoryExceptionHandling:
    """Test WebSocket factory exception handling to prevent 1011 errors."""
    
    def test_valid_context_creates_manager_successfully(self):
        """Test that valid context creates WebSocket manager successfully."""
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456", 
            run_id="run_789",
            websocket_client_id="ws_connection_abc"
        )
        
        # Should create manager without errors
        manager = create_websocket_manager(user_context)
        assert manager is not None
        assert manager.user_context.user_id == "test_user_123"
    
    def test_invalid_context_raises_factory_initialization_error(self):
        """Test that invalid context raises FactoryInitializationError."""
        # Create invalid context (empty user_id)
        user_context = UserExecutionContext(
            user_id="",  # This will fail SSOT validation
            thread_id="thread_456",
            run_id="run_789"
        )
        
        with pytest.raises(FactoryInitializationError) as exc_info:
            create_websocket_manager(user_context)
        
        error_message = str(exc_info.value)
        assert "WebSocket factory SSOT validation failed" in error_message
        assert "UserExecutionContext type incompatibility" in error_message
    
    @patch('netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager_factory')
    def test_unexpected_factory_error_raises_factory_initialization_error(self, mock_get_factory):
        """Test that unexpected factory errors raise FactoryInitializationError."""
        # Mock factory to raise unexpected error
        mock_factory = Mock()
        mock_factory.create_manager.side_effect = RuntimeError("Simulated factory error")
        mock_get_factory.return_value = mock_factory
        
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456", 
            run_id="run_789"
        )
        
        with pytest.raises(FactoryInitializationError) as exc_info:
            create_websocket_manager(user_context)
        
        error_message = str(exc_info.value)
        assert "WebSocket factory initialization failed unexpectedly" in error_message
        assert "system configuration issue" in error_message
    
    def test_non_factory_value_error_is_reraised(self):
        """Test that non-factory ValueError is re-raised as-is."""
        # Create context that will pass SSOT validation but fail elsewhere
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789"
        )
        
        # Mock to raise a ValueError that's not related to SSOT
        with patch('netra_backend.app.websocket_core.websocket_manager_factory.get_websocket_manager_factory') as mock_get_factory:
            mock_factory = Mock()
            mock_factory.create_manager.side_effect = ValueError("Different validation error")
            mock_get_factory.return_value = mock_factory
            
            # This should re-raise the ValueError, not wrap it in FactoryInitializationError
            with pytest.raises(ValueError) as exc_info:
                create_websocket_manager(user_context)
            
            assert "Different validation error" in str(exc_info.value)
            assert "FactoryInitializationError" not in str(type(exc_info.value))


class TestWebSocketFactoryManagerCreation:
    """Test WebSocket factory manager creation and isolation patterns."""
    
    def test_factory_creates_isolated_managers(self):
        """Test that factory creates isolated managers for different contexts."""
        user_context_1 = UserExecutionContext(
            user_id="user_1",
            thread_id="thread_1",
            run_id="run_1",
            websocket_client_id="ws_1"
        )
        
        user_context_2 = UserExecutionContext(
            user_id="user_2",
            thread_id="thread_2", 
            run_id="run_2",
            websocket_client_id="ws_2"
        )
        
        manager_1 = create_websocket_manager(user_context_1)
        manager_2 = create_websocket_manager(user_context_2)
        
        # Managers should be different instances
        assert manager_1 is not manager_2
        assert id(manager_1) != id(manager_2)
        
        # Managers should have correct user contexts
        assert manager_1.user_context.user_id == "user_1"
        assert manager_2.user_context.user_id == "user_2"
    
    def test_same_context_returns_same_manager_instance(self):
        """Test that same context returns same manager instance (if isolation key matches)."""
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id="ws_connection_abc"
        )
        
        manager_1 = create_websocket_manager(user_context)
        manager_2 = create_websocket_manager(user_context)
        
        # Should return same instance due to isolation key matching
        assert manager_1 is manager_2
    
    def test_factory_handles_resource_limits(self):
        """Test that factory properly handles resource limits."""
        factory = get_websocket_manager_factory()
        
        # Check that factory has resource limits configured
        assert hasattr(factory, 'max_managers_per_user')
        assert factory.max_managers_per_user > 0
        
        # Test resource limit checking
        user_id = "test_user_resource_limits"
        within_limits = factory.enforce_resource_limits(user_id)
        assert within_limits is True  # Should be within limits initially


class TestWebSocketFactoryErrorRecovery:
    """Test WebSocket factory error recovery and graceful degradation."""
    
    @pytest.mark.asyncio
    async def test_isolated_manager_basic_operations(self):
        """Test that isolated manager supports basic operations."""
        user_context = UserExecutionContext(
            user_id="test_user_123",
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id="ws_connection_abc"
        )
        
        manager = create_websocket_manager(user_context)
        
        # Test basic manager operations
        assert manager.user_context.user_id == "test_user_123"
        assert hasattr(manager, 'add_connection')
        assert hasattr(manager, 'remove_connection')
        assert hasattr(manager, 'send_to_user')
        assert hasattr(manager, 'emit_critical_event')
    
    @pytest.mark.asyncio
    async def test_manager_connection_isolation(self):
        """Test that manager properly isolates connections per user."""
        user_context = UserExecutionContext(
            user_id="test_user_isolation",
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id="ws_connection_isolation"
        )
        
        manager = create_websocket_manager(user_context)
        
        # Mock WebSocket connection
        mock_websocket = Mock()
        
        # Create mock connection object
        mock_connection = type('Connection', (), {
            'connection_id': 'test_conn_123',
            'user_id': 'test_user_isolation',
            'websocket': mock_websocket,
            'connected_at': datetime.utcnow()
        })()
        
        # Test adding connection
        await manager.add_connection(mock_connection)
        
        # Verify connection is stored
        retrieved_conn = manager.get_connection('test_conn_123')
        assert retrieved_conn is mock_connection
        
        # Test user connection tracking
        user_connections = manager.get_user_connections()
        assert 'test_conn_123' in user_connections
        
        # Test connection activity check
        is_active = manager.is_connection_active('test_user_isolation')
        assert is_active is True
    
    @pytest.mark.asyncio  
    async def test_manager_security_validation(self):
        """Test that manager enforces security validation."""
        user_context = UserExecutionContext(
            user_id="secure_user_123", 
            thread_id="thread_456",
            run_id="run_789",
            websocket_client_id="ws_secure_connection"
        )
        
        manager = create_websocket_manager(user_context)
        
        # Mock connection for different user (should be rejected)
        mock_websocket = Mock()
        mock_connection = type('Connection', (), {
            'connection_id': 'malicious_conn_456', 
            'user_id': 'different_user_789',  # Different user ID
            'websocket': mock_websocket,
            'connected_at': datetime.utcnow()
        })()
        
        # Adding connection for different user should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            await manager.add_connection(mock_connection)
        
        error_message = str(exc_info.value)
        assert "does not match manager user_id" in error_message
        assert "violates user isolation requirements" in error_message


class TestWebSocketFactoryIntegration:
    """Integration tests for WebSocket factory with real SSOT components."""
    
    def test_factory_stats_and_monitoring(self):
        """Test that factory provides proper stats and monitoring."""
        factory = get_websocket_manager_factory()
        
        # Get factory stats
        stats = factory.get_factory_stats()
        
        # Verify stats structure
        assert 'factory_metrics' in stats
        assert 'configuration' in stats
        assert 'current_state' in stats
        
        # Verify metrics contain expected fields
        factory_metrics = stats['factory_metrics']
        assert 'managers_created' in factory_metrics
        assert 'managers_active' in factory_metrics
        assert 'managers_cleaned_up' in factory_metrics
    
    @pytest.mark.asyncio
    async def test_factory_cleanup_operations(self):
        """Test that factory properly handles cleanup operations."""
        user_context = UserExecutionContext(
            user_id="cleanup_test_user",
            thread_id="cleanup_thread",
            run_id="cleanup_run",
            websocket_client_id="cleanup_ws_conn"
        )
        
        # Create manager
        manager = create_websocket_manager(user_context)
        assert manager is not None
        
        # Test manager cleanup
        await manager.cleanup_all_connections()
        
        # Verify manager is cleaned up (should be inactive)
        assert not manager._is_active
    
    def test_factory_ssot_compliance(self):
        """Test that factory maintains SSOT compliance across operations."""
        # Create multiple contexts to test SSOT compliance
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"ssot_user_{i}",
                thread_id=f"ssot_thread_{i}",
                run_id=f"ssot_run_{i}",
                websocket_client_id=f"ssot_ws_{i}"
            )
            contexts.append(context)
        
        # Create managers for all contexts  
        managers = []
        for context in contexts:
            manager = create_websocket_manager(context)
            managers.append(manager)
            
            # Verify SSOT UserExecutionContext is preserved
            assert isinstance(manager.user_context, UserExecutionContext)
            assert manager.user_context.user_id == context.user_id
        
        # Verify managers are isolated from each other
        for i, manager in enumerate(managers):
            assert manager.user_context.user_id == f"ssot_user_{i}"
            
            # Verify no shared state between managers
            for j, other_manager in enumerate(managers):
                if i != j:
                    assert manager is not other_manager
                    assert id(manager._connections) != id(other_manager._connections)


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--durations=10",
        "--log-cli-level=INFO"
    ])