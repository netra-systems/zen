"""Unit tests for AgentExecutionCore metrics and performance tracking.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure accurate performance monitoring and resource tracking
- Value Impact: Agents must provide reliable metrics for optimization and billing
- Strategic Impact: Performance data enables platform optimization and cost allocation

These unit tests validate metrics collection, performance calculations, and resource monitoring.
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
from netra_backend.app.agents.state import DeepAgentState


class TestAgentExecutionCoreMetrics:
    """Unit tests for AgentExecutionCore metrics functionality."""
    
    @pytest.fixture
    def execution_core(self):
        """Create execution core with mocked dependencies."""
        mock_registry = Mock()
        mock_websocket_bridge = Mock()
        
        with patch('netra_backend.app.core.execution_tracker.get_execution_tracker'):
            return AgentExecutionCore(mock_registry, mock_websocket_bridge)
    
    @pytest.fixture
    def sample_state(self):
        """Sample agent state with test data."""
        state = Mock(spec=DeepAgentState)
        state.user_id = "test-user-123"
        state.thread_id = "test-thread-456"
        state.__dict__ = {
            'user_id': 'test-user-123',
            'thread_id': 'test-thread-456',
            'data': {'key': 'value'},
            'context': 'test context'
        }
        return state
    
    def test_calculate_performance_metrics_timing_accuracy(self, execution_core):
        """Test that performance metrics calculate timing accurately."""
        # Start time 2.5 seconds ago
        start_time = time.time() - 2.5
        
        metrics = execution_core._calculate_performance_metrics(start_time)
        
        # Verify timing accuracy (allow 100ms tolerance)
        expected_ms = 2500
        actual_ms = metrics['execution_time_ms']
        assert abs(actual_ms - expected_ms) < 100
        
        # Verify timestamp structure
        assert metrics['start_timestamp'] == start_time
        assert metrics['end_timestamp'] > start_time
        assert metrics['end_timestamp'] - start_time > 2.4  # At least 2.4s elapsed
    
    def test_calculate_performance_metrics_with_heartbeat(self, execution_core):
        """Test performance metrics includes heartbeat count when available."""
        mock_heartbeat = Mock()
        mock_heartbeat.pulse_count = 15
        
        start_time = time.time() - 1.0
        metrics = execution_core._calculate_performance_metrics(start_time, mock_heartbeat)
        
        # Verify heartbeat metric is included
        assert 'heartbeat_count' in metrics
        assert metrics['heartbeat_count'] == 15
        
        # Verify other metrics still present
        assert 'execution_time_ms' in metrics
        assert 'start_timestamp' in metrics
    
    @patch('psutil.Process')
    def test_calculate_performance_metrics_system_resources(self, mock_psutil_process, execution_core):
        """Test system resource metrics collection."""
        # Mock psutil process data
        mock_process_instance = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 134217728  # 128 MB in bytes
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process_instance.cpu_percent.return_value = 45.2
        mock_psutil_process.return_value = mock_process_instance
        
        start_time = time.time() - 0.5
        metrics = execution_core._calculate_performance_metrics(start_time)
        
        # Verify system metrics
        assert 'memory_usage_mb' in metrics
        assert 'cpu_percent' in metrics
        assert metrics['memory_usage_mb'] == 128.0  # 128 MB
        assert metrics['cpu_percent'] == 45.2
    
    @patch('psutil.Process')
    def test_calculate_performance_metrics_psutil_error_handling(self, mock_psutil_process, execution_core):
        """Test graceful handling when psutil fails."""
        # Make psutil raise an exception
        mock_psutil_process.side_effect = Exception("psutil error")
        
        start_time = time.time() - 1.0
        metrics = execution_core._calculate_performance_metrics(start_time)
        
        # Should still have basic metrics, but no system metrics
        assert 'execution_time_ms' in metrics
        assert 'start_timestamp' in metrics
        assert 'memory_usage_mb' not in metrics
        assert 'cpu_percent' not in metrics
    
    @pytest.mark.asyncio
    async def test_collect_metrics_combines_all_sources(self, execution_core, sample_state):
        """Test that collect_metrics properly combines metrics from all sources."""
        exec_id = uuid4()
        
        # Mock execution tracker metrics
        execution_core.execution_tracker = Mock()
        execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={
            'db_queries': 5,
            'cache_hits': 12,
            'external_api_calls': 3
        })
        
        # Create result with its own metrics
        result = AgentExecutionResult(
            success=True,
            duration=3.75,
            metrics={
                'llm_tokens': 1250,
                'tool_executions': 4,
                'response_quality': 0.95
            }
        )
        
        # Collect comprehensive metrics
        combined_metrics = await execution_core._collect_metrics(exec_id, result, sample_state)
        
        # Verify all metric sources are combined
        assert 'db_queries' in combined_metrics  # From tracker
        assert 'cache_hits' in combined_metrics  # From tracker
        assert 'external_api_calls' in combined_metrics  # From tracker
        assert 'llm_tokens' in combined_metrics  # From result
        assert 'tool_executions' in combined_metrics  # From result
        assert 'response_quality' in combined_metrics  # From result
        
        # Verify computed metrics
        assert combined_metrics['result_success'] is True
        assert combined_metrics['total_duration_seconds'] == 3.75
        assert combined_metrics['state_size'] > 0
    
    @pytest.mark.asyncio
    async def test_collect_metrics_handles_empty_sources(self, execution_core, sample_state):
        """Test metrics collection when some sources are empty."""
        exec_id = uuid4()
        
        # Tracker returns None
        execution_core.execution_tracker = Mock()
        execution_core.execution_tracker.collect_metrics = AsyncMock(return_value=None)
        
        # Result has no metrics
        result = AgentExecutionResult(success=False, error="Test failure")
        
        combined_metrics = await execution_core._collect_metrics(exec_id, result, sample_state)
        
        # Should still create basic computed metrics
        assert isinstance(combined_metrics, dict)
        assert combined_metrics['result_success'] is False
        assert 'state_size' in combined_metrics
        assert combined_metrics['state_size'] > 0  # State has some data
        
        # No duration since result doesn't have it
        assert 'total_duration_seconds' not in combined_metrics
    
    @pytest.mark.asyncio
    async def test_collect_metrics_state_size_calculation(self, execution_core):
        """Test state size calculation for different state types."""
        exec_id = uuid4()
        execution_core.execution_tracker = Mock()
        execution_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        # Test with large state
        large_state = Mock(spec=DeepAgentState)
        large_state.__dict__ = {
            'user_id': 'user-123',
            'data': {'key' + str(i): 'value' * 100 for i in range(50)},  # Large data
            'context': 'context' * 1000
        }
        
        result = AgentExecutionResult(success=True)
        metrics = await execution_core._collect_metrics(exec_id, result, large_state)
        
        # State size should be reasonably large
        assert metrics['state_size'] > 10000  # At least 10KB of string data
        
        # Test with minimal state
        minimal_state = Mock(spec=DeepAgentState)
        minimal_state.__dict__ = {}
        
        metrics_minimal = await execution_core._collect_metrics(exec_id, result, minimal_state)
        assert metrics_minimal['state_size'] < metrics['state_size']
    
    @pytest.mark.asyncio
    async def test_persist_metrics_numeric_filtering(self, execution_core, sample_state):
        """Test that only numeric metrics are persisted."""
        exec_id = uuid4()
        
        # Mock persistence
        execution_core.persistence = Mock()
        execution_core.persistence.write_performance_metrics = AsyncMock()
        
        metrics = {
            'execution_time': 1500,      # int - should persist
            'memory_usage': 256.75,      # float - should persist
            'success_rate': 0.95,        # float - should persist
            'agent_name': 'test_agent',  # string - should skip
            'error_details': None,       # None - should skip
            'tools_used': ['tool1', 'tool2'],  # list - should skip
            'complex_data': {'nested': 'dict'}  # dict - should skip
        }
        
        await execution_core._persist_metrics(exec_id, metrics, "test_agent", sample_state)
        
        # Should be called exactly 3 times (for numeric values only)
        assert execution_core.persistence.write_performance_metrics.call_count == 3
        
        # Verify each call has proper structure
        calls = execution_core.persistence.write_performance_metrics.call_args_list
        for call in calls:
            args, kwargs = call
            assert len(args) == 2
            assert args[0] == exec_id  # execution_id
            
            record = args[1]
            assert 'execution_id' in record
            assert 'agent_name' in record
            assert 'user_id' in record
            assert 'metric_type' in record
            assert 'metric_value' in record
            assert isinstance(record['metric_value'], float)  # Should be converted to float
    
    @pytest.mark.asyncio
    async def test_persist_metrics_record_structure(self, execution_core, sample_state):
        """Test the structure of persisted metric records."""
        exec_id = uuid4()
        
        # Mock persistence to capture calls
        execution_core.persistence = Mock()
        execution_core.persistence.write_performance_metrics = AsyncMock()
        
        metrics = {
            'execution_time_ms': 2500,
            'cpu_percentage': 35.7
        }
        
        await execution_core._persist_metrics(exec_id, metrics, "optimization_agent", sample_state)
        
        # Verify record structure for each metric
        calls = execution_core.persistence.write_performance_metrics.call_args_list
        assert len(calls) == 2
        
        for call in calls:
            args, kwargs = call
            record = args[1]
            
            # Verify required fields
            assert record['execution_id'] == exec_id
            assert record['agent_name'] == "optimization_agent"
            assert record['user_id'] == sample_state.user_id
            assert 'metric_type' in record
            assert 'metric_value' in record
            
            # Verify metric type is one of our test metrics
            assert record['metric_type'] in ['execution_time_ms', 'cpu_percentage']
    
    @pytest.mark.asyncio
    async def test_persist_metrics_error_resilience(self, execution_core, sample_state):
        """Test that persistence errors don't crash the system."""
        exec_id = uuid4()
        
        # Mock persistence that always fails
        execution_core.persistence = Mock()
        execution_core.persistence.write_performance_metrics = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        
        metrics = {
            'test_metric': 123,
            'another_metric': 456.78
        }
        
        # Should not raise exception despite persistence failures
        await execution_core._persist_metrics(exec_id, metrics, "test_agent", sample_state)
        
        # Verify attempts were made
        assert execution_core.persistence.write_performance_metrics.call_count == 2
    
    @pytest.mark.asyncio
    async def test_persist_metrics_with_none_persistence(self, execution_core, sample_state):
        """Test persistence handling when persistence is disabled."""
        exec_id = uuid4()
        
        # Persistence is None (disabled)
        execution_core.persistence = None
        
        metrics = {'test_metric': 100}
        
        # Should handle gracefully without crashing
        await execution_core._persist_metrics(exec_id, metrics, "test_agent", sample_state)
        
        # No exception should be raised
    
    def test_metrics_timestamp_consistency(self, execution_core):
        """Test that metric timestamps are consistent and reasonable."""
        start_time1 = time.time() - 1.0
        start_time2 = time.time() - 2.0
        
        metrics1 = execution_core._calculate_performance_metrics(start_time1)
        metrics2 = execution_core._calculate_performance_metrics(start_time2)
        
        # Verify timestamp ordering
        assert metrics1['start_timestamp'] > metrics2['start_timestamp']
        assert metrics1['end_timestamp'] >= metrics1['start_timestamp']
        assert metrics2['end_timestamp'] >= metrics2['start_timestamp']
        
        # Verify execution time differences
        assert metrics2['execution_time_ms'] > metrics1['execution_time_ms']
    
    def test_metrics_edge_cases(self, execution_core):
        """Test metric calculation edge cases."""
        # Test with very recent start time (near zero duration)
        very_recent_start = time.time() - 0.001  # 1ms ago
        
        metrics = execution_core._calculate_performance_metrics(very_recent_start)
        
        # Should still work and have reasonable values
        assert metrics['execution_time_ms'] >= 0
        assert metrics['execution_time_ms'] < 100  # Should be very small
        assert 'start_timestamp' in metrics
        assert 'end_timestamp' in metrics
        
        # Test with future start time (should handle gracefully)
        future_start = time.time() + 1.0  # 1s in future
        
        future_metrics = execution_core._calculate_performance_metrics(future_start)
        
        # Should handle gracefully (may have negative or zero execution time)
        assert 'execution_time_ms' in future_metrics
        assert 'start_timestamp' in future_metrics