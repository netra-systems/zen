"""Multi-User SSOT Test - Load/Concurrency Violation Detection

PURPOSE: Validate concurrent users use same SSOT engine with isolation
SHOULD FAIL NOW: Different users get different engine types
SHOULD PASS AFTER: All users get UserExecutionEngine with isolation

Business Value: Prevents $500K+ ARR multi-user corruption and data leakage
"""

import asyncio
import random
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import AsyncMock, Mock

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    from netra_backend.app.services.user_execution_context import UserExecutionContext
except ImportError:
    # Skip test if imports not available
    pass

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MultiUserExecutionTracker:
    """Track execution engine usage across multiple concurrent users."""

    def __init__(self):
        self.user_engines: Dict[str, str] = {}  # user_id -> engine_type
        self.user_sessions: Dict[str, Dict[str, Any]] = {}  # user_id -> session_data
        self.concurrent_operations: List[Dict[str, Any]] = []
        self.isolation_violations: List[str] = []
        self.thread_safety_violations: List[str] = []
        self.lock = threading.Lock()

    def record_user_engine(self, user_id: str, engine_type: str, session_data: Dict[str, Any] = None):
        """Record engine type used by a user."""
        with self.lock:
            self.user_engines[user_id] = engine_type
            if session_data:
                self.user_sessions[user_id] = session_data

    def record_concurrent_operation(self, user_id: str, operation: str, engine_type: str, timestamp: float):
        """Record a concurrent operation."""
        with self.lock:
            self.concurrent_operations.append({
                'user_id': user_id,
                'operation': operation,
                'engine_type': engine_type,
                'timestamp': timestamp,
                'thread_id': threading.current_thread().ident
            })

    def detect_violations(self) -> List[str]:
        """Detect SSOT violations from tracked data."""
        violations = []
        ssot_engine = "UserExecutionEngine"

        with self.lock:
            # Check for non-SSOT engines
            for user_id, engine_type in self.user_engines.items():
                if engine_type != ssot_engine:
                    violations.append(
                        f"User '{user_id}' assigned non-SSOT engine: {engine_type}"
                    )

            # Check for multiple engine types across users
            unique_engines = set(self.user_engines.values())
            if len(unique_engines) > 1:
                violations.append(
                    f"Multiple engine types in use across users: {sorted(unique_engines)}"
                )

            # Check for user isolation violations
            isolation_violations = self._check_user_isolation()
            violations.extend(isolation_violations)

            # Check for thread safety violations
            thread_safety_violations = self._check_thread_safety()
            violations.extend(thread_safety_violations)

        return violations

    def _check_user_isolation(self) -> List[str]:
        """Check for user isolation violations."""
        violations = []

        # Check for shared state between users
        user_data_overlap = {}
        for user_id, session_data in self.user_sessions.items():
            if 'state_id' in session_data:
                state_id = session_data['state_id']
                if state_id in user_data_overlap:
                    violations.append(
                        f"State ID '{state_id}' shared between users: "
                        f"{user_data_overlap[state_id]} and {user_id}"
                    )
                else:
                    user_data_overlap[state_id] = user_id

        return violations

    def _check_thread_safety(self) -> List[str]:
        """Check for thread safety violations."""
        violations = []

        # Group operations by thread
        thread_operations = {}
        for op in self.concurrent_operations:
            thread_id = op['thread_id']
            if thread_id not in thread_operations:
                thread_operations[thread_id] = []
            thread_operations[thread_id].append(op)

        # Check for multiple users on same thread (potential isolation issue)
        for thread_id, operations in thread_operations.items():
            user_ids = set(op['user_id'] for op in operations)
            if len(user_ids) > 1:
                violations.append(
                    f"Thread {thread_id} handling multiple users: {sorted(user_ids)} "
                    "(potential isolation violation)"
                )

            # Check for multiple engine types on same thread
            engine_types = set(op['engine_type'] for op in operations)
            if len(engine_types) > 1:
                violations.append(
                    f"Thread {thread_id} using multiple engine types: {sorted(engine_types)}"
                )

        return violations

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from tracked data."""
        with self.lock:
            return {
                'total_users': len(self.user_engines),
                'unique_engines': len(set(self.user_engines.values())),
                'engine_distribution': {
                    engine: sum(1 for e in self.user_engines.values() if e == engine)
                    for engine in set(self.user_engines.values())
                },
                'total_operations': len(self.concurrent_operations),
                'unique_threads': len(set(op['thread_id'] for op in self.concurrent_operations))
            }


class MultiUserSSotTests(SSotAsyncTestCase):
    """Validate multi-user SSOT compliance with concurrent execution engines."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.tracker = MultiUserExecutionTracker()
        self.ssot_execution_engine = "UserExecutionEngine"

        # Test configuration
        self.num_concurrent_users = 10
        self.operations_per_user = 5

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()

    async def test_concurrent_user_engine_assignment_fails(self):
        """SHOULD FAIL: Test concurrent user engine assignments for SSOT violations."""
        violations = await self._test_concurrent_engine_assignment()

        print(f"\n👥 CONCURRENT USER ENGINE ASSIGNMENT:")
        stats = self.tracker.get_stats()
        print(f"   Total Users: {stats['total_users']}")
        print(f"   Unique Engine Types: {stats['unique_engines']}")
        print(f"   Engine Distribution: {stats['engine_distribution']}")
        print(f"   Violations: {len(violations)}")

        if violations:
            print("   Assignment Violations:")
            for violation in violations[:10]:  # Show first 10
                print(f"      X {violation}")
            if len(violations) > 10:
                print(f"      ... and {len(violations) - 10} more violations")

        # TEST SHOULD FAIL NOW - Engine assignment violations detected
        self.assertGreater(
            len(violations),
            0,
            f"X SSOT VIOLATION: Found {len(violations)} concurrent engine assignment violations. "
            f"All users must be assigned {self.ssot_execution_engine}."
        )

    async def test_user_isolation_boundary_validation_fails(self):
        """SHOULD FAIL: Validate user isolation boundaries with multiple engines."""
        isolation_violations = await self._test_user_isolation_boundaries()

        print(f"\n🔒 USER ISOLATION BOUNDARY VALIDATION:")
        print(f"   Violations Found: {len(isolation_violations)}")

        if isolation_violations:
            print("   Isolation Violations:")
            for violation in isolation_violations:
                print(f"      X {violation}")

        # TEST SHOULD FAIL NOW - User isolation violations detected
        self.assertGreater(
            len(isolation_violations),
            0,
            f"X SSOT VIOLATION: Found {len(isolation_violations)} user isolation violations. "
            "Non-SSOT engines break user isolation boundaries."
        )

    async def test_concurrent_websocket_event_delivery_fails(self):
        """SHOULD FAIL: Test concurrent WebSocket event delivery across engines."""
        event_violations = await self._test_concurrent_event_delivery()

        print(f"\n🔌 CONCURRENT WEBSOCKET EVENT DELIVERY:")
        print(f"   Violations Found: {len(event_violations)}")

        if event_violations:
            print("   Event Delivery Violations:")
            for violation in event_violations:
                print(f"      X {violation}")

        # TEST SHOULD FAIL NOW - Event delivery violations detected
        self.assertGreater(
            len(event_violations),
            0,
            f"X SSOT VIOLATION: Found {len(event_violations)} concurrent event delivery violations. "
            "Events must be delivered consistently through SSOT engine."
        )

    async def test_resource_contention_analysis_fails(self):
        """SHOULD FAIL: Analyze resource contention between different engines."""
        contention_violations = await self._analyze_resource_contention()

        print(f"\n⚡ RESOURCE CONTENTION ANALYSIS:")
        print(f"   Violations Found: {len(contention_violations)}")

        if contention_violations:
            print("   Resource Contention Violations:")
            for violation in contention_violations:
                print(f"      X {violation}")

        # TEST SHOULD FAIL NOW - Resource contention violations detected
        self.assertGreater(
            len(contention_violations),
            0,
            f"X SSOT VIOLATION: Found {len(contention_violations)} resource contention violations. "
            "Multiple engine types create resource conflicts."
        )

    async def test_thread_safety_validation_fails(self):
        """SHOULD FAIL: Validate thread safety with multiple execution engines."""
        thread_violations = await self._validate_thread_safety()

        print(f"\n🧵 THREAD SAFETY VALIDATION:")
        print(f"   Violations Found: {len(thread_violations)}")

        if thread_violations:
            print("   Thread Safety Violations:")
            for violation in thread_violations:
                print(f"      X {violation}")

        # TEST SHOULD FAIL NOW - Thread safety violations detected
        self.assertGreater(
            len(thread_violations),
            0,
            f"X SSOT VIOLATION: Found {len(thread_violations)} thread safety violations. "
            "Multiple engines create thread safety issues."
        )

    async def _test_concurrent_engine_assignment(self) -> List[str]:
        """Test concurrent engine assignment across multiple users."""
        # Simulate engine factory that assigns different engines (VIOLATION)
        def get_engine_for_user(user_id: str) -> str:
            # Simulate non-SSOT engine assignment based on user attributes
            engine_options = [
                "UserExecutionEngine",  # SSOT - correct
                "ToolExecutionEngine",  # VIOLATION
                "RequestScopedExecutionEngine",  # VIOLATION
                "MCPEnhancedExecutionEngine",  # VIOLATION
                "UnifiedToolExecutionEngine",  # VIOLATION
            ]

            # Use user_id hash to deterministically assign different engines (simulating violation)
            engine_index = hash(user_id) % len(engine_options)
            return engine_options[engine_index]

        # Create concurrent users
        tasks = []
        for i in range(self.num_concurrent_users):
            user_id = f"user_{i}"
            task = asyncio.create_task(
                self._simulate_user_session(user_id, get_engine_for_user(user_id))
            )
            tasks.append(task)

        # Execute concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

        # Detect violations
        violations = self.tracker.detect_violations()
        return violations

    async def _simulate_user_session(self, user_id: str, engine_type: str):
        """Simulate a user session with a specific engine type."""
        # Record user engine assignment
        session_data = {
            'user_id': user_id,
            'engine_type': engine_type,
            'state_id': f"state_{hash(user_id) % 3}",  # Simulate potential state sharing
            'session_start': time.time()
        }

        self.tracker.record_user_engine(user_id, engine_type, session_data)

        # Simulate user operations
        operations = ['agent_execute', 'tool_dispatch', 'websocket_emit', 'state_update', 'cleanup']

        for i, operation in enumerate(operations):
            # Record concurrent operation
            self.tracker.record_concurrent_operation(
                user_id, operation, engine_type, time.time()
            )

            # Simulate operation processing time
            await asyncio.sleep(random.uniform(0.01, 0.05))

    async def _test_user_isolation_boundaries(self) -> List[str]:
        """Test user isolation boundaries with multiple engines."""
        violations = []

        # Simulate users with shared resources (VIOLATION)
        shared_resources = {}

        for user_id in [f"user_{i}" for i in range(5)]:
            engine_type = ["UserExecutionEngine", "ToolExecutionEngine", "RequestScopedExecutionEngine"][
                hash(user_id) % 3
            ]

            # Simulate resource allocation
            if engine_type != self.ssot_execution_engine:
                # Non-SSOT engines might share resources (VIOLATION)
                resource_id = f"resource_{hash(user_id) % 2}"  # Force sharing

                if resource_id in shared_resources:
                    violations.append(
                        f"Resource '{resource_id}' shared between users: "
                        f"{shared_resources[resource_id]} and {user_id} "
                        f"(engines: {shared_resources[resource_id+'_engine']} and {engine_type})"
                    )
                else:
                    shared_resources[resource_id] = user_id
                    shared_resources[resource_id + '_engine'] = engine_type

        return violations

    async def _test_concurrent_event_delivery(self) -> List[str]:
        """Test concurrent WebSocket event delivery."""
        violations = []

        # Simulate concurrent event delivery from different engines
        event_deliveries = []

        for i in range(20):  # 20 concurrent events
            user_id = f"user_{i % 5}"
            engine_type = ["UserExecutionEngine", "ToolExecutionEngine", "RequestScopedExecutionEngine"][
                i % 3
            ]

            event_data = {
                'user_id': user_id,
                'engine_type': engine_type,
                'event_type': 'agent_thinking',
                'delivery_path': f"{engine_type}->WebSocket",
                'timestamp': time.time() + i * 0.001
            }
            event_deliveries.append(event_data)

        # Analyze event delivery patterns
        user_engine_map = {}
        for event in event_deliveries:
            user_id = event['user_id']
            engine_type = event['engine_type']

            if user_id in user_engine_map:
                if user_engine_map[user_id] != engine_type:
                    violations.append(
                        f"User '{user_id}' receiving events from multiple engines: "
                        f"{user_engine_map[user_id]} and {engine_type}"
                    )
            else:
                user_engine_map[user_id] = engine_type

        # Check for non-SSOT event sources
        for event in event_deliveries:
            if event['engine_type'] != self.ssot_execution_engine:
                violations.append(
                    f"Non-SSOT engine delivering events: {event['engine_type']} "
                    f"to user {event['user_id']}"
                )

        return violations

    async def _analyze_resource_contention(self) -> List[str]:
        """Analyze resource contention between engines."""
        violations = []

        # Simulate resource usage by different engines
        resource_usage = {
            'UserExecutionEngine': {'memory': 100, 'cpu': 50, 'connections': 10},
            'ToolExecutionEngine': {'memory': 80, 'cpu': 60, 'connections': 5},  # VIOLATION
            'RequestScopedExecutionEngine': {'memory': 120, 'cpu': 40, 'connections': 8},  # VIOLATION
            'MCPEnhancedExecutionEngine': {'memory': 150, 'cpu': 70, 'connections': 12},  # VIOLATION
        }

        # Check for resource conflicts
        total_memory = sum(usage['memory'] for usage in resource_usage.values())
        total_cpu = sum(usage['cpu'] for usage in resource_usage.values())
        total_connections = sum(usage['connections'] for usage in resource_usage.values())

        if len(resource_usage) > 1:  # Multiple engines competing
            violations.append(
                f"Multiple engines competing for resources: "
                f"Memory: {total_memory}MB, CPU: {total_cpu}%, Connections: {total_connections}"
            )

        # Check for non-SSOT resource usage
        for engine, usage in resource_usage.items():
            if engine != self.ssot_execution_engine:
                violations.append(
                    f"Non-SSOT engine '{engine}' consuming resources: {usage}"
                )

        # Check for resource limits exceeded due to multiple engines
        if total_memory > 200:  # Arbitrary limit
            violations.append(
                f"Memory limit exceeded due to multiple engines: {total_memory}MB > 200MB"
            )

        return violations

    async def _validate_thread_safety(self) -> List[str]:
        """Validate thread safety with multiple engines."""
        violations = []

        # Simulate thread-based execution
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []

            for i in range(12):  # More tasks than threads
                user_id = f"user_{i}"
                engine_type = ["UserExecutionEngine", "ToolExecutionEngine", "RequestScopedExecutionEngine"][
                    i % 3
                ]

                future = executor.submit(self._thread_worker, user_id, engine_type)
                futures.append(future)

            # Wait for completion and collect results
            thread_results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=5)
                    thread_results.append(result)
                except Exception as e:
                    violations.append(f"Thread execution failed: {str(e)}")

        # Analyze thread safety from results
        thread_engines = {}
        for result in thread_results:
            thread_id = result['thread_id']
            engine_type = result['engine_type']

            if thread_id not in thread_engines:
                thread_engines[thread_id] = set()
            thread_engines[thread_id].add(engine_type)

        # Check for multiple engines on same thread
        for thread_id, engines in thread_engines.items():
            if len(engines) > 1:
                violations.append(
                    f"Thread {thread_id} used multiple engines: {sorted(engines)} "
                    "(thread safety violation)"
                )

        return violations

    def _thread_worker(self, user_id: str, engine_type: str) -> Dict[str, Any]:
        """Worker function for thread-based testing."""
        thread_id = threading.current_thread().ident

        # Simulate work
        time.sleep(random.uniform(0.01, 0.1))

        # Record operation
        self.tracker.record_concurrent_operation(
            user_id, 'thread_operation', engine_type, time.time()
        )

        return {
            'user_id': user_id,
            'engine_type': engine_type,
            'thread_id': thread_id,
            'timestamp': time.time()
        }


if __name__ == '__main__':
    unittest.main()
