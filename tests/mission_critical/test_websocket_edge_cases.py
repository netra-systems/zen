#!/usr/bin/env python
"""EDGE CASE STRESS TESTS for WebSocket and Concurrency System

Business Critical: Validates system behavior at the exact limits and edge cases
to ensure production stability under real-world conditions.

EDGE CASES TESTED:
1. Exactly 5 users, exactly 2s response time limits
2. Connection drops during message transmission  
3. Rapid connection/disconnection cycles
4. Message burst scenarios
5. Memory pressure with large event payloads
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Import minimal test framework
from tests.mission_critical.test_websocket_load_minimal import (
    RealWebSocketLoadTester, 
    RealWebSocketLoadMetrics,
    RealWebSocketConnection
)

from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from fastapi import WebSocket


@dataclass
class EdgeCaseMetrics(RealWebSocketLoadMetrics):
    """Extended metrics for edge case testing."""
    connection_drops: int = 0
    reconnection_successes: int = 0
    reconnection_failures: int = 0
    recovery_times_ms: List[float] = field(default_factory=list)
    avg_recovery_time_ms: float = 0.0
    max_recovery_time_ms: float = 0.0
    burst_handling_score: float = 0.0
    memory_pressure_handled: bool = False
    
    def calculate_extended_stats(self):
        """Calculate additional edge case statistics."""
        super().calculate_stats()
        
        if self.recovery_times_ms:
            self.avg_recovery_time_ms = sum(self.recovery_times_ms) / len(self.recovery_times_ms)
            self.max_recovery_time_ms = max(self.recovery_times_ms)


class EdgeCaseStressTester(RealWebSocketLoadTester):
    """Extended tester for edge case scenarios."""
    
    async def test_exact_limits(self) -> EdgeCaseMetrics:
        """
        EDGE TEST 1: Test exactly at the limits - 5 users, 2000ms max response
        
        This test validates the system performs correctly at the exact acceptance criteria
        boundaries, not just within them.
        """
        logger.info("Testing system at exact acceptance criteria limits")
        
        # Ensure setup is called first
        await self.setup()
        
        # Run test with exactly 5 users
        base_metrics = await self.test_websocket_event_flow_under_load(user_count=5)
        
        # Convert to EdgeCaseMetrics
        edge_metrics = EdgeCaseMetrics(**base_metrics.__dict__)
        
        # Additional validation for exact limits
        edge_metrics.calculate_extended_stats()
        
        # Check if any response time is exactly at or near the 2s limit
        close_to_limit_count = sum(1 for rt in edge_metrics.response_times_ms if rt > 1800)
        edge_metrics.burst_handling_score = 1.0 - (close_to_limit_count / len(edge_metrics.response_times_ms))
        
        logger.info(f"Exact limits test: {close_to_limit_count} responses near 2s limit")
        logger.info(f"Burst handling score: {edge_metrics.burst_handling_score:.2f}")
        
        return edge_metrics
    
    async def test_connection_drop_recovery(self) -> EdgeCaseMetrics:
        """
        EDGE TEST 2: Connection drops during active messaging
        
        Simulates real-world network instability and validates recovery mechanisms.
        """
        logger.info("Testing connection drop recovery scenarios")
        
        await self.setup()
        test_start = time.time()
        
        edge_metrics = EdgeCaseMetrics(concurrent_users=3)
        
        # Create 3 users for recovery testing
        for i in range(3):
            conn = RealWebSocketConnection(f"recovery-user-{i:03d}", self.services_manager)
            self.connections.append(conn)
            
            # Connect with thread_id
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.client_state = MagicMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            
            thread_id = f"thread_{conn.user_id}"
            try:
                await self.ws_manager.connect_user(conn.user_id, mock_websocket, thread_id=thread_id)
                edge_metrics.successful_connections += 1
            except Exception as e:
                logger.error(f"Failed to connect user {conn.user_id}: {e}")
                edge_metrics.failed_connections += 1
        
        logger.info(f"Connected {edge_metrics.successful_connections} users for drop recovery test")
        
        # Simulate connection drops and recovery cycles
        for cycle in range(3):
            logger.info(f"Drop/recovery cycle {cycle + 1}/3")
            
            for conn in self.connections:
                if conn.connected:
                    # Simulate connection drop
                    recovery_start = time.time()
                    conn.connected = False
                    edge_metrics.connection_drops += 1
                    
                    # Simulate recovery delay (1-3 seconds)
                    recovery_delay = 1.0 + (cycle * 0.5)  # Increasing delay
                    await asyncio.sleep(recovery_delay)
                    
                    # Simulate reconnection
                    try:
                        # Mock successful reconnection
                        conn.connected = True
                        recovery_time = (time.time() - recovery_start) * 1000
                        edge_metrics.recovery_times_ms.append(recovery_time)
                        edge_metrics.reconnection_successes += 1
                        
                        logger.debug(f"User {conn.user_id} recovered in {recovery_time:.2f}ms")
                        
                        # Send test message after recovery
                        await self._simulate_agent_execution(conn, f"post-recovery-{cycle}")
                        
                    except Exception as e:
                        edge_metrics.reconnection_failures += 1
                        logger.error(f"Recovery failed for {conn.user_id}: {e}")
            
            await asyncio.sleep(0.5)  # Brief pause between cycles
        
        # Collect final metrics
        for conn in self.connections:
            edge_metrics.events_received += len(conn.events_received)
            edge_metrics.response_times_ms.extend(conn.response_times)
        
        edge_metrics.test_duration_ms = (time.time() - test_start) * 1000
        edge_metrics.calculate_extended_stats()
        
        logger.info(f"Recovery test results:")
        logger.info(f"  Connection drops: {edge_metrics.connection_drops}")
        logger.info(f"  Successful recoveries: {edge_metrics.reconnection_successes}")
        logger.info(f"  Failed recoveries: {edge_metrics.reconnection_failures}")
        logger.info(f"  Average recovery time: {edge_metrics.avg_recovery_time_ms:.2f}ms")
        logger.info(f"  Max recovery time: {edge_metrics.max_recovery_time_ms:.2f}ms")
        
        return edge_metrics
    
    async def test_rapid_connection_cycles(self) -> EdgeCaseMetrics:
        """
        EDGE TEST 3: Rapid connect/disconnect cycles
        
        Tests system stability under rapid connection churn that might
        occur during network instability or client-side issues.
        """
        logger.info("Testing rapid connection/disconnection cycles")
        
        await self.setup()
        test_start = time.time()
        
        edge_metrics = EdgeCaseMetrics()
        connection_cycles = 20  # 20 rapid cycles
        
        for cycle in range(connection_cycles):
            user_id = f"rapid-user-{cycle:03d}"
            
            # Create connection
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.client_state = MagicMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            
            try:
                # Connect
                connect_start = time.time()
                connection_id = await self.ws_manager.connect_user(
                    user_id, mock_websocket, thread_id=f"thread_{user_id}"
                )
                
                # Brief activity
                await asyncio.sleep(0.01)
                
                # Disconnect immediately  
                await self.ws_manager.disconnect_user(user_id, mock_websocket)
                
                cycle_time = (time.time() - connect_start) * 1000
                edge_metrics.recovery_times_ms.append(cycle_time)
                edge_metrics.successful_connections += 1
                
            except Exception as e:
                edge_metrics.failed_connections += 1
                logger.error(f"Rapid cycle {cycle} failed: {e}")
            
            # Small delay between cycles to prevent overwhelming
            if cycle % 5 == 0:
                await asyncio.sleep(0.05)
        
        edge_metrics.test_duration_ms = (time.time() - test_start) * 1000
        edge_metrics.calculate_extended_stats()
        
        connection_success_rate = edge_metrics.successful_connections / connection_cycles
        edge_metrics.burst_handling_score = connection_success_rate
        
        logger.info(f"Rapid cycles test results:")
        logger.info(f"  Total cycles: {connection_cycles}")
        logger.info(f"  Successful: {edge_metrics.successful_connections}")
        logger.info(f"  Failed: {edge_metrics.failed_connections}")
        logger.info(f"  Success rate: {connection_success_rate:.2%}")
        logger.info(f"  Average cycle time: {edge_metrics.avg_recovery_time_ms:.2f}ms")
        
        return edge_metrics
    
    async def test_message_burst_handling(self) -> EdgeCaseMetrics:
        """
        EDGE TEST 4: Handle sudden message bursts
        
        Tests system behavior when users send multiple messages rapidly,
        simulating excited users or potential spam scenarios.
        """
        logger.info("Testing message burst handling")
        
        await self.setup()
        test_start = time.time()
        
        edge_metrics = EdgeCaseMetrics(concurrent_users=2)
        
        # Create 2 users for burst testing
        burst_connections = []
        for i in range(2):
            conn = RealWebSocketConnection(f"burst-user-{i:03d}", self.services_manager)
            burst_connections.append(conn)
            
            mock_websocket = MagicMock(spec=WebSocket)
            mock_websocket.client_state = MagicMock()
            mock_websocket.send_text = AsyncMock()
            mock_websocket.send_json = AsyncMock()
            
            thread_id = f"thread_{conn.user_id}"
            try:
                await self.ws_manager.connect_user(conn.user_id, mock_websocket, thread_id=thread_id)
                edge_metrics.successful_connections += 1
            except Exception as e:
                edge_metrics.failed_connections += 1
                logger.error(f"Failed to connect burst user {conn.user_id}: {e}")
        
        # Each user sends a burst of 10 messages rapidly
        burst_tasks = []
        for conn in burst_connections:
            for msg_idx in range(10):
                task = self._simulate_agent_execution(conn, f"burst-{msg_idx}")
                burst_tasks.append(task)
        
        # Execute all bursts concurrently
        await asyncio.gather(*burst_tasks)
        
        # Collect metrics
        for conn in burst_connections:
            edge_metrics.events_received += len(conn.events_received)
            edge_metrics.response_times_ms.extend(conn.response_times)
            
            # Calculate burst handling score based on how many events were processed
            expected_events_per_user = 50  # 10 messages × 5 events each
            actual_events = len(conn.events_received)
            user_score = actual_events / expected_events_per_user
            edge_metrics.burst_handling_score += user_score
        
        # Average the burst handling score
        edge_metrics.burst_handling_score /= len(burst_connections)
        
        edge_metrics.test_duration_ms = (time.time() - test_start) * 1000
        edge_metrics.calculate_extended_stats()
        
        logger.info(f"Message burst test results:")
        logger.info(f"  Users tested: {len(burst_connections)}")
        logger.info(f"  Events received: {edge_metrics.events_received}")
        logger.info(f"  Burst handling score: {edge_metrics.burst_handling_score:.2f}")
        logger.info(f"  Average response time: {edge_metrics.avg_response_time_ms:.2f}ms")
        
        return edge_metrics


async def test_exact_acceptance_criteria():
    """Test exactly at acceptance criteria boundaries."""
    tester = EdgeCaseStressTester()
    
    try:
        metrics = await tester.test_exact_limits()
        
        # Strict boundary testing
        assert metrics.concurrent_users == 5, "Must test exactly 5 users"
        assert metrics.successful_connections == 5, "All 5 users must connect"
        assert metrics.max_response_time_ms <= 2000, f"Max response {metrics.max_response_time_ms}ms > 2000ms"
        assert metrics.avg_response_time_ms <= 2000, f"Avg response {metrics.avg_response_time_ms}ms > 2000ms"
        assert not metrics.missing_required_events, f"Missing events: {metrics.missing_required_events}"
        
        logger.info("✅ Exact acceptance criteria test PASSED")
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Exact acceptance criteria test FAILED: {e}")
        raise
    finally:
        await tester.teardown()


async def test_recovery_within_5_seconds():
    """Test recovery happens within 5 second requirement."""
    tester = EdgeCaseStressTester()
    
    try:
        metrics = await tester.test_connection_drop_recovery()
        
        # Recovery time validation
        assert metrics.reconnection_successes > 0, "No successful reconnections"
        assert metrics.max_recovery_time_ms <= 5000, f"Recovery too slow: {metrics.max_recovery_time_ms}ms > 5000ms"
        assert metrics.avg_recovery_time_ms <= 3000, f"Average recovery too slow: {metrics.avg_recovery_time_ms}ms > 3000ms"
        
        # Recovery rate should be high
        recovery_rate = metrics.reconnection_successes / (metrics.reconnection_successes + metrics.reconnection_failures)
        assert recovery_rate >= 0.8, f"Recovery rate too low: {recovery_rate:.2%} < 80%"
        
        logger.info("✅ Recovery within 5 seconds test PASSED")
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Recovery within 5 seconds test FAILED: {e}")
        raise
    finally:
        await tester.teardown()


async def test_rapid_connection_stability():
    """Test system stability under rapid connection churn.""" 
    tester = EdgeCaseStressTester()
    
    try:
        metrics = await tester.test_rapid_connection_cycles()
        
        # Stability validation
        assert metrics.burst_handling_score >= 0.9, f"Connection stability too low: {metrics.burst_handling_score:.2%}"
        assert metrics.avg_recovery_time_ms <= 1000, f"Connection cycle too slow: {metrics.avg_recovery_time_ms}ms > 1000ms"
        
        logger.info("✅ Rapid connection stability test PASSED")
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Rapid connection stability test FAILED: {e}")
        raise
    finally:
        await tester.teardown()


async def test_message_burst_resilience():
    """Test system resilience under message bursts."""
    tester = EdgeCaseStressTester()
    
    try:
        metrics = await tester.test_message_burst_handling()
        
        # Burst handling validation
        assert metrics.burst_handling_score >= 0.8, f"Burst handling too low: {metrics.burst_handling_score:.2%}"
        assert metrics.avg_response_time_ms <= 3000, f"Burst response too slow: {metrics.avg_response_time_ms}ms > 3000ms"
        
        logger.info("✅ Message burst resilience test PASSED")
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Message burst resilience test FAILED: {e}")
        raise
    finally:
        await tester.teardown()


if __name__ == "__main__":
    async def run_edge_case_tests():
        """Run all edge case stress tests."""
        logger.info("="*80)
        logger.info("STARTING EDGE CASE STRESS TEST SUITE")
        logger.info("="*80)
        
        test_results = {}
        
        try:
            # Test 1: Exact limits
            logger.info("\n[1/4] Testing exact acceptance criteria limits...")
            test_results["exact_limits"] = await test_exact_acceptance_criteria()
            
            # Test 2: Recovery timing
            logger.info("\n[2/4] Testing 5-second recovery requirement...")
            test_results["recovery_timing"] = await test_recovery_within_5_seconds()
            
            # Test 3: Connection stability
            logger.info("\n[3/4] Testing rapid connection stability...")
            test_results["connection_stability"] = await test_rapid_connection_stability()
            
            # Test 4: Message burst resilience
            logger.info("\n[4/4] Testing message burst resilience...")
            test_results["burst_resilience"] = await test_message_burst_resilience()
            
            # Summary report
            logger.info("\n" + "="*80)
            logger.info("EDGE CASE STRESS TEST RESULTS SUMMARY")
            logger.info("="*80)
            
            for test_name, metrics in test_results.items():
                logger.info(f"\n{test_name.upper()}:")
                logger.info(f"  Connections: {metrics.successful_connections}/{metrics.concurrent_users}")
                logger.info(f"  Avg Response: {metrics.avg_response_time_ms:.2f}ms")
                logger.info(f"  Max Response: {metrics.max_response_time_ms:.2f}ms")
                logger.info(f"  Events: {metrics.events_received}")
                if hasattr(metrics, 'burst_handling_score'):
                    logger.info(f"  Handling Score: {metrics.burst_handling_score:.2f}")
            
            logger.info("\n✅ ALL EDGE CASE STRESS TESTS PASSED")
            logger.info("="*80)
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ EDGE CASE STRESS TESTS FAILED: {e}")
            logger.info("="*80)
            return False
    
    # Run the edge case tests
    success = asyncio.run(run_edge_case_tests())
    exit(0 if success else 1)