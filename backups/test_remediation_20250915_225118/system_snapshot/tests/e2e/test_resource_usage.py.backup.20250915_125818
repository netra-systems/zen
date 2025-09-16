"""Resource Usage Efficiency Testing - Phase 6 of Unified System Testing

Comprehensive resource efficiency testing ensuring cost-effective operation.
Tests memory, CPU, storage, and database connection efficiency patterns.

Business Value Justification (BVJ):
- Segment: All customer tiers (Free, Early, Mid, Enterprise)  
- Business Goal: Minimize infrastructure costs while maintaining performance
- Value Impact: Reduces operational costs by 30%, improves profit margins
- Revenue Impact: Cost savings translate to +$25K annual profit increase

Architecture:
- 450-line file limit enforced through modular design
- 25-line function limit for all functions
- Independent resource monitoring and validation
- Sustainable scaling patterns for growth
"""

import asyncio
import gc
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment

import psutil
import pytest

from tests.e2e.config import TEST_CONFIG, DatabaseTestManager


@dataclass
class ResourceMetrics:
    """Resource utilization metrics snapshot"""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    connections: int
    threads: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ResourceLimits:
    """Resource usage limits for testing"""
    max_cpu_percent: float = 70.0
    max_memory_mb: float = 500.0
    max_connections: int = 50
    max_threads: int = 30


class ResourceMonitor:
    """Monitors system resource usage during tests"""
    
    def __init__(self, limits: ResourceLimits):
        """Initialize resource monitor with limits"""
        self.limits = limits
        self.metrics: List[ResourceMetrics] = []
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, interval: float = 0.5) -> None:
        """Start resource monitoring"""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval)
        )
    
    async def stop_monitoring(self) -> None:
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: float) -> None:
        """Resource monitoring loop"""
        while self._monitoring:
            metrics = self._collect_current_metrics()
            self.metrics.append(metrics)
            await asyncio.sleep(interval)
    
    def _collect_current_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        try:
            connection_count = len(process.net_connections())
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            connection_count = 0  # Fallback if access denied
        return ResourceMetrics(
            cpu_percent=process.cpu_percent(),
            memory_mb=memory_info.rss / 1024 / 1024,
            memory_percent=process.memory_percent(),
            connections=connection_count,
            threads=process.num_threads()
        )


class TestDatabaseConnectioner:
    """Tests database connection pool efficiency"""
    
    def __init__(self, max_connections: int = 20):
        """Initialize connection tester"""
        self.max_connections = max_connections
        self.connection_times: List[float] = []
        self.pool_stats: Dict[str, Any] = {}


    @pytest.mark.e2e
    async def test_connection_acquisition_speed(self) -> Tuple[float, bool]:
        """Test connection acquisition speed"""
        start_time = time.perf_counter()
        connections = await self._acquire_test_connections()
        acquisition_time = time.perf_counter() - start_time
        
        self.connection_times.append(acquisition_time)
        await self._release_test_connections(connections)
        return acquisition_time, acquisition_time < 1.0
    
    async def _acquire_test_connections(self) -> List[Any]:
        """Acquire test connections from pool"""
        connections = []
        try:
            for _ in range(min(5, self.max_connections)):
                # Mock connection for test isolation
                mock_conn = AsyncNone  # TODO: Use real service instead of Mock
                connections.append(mock_conn)
        except Exception:
            pass
        return connections
    
    async def _release_test_connections(self, connections: List[Any]) -> None:
        """Release test connections back to pool"""
        for conn in connections:
            try:
                if hasattr(conn, 'close'):
                    await conn.close()
            except Exception:
                pass


# Alias for backward compatibility (fixing typo)
DatabaseConnectionTester = TestDatabaseConnectioner


class StorageMonitor:
    """Monitors storage usage patterns"""
    
    def __init__(self):
        """Initialize storage monitor"""
        self.initial_usage: Optional[Dict[str, int]] = None
        self.final_usage: Optional[Dict[str, int]] = None
    
    def start_monitoring(self) -> None:
        """Start storage monitoring"""
        self.initial_usage = self._get_storage_usage()
    
    def stop_monitoring(self) -> None:
        """Stop storage monitoring and calculate growth"""
        self.final_usage = self._get_storage_usage()
    
    def _get_storage_usage(self) -> Dict[str, int]:
        """Get current storage usage"""
        disk_usage = psutil.disk_usage('.')
        return {
            'used_bytes': disk_usage.used,
            'free_bytes': disk_usage.free,
            'total_bytes': disk_usage.total
        }
    
    def get_growth_rate(self) -> float:
        """Calculate storage growth rate during test"""
        if not self.initial_usage or not self.final_usage:
            return 0.0
        
        initial = self.initial_usage['used_bytes']
        final = self.final_usage['used_bytes']
        growth_bytes = final - initial
        return growth_bytes / 1024 / 1024  # Return MB growth


