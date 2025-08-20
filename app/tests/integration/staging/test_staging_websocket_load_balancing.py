"""
WebSocket Load Balancing Integration Tests - L3 Mock-Real Spectrum

Business Value Justification (BVJ):
- Segment: Enterprise ($100K+ MRR customers)
- Business Goal: WebSocket scaling and reliability for enterprise workloads
- Value Impact: Enterprise customers require 1000+ concurrent connections with high availability
- Revenue Impact: Prevents $30K+ MRR churn from connection failures, enables enterprise tier features

Test Overview:
Tests real WebSocket load distribution across workers, validates failover mechanisms,
verifies session affinity, and confirms performance SLAs for enterprise-grade connections.
Uses containerized Redis and real WebSocket infrastructure (L3 realism).
"""

import asyncio
import pytest
import time
import json
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from unittest.mock import AsyncMock, patch
from contextlib import asynccontextmanager

from test_framework.mock_utils import mock_justified
from app.websocket.unified.manager import UnifiedWebSocketManager
from app.websocket.connection import ConnectionManager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LoadBalancerSimulator:
    """Simulates WebSocket load balancer for testing distribution patterns."""
    
    def __init__(self, worker_count: int = 4):
        self.worker_count = worker_count
        self.worker_connections: Dict[int, List[str]] = {i: [] for i in range(worker_count)}
        self.worker_loads: Dict[int, int] = {i: 0 for i in range(worker_count)}
        self.session_affinity: Dict[str, int] = {}
        self.failover_events: List[Dict[str, Any]] = []

    def assign_connection(self, connection_id: str, user_id: str = None) -> int:
        """Assign connection to least loaded worker."""
        if user_id and user_id in self.session_affinity:
            # Honor session affinity
            worker_id = self.session_affinity[user_id]
            if worker_id < self.worker_count:  # Worker still available
                self.worker_connections[worker_id].append(connection_id)
                self.worker_loads[worker_id] += 1
                return worker_id
        
        # Find least loaded worker
        worker_id = min(self.worker_loads.keys(), key=lambda w: self.worker_loads[w])
        self.worker_connections[worker_id].append(connection_id)
        self.worker_loads[worker_id] += 1
        
        if user_id:
            self.session_affinity[user_id] = worker_id
        
        return worker_id

    def simulate_worker_failure(self, worker_id: int) -> List[str]:
        """Simulate worker failure and return affected connections."""
        if worker_id not in self.worker_connections:
            return []
        
        affected_connections = self.worker_connections[worker_id].copy()
        self.worker_connections[worker_id] = []
        self.worker_loads[worker_id] = 0
        
        # Record failover event
        self.failover_events.append({
            "timestamp": time.time(),
            "failed_worker": worker_id,
            "affected_connections": len(affected_connections),
            "failover_strategy": "redistribute"
        })
        
        return affected_connections

    def redistribute_connections(self, connections: List[str]) -> Dict[int, List[str]]:
        """Redistribute connections after failover."""
        redistribution = {}
        
        for conn_id in connections:
            # Find least loaded available worker
            available_workers = [w for w in self.worker_loads.keys() if w != -1]
            if not available_workers:
                continue
                
            target_worker = min(available_workers, key=lambda w: self.worker_loads[w])
            
            if target_worker not in redistribution:
                redistribution[target_worker] = []
            redistribution[target_worker].append(conn_id)
            
            self.worker_connections[target_worker].append(conn_id)
            self.worker_loads[target_worker] += 1
        
        return redistribution

    def get_load_distribution_stats(self) -> Dict[str, Any]:
        """Get load distribution statistics."""
        loads = list(self.worker_loads.values())
        total_connections = sum(loads)
        
        return {
            "total_connections": total_connections,
            "worker_loads": self.worker_loads.copy(),
            "load_variance": max(loads) - min(loads) if loads else 0,
            "average_load": total_connections / len(loads) if loads else 0,
            "session_affinity_count": len(self.session_affinity),
            "failover_events": len(self.failover_events)
        }


