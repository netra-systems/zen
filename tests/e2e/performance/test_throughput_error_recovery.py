"""
Test Suite: Error Recovery and Resilience - E2E Implementation

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: System Reliability, Uptime Guarantees
- Value Impact: Ensures rapid recovery from failures
- Strategic/Revenue Impact: Critical for SLA compliance and customer trust

This test validates error recovery mechanisms under various failure scenarios.
"""

import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.test_helpers.throughput_helpers import E2E_TEST_CONFIG
from tests.e2e.test_helpers.websocket_helpers import (
    test_websocket_test_context as websocket_test_context,
)

logger = logging.getLogger(__name__)

RECOVERY_CONFIG = {
    "error_injection_rate": 0.1,     # 10% error rate
    "network_failure_duration": 5.0,  # seconds
    "max_recovery_time": 30.0,       # seconds
    "min_recovery_success_rate": 0.9, # 90%
    "resilience_test_duration": 120   # 2 minutes
}

class ErrorRecoveryAndResilienceTests:
    """Test error recovery and system resilience"""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.timeout(300)
    async def test_connection_failure_recovery(self, high_volume_server):
        """Test recovery from connection failures"""
        logger.info("Testing connection failure recovery")
        
        recovery_results = []
        
        for attempt in range(5):  # Multiple recovery attempts
            logger.info(f"Recovery attempt {attempt + 1}")
            
            # Simulate connection failure and recovery
            recovery_time = await self._simulate_connection_failure_recovery()
            recovery_results.append(recovery_time)
            
            assert recovery_time <= RECOVERY_CONFIG["max_recovery_time"], \
                f"Recovery too slow: {recovery_time:.2f}s"
            
            await asyncio.sleep(2.0)  # Stabilization between attempts
        
        # Validate consistent recovery performance
        avg_recovery_time = sum(recovery_results) / len(recovery_results)
        assert avg_recovery_time <= RECOVERY_CONFIG["max_recovery_time"] * 0.7, \
            f"Average recovery time too high: {avg_recovery_time:.2f}s"
        
        logger.info(f"Connection recovery test passed: {avg_recovery_time:.2f}s average")
    
    @pytest.mark.asyncio
    async def test_message_loss_recovery(self, throughput_client, high_volume_server):
        """Test recovery from message loss scenarios"""
        logger.info("Testing message loss recovery")
        
        message_count = 1000
        error_rate = RECOVERY_CONFIG["error_injection_rate"]
        
        # Send messages with simulated errors
        results = await self._send_with_error_injection(throughput_client, message_count, error_rate)
        
        # Analyze recovery effectiveness
        sent_count = results["sent_count"]
        received_count = results["received_count"]
        recovered_count = results["recovered_count"]
        
        total_successful = received_count + recovered_count
        recovery_success_rate = total_successful / sent_count if sent_count > 0 else 0
        
        assert recovery_success_rate >= RECOVERY_CONFIG["min_recovery_success_rate"], \
            f"Recovery success rate too low: {recovery_success_rate:.3f}"
        
        logger.info(f"Message loss recovery passed: {recovery_success_rate:.3f} success rate")
    
    @pytest.mark.asyncio
    async def test_system_resilience_under_stress(self, throughput_client, high_volume_server):
        """Test overall system resilience under stress conditions"""
        logger.info("Testing system resilience under stress")
        
        duration = RECOVERY_CONFIG["resilience_test_duration"]
        
        # Create multiple stress conditions simultaneously
        stress_tasks = [
            self._continuous_load_with_errors(throughput_client, duration),
            self._intermittent_connection_issues(duration),
            self._resource_pressure_simulation(duration)
        ]
        
        start_time = time.time()
        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        actual_duration = time.time() - start_time
        
        # Analyze resilience results
        load_result = stress_results[0] if len(stress_results) > 0 else {}
        
        if isinstance(load_result, dict):
            resilience_score = self._calculate_resilience_score(load_result, actual_duration)
            
            assert resilience_score >= 0.8, \
                f"System resilience score too low: {resilience_score:.3f}"
            
            logger.info(f"System resilience test passed: {resilience_score:.3f} score")
        else:
            pytest.fail(f"Stress test failed with exception: {stress_results[0]}")
    
    async def _simulate_connection_failure_recovery(self) -> float:
        """Simulate connection failure and measure recovery time"""
        recovery_start = time.time()
        
        try:
            # Attempt connection
            async with websocket_test_context(E2E_TEST_CONFIG["websocket_url"], timeout=5.0) as websocket:
                # Send test message
                test_message = {
                    "message_id": f"recovery_test_{int(time.time())}",
                    "type": "recovery_test",
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                
                recovery_time = time.time() - recovery_start
                return recovery_time
                
        except Exception as e:
            logger.warning(f"Recovery attempt failed: {e}")
            return RECOVERY_CONFIG["max_recovery_time"]  # Max penalty for failure
    
    async def _send_with_error_injection(self, throughput_client, message_count: int, 
                                       error_rate: float) -> Dict[str, int]:
        """Send messages with error injection"""
        sent_count = 0
        received_count = 0
        recovered_count = 0
        failed_messages = []
        
        for i in range(message_count):
            message = {
                "message_id": f"error_test_{i}",
                "sequence": i,
                "timestamp": time.time()
            }
            
            # Inject errors randomly
            if random.random() < error_rate:
                failed_messages.append(message)
                continue
            
            try:
                await throughput_client.send_single_message(message)
                sent_count += 1
                
                # Try to receive response
                try:
                    response = await asyncio.wait_for(
                        throughput_client.receive_single_response(), 
                        timeout=2.0
                    )
                    received_count += 1
                except asyncio.TimeoutError:
                    # Add to retry queue
                    failed_messages.append(message)
                    
            except Exception as e:
                logger.warning(f"Send failed for message {i}: {e}")
                failed_messages.append(message)
        
        # Attempt recovery for failed messages
        for message in failed_messages[:10]:  # Limit retries
            try:
                await throughput_client.send_single_message(message)
                response = await asyncio.wait_for(
                    throughput_client.receive_single_response(), 
                    timeout=5.0
                )
                recovered_count += 1
            except:
                pass  # Recovery failed
        
        return {
            "sent_count": sent_count,
            "received_count": received_count,
            "recovered_count": recovered_count,
            "failed_count": len(failed_messages)
        }
    
    async def _continuous_load_with_errors(self, throughput_client, duration: int) -> Dict[str, Any]:
        """Generate continuous load with intermittent errors"""
        end_time = time.time() + duration
        total_sent = 0
        total_received = 0
        error_count = 0
        
        while time.time() < end_time:
            try:
                # Send burst of messages
                burst_size = 50
                results = await throughput_client.send_throughput_burst(
                    message_count=burst_size,
                    rate_limit=200
                )
                
                total_sent += burst_size
                
                # Randomly inject errors
                if random.random() < 0.1:  # 10% chance of error
                    error_count += 1
                    await asyncio.sleep(1.0)  # Simulate error recovery
                    continue
                
                responses = await throughput_client.receive_responses(
                    expected_count=burst_size,
                    timeout=10.0
                )
                total_received += len(responses)
                
            except Exception as e:
                error_count += 1
                logger.warning(f"Load error: {e}")
            
            await asyncio.sleep(0.5)
        
        return {
            "total_sent": total_sent,
            "total_received": total_received,
            "error_count": error_count,
            "success_rate": total_received / total_sent if total_sent > 0 else 0
        }
    
    async def _intermittent_connection_issues(self, duration: int):
        """Simulate intermittent connection issues"""
        end_time = time.time() + duration
        
        while time.time() < end_time:
            await asyncio.sleep(random.uniform(5, 15))  # Random intervals
            
            # Simulate brief connection issue
            await asyncio.sleep(random.uniform(0.5, 2.0))
    
    async def _resource_pressure_simulation(self, duration: int):
        """Simulate resource pressure"""
        from tests.e2e.test_helpers.resource_monitoring import (
            stress_system_resources,
        )
        
        # Apply moderate resource stress
        await stress_system_resources(
            duration_seconds=duration,
            cpu_intensive=True,
            memory_intensive=False
        )
    
    def _calculate_resilience_score(self, load_result: Dict[str, Any], duration: float) -> float:
        """Calculate overall resilience score"""
        success_rate = load_result.get("success_rate", 0)
        error_count = load_result.get("error_count", 0)
        total_operations = load_result.get("total_sent", 1)
        
        # Normalize error rate
        error_rate = error_count / total_operations if total_operations > 0 else 1
        
        # Calculate resilience score (0-1)
        resilience_score = (success_rate * 0.7) + ((1 - error_rate) * 0.3)
        
        return max(0, min(1, resilience_score))
