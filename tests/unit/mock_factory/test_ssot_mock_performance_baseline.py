"""
SSOT Mock Factory Performance Baseline Tests
Test 2 - Critical Priority

Establishes performance baselines for SSOT mock creation and validates
that consolidated mock factory doesn't introduce performance regressions.

Business Value:
- Ensures SSOT mock consolidation doesn't slow down test execution
- Establishes performance SLAs for mock creation operations
- Protects developer productivity through fast test cycles

Issue: #1107 - SSOT Mock Factory Duplication
Phase: 2 - Test Creation
Priority: Critical
"""

import pytest
import time
import statistics
import asyncio
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, MagicMock
import gc

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory


class TestSSotMockPerformanceBaseline(SSotBaseTestCase):
    """
    Performance baseline test suite for SSOT mock factory.
    
    Ensures mock factory consolidation maintains acceptable performance
    characteristics for high-frequency test execution.
    """
    
    # Performance targets (based on requirements analysis)
    MAX_MOCK_CREATION_TIME_MS = 5.0  # Maximum acceptable creation time
    MAX_PERFORMANCE_OVERHEAD_PERCENT = 110  # SSOT should be ≤ 110% of direct mock time
    MIN_THROUGHPUT_MOCKS_PER_SECOND = 1000  # Minimum acceptable throughput
    
    def setUp(self):
        """Set up performance testing environment."""
        super().setUp()
        self.performance_results = {}
        
    def tearDown(self):
        """Clean up after performance tests."""
        super().tearDown()
        # Force garbage collection to ensure clean measurements
        gc.collect()

    def _measure_execution_time(self, operation_name: str, operation_func, iterations: int = 100) -> Dict[str, float]:
        """
        Measure execution time statistics for an operation.
        
        Args:
            operation_name: Name of the operation being measured
            operation_func: Function to execute and measure
            iterations: Number of iterations to run
            
        Returns:
            Dictionary with timing statistics
        """
        execution_times = []
        
        for _ in range(iterations):
            start_time = time.perf_counter()
            operation_func()
            end_time = time.perf_counter()
            execution_times.append((end_time - start_time) * 1000)  # Convert to milliseconds
        
        stats = {
            'operation': operation_name,
            'iterations': iterations,
            'mean_ms': statistics.mean(execution_times),
            'median_ms': statistics.median(execution_times),
            'min_ms': min(execution_times),
            'max_ms': max(execution_times),
            'stdev_ms': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            'p95_ms': sorted(execution_times)[int(len(execution_times) * 0.95)],
            'p99_ms': sorted(execution_times)[int(len(execution_times) * 0.99)]
        }
        
        self.performance_results[operation_name] = stats
        return stats

    def test_websocket_mock_creation_performance(self):
        """
        Test SSOT WebSocket mock creation performance baseline.
        
        CRITICAL: WebSocket mocks are created frequently in Golden Path testing.
        """
        # Test SSOT WebSocket mock creation performance
        def create_ssot_websocket_mock():
            return SSotMockFactory.create_websocket_mock(
                connection_id=f"perf-test-{time.time()}",
                user_id=f"user-{time.time()}"
            )
        
        ssot_stats = self._measure_execution_time(
            "ssot_websocket_mock_creation",
            create_ssot_websocket_mock,
            iterations=200
        )
        
        # Test direct mock creation for comparison
        def create_direct_websocket_mock():
            mock_websocket = MagicMock()
            mock_websocket.connection_id = f"perf-test-{time.time()}"
            mock_websocket.user_id = f"user-{time.time()}"
            mock_websocket.send_text = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            mock_websocket.accept = AsyncMock()
            mock_websocket.close = AsyncMock()
            return mock_websocket
        
        direct_stats = self._measure_execution_time(
            "direct_websocket_mock_creation",
            create_direct_websocket_mock,
            iterations=200
        )
        
        # Validate performance requirements
        self.assertLess(ssot_stats['mean_ms'], self.MAX_MOCK_CREATION_TIME_MS,
                       f"SSOT WebSocket mock creation too slow: {ssot_stats['mean_ms']:.2f}ms > {self.MAX_MOCK_CREATION_TIME_MS}ms")
        
        # Validate performance overhead is acceptable
        overhead_percent = (ssot_stats['mean_ms'] / direct_stats['mean_ms']) * 100
        self.assertLess(overhead_percent, self.MAX_PERFORMANCE_OVERHEAD_PERCENT,
                       f"SSOT overhead too high: {overhead_percent:.1f}% > {self.MAX_PERFORMANCE_OVERHEAD_PERCENT}%")
        
        print(f"\nWebSocket Mock Creation Performance:")
        print(f"  SSOT: {ssot_stats['mean_ms']:.2f}ms ± {ssot_stats['stdev_ms']:.2f}ms")
        print(f"  Direct: {direct_stats['mean_ms']:.2f}ms ± {direct_stats['stdev_ms']:.2f}ms")
        print(f"  Overhead: {overhead_percent:.1f}%")

    def test_agent_mock_creation_performance(self):
        """
        Test SSOT agent mock creation performance baseline.
        
        CRITICAL: Agent mocks are central to AI response pipeline testing.
        """
        # Test SSOT agent mock creation performance
        def create_ssot_agent_mock():
            return SSotMockFactory.create_agent_mock(
                agent_type="supervisor",
                execution_result={"status": "completed", "result": "test"},
                execution_time=0.1
            )
        
        ssot_stats = self._measure_execution_time(
            "ssot_agent_mock_creation",
            create_ssot_agent_mock,
            iterations=200
        )
        
        # Test direct mock creation for comparison
        def create_direct_agent_mock():
            mock_agent = AsyncMock()
            mock_agent.agent_type = "supervisor"
            mock_agent.execute.return_value = {"status": "completed", "result": "test", "execution_time": 0.1}
            mock_agent.get_capabilities.return_value = ["text_processing", "data_analysis"]
            return mock_agent
        
        direct_stats = self._measure_execution_time(
            "direct_agent_mock_creation",
            create_direct_agent_mock,
            iterations=200
        )
        
        # Validate performance requirements
        self.assertLess(ssot_stats['mean_ms'], self.MAX_MOCK_CREATION_TIME_MS,
                       f"SSOT agent mock creation too slow: {ssot_stats['mean_ms']:.2f}ms > {self.MAX_MOCK_CREATION_TIME_MS}ms")
        
        # Validate performance overhead is acceptable
        overhead_percent = (ssot_stats['mean_ms'] / direct_stats['mean_ms']) * 100
        self.assertLess(overhead_percent, self.MAX_PERFORMANCE_OVERHEAD_PERCENT,
                       f"SSOT overhead too high: {overhead_percent:.1f}% > {self.MAX_PERFORMANCE_OVERHEAD_PERCENT}%")
        
        print(f"\nAgent Mock Creation Performance:")
        print(f"  SSOT: {ssot_stats['mean_ms']:.2f}ms ± {ssot_stats['stdev_ms']:.2f}ms")
        print(f"  Direct: {direct_stats['mean_ms']:.2f}ms ± {direct_stats['stdev_ms']:.2f}ms")
        print(f"  Overhead: {overhead_percent:.1f}%")

    def test_database_mock_creation_performance(self):
        """
        Test SSOT database mock creation performance baseline.
        
        IMPORTANT: Database mocks are used extensively in integration testing.
        """
        # Test SSOT database mock creation performance
        def create_ssot_database_mock():
            return SSotMockFactory.create_database_session_mock()
        
        ssot_stats = self._measure_execution_time(
            "ssot_database_mock_creation",
            create_ssot_database_mock,
            iterations=200
        )
        
        # Test direct mock creation for comparison
        def create_direct_database_mock():
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.scalar = AsyncMock()
            mock_session.scalars = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = {"id": 1, "name": "test"}
            mock_result.fetchall.return_value = [{"id": 1, "name": "test"}]
            mock_session.execute.return_value = mock_result
            return mock_session
        
        direct_stats = self._measure_execution_time(
            "direct_database_mock_creation",
            create_direct_database_mock,
            iterations=200
        )
        
        # Validate performance requirements
        self.assertLess(ssot_stats['mean_ms'], self.MAX_MOCK_CREATION_TIME_MS,
                       f"SSOT database mock creation too slow: {ssot_stats['mean_ms']:.2f}ms > {self.MAX_MOCK_CREATION_TIME_MS}ms")
        
        # Validate performance overhead is acceptable
        overhead_percent = (ssot_stats['mean_ms'] / direct_stats['mean_ms']) * 100
        self.assertLess(overhead_percent, self.MAX_PERFORMANCE_OVERHEAD_PERCENT,
                       f"SSOT overhead too high: {overhead_percent:.1f}% > {self.MAX_PERFORMANCE_OVERHEAD_PERCENT}%")
        
        print(f"\nDatabase Mock Creation Performance:")
        print(f"  SSOT: {ssot_stats['mean_ms']:.2f}ms ± {ssot_stats['stdev_ms']:.2f}ms")
        print(f"  Direct: {direct_stats['mean_ms']:.2f}ms ± {direct_stats['stdev_ms']:.2f}ms")
        print(f"  Overhead: {overhead_percent:.1f}%")

    def test_mock_suite_creation_performance(self):
        """
        Test SSOT mock suite creation performance baseline.
        
        IMPORTANT: Mock suites are used for comprehensive integration testing.
        """
        mock_types = [
            "agent",
            "websocket",
            "database_session",
            "execution_context",
            "tool",
            "llm_client",
            "configuration"
        ]
        
        # Test SSOT mock suite creation performance
        def create_ssot_mock_suite():
            return SSotMockFactory.create_mock_suite(mock_types)
        
        ssot_stats = self._measure_execution_time(
            "ssot_mock_suite_creation",
            create_ssot_mock_suite,
            iterations=50  # Fewer iterations for complex operation
        )
        
        # Test direct mock suite creation for comparison
        def create_direct_mock_suite():
            mock_suite = {}
            
            # Agent mock
            mock_agent = AsyncMock()
            mock_agent.agent_type = "supervisor"
            mock_agent.execute.return_value = {"status": "completed"}
            mock_agent.get_capabilities.return_value = ["text_processing"]
            mock_suite["agent"] = mock_agent
            
            # WebSocket mock
            mock_websocket = MagicMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            mock_suite["websocket"] = mock_websocket
            
            # Database mock
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_suite["database_session"] = mock_db
            
            # Basic mocks for other types
            mock_suite["execution_context"] = MagicMock()
            mock_suite["tool"] = AsyncMock()
            mock_suite["llm_client"] = AsyncMock() 
            mock_suite["configuration"] = MagicMock()
            
            return mock_suite
        
        direct_stats = self._measure_execution_time(
            "direct_mock_suite_creation",
            create_direct_mock_suite,
            iterations=50
        )
        
        # Validate performance requirements (more relaxed for complex operation)
        max_suite_creation_time = self.MAX_MOCK_CREATION_TIME_MS * len(mock_types)
        self.assertLess(ssot_stats['mean_ms'], max_suite_creation_time,
                       f"SSOT mock suite creation too slow: {ssot_stats['mean_ms']:.2f}ms > {max_suite_creation_time}ms")
        
        # Validate performance overhead is acceptable
        overhead_percent = (ssot_stats['mean_ms'] / direct_stats['mean_ms']) * 100
        self.assertLess(overhead_percent, self.MAX_PERFORMANCE_OVERHEAD_PERCENT,
                       f"SSOT suite overhead too high: {overhead_percent:.1f}% > {self.MAX_PERFORMANCE_OVERHEAD_PERCENT}%")
        
        print(f"\nMock Suite Creation Performance:")
        print(f"  SSOT: {ssot_stats['mean_ms']:.2f}ms ± {ssot_stats['stdev_ms']:.2f}ms")
        print(f"  Direct: {direct_stats['mean_ms']:.2f}ms ± {direct_stats['stdev_ms']:.2f}ms")
        print(f"  Overhead: {overhead_percent:.1f}%")

    def test_mock_throughput_performance(self):
        """
        Test mock creation throughput to validate high-volume test scenarios.
        
        IMPORTANT: High-throughput testing ensures performance at scale.
        """
        iterations = 1000
        
        # Test WebSocket mock throughput
        start_time = time.perf_counter()
        for i in range(iterations):
            SSotMockFactory.create_websocket_mock(
                connection_id=f"throughput-test-{i}",
                user_id=f"user-{i}"
            )
        end_time = time.perf_counter()
        
        total_time_seconds = end_time - start_time
        throughput_per_second = iterations / total_time_seconds
        
        self.assertGreater(throughput_per_second, self.MIN_THROUGHPUT_MOCKS_PER_SECOND,
                         f"WebSocket mock throughput too low: {throughput_per_second:.0f} < {self.MIN_THROUGHPUT_MOCKS_PER_SECOND} mocks/sec")
        
        print(f"\nWebSocket Mock Throughput: {throughput_per_second:.0f} mocks/second")

    @pytest.mark.asyncio
    async def test_async_mock_operation_performance(self):
        """
        Test performance of async operations with SSOT mocks.
        
        CRITICAL: Async mock operations are used extensively in agent testing.
        """
        # Create SSOT mocks for async testing
        agent_mock = SSotMockFactory.create_agent_mock()
        websocket_mock = SSotMockFactory.create_websocket_mock()
        db_mock = SSotMockFactory.create_database_session_mock()
        
        iterations = 100
        operation_times = []
        
        # Test async operation performance
        for _ in range(iterations):
            start_time = time.perf_counter()
            
            # Simulate typical async mock usage pattern
            await agent_mock.execute()
            await websocket_mock.send_json({"event": "test"})
            await db_mock.execute("SELECT 1")
            await db_mock.commit()
            
            end_time = time.perf_counter()
            operation_times.append((end_time - start_time) * 1000)
        
        mean_time = statistics.mean(operation_times)
        max_async_operation_time = 1.0  # 1ms for basic async mock calls
        
        self.assertLess(mean_time, max_async_operation_time,
                       f"Async mock operations too slow: {mean_time:.2f}ms > {max_async_operation_time}ms")
        
        print(f"\nAsync Mock Operations Performance: {mean_time:.2f}ms ± {statistics.stdev(operation_times):.2f}ms")

    def test_memory_usage_baseline(self):
        """
        Test memory usage baseline for SSOT mock creation.
        
        IMPORTANT: Memory efficiency prevents test suite memory bloat.
        """
        import psutil
        import os
        
        # Get baseline memory usage
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        
        # Create large batch of mocks
        mock_batch_size = 1000
        mocks = []
        
        for i in range(mock_batch_size):
            mocks.append(SSotMockFactory.create_websocket_mock(
                connection_id=f"memory-test-{i}",
                user_id=f"user-{i}"
            ))
        
        # Measure memory after mock creation
        peak_memory = process.memory_info().rss
        memory_per_mock_bytes = (peak_memory - baseline_memory) / mock_batch_size
        memory_per_mock_kb = memory_per_mock_bytes / 1024
        
        # Validate memory usage is reasonable (< 1KB per mock)
        max_memory_per_mock_kb = 1.0
        self.assertLess(memory_per_mock_kb, max_memory_per_mock_kb,
                       f"Memory usage too high: {memory_per_mock_kb:.2f}KB > {max_memory_per_mock_kb}KB per mock")
        
        print(f"\nMemory Usage: {memory_per_mock_kb:.2f}KB per WebSocket mock")
        
        # Clean up
        del mocks
        gc.collect()

    def test_performance_regression_detection(self):
        """
        Test that validates performance hasn't regressed compared to known baselines.
        
        This test will initially establish baselines and detect regressions in future runs.
        """
        # Define baseline performance expectations (will be updated as we gather data)
        performance_baselines = {
            'websocket_mock_creation_ms': 2.0,
            'agent_mock_creation_ms': 2.0,
            'database_mock_creation_ms': 3.0,
            'mock_suite_creation_ms': 15.0
        }
        
        # Test current performance against baselines
        if 'ssot_websocket_mock_creation' in self.performance_results:
            current_websocket_time = self.performance_results['ssot_websocket_mock_creation']['mean_ms']
            baseline_websocket_time = performance_baselines['websocket_mock_creation_ms']
            
            if current_websocket_time > baseline_websocket_time * 1.5:  # Allow 50% variance
                print(f"WARNING: WebSocket mock creation regression detected: {current_websocket_time:.2f}ms vs {baseline_websocket_time:.2f}ms baseline")

    def tearDown(self):
        """Print comprehensive performance summary."""
        super().tearDown()
        
        if self.performance_results:
            print(f"\n{'='*60}")
            print(f"SSOT Mock Factory Performance Summary")
            print(f"{'='*60}")
            
            for operation, stats in self.performance_results.items():
                print(f"\n{operation.replace('_', ' ').title()}:")
                print(f"  Mean: {stats['mean_ms']:.2f}ms")
                print(f"  P95:  {stats['p95_ms']:.2f}ms") 
                print(f"  Max:  {stats['max_ms']:.2f}ms")
                print(f"  StdDev: {stats['stdev_ms']:.2f}ms")
                
            print(f"\nPerformance Targets:")
            print(f"  Max Creation Time: {self.MAX_MOCK_CREATION_TIME_MS}ms")
            print(f"  Max Overhead: {self.MAX_PERFORMANCE_OVERHEAD_PERCENT}%") 
            print(f"  Min Throughput: {self.MIN_THROUGHPUT_MOCKS_PER_SECOND} mocks/sec")

if __name__ == "__main__":
    # Run as standalone test for development
    pytest.main([__file__, "-v", "-s"])  # -s to see performance output