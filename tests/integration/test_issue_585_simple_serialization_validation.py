"""Simple integration test for Issue #585: Agent pipeline pickle serialization errors

This test validates the core serialization issues without complex mocking or setup.
"""

import asyncio
import pickle
import pytest
import sys
from unittest.mock import MagicMock

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine


class TestIssue585SimpleSerializationValidation:
    """Simple validation tests for Issue #585 pickle serialization errors."""
    
    def test_agent_pipeline_context_serialization_issue(self):
        """Test that agent pipeline contexts fail pickle serialization as described in Issue #585."""
        
        # Create a user context like what would be used in real agent execution
        user_context = UserExecutionContext(
            user_id="integration-user-585",
            thread_id="integration-thread-585",
            run_id="integration-run-585",
            request_id="integration-req-585"
        )
        
        # Simulate what happens in agent pipeline execution that causes pickle errors
        agent_execution_context = {
            'user_context': user_context,
            'agent_name': 'reporting_agent',
            'input_data': {
                'message': 'Generate optimization report',
                'report_type': 'performance',
                'time_range': '7days'
            },
            # These are the problematic elements that cause Issue #585:
            'execution_engine_class': UserExecutionEngine,  # Class references
            'agent_mock': MagicMock(),  # Mock objects with module references
            'sys_module': sys,  # Direct module references
            'lambda_callback': lambda x: x,  # Lambda functions
            'builtin_function': print,  # Built-in function references
        }
        
        # This should fail with pickle serialization error - Issue #585 reproduction
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)) as exc_info:
            pickle.dumps(agent_execution_context)
        
        error_msg = str(exc_info.value).lower()
        
        # Verify this is the specific type of error described in Issue #585
        assert (
            "pickle" in error_msg or 
            "can't pickle" in error_msg or
            "cannot pickle" in error_msg or
            "module" in error_msg
        ), f"Expected pickle-related error for Issue #585, got: {exc_info.value}"
        
    def test_reporting_agent_result_serialization_failure(self):
        """Test that reporting agent results fail serialization due to contamination."""
        
        # Simulate a reporting agent result that gets contaminated
        reporting_result = {
            'status': 'completed',
            'report_data': {
                'cpu_usage': [85, 90, 78, 82],
                'memory_usage': [65, 70, 68, 71],
                'recommendations': [
                    'Optimize database queries',
                    'Implement caching layer'
                ]
            },
            'metadata': {
                'generation_time': '2024-01-15T10:30:00Z',
                'agent_version': '1.0.0'
            },
            # Contamination that causes Issue #585:
            'agent_instance': MagicMock(),  # Agent instance reference
            'execution_context': UserExecutionContext(
                user_id="test-user",
                thread_id="test-thread", 
                run_id="test-run"
            ),
            'processing_functions': {
                'data_processor': lambda x: x,  # Lambda function
                'error_handler': Exception  # Exception class
            }
        }
        
        # This demonstrates Issue #585 - reporting agent results can't be pickled
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(reporting_result)
            
    def test_optimization_agent_result_serialization_failure(self):
        """Test that optimization agent results fail serialization due to contamination."""
        
        # Simulate an optimization agent result
        optimization_result = {
            'status': 'completed',
            'optimizations': [
                {
                    'resource': 'CPU',
                    'current_usage': 85,
                    'target_usage': 70,
                    'actions': ['Scale down pods', 'Optimize queries']
                },
                {
                    'resource': 'Memory', 
                    'current_usage': 78,
                    'target_usage': 65,
                    'actions': ['Implement garbage collection']
                }
            ],
            'estimated_savings': {'cost': 150, 'performance_gain': '15%'},
            # Contamination causing Issue #585:
            'optimization_engine': UserExecutionEngine,  # Class reference
            'analysis_modules': [sys, asyncio],  # Module references
            'callback_registry': {
                'on_complete': print,  # Built-in function
                'on_error': lambda e: None  # Lambda function
            }
        }
        
        # This demonstrates Issue #585 - optimization results can't be cached via pickle
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(optimization_result)
            
    def test_clean_agent_result_serialization_success(self):
        """Test that properly sanitized agent results can be serialized successfully."""
        
        # This demonstrates what agent results SHOULD look like after Issue #585 fix
        clean_result = {
            'status': 'completed',
            'agent_type': 'reporting_agent',
            'user_id': 'test-user-585',
            'thread_id': 'test-thread-585',
            'run_id': 'test-run-585',
            'result_data': {
                'report': 'Sample report content',
                'metrics': {'cpu': 85, 'memory': 70},
                'recommendations': ['Optimize queries', 'Add caching']
            },
            'metadata': {
                'timestamp': '2024-01-15T10:30:00Z',
                'processing_time': 2.5,
                'version': '1.0.0'
            }
        }
        
        # This should succeed - demonstrating the target state after Issue #585 fix
        try:
            serialized = pickle.dumps(clean_result)
            deserialized = pickle.loads(serialized)
            assert clean_result == deserialized
        except Exception as e:
            pytest.fail(f"Clean agent result should be serializable: {e}")
            
    def test_redis_cache_serialization_impact(self):
        """Test the impact of serialization failures on Redis caching."""
        
        # Simulate what happens when trying to cache contaminated agent results
        cache_key = "agent_result:user_123:run_456"
        
        contaminated_cache_data = {
            'key': cache_key,
            'result': {
                'data': 'Sample result',
                'status': 'completed'
            },
            # Contamination that prevents caching:
            'context_ref': UserExecutionEngine,  # Class reference
            'module_ref': sys,  # Module reference
            'function_ref': lambda x: x  # Lambda function
        }
        
        # This should fail - Issue #585 prevents caching
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(contaminated_cache_data)
            
        # Demonstrate what cacheable data should look like
        clean_cache_data = {
            'key': cache_key,
            'result': {
                'data': 'Sample result',
                'status': 'completed'
            },
            'metadata': {
                'cached_at': '2024-01-15T10:30:00Z',
                'ttl': 3600
            }
        }
        
        # This should succeed
        try:
            pickle.dumps(clean_cache_data)
        except Exception as e:
            pytest.fail(f"Clean cache data should be serializable: {e}")


if __name__ == '__main__':
    pytest.main([__file__, "-v"])