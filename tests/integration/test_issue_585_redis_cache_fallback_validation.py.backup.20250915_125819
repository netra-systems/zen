"""Integration test for Issue #585: Redis cache fallback behavior with pickle errors

Tests the Redis cache manager's handling of pickle serialization failures
and validates that fallback mechanisms work correctly.
"""
import asyncio
import pickle
import pytest
import sys
from unittest.mock import MagicMock, patch, AsyncMock
from netra_backend.app.cache.redis_cache_manager import RedisCacheManager
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

@pytest.mark.integration
class TestIssue585RedisCacheFallbackValidation:
    """Test Redis cache fallback behavior for Issue #585 pickle errors."""

    @pytest.fixture
    def cache_manager(self):
        """Create cache manager for testing."""
        return RedisCacheManager(namespace='test-issue-585')

    @pytest.fixture
    def user_context(self):
        """Create user context for testing."""
        return UserExecutionContext(user_id='cache-test-user-585', thread_id='cache-test-thread-585', run_id='cache-test-run-585')

    async def test_pickle_fallback_to_string_serialization(self, cache_manager):
        """Test that cache manager falls back to string when pickle fails."""
        unpicklable_data = {'result': 'agent execution result', 'status': 'completed', 'agent_class': UserExecutionEngine, 'module_ref': sys, 'lambda_func': lambda x: x, 'mock_obj': MagicMock()}
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            result = await cache_manager.set('test-key-585', unpicklable_data)
            assert result is True
            mock_redis.set.assert_called_once()
            call_args = mock_redis.set.call_args
            stored_value = call_args[0][1]
            assert isinstance(stored_value, str)
            assert 'agent execution result' in stored_value

    async def test_agent_result_caching_with_contamination(self, cache_manager, user_context):
        """Test caching of contaminated agent results."""
        contaminated_result = {'user_id': user_context.user_id, 'thread_id': user_context.thread_id, 'run_id': user_context.run_id, 'agent_name': 'reporting_agent', 'result_data': {'report': 'Performance analysis complete', 'metrics': {'cpu': 85, 'memory': 70}, 'recommendations': ['Optimize queries', 'Add caching']}, 'execution_context': user_context, 'agent_instance': MagicMock(), 'processing_engine': UserExecutionEngine}
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(contaminated_result)
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            cache_key = f'agent_result:{user_context.user_id}:{user_context.run_id}'
            success = await cache_manager.set(cache_key, contaminated_result)
            assert success is True
            mock_redis.set.assert_called_once()

    async def test_cache_retrieval_with_mixed_serialization(self, cache_manager):
        """Test cache retrieval handles mixed serialization formats."""
        test_cases = [{'key': 'json-serializable', 'data': {'status': 'success', 'count': 42}, 'expected_format': 'json'}, {'key': 'pickle-only', 'data': {'status': 'success', 'complex': set([1, 2, 3])}, 'expected_format': 'pickle'}, {'key': 'string-fallback', 'data': {'status': 'success', 'unpicklable': UserExecutionEngine}, 'expected_format': 'string'}]
        for test_case in test_cases:
            with patch.object(cache_manager, 'redis_client') as mock_redis:
                mock_redis.set = AsyncMock(return_value=True)
                mock_redis.get = AsyncMock()
                await cache_manager.set(test_case['key'], test_case['data'])
                call_args = mock_redis.set.call_args[0]
                stored_value = call_args[1]
                if test_case['expected_format'] == 'string':
                    assert isinstance(stored_value, str)
                else:
                    assert stored_value != str(test_case['data'])

    async def test_redis_cache_error_handling_with_pickle_failures(self, cache_manager):
        """Test Redis cache error handling when both pickle and JSON fail."""
        problematic_data = {'circular_ref': None, 'module_ref': sys, 'class_ref': UserExecutionEngine}
        problematic_data['circular_ref'] = problematic_data
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            success = await cache_manager.set('problematic-key', problematic_data)
            assert success is True
            call_args = mock_redis.set.call_args[0]
            stored_value = call_args[1]
            assert isinstance(stored_value, str)

    async def test_cache_performance_impact_of_serialization_fallbacks(self, cache_manager):
        """Test performance impact of serialization fallbacks on cache operations."""
        test_data = [{'type': 'json', 'data': {'simple': 'data'}}, {'type': 'pickle', 'data': {'complex': set([1, 2, 3])}}, {'type': 'fallback', 'data': {'unpicklable': lambda x: x}}]
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            import time
            start_time = time.time()
            for i, item in enumerate(test_data):
                await cache_manager.set(f'perf-test-{i}', item['data'])
            elapsed = time.time() - start_time
            assert elapsed < 1.0, f'Cache operations took {elapsed}s, too slow'
            assert mock_redis.set.call_count == len(test_data)

    async def test_issue_585_specific_agent_pipeline_caching(self, cache_manager):
        """Test specific Issue #585 scenario: caching agent pipeline results."""
        agent_pipeline_result = {'pipeline_id': 'reporting-pipeline-585', 'agent_results': [{'agent_name': 'data_collector', 'status': 'completed', 'data': {'records': 1500}}, {'agent_name': 'reporter', 'status': 'completed', 'report': 'Analysis complete'}], 'execution_metadata': {'start_time': '2024-01-15T10:00:00Z', 'duration': 45.2, 'total_agents': 2}, 'pipeline_executor': UserExecutionEngine, 'agent_instances': [MagicMock(), MagicMock()]}
        with pytest.raises((TypeError, AttributeError, pickle.PicklingError)):
            pickle.dumps(agent_pipeline_result)
        with patch.object(cache_manager, 'redis_client') as mock_redis:
            mock_redis.set = AsyncMock(return_value=True)
            success = await cache_manager.set('pipeline:reporting-pipeline-585', agent_pipeline_result, ttl=3600)
            assert success is True
            call_args = mock_redis.set.call_args[0]
            stored_value = call_args[1]
            assert isinstance(stored_value, str)
            assert 'reporting-pipeline-585' in stored_value
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')