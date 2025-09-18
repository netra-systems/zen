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
import pytest
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
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.unit
class ExecutionEngineFactoryFragmentation1123Tests(SSotAsyncTestCase):
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
        self.factory_creation_times = []
        self.memory_usage_before = []
        self.memory_usage_after = []
        self.canonical_factory_module = 'netra_backend.app.agents.supervisor.execution_engine_factory'
        self.canonical_factory_class = 'ExecutionEngineFactory'

    async def asyncTearDown(self):
        """Clean up test resources."""
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
        gc.collect()
        await super().asyncTearDown()

    async def test_execution_engine_factory_ssot_compliance_fragmentation_detection(self):
        """FAILING TEST: Detect multiple ExecutionEngineFactory implementations

        BVJ: Platform - Ensures SSOT compliance prevents factory fragmentation
        EXPECTED: FAIL - Multiple factory implementations should be detected
        ISSUE: Factory implementations scattered across 4+ modules causing conflicts
        """
        factory_implementations = []
        factory_modules_to_check = ['netra_backend.app.agents.supervisor.execution_engine_factory', 'netra_backend.app.agents.execution_engine_unified_factory', 'netra_backend.app.core.managers.execution_engine_factory', 'test_framework.fixtures.execution_engine_factory_fixtures']
        for module_name in factory_modules_to_check:
            try:
                module = importlib.import_module(module_name)
                for name in dir(module):
                    obj = getattr(module, name)
                    if inspect.isclass(obj) and ('ExecutionEngineFactory' in name or hasattr(obj, 'create_execution_engine') or hasattr(obj, 'create_for_user')):
                        factory_implementations.append({'module': module_name, 'class': name, 'object': obj})
            except ImportError:
                continue
        detected_implementations = [f"{impl['module']}.{impl['class']}" for impl in factory_implementations]
        self.assertEqual(len(factory_implementations), 1, f'SSOT VIOLATION: Found {len(factory_implementations)} factory implementations. Should have only 1 canonical ExecutionEngineFactory. Detected: {detected_implementations}')
        if factory_implementations:
            canonical_factory = factory_implementations[0]['object']
            for impl in factory_implementations[1:]:
                self.assertIs(impl['object'], canonical_factory, f"SSOT VIOLATION: {impl['module']}.{impl['class']} is not the same as canonical factory. Multiple distinct factory classes exist.")

    async def test_factory_import_path_consolidation_fragmentation(self):
        """FAILING TEST: Validate all import paths resolve to same canonical factory

        BVJ: Platform - Ensures import path consistency prevents race conditions
        EXPECTED: FAIL - Different import paths lead to different factory classes
        ISSUE: Import fragmentation causes factory initialization conflicts
        """
        import_paths_to_test = [('netra_backend.app.agents.supervisor.execution_engine_factory', 'ExecutionEngineFactory'), ('netra_backend.app.agents.execution_engine_unified_factory', 'UnifiedExecutionEngineFactory'), ('netra_backend.app.core.managers.execution_engine_factory', 'ExecutionEngineFactory')]
        imported_factories = {}
        for module_path, class_name in import_paths_to_test:
            try:
                module = importlib.import_module(module_path)
                factory_class = getattr(module, class_name, None)
                if factory_class and inspect.isclass(factory_class):
                    imported_factories[f'{module_path}.{class_name}'] = factory_class
            except ImportError as e:
                imported_factories[f'{module_path}.{class_name}'] = f'ImportError: {e}'
        actual_factory_classes = [factory for factory in imported_factories.values() if inspect.isclass(factory)]
        if len(actual_factory_classes) > 1:
            canonical_factory = actual_factory_classes[0]
            for i, factory_class in enumerate(actual_factory_classes[1:], 1):
                self.assertIs(factory_class, canonical_factory, f'IMPORT FRAGMENTATION: Factory class from import path {i + 1} ({factory_class}) is not the same as canonical factory ({canonical_factory}). Import paths resolve to different classes.')
        import_failures = [path for path, result in imported_factories.items() if isinstance(result, str) and 'ImportError' in result]
        self.assertEqual(len(import_failures), 0, f'IMPORT FRAGMENTATION: Failed imports detected: {import_failures}. All factory import paths should resolve successfully.')

    async def test_concurrent_user_factory_isolation_contamination(self):
        """FAILING TEST: Reproduce user state contamination in concurrent factory usage

        BVJ: All Segments - Ensures user data isolation for HIPAA/SOC2 compliance
        EXPECTED: FAIL - User contexts contaminate each other in concurrent usage
        ISSUE: Shared factory state causes cross-user data leakage
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, configure_execution_engine_factory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        num_concurrent_users = 5
        user_contexts = []
        for i in range(num_concurrent_users):
            context = UserExecutionContext(user_id=f'test_user_{i}', run_id=f'test_run_{i}_{int(time.time() * 1000)}', session_id=f'test_session_{i}', request_id=f'test_request_{i}')
            user_contexts.append(context)
            self.created_contexts.append(context)
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        created_engines = []

        async def create_user_engine(user_context):
            """Create engine for a specific user."""
            engine = await factory.create_for_user(user_context)
            return (engine, user_context)
        tasks = [create_user_engine(ctx) for ctx in user_contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, tuple):
                engine, context = result
                created_engines.append((engine, context))
        for i, (engine1, context1) in enumerate(created_engines):
            for j, (engine2, context2) in enumerate(created_engines):
                if i != j:
                    engine1_context = engine1.get_user_context()
                    engine2_context = engine2.get_user_context()
                    self.assertNotEqual(engine1_context.user_id, engine2_context.user_id, f'USER ISOLATION VIOLATION: Engine {i} and Engine {j} have the same user_id ({engine1_context.user_id}). Cross-user contamination detected.')
                    self.assertNotEqual(engine1_context.run_id, engine2_context.run_id, f'USER ISOLATION VIOLATION: Engine {i} and Engine {j} have the same run_id ({engine1_context.run_id}). Run context contamination detected.')
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
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        num_iterations = 10
        max_memory_growth = 50
        for iteration in range(num_iterations):
            factory = ExecutionEngineFactory(websocket_bridge=None)
            self.factory_instances.append(factory)
            user_contexts = []
            for i in range(3):
                context = UserExecutionContext(user_id=f'memory_test_user_{iteration}_{i}', run_id=f'memory_test_run_{iteration}_{i}_{int(time.time() * 1000)}', session_id=f'memory_test_session_{iteration}_{i}', request_id=f'memory_test_request_{iteration}_{i}')
                user_contexts.append(context)
                self.created_contexts.append(context)
            engines = []
            for context in user_contexts:
                try:
                    engine = await factory.create_for_user(context)
                    engines.append(engine)
                except Exception:
                    pass
            for engine in engines:
                try:
                    await factory.cleanup_engine(engine)
                except Exception:
                    pass
            try:
                await factory.shutdown()
            except Exception:
                pass
            gc.collect()
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_growth = current_memory - initial_memory
            self.memory_usage_before.append(initial_memory)
            self.memory_usage_after.append(current_memory)
        final_memory = process.memory_info().rss / 1024 / 1024
        total_memory_growth = final_memory - initial_memory
        self.assertLess(total_memory_growth, max_memory_growth, f'MEMORY LEAK DETECTED: Factory operations caused {total_memory_growth:.1f}MB memory growth (limit: {max_memory_growth}MB). Initial: {initial_memory:.1f}MB, Final: {final_memory:.1f}MB. Factory cleanup is not releasing memory properly.')

    async def test_factory_initialization_race_conditions_reproduction(self):
        """FAILING TEST: Reproduce factory initialization timing conflicts

        BVJ: Platform - Ensures factory initialization doesn't cause race conditions
        EXPECTED: FAIL - Concurrent factory initialization causes timing conflicts
        ISSUE: Factory initialization race conditions cause WebSocket 1011 errors
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, configure_execution_engine_factory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        num_concurrent_inits = 5
        initialization_results = []

        async def initialize_factory(factory_id: int):
            """Initialize a factory concurrently."""
            start_time = time.time()
            try:
                factory = ExecutionEngineFactory(websocket_bridge=None)
                context = UserExecutionContext(user_id=f'race_test_user_{factory_id}', run_id=f'race_test_run_{factory_id}_{int(time.time() * 1000)}', session_id=f'race_test_session_{factory_id}', request_id=f'race_test_request_{factory_id}')
                engine = await factory.create_for_user(context)
                end_time = time.time()
                duration = end_time - start_time
                await factory.cleanup_engine(engine)
                await factory.shutdown()
                return {'factory_id': factory_id, 'success': True, 'duration': duration, 'error': None}
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                return {'factory_id': factory_id, 'success': False, 'duration': duration, 'error': str(e)}
        tasks = [initialize_factory(i) for i in range(num_concurrent_inits)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
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
                    error = result['error'].lower()
                    if any((indicator in error for indicator in ['race', 'conflict', 'already', 'lock', 'timeout', 'busy'])):
                        race_condition_errors.append(result)
            else:
                failed_inits += 1
                if hasattr(result, '__str__'):
                    error_str = str(result).lower()
                    if any((indicator in error_str for indicator in ['race', 'conflict', 'already', 'lock', 'timeout', 'busy'])):
                        race_condition_errors.append({'factory_id': 'unknown', 'success': False, 'error': str(result)})
        self.assertEqual(len(race_condition_errors), 0, f"RACE CONDITION DETECTED: {len(race_condition_errors)} factory initializations failed due to race conditions. Errors: {[err['error'] for err in race_condition_errors]}. Factory initialization is not thread-safe.")
        self.assertEqual(failed_inits, 0, f'FACTORY INITIALIZATION FAILURES: {failed_inits} out of {num_concurrent_inits} factory initializations failed. Concurrent factory creation is unreliable.')

    async def test_factory_websocket_coordination_timing_issues(self):
        """FAILING TEST: Reproduce factory/WebSocket initialization timing conflicts

        BVJ: All Segments - Ensures WebSocket events work reliably for chat
        EXPECTED: FAIL - Factory/WebSocket timing issues cause coordination failures
        ISSUE: Factory and WebSocket bridge initialization timing conflicts
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError:
            self.fail('Cannot import required classes - SSOT consolidation incomplete')
        timing_test_results = []
        start_time = time.time()
        factory_no_ws = ExecutionEngineFactory(websocket_bridge=None)
        no_ws_duration = time.time() - start_time
        timing_test_results.append({'test': 'factory_without_websocket', 'duration': no_ws_duration, 'success': True})
        self.factory_instances.append(factory_no_ws)
        start_time = time.time()
        try:

            class MockWebSocketBridge:

                def __init__(self):
                    time.sleep(0.1)
                    self.initialized = True

                async def send_event(self, *args, **kwargs):
                    pass
            mock_bridge = MockWebSocketBridge()
            factory_with_ws = ExecutionEngineFactory(websocket_bridge=mock_bridge)
            ws_duration = time.time() - start_time
            timing_test_results.append({'test': 'factory_with_websocket', 'duration': ws_duration, 'success': True})
            self.factory_instances.append(factory_with_ws)
        except Exception as e:
            ws_duration = time.time() - start_time
            timing_test_results.append({'test': 'factory_with_websocket', 'duration': ws_duration, 'success': False, 'error': str(e)})

        async def create_factory_with_bridge(test_id):
            """Create factory with WebSocket bridge concurrently."""
            start_time = time.time()
            try:
                await asyncio.sleep(0.05)
                mock_bridge = MockWebSocketBridge()
                factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
                context = UserExecutionContext(user_id=f'ws_timing_user_{test_id}', run_id=f'ws_timing_run_{test_id}_{int(time.time() * 1000)}', session_id=f'ws_timing_session_{test_id}', request_id=f'ws_timing_request_{test_id}')
                engine = await factory.create_for_user(context)
                duration = time.time() - start_time
                await factory.cleanup_engine(engine)
                await factory.shutdown()
                return {'test_id': test_id, 'duration': duration, 'success': True}
            except Exception as e:
                duration = time.time() - start_time
                return {'test_id': test_id, 'duration': duration, 'success': False, 'error': str(e)}
        concurrent_tasks = [create_factory_with_bridge(i) for i in range(3)]
        concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        coordination_failures = []
        for result in concurrent_results:
            if isinstance(result, dict) and (not result['success']):
                coordination_failures.append(result)
            elif not isinstance(result, dict):
                coordination_failures.append({'test_id': 'unknown', 'error': str(result), 'success': False})
        self.assertEqual(len(coordination_failures), 0, f"WEBSOCKET COORDINATION FAILURES: {len(coordination_failures)} factory creation attempts failed due to WebSocket timing issues. Errors: {[err.get('error', 'Unknown') for err in coordination_failures]}. Factory/WebSocket coordination is unreliable.")
        if len(timing_test_results) >= 2:
            no_ws_time = timing_test_results[0]['duration']
            ws_time = timing_test_results[1]['duration']
            timing_ratio = ws_time / no_ws_time if no_ws_time > 0 else float('inf')
            max_acceptable_ratio = 5.0
            self.assertLess(timing_ratio, max_acceptable_ratio, f'WEBSOCKET TIMING ISSUE: Factory with WebSocket bridge is {timing_ratio:.1f}x slower than without ({ws_time:.3f}s vs {no_ws_time:.3f}s). WebSocket coordination is causing excessive delays.')

    def _log_test_failure_details(self, test_name: str, failure_details: Dict[str, Any]):
        """Log detailed test failure information for analysis."""
        print(f'\n=== FACTORY FRAGMENTATION TEST FAILURE: {test_name} ===')
        print(f'Timestamp: {datetime.now().isoformat()}')
        print(f'Business Impact: Golden Path blocked - $500K+ ARR at risk')
        print(f'Issue: #1123 Execution Engine Factory Fragmentation')
        print('\nFailure Details:')
        for key, value in failure_details.items():
            print(f'  {key}: {value}')
        print('\nNext Steps:')
        print('1. Implement SSOT consolidation for ExecutionEngineFactory')
        print('2. Remove duplicate factory implementations')
        print('3. Fix user isolation and race condition issues')
        print('4. Re-run tests to validate fixes')
        print('=' * 60)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')