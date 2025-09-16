"""
Performance Benchmark Tests for Rapid Message Succession.

Business Value Justification (BVJ):
- Segment: All Segments
- Business Goal: Performance Optimization
- Value Impact: Validates system performance under rapid message load
- Strategic/Revenue Impact: Ensures scalability for growing customer base
"""

import asyncio
import statistics
import time
import uuid
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.fixtures.rapid_message_fixtures import (
    message_validator,
    test_config,
    user_token,
)
from tests.e2e.utils.rapid_message_sender import RapidMessageSender


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.performance
class RapidMessagePerformanceTests:
    """Performance benchmark tests for rapid message processing."""
    
    @pytest.mark.performance
    async def test_throughput_benchmark(self, user_token, message_validator, test_config):
        """Benchmark message throughput under various conditions."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Test different burst sizes
            test_cases = [
                {"size": 10, "delay": 0.01},
                {"size": 50, "delay": 0.005},
                {"size": 100, "delay": 0.001}
            ]
            
            results = {}
            
            for case in test_cases:
                start_time = time.time()
                result = await sender.send_message_burst(
                    f"{user_id}_{case['size']}", 
                    case["size"], 
                    burst_delay=case["delay"]
                )
                end_time = time.time()
                
                throughput = result.successful_sends / (end_time - start_time)
                results[case["size"]] = {
                    "throughput": throughput,
                    "success_rate": result.successful_sends / result.total_messages,
                    "avg_processing_time": statistics.mean(result.processing_times) if result.processing_times else 0
                }
                
                # Brief pause between test cases
                await asyncio.sleep(0.5)
            
            # Validate performance benchmarks
            assert results[10]["throughput"] >= 5.0, "Low throughput for small bursts"
            assert results[50]["throughput"] >= 10.0, "Low throughput for medium bursts"
            assert results[100]["success_rate"] >= 0.8, "Poor success rate for large bursts"
            
        finally:
            await sender.disconnect()
    
    @pytest.mark.performance
    async def test_latency_distribution(self, user_token, message_validator, test_config):
        """Test latency distribution under rapid message load."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Send burst and analyze latency
            result = await sender.send_message_burst(user_id, 100, burst_delay=0.002)
            
            if result.processing_times:
                # Calculate latency statistics
                processing_times = result.processing_times
                avg_latency = statistics.mean(processing_times)
                median_latency = statistics.median(processing_times)
                p95_latency = sorted(processing_times)[int(0.95 * len(processing_times))]
                
                # Performance targets
                assert avg_latency <= 2.0, f"Average latency too high: {avg_latency}s"
                assert median_latency <= 1.5, f"Median latency too high: {median_latency}s"
                assert p95_latency <= 5.0, f"P95 latency too high: {p95_latency}s"
                
        finally:
            await sender.disconnect()
    
    @pytest.mark.performance
    async def test_concurrent_user_performance(self, user_token, message_validator, test_config):
        """Test performance with multiple concurrent users."""
        user_base = f"test_user_{uuid.uuid4().hex[:8]}"
        user_count = 10
        messages_per_user = 20
        
        # Create concurrent senders
        senders = []
        for i in range(user_count):
            sender = RapidMessageSender(test_config["websocket_url"], user_token)
            assert await sender.connect()
            senders.append(sender)
        
        try:
            start_time = time.time()
            
            # All users send messages concurrently
            tasks = []
            for i, sender in enumerate(senders):
                task = sender.send_message_burst(
                    f"{user_base}_user_{i}", 
                    messages_per_user, 
                    burst_delay=0.005
                )
                tasks.append(task)
                
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Calculate overall metrics
            total_messages = user_count * messages_per_user
            total_successful = sum(r.successful_sends for r in results)
            overall_throughput = total_successful / (end_time - start_time)
            overall_success_rate = total_successful / total_messages
            
            # Performance targets for concurrent load
            assert overall_throughput >= 50.0, f"Concurrent throughput too low: {overall_throughput}"
            assert overall_success_rate >= 0.85, f"Concurrent success rate too low: {overall_success_rate}"
            
        finally:
            for sender in senders:
                await sender.disconnect()
    
    @pytest.mark.slow
    async def test_sustained_load_performance(self, user_token, message_validator, test_config):
        """Test performance under sustained load over time."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        sender = RapidMessageSender(test_config["websocket_url"], user_token)
        
        assert await sender.connect()
        
        try:
            # Sustained load test
            duration_minutes = 2
            batch_interval = 5  # seconds
            messages_per_batch = 25
            
            start_time = time.time()
            batch_results = []
            
            while (time.time() - start_time) < (duration_minutes * 60):
                batch_start = time.time()
                result = await sender.send_message_burst(
                    f"{user_id}_sustained_{len(batch_results)}", 
                    messages_per_batch, 
                    burst_delay=0.002
                )
                
                batch_results.append({
                    "timestamp": batch_start,
                    "success_rate": result.successful_sends / result.total_messages,
                    "avg_processing_time": statistics.mean(result.processing_times) if result.processing_times else 0
                })
                
                # Wait for next batch
                await asyncio.sleep(batch_interval)
            
            # Analyze sustained performance
            success_rates = [b["success_rate"] for b in batch_results]
            processing_times = [b["avg_processing_time"] for b in batch_results if b["avg_processing_time"] > 0]
            
            # Performance should remain stable
            avg_success_rate = statistics.mean(success_rates)
            assert avg_success_rate >= 0.9, f"Sustained success rate degraded: {avg_success_rate}"
            
            if processing_times:
                # Processing time shouldn't degrade significantly
                first_half = processing_times[:len(processing_times)//2]
                second_half = processing_times[len(processing_times)//2:]
                
                if first_half and second_half:
                    degradation = statistics.mean(second_half) / statistics.mean(first_half)
                    assert degradation <= 2.0, f"Performance degraded over time: {degradation}x"
            
        finally:
            await sender.disconnect()
