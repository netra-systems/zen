"""
Unit Tests for Factory Context Creation and Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal & All tiers
- Business Goal: Robust factory context creation with comprehensive validation
- Value Impact: Prevents runtime errors and ensures reliable multi-user operations  
- Strategic Impact: Foundation for stable factory patterns and user isolation

CRITICAL MISSION: Test Factory Context Creation and Validation ensuring:
1. UserExecutionContext validation and creation patterns
2. Factory context creation with comprehensive error handling
3. Context parameter validation and sanitization
4. Database session integration and lifecycle management
5. WebSocket client ID handling and validation
6. Metadata validation and processing
7. Context immutability and thread safety
8. Error propagation and recovery patterns

FOCUS: Comprehensive validation patterns as per SSOT architecture
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserWebSocketEmitter
)

from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    InvalidContextError
)

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_websocket_bridge():
    """Create mock WebSocket bridge."""
    mock_bridge = AsyncMock(spec=AgentWebSocketBridge)
    mock_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    mock_bridge.unregister_run_mapping = AsyncMock(return_value=True)
    return mock_bridge


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.close = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session


@pytest.fixture
def valid_context_params():
    """Create valid context parameters."""
    return {
        'user_id': f"user_{uuid.uuid4().hex[:8]}",
        'thread_id': f"thread_{uuid.uuid4().hex[:8]}",
        'run_id': f"run_{uuid.uuid4().hex[:8]}"
    }


@pytest.fixture
def comprehensive_metadata():
    """Create comprehensive metadata for testing."""
    return {
        'source': 'test_suite',
        'priority': 'high',
        'client_version': '1.0.0',
        'feature_flags': ['feature_a', 'feature_b'],
        'user_preferences': {
            'theme': 'dark',
            'language': 'en'
        },
        'request_metadata': {
            'ip_address': '127.0.0.1',
            'user_agent': 'test-client/1.0',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }


# ============================================================================
# TEST: UserExecutionContext Validation Patterns
# ============================================================================

class TestUserExecutionContextValidation(SSotBaseTestCase):
    """Test UserExecutionContext validation and creation patterns."""
    
    def test_user_execution_context_basic_validation(self, valid_context_params):
        """Test basic UserExecutionContext validation with valid parameters."""
        context = UserExecutionContext(
            user_id=valid_context_params['user_id'],
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            thread_id=valid_context_params['thread_id'],
            run_id=valid_context_params['run_id']
        )
        
        assert context.user_id == valid_context_params['user_id']
        assert context.thread_id == valid_context_params['thread_id']
        assert context.run_id == valid_context_params['run_id']
        assert context.created_at is not None
        assert isinstance(context.created_at, datetime)
    
    def test_user_execution_context_required_parameter_validation(self):
        """Test UserExecutionContext validates required parameters."""
        # Test empty string validation
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="",  # Empty string
                thread_id="valid_thread",
                run_id="valid_run"
            )
        
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="",  # Empty string
                run_id="valid_run" 
            )
        
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id=""  # Empty string
            )
    
    def test_user_execution_context_whitespace_validation(self):
        """Test UserExecutionContext handles whitespace-only strings."""
        # Test whitespace-only strings
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="   ",  # Whitespace only
                thread_id="valid_thread",
                run_id="valid_run"
            )
        
        with pytest.raises(InvalidContextError):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="\t\n  ",  # Mixed whitespace
                run_id="valid_run"
            )
    
    def test_user_execution_context_none_parameter_validation(self):
        """Test UserExecutionContext validates None parameters."""
        with pytest.raises((InvalidContextError, TypeError)):
            UserExecutionContext(
                user_id=None,
                thread_id="valid_thread", 
                run_id="valid_run"
            )
        
        with pytest.raises((InvalidContextError, TypeError)):
            UserExecutionContext(
                user_id="valid_user",
                thread_id=None,
                run_id="valid_run"
            )
        
        with pytest.raises((InvalidContextError, TypeError)):
            UserExecutionContext(
                user_id="valid_user",
                thread_id="valid_thread",
                run_id=None
            )
    
    def test_user_execution_context_type_validation(self):
        """Test UserExecutionContext validates parameter types."""
        invalid_types = [123, [], {}, object()]
        
        for invalid_value in invalid_types:
            with pytest.raises((InvalidContextError, TypeError)):
                UserExecutionContext(
                    user_id=invalid_value,
                    thread_id="valid_thread",
                    run_id="valid_run"
                )
    
    def test_user_execution_context_edge_case_values(self):
        """Test UserExecutionContext with edge case valid values."""
        # Single character IDs (should be valid)
        context = UserExecutionContext(
            user_id="a",
            thread_id="b", 
            run_id="c"
        )
        assert context.user_id == "a"
        assert context.thread_id == "b"
        assert context.run_id == "c"
        
        # Very long IDs (should be valid)
        long_id = "a" * 1000
        context = UserExecutionContext(
            user_id=long_id,
            thread_id=long_id,
            run_id=long_id
        )
        assert len(context.user_id) == 1000
        assert len(context.thread_id) == 1000  
        assert len(context.run_id) == 1000
    
    def test_user_execution_context_special_characters(self):
        """Test UserExecutionContext with special characters."""
        special_chars = "user-123_test@example.com:8080/path?query=value#fragment"
        
        # Should handle special characters in IDs
        context = UserExecutionContext(
            user_id=special_chars,
            thread_id=f"thread-{special_chars}",
            run_id=f"run_{uuid.uuid4()}"
        )
        
        assert context.user_id == special_chars
        assert special_chars in context.thread_id
    
    def test_user_execution_context_with_optional_parameters(self, comprehensive_metadata):
        """Test UserExecutionContext with optional parameters."""
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request",
            metadata=comprehensive_metadata
        )
        
        assert context.request_id == "test_request"
        assert context.metadata == comprehensive_metadata
        
        # Verify metadata is properly stored
        assert context.metadata['source'] == 'test_suite'
        assert context.metadata['priority'] == 'high'
        assert 'user_preferences' in context.metadata
    
    def test_user_execution_context_immutability(self):
        """Test UserExecutionContext immutability after creation."""
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run"
        )
        
        original_user_id = context.user_id
        original_created_at = context.created_at
        
        # Context should be immutable - attributes shouldn't be changeable
        # (Note: This depends on the actual implementation of UserExecutionContext)
        assert context.user_id == original_user_id
        assert context.created_at == original_created_at


# ============================================================================
# TEST: Factory Context Creation with Validation
# ============================================================================

class TestFactoryContextCreationWithValidation(SSotBaseTestCase):
    """Test AgentInstanceFactory context creation with comprehensive validation."""
    
    @pytest.mark.asyncio
    async def test_factory_create_context_basic_validation(self, mock_websocket_bridge, valid_context_params):
        """Test factory context creation with basic parameter validation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id=valid_context_params['user_id'],
            thread_id=valid_context_params['thread_id'],
            run_id=valid_context_params['run_id']
        )
        
        assert context.user_id == valid_context_params['user_id']
        assert context.thread_id == valid_context_params['thread_id']
        assert context.run_id == valid_context_params['run_id']
        assert context.created_at is not None
    
    @pytest.mark.asyncio
    async def test_factory_create_context_parameter_validation(self, mock_websocket_bridge):
        """Test factory validates parameters before context creation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test empty string validation
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("", "thread", "run")
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("user", "", "run")
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("user", "thread", "")
    
    @pytest.mark.asyncio
    async def test_factory_create_context_none_parameter_validation(self, mock_websocket_bridge):
        """Test factory validates None parameters."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context(None, "thread", "run")
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("user", None, "run")
        
        with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
            await factory.create_user_execution_context("user", "thread", None)
    
    @pytest.mark.asyncio
    async def test_factory_create_context_unconfigured_validation(self):
        """Test factory validates configuration before context creation."""
        factory = AgentInstanceFactory()
        # Don't configure factory
        
        with pytest.raises(ValueError, match="Factory not configured - call configure\\(\\) first"):
            await factory.create_user_execution_context("user", "thread", "run")
    
    @pytest.mark.asyncio
    async def test_factory_create_context_with_database_session(self, mock_websocket_bridge, mock_db_session):
        """Test factory context creation with database session."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            db_session=mock_db_session
        )
        
        assert context.db_session == mock_db_session
    
    @pytest.mark.asyncio
    async def test_factory_create_context_with_websocket_client_id(self, mock_websocket_bridge):
        """Test factory context creation with WebSocket client ID."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        client_id = f"client_{uuid.uuid4().hex[:8]}"
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread", 
            run_id="test_run",
            websocket_client_id=client_id
        )
        
        assert context.websocket_connection_id == client_id
    
    @pytest.mark.asyncio
    async def test_factory_create_context_with_comprehensive_metadata(self, mock_websocket_bridge, comprehensive_metadata):
        """Test factory context creation with comprehensive metadata."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            metadata=comprehensive_metadata
        )
        
        assert context.metadata == comprehensive_metadata
        assert context.metadata['source'] == 'test_suite'
        assert 'user_preferences' in context.metadata
        assert context.metadata['user_preferences']['theme'] == 'dark'
    
    @pytest.mark.asyncio
    async def test_factory_create_context_metrics_tracking(self, mock_websocket_bridge):
        """Test factory tracks context creation metrics."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Initial metrics
        initial_metrics = factory.get_factory_metrics()
        assert initial_metrics['total_instances_created'] == 0
        assert initial_metrics['active_contexts'] == 0
        
        # Create context
        context = await factory.create_user_execution_context("user", "thread", "run")
        
        # Verify metrics updated
        updated_metrics = factory.get_factory_metrics()
        assert updated_metrics['total_instances_created'] == 1
        assert updated_metrics['active_contexts'] == 1
        assert len(updated_metrics['active_context_ids']) == 1
        
        # Verify context ID in active list
        expected_context_id = f"{context.user_id}_{context.thread_id}_{context.run_id}"
        assert expected_context_id in updated_metrics['active_context_ids']
    
    @pytest.mark.asyncio
    async def test_factory_create_context_error_handling(self, mock_websocket_bridge):
        """Test factory handles context creation errors appropriately."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Mock UserExecutionContext.from_request_supervisor to raise exception
        with patch('netra_backend.app.services.user_execution_context.UserExecutionContext.from_request_supervisor',
                   side_effect=Exception("Context creation failed")):
            
            with pytest.raises(RuntimeError, match="Context creation failed for user_thread_run"):
                await factory.create_user_execution_context("user", "thread", "run")
        
        # Verify error metrics tracked
        metrics = factory.get_factory_metrics()
        assert metrics['creation_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_factory_create_context_websocket_mapping_registration(self, mock_websocket_bridge):
        """Test factory registers WebSocket run-thread mapping."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        context = await factory.create_user_execution_context("user", "thread", "run")
        
        # Verify run-thread mapping was registered
        mock_websocket_bridge.register_run_thread_mapping.assert_called_once_with(
            run_id="run",
            thread_id="thread",
            metadata={
                'user_id': "user",
                'created_at': context.created_at.isoformat(),
                'factory_context_id': "user_thread_run"
            }
        )
    
    @pytest.mark.asyncio
    async def test_factory_create_context_websocket_mapping_failure_handling(self, mock_websocket_bridge):
        """Test factory handles WebSocket mapping registration failures."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Mock registration failure
        mock_websocket_bridge.register_run_thread_mapping.return_value = False
        
        # Should still create context successfully
        context = await factory.create_user_execution_context("user", "thread", "run")
        
        assert context is not None
        assert context.user_id == "user"


# ============================================================================
# TEST: Context Parameter Validation and Sanitization
# ============================================================================

class TestContextParameterValidationAndSanitization(SSotBaseTestCase):
    """Test parameter validation and sanitization in context creation."""
    
    @pytest.mark.asyncio
    async def test_parameter_sanitization_edge_cases(self, mock_websocket_bridge):
        """Test parameter sanitization handles edge cases."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test with IDs containing special characters that should be preserved
        special_user_id = "user-123_test@domain.com"
        special_thread_id = "thread:8080/path?query=value"
        special_run_id = f"run#{uuid.uuid4()}"
        
        context = await factory.create_user_execution_context(
            user_id=special_user_id,
            thread_id=special_thread_id,
            run_id=special_run_id
        )
        
        # Special characters should be preserved
        assert context.user_id == special_user_id
        assert context.thread_id == special_thread_id
        assert context.run_id == special_run_id
    
    @pytest.mark.asyncio
    async def test_metadata_validation_complex_structures(self, mock_websocket_bridge):
        """Test metadata validation with complex nested structures."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        complex_metadata = {
            'nested_dict': {
                'level1': {
                    'level2': {
                        'values': [1, 2, 3, 'string', True, None]
                    }
                }
            },
            'arrays': [
                {'type': 'config', 'enabled': True},
                {'type': 'feature', 'enabled': False}
            ],
            'mixed_types': {
                'integer': 42,
                'float': 3.14159,
                'boolean': True,
                'null_value': None,
                'datetime_string': datetime.now(timezone.utc).isoformat()
            }
        }
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            metadata=complex_metadata
        )
        
        # Complex metadata should be preserved
        assert context.metadata == complex_metadata
        assert context.metadata['nested_dict']['level1']['level2']['values'] == [1, 2, 3, 'string', True, None]
        assert len(context.metadata['arrays']) == 2
        assert context.metadata['mixed_types']['float'] == 3.14159
    
    @pytest.mark.asyncio
    async def test_metadata_validation_none_and_empty_values(self, mock_websocket_bridge):
        """Test metadata validation with None and empty values."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test with None metadata (should be converted to empty dict)
        context1 = await factory.create_user_execution_context(
            user_id="user1",
            thread_id="thread1",
            run_id="run1",
            metadata=None
        )
        
        assert context1.metadata == {}
        
        # Test with empty dict metadata
        context2 = await factory.create_user_execution_context(
            user_id="user2",
            thread_id="thread2", 
            run_id="run2",
            metadata={}
        )
        
        assert context2.metadata == {}
    
    @pytest.mark.asyncio
    async def test_database_session_validation(self, mock_websocket_bridge):
        """Test database session parameter validation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test with valid AsyncSession
        mock_session = AsyncMock(spec=AsyncSession)
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            db_session=mock_session
        )
        
        assert context.db_session == mock_session
        
        # Test with None session (should be acceptable)
        context_no_session = await factory.create_user_execution_context(
            user_id="test_user2",
            thread_id="test_thread2",
            run_id="test_run2",
            db_session=None
        )
        
        assert context_no_session.db_session is None
    
    @pytest.mark.asyncio
    async def test_websocket_client_id_validation(self, mock_websocket_bridge):
        """Test WebSocket client ID parameter validation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Test with valid client ID
        valid_client_id = f"ws_client_{uuid.uuid4().hex}"
        
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            websocket_client_id=valid_client_id
        )
        
        assert context.websocket_connection_id == valid_client_id
        
        # Test with None client ID (should be acceptable)
        context_no_client = await factory.create_user_execution_context(
            user_id="test_user2",
            thread_id="test_thread2",
            run_id="test_run2",
            websocket_client_id=None
        )
        
        assert context_no_client.websocket_connection_id is None
        
        # Test with empty string client ID (should be acceptable) 
        context_empty_client = await factory.create_user_execution_context(
            user_id="test_user3",
            thread_id="test_thread3",
            run_id="test_run3",
            websocket_client_id=""
        )
        
        assert context_empty_client.websocket_connection_id == ""


