"""
Test Suite: Latency Percentile Distribution - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Performance SLA Compliance
- Value Impact: Ensures predictable response times for enterprise users
- Strategic/Revenue Impact: Critical for real-time application contracts

This test validates latency distribution under various load conditions.
"""

import asyncio
import logging
import statistics
import time
from typing import Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.throughput_helpers import (
    E2E_TEST_CONFIG,
    LatencyMeasurement,
    analyze_latency_distribution,
)

logger = logging.getLogger(__name__)

LATENCY_CONFIG = {
    "test_rates": [100, 500, 1000, 2000],
    "samples_per_rate": 1000,
    "max_p95_latency_ms": 500,
    "max_p99_latency_ms": 1000,
    "max_mean_latency_ms": 200
}

class LatencyPercentileDistributionTests:
    """Test latency distribution analysis"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_latency_percentiles_under_load(self, throughput_client, high_volume_server):
        """Validate latency percentiles under increasing load"""
        latency_results = {}
        
        for rate in LATENCY_CONFIG["test_rates"]:
            logger.info(f"Testing latency at {rate} msg/sec")
            
            measurements = await self._measure_latency_at_rate(throughput_client, rate)
            distribution = analyze_latency_distribution(measurements)
            latency_results[rate] = distribution
            
            # Assert latency requirements
            assert distribution["p95"] <= LATENCY_CONFIG["max_p95_latency_ms"], \
                f"P95 latency too high at {rate} msg/sec: {distribution['p95']:.1f}ms"
            
            assert distribution["p99"] <= LATENCY_CONFIG["max_p99_latency_ms"], \
                f"P99 latency too high at {rate} msg/sec: {distribution['p99']:.1f}ms"
            
            assert distribution["mean"] <= LATENCY_CONFIG["max_mean_latency_ms"], \
                f"Mean latency too high at {rate} msg/sec: {distribution['mean']:.1f}ms"
        
        # Validate latency scaling characteristics
        self._validate_latency_scaling(latency_results)
        logger.info("Latency percentile validation completed")
    
    @pytest.mark.asyncio
    async def test_latency_consistency(self, throughput_client, high_volume_server):
        """Test latency consistency over extended period"""
        rate = 500  # Moderate rate for consistency test
        test_duration = 120  # 2 minutes
        sample_interval = 10  # Sample every 10 seconds
        
        logger.info(f"Testing latency consistency at {rate} msg/sec for {test_duration}s")
        
        interval_latencies = []
        
        for interval in range(test_duration // sample_interval):
            measurements = await self._measure_latency_at_rate(throughput_client, rate, 
                                                             samples=100, duration=sample_interval)
            distribution = analyze_latency_distribution(measurements)
            interval_latencies.append(distribution)
            
            logger.info(f"Interval {interval}: P95={distribution['p95']:.1f}ms")
        
        # Check consistency
        p95_values = [lat["p95"] for lat in interval_latencies]
        p95_std_dev = statistics.stdev(p95_values)
        p95_mean = statistics.mean(p95_values)
        
        # P95 should be consistent (low coefficient of variation)
        cv = p95_std_dev / p95_mean if p95_mean > 0 else 0
        assert cv <= 0.3, f"P95 latency too inconsistent: CV={cv:.3f}"
        
        logger.info(f"Latency consistency validated: CV={cv:.3f}")
    
    async def _measure_latency_at_rate(self, throughput_client, rate: int, 
                                     samples: int = None, duration: int = 10) -> List[LatencyMeasurement]:
        """Measure latency at specific rate"""
        if samples is None:
            samples = min(LATENCY_CONFIG["samples_per_rate"], rate * duration)
        
        measurements = []
        
        for i in range(samples):
            message_id = f"latency_test_{rate}_{i}"
            
            send_time = time.time()
            await throughput_client.send_single_message({
                "message_id": message_id,
                "send_timestamp": send_time,
                "type": "latency_test"
            })
            
            # Wait for response
            try:
                response = await asyncio.wait_for(
                    throughput_client.receive_single_response(), 
                    timeout=5.0
                )
                receive_time = time.time()
                
                measurement = LatencyMeasurement(
                    message_id=message_id,
                    send_time=send_time,
                    receive_time=receive_time,
                    processing_time=0.0  # Would be extracted from response
                )
                measurement.calculate_latency()
                measurements.append(measurement)
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout for message {message_id}")
            
            # Rate limiting
            if i < samples - 1:
                await asyncio.sleep(1.0 / rate)
        
        return measurements
    
    def _validate_latency_scaling(self, latency_results: Dict[int, Dict[str, float]]):
        """Validate latency scaling characteristics"""
        rates = sorted(latency_results.keys())
        p95_latencies = [latency_results[rate]["p95"] for rate in rates]
        
        # P95 latency should not increase too dramatically with load
        for i in range(1, len(rates)):
            current_rate = rates[i]
            prev_rate = rates[i-1]
            
            current_p95 = p95_latencies[i]
            prev_p95 = p95_latencies[i-1]
            
            rate_multiplier = current_rate / prev_rate
            latency_multiplier = current_p95 / prev_p95 if prev_p95 > 0 else 1
            
            # Latency should not increase faster than rate squared
            max_acceptable_multiplier = rate_multiplier ** 1.5
            
            assert latency_multiplier <= max_acceptable_multiplier, \
                f"Latency scaling too steep: {latency_multiplier:.2f}x at {current_rate} msg/sec"
        
        logger.info("Latency scaling validation passed")