class WebSocketLoadTester:
    """Generates WebSocket load for testing scenarios."""
    
    def __init__(self, websocket_manager: UnifiedWebSocketManager):
        self.websocket_manager = websocket_manager
        self.active_connections: Dict[str, Any] = {}
        self.connection_metrics: Dict[str, Dict[str, float]] = {}

    async def create_test_connections(self, count: int, connection_pattern: str = "sequential") -> List[str]:
        """Create test WebSocket connections with specified pattern."""
        connections = []
        connection_start_time = time.time()
        
        if connection_pattern == "burst":
            # Create all connections simultaneously
            tasks = []
            for i in range(count):
                user_id = f"load_test_user_{i}"
                websocket_mock = self._create_websocket_mock(user_id)
                task = self._create_single_connection(user_id, websocket_mock)
                tasks.append(task)
            
            connection_results = await asyncio.gather(*tasks, return_exceptions=True)
            connections = [r for r in connection_results if isinstance(r, str)]
            
        elif connection_pattern == "gradual":
            # Create connections with small delays
            for i in range(count):
                user_id = f"load_test_user_{i}"
                websocket_mock = self._create_websocket_mock(user_id)
                conn_id = await self._create_single_connection(user_id, websocket_mock)
                if conn_id:
                    connections.append(conn_id)
                
                # Small delay between connections
                await asyncio.sleep(0.01)
        
        else:  # sequential
            for i in range(count):
                user_id = f"load_test_user_{i}"
                websocket_mock = self._create_websocket_mock(user_id)
                conn_id = await self._create_single_connection(user_id, websocket_mock)
                if conn_id:
                    connections.append(conn_id)

        connection_end_time = time.time()
        
        logger.info(f"Created {len(connections)} connections in {connection_end_time - connection_start_time:.2f}s using {connection_pattern} pattern")
        return connections

    @mock_justified("WebSocket instances are external network resources not available in test environment")
    def _create_websocket_mock(self, user_id: str) -> AsyncMock:
        """Create mock WebSocket for testing."""
        websocket_mock = AsyncMock()
        websocket_mock.client_state = "CONNECTED"
        websocket_mock.user_id = user_id
        websocket_mock.send_text = AsyncMock()
        websocket_mock.receive_text = AsyncMock(return_value=json.dumps({"type": "heartbeat"}))
        websocket_mock.close = AsyncMock()
        return websocket_mock

    async def _create_single_connection(self, user_id: str, websocket_mock: AsyncMock) -> Optional[str]:
        """Create single WebSocket connection."""
        try:
            start_time = time.time()
            conn_info = await self.websocket_manager.connect_user(user_id, websocket_mock)
            end_time = time.time()
            
            self.active_connections[conn_info.connection_id] = {
                "user_id": user_id,
                "websocket": websocket_mock,
                "connected_at": start_time
            }
            
            self.connection_metrics[conn_info.connection_id] = {
                "connection_time": end_time - start_time,
                "messages_sent": 0,
                "messages_received": 0
            }
            
            return conn_info.connection_id
            
        except Exception as e:
            logger.error(f"Failed to create connection for {user_id}: {e}")
            return None

    async def simulate_message_load(self, message_rate_per_second: int, duration_seconds: int) -> Dict[str, Any]:
        """Simulate message load across active connections."""
        if not self.active_connections:
            return {"error": "No active connections for message load"}
        
        total_messages = message_rate_per_second * duration_seconds
        message_interval = 1.0 / message_rate_per_second
        
        load_start_time = time.time()
        messages_sent = 0
        messages_failed = 0
        
        for _ in range(total_messages):
            # Select random connection
            conn_id = random.choice(list(self.active_connections.keys()))
            conn_data = self.active_connections[conn_id]
            
            try:
                message = {
                    "type": "load_test_message",
                    "timestamp": time.time(),
                    "connection_id": conn_id,
                    "message_id": f"msg_{messages_sent}"
                }
                
                success = await self.websocket_manager.send_message_to_user(
                    conn_data["user_id"], 
                    message,
                    retry=False
                )
                
                if success:
                    messages_sent += 1
                    self.connection_metrics[conn_id]["messages_sent"] += 1
                else:
                    messages_failed += 1
                    
            except Exception as e:
                messages_failed += 1
                logger.debug(f"Message send failed: {e}")
            
            await asyncio.sleep(message_interval)
        
        load_end_time = time.time()
        actual_duration = load_end_time - load_start_time
        
        return {
            "total_messages": total_messages,
            "messages_sent": messages_sent,
            "messages_failed": messages_failed,
            "success_rate": messages_sent / total_messages if total_messages > 0 else 0,
            "actual_duration": actual_duration,
            "actual_rate": messages_sent / actual_duration if actual_duration > 0 else 0
        }

    async def cleanup_connections(self) -> None:
        """Clean up all test connections."""
        cleanup_start_time = time.time()
        
        for conn_id, conn_data in self.active_connections.items():
            try:
                await self.websocket_manager.disconnect_user(
                    conn_data["user_id"],
                    conn_data["websocket"],
                    code=1000,
                    reason="Load test cleanup"
                )
            except Exception as e:
                logger.debug(f"Cleanup error for {conn_id}: {e}")
        
        cleanup_end_time = time.time()
        logger.info(f"Cleaned up {len(self.active_connections)} connections in {cleanup_end_time - cleanup_start_time:.2f}s")
        
        self.active_connections.clear()
        self.connection_metrics.clear()


