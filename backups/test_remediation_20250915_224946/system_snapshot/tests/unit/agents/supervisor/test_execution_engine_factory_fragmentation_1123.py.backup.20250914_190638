"""Phase 1 Unit Tests: Execution Engine Factory Fragmentation Reproduction (Issue #1123)

CRITICAL BUSINESS VALUE: These tests reproduce factory fragmentation issues that block
the Golden Path user flow (login → AI response), protecting $500K+ ARR functionality.

EXPECTED BEHAVIOR: All tests in this file should INITIALLY FAIL to demonstrate
the factory fragmentation problems. They will pass after SSOT consolidation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure factory pattern reliability and SSOT compliance
- Value Impact: Prevents user isolation failures, memory leaks, and WebSocket 1011 errors
- Strategic Impact: Foundation for $500K+ ARR multi-user chat functionality

Test Philosophy:
- FAILING TESTS FIRST: These tests reproduce real issues before fixing them
- REAL PROBLEM REPRODUCTION: Each test demonstrates actual fragmentation issues
- SSOT VALIDATION: Tests validate single canonical factory implementation
- USER ISOLATION: Tests ensure complete user context isolation
- GOLDEN PATH PROTECTION: Tests protect end-to-end user value delivery
"""

import asyncio
import gc
import inspect
import importlib
import os
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import patch

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestExecutionEngineFactoryFragmentation1123(SSotAsyncTestCase):
    """Phase 1 Unit Tests: Factory Fragmentation Reproduction

    These tests are designed to FAIL initially to demonstrate the factory
    fragmentation issues blocking the Golden Path. They will pass after
    SSOT consolidation fixes are implemented.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_users = []
        self.factory_instances = []
        self.created_contexts = []

        # Track factory creation metrics
        self.factory_creation_times = []
        self.memory_usage_before = []
        self.memory_usage_after = []

        # Expected canonical factory location
        self.canonical_factory_module = "netra_backend.app.agents.supervisor.execution_engine_factory"
        self.canonical_factory_class = "ExecutionEngineFactory"

    async def asyncTearDown(self):
        """Clean up test resources."""
        # Cleanup any created contexts and factories
        for context in self.created_contexts:
            try:
                if hasattr(context, 'cleanup'):
                    await context.cleanup()
            except Exception:
                pass

        for factory in self.factory_instances:
            try:
                if hasattr(factory, 'shutdown'):
                    await factory.shutdown()
            except Exception:
                pass

        # Force garbage collection
        gc.collect()
        await super().asyncTearDown()

    # === FACTORY SSOT COMPLIANCE VALIDATION TESTS ===

    async def test_execution_engine_factory_ssot_compliance_fragmentation_detection(self):
        """FAILING TEST: Detect multiple ExecutionEngineFactory implementations

        BVJ: Platform - Ensures SSOT compliance prevents factory fragmentation
        EXPECTED: FAIL - Multiple factory implementations should be detected
        ISSUE: Factory implementations scattered across 4+ modules causing conflicts
        """
        factory_implementations = []

        # Search for ExecutionEngineFactory implementations across the codebase
        factory_modules_to_check = [
            "netra_backend.app.agents.supervisor.execution_engine_factory",
            "netra_backend.app.agents.execution_engine_unified_factory",
            "netra_backend.app.core.managers.execution_engine_factory",
            "test_framework.fixtures.execution_engine_factory_fixtures"
        ]

        for module_name in factory_modules_to_check:
            try:
                module = importlib.import_module(module_name)

                # Look for ExecutionEngineFactory classes
                for name in dir(module):
                    obj = getattr(module, name)
                    if (inspect.isclass(obj) and
                        ('ExecutionEngineFactory' in name or
                         hasattr(obj, 'create_execution_engine') or
                         hasattr(obj, 'create_for_user'))):
                        factory_implementations.append({
                            'module': module_name,
                            'class': name,
                            'object': obj
                        })

            except ImportError:
                # Module doesn't exist - that's fine
                continue

        # ASSERTION THAT SHOULD FAIL: Only one canonical factory should exist
        detected_implementations = [f"{impl['module']}.{impl['class']}" for impl in factory_implementations]
        self.assertEqual(
            len(factory_implementations), 1,
            f"SSOT VIOLATION: Found {len(factory_implementations)} factory implementations. "
            f"Should have only 1 canonical ExecutionEngineFactory. "
            f"Detected: {detected_implementations}"
        )

        # ASSERTION THAT SHOULD FAIL: All should be the same canonical class
        if factory_implementations:
            canonical_factory = factory_implementations[0]['object']
            for impl in factory_implementations[1:]:
                self.assertIs(
                    impl['object'], canonical_factory,
                    f"SSOT VIOLATION: {impl['module']}.{impl['class']} "
                    f"is not the same as canonical factory. "
                    f"Multiple distinct factory classes exist."
                )

    async def test_factory_import_path_consolidation_fragmentation(self):
        """FAILING TEST: Validate all import paths resolve to same canonical factory

        BVJ: Platform - Ensures import path consistency prevents race conditions
        EXPECTED: FAIL - Different import paths lead to different factory classes
        ISSUE: Import fragmentation causes factory initialization conflicts
        """
        import_paths_to_test = [
            ("netra_backend.app.agents.supervisor.execution_engine_factory", "ExecutionEngineFactory"),
            ("netra_backend.app.agents.execution_engine_unified_factory", "UnifiedExecutionEngineFactory"),
            ("netra_backend.app.core.managers.execution_engine_factory", "ExecutionEngineFactory"),
        ]

        imported_factories = {}

        for module_path, class_name in import_paths_to_test:
            try:
                module = importlib.import_module(module_path)
                factory_class = getattr(module, class_name, None)

                if factory_class and inspect.isclass(factory_class):
                    imported_factories[f"{module_path}.{class_name}"] = factory_class

            except ImportError as e:
                # Track import failures
                imported_factories[f"{module_path}.{class_name}"] = f"ImportError: {e}"

        # Extract actual factory classes (not error messages)
        actual_factory_classes = [
            factory for factory in imported_factories.values()
            if inspect.isclass(factory)
        ]

        # ASSERTION THAT SHOULD FAIL: All imports should resolve to the same class
        if len(actual_factory_classes) > 1:
            canonical_factory = actual_factory_classes[0]
            for i, factory_class in enumerate(actual_factory_classes[1:], 1):
                self.assertIs(
                    factory_class, canonical_factory,
                    f"IMPORT FRAGMENTATION: Factory class from import path {i+1} "
                    f"({factory_class}) is not the same as canonical factory "
                    f"({canonical_factory}). Import paths resolve to different classes."
                )

        # ASSERTION THAT SHOULD FAIL: Should have successful imports
        import_failures = [
            path for path, result in imported_factories.items()
            if isinstance(result, str) and "ImportError" in result
        ]

        self.assertEqual(
            len(import_failures), 0,
            f"IMPORT FRAGMENTATION: Failed imports detected: {import_failures}. "
            f"All factory import paths should resolve successfully."
        )

    # === USER ISOLATION VALIDATION TESTS ===

    async def test_concurrent_user_factory_isolation_contamination(self):
        """FAILING TEST: Reproduce user state contamination in concurrent factory usage

        BVJ: All Segments - Ensures user data isolation for HIPAA/SOC2 compliance
        EXPECTED: FAIL - User contexts contaminate each other in concurrent usage
        ISSUE: Shared factory state causes cross-user data leakage
        """
        # Import the execution engine factory
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory,
                configure_execution_engine_factory
            )
        except ImportError:
            self.fail("Cannot import ExecutionEngineFactory - SSOT consolidation incomplete")

        # Create test user contexts
        num_concurrent_users = 5
        user_contexts = []

        for i in range(num_concurrent_users):
            context = UserExecutionContext(
                user_id=f"test_user_{i}",
                run_id=f"test_run_{i}_{int(time.time() * 1000)}",
                session_id=f"test_session_{i}",
                request_id=f"test_request_{i}"
            )
            user_contexts.append(context)
            self.created_contexts.append(context)

        # Create factory without WebSocket bridge (test mode)
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)

        # Create execution engines for all users concurrently
        created_engines = []

        async def create_user_engine(user_context):
            """Create engine for a specific user."""
            engine = await factory.create_for_user(user_context)
            return engine, user_context

        # Execute concurrent engine creation
        tasks = [create_user_engine(ctx) for ctx in user_contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successfully created engines
        for result in results:
            if isinstance(result, tuple):
                engine, context = result
                created_engines.append((engine, context))

        # ASSERTION THAT SHOULD FAIL: Each engine should have isolated user context
        for i, (engine1, context1) in enumerate(created_engines):
            for j, (engine2, context2) in enumerate(created_engines):
                if i != j:
                    # Engines should not share user context
                    engine1_context = engine1.get_user_context()
                    engine2_context = engine2.get_user_context()

                    # CRITICAL ISOLATION CHECK: User IDs must not contaminate
                    self.assertNotEqual(
                        engine1_context.user_id, engine2_context.user_id,
                        f"USER ISOLATION VIOLATION: Engine {i} and Engine {j} "
                        f"have the same user_id ({engine1_context.user_id}). "
                        f"Cross-user contamination detected."
                    )

                    # CRITICAL ISOLATION CHECK: Run IDs must be unique
                    self.assertNotEqual(
                        engine1_context.run_id, engine2_context.run_id,
                        f"USER ISOLATION VIOLATION: Engine {i} and Engine {j} "
                        f"have the same run_id ({engine1_context.run_id}). "
                        f"Run context contamination detected."
                    )

        # Cleanup engines
        for engine, _ in created_engines:
            try:
                await factory.cleanup_engine(engine)
            except Exception:
                pass

    async def test_factory_memory_leak_prevention_reproduction(self):
        """FAILING TEST: Reproduce memory leaks from improper factory cleanup

        BVJ: Platform - Ensures factory cleanup prevents memory exhaustion
        EXPECTED: FAIL - Memory usage grows without bound due to cleanup issues
        ISSUE: Factory instances accumulate without proper cleanup
        """
        # Import the execution engine factory
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
        except ImportError:
            self.fail("Cannot import ExecutionEngineFactory - SSOT consolidation incomplete")

        # Measure initial memory baseline
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create and destroy many factory instances
        num_iterations = 10
        max_memory_growth = 50  # MB - reasonable limit

        for iteration in range(num_iterations):
            # Create factory with test configuration
            factory = ExecutionEngineFactory(websocket_bridge=None)
            self.factory_instances.append(factory)

            # Create multiple user contexts for this factory
            user_contexts = []
            for i in range(3):  # 3 users per factory
                context = UserExecutionContext(
                    user_id=f"memory_test_user_{iteration}_{i}",
                    run_id=f"memory_test_run_{iteration}_{i}_{int(time.time() * 1000)}",
                    session_id=f"memory_test_session_{iteration}_{i}",
                    request_id=f"memory_test_request_{iteration}_{i}"
                )
                user_contexts.append(context)
                self.created_contexts.append(context)

            # Create execution engines
            engines = []
            for context in user_contexts:
                try:
                    engine = await factory.create_for_user(context)
                    engines.append(engine)
                except Exception:
                    pass  # Continue test even if some engines fail

            # Cleanup engines
            for engine in engines:
                try:
                    await factory.cleanup_engine(engine)
                except Exception:
                    pass

            # Attempt to cleanup factory
            try:
                await factory.shutdown()
            except Exception:
                pass

            # Force garbage collection
            gc.collect()

            # Measure memory after this iteration
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = current_memory - initial_memory

            self.memory_usage_before.append(initial_memory)
            self.memory_usage_after.append(current_memory)

        # ASSERTION THAT SHOULD FAIL: Memory growth should be bounded
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_growth = final_memory - initial_memory

        self.assertLess(
            total_memory_growth, max_memory_growth,
            f"MEMORY LEAK DETECTED: Factory operations caused {total_memory_growth:.1f}MB "
            f"memory growth (limit: {max_memory_growth}MB). "
            f"Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB. "
            f"Factory cleanup is not releasing memory properly."
        )

    # === FACTORY INITIALIZATION RACE CONDITIONS TESTS ===

    async def test_factory_initialization_race_conditions_reproduction(self):
        """FAILING TEST: Reproduce factory initialization timing conflicts

        BVJ: Platform - Ensures factory initialization doesn't cause race conditions
        EXPECTED: FAIL - Concurrent factory initialization causes timing conflicts
        ISSUE: Factory initialization race conditions cause WebSocket 1011 errors
        """
        # Import the execution engine factory
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory,
                configure_execution_engine_factory
            )
        except ImportError:
            self.fail("Cannot import ExecutionEngineFactory - SSOT consolidation incomplete")

        # Test concurrent factory initialization
        num_concurrent_inits = 5
        initialization_results = []

        async def initialize_factory(factory_id: int):
            """Initialize a factory concurrently."""
            start_time = time.time()
            try:
                # Create factory
                factory = ExecutionEngineFactory(websocket_bridge=None)

                # Create a test user context
                context = UserExecutionContext(
                    user_id=f"race_test_user_{factory_id}",
                    run_id=f"race_test_run_{factory_id}_{int(time.time() * 1000)}",
                    session_id=f"race_test_session_{factory_id}",
                    request_id=f"race_test_request_{factory_id}"
                )

                # Try to create an execution engine immediately
                engine = await factory.create_for_user(context)

                end_time = time.time()
                duration = end_time - start_time

                # Cleanup
                await factory.cleanup_engine(engine)
                await factory.shutdown()

                return {
                    'factory_id': factory_id,
                    'success': True,
                    'duration': duration,
                    'error': None
                }

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time

                return {
                    'factory_id': factory_id,
                    'success': False,
                    'duration': duration,
                    'error': str(e)
                }

        # Execute concurrent factory initializations
        tasks = [initialize_factory(i) for i in range(num_concurrent_inits)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        successful_inits = 0
        failed_inits = 0
        race_condition_errors = []

        for result in results:
            if isinstance(result, dict):
                initialization_results.append(result)
                if result['success']:
                    successful_inits += 1
                else:
                    failed_inits += 1
                    # Check for race condition indicators
                    error = result['error'].lower()
                    if any(indicator in error for indicator in [
                        'race', 'conflict', 'already', 'lock', 'timeout', 'busy'
                    ]):
                        race_condition_errors.append(result)
            else:
                # Exception occurred
                failed_inits += 1
                if hasattr(result, '__str__'):
                    error_str = str(result).lower()
                    if any(indicator in error_str for indicator in [
                        'race', 'conflict', 'already', 'lock', 'timeout', 'busy'
                    ]):
                        race_condition_errors.append({
                            'factory_id': 'unknown',
                            'success': False,
                            'error': str(result)
                        })

        # ASSERTION THAT SHOULD FAIL: No race conditions should occur
        self.assertEqual(
            len(race_condition_errors), 0,
            f"RACE CONDITION DETECTED: {len(race_condition_errors)} factory "
            f"initializations failed due to race conditions. "
            f"Errors: {[err['error'] for err in race_condition_errors]}. "
            f"Factory initialization is not thread-safe."
        )

        # ASSERTION THAT SHOULD FAIL: All initializations should succeed
        self.assertEqual(
            failed_inits, 0,
            f"FACTORY INITIALIZATION FAILURES: {failed_inits} out of "
            f"{num_concurrent_inits} factory initializations failed. "
            f"Concurrent factory creation is unreliable."
        )

    async def test_factory_websocket_coordination_timing_issues(self):
        """FAILING TEST: Reproduce factory/WebSocket initialization timing conflicts

        BVJ: All Segments - Ensures WebSocket events work reliably for chat
        EXPECTED: FAIL - Factory/WebSocket timing issues cause coordination failures
        ISSUE: Factory and WebSocket bridge initialization timing conflicts
        """
        # Import the execution engine factory
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory
            )
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError:
            self.fail("Cannot import required classes - SSOT consolidation incomplete")

        # Test factory creation with/without WebSocket bridge timing
        timing_test_results = []

        # Test 1: Factory without WebSocket bridge (should be fast)
        start_time = time.time()
        factory_no_ws = ExecutionEngineFactory(websocket_bridge=None)
        no_ws_duration = time.time() - start_time

        timing_test_results.append({
            'test': 'factory_without_websocket',
            'duration': no_ws_duration,
            'success': True
        })

        self.factory_instances.append(factory_no_ws)

        # Test 2: Factory with mock WebSocket bridge (may have timing issues)
        start_time = time.time()
        try:
            # Create a mock WebSocket bridge that simulates initialization delay
            class MockWebSocketBridge:
                def __init__(self):
                    # Simulate WebSocket initialization delay
                    time.sleep(0.1)  # 100ms delay
                    self.initialized = True

                async def send_event(self, *args, **kwargs):
                    pass

            mock_bridge = MockWebSocketBridge()
            factory_with_ws = ExecutionEngineFactory(websocket_bridge=mock_bridge)
            ws_duration = time.time() - start_time

            timing_test_results.append({
                'test': 'factory_with_websocket',
                'duration': ws_duration,
                'success': True
            })

            self.factory_instances.append(factory_with_ws)

        except Exception as e:
            ws_duration = time.time() - start_time
            timing_test_results.append({
                'test': 'factory_with_websocket',
                'duration': ws_duration,
                'success': False,
                'error': str(e)
            })

        # Test 3: Concurrent factory + WebSocket bridge creation
        async def create_factory_with_bridge(test_id):
            """Create factory with WebSocket bridge concurrently."""
            start_time = time.time()
            try:
                # Simulate WebSocket bridge creation delay
                await asyncio.sleep(0.05)  # 50ms async delay

                mock_bridge = MockWebSocketBridge()
                factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)

                # Try to create an execution engine immediately
                context = UserExecutionContext(
                    user_id=f"ws_timing_user_{test_id}",
                    run_id=f"ws_timing_run_{test_id}_{int(time.time() * 1000)}",
                    session_id=f"ws_timing_session_{test_id}",
                    request_id=f"ws_timing_request_{test_id}"
                )

                engine = await factory.create_for_user(context)

                duration = time.time() - start_time

                # Cleanup
                await factory.cleanup_engine(engine)
                await factory.shutdown()

                return {
                    'test_id': test_id,
                    'duration': duration,
                    'success': True
                }

            except Exception as e:
                duration = time.time() - start_time
                return {
                    'test_id': test_id,
                    'duration': duration,
                    'success': False,
                    'error': str(e)
                }

        # Execute concurrent factory+WebSocket tests
        concurrent_tasks = [create_factory_with_bridge(i) for i in range(3)]
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        # Analyze timing coordination issues
        coordination_failures = []
        for result in concurrent_results:
            if isinstance(result, dict) and not result['success']:
                coordination_failures.append(result)
            elif not isinstance(result, dict):
                coordination_failures.append({
                    'test_id': 'unknown',
                    'error': str(result),
                    'success': False
                })

        # ASSERTION THAT SHOULD FAIL: No WebSocket coordination failures
        self.assertEqual(
            len(coordination_failures), 0,
            f"WEBSOCKET COORDINATION FAILURES: {len(coordination_failures)} factory "
            f"creation attempts failed due to WebSocket timing issues. "
            f"Errors: {[err.get('error', 'Unknown') for err in coordination_failures]}. "
            f"Factory/WebSocket coordination is unreliable."
        )

        # ASSERTION THAT SHOULD FAIL: WebSocket factories shouldn't be much slower
        if len(timing_test_results) >= 2:
            no_ws_time = timing_test_results[0]['duration']
            ws_time = timing_test_results[1]['duration']
            timing_ratio = ws_time / no_ws_time if no_ws_time > 0 else float('inf')

            # Allow up to 5x slower for WebSocket initialization
            max_acceptable_ratio = 5.0

            self.assertLess(
                timing_ratio, max_acceptable_ratio,
                f"WEBSOCKET TIMING ISSUE: Factory with WebSocket bridge is "
                f"{timing_ratio:.1f}x slower than without ({ws_time:.3f}s vs {no_ws_time:.3f}s). "
                f"WebSocket coordination is causing excessive delays."
            )

    # === TEST RESULT DOCUMENTATION ===

    def _log_test_failure_details(self, test_name: str, failure_details: Dict[str, Any]):
        """Log detailed test failure information for analysis."""
        print(f"\n=== FACTORY FRAGMENTATION TEST FAILURE: {test_name} ===")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Business Impact: Golden Path blocked - $500K+ ARR at risk")
        print(f"Issue: #1123 Execution Engine Factory Fragmentation")
        print("\nFailure Details:")
        for key, value in failure_details.items():
            print(f"  {key}: {value}")
        print("\nNext Steps:")
        print("1. Implement SSOT consolidation for ExecutionEngineFactory")
        print("2. Remove duplicate factory implementations")
        print("3. Fix user isolation and race condition issues")
        print("4. Re-run tests to validate fixes")
        print("=" * 60)


if __name__ == '__main__':
    # Run the fragmentation tests
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])