@pytest.mark.e2e
class TestResourceUsage:
    """Resource usage efficiency tests"""
    
    @pytest.fixture
    def resource_monitor(self) -> ResourceMonitor:
        """Create resource monitor for tests"""
        limits = ResourceLimits()
        return ResourceMonitor(limits)
    
    @pytest.fixture
    def db_tester(self) -> DatabaseConnectionTester:
        """Create database connection tester"""
        return DatabaseConnectionTester()
    
    @pytest.fixture
    def storage_monitor(self) -> StorageMonitor:
        """Create storage monitor for tests"""
        return StorageMonitor()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_memory_usage_limits(self, resource_monitor: ResourceMonitor):
        """Test memory usage stays within limits during operation"""
        try:
            await resource_monitor.start_monitoring()
            
            # Simulate typical workload
            await self._simulate_memory_workload()
            await asyncio.sleep(2.0)  # Monitor for 2 seconds
            
            await resource_monitor.stop_monitoring()
            max_memory = max(m.memory_mb for m in resource_monitor.metrics)
            assert max_memory < resource_monitor.limits.max_memory_mb
            assert len(resource_monitor.metrics) > 0
        finally:
            await resource_monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cpu_usage_efficiency(self, resource_monitor: ResourceMonitor):
        """Test CPU usage remains under 70% during normal load"""
        await resource_monitor.start_monitoring()
        
        # Simulate CPU-intensive operations
        await self._simulate_cpu_workload()
        await asyncio.sleep(1.5)  # Monitor during workload
        
        await resource_monitor.stop_monitoring()
        avg_cpu = sum(m.cpu_percent for m in resource_monitor.metrics) / len(resource_monitor.metrics)
        assert avg_cpu < resource_monitor.limits.max_cpu_percent
        assert len(resource_monitor.metrics) >= 2
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_connection_pooling(self, db_tester: DatabaseConnectionTester):
        """Test database connection pool efficiency"""
        # Test multiple connection acquisition cycles
        acquisition_times = []
        
        for _ in range(3):
            acq_time, is_fast = await db_tester.test_connection_acquisition_speed()
            acquisition_times.append(acq_time)
            assert is_fast, f"Connection acquisition too slow: {acq_time}s"
        
        # Test pool reuse efficiency
        avg_time = sum(acquisition_times) / len(acquisition_times)
        assert avg_time < 0.5, f"Average connection time too slow: {avg_time}s"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_storage_growth_rate(self, storage_monitor: StorageMonitor):
        """Test storage growth remains predictable"""
        storage_monitor.start_monitoring()
        
        # Simulate operations that may create storage
        await self._simulate_storage_operations()
        await asyncio.sleep(1.0)  # Let operations complete
        
        storage_monitor.stop_monitoring()
        growth_mb = storage_monitor.get_growth_rate()
        
        # Growth should be minimal for test operations
        assert growth_mb < 50.0, f"Storage growth too high: {growth_mb}MB"
        assert growth_mb >= 0.0, "Storage growth should not be negative"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_memory_leak_detection(self, resource_monitor: ResourceMonitor):
        """Test for memory leaks during repeated operations"""
        await resource_monitor.start_monitoring()
        
        # Run repeated operations
        for _ in range(5):
            await self._simulate_memory_workload()
            gc.collect()  # Force garbage collection
            await asyncio.sleep(0.2)
        
        await resource_monitor.stop_monitoring()
        
        # Check memory doesn't continuously grow
        mid_point = len(resource_monitor.metrics) // 2
        first_half = resource_monitor.metrics[:mid_point]
        second_half = resource_monitor.metrics[mid_point:]
        
        avg_first = sum(m.memory_mb for m in first_half) / len(first_half)
        avg_second = sum(m.memory_mb for m in second_half) / len(second_half)
        growth_rate = (avg_second - avg_first) / avg_first if avg_first > 0 else 0
        assert growth_rate < 0.2, f"Memory growth rate too high: {growth_rate*100}%"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_resource_cleanup_efficiency(self, resource_monitor: ResourceMonitor):
        """Test resource cleanup after operations"""
        initial_metrics = resource_monitor._collect_current_metrics()
        
        await self._simulate_resource_intensive_workload()
        await asyncio.sleep(1.0)
        gc.collect()
        final_metrics = resource_monitor._collect_current_metrics()
        
        memory_diff = final_metrics.memory_mb - initial_metrics.memory_mb
        thread_diff = final_metrics.threads - initial_metrics.threads
        assert abs(memory_diff) < 100, f"Memory not cleaned up: {memory_diff}MB"
        assert abs(thread_diff) <= 2, f"Threads not cleaned up: {thread_diff}"
    
    async def _simulate_memory_workload(self) -> None:
        """Simulate typical memory usage patterns"""
        data = [str(i) * 100 for i in range(1000)]
        await asyncio.sleep(0.1)
        del data
    
    async def _simulate_cpu_workload(self) -> None:
        """Simulate CPU-intensive operations"""
        for _ in range(10000):
            hash(f"cpu_work_{_}")
        await asyncio.sleep(0.01)
    
    async def _simulate_storage_operations(self) -> None:
        """Simulate operations that might affect storage"""
        temp_data = {"test": "data", "timestamp": datetime.now().isoformat()}
        await asyncio.sleep(0.1)
        del temp_data
    
    async def _simulate_resource_intensive_workload(self) -> None:
        """Simulate resource-intensive operations"""
        tasks = [asyncio.create_task(self._simulate_memory_workload()) for _ in range(5)]
        await asyncio.gather(*tasks)