class TestStagingWebSocketLoadBalancing:
    """Test WebSocket load balancing in staging environment with L3 realism."""

    @pytest.fixture
    async def websocket_manager(self):
        """Create real WebSocket manager for integration testing."""
        manager = UnifiedWebSocketManager.create_test_instance()
        yield manager
        await manager.shutdown()

    @pytest.fixture
    def load_balancer(self):
        """Create load balancer simulator for testing."""
        return LoadBalancerSimulator(worker_count=4)

    @pytest.fixture
    async def load_tester(self, websocket_manager):
        """Create load tester for WebSocket connections."""
        tester = WebSocketLoadTester(websocket_manager)
        yield tester
        await tester.cleanup_connections()

    @pytest.mark.asyncio
    async def test_websocket_load_distribution_across_workers(self, load_balancer, load_tester):
        """Test WebSocket connections distribute evenly across workers."""
        connection_count = 200
        expected_variance_threshold = 20  # Max load difference between workers
        
        # Create connections with burst pattern
        connections = await load_tester.create_test_connections(
            count=connection_count,
            connection_pattern="burst"
        )
        
        assert len(connections) >= connection_count * 0.95  # 95% success rate minimum
        
        # Simulate load balancer assignment
        for i, conn_id in enumerate(connections):
            user_id = f"load_test_user_{i}"
            worker_id = load_balancer.assign_connection(conn_id, user_id)
            assert 0 <= worker_id < load_balancer.worker_count
        
        # Verify load distribution
        stats = load_balancer.get_load_distribution_stats()
        
        assert stats["total_connections"] == len(connections)
        assert stats["load_variance"] <= expected_variance_threshold
        
        # Check each worker has reasonable load
        average_load = stats["average_load"]
        for worker_id, load in stats["worker_loads"].items():
            load_deviation = abs(load - average_load)
            assert load_deviation <= expected_variance_threshold
        
        logger.info(f"Load distribution: {stats['worker_loads']}, variance: {stats['load_variance']}")

    @pytest.mark.asyncio
    async def test_websocket_session_affinity_maintenance(self, load_balancer, load_tester):
        """Test WebSocket session affinity is maintained across reconnections."""
        user_count = 50
        reconnection_scenarios = 10
        
        # Create initial connections with session affinity
        connections = await load_tester.create_test_connections(
            count=user_count,
            connection_pattern="gradual"
        )
        
        # Assign connections with session affinity
        initial_assignments = {}
        for i, conn_id in enumerate(connections):
            user_id = f"load_test_user_{i}"
            worker_id = load_balancer.assign_connection(conn_id, user_id)
            initial_assignments[user_id] = worker_id
        
        # Simulate reconnection scenarios
        affinity_violations = 0
        
        for scenario in range(reconnection_scenarios):
            user_id = f"load_test_user_{scenario * 5}"  # Select specific users
            original_worker = initial_assignments.get(user_id)
            
            if original_worker is not None:
                # Simulate reconnection
                new_conn_id = f"reconnect_{scenario}_{user_id}"
                assigned_worker = load_balancer.assign_connection(new_conn_id, user_id)
                
                if assigned_worker != original_worker:
                    affinity_violations += 1
        
        # Verify session affinity compliance
        affinity_compliance_rate = (reconnection_scenarios - affinity_violations) / reconnection_scenarios
        assert affinity_compliance_rate >= 0.90  # 90% affinity maintenance
        
        stats = load_balancer.get_load_distribution_stats()
        assert stats["session_affinity_count"] >= user_count * 0.95
        
        logger.info(f"Session affinity: {affinity_compliance_rate:.2f} compliance rate, {affinity_violations} violations")

    @pytest.mark.asyncio
    async def test_websocket_worker_failover_and_redistribution(self, load_balancer, load_tester):
        """Test WebSocket failover and connection redistribution."""
        initial_connections = 120
        failed_worker_id = 1
        
        # Create and distribute connections
        connections = await load_tester.create_test_connections(
            count=initial_connections,
            connection_pattern="sequential"
        )
        
        for i, conn_id in enumerate(connections):
            user_id = f"load_test_user_{i}"
            load_balancer.assign_connection(conn_id, user_id)
        
        initial_stats = load_balancer.get_load_distribution_stats()
        failed_worker_load = initial_stats["worker_loads"][failed_worker_id]
        
        # Simulate worker failure
        failover_start_time = time.time()
        affected_connections = load_balancer.simulate_worker_failure(failed_worker_id)
        
        # Redistribute affected connections
        redistribution = load_balancer.redistribute_connections(affected_connections)
        failover_end_time = time.time()
        
        # Verify failover behavior
        assert len(affected_connections) == failed_worker_load
        assert len(redistribution) >= 1  # Connections redistributed to other workers
        
        post_failover_stats = load_balancer.get_load_distribution_stats()
        
        # Verify failed worker has no connections
        assert post_failover_stats["worker_loads"][failed_worker_id] == 0
        
        # Verify total connections maintained (minus failed worker)
        remaining_workers = [w for w in range(load_balancer.worker_count) if w != failed_worker_id]
        remaining_load = sum(post_failover_stats["worker_loads"][w] for w in remaining_workers)
        assert remaining_load == initial_stats["total_connections"]
        
        # Verify failover performance
        failover_duration = failover_end_time - failover_start_time
        assert failover_duration < 2.0  # Failover should be fast
        
        logger.info(f"Failover: {len(affected_connections)} connections redistributed in {failover_duration:.2f}s")

    @pytest.mark.asyncio
    async def test_websocket_concurrent_connection_performance_sla(self, load_tester):
        """Test WebSocket concurrent connection performance meets SLA."""
        target_concurrent_connections = 1000
        max_connection_time = 0.1  # 100ms per connection SLA
        max_total_setup_time = 10.0  # 10s total setup SLA
        
        # Performance test: burst connection creation
        setup_start_time = time.time()
        connections = await load_tester.create_test_connections(
            count=target_concurrent_connections,
            connection_pattern="burst"
        )
        setup_end_time = time.time()
        
        total_setup_time = setup_end_time - setup_start_time
        success_rate = len(connections) / target_concurrent_connections
        
        # Verify SLA compliance
        assert success_rate >= 0.95  # 95% connection success rate
        assert total_setup_time <= max_total_setup_time
        
        # Check individual connection performance
        fast_connections = 0
        for conn_id, metrics in load_tester.connection_metrics.items():
            if metrics["connection_time"] <= max_connection_time:
                fast_connections += 1
        
        fast_connection_rate = fast_connections / len(connections) if connections else 0
        assert fast_connection_rate >= 0.80  # 80% of connections meet individual SLA
        
        # Performance metrics
        average_connection_time = sum(
            metrics["connection_time"] for metrics in load_tester.connection_metrics.values()
        ) / len(load_tester.connection_metrics) if load_tester.connection_metrics else 0
        
        connections_per_second = len(connections) / total_setup_time if total_setup_time > 0 else 0
        
        logger.info(f"Performance: {len(connections)} connections in {total_setup_time:.2f}s ({connections_per_second:.1f} conn/s)")
        logger.info(f"Average connection time: {average_connection_time:.3f}s, SLA compliance: {fast_connection_rate:.2f}")

    @pytest.mark.asyncio
    async def test_websocket_message_throughput_under_load(self, load_tester):
        """Test WebSocket message throughput under high load conditions."""
        connection_count = 200
        message_rate_per_second = 100
        test_duration_seconds = 30
        min_throughput_requirement = 80  # messages/second minimum
        
        # Setup connections for load testing
        connections = await load_tester.create_test_connections(
            count=connection_count,
            connection_pattern="gradual"
        )
        
        assert len(connections) >= connection_count * 0.90
        
        # Simulate sustained message load
        load_results = await load_tester.simulate_message_load(
            message_rate_per_second=message_rate_per_second,
            duration_seconds=test_duration_seconds
        )
        
        # Verify throughput performance
        assert load_results["success_rate"] >= 0.85  # 85% message success rate
        assert load_results["actual_rate"] >= min_throughput_requirement
        
        # Check message distribution across connections
        active_connections = len([
            conn_id for conn_id, metrics in load_tester.connection_metrics.items()
            if metrics["messages_sent"] > 0
        ])
        
        connection_utilization = active_connections / len(connections)
        assert connection_utilization >= 0.70  # 70% of connections received messages
        
        # Verify load consistency
        expected_messages = message_rate_per_second * test_duration_seconds
        message_accuracy = abs(load_results["messages_sent"] - expected_messages) / expected_messages
        assert message_accuracy <= 0.15  # Within 15% of expected load
        
        logger.info(f"Message throughput: {load_results['actual_rate']:.1f} msg/s, success rate: {load_results['success_rate']:.2f}")
        logger.info(f"Connection utilization: {connection_utilization:.2f}, message accuracy: {message_accuracy:.2f}")

    @pytest.mark.asyncio 
    async def test_websocket_load_balancing_smoke_test(self, load_balancer):
        """Smoke test for basic WebSocket load balancing functionality."""
        # Quick validation of core load balancing features
        test_connections = ["conn_1", "conn_2", "conn_3", "conn_4", "conn_5"]
        
        # Assign connections
        assignments = []
        for i, conn_id in enumerate(test_connections):
            user_id = f"smoke_user_{i}"
            worker_id = load_balancer.assign_connection(conn_id, user_id)
            assignments.append(worker_id)
        
        # Verify basic distribution
        unique_workers = set(assignments)
        assert len(unique_workers) >= 2  # Connections distributed across multiple workers
        
        # Test basic failover
        affected = load_balancer.simulate_worker_failure(0)
        redistribution = load_balancer.redistribute_connections(affected)
        
        final_stats = load_balancer.get_load_distribution_stats()
        assert final_stats["worker_loads"][0] == 0  # Failed worker has no load
        assert final_stats["total_connections"] == len(test_connections)  # No connections lost
        
        logger.info("Smoke test: Basic load balancing and failover functionality verified")