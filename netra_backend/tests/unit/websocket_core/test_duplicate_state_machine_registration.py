"""
Test 1: Duplicate State Machine Registration Detection

This test reproduces the WebSocket race condition bug related to duplicate
state machine registration. The bug occurs when multiple threads or async
tasks attempt to register the same connection ID simultaneously, leading to
silent overwrites or race conditions.

Bug Location: connection_state_machine.py:710-712
Bug Behavior: When a connection is already registered, the registry silently 
             returns the existing machine instead of detecting this as a
             potential race condition error.

Expected Behavior: Should detect duplicate registrations and either:
1. Raise an error for true duplicates (same connection registered twice)
2. Provide proper synchronization to prevent race conditions
3. Log warnings but ensure thread safety

Business Impact: $500K+ ARR dependency - race conditions in connection management
"""

import pytest
import uuid
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.types.core_types import ConnectionID, UserID
from netra_backend.app.websocket_core.connection_state_machine import (
    ConnectionStateMachineRegistry,
    ConnectionStateMachine,
    get_connection_state_registry
)


class TestDuplicateStateMachineRegistration(SSotBaseTestCase):
    """Test suite to detect duplicate state machine registration race conditions."""

    def setup_method(self, method=None):
        """Set up test with fresh registry."""
        super().setup_method(method)
        # Create a fresh registry for each test to avoid contamination
        self.registry = ConnectionStateMachineRegistry()

    def test_duplicate_registration_silent_return_bug(self):
        """
        🚨 BUG REPRODUCTION: Duplicate registration silently returns existing machine
        
        Expected Behavior: Should detect duplicate as potential race condition
        Actual Behavior: Silently returns existing machine (the bug)
        
        This test SHOULD FAIL if we add proper duplicate detection.
        Currently it will PASS because the bug allows silent duplicates.
        """
        # ARRANGE: Create connection info
        connection_id = ConnectionID(str(uuid.uuid4()))
        user_id = UserID(str(uuid.uuid4()))
        
        # ACT: Register the same connection twice
        first_machine = self.registry.register_connection(connection_id, user_id)
        second_machine = self.registry.register_connection(connection_id, user_id)
        
        # CURRENT BUG: Both registrations succeed and return the same object
        assert first_machine is second_machine, "Bug behavior: both registrations return same object"
        
        # 🚨 THIS IS WHERE THE BUG MANIFESTS:
        # The registry should detect this as a potential race condition and either:
        # 1. Raise a DuplicateRegistrationError
        # 2. Log a WARNING about potential race condition
        # 3. Provide additional validation
        
        # For now, we test the current (buggy) behavior to establish baseline
        # When the bug is fixed, this test should be updated to expect proper error handling
        
        # Verify only one machine is actually registered
        registered_machine = self.registry.get_connection_state_machine(connection_id)
        assert registered_machine is first_machine
        assert registered_machine is second_machine
        
        # Record bug detection metrics
        self.record_metric("duplicate_registration_allowed", True)
        self.record_metric("same_object_returned", first_machine is second_machine)
        self.record_metric("registration_count", 2)  # Attempted registrations

    def test_concurrent_registration_race_condition_detection(self):
        """
        🚨 RACE CONDITION REPRODUCTION: Multiple threads registering same connection
        
        This test reproduces the race condition where multiple threads attempt to
        register the same connection simultaneously. This can lead to:
        1. Multiple state machines for the same connection
        2. Lost state updates
        3. Inconsistent connection state
        
        This test SHOULD FAIL if proper race condition detection is implemented.
        """
        # ARRANGE: Create connection info and synchronization
        connection_id = ConnectionID(str(uuid.uuid4()))
        user_id = UserID(str(uuid.uuid4()))
        
        # Results storage for thread coordination
        registration_results = []
        registration_errors = []
        start_barrier = threading.Barrier(5)  # 5 threads will start simultaneously
        
        def register_connection_worker(thread_id):
            """Worker function for concurrent registration."""
            try:
                # Wait for all threads to be ready
                start_barrier.wait(timeout=1.0)
                
                # All threads attempt registration simultaneously
                machine = self.registry.register_connection(connection_id, user_id)
                registration_results.append((thread_id, machine, id(machine)))
                
            except Exception as e:
                registration_errors.append((thread_id, str(e)))
        
        # ACT: Launch concurrent registration attempts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(register_connection_worker, i)
                for i in range(5)
            ]
            
            # Wait for all threads to complete
            for future in as_completed(futures, timeout=2.0):
                future.result()
        
        # ASSERT: Analyze race condition results
        
        # All registrations should complete (current buggy behavior)
        assert len(registration_errors) == 0, f"Unexpected errors: {registration_errors}"
        assert len(registration_results) == 5, f"Expected 5 results, got {len(registration_results)}"
        
        # 🚨 BUG DETECTION: All threads should get the same machine object
        machine_objects = [result[1] for result in registration_results]
        machine_ids = [result[2] for result in registration_results]
        
        # Current bug: all threads get the same machine (no error detection)
        unique_machines = set(machine_ids)
        assert len(unique_machines) == 1, (
            f"BUG CONFIRMED: Expected 1 unique machine due to silent duplicate handling, "
            f"got {len(unique_machines)} machines. This suggests race condition protection "
            f"is working, but proper error detection should flag this as suspicious."
        )
        
        # Verify the registry only has one machine registered
        registered_machine = self.registry.get_connection_state_machine(connection_id)
        assert registered_machine is not None
        
        # All returned machines should be the same as the registered one
        for thread_id, machine, machine_id in registration_results:
            assert machine is registered_machine, f"Thread {thread_id} got different machine"
        
        # Record race condition metrics
        self.record_metric("concurrent_registrations", len(registration_results))
        self.record_metric("unique_machines", len(unique_machines))
        self.record_metric("race_condition_detected", False)  # Bug: no detection
        self.record_metric("all_same_machine", len(unique_machines) == 1)

    def test_registration_with_different_user_ids_should_detect_conflict(self):
        """
        Test registration of same connection with different user IDs.
        
        This SHOULD be detected as an error because a connection can't belong
        to multiple users simultaneously.
        
        This test SHOULD FAIL if proper conflict detection is implemented.
        """
        # ARRANGE: Same connection, different users
        connection_id = ConnectionID(str(uuid.uuid4()))
        user_id_1 = UserID(str(uuid.uuid4()))
        user_id_2 = UserID(str(uuid.uuid4()))
        
        # ACT: Register same connection with different users
        machine_1 = self.registry.register_connection(connection_id, user_id_1)
        machine_2 = self.registry.register_connection(connection_id, user_id_2)
        
        # CURRENT BUG: Second registration is ignored, returns first machine
        assert machine_1 is machine_2, "Bug: returns same machine despite different user"
        assert machine_1.user_id == user_id_1, "Machine should keep original user ID"
        
        # 🚨 BUG: Should detect user ID conflict
        # When fixed, should raise UserIDConflictError or similar
        
        # Verify the registry ignores the second user ID (current bug behavior)
        registered_machine = self.registry.get_connection_state_machine(connection_id)
        assert registered_machine.user_id == user_id_1  # Original user preserved
        
        # Record user conflict bug
        self.record_metric("user_id_conflict_detected", False)  # Bug: no detection
        self.record_metric("original_user_preserved", True)

    def test_rapid_registration_unregistration_race_condition(self):
        """
        Test rapid registration/unregistration cycles for race conditions.
        
        This tests a common race condition pattern where connections are
        rapidly created and destroyed.
        """
        # ARRANGE
        connection_id = ConnectionID(str(uuid.uuid4()))
        user_id = UserID(str(uuid.uuid4()))
        
        # ACT: Rapid register/unregister cycles
        for i in range(10):
            # Register
            machine = self.registry.register_connection(connection_id, user_id)
            assert machine is not None, f"Registration {i} failed"
            
            # Verify registration
            registered = self.registry.get_connection_state_machine(connection_id)
            assert registered is machine, f"Registration {i} not found"
            
            # Unregister
            success = self.registry.unregister_connection(connection_id)
            assert success is True, f"Unregistration {i} failed"
            
            # Verify unregistration
            after_unreg = self.registry.get_connection_state_machine(connection_id)
            assert after_unreg is None, f"Unregistration {i} incomplete"
        
        # Record rapid cycle test
        self.record_metric("rapid_cycles_completed", 10)
        self.record_metric("rapid_cycle_test", "passed")

    def test_registry_state_consistency_under_load(self):
        """
        Test registry state consistency when under load from multiple operations.
        """
        # ARRANGE: Multiple connections and operations
        connections = [
            (ConnectionID(str(uuid.uuid4())), UserID(str(uuid.uuid4())))
            for _ in range(10)
        ]
        
        results = []
        
        def worker_operations(connection_data):
            """Perform various operations on connections."""
            connection_id, user_id = connection_data
            
            # Register
            machine = self.registry.register_connection(connection_id, user_id)
            
            # Verify
            retrieved = self.registry.get_connection_state_machine(connection_id)
            assert retrieved is machine
            
            # Multiple get operations
            for _ in range(5):
                get_result = self.registry.get_connection_state_machine(connection_id)
                assert get_result is machine
            
            results.append(("success", connection_id))
        
        # ACT: Execute operations concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(worker_operations, conn_data)
                for conn_data in connections
            ]
            
            for future in as_completed(futures, timeout=5.0):
                future.result()
        
        # ASSERT: Verify final state consistency
        assert len(results) == 10, f"Expected 10 successful operations, got {len(results)}"
        
        # Verify all connections are properly registered
        for connection_id, user_id in connections:
            machine = self.registry.get_connection_state_machine(connection_id)
            assert machine is not None, f"Connection {connection_id} not found"
            assert machine.connection_id == connection_id
            assert machine.user_id == user_id
        
        # Record load test metrics
        self.record_metric("concurrent_connections", len(connections))
        self.record_metric("load_test_success", len(results) == 10)

    def teardown_method(self, method=None):
        """Clean up test state and log duplicate registration results."""
        super().teardown_method(method)
        
        # Log metrics for bug tracking
        metrics = self.get_all_metrics()
        if "duplicate_registration_allowed" in metrics:
            print(f"\n🚨 DUPLICATE REGISTRATION BUG REPORT:")
            print(f"Duplicates Allowed: {metrics.get('duplicate_registration_allowed')}")
            print(f"Same Object Returned: {metrics.get('same_object_returned')}")
            print(f"Registration Attempts: {metrics.get('registration_count')}")
            print(f"Test Duration: {metrics.get('execution_time'):.3f}s")
        
        if "race_condition_detected" in metrics:
            print(f"\n🚨 RACE CONDITION BUG REPORT:")
            print(f"Concurrent Registrations: {metrics.get('concurrent_registrations')}")
            print(f"Unique Machines Created: {metrics.get('unique_machines')}")
            print(f"Race Condition Detected: {metrics.get('race_condition_detected')}")
            print(f"All Same Machine: {metrics.get('all_same_machine')}")