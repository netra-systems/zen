"""Unit tests for Issue #585: Agent pipeline pickle module serialization errors

This test suite reproduces the "cannot pickle 'module' object" error that occurs
when agent instances and execution infrastructure are included in serialization contexts
during execute_agent_pipeline operations.

Business Value: P1 critical bug affecting reporting/optimization agents functionality.
"""

import asyncio
import pickle
import pytest
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


@pytest.fixture
def test_context():
    """Test fixture for user execution context."""
    test_user_id = "test-user-585"
    test_thread_id = "thread-585"
    test_run_id = "run-585"
    
    user_context = UserExecutionContext(
        user_id=test_user_id,
        thread_id=test_thread_id,
        run_id=test_run_id,
        request_id="req-585-test",
        agent_context={
            "test_scenario": "pickle_serialization_error",
            "agent_type": "reporting_agent"
        }
    )
    
    return {
        'user_id': test_user_id,
        'thread_id': test_thread_id,
        'run_id': test_run_id,
        'user_context': user_context
    }


class TestIssue585PickleModuleSerializationErrors:
    """Test suite to reproduce pickle module serialization errors in agent pipelines."""
        
    def test_pickle_module_object_error_reproduction(self):
        """Test to reproduce 'cannot pickle module object' error."""
        
        # Create a context that includes module objects (common cause)
        problematic_context = {
            'user_data': {'message': 'Test reporting request'},
            'agent_instance': MagicMock(),  # This will contain module references
            'execution_engine': UserExecutionEngine,  # Class reference
            'sys_module': sys,  # Direct module reference
            'imported_module': asyncio,  # Another module reference
        }
        
        # Attempt to pickle the context - this should fail
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)) as exc_info:
            pickle.dumps(problematic_context)
        
        error_message = str(exc_info.value).lower()
        assert "pickle" in error_message or "can't" in error_message or "module" in error_message
        
        # Verify specific error patterns - this confirms Issue #585 reproduction
        assert (
            "can't pickle" in error_message or
            "cannot pickle" in error_message or
            "module" in error_message or
            "not picklable" in error_message
        )
        
    def test_agent_context_contamination_serialization(self, test_context):
        """Test agent context contamination causing serialization failures."""
        
        # Create agent execution context with contaminated metadata
        contaminated_metadata = {
            'user_request': 'Generate optimization report',
            'agent_class': UserExecutionEngine,  # Class reference causes issues
            'execution_module': sys.modules[__name__],  # Module reference
            'callback_functions': {
                'on_complete': lambda x: x,  # Lambda functions can't be pickled
                'error_handler': print  # Built-in function references
            }
        }
        
        agent_context = AgentExecutionContext(
            user_id=test_context['user_id'],
            thread_id=test_context['thread_id'],
            run_id=test_context['run_id'],
            request_id="req-585-contaminated",
            agent_name="reporting_agent",
            metadata=contaminated_metadata
        )
        
        # Attempt to serialize the context
        with pytest.raises((TypeError, AttributeError, pickle.PickleError)):
            pickle.dumps(agent_context)
            
    def test_clean_context_serialization_success(self, test_context):
        """Test that clean contexts can be serialized successfully."""
        
        # Create a clean context with only serializable data
        clean_context = {
            'user_request': 'Generate optimization report',
            'user_id': test_context['user_id'],
            'thread_id': test_context['thread_id'],
            'agent_name': 'reporting_agent',
            'input_data': {
                'query_type': 'optimization',
                'time_range': '7days',
                'metrics': ['cpu_usage', 'memory_usage']
            }
        }
        
        # This should succeed
        try:
            serialized = pickle.dumps(clean_context)
            deserialized = pickle.loads(serialized)
            assert clean_context == deserialized
        except Exception as e:
            pytest.fail(f"Clean context serialization failed: {e}")
            
    def test_user_execution_context_serialization(self, test_context):
        """Test UserExecutionContext serialization behavior."""
        
        # Test base context
        try:
            pickle.dumps(test_context['user_context'])
        except Exception as e:
            # Document the error for Issue #585 analysis
            pytest.fail(f"UserExecutionContext serialization failed: {e}")
            
        # Test context with problematic additional_context
        problematic_user_context = UserExecutionContext(
            user_id=test_context['user_id'],
            thread_id=test_context['thread_id'],
            run_id=test_context['run_id'],
            request_id="req-585-problematic",
            agent_context={
                'agent_instance': UserExecutionEngine,  # Class reference
                'module_ref': sys,  # Module reference
            }
        )
        
        with pytest.raises((TypeError, AttributeError, pickle.PickleError)):
            pickle.dumps(problematic_user_context)

    @patch('netra_backend.app.cache.redis_cache_manager.pickle.dumps')
    def test_redis_cache_pickle_fallback_behavior(self, mock_pickle_dumps, test_context):
        """Test Redis cache fallback when pickle serialization fails."""
        
        # Simulate pickle failure
        mock_pickle_dumps.side_effect = TypeError("cannot pickle 'module' object")
        
        from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
        
        cache_manager = RedisCacheManager(namespace="test-585")
        
        # Create data that would cause pickle errors
        problematic_data = {
            'agent_instance': UserExecutionEngine,
            'module_ref': sys,
            'user_context': test_context['user_context']
        }
        
        # This should trigger fallback behavior in the cache manager
        # The current implementation should handle this gracefully
        try:
            # Note: This is testing the fallback mechanism, not success
            result = asyncio.run(cache_manager.set("test-key-585", problematic_data))
            # The cache manager should handle the pickle error gracefully
        except Exception as e:
            # Document if fallback mechanism is not working
            pytest.fail(f"Cache manager failed to handle pickle error gracefully: {e}")

    def test_agent_pipeline_context_sanitization_need(self, test_context):
        """Test to demonstrate the need for context sanitization in agent pipelines."""
        
        # Create execution context that mimics what happens in execute_agent_pipeline
        pipeline_input = {
            'message': 'Generate performance report',
            'user_id': test_context['user_id'],
            'agent_type': 'reporting_agent'
        }
        
        # This simulates what might happen inside execute_agent_pipeline
        # where agent instances get mixed into the context
        execution_state = {
            'input_data': pipeline_input,
            'user_context': test_context['user_context'],
            # These are problematic inclusions that happen in practice:
            'execution_engine_ref': UserExecutionEngine,  # Class reference
            'current_module': sys.modules[__name__],  # Module reference
            'agent_registry': MagicMock(),  # Mock with module references
        }
        
        # This should fail to pickle
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(execution_state)
        
        # Demonstrate what should be sanitized
        sanitized_state = {
            'input_data': pipeline_input,
            'user_context_data': {
                'user_id': test_context['user_context'].user_id,
                'thread_id': test_context['user_context'].thread_id,
                'run_id': test_context['user_context'].run_id,
                'request_id': test_context['user_context'].request_id,
                # additional_context should be filtered for serializability
            }
        }
        
        # This should succeed
        try:
            pickle.dumps(sanitized_state)
        except Exception as e:
            pytest.fail(f"Sanitized state should be serializable: {e}")


if __name__ == '__main__':
    pytest.main([__file__, "-v"])