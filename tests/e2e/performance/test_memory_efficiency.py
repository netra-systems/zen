"""
Memory Efficiency Tests

Tests memory usage patterns and leak detection under various load conditions.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Resource Optimization, System Stability
- Value Impact: Prevents memory leaks that could cause production outages
- Strategic Impact: Critical for long-running enterprise deployments
"""

import asyncio
import gc
import logging
import time
from shared.isolated_environment import IsolatedEnvironment

import psutil
import pytest

from tests.e2e.test_helpers.performance_base import HIGH_VOLUME_CONFIG

logger = logging.getLogger(__name__)


class MemoryEfficiencyUnderLoadTests:
    """Test memory efficiency and leak detection under load."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_memory_efficiency_under_load(self, throughput_client, high_volume_server):
        """Test memory usage and leak detection during sustained load."""
        logger.info("Testing memory efficiency under sustained load...")
        
        # Measure initial memory
        gc.collect()  # Clean up before measurement
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        memory_samples = [initial_memory]
        load_phases = [
            {"messages": 2000, "rate": 500, "name": "ramp_up"},
            {"messages": 5000, "rate": 1000, "name": "sustained"},
            {"messages": 3000, "rate": 1500, "name": "peak"},
            {"messages": 1000, "rate": 300, "name": "ramp_down"}
        ]
        
        for phase in load_phases:
            logger.info(f"Memory test phase: {phase['name']}")
            
            phase_start_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            results = await throughput_client.send_throughput_burst(
                message_count=phase["messages"], rate_limit=phase["rate"]
            )
            
            responses = await throughput_client.receive_responses(
                expected_count=phase["messages"], timeout=60.0
            )
            
            # Force garbage collection and measure memory
            gc.collect()
            await asyncio.sleep(1.0)  # Allow cleanup
            
            phase_end_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            memory_samples.append(phase_end_memory)
            
            logger.info(f"Phase {phase['name']}: {phase_start_memory:.1f} MB -> {phase_end_memory:.1f} MB")
        
        self._assert_memory_efficiency(initial_memory, memory_samples)

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_connection_memory_scaling(self, high_volume_server):
        """Test memory usage with scaling connection counts."""
        connection_counts = [1, 10, 50, 100]
        memory_per_connection = []
        
        for conn_count in connection_counts:
            gc.collect()
            before_memory = psutil.Process().memory_info().rss / (1024 * 1024)
            
            # Create connections
            clients = await self._create_multiple_clients(conn_count)
            
            try:
                # Small workload to establish connections
                tasks = [
                    client.send_throughput_burst(100, rate_limit=100) 
                    for client in clients
                ]
                await asyncio.gather(*tasks)
                
                gc.collect()
                await asyncio.sleep(1.0)
                
                after_memory = psutil.Process().memory_info().rss / (1024 * 1024)
                memory_growth = after_memory - before_memory
                memory_per_conn = memory_growth / conn_count if conn_count > 0 else 0
                
                memory_per_connection.append({
                    "connections": conn_count,
                    "memory_growth_mb": memory_growth, 
                    "memory_per_connection_mb": memory_per_conn
                })
                
                logger.info(f"{conn_count} connections: {memory_growth:.2f} MB "
                           f"({memory_per_conn:.2f} MB per connection)")
                
            finally:
                await self._cleanup_clients(clients)
        
        self._assert_connection_memory_scaling(memory_per_connection)

    @pytest.mark.asyncio
    @pytest.mark.e2e 
    async def test_long_running_stability(self, throughput_client, high_volume_server):
        """Test memory stability over extended operation."""
        duration_minutes = 5  # 5 minute stability test
        sample_interval = 30  # Sample every 30 seconds
        
        gc.collect()
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        memory_timeline = [{"time": 0, "memory_mb": initial_memory}]
        
        start_time = time.time()
        last_sample = start_time
        
        while time.time() - start_time < (duration_minutes * 60):
            # Continuous moderate load
            results = await throughput_client.send_throughput_burst(
                message_count=500, rate_limit=200
            )
            responses = await throughput_client.receive_responses(500, timeout=15.0)
            
            # Sample memory if interval elapsed
            if time.time() - last_sample >= sample_interval:
                gc.collect()
                current_memory = psutil.Process().memory_info().rss / (1024 * 1024)
                elapsed = time.time() - start_time
                
                memory_timeline.append({
                    "time": elapsed,
                    "memory_mb": current_memory
                })
                
                logger.info(f"Stability test {elapsed/60:.1f}min: {current_memory:.1f} MB")
                last_sample = time.time()
        
        self._assert_long_running_stability(memory_timeline, initial_memory)
    
    def _assert_memory_efficiency(self, initial_memory: float, memory_samples: list):
        """Assert memory efficiency requirements."""
        final_memory = memory_samples[-1]
        max_memory = max(memory_samples)
        
        # Total memory growth should be within limits
        total_growth = final_memory - initial_memory
        assert total_growth <= HIGH_VOLUME_CONFIG["max_memory_growth_mb"], \
            f"Memory growth {total_growth:.1f} MB exceeds limit {HIGH_VOLUME_CONFIG['max_memory_growth_mb']} MB"
        
        # Peak memory usage should be reasonable
        peak_growth = max_memory - initial_memory
        assert peak_growth <= HIGH_VOLUME_CONFIG["max_memory_growth_mb"] * 1.5, \
            f"Peak memory growth {peak_growth:.1f} MB too high"
        
        # Memory should not indicate leaks (final close to initial)
        memory_leak_indicator = final_memory - initial_memory
        assert memory_leak_indicator <= HIGH_VOLUME_CONFIG["memory_leak_threshold_mb"], \
            f"Potential memory leak detected: {memory_leak_indicator:.1f} MB growth"
    
    def _assert_connection_memory_scaling(self, memory_data: list):
        """Assert connection memory scaling is reasonable."""
        if len(memory_data) < 2:
            return
        
        # Memory per connection should be consistent
        per_conn_values = [d["memory_per_connection_mb"] for d in memory_data if d["connections"] > 0]
        if per_conn_values:
            max_per_conn = max(per_conn_values)
            min_per_conn = min(per_conn_values)
            
            # Memory per connection should not vary too much
            variation_ratio = (max_per_conn - min_per_conn) / max_per_conn if max_per_conn > 0 else 0
            assert variation_ratio <= 0.5, \
                f"Memory per connection varies too much: {variation_ratio:.3f}"
    
    def _assert_long_running_stability(self, timeline: list, initial_memory: float):
        """Assert long-running memory stability."""
        final_memory = timeline[-1]["memory_mb"]
        max_memory = max(t["memory_mb"] for t in timeline)
        
        # Should not grow beyond threshold over time
        total_growth = final_memory - initial_memory
        assert total_growth <= HIGH_VOLUME_CONFIG["memory_leak_threshold_mb"], \
            f"Memory grew {total_growth:.1f} MB over long run (leak indicator)"
        
        # Should not have excessive peaks
        peak_growth = max_memory - initial_memory
        assert peak_growth <= HIGH_VOLUME_CONFIG["max_memory_growth_mb"], \
            f"Peak memory growth {peak_growth:.1f} MB too high for stability test"
        
        # Memory should be relatively stable (no continuous growth)
        if len(timeline) >= 3:
            recent_avg = sum(t["memory_mb"] for t in timeline[-3:]) / 3
            early_avg = sum(t["memory_mb"] for t in timeline[:3]) / 3
            
            trend = (recent_avg - early_avg) / early_avg if early_avg > 0 else 0
            assert trend <= 0.1, \
                f"Memory shows upward trend {trend:.3f} indicating potential leak"
    
    async def _create_multiple_clients(self, count: int) -> list:
        """Create multiple client connections."""
        from tests.e2e.fixtures.high_volume_data import MockAuthenticator
        from tests.e2e.test_helpers.performance_base import (
            HighVolumeThroughputClient,
        )
        
        clients = []
        for i in range(count):
            user = MockAuthenticator.create_test_user()
            client = HighVolumeThroughputClient(
                "ws://localhost:8765", user["token"], f"memory-client-{i}"
            )
            await client.connect()
            clients.append(client)
        
        return clients
    
    async def _cleanup_clients(self, clients: list):
        """Clean up client connections."""
        for client in clients:
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Client cleanup error: {e}")
