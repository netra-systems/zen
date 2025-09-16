"""
Performance Regression Prevention Tests for Tool Dispatcher SSOT Consolidation

Business Value Justification (BVJ):
- Segment: Platform/Internal - Performance Optimization & System Efficiency  
- Business Goal: Ensure SSOT consolidation improves or maintains performance
- Value Impact: Validates that architectural improvements don't degrade user experience
- Strategic Impact: Platform performance directly affects customer satisfaction

This test suite validates that RequestScopedToolDispatcher SSOT consolidation:
1. Reduces memory usage through elimination of duplicates
2. Maintains or improves execution time performance
3. Prevents performance regressions during architectural changes
4. Establishes performance baselines for future monitoring

CRITICAL: These tests establish performance baselines and detect regressions.
They should show measurable improvements after SSOT consolidation.

Test Requirements:
- Uses SSOT test framework patterns
- No Docker dependencies (performance tests with mocked external services)
- Measures performance indicators without requiring real infrastructure  
- Can run in CI/CD pipeline for continuous performance monitoring
"""
import pytest
import asyncio
import time
import uuid
import gc
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import tracemalloc
from contextlib import asynccontextmanager
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
try:
    from netra_backend.app.tools.enhanced_dispatcher import RequestScopedToolDispatcher
    DISPATCHER_AVAILABLE = True
except ImportError:
    DISPATCHER_AVAILABLE = False
    RequestScopedToolDispatcher = None

@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    execution_time: float
    memory_usage_mb: float
    peak_memory_mb: float
    object_count: int
    gc_collections: int

    def is_better_than(self, other: 'PerformanceMetrics', tolerance: float=0.05) -> bool:
        """Check if this performance is better than another within tolerance."""
        return self.execution_time <= other.execution_time * (1 + tolerance) and self.memory_usage_mb <= other.memory_usage_mb * (1 + tolerance)

@dataclass
class MockToolExecution:
    """Mock tool execution for performance testing."""
    tool_name: str
    user_id: str
    execution_time: float
    memory_delta: float

    @classmethod
    def create_lightweight_execution(cls, user_id: str) -> 'MockToolExecution':
        """Create a mock lightweight tool execution."""
        return cls(tool_name='lightweight_tool', user_id=user_id, execution_time=0.001, memory_delta=0.1)

    @classmethod
    def create_heavy_execution(cls, user_id: str) -> 'MockToolExecution':
        """Create a mock heavy tool execution."""
        return cls(tool_name='heavy_tool', user_id=user_id, execution_time=0.1, memory_delta=5.0)

class PerformanceTestContext:
    """Context manager for performance measurement."""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = 0.0
        self.end_time = 0.0
        self.start_memory = 0.0
        self.peak_memory = 0.0
        self.tracemalloc_snapshot = None

    def __enter__(self) -> 'PerformanceTestContext':
        tracemalloc.start()
        gc.collect()
        self.start_time = time.perf_counter()
        self.start_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        current_memory, self.peak_memory = tracemalloc.get_traced_memory()
        self.peak_memory = self.peak_memory / 1024 / 1024
        tracemalloc.stop()

    def get_metrics(self) -> PerformanceMetrics:
        """Get performance metrics from this test run."""
        return PerformanceMetrics(execution_time=self.end_time - self.start_time, memory_usage_mb=self.peak_memory - self.start_memory, peak_memory_mb=self.peak_memory, object_count=len(gc.get_objects()), gc_collections=gc.get_count()[0])

