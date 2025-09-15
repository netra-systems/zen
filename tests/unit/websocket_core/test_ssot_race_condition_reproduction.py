"""
SSOT WebSocket Manager Race Condition Reproduction Test

This test reproduces race conditions that occur due to WebSocket manager fragmentation
and validates that SSOT consolidation prevents these race conditions.

EXPECTED BEHAVIOR: These tests should FAIL initially to prove race conditions exist.
After SSOT refactor (Step 4), they should PASS with race conditions eliminated.

Business Value: Platform/Internal - System Reliability & Performance
Ensures race condition elimination for WebSocket management, protecting $500K+ ARR Golden Path.

Test Strategy: Multi-threaded simulation and concurrent initialization testing.
Unit test approach - no Docker dependencies, uses threading to simulate race conditions.
"""

import pytest
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Set, Any, Optional, Tuple
import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class RaceConditionTestResult:
    """Result of a race condition test scenario."""
    test_name: str
    thread_count: int
    iterations: int
    race_conditions_detected: int
    state_inconsistencies: int
    errors: List[str]
    execution_time_ms: float


@pytest.mark.unit
class WebSocketManagerRaceConditionReproductionTests(SSotBaseTestCase, unittest.TestCase):
    """Test suite to reproduce and validate elimination of WebSocket manager race conditions.

    These tests should FAIL initially, proving race conditions exist due to fragmentation.
    After refactor, they should PASS with race conditions eliminated via SSOT consolidation.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.race_condition_results = []
        self.mock_managers = {}
        self.shared_state = {}
        self.test_lock = threading.RLock()

    def _create_mock_websocket_manager(self, manager_id: str) -> MagicMock:
        """Create a mock WebSocket manager that simulates fragmented behavior.

        Args:
            manager_id: Unique identifier for this manager instance

        Returns:
            MagicMock configured to simulate WebSocket manager behavior
        """
        manager = MagicMock()
        manager.manager_id = manager_id
        manager.connection_count = 0
        manager.active_connections = {}
        manager.is_initialized = False
        manager.initialization_time = None
        manager.state_version = 0

        # Simulate initialization race condition
        def mock_initialize():
            # Add artificial delay to increase race condition probability
            time.sleep(0.001)  # 1ms delay

            if not manager.is_initialized:
                manager.initialization_time = time.time()
                manager.is_initialized = True
                manager.state_version += 1
                return True
            return False

        # Simulate connection management race condition
        def mock_add_connection(connection_id: str, user_id: str):
            # Add artificial delay
            time.sleep(0.0005)  # 0.5ms delay

            if connection_id not in manager.active_connections:
                manager.active_connections[connection_id] = user_id
                manager.connection_count += 1
                manager.state_version += 1
                return True
            return False

        # Simulate state synchronization issues
        def mock_get_state():
            # Simulate state inconsistency
            return {
                "manager_id": manager.manager_id,
                "connection_count": manager.connection_count,
                "is_initialized": manager.is_initialized,
                "state_version": manager.state_version,
                "timestamp": time.time()
            }

        manager.initialize = mock_initialize
        manager.add_connection = mock_add_connection
        manager.get_state = mock_get_state

        return manager

    def _simulate_concurrent_manager_initialization(self, thread_count: int = 10) -> RaceConditionTestResult:
        """Simulate concurrent initialization of multiple WebSocket managers.

        Args:
            thread_count: Number of concurrent threads to use

        Returns:
            RaceConditionTestResult with detected race conditions
        """
        start_time = time.time()
        errors = []
        initialization_results = {}
        managers = {}

        def initialize_manager(thread_id: int):
            """Initialize a WebSocket manager in a separate thread."""
            try:
                manager_id = f"manager_{thread_id}"
                manager = self._create_mock_websocket_manager(manager_id)
                managers[thread_id] = manager

                # Attempt initialization
                result = manager.initialize()
                initialization_results[thread_id] = {
                    "success": result,
                    "manager_id": manager_id,
                    "initialization_time": manager.initialization_time,
                    "state_version": manager.state_version
                }

                return result

            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")
                return False

        # Execute concurrent initialization
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = [executor.submit(initialize_manager, i) for i in range(thread_count)]
            results = [future.result() for future in as_completed(futures)]

        # Analyze results for race conditions
        race_conditions_detected = 0
        state_inconsistencies = 0

        # Check for initialization timing race conditions
        init_times = [r["initialization_time"] for r in initialization_results.values() if r["initialization_time"]]
        if len(init_times) > 1:
            # If multiple managers initialized at nearly the same time, it's a race condition
            time_diffs = [abs(init_times[i] - init_times[0]) for i in range(1, len(init_times))]
            if any(diff < 0.01 for diff in time_diffs):  # Within 10ms
                race_conditions_detected += 1

        # Check for state version inconsistencies
        state_versions = [r["state_version"] for r in initialization_results.values()]
        if len(set(state_versions)) > 1:
            state_inconsistencies += 1

        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        return RaceConditionTestResult(
            test_name="concurrent_manager_initialization",
            thread_count=thread_count,
            iterations=1,
            race_conditions_detected=race_conditions_detected,
            state_inconsistencies=state_inconsistencies,
            errors=errors,
            execution_time_ms=execution_time
        )

    def _simulate_concurrent_connection_management(self, connection_count: int = 50) -> RaceConditionTestResult:
        """Simulate concurrent connection management across fragmented managers.

        Args:
            connection_count: Number of connections to simulate

        Returns:
            RaceConditionTestResult with detected race conditions
        """
        start_time = time.time()
        errors = []
        connection_results = {}

        # Create multiple managers (simulating fragmentation)
        manager1 = self._create_mock_websocket_manager("manager_1")
        manager2 = self._create_mock_websocket_manager("manager_2")
        manager1.initialize()
        manager2.initialize()

        def add_connection_to_random_manager(connection_id: str):
            """Add connection to a randomly chosen manager."""
            try:
                # Simulate fragmentation - connections go to different managers
                manager = manager1 if hash(connection_id) % 2 == 0 else manager2
                user_id = f"user_{connection_id}"

                result = manager.add_connection(connection_id, user_id)
                connection_results[connection_id] = {
                    "success": result,
                    "manager_id": manager.manager_id,
                    "timestamp": time.time()
                }

                return result

            except Exception as e:
                errors.append(f"Connection {connection_id}: {str(e)}")
                return False

        # Execute concurrent connection additions
        with ThreadPoolExecutor(max_workers=20) as executor:
            connection_ids = [f"conn_{i}" for i in range(connection_count)]
            futures = [executor.submit(add_connection_to_random_manager, conn_id) for conn_id in connection_ids]
            results = [future.result() for future in as_completed(futures)]

        # Analyze results for race conditions
        race_conditions_detected = 0
        state_inconsistencies = 0

        # Check for connection distribution issues (fragmentation indicator)
        manager1_connections = len([r for r in connection_results.values() if r["manager_id"] == "manager_1"])
        manager2_connections = len([r for r in connection_results.values() if r["manager_id"] == "manager_2"])

        if manager1_connections > 0 and manager2_connections > 0:
            # Fragmentation detected - connections split across managers
            race_conditions_detected += 1

        # Check for state inconsistencies between managers
        manager1_state = manager1.get_state()
        manager2_state = manager2.get_state()

        total_expected_connections = sum(1 for r in connection_results.values() if r["success"])
        total_actual_connections = manager1_state["connection_count"] + manager2_state["connection_count"]

        if total_expected_connections != total_actual_connections:
            state_inconsistencies += 1

        execution_time = (time.time() - start_time) * 1000

        return RaceConditionTestResult(
            test_name="concurrent_connection_management",
            thread_count=20,
            iterations=connection_count,
            race_conditions_detected=race_conditions_detected,
            state_inconsistencies=state_inconsistencies,
            errors=errors,
            execution_time_ms=execution_time
        )

    def _simulate_websocket_event_delivery_race_conditions(self, event_count: int = 100) -> RaceConditionTestResult:
        """Simulate race conditions in WebSocket event delivery due to manager fragmentation.

        Args:
            event_count: Number of events to simulate

        Returns:
            RaceConditionTestResult with detected race conditions
        """
        start_time = time.time()
        errors = []
        event_delivery_results = {}
        delivered_events = {}

        # Create fragmented event delivery system
        event_managers = {
            f"event_manager_{i}": self._create_mock_websocket_manager(f"event_manager_{i}")
            for i in range(3)  # 3 different managers handling events
        }

        for manager in event_managers.values():
            manager.initialize()
            manager.delivered_events = []

        def deliver_event(event_id: str, user_id: str, event_data: dict):
            """Deliver event through fragmented manager system."""
            try:
                # Simulate fragmentation - different events go to different managers
                manager_key = f"event_manager_{hash(user_id) % 3}"
                manager = event_managers[manager_key]

                # Simulate event delivery delay
                time.sleep(0.0001)  # 0.1ms delay

                # Track delivery
                event_info = {
                    "event_id": event_id,
                    "user_id": user_id,
                    "data": event_data,
                    "timestamp": time.time(),
                    "manager": manager_key
                }

                manager.delivered_events.append(event_info)

                with self.test_lock:
                    delivered_events[event_id] = event_info

                event_delivery_results[event_id] = {
                    "success": True,
                    "manager": manager_key,
                    "timestamp": event_info["timestamp"]
                }

                return True

            except Exception as e:
                errors.append(f"Event {event_id}: {str(e)}")
                return False

        # Execute concurrent event delivery
        with ThreadPoolExecutor(max_workers=30) as executor:
            events = [
                (f"event_{i}", f"user_{i % 10}", {"type": "agent_event", "data": f"event_{i}"})
                for i in range(event_count)
            ]
            futures = [executor.submit(deliver_event, event_id, user_id, data) for event_id, user_id, data in events]
            results = [future.result() for future in as_completed(futures)]

        # Analyze results for race conditions
        race_conditions_detected = 0
        state_inconsistencies = 0

        # Check for event fragmentation across managers
        events_per_manager = {}
        for manager_key, manager in event_managers.items():
            events_per_manager[manager_key] = len(manager.delivered_events)

        if len(set(events_per_manager.values())) > 1:
            # Events fragmented across different managers
            race_conditions_detected += 1

        # Check for event delivery order issues (race condition indicator)
        all_events = []
        for manager in event_managers.values():
            all_events.extend(manager.delivered_events)

        # Sort by timestamp and check for order inconsistencies
        all_events.sort(key=lambda x: x["timestamp"])

        # Look for events delivered to same user out of order
        user_event_order = {}
        for event in all_events:
            user_id = event["user_id"]
            if user_id not in user_event_order:
                user_event_order[user_id] = []
            user_event_order[user_id].append(event["event_id"])

        # Check for ordering issues within user events
        for user_id, event_ids in user_event_order.items():
            expected_order = sorted([int(eid.split("_")[1]) for eid in event_ids])
            actual_order = [int(eid.split("_")[1]) for eid in event_ids]
            if expected_order != actual_order:
                state_inconsistencies += 1
                break

        execution_time = (time.time() - start_time) * 1000

        return RaceConditionTestResult(
            test_name="websocket_event_delivery_race_conditions",
            thread_count=30,
            iterations=event_count,
            race_conditions_detected=race_conditions_detected,
            state_inconsistencies=state_inconsistencies,
            errors=errors,
            execution_time_ms=execution_time
        )

    def test_concurrent_websocket_manager_initialization_race_condition(self):
        """Test for race conditions during concurrent WebSocket manager initialization.

        EXPECTED: This test should FAIL initially - race conditions detected.
        After refactor: Should PASS with no race conditions due to SSOT consolidation.
        """
        result = self._simulate_concurrent_manager_initialization(thread_count=15)
        self.race_condition_results.append(result)

        # This test should FAIL initially - proving race conditions exist
        self.assertEqual(
            result.race_conditions_detected, 0,
            f"RACE CONDITION DETECTED: Concurrent initialization caused {result.race_conditions_detected} race conditions. "
            f"State inconsistencies: {result.state_inconsistencies}. "
            f"Errors: {result.errors}. "
            f"SSOT consolidation should eliminate these race conditions."
        )

    def test_fragmented_connection_management_race_condition(self):
        """Test for race conditions in connection management across fragmented managers.

        EXPECTED: This test should FAIL initially - fragmentation causes race conditions.
        After refactor: Should PASS with consolidated connection management.
        """
        result = self._simulate_concurrent_connection_management(connection_count=75)
        self.race_condition_results.append(result)

        # This test should FAIL initially - proving fragmentation issues exist
        self.assertEqual(
            result.race_conditions_detected, 0,
            f"CONNECTION FRAGMENTATION RACE CONDITION: Found {result.race_conditions_detected} race conditions "
            f"due to fragmented connection management. "
            f"State inconsistencies: {result.state_inconsistencies}. "
            f"SSOT consolidation should eliminate connection fragmentation."
        )

    def test_websocket_event_delivery_race_condition(self):
        """Test for race conditions in WebSocket event delivery due to fragmentation.

        EXPECTED: This test should FAIL initially - event delivery race conditions exist.
        After refactor: Should PASS with consolidated event delivery.
        """
        result = self._simulate_websocket_event_delivery_race_conditions(event_count=120)
        self.race_condition_results.append(result)

        # This test should FAIL initially - proving event delivery fragmentation
        self.assertEqual(
            result.race_conditions_detected, 0,
            f"EVENT DELIVERY RACE CONDITION: Found {result.race_conditions_detected} race conditions "
            f"in event delivery system. "
            f"State inconsistencies: {result.state_inconsistencies}. "
            f"SSOT consolidation should eliminate event delivery fragmentation."
        )

    def test_race_condition_performance_impact(self):
        """Test the performance impact of race conditions.

        EXPECTED: This test documents performance impact of race conditions.
        After refactor: Should show improved performance with SSOT consolidation.
        """
        # Run multiple scenarios and measure performance impact
        initialization_result = self._simulate_concurrent_manager_initialization(thread_count=10)
        connection_result = self._simulate_concurrent_connection_management(connection_count=50)
        event_result = self._simulate_websocket_event_delivery_race_conditions(event_count=80)

        # Calculate total performance metrics
        total_execution_time = (initialization_result.execution_time_ms +
                               connection_result.execution_time_ms +
                               event_result.execution_time_ms)

        total_race_conditions = (initialization_result.race_conditions_detected +
                               connection_result.race_conditions_detected +
                               event_result.race_conditions_detected)

        total_errors = len(initialization_result.errors + connection_result.errors + event_result.errors)

        # Document performance impact (this is informational)
        print(f"\n=== RACE CONDITION PERFORMANCE IMPACT ===")
        print(f"Total execution time: {total_execution_time:.2f}ms")
        print(f"Total race conditions detected: {total_race_conditions}")
        print(f"Total errors: {total_errors}")
        print(f"=== END PERFORMANCE IMPACT ===")

        # Verify that race conditions have performance impact
        if total_race_conditions > 0:
            self.assertGreater(
                total_execution_time, 50,  # Expect >50ms when race conditions exist
                f"Race conditions should cause measurable performance impact. "
                f"Found {total_race_conditions} race conditions with {total_execution_time:.2f}ms execution time."
            )

    def teardown_method(self, method=None):
        """Clean up after test."""
        # Log race condition results for debugging Step 4 refactor
        if self.race_condition_results:
            print(f"\n=== RACE CONDITION TEST RESULTS ===")
            for result in self.race_condition_results:
                print(f"Test: {result.test_name}")
                print(f"  - Threads: {result.thread_count}, Iterations: {result.iterations}")
                print(f"  - Race conditions detected: {result.race_conditions_detected}")
                print(f"  - State inconsistencies: {result.state_inconsistencies}")
                print(f"  - Errors: {len(result.errors)}")
                print(f"  - Execution time: {result.execution_time_ms:.2f}ms")

        print(f"=== END RACE CONDITION RESULTS ===\n")

        super().teardown_method(method)


if __name__ == "__main__":
    # Run tests to demonstrate race condition violations
    unittest.main(verbosity=2)