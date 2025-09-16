"""
Test Suite: Memory Efficiency Under Load - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Resource Optimization, Cost Control
- Value Impact: Ensures efficient resource utilization for cost-effective scaling
- Strategic/Revenue Impact: Reduces infrastructure costs and improves margins

This test validates memory efficiency under high load conditions.
"""

import asyncio
import gc
import logging
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.resource_monitoring import (
    MemoryLeakDetector,
    ResourceMonitor,
    resource_monitoring_context,
)
from tests.e2e.test_helpers.throughput_helpers import E2E_TEST_CONFIG

logger = logging.getLogger(__name__)

MEMORY_CONFIG = {
    "load_test_duration": 120,  # 2 minutes
    "message_rate": 1000,       # msg/sec
    "max_memory_growth_mb": 100,
    "leak_threshold_mb": 50,
    "gc_frequency": 30          # seconds
}

class MemoryEfficiencyUnderLoadTests:
    """Test memory efficiency under sustained load"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_memory_efficiency_sustained_load(self, throughput_client, high_volume_server):
        """Test memory usage during sustained load"""
        logger.info("Testing memory efficiency under sustained load")
        
        leak_detector = MemoryLeakDetector(threshold_mb=MEMORY_CONFIG["leak_threshold_mb"])
        leak_detector.establish_baseline()
        
        async with resource_monitoring_context(interval=2.0) as monitor:
            # Run sustained load test
            await self._execute_sustained_load_test(throughput_client)
            
            # Check for memory leaks
            leak_result = leak_detector.check_for_leak()
            
            assert not leak_result["leak_detected"], \
                f"Memory leak detected: {leak_result['growth_mb']:.1f}MB growth"
        
        # Validate final resource usage
        stats = monitor.get_statistics()
        assert stats["memory"]["growth_mb"] <= MEMORY_CONFIG["max_memory_growth_mb"], \
            f"Memory growth too high: {stats['memory']['growth_mb']:.1f}MB"
        
        logger.info(f"Memory efficiency test passed: {stats['memory']['growth_mb']:.1f}MB growth")
    
    @pytest.mark.asyncio
    async def test_garbage_collection_effectiveness(self, throughput_client, high_volume_server):
        """Test that garbage collection is effective under load"""
        logger.info("Testing garbage collection effectiveness")
        
        # Create memory pressure
        await self._create_memory_pressure(throughput_client)
        
        # Measure memory before GC
        pre_gc_memory = self._get_memory_usage()
        
        # Force garbage collection
        gc.collect()
        await asyncio.sleep(2.0)  # Allow GC to complete
        
        # Measure memory after GC
        post_gc_memory = self._get_memory_usage()
        memory_freed = pre_gc_memory - post_gc_memory
        
        # Should free reasonable amount of memory
        assert memory_freed >= 0, "Memory increased after GC"
        
        # If significant memory was used, GC should free some
        if pre_gc_memory > 100:  # 100MB threshold
            gc_effectiveness = memory_freed / pre_gc_memory
            assert gc_effectiveness >= 0.1, \
                f"GC not effective enough: {gc_effectiveness:.3f} freed ratio"
        
        logger.info(f"GC freed {memory_freed:.1f}MB ({memory_freed/pre_gc_memory:.1%})")
    
    @pytest.mark.asyncio
    async def test_memory_usage_patterns(self, throughput_client, high_volume_server):
        """Test memory usage patterns during different load phases"""
        logger.info("Testing memory usage patterns")
        
        pattern_results = {}
        
        # Test different load patterns
        test_phases = [
            ("idle", 0, 30),
            ("light_load", 100, 30),
            ("moderate_load", 500, 30),
            ("heavy_load", 1000, 30),
            ("recovery", 0, 30)
        ]
        
        for phase_name, rate, duration in test_phases:
            logger.info(f"Testing {phase_name} phase: {rate} msg/sec for {duration}s")
            
            start_memory = self._get_memory_usage()
            
            if rate > 0:
                await self._load_test_phase(throughput_client, rate, duration)
            else:
                await asyncio.sleep(duration)  # Idle phase
            
            end_memory = self._get_memory_usage()
            memory_change = end_memory - start_memory
            
            pattern_results[phase_name] = {
                "rate": rate,
                "duration": duration,
                "memory_change_mb": memory_change,
                "start_memory_mb": start_memory,
                "end_memory_mb": end_memory
            }
            
            # Allow stabilization between phases
            await asyncio.sleep(5.0)
        
        # Validate patterns
        self._validate_memory_patterns(pattern_results)
        
        logger.info("Memory usage pattern validation completed")
    
    async def _execute_sustained_load_test(self, throughput_client):
        """Execute sustained load test"""
        duration = MEMORY_CONFIG["load_test_duration"]
        rate = MEMORY_CONFIG["message_rate"]
        gc_frequency = MEMORY_CONFIG["gc_frequency"]
        
        end_time = time.time() + duration
        last_gc = time.time()
        
        while time.time() < end_time:
            # Send burst of messages
            burst_duration = min(10, end_time - time.time())
            message_count = int(rate * burst_duration)
            
            if message_count > 0:
                await throughput_client.send_throughput_burst(
                    message_count=message_count,
                    rate_limit=rate
                )
            
            # Periodic garbage collection
            if time.time() - last_gc >= gc_frequency:
                gc.collect()
                last_gc = time.time()
            
            await asyncio.sleep(1.0)
    
    async def _create_memory_pressure(self, throughput_client):
        """Create memory pressure for GC testing"""
        # Send large burst to create temporary memory pressure
        burst_size = 5000
        await throughput_client.send_throughput_burst(
            message_count=burst_size,
            rate_limit=2000  # High rate
        )
    
    async def _load_test_phase(self, throughput_client, rate: int, duration: int):
        """Execute single load test phase"""
        message_count = rate * duration
        
        await throughput_client.send_throughput_burst(
            message_count=message_count,
            rate_limit=rate
        )
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def _validate_memory_patterns(self, pattern_results: Dict[str, Dict]):
        """Validate memory usage patterns are reasonable"""
        # Recovery phase should not have significant growth
        recovery = pattern_results.get("recovery", {})
        if recovery:
            assert recovery["memory_change_mb"] <= 20, \
                f"Memory grew during recovery: {recovery['memory_change_mb']:.1f}MB"
        
        # Heavy load should not cause excessive growth
        heavy_load = pattern_results.get("heavy_load", {})
        if heavy_load:
            assert heavy_load["memory_change_mb"] <= MEMORY_CONFIG["max_memory_growth_mb"], \
                f"Heavy load memory growth too high: {heavy_load['memory_change_mb']:.1f}MB"
        
        logger.info("Memory pattern validation passed")
