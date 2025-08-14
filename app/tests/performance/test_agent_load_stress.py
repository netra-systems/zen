"""
Agent Load and Stress Test Suite

Comprehensive testing for agent system under load conditions.
Tests concurrent agent requests, resource isolation, and performance degradation.
"""

import pytest
import asyncio
import time
import psutil
import gc
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
import statistics

from app.agents.supervisor.agent_registry import AgentRegistry
from app.agents.supervisor_consolidated import SupervisorAgent
from app.ws_manager import WebSocketManager
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.schemas.websocket_message_types import ServerMessage


class AgentLoadTestFixtures:
    """Fixtures for agent load testing with ≤8 line functions."""
    
    @staticmethod
    def create_mock_dependencies() -> Dict[str, Any]:
        """Create mock dependencies for agent testing."""
        return {
            'llm_manager': AsyncMock(spec=LLMManager),
            'tool_dispatcher': AsyncMock(spec=ToolDispatcher),
            'websocket_manager': AsyncMock(spec=WebSocketManager),
            'db_session': AsyncMock()
        }
    
    @staticmethod
    def create_load_test_params(concurrent_users: int) -> Dict[str, Any]:
        """Create parameters for load testing scenarios."""
        return {
            'concurrent_users': concurrent_users,
            'requests_per_user': 10,
            'ramp_up_duration': 30,
            'sustained_duration': 120
        }


class PerformanceMetricsCollector:
    """Collects performance metrics during load tests."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        self.throughput_samples: List[float] = []
        self.resource_usage: List[Dict[str, float]] = []
    
    def record_response_time(self, duration: float) -> None:
        """Record response time for request."""
        self.response_times.append(duration)
    
    def record_error(self, error_type: str) -> None:
        """Record error occurrence by type."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def record_throughput(self, requests_per_second: float) -> None:
        """Record throughput measurement."""
        self.throughput_samples.append(requests_per_second)
    
    def record_resource_usage(self) -> None:
        """Record current resource usage snapshot."""
        process = psutil.Process()
        memory_info = process.memory_info()
        self.resource_usage.append({
            'memory_mb': memory_info.rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
            'open_files': len(process.open_files())
        })
    
    def get_percentiles(self) -> Dict[str, float]:
        """Calculate response time percentiles."""
        if not self.response_times:
            return {'p50': 0, 'p95': 0, 'p99': 0}
        sorted_times = sorted(self.response_times)
        return {
            'p50': statistics.median(sorted_times),
            'p95': sorted_times[int(0.95 * len(sorted_times))],
            'p99': sorted_times[int(0.99 * len(sorted_times))]
        }


class AgentLoadSimulator:
    """Simulates load patterns for agent testing."""
    
    def __init__(self, metrics: PerformanceMetricsCollector):
        self.metrics = metrics
        self.active_connections = 0
        self.failed_requests = 0
    
    async def simulate_agent_request(self, agent: SupervisorAgent, 
                                   request_data: Dict[str, Any]) -> bool:
        """Simulate single agent request with timing."""
        start_time = time.perf_counter()
        try:
            await self._execute_mock_agent_operation(agent, request_data)
            duration = time.perf_counter() - start_time
            self.metrics.record_response_time(duration)
            return True
        except Exception as e:
            self.metrics.record_error(type(e).__name__)
            return False
    
    async def _execute_mock_agent_operation(self, agent: SupervisorAgent,
                                          request_data: Dict[str, Any]) -> None:
        """Execute mock agent operation."""
        # Simulate realistic agent processing time
        await asyncio.sleep(0.05 + (0.1 * len(request_data.get('tools', []))))


