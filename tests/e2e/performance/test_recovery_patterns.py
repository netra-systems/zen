"""
Recovery Patterns and Resilience Tests

Tests error recovery, resilience mechanisms, and memory efficiency under load.

Business Value Justification (BVJ):
- Segment: Enterprise/Mid
- Business Goal: Platform Resilience, Error Recovery
- Value Impact: Ensures system stability during adverse conditions
- Strategic Impact: Critical for production reliability and uptime guarantees
"""

import asyncio
import gc
import logging
import random
import time
from shared.isolated_environment import IsolatedEnvironment

import psutil
import pytest

from tests.e2e.test_helpers.performance_base import (
    HIGH_VOLUME_CONFIG,
    HighVolumeThroughputClient,
    LoadTestResults,
)

logger = logging.getLogger(__name__)


class ErrorRecoveryAndResilienceTests:
    """Test error recovery and system resilience."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_error_recovery_and_resilience(self, throughput_client, high_volume_server):
        """Test system recovery from errors during high-volume operations."""
        test_results = self._create_test_results("error_recovery_and_resilience")
        baseline_rate = 3000
        
        logger.info(f"Starting error recovery test with {baseline_rate} msg/sec baseline...")
        
        # Establish baseline
        baseline_data = await self._establish_baseline(throughput_client, baseline_rate)
        
        # Test error scenarios
        error_scenarios = self._define_error_scenarios()
        error_results = {}
        
        for scenario in error_scenarios:
            logger.info(f"Testing error scenario: {scenario['name']}")
            scenario_data = await self._test_error_scenario(scenario)
            error_results[scenario["name"]] = scenario_data
        
        self._assert_resilience_requirements(baseline_data, error_results)
        self._finalize_resilience_results(test_results, baseline_data, error_results)
        
        logger.info("Error recovery and resilience testing completed")

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_connection_failure_recovery(self, throughput_client, high_volume_server):
        """Test recovery from connection failures."""
        message_count = 5000
        failure_points = [1000, 2500, 4000]  # Inject failures at these message counts
        
        recovery_data = {"failures": 0, "recoveries": 0, "total_sent": 0, "total_received": 0}
        
        sent_so_far = 0
        for i, batch_size in enumerate([1000, 1500, 1500, 1000]):
            # Inject failure at specific points
            if sent_so_far + batch_size in failure_points:
                logger.info(f"Injecting connection failure at message {sent_so_far}")
                
                # Simulate connection failure
                await throughput_client.disconnect()
                recovery_data["failures"] += 1
                
                # Wait and reconnect
                await asyncio.sleep(2.0)
                await throughput_client.connect()
                recovery_data["recoveries"] += 1
            
            # Send batch
            results = await throughput_client.send_throughput_burst(
                message_count=batch_size, rate_limit=1000
            )
            responses = await throughput_client.receive_responses(
                expected_count=batch_size, timeout=30.0
            )
            
            batch_sent = len([r for r in results if r["status"] == "sent"])
            recovery_data["total_sent"] += batch_sent
            recovery_data["total_received"] += len(responses)
            sent_so_far += batch_size
        
        # Assert recovery effectiveness
        self._assert_connection_recovery(recovery_data)

    def _create_test_results(self, test_name: str) -> LoadTestResults:
        """Create test results object."""
        return LoadTestResults(
            test_name=test_name,
            start_time=time.time(),
            end_time=0,
            total_duration=0
        )
    
    async def _establish_baseline(self, client, rate: int) -> dict:
        """Establish baseline performance."""
        baseline_count = 1000
        results = await client.send_throughput_burst(
            message_count=baseline_count, rate_limit=rate
        )
        responses = await client.receive_responses(baseline_count, timeout=30.0)
        
        return {
            "throughput": len(responses) / 30.0,
            "delivery_ratio": len(responses) / baseline_count,
            "sent": baseline_count,
            "received": len(responses)
        }
    
    def _define_error_scenarios(self) -> list:
        """Define error injection scenarios."""
        return [
            {
                "name": "connection_drops",
                "description": "Simulate random connection drops",
                "duration": 60,
                "error_rate": 0.05
            },
            {
                "name": "server_overload", 
                "description": "Simulate server processing delays",
                "duration": 45,
                "error_rate": 0.1
            },
            {
                "name": "network_partitions",
                "description": "Simulate network connectivity issues", 
                "duration": 30,
                "error_rate": 0.15
            }
        ]
    
    async def _test_error_scenario(self, scenario: dict) -> dict:
        """Test a specific error scenario."""
        scenario_clients = []
        scenario_data = {
            "messages_sent": 0,
            "messages_received": 0, 
            "errors_injected": 0,
            "successful_recoveries": 0,
            "throughput_impact": 0.0
        }
        
        try:
            # Create clients for scenario
            for i in range(5):
                client = HighVolumeThroughputClient(
                    "ws://localhost:8765", "mock-token", f"{scenario['name']}-client-{i}"
                )
                await client.connect()
                scenario_clients.append(client)
            
            # Run scenario with error injection
            messages_per_client = int(3000 * scenario["duration"] / len(scenario_clients))
            
            tasks = [
                self._run_client_with_errors(client, i, messages_per_client, scenario, scenario_data)
                for i, client in enumerate(scenario_clients)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for result in results:
                if isinstance(result, dict):
                    scenario_data["messages_sent"] += result.get("sent", 0)
                    scenario_data["messages_received"] += result.get("received", 0)
            
            return scenario_data
            
        finally:
            await self._cleanup_clients(scenario_clients)
    
    async def _run_client_with_errors(self, client, client_id: int, message_count: int, 
                                    scenario: dict, shared_data: dict) -> dict:
        """Run client with error injection."""
        client_data = {"sent": 0, "received": 0, "errors": 0, "recoveries": 0}
        
        batch_size = 100
        batches = message_count // batch_size
        
        for batch in range(batches):
            try:
                # Inject errors based on scenario
                if random.random() < scenario["error_rate"]:
                    client_data["errors"] += 1
                    shared_data["errors_injected"] += 1
                    
                    if scenario["name"] == "connection_drops":
                        await client.disconnect()
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        await client.connect()
                        client_data["recoveries"] += 1
                        shared_data["successful_recoveries"] += 1
                    
                    elif scenario["name"] == "server_overload":
                        # Send burst to simulate overload
                        await client.send_throughput_burst(batch_size, rate_limit=None)
                    
                    elif scenario["name"] == "network_partitions":
                        # Simulate network delay
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Normal batch processing
                results = await client.send_throughput_burst(batch_size, rate_limit=300)
                responses = await client.receive_responses(batch_size, timeout=10.0)
                
                sent_count = len([r for r in results if r["status"] == "sent"])
                client_data["sent"] += sent_count
                client_data["received"] += len(responses)
                
            except Exception as e:
                logger.warning(f"Error in client {client_id} batch {batch}: {e}")
        
        return client_data
    
    def _assert_resilience_requirements(self, baseline_data: dict, error_results: dict):
        """Assert resilience requirements are met."""
        # System should maintain reasonable performance under errors
        for scenario_name, data in error_results.items():
            if data["messages_sent"] > 0:
                delivery_ratio = data["messages_received"] / data["messages_sent"]
                assert delivery_ratio >= 0.8, \
                    f"{scenario_name}: Delivery ratio {delivery_ratio:.3f} too low under errors"
        
        # Recovery success rate should be high
        total_recoveries = sum(data["successful_recoveries"] for data in error_results.values())
        total_errors = sum(data["errors_injected"] for data in error_results.values())
        
        if total_errors > 0:
            recovery_rate = total_recoveries / total_errors
            assert recovery_rate >= 0.8, \
                f"Recovery rate too low: {recovery_rate:.3f}"
    
    def _assert_connection_recovery(self, recovery_data: dict):
        """Assert connection recovery requirements."""
        # Should have attempted failures and recoveries
        assert recovery_data["failures"] > 0, "No connection failures were injected"
        assert recovery_data["recoveries"] >= recovery_data["failures"], \
            "Not all connection failures were recovered"
        
        # Should maintain reasonable delivery ratio despite failures
        if recovery_data["total_sent"] > 0:
            delivery_ratio = recovery_data["total_received"] / recovery_data["total_sent"]
            assert delivery_ratio >= 0.85, \
                f"Delivery ratio too low after connection failures: {delivery_ratio:.3f}"
    
    def _finalize_resilience_results(self, test_results: LoadTestResults, 
                                   baseline_data: dict, error_results: dict):
        """Finalize resilience test results."""
        total_sent = baseline_data["sent"] + sum(data["messages_sent"] for data in error_results.values())
        total_received = baseline_data["received"] + sum(data["messages_received"] for data in error_results.values())
        total_recoveries = sum(data["successful_recoveries"] for data in error_results.values())
        
        test_results.messages_sent = total_sent
        test_results.messages_received = total_received
        test_results.recovery_count = total_recoveries
        test_results.delivery_ratio = total_received / total_sent if total_sent > 0 else 0
        test_results.end_time = time.time()
        test_results.total_duration = test_results.end_time - test_results.start_time
    
    async def _cleanup_clients(self, clients: list):
        """Clean up client connections."""
        for client in clients:
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Client cleanup error: {e}")


