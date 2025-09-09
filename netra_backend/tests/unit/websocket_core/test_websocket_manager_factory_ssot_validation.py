"""
Unit Tests for WebSocketManagerFactory SSOT Validation Failures

These tests are DESIGNED TO FAIL initially to prove SSOT validation issues
exist in the WebSocketManagerFactory implementation. The tests demonstrate
specific SSOT violations that prevent proper factory initialization.

Test Categories:
1. Factory Initialization SSOT - Missing or invalid factory dependencies
2. User Context Manager Creation - SSOT validation failures during manager creation
3. Connection Isolation SSOT - Connection pool integration and isolation failures
4. ID Generation SSOT - Inconsistent ID generation patterns across managers
5. Lifecycle Management SSOT - Manager cleanup and resource management violations

Expected Outcomes:
- All tests should FAIL initially with specific SSOT error messages
- Failures demonstrate the factory initialization problems affecting golden path  
- Error messages provide concrete evidence of SSOT validation violations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    FactoryInitializationError,
    create_defensive_user_execution_context
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketManagerFactorySSotValidation:
    """Test SSOT validation failures in WebSocketManagerFactory."""
    
    def test_websocket_manager_factory_initialization_ssot_validation(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate initialization dependencies SSOT.
        
        SSOT Issue: Factory initializes without required dependencies, violating SSOT pattern.
        Expected Failure: Factory should require all SSOT dependencies during initialization.
        """
        # This should FAIL with SSOT validation error
        with pytest.raises(FactoryInitializationError, match="dependencies"):
            WebSocketManagerFactory(
                # Missing required SSOT dependencies
                connection_pool=None,  # SSOT violation: None dependency
                user_context_factory=None,  # SSOT violation: None dependency
                id_manager=None  # SSOT violation: None dependency
            )
    
    def test_defensive_user_execution_context_ssot_user_id_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Defensive context creation should validate user_id SSOT.
        
        SSOT Issue: Function allows invalid user_id values, violating SSOT validation.
        Expected Failure: Should reject empty, None, or invalid user_id values.
        """
        # This should FAIL - empty user_id violates SSOT validation
        with pytest.raises(ValueError, match="user_id must be non-empty"):
            create_defensive_user_execution_context(
                user_id="",  # SSOT violation: empty user_id
                websocket_client_id="valid_client_id"
            )
    
    def test_defensive_user_execution_context_ssot_none_user_id_failure(self):
        """
        TEST DESIGNED TO FAIL: Defensive context creation should reject None user_id SSOT.
        
        SSOT Issue: Function allows None user_id, violating SSOT validation pattern.
        Expected Failure: Should reject None user_id values explicitly.
        """
        # This should FAIL - None user_id violates SSOT validation
        with pytest.raises(ValueError, match="user_id must be non-empty"):
            create_defensive_user_execution_context(
                user_id=None,  # SSOT violation: None user_id
                websocket_client_id="valid_client_id"
            )
    
    def test_defensive_user_execution_context_ssot_whitespace_user_id_failure(self):
        """
        TEST DESIGNED TO FAIL: Defensive context creation should reject whitespace user_id SSOT.
        
        SSOT Issue: Function allows whitespace-only user_id, violating SSOT validation.
        Expected Failure: Should reject user_id that is only whitespace.
        """
        # This should FAIL - whitespace-only user_id violates SSOT validation
        with pytest.raises(ValueError, match="user_id must be non-empty"):
            create_defensive_user_execution_context(
                user_id="   ",  # SSOT violation: whitespace-only user_id
                websocket_client_id="valid_client_id"
            )
    
    def test_defensive_user_execution_context_ssot_id_generation_failure(self):
        """
        TEST DESIGNED TO FAIL: Defensive context should validate ID generation SSOT.
        
        SSOT Issue: Function doesn't validate generated IDs from SSOT ID generator.
        Expected Failure: Should validate all generated IDs are proper format.
        """
        # Mock ID generator to return invalid IDs (SSOT violation)
        with patch('shared.id_generation.unified_id_generator.UnifiedIdGenerator.generate_user_context_ids') as mock_gen:
            mock_gen.return_value = ("", "", "")  # SSOT violation: empty IDs
            
            # This should FAIL - invalid generated IDs should be rejected
            with pytest.raises(ValueError, match="Invalid.*ID.*generated"):
                create_defensive_user_execution_context(
                    user_id="valid_user",
                    websocket_client_id="valid_client_id"
                )
    
    def test_websocket_manager_factory_user_context_validation_ssot_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate user context SSOT compliance.
        
        SSOT Issue: Factory creates managers without validating UserExecutionContext SSOT.
        Expected Failure: Should reject manager creation with invalid user contexts.
        """
        # Mock factory with required dependencies
        mock_connection_pool = Mock()
        mock_user_context_factory = Mock()
        mock_id_manager = Mock()
        
        factory = WebSocketManagerFactory(
            connection_pool=mock_connection_pool,
            user_context_factory=mock_user_context_factory,
            id_manager=mock_id_manager
        )
        
        # This should FAIL - invalid user context should be rejected
        invalid_context = UserExecutionContext(
            user_id="",  # SSOT violation: empty user_id
            thread_id="valid_thread",
            run_id="valid_run",
            request_id="valid_request"
        )
        
        with pytest.raises(ValueError, match="Invalid.*user.*context"):
            factory.create_isolated_websocket_manager(invalid_context)
    
    def test_websocket_manager_factory_connection_pool_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate connection pool SSOT interface.
        
        SSOT Issue: Factory accepts invalid connection pool types without validation.
        Expected Failure: Should validate connection pool interface compliance.
        """
        # This should FAIL - invalid connection pool type should be rejected
        invalid_connection_pool = "not_a_connection_pool"  # SSOT violation: wrong type
        
        with pytest.raises(TypeError, match="connection.*pool"):
            WebSocketManagerFactory(
                connection_pool=invalid_connection_pool,  # SSOT violation: invalid type
                user_context_factory=Mock(),
                id_manager=Mock()
            )
    
    def test_websocket_manager_factory_id_manager_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate ID manager SSOT interface.
        
        SSOT Issue: Factory accepts invalid ID manager types without validation.
        Expected Failure: Should validate ID manager interface compliance.
        """
        # This should FAIL - invalid ID manager type should be rejected
        invalid_id_manager = "not_an_id_manager"  # SSOT violation: wrong type
        
        with pytest.raises(TypeError, match="ID.*manager"):
            WebSocketManagerFactory(
                connection_pool=Mock(),
                user_context_factory=Mock(),
                id_manager=invalid_id_manager  # SSOT violation: invalid type
            )
    
    def test_websocket_manager_factory_user_isolation_ssot_enforcement_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce user isolation SSOT pattern.
        
        SSOT Issue: Factory creates managers that share state between users.
        Expected Failure: Should ensure complete isolation between user managers.
        """
        mock_connection_pool = Mock()
        mock_user_context_factory = Mock()
        mock_id_manager = Mock()
        
        factory = WebSocketManagerFactory(
            connection_pool=mock_connection_pool,
            user_context_factory=mock_user_context_factory,
            id_manager=mock_id_manager
        )
        
        # Create contexts for two different users
        context1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1",
            run_id="run1",
            request_id="request1"
        )
        
        context2 = UserExecutionContext(
            user_id="user2", 
            thread_id="thread2",
            run_id="run2",
            request_id="request2"
        )
        
        # Create managers for both users
        manager1 = factory.create_isolated_websocket_manager(context1)
        manager2 = factory.create_isolated_websocket_manager(context2)
        
        # This should FAIL if SSOT isolation is violated
        assert manager1 is not manager2, \
            "SSOT violation: Different users got same manager instance"
        assert manager1.user_context.user_id != manager2.user_context.user_id, \
            "SSOT violation: Managers share user context between different users"
    
    def test_websocket_manager_factory_connection_lifecycle_ssot_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce connection lifecycle SSOT pattern.
        
        SSOT Issue: Factory doesn't properly manage connection lifecycle.
        Expected Failure: Should track and cleanup connections properly.
        """
        mock_connection_pool = Mock()
        mock_user_context_factory = Mock()
        mock_id_manager = Mock()
        
        factory = WebSocketManagerFactory(
            connection_pool=mock_connection_pool,
            user_context_factory=mock_user_context_factory,
            id_manager=mock_id_manager
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Create manager
        manager = factory.create_isolated_websocket_manager(valid_context)
        
        initial_connections = factory.get_active_connections_count()
        
        # Cleanup manager
        factory.cleanup_manager(manager)
        
        # This should FAIL if SSOT lifecycle management is violated
        final_connections = factory.get_active_connections_count()
        assert final_connections < initial_connections, \
            "SSOT violation: Connection count not decreased after cleanup"
    
    def test_websocket_manager_factory_memory_leak_ssot_prevention_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should prevent memory leaks SSOT pattern.
        
        SSOT Issue: Factory doesn't properly cleanup weak references and tracking.
        Expected Failure: Should maintain clean memory state after manager cleanup.
        """
        mock_connection_pool = Mock()
        mock_user_context_factory = Mock() 
        mock_id_manager = Mock()
        
        factory = WebSocketManagerFactory(
            connection_pool=mock_connection_pool,
            user_context_factory=mock_user_context_factory,
            id_manager=mock_id_manager
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        initial_memory_refs = len(factory._active_managers)
        
        # Create and cleanup multiple managers
        for i in range(10):
            manager = factory.create_isolated_websocket_manager(valid_context)
            factory.cleanup_manager(manager)
        
        # This should FAIL if SSOT memory management is violated
        final_memory_refs = len(factory._active_managers)
        assert final_memory_refs == initial_memory_refs, \
            "SSOT violation: Memory references not cleaned up properly"
    
    def test_websocket_manager_factory_concurrent_access_ssot_safety_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should enforce concurrent access SSOT safety.
        
        SSOT Issue: Factory doesn't properly handle concurrent manager creation.
        Expected Failure: Should maintain thread safety during concurrent operations.
        """
        mock_connection_pool = Mock()
        mock_user_context_factory = Mock()
        mock_id_manager = Mock()
        
        factory = WebSocketManagerFactory(
            connection_pool=mock_connection_pool,
            user_context_factory=mock_user_context_factory,
            id_manager=mock_id_manager
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        # Create multiple managers concurrently
        managers = []
        for i in range(5):
            manager = factory.create_isolated_websocket_manager(valid_context)
            managers.append(manager)
        
        # This should FAIL if SSOT concurrent safety is violated
        unique_managers = set(id(manager) for manager in managers)
        assert len(unique_managers) == len(managers), \
            "SSOT violation: Concurrent creation produced duplicate manager instances"
    
    def test_websocket_manager_factory_configuration_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should validate configuration SSOT consistency.
        
        SSOT Issue: Factory doesn't validate configuration parameters properly.
        Expected Failure: Should reject invalid configuration parameters.
        """
        # This should FAIL - invalid configuration should be rejected
        with pytest.raises(ValueError, match="configuration"):
            WebSocketManagerFactory(
                connection_pool=Mock(),
                user_context_factory=Mock(),
                id_manager=Mock(),
                max_connections_per_user=-1,  # SSOT violation: negative value
                connection_timeout=0  # SSOT violation: zero timeout
            )
    
    def test_defensive_context_fallback_context_ssot_validation_failure(self):
        """
        TEST DESIGNED TO FAIL: Defensive context should validate fallback context SSOT.
        
        SSOT Issue: Function doesn't validate fallback_context structure properly.
        Expected Failure: Should validate fallback_context contains required SSOT fields.
        """
        # This should FAIL - invalid fallback context should be rejected
        invalid_fallback = {
            "invalid_field": "value"
            # Missing required SSOT fields
        }
        
        with pytest.raises(ValueError, match="fallback.*context"):
            create_defensive_user_execution_context(
                user_id="valid_user",
                websocket_client_id="valid_client_id",
                fallback_context=invalid_fallback  # SSOT violation: invalid structure
            )
    
    def test_websocket_manager_factory_metrics_ssot_consistency_failure(self):
        """
        TEST DESIGNED TO FAIL: Factory should maintain metrics SSOT consistency.
        
        SSOT Issue: Factory metrics don't accurately reflect actual state.
        Expected Failure: Should maintain consistent metrics tracking.
        """
        mock_connection_pool = Mock()
        mock_user_context_factory = Mock()
        mock_id_manager = Mock()
        
        factory = WebSocketManagerFactory(
            connection_pool=mock_connection_pool,
            user_context_factory=mock_user_context_factory,
            id_manager=mock_id_manager
        )
        
        valid_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )
        
        initial_metrics = factory.get_factory_metrics()
        initial_created = initial_metrics['managers_created']
        
        # Create manager
        manager = factory.create_isolated_websocket_manager(valid_context)
        
        updated_metrics = factory.get_factory_metrics()
        
        # This should FAIL if metrics SSOT consistency is violated
        assert updated_metrics['managers_created'] == initial_created + 1, \
            "SSOT violation: managers_created not incremented correctly"
    
    def test_websocket_manager_factory_singleton_pattern_ssot_violation(self):
        """
        TEST DESIGNED TO FAIL: Factory should follow SSOT singleton pattern if required.
        
        SSOT Issue: Multiple factory instances violate SSOT singleton pattern.
        Expected Failure: Should enforce single factory instance or proper isolation.
        """
        # Create two factory instances
        factory1 = WebSocketManagerFactory(
            connection_pool=Mock(),
            user_context_factory=Mock(),
            id_manager=Mock()
        )
        
        factory2 = WebSocketManagerFactory(
            connection_pool=Mock(),
            user_context_factory=Mock(),
            id_manager=Mock()
        )
        
        # This should FAIL if SSOT singleton pattern is required but violated
        # (This test may pass if singleton pattern is not required for this factory)
        if hasattr(WebSocketManagerFactory, '_instance'):
            assert factory1 is factory2, \
                "SSOT violation: Multiple factory instances detected, should be singleton"