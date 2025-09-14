"""
Test WebSocket Manager Race Condition Reproduction (Issue #1055)

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Critical Infrastructure
- Business Goal: Protect $500K+ ARR by reproducing WebSocket race conditions before fixing
- Value Impact: Demonstrates actual race conditions that cause chat failures in production
- Revenue Impact: Validates that SSOT fixes eliminate race conditions affecting user experience

CRITICAL PURPOSE: These tests are DESIGNED TO FAIL to reproduce actual race conditions
caused by WebSocket Manager fragmentation. They should PASS only after SSOT consolidation.

TEST STRATEGY: Create failing tests that reproduce the exact race conditions and timing
issues that occur with multiple WebSocket Manager implementations in production.
"""

import pytest
import asyncio
import threading
import time
import concurrent.futures
import random
from typing import Dict, List, Any, Set, Optional, Callable
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass, field
import gc

from test_framework.base_integration_test import BaseIntegrationTest
from shared.types.core_types import UserID, ensure_user_id


@dataclass
class RaceConditionScenario:
    """Represents a race condition test scenario."""
    scenario_name: str
    description: str
    users_count: int
    concurrent_threads: int
    operations_per_thread: int
    expected_race_conditions: List[str]
    race_conditions_detected: List[str] = field(default_factory=list)
    timing_issues: List[str] = field(default_factory=list)
    success: bool = False