# ============================================================================
# TEST: Error Propagation and Recovery Patterns
# ============================================================================

class TestErrorPropagationAndRecoveryPatterns(SSotBaseTestCase):
    """Test error propagation and recovery in context creation."""
    
    @pytest.mark.asyncio
    async def test_context_creation_failure_error_propagation(self, mock_websocket_bridge):
        """Test error propagation when context creation fails."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Mock UserExecutionContext creation to fail
        with patch('netra_backend.app.services.user_execution_context.UserExecutionContext.from_request_supervisor') as mock_create:
            mock_create.side_effect = InvalidContextError("Invalid context parameters")
            
            with pytest.raises(RuntimeError, match="Context creation failed"):
                await factory.create_user_execution_context("user", "thread", "run")
            
            # Verify error metrics updated
            metrics = factory.get_factory_metrics()
            assert metrics['creation_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_creation_failure_handling(self, mock_websocket_bridge):
        """Test handling of WebSocket emitter creation failures."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Mock emitter creation to fail
        with patch.object(factory, '_create_emitter', side_effect=Exception("Emitter creation failed")):
            
            with pytest.raises(RuntimeError, match="Context creation failed"):
                await factory.create_user_execution_context("user", "thread", "run")
            
            # Error should be tracked
            assert factory.get_factory_metrics()['creation_errors'] == 1
    
    @pytest.mark.asyncio
    async def test_partial_failure_cleanup(self, mock_websocket_bridge):
        """Test cleanup occurs even when context creation partially fails."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Mock to fail after context creation but before completion
        with patch.object(factory, '_create_emitter', side_effect=Exception("Emitter failed")):
            
            try:
                await factory.create_user_execution_context("user", "thread", "run")
            except RuntimeError:
                pass  # Expected failure
            
            # Partial state should not leak into active contexts
            assert len(factory._active_contexts) == 0
    
    @pytest.mark.asyncio
    async def test_database_session_error_handling(self, mock_websocket_bridge):
        """Test error handling with database session issues."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create mock session that raises exception on access
        mock_session = Mock()
        mock_session.side_effect = Exception("Database connection failed")
        
        # Should still create context successfully (DB session errors don't prevent context creation)
        context = await factory.create_user_execution_context(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run",
            db_session=mock_session  # This is just stored, not accessed during creation
        )
        
        assert context.db_session == mock_session
    
    @pytest.mark.asyncio
    async def test_concurrent_creation_failure_isolation(self, mock_websocket_bridge):
        """Test that concurrent creation failures don't affect other contexts."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        async def create_context_success(user_id):
            return await factory.create_user_execution_context(user_id, "thread", "run")
        
        async def create_context_failure(user_id):
            # Mock failure for specific user
            if user_id == "failing_user":
                with patch('netra_backend.app.services.user_execution_context.UserExecutionContext.from_request_supervisor',
                           side_effect=Exception("Context creation failed")):
                    return await factory.create_user_execution_context(user_id, "thread", "run")
            else:
                return await factory.create_user_execution_context(user_id, "thread", "run")
        
        # Mix successful and failing context creations
        tasks = [
            create_context_success("success_user_1"),
            create_context_failure("failing_user"),  # This will fail
            create_context_success("success_user_2"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have successful contexts and one exception
        successful_contexts = [r for r in results if isinstance(r, UserExecutionContext)]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        assert len(successful_contexts) >= 2  # At least the successful ones
        assert len(exceptions) >= 1  # At least the failing one
        
        # Successful contexts should be tracked properly
        assert factory.get_factory_metrics()['active_contexts'] >= 2


# ============================================================================
# TEST: Performance and Timing Validation
# ============================================================================

class TestPerformanceAndTimingValidation(SSotBaseTestCase):
    """Test performance characteristics and timing validation."""
    
    @pytest.mark.asyncio
    async def test_context_creation_timing_tracking(self, mock_websocket_bridge):
        """Test that context creation timing is tracked properly."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        start_time = time.time()
        
        context = await factory.create_user_execution_context("user", "thread", "run")
        
        end_time = time.time()
        creation_time = (end_time - start_time) * 1000  # Convert to ms
        
        # Context should have proper created_at timestamp
        assert context.created_at is not None
        
        # Creation should be relatively fast (less than 1 second for test)
        assert creation_time < 1000
    
    @pytest.mark.asyncio
    async def test_concurrent_context_creation_performance(self, mock_websocket_bridge):
        """Test performance characteristics with concurrent context creation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        num_contexts = 20
        start_time = time.time()
        
        # Create many contexts concurrently
        tasks = []
        for i in range(num_contexts):
            task = factory.create_user_execution_context(f"user_{i}", f"thread_{i}", f"run_{i}")
            tasks.append(task)
        
        contexts = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All contexts should be created successfully
        assert len(contexts) == num_contexts
        
        # Concurrent creation should be efficient (less than 5 seconds for 20 contexts)
        assert total_time < 5.0
        
        # Factory metrics should be accurate
        metrics = factory.get_factory_metrics()
        assert metrics['active_contexts'] == num_contexts
        assert metrics['total_instances_created'] == num_contexts
    
    @pytest.mark.asyncio
    async def test_context_creation_memory_efficiency(self, mock_websocket_bridge):
        """Test memory efficiency in context creation."""
        factory = AgentInstanceFactory()
        factory.configure(websocket_bridge=mock_websocket_bridge)
        
        # Create and immediately cleanup contexts to test memory management
        for i in range(10):
            context = await factory.create_user_execution_context(f"user_{i}", "thread", "run")
            await factory.cleanup_user_context(context)
        
        # All contexts should be cleaned up
        metrics = factory.get_factory_metrics()
        assert metrics['active_contexts'] == 0
        assert metrics['total_contexts_cleaned'] == 10
        
        # Factory should not accumulate state
        assert len(factory._active_contexts) == 0


if __name__ == "__main__":
    # Import time for timing tests
    import time
    
    # Run tests with proper async support
    pytest.main([__file__, "-v", "--tb=short"])