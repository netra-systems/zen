"""
Burst Handling and Message Ordering Tests

Tests message ordering preservation and burst handling capabilities.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Platform Reliability, Message Integrity
- Value Impact: Ensures message ordering guarantees for enterprise workflows
- Strategic Impact: Critical for applications requiring strict message sequencing
"""

import asyncio
import logging
import time
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.performance_base import (
    HighVolumeThroughputClient,
    LoadTestResults,
    ThroughputAnalyzer,
)

logger = logging.getLogger(__name__)


class TestMessageOrderingPreservation:
    """Test message ordering preservation under high load."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(180)
    async def test_message_ordering_preservation_flood(self, throughput_client, high_volume_server):
        """Ensure strict message ordering during high-volume bursts."""
        test_results = self._create_test_results("message_ordering_preservation")
        
        # Single connection flood test
        message_count = 10000
        logger.info(f"Flooding server with {message_count} ordered messages...")
        
        start_time = time.perf_counter()
        results = await throughput_client.send_throughput_burst(
            message_count=message_count, rate_limit=1000
        )
        send_duration = time.perf_counter() - start_time
        
        responses = await throughput_client.receive_responses(
            expected_count=message_count, timeout=120.0
        )
        
        ordering_validation = ThroughputAnalyzer.validate_message_ordering(responses)
        
        # Test concurrent connections
        concurrent_responses = await self._test_concurrent_ordering()
        concurrent_ordering = ThroughputAnalyzer.validate_message_ordering(concurrent_responses)
        
        self._assert_ordering_requirements(ordering_validation, concurrent_ordering)
        self._finalize_ordering_results(test_results, responses, concurrent_responses, 
                                      ordering_validation, concurrent_ordering)
        
        logger.info(f"Message ordering test completed: {test_results.ordering_violations} violations")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_burst_pattern_handling(self, throughput_client, high_volume_server):
        """Test handling of various burst patterns."""
        patterns = [
            {"name": "rapid_burst", "messages": 5000, "rate": 2000, "duration": 2.5},
            {"name": "sustained_burst", "messages": 10000, "rate": 1000, "duration": 10},
            {"name": "spike_burst", "messages": 1000, "rate": 5000, "duration": 0.2}
        ]
        
        results = {}
        
        for pattern in patterns:
            logger.info(f"Testing {pattern['name']} pattern...")
            
            start_time = time.perf_counter()
            send_results = await throughput_client.send_throughput_burst(
                message_count=pattern["messages"], 
                rate_limit=pattern["rate"]
            )
            actual_duration = time.perf_counter() - start_time
            
            responses = await throughput_client.receive_responses(
                expected_count=pattern["messages"], timeout=60.0
            )
            
            metrics = self._calculate_burst_metrics(send_results, responses, actual_duration)
            results[pattern["name"]] = metrics
            
            self._assert_burst_performance(pattern, metrics)
        
        self._validate_burst_consistency(results)

    def _create_test_results(self, test_name: str) -> LoadTestResults:
        """Create test results object."""
        return LoadTestResults(
            test_name=test_name,
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
    
    async def _test_concurrent_ordering(self) -> list:
        """Test ordering with concurrent connections."""
        logger.info("Testing ordering with concurrent connections...")
        
        concurrent_clients = []
        try:
            # Create 10 concurrent clients
            for i in range(10):
                client = HighVolumeThroughputClient(
                    "ws://localhost:8765", "mock-token", f"concurrent-client-{i}"
                )
                await client.connect()
                concurrent_clients.append(client)
            
            # Each client sends 1000 messages concurrently
            tasks = [
                client.send_throughput_burst(1000, rate_limit=100)
                for client in concurrent_clients
            ]
            await asyncio.gather(*tasks)
            
            # Collect responses from all clients
            all_responses = []
            for client in concurrent_clients:
                responses = await client.receive_responses(1000, timeout=60.0)
                all_responses.extend(responses)
            
            return all_responses
            
        finally:
            await self._cleanup_clients(concurrent_clients)
    
    def _calculate_burst_metrics(self, send_results: list, responses: list, duration: float) -> dict:
        """Calculate metrics for burst pattern."""
        sent_count = len([r for r in send_results if r["status"] == "sent"])
        received_count = len(responses)
        
        return {
            "sent_count": sent_count,
            "received_count": received_count,
            "duration": duration,
            "throughput": sent_count / duration if duration > 0 else 0,
            "delivery_ratio": received_count / sent_count if sent_count > 0 else 0
        }
    
    def _assert_ordering_requirements(self, single_ordering: dict, concurrent_ordering: dict):
        """Assert ordering requirements are met."""
        assert len(single_ordering["ordering_violations"]) == 0, \
            f"Ordering violations in single connection: {single_ordering['ordering_violations']}"
        
        assert len(single_ordering["missing_sequences"]) == 0, \
            f"Missing sequences: {single_ordering['missing_sequences']}"
        
        assert single_ordering["out_of_order_count"] == 0, \
            f"Out of order messages: {single_ordering['out_of_order_count']}"
        
        assert len(concurrent_ordering["ordering_violations"]) == 0, \
            f"Concurrent ordering violations: {concurrent_ordering['ordering_violations']}"
    
    def _assert_burst_performance(self, pattern: dict, metrics: dict):
        """Assert burst performance requirements."""
        assert metrics["delivery_ratio"] >= 0.95, \
            f"{pattern['name']}: Delivery ratio too low: {metrics['delivery_ratio']:.3f}"
        
        expected_rate = pattern["rate"]
        actual_rate = metrics["throughput"]
        rate_ratio = actual_rate / expected_rate if expected_rate > 0 else 0
        
        assert rate_ratio >= 0.8, \
            f"{pattern['name']}: Throughput too low: {actual_rate:.1f} vs {expected_rate}"
    
    def _validate_burst_consistency(self, results: dict):
        """Validate consistency across burst patterns."""
        delivery_ratios = [results[p]["delivery_ratio"] for p in results]
        min_ratio = min(delivery_ratios)
        
        assert min_ratio >= 0.9, \
            f"Inconsistent burst handling: minimum delivery ratio {min_ratio:.3f}"
    
    def _finalize_ordering_results(self, test_results: LoadTestResults, 
                                 responses: list, concurrent_responses: list,
                                 ordering_validation: dict, concurrent_ordering: dict):
        """Finalize test results with ordering metrics."""
        test_results.messages_sent = 10000 + 10000  # Single + concurrent
        test_results.messages_received = len(responses) + len(concurrent_responses)
        test_results.ordering_violations = (
            len(ordering_validation["ordering_violations"]) +
            len(concurrent_ordering["ordering_violations"])
        )
        test_results.delivery_ratio = test_results.messages_received / test_results.messages_sent
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
    
    async def _cleanup_clients(self, clients: list):
        """Clean up client connections."""
        for client in clients:
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Client cleanup error: {e}")


class TestDeliveryGuaranteeValidation:
    """Test message delivery guarantees under various conditions."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_delivery_guarantee_validation(self, throughput_client, high_volume_server):
        """Validate 99.9% delivery guarantee under various load conditions."""
        test_scenarios = [
            {"name": "low_load", "messages": 1000, "rate": 100},
            {"name": "medium_load", "messages": 5000, "rate": 500}, 
            {"name": "high_load", "messages": 10000, "rate": 1000},
            {"name": "extreme_load", "messages": 15000, "rate": 2000}
        ]
        
        delivery_results = {}
        
        for scenario in test_scenarios:
            logger.info(f"Testing delivery guarantees: {scenario['name']}")
            
            results = await throughput_client.send_throughput_burst(
                message_count=scenario["messages"],
                rate_limit=scenario["rate"]
            )
            
            responses = await throughput_client.receive_responses(
                expected_count=scenario["messages"],
                timeout=120.0
            )
            
            sent_count = len([r for r in results if r["status"] == "sent"])
            received_count = len(responses)
            delivery_ratio = received_count / sent_count if sent_count > 0 else 0
            
            delivery_results[scenario["name"]] = {
                "sent": sent_count,
                "received": received_count,
                "ratio": delivery_ratio
            }
            
            # Individual scenario assertion
            assert delivery_ratio >= 0.999, \
                f"{scenario['name']}: Delivery ratio {delivery_ratio:.4f} below 99.9%"
        
        # Overall consistency check
        ratios = [delivery_results[s]["ratio"] for s in delivery_results]
        min_ratio = min(ratios)
        
        assert min_ratio >= 0.999, \
            f"Delivery guarantee violated: minimum ratio {min_ratio:.4f}"
        
        logger.info("Delivery guarantee validation passed for all scenarios")