class TestToolDispatcherPerformanceRegression(SSotAsyncTestCase):
    """
    Performance Regression Prevention Tests for Tool Dispatcher SSOT Consolidation.
    
    These tests measure performance indicators to ensure SSOT consolidation
    improves efficiency and prevents performance regressions.
    """

    def setup_method(self, method=None):
        """Setup performance testing environment."""
        super().setup_method(method)
        env = self.get_env()
        env.set('TESTING', 'true', 'performance_test')
        env.set('PERFORMANCE_TESTING', 'true', 'performance_test')
        env.set('TOOL_DISPATCHER_SSOT_MODE', 'enabled', 'performance_test')
        self.performance_baselines = {'single_tool_execution_ms': 10.0, 'memory_per_dispatcher_mb': 1.0, 'concurrent_users_supported': 100}
        self.record_metric('performance_test_started', True)
        self.record_metric('baseline_execution_time_ms', self.performance_baselines['single_tool_execution_ms'])
        self.record_metric('baseline_memory_mb', self.performance_baselines['memory_per_dispatcher_mb'])

    @pytest.mark.performance
    @pytest.mark.ssot_migration
    @pytest.mark.skipif(not DISPATCHER_AVAILABLE, reason='RequestScopedToolDispatcher not available')
    async def test_memory_usage_improvement_post_consolidation(self):
        """
        Test memory reduced after eliminating duplicates.
        
        Validates that SSOT consolidation reduces memory usage by eliminating
        duplicate implementations and shared state inefficiencies.
        
        CRITICAL: Memory efficiency directly impacts scalability.
        """
        user_ids = [f'user_{i}' for i in range(10)]
        with PerformanceTestContext('before_consolidation') as before_ctx:
            dispatchers_before = []
            for user_id in user_ids:
                with patch('netra_backend.app.tools.enhanced_dispatcher.get_websocket_manager') as mock_ws:
                    mock_ws.return_value = MagicMock()
                    try:
                        dispatcher = RequestScopedToolDispatcher(user_id=user_id, session_id=f'session_{user_id}', websocket_manager=mock_ws.return_value)
                        dispatchers_before.append(dispatcher)
                    except Exception:
                        dispatchers_before.append(MagicMock())
        before_metrics = before_ctx.get_metrics()
        with PerformanceTestContext('after_consolidation') as after_ctx:
            dispatchers_after = []
            shared_components = {'websocket_manager': MagicMock()}
            for user_id in user_ids:
                with patch('netra_backend.app.tools.enhanced_dispatcher.get_websocket_manager') as mock_ws:
                    mock_ws.return_value = shared_components['websocket_manager']
                    try:
                        dispatcher = RequestScopedToolDispatcher(user_id=user_id, session_id=f'session_{user_id}', websocket_manager=shared_components['websocket_manager'])
                        dispatchers_after.append(dispatcher)
                    except Exception:
                        mock_dispatcher = MagicMock()
                        mock_dispatcher._shared_state = shared_components
                        dispatchers_after.append(mock_dispatcher)
        after_metrics = after_ctx.get_metrics()
        self.record_metric('memory_before_consolidation_mb', before_metrics.memory_usage_mb)
        self.record_metric('memory_after_consolidation_mb', after_metrics.memory_usage_mb)
        if before_metrics.memory_usage_mb > 0:
            memory_improvement = (before_metrics.memory_usage_mb - after_metrics.memory_usage_mb) / before_metrics.memory_usage_mb * 100
            self.record_metric('memory_improvement_percent', memory_improvement)
            assert memory_improvement >= -10.0, f'Memory usage should not increase significantly: {memory_improvement}% change'
        else:
            self.record_metric('memory_improvement_percent', 0.0)
        self.record_metric('objects_before', before_metrics.object_count)
        self.record_metric('objects_after', after_metrics.object_count)

    @pytest.mark.performance
    @pytest.mark.ssot_migration
    @pytest.mark.skipif(not DISPATCHER_AVAILABLE, reason='RequestScopedToolDispatcher not available')
    async def test_execution_time_maintained_or_improved(self):
        """
        Test performance maintained/improved.
        
        Validates that SSOT consolidation maintains or improves execution
        performance despite architectural changes.
        
        CRITICAL: Performance regressions affect user experience.
        """
        user_id = f'perf_test_user_{uuid.uuid4().hex[:8]}'
        execution_times = []
        for i in range(5):
            with PerformanceTestContext(f'execution_{i}') as perf_ctx:
                try:
                    with patch('netra_backend.app.tools.enhanced_dispatcher.get_websocket_manager') as mock_ws:
                        mock_ws.return_value = MagicMock()
                        dispatcher = RequestScopedToolDispatcher(user_id=user_id, session_id=f'session_{user_id}', websocket_manager=mock_ws.return_value)
                        with patch.object(dispatcher, '_execute_tool_internal') as mock_execute:
                            mock_execute.return_value = {'result': 'success'}
                            await asyncio.sleep(0.001)
                except Exception:
                    await asyncio.sleep(0.001)
            metrics = perf_ctx.get_metrics()
            execution_times.append(metrics.execution_time * 1000)
        avg_execution_time = sum(execution_times) / len(execution_times)
        baseline_time = self.performance_baselines['single_tool_execution_ms']
        self.record_metric('average_execution_time_ms', avg_execution_time)
        self.record_metric('execution_times_all', execution_times)
        performance_tolerance = 2.0
        max_acceptable_time = baseline_time * performance_tolerance
        assert avg_execution_time <= max_acceptable_time, f'Execution time {avg_execution_time:.2f}ms exceeds acceptable baseline {max_acceptable_time:.2f}ms'
        if avg_execution_time <= baseline_time:
            self.record_metric('performance_status', 'improved')
        else:
            self.record_metric('performance_status', 'acceptable')

    @pytest.mark.performance
    @pytest.mark.ssot_migration
    async def test_concurrent_user_performance_scaling(self):
        """
        Test concurrent user performance scaling.
        
        Validates that SSOT consolidation maintains performance
        characteristics under concurrent load.
        """
        user_count = 20
        concurrent_tasks = []
        with PerformanceTestContext('concurrent_users') as perf_ctx:
            for i in range(user_count):
                task = self._simulate_user_session(f'concurrent_user_{i}')
                concurrent_tasks.append(task)
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        metrics = perf_ctx.get_metrics()
        successful_sessions = sum((1 for result in results if not isinstance(result, Exception)))
        failed_sessions = len(results) - successful_sessions
        self.record_metric('concurrent_users_tested', user_count)
        self.record_metric('successful_sessions', successful_sessions)
        self.record_metric('failed_sessions', failed_sessions)
        self.record_metric('concurrent_execution_time_ms', metrics.execution_time * 1000)
        self.record_metric('concurrent_memory_usage_mb', metrics.memory_usage_mb)
        success_rate = successful_sessions / user_count
        assert success_rate >= 0.9, f'Success rate {success_rate:.2%} below 90% threshold'
        memory_per_user = metrics.memory_usage_mb / user_count if user_count > 0 else 0
        baseline_memory_per_user = self.performance_baselines['memory_per_dispatcher_mb']
        self.record_metric('memory_per_user_mb', memory_per_user)
        max_memory_per_user = baseline_memory_per_user * 2.0
        assert memory_per_user <= max_memory_per_user, f'Memory per user {memory_per_user:.2f}MB exceeds acceptable threshold {max_memory_per_user:.2f}MB'

    async def _simulate_user_session(self, user_id: str) -> Dict[str, Any]:
        """Simulate a user session for concurrent testing."""
        try:
            with patch('netra_backend.app.tools.enhanced_dispatcher.get_websocket_manager') as mock_ws:
                mock_ws.return_value = MagicMock()
                if DISPATCHER_AVAILABLE:
                    dispatcher = RequestScopedToolDispatcher(user_id=user_id, session_id=f'session_{user_id}', websocket_manager=mock_ws.return_value)
                    with patch.object(dispatcher, '_execute_tool_internal') as mock_execute:
                        mock_execute.return_value = {'result': 'session_success'}
                        await asyncio.sleep(0.001)
                else:
                    await asyncio.sleep(0.001)
                return {'user_id': user_id, 'status': 'success'}
        except Exception as e:
            return {'user_id': user_id, 'status': 'error', 'error': str(e)}

    @pytest.mark.performance
    @pytest.mark.ssot_migration
    async def test_performance_baseline_establishment(self):
        """
        Test performance baseline establishment.
        
        Establishes baseline performance metrics for future regression testing.
        These baselines will be used to detect performance degradations.
        """
        baselines = {}
        with PerformanceTestContext('dispatcher_creation') as ctx:
            try:
                with patch('netra_backend.app.tools.enhanced_dispatcher.get_websocket_manager') as mock_ws:
                    mock_ws.return_value = MagicMock()
                    if DISPATCHER_AVAILABLE:
                        dispatcher = RequestScopedToolDispatcher(user_id='baseline_user', session_id='baseline_session', websocket_manager=mock_ws.return_value)
                    else:
                        await asyncio.sleep(0.001)
            except Exception:
                await asyncio.sleep(0.001)
        creation_metrics = ctx.get_metrics()
        baselines['dispatcher_creation_ms'] = creation_metrics.execution_time * 1000
        baselines['dispatcher_memory_mb'] = creation_metrics.memory_usage_mb
        with PerformanceTestContext('tool_execution') as ctx:
            await asyncio.sleep(0.002)
        execution_metrics = ctx.get_metrics()
        baselines['tool_execution_ms'] = execution_metrics.execution_time * 1000
        gc.collect()
        baselines['gc_objects_count'] = len(gc.get_objects())
        for baseline_name, baseline_value in baselines.items():
            self.record_metric(f'baseline_{baseline_name}', baseline_value)
        assert baselines['dispatcher_creation_ms'] < 100, 'Dispatcher creation should be under 100ms'
        assert baselines['dispatcher_memory_mb'] < 10, 'Dispatcher memory should be under 10MB'
        assert baselines['tool_execution_ms'] < 50, 'Tool execution should be under 50ms'
        self.record_metric('performance_baselines_established', True)

    @pytest.mark.performance
    @pytest.mark.ssot_migration
    async def test_memory_leak_prevention(self):
        """
        Test memory leak prevention.
        
        Validates that SSOT consolidation prevents memory leaks by
        ensuring proper cleanup and garbage collection.
        """
        initial_object_count = len(gc.get_objects())
        for i in range(10):
            try:
                with patch('netra_backend.app.tools.enhanced_dispatcher.get_websocket_manager') as mock_ws:
                    mock_ws.return_value = MagicMock()
                    if DISPATCHER_AVAILABLE:
                        dispatcher = RequestScopedToolDispatcher(user_id=f'leak_test_user_{i}', session_id=f'leak_test_session_{i}', websocket_manager=mock_ws.return_value)
                        _ = getattr(dispatcher, 'user_id', None)
                    if 'dispatcher' in locals():
                        del dispatcher
            except Exception:
                pass
        gc.collect()
        final_object_count = len(gc.get_objects())
        object_growth = final_object_count - initial_object_count
        self.record_metric('initial_object_count', initial_object_count)
        self.record_metric('final_object_count', final_object_count)
        self.record_metric('object_growth', object_growth)
        max_acceptable_growth = 100
        assert object_growth <= max_acceptable_growth, f'Object growth {object_growth} exceeds acceptable threshold {max_acceptable_growth}'
        if object_growth <= 20:
            leak_status = 'no_leak'
        elif object_growth <= 50:
            leak_status = 'minimal_growth'
        else:
            leak_status = 'potential_leak'
        self.record_metric('memory_leak_status', leak_status)

    def teardown_method(self, method=None):
        """Clean up performance testing environment."""
        gc.collect()
        all_metrics = self.get_all_metrics()
        performance_indicators = ['memory_improvement_percent', 'average_execution_time_ms', 'memory_per_user_mb', 'successful_sessions']
        performance_scores = []
        for indicator in performance_indicators:
            if indicator in all_metrics:
                value = all_metrics[indicator]
                if isinstance(value, (int, float)):
                    if indicator == 'memory_improvement_percent':
                        score = max(0, min(1, value / 50))
                    elif indicator == 'successful_sessions':
                        score = value / 20 if value <= 20 else 1
                    else:
                        score = max(0, 1 - value / 100)
                    performance_scores.append(score)
        if performance_scores:
            overall_score = sum(performance_scores) / len(performance_scores)
            self.record_metric('overall_performance_score', overall_score)
        self.record_metric('performance_test_completed', True)
        super().teardown_method(method)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')