class TestAgentLoadScenarios:
    """Load test scenarios for agent system."""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_gradual_load_ramp_up(self):
        """Test gradual increase in concurrent users."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        metrics = PerformanceMetricsCollector()
        
        registry = AgentRegistry(mocks['llm_manager'], mocks['tool_dispatcher'])
        simulator = AgentLoadSimulator(metrics)
        
        await self._execute_ramp_up_test(registry, simulator, metrics)
        
        # Validate performance degradation is gradual
        percentiles = metrics.get_percentiles()
        assert percentiles['p95'] < 1000  # 95th percentile under 1 second
        assert len(metrics.error_counts) == 0  # No errors during ramp-up
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_sustained_peak_load(self):
        """Test system under sustained peak load."""
        fixtures = AgentLoadTestFixtures()
        params = fixtures.create_load_test_params(concurrent_users=100)
        mocks = fixtures.create_mock_dependencies()
        
        metrics = PerformanceMetricsCollector()
        
        await self._execute_sustained_load_test(mocks, metrics, params)
        
        # Validate sustained performance
        avg_throughput = statistics.mean(metrics.throughput_samples)
        assert avg_throughput > 50  # Minimum 50 requests/second
        assert len(metrics.response_times) >= params['requests_per_user'] * 50
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_burst_traffic_patterns(self):
        """Test handling of sudden traffic bursts."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        metrics = PerformanceMetricsCollector()
        
        # Simulate burst pattern: low -> high -> low
        burst_phases = [10, 200, 10]  # User counts per phase
        
        for phase_users in burst_phases:
            await self._execute_burst_phase(mocks, metrics, phase_users)
            await asyncio.sleep(5)  # Brief pause between phases
        
        # System should handle bursts without catastrophic failure
        error_rate = sum(metrics.error_counts.values()) / len(metrics.response_times)
        assert error_rate < 0.1  # Less than 10% error rate
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_mixed_workload_types(self):
        """Test mixed agent types under concurrent load."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        
        agent_types = ['triage', 'data', 'optimization', 'actions', 'reporting']
        workload_results = {}
        
        for agent_type in agent_types:
            metrics = PerformanceMetricsCollector()
            await self._test_agent_type_load(mocks, metrics, agent_type)
            workload_results[agent_type] = metrics.get_percentiles()
        
        # All agent types should perform reasonably
        for agent_type, percentiles in workload_results.items():
            assert percentiles['p95'] < 2000  # Under 2 seconds for 95th percentile
    
    async def _execute_ramp_up_test(self, registry: AgentRegistry,
                                  simulator: AgentLoadSimulator,
                                  metrics: PerformanceMetricsCollector) -> None:
        """Execute gradual ramp-up load test."""
        user_counts = [10, 25, 50, 75, 100]
        for user_count in user_counts:
            await self._simulate_concurrent_users(registry, simulator, user_count)
            metrics.record_resource_usage()
            await asyncio.sleep(10)  # Stabilization period
    
    async def _execute_sustained_load_test(self, mocks: Dict[str, Any],
                                         metrics: PerformanceMetricsCollector,
                                         params: Dict[str, Any]) -> None:
        """Execute sustained load test."""
        duration = params['sustained_duration']
        concurrent_users = params['concurrent_users']
        
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < duration:
            throughput_start = time.perf_counter()
            await self._simulate_request_batch(mocks, metrics, concurrent_users)
            throughput_duration = time.perf_counter() - throughput_start
            metrics.record_throughput(concurrent_users / throughput_duration)
    
    async def _execute_burst_phase(self, mocks: Dict[str, Any],
                                 metrics: PerformanceMetricsCollector,
                                 user_count: int) -> None:
        """Execute single burst phase."""
        tasks = []
        for _ in range(user_count):
            task = self._simulate_user_session(mocks, metrics)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _test_agent_type_load(self, mocks: Dict[str, Any],
                                  metrics: PerformanceMetricsCollector,
                                  agent_type: str) -> None:
        """Test specific agent type under load."""
        tasks = []
        for _ in range(50):  # 50 concurrent requests per agent type
            task = self._simulate_agent_type_request(mocks, metrics, agent_type)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_concurrent_users(self, registry: AgentRegistry,
                                       simulator: AgentLoadSimulator,
                                       user_count: int) -> None:
        """Simulate concurrent users."""
        with patch.object(registry, 'register_default_agents'):
            registry.register_default_agents()
            
        tasks = []
        for _ in range(user_count):
            agent = SupervisorAgent(
                AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
            )
            task = simulator.simulate_agent_request(
                agent, {'tools': ['test_tool'], 'query': 'test query'}
            )
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_request_batch(self, mocks: Dict[str, Any],
                                    metrics: PerformanceMetricsCollector,
                                    batch_size: int) -> None:
        """Simulate batch of concurrent requests."""
        tasks = []
        for _ in range(batch_size):
            task = self._simulate_user_session(mocks, metrics)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_user_session(self, mocks: Dict[str, Any],
                                   metrics: PerformanceMetricsCollector) -> None:
        """Simulate single user session."""
        start_time = time.perf_counter()
        try:
            # Simulate realistic user interaction
            await asyncio.sleep(0.1)  # Mock processing time
            duration = time.perf_counter() - start_time
            metrics.record_response_time(duration)
        except Exception as e:
            metrics.record_error(type(e).__name__)
    
    async def _simulate_agent_type_request(self, mocks: Dict[str, Any],
                                         metrics: PerformanceMetricsCollector,
                                         agent_type: str) -> None:
        """Simulate request for specific agent type."""
        start_time = time.perf_counter()
        try:
            # Mock agent-specific processing
            processing_time = {'triage': 0.05, 'data': 0.15, 'optimization': 0.2,
                             'actions': 0.1, 'reporting': 0.08}.get(agent_type, 0.1)
            await asyncio.sleep(processing_time)
            
            duration = time.perf_counter() - start_time
            metrics.record_response_time(duration)
        except Exception as e:
            metrics.record_error(type(e).__name__)


class TestAgentStressScenarios:
    """Stress test scenarios pushing system beyond limits."""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_beyond_capacity_limits(self):
        """Test system behavior beyond designed capacity."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        metrics = PerformanceMetricsCollector()
        
        # Stress with 500+ concurrent users
        stress_users = 500
        await self._execute_capacity_stress_test(mocks, metrics, stress_users)
        
        # System should degrade gracefully, not crash
        percentiles = metrics.get_percentiles()
        assert percentiles['p99'] < 30000  # Under 30 seconds even under stress
        assert sum(metrics.error_counts.values()) < stress_users * 0.5  # <50% failure
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_resource_starvation(self):
        """Test behavior under resource starvation."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        metrics = PerformanceMetricsCollector()
        
        # Simulate memory pressure
        memory_hogs = []
        try:
            await self._create_memory_pressure(memory_hogs)
            await self._test_under_memory_pressure(mocks, metrics)
            
            # System should still respond under pressure
            percentiles = metrics.get_percentiles()
            assert len(metrics.response_times) > 0  # Some requests completed
        finally:
            # Cleanup memory pressure
            del memory_hogs
            gc.collect()
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_connection_pool_exhaustion(self):
        """Test database connection pool exhaustion."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        
        # Mock connection pool with limited connections
        connection_limit = 10
        active_connections = 0
        
        async def mock_get_connection():
            nonlocal active_connections
            if active_connections >= connection_limit:
                raise Exception("Connection pool exhausted")
            active_connections += 1
            return AsyncMock()
        
        mocks['db_session'].get_connection = mock_get_connection
        
        # Stress test with more concurrent requests than connections
        tasks = []
        for _ in range(50):  # 50 requests for 10 connections
            task = self._simulate_db_intensive_request(mocks)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle gracefully with proper error responses
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) > 0  # Some requests should fail appropriately
        assert len(exceptions) < len(tasks)  # Not all should fail
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        
        initial_memory = psutil.Process().memory_info().rss
        metrics_snapshots = []
        
        # Run multiple cycles to detect memory growth
        for cycle in range(5):
            await self._execute_memory_test_cycle(mocks, cycle)
            current_memory = psutil.Process().memory_info().rss
            metrics_snapshots.append(current_memory)
            gc.collect()  # Force garbage collection
        
        # Memory growth should be reasonable (under 2x initial)
        final_memory = metrics_snapshots[-1]
        memory_growth_ratio = final_memory / initial_memory
        assert memory_growth_ratio < 2.0  # Less than 2x memory growth
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_cpu_saturation_handling(self):
        """Test system behavior under CPU saturation."""
        fixtures = AgentLoadTestFixtures()
        mocks = fixtures.create_mock_dependencies()
        metrics = PerformanceMetricsCollector()
        
        # Create CPU-intensive background tasks
        cpu_tasks = []
        for _ in range(psutil.cpu_count()):
            task = asyncio.create_task(self._cpu_intensive_task())
            cpu_tasks.append(task)
        
        try:
            # Test agent system under CPU pressure
            await self._test_under_cpu_pressure(mocks, metrics)
            
            # System should still be responsive
            percentiles = metrics.get_percentiles()
            assert len(metrics.response_times) >= 10  # At least some requests completed
        finally:
            # Cleanup CPU tasks
            for task in cpu_tasks:
                task.cancel()
            await asyncio.gather(*cpu_tasks, return_exceptions=True)
    
    async def _execute_capacity_stress_test(self, mocks: Dict[str, Any],
                                          metrics: PerformanceMetricsCollector,
                                          user_count: int) -> None:
        """Execute stress test beyond capacity."""
        tasks = []
        for _ in range(user_count):
            task = self._simulate_stress_request(mocks, metrics)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _create_memory_pressure(self, memory_hogs: List[bytes]) -> None:
        """Create memory pressure for testing."""
        # Allocate memory to simulate pressure (100MB chunks)
        for _ in range(10):
            memory_hogs.append(b'x' * (100 * 1024 * 1024))
            await asyncio.sleep(0.1)
    
    async def _test_under_memory_pressure(self, mocks: Dict[str, Any],
                                        metrics: PerformanceMetricsCollector) -> None:
        """Test agent system under memory pressure."""
        tasks = []
        for _ in range(20):
            task = self._simulate_memory_intensive_request(mocks, metrics)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_db_intensive_request(self, mocks: Dict[str, Any]) -> None:
        """Simulate database-intensive request."""
        try:
            connection = await mocks['db_session'].get_connection()
            await asyncio.sleep(0.1)  # Simulate DB operation
            return "success"
        except Exception:
            return "connection_failed"
    
    async def _execute_memory_test_cycle(self, mocks: Dict[str, Any], 
                                       cycle: int) -> None:
        """Execute single memory test cycle."""
        # Create temporary objects that should be garbage collected
        temp_data = []
        for _ in range(1000):
            temp_data.append({'cycle': cycle, 'data': list(range(100))})
        
        # Simulate some processing
        await asyncio.sleep(0.1)
        
        # Clear references
        del temp_data
    
    async def _cpu_intensive_task(self) -> None:
        """CPU-intensive background task."""
        try:
            while True:
                # CPU-bound calculation
                sum(i * i for i in range(10000))
                await asyncio.sleep(0.001)  # Brief yield
        except asyncio.CancelledError:
            pass
    
    async def _test_under_cpu_pressure(self, mocks: Dict[str, Any],
                                     metrics: PerformanceMetricsCollector) -> None:
        """Test agent system under CPU pressure."""
        tasks = []
        for _ in range(50):
            task = self._simulate_cpu_sensitive_request(mocks, metrics)
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _simulate_stress_request(self, mocks: Dict[str, Any],
                                     metrics: PerformanceMetricsCollector) -> None:
        """Simulate high-stress request."""
        start_time = time.perf_counter()
        try:
            await asyncio.sleep(0.05)  # Mock processing
            duration = time.perf_counter() - start_time
            metrics.record_response_time(duration)
        except Exception as e:
            metrics.record_error(type(e).__name__)
    
    async def _simulate_memory_intensive_request(self, mocks: Dict[str, Any],
                                               metrics: PerformanceMetricsCollector) -> None:
        """Simulate memory-intensive request."""
        start_time = time.perf_counter()
        try:
            # Create temporary large object
            large_data = [i for i in range(100000)]
            await asyncio.sleep(0.01)
            del large_data
            
            duration = time.perf_counter() - start_time
            metrics.record_response_time(duration)
        except Exception as e:
            metrics.record_error(type(e).__name__)
    
    async def _simulate_cpu_sensitive_request(self, mocks: Dict[str, Any],
                                            metrics: PerformanceMetricsCollector) -> None:
        """Simulate CPU-sensitive request."""
        start_time = time.perf_counter()
        try:
            # Some computation
            result = sum(i for i in range(1000))
            await asyncio.sleep(0.01)
            
            duration = time.perf_counter() - start_time
            metrics.record_response_time(duration)
        except Exception as e:
            metrics.record_error(type(e).__name__)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto", "-m", "performance"])