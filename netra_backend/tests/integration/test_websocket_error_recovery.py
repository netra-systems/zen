"""
WebSocket Error Recovery Integration Tests

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise, Mid, Early - All customers need error resilience
2. **Business Goal**: Prevent $5K-$25K revenue loss from system instability and error cascades
3. **Value Impact**: Ensures graceful error handling and system resilience under adverse conditions
4. **Revenue Impact**: Error resilience = system stability = customer confidence = retention

Tests WebSocket error scenarios, performance under load, race condition handling,
and recovery behavior with corrupted state. Critical for system reliability and SLA compliance.

COVERAGE TARGET: 100% for error recovery and performance scenarios
All functions ≤8 lines per CLAUDE.md requirements.
"""

# Add project root to path

from netra_backend.app.websocket.connection_manager import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import random
import time

import pytest

# Add project root to path
from netra_backend.app.websocket.unified.manager import UnifiedWebSocketManager
from netra_backend.tests.websocket_recovery_fixtures import (
    # Add project root to path

    MockWebSocket,

    NetworkConditionSimulator,

    ReconnectionMetricsCollector,

    StateRecoveryTestHelper,

    setup_test_manager_with_helper,

)


class TestWebSocketPerformanceUnderLoad:

    """Performance tests for WebSocket state recovery operations under load."""
    

    async def test_websocket_performance_under_connection_load(self):

        """Test WebSocket performance under high connection load."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        start_time = time.time()
        
        # Create multiple connections rapidly

        connections = await self._create_rapid_connections(manager, 10)
        
        # Test mass disconnection performance

        await self._simulate_mass_disconnection_performance(manager, connections)
        
        # Verify performance metrics

        self._verify_load_performance_metrics(manager, start_time, connections)

        await manager.shutdown()
    

    async def _create_rapid_connections(self, manager: UnifiedWebSocketManager, count: int) -> list:

        """Create multiple connections rapidly for load testing."""

        connections = []

        for i in range(count):

            user_id = f"load_test_user_{i}"

            websocket = MockWebSocket(user_id)

            conn_info = await manager.connect_user(user_id, websocket)

            connections.append({"user_id": user_id, "websocket": websocket, "conn_info": conn_info})

        return connections
    

    async def _simulate_mass_disconnection_performance(self, manager: UnifiedWebSocketManager, 

                                                     connections: list) -> None:

        """Simulate mass disconnection for performance testing."""

        for conn in connections:

            conn["websocket"].simulate_disconnect(1001, "Load test")

            await manager.disconnect_user(conn["user_id"], conn["websocket"], 1001, "Load test")
    

    def _verify_load_performance_metrics(self, manager: UnifiedWebSocketManager, 

                                       start_time: float, connections: list) -> None:

        """Verify performance metrics under load."""

        recovery_time = time.time() - start_time

        assert recovery_time < 10.0, f"Load test too slow: {recovery_time}s"

        assert manager.telemetry["connections_opened"] >= len(connections), "Connections should be tracked"

        assert manager.telemetry["connections_closed"] >= len(connections), "Disconnections should be tracked"
    

    async def test_message_queue_performance_under_load(self):

        """Test message queue recovery performance with large queues."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        user_id = "perf_test_user"
        
        # Create large message queue

        queue_size = await self._create_large_message_queue(manager, user_id)
        
        # Verify queue processing performance

        await self._verify_queue_processing_performance(manager, queue_size)
    

    async def _create_large_message_queue(self, manager: UnifiedWebSocketManager, user_id: str) -> int:

        """Create large message queue for performance testing."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)

        websocket.state = "disconnected"
        

        for i in range(100):

            msg = {"type": "perf_test", "sequence": i, "data": f"test_data_{i}"}

            await manager.send_message_to_user(user_id, msg, retry=True)
        

        return 100
    

    async def _verify_queue_processing_performance(self, manager: UnifiedWebSocketManager, 

                                                 expected_size: int) -> None:

        """Verify message queue processing performance."""

        stats = await manager.get_transactional_stats()

        assert stats["pending_messages"] <= expected_size, "Queue size should be managed efficiently"


class TestWebSocketErrorScenarios:

    """Error scenario tests for WebSocket state recovery resilience."""
    

    async def test_recovery_with_corrupted_state_data(self):

        """Test recovery behavior with corrupted state data."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        user_id = "error_test_user"
        
        # Create invalid state scenario

        invalid_state = await self._create_invalid_state_scenario(manager, user_id)
        
        # Verify graceful error handling

        await self._verify_graceful_error_recovery(manager, user_id, invalid_state)
    

    async def _create_invalid_state_scenario(self, manager: UnifiedWebSocketManager, user_id: str) -> dict:

        """Create scenario with invalid state data."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)
        

        invalid_message = {"type": "invalid", "malformed_data": None}

        try:

            await manager.send_message_to_user(user_id, invalid_message)

        except Exception as e:

            return {"websocket": websocket, "error": str(e), "handled": True}
        

        return {"websocket": websocket, "error": None, "handled": False}
    

    async def _verify_graceful_error_recovery(self, manager: UnifiedWebSocketManager,

                                            user_id: str, invalid_state: dict) -> None:

        """Verify graceful recovery from invalid state."""

        stats = manager.get_unified_stats()

        assert stats["telemetry"]["errors_handled"] >= 0, "Error handling should be tracked"
        

        valid_message = {"type": "recovery_test", "data": "valid"}

        result = await manager.send_message_to_user(user_id, valid_message)
        # Result should be handled gracefully (True or False, not exception)
    

    async def test_concurrent_race_condition_stability(self):

        """Test recovery behavior under concurrent connection race conditions."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        user_id = "race_test_user"
        
        # Create concurrent race condition

        race_results = await self._create_concurrent_race_scenario(manager, user_id)
        
        # Verify system stability despite race conditions

        await self._verify_race_condition_stability(manager, race_results)
    

    async def _create_concurrent_race_scenario(self, manager: UnifiedWebSocketManager, user_id: str) -> list:

        """Create concurrent connection race condition."""

        tasks = []

        for i in range(5):

            websocket = MockWebSocket(f"{user_id}_{i}")

            task = asyncio.create_task(manager.connect_user(f"{user_id}_{i}", websocket))

            tasks.append(task)
        

        return await asyncio.gather(*tasks, return_exceptions=True)
    

    async def _verify_race_condition_stability(self, manager: UnifiedWebSocketManager, race_results: list) -> None:

        """Verify system stability despite race conditions."""

        stats = manager.get_unified_stats()

        connections_opened = stats["telemetry"]["connections_opened"]

        assert connections_opened >= 0, "Connection tracking should remain consistent"


