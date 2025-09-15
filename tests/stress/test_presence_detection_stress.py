"""
Stress Tests for Presence Detection System

Business Value Justification:
- Segment: Mid & Enterprise (high concurrent user load)
- Business Goal: Scalability & Performance
- Value Impact: Ensures system handles peak loads without degradation
- Strategic Impact: Validates readiness for enterprise deployments

Stress tests for:
- High concurrent connections
- Rapid connect/disconnect cycles
- Memory leak detection
- CPU usage under load
- Network congestion handling
- Resource exhaustion scenarios
"""

import asyncio
import gc
import json
import psutil
# import resource  # Not available on Windows
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.manager import (
    WebSocketHeartbeatManager,
    HeartbeatConfig,
    get_heartbeat_manager
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class StressTestMetrics:
    """Metrics collected during stress tests."""
    start_time: float
    end_time: float
    total_connections: int
    successful_connections: int
    failed_connections: int
    total_heartbeats: int
    missed_heartbeats: int
    memory_start_mb: float
    memory_peak_mb: float
    memory_end_mb: float
    cpu_percent_avg: float
    errors: List[str]
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float


class MockWebSocketStress:
    """Mock WebSocket for stress testing."""
    
    def __init__(self, conn_id: str, fail_rate: float = 0.0):
        self.conn_id = conn_id
        self.fail_rate = fail_rate
        self.ping_count = 0
        self.is_connected = True
        
    async def ping(self, data: bytes = b''):
        """Simulate ping with configurable failure rate."""
        import random
        if random.random() < self.fail_rate:
            raise ConnectionError("Simulated connection error")
        self.ping_count += 1
        await asyncio.sleep(0.001)  # Minimal delay


class PresenceDetectionStressTests:
    """Stress tests for presence detection system."""
    
    @pytest.fixture
    def stress_manager(self):
        """Create heartbeat manager for stress testing."""
        config = HeartbeatConfig(
            heartbeat_interval_seconds=0.5,  # Faster for stress testing
            heartbeat_timeout_seconds=2,
            max_missed_heartbeats=2,
            cleanup_interval_seconds=3
        )
        return WebSocketHeartbeatManager(config)
    
    def collect_system_metrics(self) -> Tuple[float, float]:
        """Collect current system metrics."""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)
        return memory_mb, cpu_percent
    
    @pytest.mark.asyncio
    async def test_high_concurrent_connections(self, stress_manager):
        """Test with high number of concurrent connections."""
        num_connections = 1000
        metrics = StressTestMetrics(
            start_time=time.time(),
            end_time=0,
            total_connections=num_connections,
            successful_connections=0,
            failed_connections=0,
            total_heartbeats=0,
            missed_heartbeats=0,
            memory_start_mb=0,
            memory_peak_mb=0,
            memory_end_mb=0,
            cpu_percent_avg=0,
            errors=[],
            latency_p50_ms=0,
            latency_p95_ms=0,
            latency_p99_ms=0
        )
        
        # Start monitoring
        metrics.memory_start_mb, _ = self.collect_system_metrics()
        await stress_manager.start()
        
        connections = {}
        websockets = {}
        
        # Create connections concurrently
        async def create_connection(i: int):
            try:
                conn_id = f"stress_conn_{i}"
                ws = MockWebSocketStress(conn_id, fail_rate=0.01)
                
                await stress_manager.register_connection(conn_id)
                connections[conn_id] = time.time()
                websockets[conn_id] = ws
                metrics.successful_connections += 1
                
                # Send initial ping
                await stress_manager.send_ping(conn_id, ws)
                
            except Exception as e:
                metrics.failed_connections += 1
                metrics.errors.append(str(e))
        
        # Create all connections
        await asyncio.gather(*[create_connection(i) for i in range(num_connections)])
        
        # Simulate activity for 5 seconds
        activity_duration = 5
        activity_start = time.time()
        cpu_samples = []
        memory_samples = []
        latencies = []
        
        while time.time() - activity_start < activity_duration:
            # Sample metrics
            mem, cpu = self.collect_system_metrics()
            memory_samples.append(mem)
            cpu_samples.append(cpu)
            
            # Send heartbeats to random connections
            import random
            sample_size = min(100, len(connections))
            sample_conns = random.sample(list(connections.keys()), sample_size)
            
            for conn_id in sample_conns:
                if conn_id in websockets:
                    start = time.time()
                    try:
                        result = await stress_manager.send_ping(conn_id, websockets[conn_id])
                        if result:
                            metrics.total_heartbeats += 1
                            # Simulate pong
                            await stress_manager.record_pong(conn_id)
                    except Exception:
                        metrics.missed_heartbeats += 1
                    
                    latency_ms = (time.time() - start) * 1000
                    latencies.append(latency_ms)
            
            await asyncio.sleep(0.1)
        
        # Calculate metrics
        metrics.end_time = time.time()
        metrics.memory_peak_mb = max(memory_samples) if memory_samples else 0
        metrics.memory_end_mb, _ = self.collect_system_metrics()
        metrics.cpu_percent_avg = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        
        if latencies:
            latencies.sort()
            metrics.latency_p50_ms = latencies[len(latencies) // 2]
            metrics.latency_p95_ms = latencies[int(len(latencies) * 0.95)]
            metrics.latency_p99_ms = latencies[int(len(latencies) * 0.99)]
        
        # Cleanup
        for conn_id in connections:
            await stress_manager.unregister_connection(conn_id)
        
        await stress_manager.stop()
        
        # Report metrics
        logger.info(f"Stress test completed:")
        logger.info(f"  Connections: {metrics.successful_connections}/{metrics.total_connections}")
        logger.info(f"  Heartbeats: {metrics.total_heartbeats} sent, {metrics.missed_heartbeats} missed")
        logger.info(f"  Memory: {metrics.memory_start_mb:.1f} -> {metrics.memory_peak_mb:.1f} MB (peak)")
        logger.info(f"  CPU: {metrics.cpu_percent_avg:.1f}% average")
        logger.info(f"  Latency: p50={metrics.latency_p50_ms:.1f}ms, p95={metrics.latency_p95_ms:.1f}ms, p99={metrics.latency_p99_ms:.1f}ms")
        
        # Assertions
        assert metrics.successful_connections >= num_connections * 0.95  # 95% success rate
        assert metrics.memory_peak_mb - metrics.memory_start_mb < 100  # Less than 100MB growth
        assert metrics.latency_p95_ms < 50  # 95th percentile under 50ms
    
    @pytest.mark.asyncio
    async def test_rapid_connect_disconnect_cycles(self, stress_manager):
        """Test rapid connection and disconnection cycles."""
        num_cycles = 100
        connections_per_cycle = 50
        
        await stress_manager.start()
        
        cycle_times = []
        total_errors = 0
        
        for cycle in range(num_cycles):
            cycle_start = time.time()
            connections = []
            
            # Connect batch
            for i in range(connections_per_cycle):
                conn_id = f"cycle_{cycle}_conn_{i}"
                try:
                    await stress_manager.register_connection(conn_id)
                    connections.append(conn_id)
                except Exception:
                    total_errors += 1
            
            # Brief activity
            await asyncio.sleep(0.01)
            
            # Disconnect batch
            for conn_id in connections:
                await stress_manager.unregister_connection(conn_id)
            
            cycle_time = time.time() - cycle_start
            cycle_times.append(cycle_time)
        
        await stress_manager.stop()
        
        # Analyze results
        avg_cycle_time = sum(cycle_times) / len(cycle_times)
        max_cycle_time = max(cycle_times)
        
        logger.info(f"Rapid cycle test:")
        logger.info(f"  Cycles: {num_cycles}")
        logger.info(f"  Avg cycle time: {avg_cycle_time*1000:.1f}ms")
        logger.info(f"  Max cycle time: {max_cycle_time*1000:.1f}ms")
        logger.info(f"  Errors: {total_errors}")
        
        # Assertions
        assert avg_cycle_time < 0.5  # Average cycle under 500ms
        assert total_errors < num_cycles * connections_per_cycle * 0.01  # Less than 1% errors
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, stress_manager):
        """Test for memory leaks during extended operation."""
        tracemalloc.start()
        
        await stress_manager.start()
        
        # Take initial snapshot
        snapshot1 = tracemalloc.take_snapshot()
        gc.collect()
        memory_start, _ = self.collect_system_metrics()
        
        # Run cycles
        num_iterations = 50
        connections_per_iteration = 100
        
        for iteration in range(num_iterations):
            connections = []
            
            # Create connections
            for i in range(connections_per_iteration):
                conn_id = f"leak_test_{iteration}_{i}"
                await stress_manager.register_connection(conn_id)
                connections.append(conn_id)
            
            # Activity
            for conn_id in connections:
                await stress_manager.record_activity(conn_id)
            
            # Mark some as dead
            for i in range(0, len(connections), 2):
                await stress_manager._mark_connection_dead(connections[i])
            
            # Cleanup
            await stress_manager._cleanup_stale_data()
            
            # Remove all
            for conn_id in connections:
                if conn_id in stress_manager.connection_heartbeats:
                    await stress_manager.unregister_connection(conn_id)
            
            # Force garbage collection
            gc.collect()
        
        # Take final snapshot
        snapshot2 = tracemalloc.take_snapshot()
        memory_end, _ = self.collect_system_metrics()
        
        # Analyze memory growth
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        logger.info("Memory leak detection:")
        logger.info(f"  Memory: {memory_start:.1f} -> {memory_end:.1f} MB")
        logger.info("  Top memory increases:")
        for stat in top_stats[:5]:
            if stat.size_diff > 0:
                logger.info(f"    {stat}")
        
        await stress_manager.stop()
        tracemalloc.stop()
        
        # Assert no significant memory leak
        memory_growth_mb = memory_end - memory_start
        assert memory_growth_mb < 10  # Less than 10MB growth
    
    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self, stress_manager):
        """Test CPU usage under sustained load."""
        await stress_manager.start()
        
        num_connections = 500
        duration_seconds = 10
        
        # Create connections
        for i in range(num_connections):
            await stress_manager.register_connection(f"cpu_test_{i}")
        
        # Monitor CPU during load
        cpu_samples = []
        start_time = time.time()
        
        async def generate_load():
            """Generate continuous load."""
            while time.time() - start_time < duration_seconds:
                # Parallel operations
                tasks = []
                for i in range(min(50, num_connections)):
                    conn_id = f"cpu_test_{i}"
                    tasks.append(stress_manager.check_connection_health(conn_id))
                    tasks.append(stress_manager.record_activity(conn_id))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.01)
        
        # Run load generator and monitor CPU
        load_task = asyncio.create_task(generate_load())
        
        while time.time() - start_time < duration_seconds:
            _, cpu = self.collect_system_metrics()
            cpu_samples.append(cpu)
            await asyncio.sleep(0.5)
        
        await load_task
        
        # Cleanup
        for i in range(num_connections):
            await stress_manager.unregister_connection(f"cpu_test_{i}")
        
        await stress_manager.stop()
        
        # Analyze CPU usage
        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
        max_cpu = max(cpu_samples) if cpu_samples else 0
        
        logger.info(f"CPU usage under load:")
        logger.info(f"  Connections: {num_connections}")
        logger.info(f"  Average CPU: {avg_cpu:.1f}%")
        logger.info(f"  Peak CPU: {max_cpu:.1f}%")
        
        # CPU should remain reasonable
        assert avg_cpu < 80  # Average CPU under 80%
        assert max_cpu < 100  # Should not peg CPU
    
    @pytest.mark.asyncio
    async def test_network_congestion_simulation(self, stress_manager):
        """Test behavior under simulated network congestion."""
        await stress_manager.start()
        
        num_connections = 200
        connections = {}
        
        # Create connections with varying network conditions
        for i in range(num_connections):
            conn_id = f"network_test_{i}"
            # Higher fail rate for some connections
            fail_rate = 0.3 if i % 5 == 0 else 0.05
            ws = MockWebSocketStress(conn_id, fail_rate=fail_rate)
            
            await stress_manager.register_connection(conn_id)
            connections[conn_id] = ws
        
        # Simulate congested network
        successful_pings = 0
        failed_pings = 0
        timeouts = 0
        
        for _ in range(100):
            # Try to ping random connections
            import random
            conn_id = random.choice(list(connections.keys()))
            ws = connections[conn_id]
            
            try:
                start = time.time()
                result = await stress_manager.send_ping(conn_id, ws)
                
                if result:
                    successful_pings += 1
                    # Simulate delayed pong
                    await asyncio.sleep(random.uniform(0, 0.5))
                    await stress_manager.record_pong(conn_id)
                else:
                    failed_pings += 1
                    
            except asyncio.TimeoutError:
                timeouts += 1
            except Exception:
                failed_pings += 1
        
        # Check health of connections
        healthy_count = 0
        for conn_id in connections:
            if await stress_manager.check_connection_health(conn_id):
                healthy_count += 1
        
        # Cleanup
        for conn_id in connections:
            await stress_manager.unregister_connection(conn_id)
        
        await stress_manager.stop()
        
        logger.info(f"Network congestion simulation:")
        logger.info(f"  Successful pings: {successful_pings}")
        logger.info(f"  Failed pings: {failed_pings}")
        logger.info(f"  Timeouts: {timeouts}")
        logger.info(f"  Healthy connections: {healthy_count}/{num_connections}")
        
        # System should handle congestion gracefully
        assert successful_pings > failed_pings  # More successes than failures
        assert healthy_count > num_connections * 0.5  # At least 50% remain healthy
    
    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self, stress_manager):
        """Test recovery from resource exhaustion."""
        await stress_manager.start()
        
        # Phase 1: Exhaust resources
        phase1_connections = []
        max_connections = 2000
        
        logger.info("Phase 1: Exhausting resources...")
        
        for i in range(max_connections):
            try:
                conn_id = f"exhaust_{i}"
                await stress_manager.register_connection(conn_id)
                phase1_connections.append(conn_id)
            except Exception as e:
                logger.info(f"Resource exhaustion at {i} connections: {e}")
                break
        
        initial_count = len(phase1_connections)
        
        # Phase 2: Cleanup and recovery
        logger.info("Phase 2: Cleanup and recovery...")
        
        # Remove half of connections
        for conn_id in phase1_connections[:len(phase1_connections)//2]:
            await stress_manager.unregister_connection(conn_id)
        
        # Force cleanup
        await stress_manager._cleanup_stale_data()
        gc.collect()
        
        # Phase 3: Verify recovery
        logger.info("Phase 3: Verifying recovery...")
        
        phase3_connections = []
        recovery_target = initial_count // 4
        
        for i in range(recovery_target):
            try:
                conn_id = f"recovery_{i}"
                await stress_manager.register_connection(conn_id)
                phase3_connections.append(conn_id)
            except Exception:
                break
        
        recovery_count = len(phase3_connections)
        
        # Cleanup all
        for conn_id in phase1_connections[len(phase1_connections)//2:]:
            if conn_id in stress_manager.connection_heartbeats:
                await stress_manager.unregister_connection(conn_id)
        
        for conn_id in phase3_connections:
            await stress_manager.unregister_connection(conn_id)
        
        await stress_manager.stop()
        
        logger.info(f"Resource exhaustion test:")
        logger.info(f"  Initial capacity: {initial_count}")
        logger.info(f"  Recovery target: {recovery_target}")
        logger.info(f"  Actual recovery: {recovery_count}")
        
        # Should recover at least 90% of target
        assert recovery_count >= recovery_target * 0.9
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_stress(self, stress_manager):
        """Test highly concurrent operations on same connections."""
        await stress_manager.start()
        
        num_connections = 100
        operations_per_connection = 50
        
        # Create connections
        for i in range(num_connections):
            await stress_manager.register_connection(f"concurrent_{i}")
        
        # Define concurrent operations
        async def concurrent_ops(conn_id: str):
            """Perform multiple operations concurrently."""
            tasks = []
            
            for _ in range(operations_per_connection):
                # Mix of operations
                tasks.append(stress_manager.record_activity(conn_id))
                tasks.append(stress_manager.check_connection_health(conn_id))
                
                if len(tasks) >= 10:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Run concurrent operations on all connections
        start_time = time.time()
        
        await asyncio.gather(*[
            concurrent_ops(f"concurrent_{i}") 
            for i in range(num_connections)
        ])
        
        duration = time.time() - start_time
        total_operations = num_connections * operations_per_connection * 2
        ops_per_second = total_operations / duration
        
        # Cleanup
        for i in range(num_connections):
            await stress_manager.unregister_connection(f"concurrent_{i}")
        
        await stress_manager.stop()
        
        logger.info(f"Concurrent operations stress:")
        logger.info(f"  Total operations: {total_operations}")
        logger.info(f"  Duration: {duration:.2f}s")
        logger.info(f"  Operations/second: {ops_per_second:.0f}")
        
        # Should handle high concurrency
        assert ops_per_second > 1000  # At least 1000 ops/sec
