"""Phase 1 Unit Tests: Execution Engine Factory SSOT Violations (Issue #884)

CRITICAL BUSINESS VALUE: These tests reproduce execution engine factory fragmentation
issues that block the Golden Path user flow (login → AI response), protecting $500K+ ARR.

EXPECTED BEHAVIOR: All tests in this file should INITIALLY FAIL to demonstrate
SSOT violations in execution engine factory patterns. They will pass after consolidation.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure execution engine factory SSOT compliance and reliability
- Value Impact: Prevents factory fragmentation, user isolation failures, memory leaks
- Strategic Impact: Foundation for $500K+ ARR multi-user chat functionality

Test Philosophy:
- FAILING TESTS FIRST: These tests reproduce real SSOT violations before fixing them
- REAL PROBLEM REPRODUCTION: Each test demonstrates actual factory fragmentation issues
- SSOT VALIDATION: Tests validate single canonical execution engine factory
- USER ISOLATION: Tests ensure complete user context isolation in factory operations
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
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.unit
class ExecutionEngineFactorySSOTViolations884Tests(SSotAsyncTestCase):
    """Phase 1 Unit Tests: Execution Engine Factory SSOT Violations

    These tests are designed to FAIL initially to demonstrate the factory
    SSOT violations blocking the Golden Path. They will pass after
    SSOT consolidation fixes are implemented.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_users = []
        self.factory_instances = []
        self.created_contexts = []
        self.factory_classes_found = []
        self.import_paths_tested = []
        self.singleton_violations = []
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

    async def test_execution_engine_factory_canonical_ssot_location(self):
        """FAILING TEST: Validate ExecutionEngineFactory exists in canonical SSOT location

        BVJ: Platform - Ensures SSOT compliance prevents factory fragmentation
        EXPECTED: FAIL - Factory may not exist in expected canonical location
        ISSUE: Factory implementations scattered across multiple modules
        """
        factory_class = None
        try:
            module = importlib.import_module(self.canonical_factory_module)
            factory_class = getattr(module, self.canonical_factory_class, None)
        except ImportError as e:
            self.fail(f'SSOT VIOLATION: Cannot import canonical ExecutionEngineFactory from {self.canonical_factory_module}. ImportError: {e}. Factory must exist in canonical SSOT location.')
        self.assertIsNotNone(factory_class, f'SSOT VIOLATION: {self.canonical_factory_class} not found in {self.canonical_factory_module}. Canonical factory missing from SSOT location.')
        self.assertTrue(inspect.isclass(factory_class), f'SSOT VIOLATION: {self.canonical_factory_class} is not a class. Expected class object, got {type(factory_class)}.')
        required_ssot_methods = ['create_for_user', 'user_execution_scope', 'cleanup_engine', 'get_factory_metrics', 'shutdown']
        missing_methods = []
        for method_name in required_ssot_methods:
            if not hasattr(factory_class, method_name):
                missing_methods.append(method_name)
        self.assertEqual(len(missing_methods), 0, f'SSOT VIOLATION: Canonical ExecutionEngineFactory missing required methods: {missing_methods}. Factory does not implement SSOT interface.')

    async def test_execution_engine_factory_duplicate_implementations_detection(self):
        """FAILING TEST: Detect multiple ExecutionEngineFactory implementations

        BVJ: Platform - Ensures SSOT compliance prevents factory fragmentation
        EXPECTED: FAIL - Multiple factory implementations should be detected
        ISSUE: Factory implementations scattered across 4+ modules causing conflicts
        """
        factory_implementations = []
        factory_modules_to_check = ['netra_backend.app.agents.supervisor.execution_engine_factory', 'netra_backend.app.agents.supervisor.request_scoped_execution_engine', 'netra_backend.app.agents.supervisor.user_execution_engine', 'netra_backend.app.agents.execution_engine_unified_factory', 'netra_backend.app.core.managers.execution_engine_factory', 'test_framework.fixtures.execution_engine_factory_fixtures', 'netra_backend.app.agents.supervisor.mcp_execution_engine']
        for module_name in factory_modules_to_check:
            try:
                module = importlib.import_module(module_name)
                for name in dir(module):
                    obj = getattr(module, name)
                    if inspect.isclass(obj) and ('ExecutionEngineFactory' in name or 'ExecutionEngine' in name or hasattr(obj, 'create_execution_engine') or hasattr(obj, 'create_for_user') or hasattr(obj, 'user_execution_scope')):
                        factory_implementations.append({'module': module_name, 'class': name, 'object': obj})
            except ImportError:
                continue
        self.factory_classes_found = factory_implementations
        detected_implementations = [f"{impl['module']}.{impl['class']}" for impl in factory_implementations]
        self.assertEqual(len(factory_implementations), 1, f'SSOT VIOLATION: Found {len(factory_implementations)} execution engine factory implementations. Should have only 1 canonical ExecutionEngineFactory. Detected: {detected_implementations}')
        if len(factory_implementations) > 1:
            canonical_factory = factory_implementations[0]['object']
            for impl in factory_implementations[1:]:
                self.assertIs(impl['object'], canonical_factory, f"SSOT VIOLATION: {impl['module']}.{impl['class']} is not the same as canonical factory. Multiple distinct factory classes exist.")

    async def test_execution_engine_factory_import_path_consolidation(self):
        """FAILING TEST: Validate all import paths resolve to same canonical factory

        BVJ: Platform - Ensures import path consistency prevents race conditions
        EXPECTED: FAIL - Different import paths lead to different factory classes
        ISSUE: Import fragmentation causes factory initialization conflicts
        """
        import_paths_to_test = [('netra_backend.app.agents.supervisor.execution_engine_factory', 'ExecutionEngineFactory'), ('netra_backend.app.agents.supervisor.execution_engine_factory', 'RequestScopedExecutionEngineFactory'), ('netra_backend.app.agents.supervisor.request_scoped_execution_engine', 'RequestScopedExecutionEngine'), ('netra_backend.app.agents.execution_engine_unified_factory', 'UnifiedExecutionEngineFactory'), ('netra_backend.app.core.managers.execution_engine_factory', 'ExecutionEngineFactory')]
        imported_factories = {}
        self.import_paths_tested = import_paths_to_test
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
        max_allowed_failures = len(import_paths_to_test) - 1
        self.assertLessEqual(len(import_failures), max_allowed_failures, f'IMPORT FRAGMENTATION: Too many failed imports: {import_failures}. At least canonical factory import path should work.')

    async def test_execution_engine_factory_singleton_violations_detection(self):
        """FAILING TEST: Detect singleton pattern violations in execution engine factories

        BVJ: All Segments - Ensures proper factory instantiation prevents state contamination
        EXPECTED: FAIL - Singleton violations should be detected causing user isolation issues
        ISSUE: Global singleton patterns cause cross-user data contamination
        """
        singleton_violations = []
        modules_to_check = ['netra_backend.app.agents.supervisor.execution_engine_factory', 'netra_backend.app.agents.supervisor.request_scoped_execution_engine', 'netra_backend.app.agents.supervisor.user_execution_engine']
        for module_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                for name in dir(module):
                    obj = getattr(module, name)
                    if isinstance(obj, object) and name.startswith('_') and ('instance' in name.lower() or 'singleton' in name.lower() or 'factory' in name.lower()):
                        singleton_violations.append({'module': module_name, 'variable': name, 'type': type(obj).__name__, 'violation_type': 'global_singleton_instance'})
                    if inspect.isfunction(obj) and ('get_' in name and 'factory' in name.lower()) or ('create_' in name and 'singleton' in name.lower()):
                        singleton_violations.append({'module': module_name, 'function': name, 'violation_type': 'singleton_factory_function'})
                for attr_name in ['_factory_instance', '_execution_engine_factory', '_global_factory']:
                    if hasattr(module, attr_name):
                        attr_value = getattr(module, attr_name)
                        if attr_value is not None:
                            singleton_violations.append({'module': module_name, 'attribute': attr_name, 'value_type': type(attr_value).__name__, 'violation_type': 'module_level_singleton'})
            except ImportError:
                continue
        self.singleton_violations = singleton_violations
        self.assertEqual(len(singleton_violations), 0, f'SINGLETON VIOLATIONS DETECTED: Found {len(singleton_violations)} singleton pattern violations. Violations: {singleton_violations}. Singleton patterns prevent proper user isolation and cause data contamination.')

    async def test_execution_engine_factory_global_state_contamination(self):
        """FAILING TEST: Reproduce global state contamination in factory patterns

        BVJ: All Segments - Ensures user data isolation for HIPAA/SOC2 compliance
        EXPECTED: FAIL - Global state should contaminate between factory instances
        ISSUE: Shared global state causes cross-user data leakage
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, get_execution_engine_factory, configure_execution_engine_factory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        num_factory_instances = 3
        factory_instances = []
        global_state_contamination = []
        for i in range(num_factory_instances):
            try:
                factory = ExecutionEngineFactory(websocket_bridge=None)
                factory_instances.append(factory)
                self.factory_instances.append(factory)
                unique_state_key = f'test_state_{i}'
                unique_state_value = f'factory_{i}_state_{int(time.time() * 1000)}'
                if hasattr(factory, '_test_state'):
                    factory._test_state[unique_state_key] = unique_state_value
                else:
                    factory._test_state = {unique_state_key: unique_state_value}
            except Exception as e:
                self.fail(f'Failed to create factory instance {i}: {e}')
        for i, factory1 in enumerate(factory_instances):
            for j, factory2 in enumerate(factory_instances):
                if i != j:
                    if hasattr(factory1, '_test_state') and hasattr(factory2, '_test_state'):
                        if factory1._test_state is factory2._test_state:
                            global_state_contamination.append({'factory1_index': i, 'factory2_index': j, 'contamination_type': 'shared_state_reference', 'shared_object': 'test_state'})
                        shared_keys = set(factory1._test_state.keys()) & set(factory2._test_state.keys())
                        if shared_keys:
                            global_state_contamination.append({'factory1_index': i, 'factory2_index': j, 'contamination_type': 'shared_state_keys', 'shared_keys': list(shared_keys)})
        try:
            global_factory_1 = await get_execution_engine_factory()
            global_factory_2 = await get_execution_engine_factory()
            if global_factory_1 is global_factory_2:
                global_state_contamination.append({'contamination_type': 'global_singleton_access', 'description': 'get_execution_engine_factory() returns same instance'})
        except Exception:
            pass
        self.assertEqual(len(global_state_contamination), 0, f'GLOBAL STATE CONTAMINATION DETECTED: Found {len(global_state_contamination)} instances of global state sharing between factory instances. Contamination: {global_state_contamination}. Global state sharing prevents proper user isolation.')

    async def test_execution_engine_factory_interface_fragmentation(self):
        """FAILING TEST: Detect interface inconsistencies across factory implementations

        BVJ: Platform - Ensures consistent factory interfaces prevent integration failures
        EXPECTED: FAIL - Different factory implementations have inconsistent interfaces
        ISSUE: Interface fragmentation causes integration and compatibility issues
        """
        if not hasattr(self, 'factory_classes_found') or not self.factory_classes_found:
            await self.test_execution_engine_factory_duplicate_implementations_detection()
        interface_inconsistencies = []
        expected_interface = {'methods': ['create_for_user', 'user_execution_scope', 'cleanup_engine', 'get_factory_metrics', 'shutdown'], 'async_methods': ['create_for_user', 'user_execution_scope', 'cleanup_engine', 'shutdown'], 'properties': ['__init__']}
        for impl in self.factory_classes_found:
            factory_class = impl['object']
            class_name = f"{impl['module']}.{impl['class']}"
            missing_methods = []
            for method_name in expected_interface['methods']:
                if not hasattr(factory_class, method_name):
                    missing_methods.append(method_name)
            if missing_methods:
                interface_inconsistencies.append({'factory_class': class_name, 'issue_type': 'missing_methods', 'missing_methods': missing_methods})
            signature_issues = []
            for method_name in expected_interface['methods']:
                if hasattr(factory_class, method_name):
                    method = getattr(factory_class, method_name)
                    if callable(method):
                        try:
                            sig = inspect.signature(method)
                            if method_name in expected_interface['async_methods']:
                                if not asyncio.iscoroutinefunction(method):
                                    signature_issues.append({'method': method_name, 'issue': 'not_async', 'expected': 'async method', 'actual': 'sync method'})
                        except Exception as e:
                            signature_issues.append({'method': method_name, 'issue': 'signature_inspection_failed', 'error': str(e)})
            if signature_issues:
                interface_inconsistencies.append({'factory_class': class_name, 'issue_type': 'signature_issues', 'signature_issues': signature_issues})
        self.assertEqual(len(interface_inconsistencies), 0, f'INTERFACE FRAGMENTATION DETECTED: Found {len(interface_inconsistencies)} interface inconsistencies across factory implementations. Inconsistencies: {interface_inconsistencies}. Interface fragmentation prevents reliable factory usage.')

    async def test_execution_engine_factory_cleanup_coordination_failures(self):
        """FAILING TEST: Reproduce factory cleanup coordination failures

        BVJ: Platform - Ensures proper factory cleanup prevents resource leaks
        EXPECTED: FAIL - Factory cleanup coordination should fail with multiple implementations
        ISSUE: Multiple factory implementations have inconsistent cleanup behavior
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        cleanup_coordination_failures = []
        num_factories = 3
        factories = []
        user_contexts = []
        try:
            for i in range(num_factories):
                factory = ExecutionEngineFactory(websocket_bridge=None)
                factories.append(factory)
                self.factory_instances.append(factory)
                context = UserExecutionContext(user_id=f'cleanup_test_user_{i}', run_id=f'cleanup_test_run_{i}_{int(time.time() * 1000)}', session_id=f'cleanup_test_session_{i}', request_id=f'cleanup_test_request_{i}')
                user_contexts.append(context)
                self.created_contexts.append(context)
                try:
                    engine = await factory.create_for_user(context)
                    await factory.cleanup_engine(engine)
                except Exception as e:
                    cleanup_coordination_failures.append({'factory_index': i, 'operation': 'create_and_cleanup', 'error': str(e), 'failure_type': 'immediate_cleanup_failure'})
            if len(factories) >= 2:
                try:
                    context = user_contexts[0]
                    engine = await factories[0].create_for_user(context)
                    try:
                        await factories[1].cleanup_engine(engine)
                        cleanup_coordination_failures.append({'factory1_index': 0, 'factory2_index': 1, 'operation': 'cross_factory_cleanup', 'failure_type': 'cross_factory_cleanup_succeeded', 'description': 'Factory 1 cleaned up engine created by Factory 0'})
                    except Exception:
                        pass
                    await factories[0].cleanup_engine(engine)
                except Exception as e:
                    cleanup_coordination_failures.append({'operation': 'cross_factory_test', 'error': str(e), 'failure_type': 'cross_factory_test_setup_failure'})
            shutdown_failures = []
            for i, factory in enumerate(factories):
                try:
                    await factory.shutdown()
                except Exception as e:
                    shutdown_failures.append({'factory_index': i, 'error': str(e), 'failure_type': 'shutdown_failure'})
            if shutdown_failures:
                cleanup_coordination_failures.extend(shutdown_failures)
        except Exception as e:
            cleanup_coordination_failures.append({'operation': 'factory_setup', 'error': str(e), 'failure_type': 'factory_setup_failure'})
        self.assertEqual(len(cleanup_coordination_failures), 0, f'CLEANUP COORDINATION FAILURES: Found {len(cleanup_coordination_failures)} factory cleanup coordination failures. Failures: {cleanup_coordination_failures}. Inconsistent cleanup behavior prevents reliable resource management.')

    def _log_test_failure_details(self, test_name: str, failure_details: Dict[str, Any]):
        """Log detailed test failure information for analysis."""
        print(f'\n=== EXECUTION ENGINE FACTORY SSOT VIOLATION: {test_name} ===')
        print(f'Timestamp: {datetime.now().isoformat()}')
        print(f'Business Impact: Golden Path blocked - $500K+ ARR at risk')
        print(f'Issue: #884 Execution Engine Factory Fragmentation')
        print('\nFailure Details:')
        for key, value in failure_details.items():
            print(f'  {key}: {value}')
        print('\nNext Steps:')
        print('1. Implement SSOT consolidation for ExecutionEngineFactory')
        print('2. Remove duplicate factory implementations')
        print('3. Fix singleton pattern violations')
        print('4. Ensure consistent factory interfaces')
        print('5. Re-run tests to validate fixes')
        print('=' * 60)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')