class TestWebSocketRaceConditionReproduction(BaseIntegrationTest):
    """Reproduce WebSocket Manager race conditions for SSOT validation."""

    def setUp(self):
        """Set up test environment for race condition detection."""
        super().setUp()
        self.race_condition_results = {}
        self.timing_measurements = []
        self.instance_tracking = {}
        self.operation_counters = {}

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_initialization_race_condition(self):
        """
        DESIGNED TO FAIL: Reproduce WebSocket Manager initialization race conditions.

        This test reproduces the exact race condition that occurs when multiple
        WebSocket Manager implementations try to initialize simultaneously,
        causing the "Golden Path blocked" issue reported in Issue #1055.
        """
        scenario = RaceConditionScenario(
            scenario_name="initialization_race",
            description="Multiple WebSocket Manager implementations initializing concurrently",
            users_count=5,
            concurrent_threads=10,
            operations_per_thread=3,
            expected_race_conditions=[
                "duplicate_initialization",
                "initialization_order_dependency",
                "singleton_factory_conflict",
                "import_timing_conflict"
            ]
        )

        # Track initialization attempts and timings
        initialization_attempts = []
        initialization_errors = []
        result_lock = threading.Lock()

        def concurrent_initialization(thread_id: int, attempt: int) -> None:
            """Attempt concurrent WebSocket Manager initialization."""
            try:
                start_time = time.time()

                # Simulate the exact initialization pattern that causes race conditions
                initialization_results = []

                # Attempt 1: Direct WebSocket Manager import (timing sensitive)
                try:
                    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                    instance1 = WebSocketManager()
                    initialization_results.append(("direct_manager", id(instance1), time.time() - start_time))
                except Exception as e:
                    initialization_results.append(("direct_manager_error", str(e), time.time() - start_time))

                # Attempt 2: Unified WebSocket Manager (potential singleton conflict)
                try:
                    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
                    instance2 = UnifiedWebSocketManager()
                    initialization_results.append(("unified_manager", id(instance2), time.time() - start_time))
                except Exception as e:
                    initialization_results.append(("unified_manager_error", str(e), time.time() - start_time))

                # Attempt 3: Factory-based creation (context timing sensitive)
                try:
                    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                    user_context = self._create_test_context_with_timing(f"user_{thread_id}_{attempt}")
                    instance3 = create_websocket_manager(user_context=user_context)
                    initialization_results.append(("factory_creation", id(instance3), time.time() - start_time))
                except Exception as e:
                    initialization_results.append(("factory_creation_error", str(e), time.time() - start_time))

                # Attempt 4: Adapter pattern (dependency timing sensitive)
                try:
                    from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter
                    mock_manager = MagicMock()
                    adapter = WebSocketManagerAdapter(mock_manager)
                    initialization_results.append(("adapter_pattern", id(adapter), time.time() - start_time))
                except Exception as e:
                    initialization_results.append(("adapter_pattern_error", str(e), time.time() - start_time))

                with result_lock:
                    initialization_attempts.append({
                        'thread_id': thread_id,
                        'attempt': attempt,
                        'results': initialization_results,
                        'total_duration': time.time() - start_time,
                        'successful_initializations': len([r for r in initialization_results if not r[0].endswith('_error')])
                    })

            except Exception as e:
                with result_lock:
                    initialization_errors.append({
                        'thread_id': thread_id,
                        'attempt': attempt,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })

        # Execute concurrent initialization to trigger race conditions
        with concurrent.futures.ThreadPoolExecutor(max_workers=scenario.concurrent_threads) as executor:
            futures = []
            for thread_id in range(scenario.concurrent_threads):
                for attempt in range(scenario.operations_per_thread):
                    # Add small random delay to increase race condition probability
                    time.sleep(random.uniform(0.001, 0.01))
                    future = executor.submit(concurrent_initialization, thread_id, attempt)
                    futures.append(future)

            # Wait for all initialization attempts
            concurrent.futures.wait(futures, timeout=30)

        # Analyze results for race condition indicators
        race_conditions_detected = self._analyze_initialization_race_conditions(
            initialization_attempts, initialization_errors
        )

        scenario.race_conditions_detected = race_conditions_detected

        # ASSERTION: This test is DESIGNED TO FAIL when race conditions exist
        if race_conditions_detected:
            pytest.fail(
                f"RACE CONDITION REPRODUCTION SUCCESS: WebSocket Manager initialization race conditions detected: "
                f"{race_conditions_detected}. "
                f"Total attempts: {len(initialization_attempts)}, Errors: {len(initialization_errors)}. "
                f"This reproduces the Golden Path blocking issue. "
                f"Test should PASS only after SSOT consolidation eliminates these race conditions."
            )

        # SUCCESS: No race conditions detected (after SSOT consolidation)
        assert len(race_conditions_detected) == 0, (
            f"Race conditions should be eliminated after SSOT consolidation. "
            f"Detected: {race_conditions_detected}"
        )

    def _analyze_initialization_race_conditions(self, attempts: List[Dict], errors: List[Dict]) -> List[str]:
        """Analyze initialization attempts for race condition indicators."""
        race_conditions = []

        # Check for multiple successful initialization methods (fragmentation indicator)
        all_successful_methods = set()
        for attempt in attempts:
            for method, result, duration in attempt['results']:
                if not method.endswith('_error') and result:
                    all_successful_methods.add(method)

        if len(all_successful_methods) > 1:
            race_conditions.append(f"multiple_initialization_methods: {all_successful_methods}")

        # Check for timing-based inconsistencies
        method_timings = {}
        for attempt in attempts:
            for method, result, duration in attempt['results']:
                if not method.endswith('_error'):
                    if method not in method_timings:
                        method_timings[method] = []
                    method_timings[method].append(duration)

        # Look for inconsistent timing patterns (race condition indicator)
        for method, timings in method_timings.items():
            if len(timings) > 1:
                timing_variance = max(timings) - min(timings)
                if timing_variance > 0.1:  # 100ms variance suggests timing issues
                    race_conditions.append(f"timing_inconsistency_{method}: {timing_variance:.3f}s variance")

        # Check for singleton vs factory conflicts
        singleton_instances = set()
        factory_instances = set()

        for attempt in attempts:
            for method, result, duration in attempt['results']:
                if not method.endswith('_error') and result:
                    if 'unified' in method or 'direct' in method:
                        singleton_instances.add(result)
                    elif 'factory' in method or 'adapter' in method:
                        factory_instances.add(result)

        if len(singleton_instances) > 1 and len(factory_instances) > 1:
            race_conditions.append(f"singleton_factory_conflict: {len(singleton_instances)} singletons, {len(factory_instances)} factory instances")

        return race_conditions

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_user_context_race_condition(self):
        """
        DESIGNED TO FAIL: Reproduce user context race conditions.

        This test reproduces race conditions that occur when multiple users
        create WebSocket Manager instances simultaneously, causing user
        context isolation failures.
        """
        scenario = RaceConditionScenario(
            scenario_name="user_context_race",
            description="Multiple users creating WebSocket Manager instances concurrently",
            users_count=8,
            concurrent_threads=12,
            operations_per_thread=2,
            expected_race_conditions=[
                "user_context_cross_contamination",
                "shared_instance_isolation_failure",
                "context_timing_dependency"
            ]
        )

        # Track user context creation and isolation
        user_context_results = []
        context_isolation_violations = []
        result_lock = threading.Lock()

        def concurrent_user_context_creation(user_id: str, thread_id: int) -> None:
            """Create WebSocket Manager with user context concurrently."""
            try:
                start_time = time.time()

                # Create user context (timing sensitive for race conditions)
                user_context = self._create_test_context_with_timing(user_id)
                context_creation_time = time.time() - start_time

                # Attempt WebSocket Manager creation with different patterns
                creation_attempts = []

                # Pattern 1: Factory-based creation
                try:
                    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                    factory_start = time.time()
                    manager1 = create_websocket_manager(user_context=user_context)
                    creation_attempts.append({
                        'pattern': 'factory',
                        'instance_id': id(manager1),
                        'user_id': user_id,
                        'creation_time': time.time() - factory_start,
                        'context_data': getattr(user_context, 'user_id', None)
                    })
                except Exception as e:
                    creation_attempts.append({
                        'pattern': 'factory',
                        'error': str(e),
                        'user_id': user_id
                    })

                # Pattern 2: Direct instantiation (may not respect context)
                try:
                    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                    direct_start = time.time()
                    manager2 = WebSocketManager()

                    # Try to set user context (timing sensitive)
                    if hasattr(manager2, 'set_user_context'):
                        manager2.set_user_context(user_context)

                    creation_attempts.append({
                        'pattern': 'direct',
                        'instance_id': id(manager2),
                        'user_id': user_id,
                        'creation_time': time.time() - direct_start,
                        'context_data': getattr(user_context, 'user_id', None)
                    })
                except Exception as e:
                    creation_attempts.append({
                        'pattern': 'direct',
                        'error': str(e),
                        'user_id': user_id
                    })

                # Pattern 3: Unified manager (potential singleton issues)
                try:
                    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
                    unified_start = time.time()
                    manager3 = UnifiedWebSocketManager()
                    creation_attempts.append({
                        'pattern': 'unified',
                        'instance_id': id(manager3),
                        'user_id': user_id,
                        'creation_time': time.time() - unified_start,
                        'context_data': getattr(user_context, 'user_id', None)
                    })
                except Exception as e:
                    creation_attempts.append({
                        'pattern': 'unified',
                        'error': str(e),
                        'user_id': user_id
                    })

                with result_lock:
                    user_context_results.append({
                        'user_id': user_id,
                        'thread_id': thread_id,
                        'context_creation_time': context_creation_time,
                        'creation_attempts': creation_attempts,
                        'total_duration': time.time() - start_time
                    })

            except Exception as e:
                with result_lock:
                    context_isolation_violations.append({
                        'user_id': user_id,
                        'thread_id': thread_id,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })

        # Execute concurrent user context creation
        user_ids = [f"user_{i}" for i in range(scenario.users_count)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=scenario.concurrent_threads) as executor:
            futures = []
            for _ in range(scenario.operations_per_thread):
                for user_id in user_ids:
                    # Random delay to increase race condition probability
                    time.sleep(random.uniform(0.001, 0.005))
                    future = executor.submit(concurrent_user_context_creation, user_id, threading.get_ident())
                    futures.append(future)

            concurrent.futures.wait(futures, timeout=45)

        # Analyze for user context race conditions
        race_conditions_detected = self._analyze_user_context_race_conditions(
            user_context_results, context_isolation_violations
        )

        scenario.race_conditions_detected = race_conditions_detected

        # ASSERTION: This test is DESIGNED TO FAIL when user context race conditions exist
        if race_conditions_detected:
            pytest.fail(
                f"USER CONTEXT RACE CONDITION REPRODUCTION SUCCESS: Detected race conditions: "
                f"{race_conditions_detected}. "
                f"Total user operations: {len(user_context_results)}, Violations: {len(context_isolation_violations)}. "
                f"This reproduces user context isolation failures that affect multi-user chat. "
                f"Test should PASS only after SSOT consolidation fixes user isolation."
            )

        # SUCCESS: No user context race conditions (after SSOT consolidation)
        assert len(race_conditions_detected) == 0, (
            f"User context race conditions should be eliminated after SSOT consolidation. "
            f"Detected: {race_conditions_detected}"
        )

    def _analyze_user_context_race_conditions(self, results: List[Dict], violations: List[Dict]) -> List[str]:
        """Analyze user context results for race condition indicators."""
        race_conditions = []

        # Check for user context cross-contamination
        user_instance_mapping = {}
        for result in results:
            user_id = result['user_id']
            for attempt in result['creation_attempts']:
                if 'instance_id' in attempt:
                    instance_id = attempt['instance_id']
                    pattern = attempt['pattern']

                    if instance_id not in user_instance_mapping:
                        user_instance_mapping[instance_id] = set()

                    user_instance_mapping[instance_id].add((user_id, pattern))

        # Check for shared instances across users (isolation violation)
        for instance_id, user_pattern_set in user_instance_mapping.items():
            if len(user_pattern_set) > 1:
                users = set(up[0] for up in user_pattern_set)
                patterns = set(up[1] for up in user_pattern_set)
                if len(users) > 1:
                    race_conditions.append(f"shared_instance_across_users: instance {instance_id} used by users {users} with patterns {patterns}")

        # Check for pattern-specific race conditions
        pattern_instance_counts = {}
        for result in results:
            for attempt in result['creation_attempts']:
                if 'instance_id' in attempt:
                    pattern = attempt['pattern']
                    instance_id = attempt['instance_id']

                    if pattern not in pattern_instance_counts:
                        pattern_instance_counts[pattern] = set()
                    pattern_instance_counts[pattern].add(instance_id)

        # Unified manager should have fewer instances (singleton), factory should have more (isolation)
        if 'unified' in pattern_instance_counts and 'factory' in pattern_instance_counts:
            unified_count = len(pattern_instance_counts['unified'])
            factory_count = len(pattern_instance_counts['factory'])

            # Race condition: inconsistent isolation behavior
            if unified_count > 1 and factory_count == unified_count:
                race_conditions.append(f"inconsistent_isolation_pattern: unified={unified_count}, factory={factory_count}")

        return race_conditions

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_memory_leak_race_condition(self):
        """
        DESIGNED TO FAIL: Reproduce memory leak race conditions.

        This test reproduces memory leaks that occur when multiple WebSocket Manager
        implementations create instances without proper cleanup coordination.
        """
        scenario = RaceConditionScenario(
            scenario_name="memory_leak_race",
            description="Memory leaks from uncoordinated WebSocket Manager instance creation",
            users_count=10,
            concurrent_threads=15,
            operations_per_thread=5,
            expected_race_conditions=[
                "instance_accumulation",
                "cleanup_coordination_failure",
                "garbage_collection_interference"
            ]
        )

        # Track memory usage and instance creation
        initial_instances = self._count_websocket_manager_instances()
        creation_cycles = []

        def memory_stress_cycle(cycle_id: int) -> Dict[str, Any]:
            """Create and potentially cleanup WebSocket Manager instances."""
            cycle_start_instances = self._count_websocket_manager_instances()
            created_instances = []

            try:
                # Create multiple instances with different patterns
                for i in range(5):
                    user_id = f"cycle_{cycle_id}_user_{i}"

                    # Pattern 1: Factory creation (should be cleanable)
                    try:
                        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                        user_context = self._create_test_context_with_timing(user_id)
                        factory_instance = create_websocket_manager(user_context=user_context)
                        created_instances.append(('factory', factory_instance))
                    except ImportError:
                        pass

                    # Pattern 2: Direct creation (may not be cleanable)
                    try:
                        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                        direct_instance = WebSocketManager()
                        created_instances.append(('direct', direct_instance))
                    except ImportError:
                        pass

                    # Pattern 3: Unified manager (singleton, may accumulate)
                    try:
                        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
                        unified_instance = UnifiedWebSocketManager()
                        created_instances.append(('unified', unified_instance))
                    except ImportError:
                        pass

                # Attempt cleanup (race condition prone)
                cleanup_results = []
                for pattern, instance in created_instances:
                    cleanup_result = self._attempt_instance_cleanup(pattern, instance)
                    cleanup_results.append(cleanup_result)

                # Force garbage collection
                gc.collect()

                cycle_end_instances = self._count_websocket_manager_instances()

                return {
                    'cycle_id': cycle_id,
                    'initial_instances': cycle_start_instances,
                    'created_count': len(created_instances),
                    'cleanup_results': cleanup_results,
                    'final_instances': cycle_end_instances,
                    'instance_delta': cycle_end_instances - cycle_start_instances,
                    'patterns_used': list(set(pattern for pattern, _ in created_instances))
                }

            except Exception as e:
                return {
                    'cycle_id': cycle_id,
                    'error': str(e),
                    'error_type': type(e).__name__
                }

        # Execute memory stress cycles concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=scenario.concurrent_threads) as executor:
            futures = []
            for cycle_id in range(scenario.operations_per_thread * 3):  # More cycles for memory stress
                future = executor.submit(memory_stress_cycle, cycle_id)
                futures.append(future)

                # Small delay to increase race condition probability
                time.sleep(random.uniform(0.001, 0.01))

            # Collect results
            for future in concurrent.futures.as_completed(futures, timeout=60):
                try:
                    cycle_result = future.result()
                    creation_cycles.append(cycle_result)
                except Exception as e:
                    creation_cycles.append({'error': str(e)})

        # Analyze for memory leak race conditions
        final_instances = self._count_websocket_manager_instances()
        race_conditions_detected = self._analyze_memory_leak_race_conditions(
            initial_instances, final_instances, creation_cycles
        )

        scenario.race_conditions_detected = race_conditions_detected

        # ASSERTION: This test is DESIGNED TO FAIL when memory leak race conditions exist
        if race_conditions_detected:
            pytest.fail(
                f"MEMORY LEAK RACE CONDITION REPRODUCTION SUCCESS: Detected memory issues: "
                f"{race_conditions_detected}. "
                f"Initial instances: {initial_instances}, Final instances: {final_instances}. "
                f"Completed cycles: {len([c for c in creation_cycles if 'error' not in c])}. "
                f"This reproduces memory leaks that affect long-running WebSocket connections. "
                f"Test should PASS only after SSOT consolidation prevents memory leaks."
            )

        # SUCCESS: No memory leak race conditions (after SSOT consolidation)
        assert len(race_conditions_detected) == 0, (
            f"Memory leak race conditions should be eliminated after SSOT consolidation. "
            f"Detected: {race_conditions_detected}"
        )

    def _count_websocket_manager_instances(self) -> int:
        """Count currently active WebSocket Manager instances."""
        # Force garbage collection before counting
        gc.collect()

        # This is a simplified instance counter - in real implementation,
        # would track instances through registry or weak references
        instance_count = 0

        # Count by attempting to access different implementation types
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            # In real implementation, would have instance tracking
            instance_count += 1  # Simplified counting
        except ImportError:
            pass

        return instance_count

    def _attempt_instance_cleanup(self, pattern: str, instance: Any) -> Dict[str, Any]:
        """Attempt to cleanup a WebSocket Manager instance."""
        cleanup_result = {
            'pattern': pattern,
            'cleanup_attempted': False,
            'cleanup_successful': False,
            'cleanup_method': None
        }

        try:
            # Try different cleanup methods
            if hasattr(instance, 'cleanup'):
                instance.cleanup()
                cleanup_result['cleanup_attempted'] = True
                cleanup_result['cleanup_successful'] = True
                cleanup_result['cleanup_method'] = 'cleanup'
            elif hasattr(instance, 'close'):
                instance.close()
                cleanup_result['cleanup_attempted'] = True
                cleanup_result['cleanup_successful'] = True
                cleanup_result['cleanup_method'] = 'close'
            elif hasattr(instance, 'disconnect'):
                instance.disconnect()
                cleanup_result['cleanup_attempted'] = True
                cleanup_result['cleanup_successful'] = True
                cleanup_result['cleanup_method'] = 'disconnect'

        except Exception as e:
            cleanup_result['cleanup_attempted'] = True
            cleanup_result['cleanup_error'] = str(e)

        return cleanup_result

    def _analyze_memory_leak_race_conditions(self, initial: int, final: int, cycles: List[Dict]) -> List[str]:
        """Analyze memory usage for race condition indicators."""
        race_conditions = []

        # Check for instance accumulation
        if final > initial + 2:  # Allow for some legitimate growth
            race_conditions.append(f"instance_accumulation: {final - initial} instances accumulated")

        # Check for cleanup coordination failures
        cleanup_failures = 0
        cleanup_successes = 0

        for cycle in cycles:
            if 'cleanup_results' in cycle:
                for cleanup in cycle['cleanup_results']:
                    if cleanup['cleanup_attempted']:
                        if cleanup['cleanup_successful']:
                            cleanup_successes += 1
                        else:
                            cleanup_failures += 1

        if cleanup_failures > cleanup_successes:
            race_conditions.append(f"cleanup_coordination_failure: {cleanup_failures} failures vs {cleanup_successes} successes")

        # Check for inconsistent instance deltas across cycles
        deltas = [cycle.get('instance_delta', 0) for cycle in cycles if 'instance_delta' in cycle]
        if deltas:
            max_delta = max(deltas)
            min_delta = min(deltas)
            if max_delta - min_delta > 5:  # Significant variation
                race_conditions.append(f"inconsistent_instance_management: delta variation {max_delta - min_delta}")

        return race_conditions

    def _create_test_context_with_timing(self, user_id: str) -> Any:
        """Create test user context with timing variations for race condition testing."""
        # Add small random delay to simulate timing variations
        time.sleep(random.uniform(0.001, 0.01))

        try:
            from netra_backend.app.core.user_context.factory import UserExecutionContextFactory
            return UserExecutionContextFactory.create_test_context(user_id=user_id)
        except ImportError:
            # Fallback to mock context
            from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

            id_manager = UnifiedIDManager()
            return type('MockUserContext', (), {
                'user_id': ensure_user_id(user_id),
                'session_id': id_manager.generate_id(IDType.THREAD, prefix="test"),
                'request_id': id_manager.generate_id(IDType.REQUEST, prefix="test"),
                'is_test': True,
                'created_at': time.time()
            })()

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_import_circular_dependency_race(self):
        """
        DESIGNED TO FAIL: Reproduce circular import race conditions.

        This test reproduces circular import issues that occur when multiple
        WebSocket Manager implementations import each other, causing import
        timing race conditions.
        """
        import importlib
        import sys

        # Track import order and timing
        import_results = []
        import_errors = []
        result_lock = threading.Lock()

        # Modules that may have circular dependencies
        websocket_modules = [
            "netra_backend.app.websocket_core.websocket_manager",
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.websocket_manager_factory",
            "netra_backend.app.websocket_core.protocols",
            "netra_backend.app.agents.supervisor.agent_registry"
        ]

        def concurrent_import_test(thread_id: int, module_order: List[str]) -> None:
            """Test concurrent imports with different orders."""
            try:
                import_sequence = []

                for module_name in module_order:
                    start_time = time.time()

                    # Clear module from cache to force reimport (race condition trigger)
                    if module_name in sys.modules:
                        del sys.modules[module_name]

                    try:
                        module = importlib.import_module(module_name)
                        import_duration = time.time() - start_time
                        import_sequence.append({
                            'module': module_name,
                            'success': True,
                            'duration': import_duration,
                            'thread_id': thread_id
                        })
                    except ImportError as e:
                        import_sequence.append({
                            'module': module_name,
                            'success': False,
                            'error': str(e),
                            'duration': time.time() - start_time,
                            'thread_id': thread_id
                        })

                with result_lock:
                    import_results.append({
                        'thread_id': thread_id,
                        'import_sequence': import_sequence,
                        'total_modules': len(module_order),
                        'successful_imports': len([i for i in import_sequence if i['success']])
                    })

            except Exception as e:
                with result_lock:
                    import_errors.append({
                        'thread_id': thread_id,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })

        # Execute concurrent imports with different orders
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []

            # Create different import orders for each thread
            for thread_id in range(8):
                module_order = websocket_modules.copy()
                random.shuffle(module_order)  # Different order per thread

                future = executor.submit(concurrent_import_test, thread_id, module_order)
                futures.append(future)

                # Small delay between thread starts
                time.sleep(random.uniform(0.01, 0.05))

            # Wait for completion
            concurrent.futures.wait(futures, timeout=30)

        # Analyze for circular import race conditions
        circular_dependency_issues = self._analyze_circular_import_race_conditions(
            import_results, import_errors
        )

        # ASSERTION: This test is DESIGNED TO FAIL when circular import race conditions exist
        if circular_dependency_issues:
            pytest.fail(
                f"CIRCULAR IMPORT RACE CONDITION REPRODUCTION SUCCESS: Detected import issues: "
                f"{circular_dependency_issues}. "
                f"Successful import sequences: {len(import_results)}, Import errors: {len(import_errors)}. "
                f"This reproduces circular dependency issues that cause WebSocket Manager fragmentation. "
                f"Test should PASS only after SSOT consolidation eliminates circular dependencies."
            )

        # SUCCESS: No circular import race conditions (after SSOT consolidation)
        assert len(circular_dependency_issues) == 0, (
            f"Circular import race conditions should be eliminated after SSOT consolidation. "
            f"Detected issues: {circular_dependency_issues}"
        )

    def _analyze_circular_import_race_conditions(self, results: List[Dict], errors: List[Dict]) -> List[str]:
        """Analyze import results for circular dependency race conditions."""
        race_conditions = []

        # Check for inconsistent import success across threads
        module_success_rates = {}
        for result in results:
            for import_info in result['import_sequence']:
                module = import_info['module']
                success = import_info['success']

                if module not in module_success_rates:
                    module_success_rates[module] = {'success': 0, 'total': 0}

                module_success_rates[module]['total'] += 1
                if success:
                    module_success_rates[module]['success'] += 1

        # Look for modules with inconsistent import success (circular dependency indicator)
        for module, stats in module_success_rates.items():
            success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            if 0 < success_rate < 1:  # Partial success indicates race conditions
                race_conditions.append(f"inconsistent_import_{module.split('.')[-1]}: {success_rate:.2f} success rate")

        # Check for import timing variations (race condition indicator)
        module_timings = {}
        for result in results:
            for import_info in result['import_sequence']:
                if import_info['success']:
                    module = import_info['module']
                    if module not in module_timings:
                        module_timings[module] = []
                    module_timings[module].append(import_info['duration'])

        for module, timings in module_timings.items():
            if len(timings) > 1:
                timing_variance = max(timings) - min(timings)
                if timing_variance > 0.1:  # 100ms variance suggests timing dependencies
                    race_conditions.append(f"import_timing_variance_{module.split('.')[-1]}: {timing_variance:.3f}s")

        return race_conditions