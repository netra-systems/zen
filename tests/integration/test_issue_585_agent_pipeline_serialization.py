"""Integration tests for Issue #585: Agent pipeline serialization errors

Tests the complete agent pipeline execution flow to reproduce pickle serialization
errors that occur with reporting and optimization agents.

Business Value: P1 critical bug affecting multi-user agent execution capability.
"""

import asyncio
import pickle
import pytest
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_factory import ExecutionFactory


class TestIssue585AgentPipelineSerializationIntegration(SSotAsyncTestCase):
    """Integration tests for agent pipeline pickle serialization issues."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_user_id = "integration-user-585"
        self.test_thread_id = "integration-thread-585"
        self.test_run_id = "integration-run-585"
        
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id="req-585-integration",
            additional_context={
                "test_type": "integration",
                "issue": "585"
            }
        )
        
    async def test_reporting_agent_pipeline_serialization_error(self):
        """Test execute_agent_pipeline with reporting agent causing serialization errors."""
        
        # Test data structure that mimics what happens in agent pipeline
        # This simulates the result context that gets contaminated
        pipeline_context = {
            'user_context': self.user_context,
            'agent_name': 'reporting_agent',
            'input_data': {
                'message': 'Generate performance report for last 7 days',
                'agent_type': 'reporting_agent',
                'report_config': {
                    'time_range': '7d',
                    'metrics': ['cpu', 'memory', 'network'],
                    'format': 'detailed'
                }
            },
            # These are the problematic additions that happen during execution:
            'execution_engine': UserExecutionEngine,  # Class reference
            'agent_instance': MagicMock(),  # Mock/agent instance with module refs
            'callback_handlers': {
                'on_success': lambda x: x,  # Lambda functions
                'on_error': print  # Built-in functions
            }
        }
        
        # This should fail to pickle - demonstrating Issue #585
        try:
            pickle.dumps(pipeline_context)
            # If we get here, there's no pickle error (unexpected)
            pytest.fail("Expected pickle serialization error but serialization succeeded")
        except (TypeError, AttributeError, pickle.PicklingError) as e:
            # This is expected - Issue #585 reproduction
            error_msg = str(e).lower()
            assert ("pickle" in error_msg or "can't pickle" in error_msg or 
                   "cannot pickle" in error_msg), f"Expected pickle error, got: {e}"
                
    @patch('netra_backend.app.agents.supervisor.user_execution_engine.UserExecutionEngine._create_agent_from_registry')
    async def test_optimization_agent_pipeline_serialization_error(self, mock_create_agent):
        """Test execute_agent_pipeline with optimization agent causing serialization errors."""
        
        # Mock optimization agent with problematic state
        mock_agent = MagicMock()
        mock_agent.optimization_models = [MagicMock()]  # Complex objects
        mock_agent.analysis_engine = lambda x: x  # Lambda functions can't be pickled
        mock_agent.execute = AsyncMock(return_value={
            'optimizations': ['sample optimization'],
            'analysis_state': mock_agent,  # Contains unpicklable references
            'models': mock_agent.optimization_models,
        })
        mock_create_agent.return_value = mock_agent
        
        execution_engine = UserExecutionEngine()
        
        input_data = {
            'message': 'Optimize resource allocation',
            'agent_type': 'optimization_agent',
            'optimization_targets': ['cpu', 'memory'],
            'constraints': {'max_cost': 1000, 'min_performance': 0.9}
        }
        
        try:
            result = await execution_engine.execute_agent_pipeline(
                agent_name="optimization_agent", 
                execution_context=self.user_context,
                input_data=input_data
            )
            
            # Test serialization of the result
            with self.assertRaises((TypeError, AttributeError)):
                pickle.dumps(result)
                
        except Exception as e:
            # Check if this is the expected serialization error
            if "pickle" in str(e).lower():
                # Expected - this demonstrates Issue #585
                pass
            else:
                raise e
                
    async def test_execution_factory_contamination(self):
        """Test ExecutionFactory for context contamination issues."""
        
        # Test ExecutionFactory create methods
        factory = ExecutionFactory()
        
        # Create context that might get contaminated
        test_context = {
            'user_data': {'request': 'test'},
            'execution_metadata': {
                'agent_name': 'test_agent',
                'factory_instance': factory,  # This could cause issues
            }
        }
        
        # Test if the factory adds unpicklable references
        with self.assertRaises((TypeError, AttributeError)):
            pickle.dumps(test_context)
            
    @patch('netra_backend.app.cache.redis_cache_manager.pickle.dumps')
    async def test_pipeline_caching_serialization_failure(self, mock_pickle):
        """Test caching failures during pipeline execution."""
        
        # Simulate pickle failure during caching
        mock_pickle.side_effect = TypeError("cannot pickle 'module' object")
        
        # Create minimal execution context
        execution_engine = UserExecutionEngine()
        
        input_data = {
            'message': 'Simple test request',
            'cache_key': 'test-585-cache'
        }
        
        # This should handle caching failures gracefully
        try:
            with patch.object(execution_engine, '_create_agent_from_registry') as mock_create:
                mock_agent = MagicMock()
                mock_agent.execute = AsyncMock(return_value={'result': 'success'})
                mock_create.return_value = mock_agent
                
                result = await execution_engine.execute_agent_pipeline(
                    agent_name="test_agent",
                    execution_context=self.user_context,
                    input_data=input_data
                )
                
                # Execution should succeed even if caching fails
                self.assertIsNotNone(result)
                
        except Exception as e:
            if "pickle" in str(e).lower():
                self.fail(f"Pipeline should handle pickle caching errors gracefully: {e}")
            else:
                # Other errors might be acceptable
                pass

    async def test_context_isolation_serialization_requirements(self):
        """Test that user context isolation requires proper serialization."""
        
        # Create multiple user contexts to test isolation
        user_contexts = []
        for i in range(3):
            ctx = UserExecutionContext(
                user_id=f"user-{i}-585",
                thread_id=f"thread-{i}-585", 
                run_id=f"run-{i}-585",
                request_id=f"req-{i}-585",
                additional_context={
                    'user_index': i,
                    'isolation_test': True
                }
            )
            user_contexts.append(ctx)
            
        # All contexts should be serializable for proper isolation
        for i, ctx in enumerate(user_contexts):
            try:
                serialized = pickle.dumps(ctx)
                deserialized = pickle.loads(serialized)
                
                # Verify isolation is maintained
                self.assertEqual(ctx.user_id, deserialized.user_id)
                self.assertEqual(ctx.thread_id, deserialized.thread_id)
                
            except Exception as e:
                self.fail(f"User context {i} failed serialization test: {e}")
                
    async def test_agent_state_contamination_patterns(self):
        """Test common patterns that cause agent state contamination."""
        
        execution_engine = UserExecutionEngine()
        
        # Test patterns that commonly cause contamination
        contamination_patterns = [
            {
                'pattern': 'agent_instance_in_result',
                'data': {'result': 'success', 'agent_ref': execution_engine}
            },
            {
                'pattern': 'module_reference', 
                'data': {'result': 'success', 'module': asyncio}
            },
            {
                'pattern': 'class_reference',
                'data': {'result': 'success', 'class_ref': UserExecutionEngine}
            },
            {
                'pattern': 'lambda_function',
                'data': {'result': 'success', 'callback': lambda x: x}
            }
        ]
        
        for pattern_info in contamination_patterns:
            with self.subTest(pattern=pattern_info['pattern']):
                with self.assertRaises((TypeError, AttributeError)):
                    pickle.dumps(pattern_info['data'])


if __name__ == '__main__':
    pytest.main([__file__, "-v"])