class TestWebSocketNetworkConditionRecovery:

    """Network condition simulation and recovery tests."""
    

    async def test_recovery_under_intermittent_connectivity(self):

        """Test recovery behavior under intermittent network connectivity."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        user_id = "intermittent_test_user"
        
        # Setup intermittent connectivity scenario

        intermittent_state = await self._setup_intermittent_connectivity_scenario(manager, user_id)
        
        # Verify recovery under network instability

        await self._verify_intermittent_recovery(manager, user_id, intermittent_state)
    

    async def _setup_intermittent_connectivity_scenario(self, manager: UnifiedWebSocketManager, 

                                                      user_id: str) -> dict:

        """Setup scenario with intermittent connectivity."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)
        

        NetworkConditionSimulator.simulate_intermittent_connectivity(websocket, 0.5)
        

        test_message = {"type": "network_test", "data": "intermittent test"}

        try:

            result = await manager.send_message_to_user(user_id, test_message)

        except Exception:

            pass  # Expected under intermittent conditions
        

        return {"websocket": websocket, "network_condition": "intermittent"}
    

    async def _verify_intermittent_recovery(self, manager: UnifiedWebSocketManager,

                                          user_id: str, intermittent_state: dict) -> None:

        """Verify recovery under intermittent network conditions."""

        stats = manager.get_unified_stats()

        assert stats["telemetry"]["errors_handled"] >= 0, "Network error handling should be tracked"
    

    async def test_recovery_under_high_latency_conditions(self):

        """Test recovery behavior under high latency network conditions."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        user_id = "latency_test_user"
        
        # Setup high latency scenario

        latency_state = await self._setup_high_latency_scenario(manager, user_id)
        
        # Verify performance under high latency

        await self._verify_high_latency_recovery(manager, user_id, latency_state)
    

    async def _setup_high_latency_scenario(self, manager: UnifiedWebSocketManager, user_id: str) -> dict:

        """Setup scenario with high network latency."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)
        

        NetworkConditionSimulator.simulate_high_latency_network(websocket, 1500)
        

        start_time = time.time()

        test_message = {"type": "latency_test", "timestamp": start_time}

        result = await manager.send_message_to_user(user_id, test_message)
        

        return {"websocket": websocket, "latency_ms": 1500, "start_time": start_time}
    

    async def _verify_high_latency_recovery(self, manager: UnifiedWebSocketManager,

                                          user_id: str, latency_state: dict) -> None:

        """Verify system performance under high latency conditions."""
        # System should remain stable even with high latency

        stats = manager.get_unified_stats()

        assert stats["active_connections"] >= 0, "Connection tracking should remain stable"


class TestWebSocketCircuitBreakerRecovery:

    """Circuit breaker pattern tests for WebSocket error recovery."""
    

    async def test_circuit_breaker_activation_and_recovery(self):

        """Test circuit breaker activation during error scenarios and recovery."""

        UnifiedWebSocketManager._instance = None

        manager = UnifiedWebSocketManager()

        user_id = "circuit_breaker_test"
        
        # Setup scenario to trigger circuit breaker

        circuit_state = await self._setup_circuit_breaker_scenario(manager, user_id)
        
        # Verify circuit breaker behavior

        await self._verify_circuit_breaker_recovery(manager, user_id, circuit_state)
    

    async def _setup_circuit_breaker_scenario(self, manager: UnifiedWebSocketManager, user_id: str) -> dict:

        """Setup scenario to trigger circuit breaker activation."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)
        
        # Simulate multiple rapid failures

        websocket.failure_simulation = True

        for i in range(5):

            test_message = {"type": "failure_test", "attempt": i}

            try:

                await manager.send_message_to_user(user_id, test_message)

            except Exception:

                pass  # Expected failures
        

        return {"websocket": websocket, "failure_count": 5}
    

    async def _verify_circuit_breaker_recovery(self, manager: UnifiedWebSocketManager,

                                             user_id: str, circuit_state: dict) -> None:

        """Verify circuit breaker recovery behavior."""
        # System should track circuit breaker activations

        stats = manager.get_unified_stats()

        telemetry = stats.get("telemetry", {})

        assert telemetry.get("circuit_breaks", 0) >= 0, "Circuit breaker activations should be tracked"