"""
Test Suite: Backpressure Mechanism Testing - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: System Stability, Resource Management
- Value Impact: Prevents system collapse under extreme load
- Strategic/Revenue Impact: Essential for SLA compliance and uptime guarantees

This test validates backpressure mechanisms under overload conditions.
"""

import asyncio
import logging
import time
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.resource_monitoring import ResourceMonitor
from tests.e2e.test_helpers.throughput_helpers import (
    E2E_TEST_CONFIG,
    LoadTestResults,
    measure_system_resources,
)

logger = logging.getLogger(__name__)

BACKPRESSURE_CONFIG = {
    "overload_rate": 10000,  # Messages/sec to trigger backpressure
    "normal_rate": 1000,     # Normal operating rate
    "burst_duration": 30,    # Seconds
    "recovery_timeout": 60,  # Seconds
    "max_queue_depth": 5000,
    "backpressure_threshold": 0.8  # CPU/Memory threshold
}

class BackpressureMechanismTestingTests:
    """Test backpressure mechanisms under overload"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_backpressure_activation(self, throughput_client, high_volume_server):
        """Test that backpressure activates under overload conditions"""
        logger.info("Testing backpressure activation under overload")
        
        monitor = ResourceMonitor(interval_seconds=1.0)
        await monitor.start()
        
        try:
            # Send at overload rate to trigger backpressure
            overload_rate = BACKPRESSURE_CONFIG["overload_rate"]
            burst_duration = BACKPRESSURE_CONFIG["burst_duration"]
            message_count = overload_rate * burst_duration
            
            start_time = time.time()
            results = await throughput_client.send_throughput_burst(
                message_count=message_count,
                rate_limit=overload_rate
            )
            send_time = time.time() - start_time
            
            # Should take longer than expected due to backpressure
            expected_time = message_count / overload_rate
            backpressure_detected = send_time > expected_time * 1.5
            
            assert backpressure_detected, \
                f"Backpressure not detected: expected >{expected_time * 1.5}s, got {send_time}s"
            
            logger.info(f"Backpressure activated: {send_time:.1f}s vs expected {expected_time:.1f}s")
            
        finally:
            stats = await monitor.stop()
            
        # Verify system remained stable under backpressure
        assert stats["cpu"]["max"] <= 100, "CPU usage exceeded limits"
        assert stats["memory"]["growth_mb"] < 500, "Excessive memory growth"
    
    @pytest.mark.asyncio
    async def test_backpressure_recovery(self, throughput_client, high_volume_server):
        """Test system recovery after backpressure period"""
        logger.info("Testing backpressure recovery")
        
        # Create backpressure
        await self._create_backpressure_condition(throughput_client)
        
        # Wait for system to recover
        await asyncio.sleep(5.0)
        
        # Test normal operation after recovery
        normal_rate = BACKPRESSURE_CONFIG["normal_rate"]
        test_duration = 10
        message_count = normal_rate * test_duration
        
        start_time = time.time()
        results = await throughput_client.send_throughput_burst(
            message_count=message_count,
            rate_limit=normal_rate
        )
        
        responses = await throughput_client.receive_responses(
            expected_count=message_count,
            timeout=30.0
        )
        
        recovery_time = time.time() - start_time
        expected_time = test_duration
        
        # Should operate normally after recovery
        performance_ratio = recovery_time / expected_time
        assert performance_ratio < 1.5, \
            f"Poor performance after recovery: {performance_ratio:.2f}x slower"
        
        delivery_ratio = len(responses) / message_count
        assert delivery_ratio >= 0.95, \
            f"Poor delivery after recovery: {delivery_ratio:.3f}"
        
        logger.info(f"Recovery successful: {performance_ratio:.2f}x, {delivery_ratio:.3f} delivery")
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, throughput_client, high_volume_server):
        """Test graceful degradation under sustained overload"""
        logger.info("Testing graceful degradation under sustained load")
        
        sustained_rate = BACKPRESSURE_CONFIG["overload_rate"] // 2  # 50% of overload
        test_duration = 60  # 1 minute sustained test
        
        monitor = ResourceMonitor(interval_seconds=2.0)
        await monitor.start()
        
        try:
            results = await self._sustained_load_test(throughput_client, sustained_rate, test_duration)
            
            # Verify graceful degradation
            assert results["avg_delivery_ratio"] >= 0.8, \
                f"Delivery ratio too low under sustained load: {results['avg_delivery_ratio']:.3f}"
            
            assert results["performance_degradation"] <= 2.0, \
                f"Performance degraded too much: {results['performance_degradation']:.2f}x"
            
        finally:
            stats = await monitor.stop()
            
        # System should remain stable
        assert stats["cpu"]["avg"] <= 90, f"Average CPU too high: {stats['cpu']['avg']:.1f}%"
        assert stats["memory"]["growth_mb"] < 200, "Memory growth too high under sustained load"
        
        logger.info("Graceful degradation test passed")
    
    async def _create_backpressure_condition(self, throughput_client):
        """Create backpressure condition"""
        burst_rate = BACKPRESSURE_CONFIG["overload_rate"]
        burst_messages = burst_rate * 10  # 10 seconds of burst
        
        await throughput_client.send_throughput_burst(
            message_count=burst_messages,
            rate_limit=burst_rate
        )
    
    async def _sustained_load_test(self, throughput_client, rate: int, duration: int) -> Dict[str, Any]:
        """Execute sustained load test"""
        interval_duration = 10  # 10-second intervals
        intervals = duration // interval_duration
        
        delivery_ratios = []
        performance_ratios = []
        
        for interval in range(intervals):
            interval_messages = rate * interval_duration
            
            start_time = time.time()
            results = await throughput_client.send_throughput_burst(
                message_count=interval_messages,
                rate_limit=rate
            )
            
            responses = await throughput_client.receive_responses(
                expected_count=interval_messages,
                timeout=30.0
            )
            
            interval_time = time.time() - start_time
            expected_time = interval_duration
            
            delivery_ratio = len(responses) / interval_messages if interval_messages > 0 else 0
            performance_ratio = interval_time / expected_time
            
            delivery_ratios.append(delivery_ratio)
            performance_ratios.append(performance_ratio)
            
            logger.info(f"Interval {interval}: {delivery_ratio:.3f} delivery, "
                       f"{performance_ratio:.2f}x performance")
        
        return {
            "avg_delivery_ratio": sum(delivery_ratios) / len(delivery_ratios),
            "performance_degradation": max(performance_ratios),
            "delivery_ratios": delivery_ratios,
            "performance_ratios": performance_ratios
        }
