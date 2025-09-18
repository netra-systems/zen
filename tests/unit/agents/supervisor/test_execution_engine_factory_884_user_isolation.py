"""Phase 1 Unit Tests: Execution Engine Factory User Isolation (Issue #884)

CRITICAL BUSINESS VALUE: These tests reproduce user isolation failures in execution
engine factory patterns that create HIPAA/SOC2 compliance violations and cross-user
data contamination, protecting 500K+ ARR functionality.

EXPECTED BEHAVIOR: All tests in this file should INITIALLY FAIL to demonstrate
user isolation violations. They will pass after SSOT consolidation.

Business Value Justification (BVJ):
- Segment: All Segments (Enterprise compliance critical)
- Business Goal: Ensure user data isolation for regulatory compliance
- Value Impact: Prevents HIPAA/SOC2 violations, cross-user data leakage
- Strategic Impact: Enterprise readiness for 500K+ ARR multi-user operations

Test Philosophy:
- FAILING TESTS FIRST: These tests reproduce real user isolation violations
- SECURITY FOCUSED: Tests validate enterprise-grade user isolation requirements
- COMPLIANCE DRIVEN: Tests ensure HIPAA, SOC2, SEC compliance readiness
- CONCURRENT VALIDATION: Tests ensure isolation under concurrent user load
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
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.unit
class ExecutionEngineFactoryUserIsolation884Tests(SSotAsyncTestCase):
    """Phase 1 Unit Tests: Execution Engine Factory User Isolation Violations

    These tests are designed to FAIL initially to demonstrate user isolation
    violations in factory patterns. They will pass after SSOT consolidation.
    """

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_users = []
        self.factory_instances = []
        self.created_contexts = []
        self.created_engines = []
        self.isolation_violations = []
        self.context_contamination = []
        self.shared_state_instances = []
        self.max_concurrent_users = 10
        self.isolation_stress_iterations = 5

    async def asyncTearDown(self):
        """Clean up test resources."""
        for engine in self.created_engines:
            try:
                if hasattr(engine, 'cleanup'):
                    await engine.cleanup()
            except Exception:
                pass
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

    async def test_concurrent_user_context_isolation_contamination(self):
        """FAILING TEST: Reproduce user context contamination in concurrent factory usage

        BVJ: All Segments - Ensures user data isolation for HIPAA/SOC2 compliance
        EXPECTED: FAIL - User contexts contaminate each other in concurrent usage
        ISSUE: Factory patterns allow cross-user context contamination
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        num_concurrent_users = 5
        user_contexts = []
        user_isolation_violations = []
        for i in range(num_concurrent_users):
            context = UserExecutionContext(user_id=f'isolation_test_user_{i}', run_id=f'isolation_test_run_{i}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}', session_id=f'isolation_test_session_{i}_{uuid.uuid4().hex[:8]}', request_id=f'isolation_test_request_{i}_{uuid.uuid4().hex[:8]}')
            user_contexts.append(context)
            self.created_contexts.append(context)
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        created_engines = []

        async def create_user_engine_with_isolation_check(user_context, user_index):
            """Create engine for a specific user and validate isolation."""
            try:
                engine = await factory.create_for_user(user_context)
                engine_context = engine.get_user_context()
                if engine_context.user_id != user_context.user_id:
                    user_isolation_violations.append({'user_index': user_index, 'violation_type': 'user_id_mismatch', 'expected': user_context.user_id, 'actual': engine_context.user_id, 'description': 'Engine user_id does not match input context'})
                if engine_context.run_id != user_context.run_id:
                    user_isolation_violations.append({'user_index': user_index, 'violation_type': 'run_id_mismatch', 'expected': user_context.run_id, 'actual': engine_context.run_id, 'description': 'Engine run_id does not match input context'})
                if engine_context.session_id != user_context.session_id:
                    user_isolation_violations.append({'user_index': user_index, 'violation_type': 'session_id_mismatch', 'expected': user_context.session_id, 'actual': engine_context.session_id, 'description': 'Engine session_id does not match input context'})
                return (engine, user_context, user_index)
            except Exception as e:
                user_isolation_violations.append({'user_index': user_index, 'violation_type': 'engine_creation_failure', 'error': str(e), 'description': 'Failed to create engine for user'})
                return (None, user_context, user_index)
        tasks = [create_user_engine_with_isolation_check(ctx, i) for i, ctx in enumerate(user_contexts)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, tuple) and result[0] is not None:
                engine, context, user_index = result
                created_engines.append((engine, context, user_index))
                self.created_engines.append(engine)
        for i, (engine1, context1, user_index1) in enumerate(created_engines):
            for j, (engine2, context2, user_index2) in enumerate(created_engines):
                if i != j:
                    engine1_context = engine1.get_user_context()
                    engine2_context = engine2.get_user_context()
                    self.assertNotEqual(engine1_context.user_id, engine2_context.user_id, f'USER ISOLATION VIOLATION: Engine {user_index1} and Engine {user_index2} have the same user_id ({engine1_context.user_id}). Cross-user contamination detected.')
                    self.assertNotEqual(engine1_context.run_id, engine2_context.run_id, f'USER ISOLATION VIOLATION: Engine {user_index1} and Engine {user_index2} have the same run_id ({engine1_context.run_id}). Run context contamination detected.')
                    self.assertNotEqual(engine1_context.session_id, engine2_context.session_id, f'USER ISOLATION VIOLATION: Engine {user_index1} and Engine {user_index2} have the same session_id ({engine1_context.session_id}). Session contamination detected.')
        self.assertEqual(len(user_isolation_violations), 0, f'USER ISOLATION VIOLATIONS DETECTED: Found {len(user_isolation_violations)} user isolation violations during concurrent engine creation. Violations: {user_isolation_violations}')
        for engine, _, _ in created_engines:
            try:
                await factory.cleanup_engine(engine)
            except Exception:
                pass

    async def test_execution_engine_shared_state_contamination(self):
        """FAILING TEST: Reproduce shared state contamination between user engines

        BVJ: Enterprise - Ensures enterprise-grade user isolation
        EXPECTED: FAIL - Engines share state causing cross-user data leakage
        ISSUE: Execution engines share internal state between users
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        num_users = 3
        user_engines = []
        shared_state_violations = []
        for i in range(num_users):
            context = UserExecutionContext(user_id=f'shared_state_user_{i}', run_id=f'shared_state_run_{i}_{int(time.time() * 1000)}', session_id=f'shared_state_session_{i}', request_id=f'shared_state_request_{i}')
            self.created_contexts.append(context)
            engine = await factory.create_for_user(context)
            user_engines.append((engine, context, i))
            self.created_engines.append(engine)
        for i, (engine1, context1, user_index1) in enumerate(user_engines):
            for j, (engine2, context2, user_index2) in enumerate(user_engines):
                if i != j:
                    shared_references = []
                    attributes_to_check = ['_agent_factory', '_websocket_emitter', '_execution_context', '_active_runs', 'agent_class_registry', 'database_session_manager', 'redis_manager']
                    for attr_name in attributes_to_check:
                        if hasattr(engine1, attr_name) and hasattr(engine2, attr_name):
                            attr1 = getattr(engine1, attr_name)
                            attr2 = getattr(engine2, attr_name)
                            if attr1 is attr2 and attr1 is not None:
                                shared_references.append({'attribute': attr_name, 'shared_object_type': type(attr1).__name__, 'engine1_user': user_index1, 'engine2_user': user_index2})
                    if shared_references:
                        shared_state_violations.append({'engine1_user': user_index1, 'engine2_user': user_index2, 'shared_references': shared_references, 'violation_type': 'shared_object_references'})
                    engine1_context = engine1.get_user_context()
                    engine2_context = engine2.get_user_context()
                    if engine1_context is engine2_context:
                        shared_state_violations.append({'engine1_user': user_index1, 'engine2_user': user_index2, 'violation_type': 'shared_user_context_reference', 'description': 'Engines share the same UserExecutionContext object'})
        self.assertEqual(len(shared_state_violations), 0, f'SHARED STATE CONTAMINATION DETECTED: Found {len(shared_state_violations)} instances of shared state between user engines. Violations: {shared_state_violations}. Shared state causes cross-user data contamination.')
        for engine, _, _ in user_engines:
            try:
                await factory.cleanup_engine(engine)
            except Exception:
                pass

    async def test_high_concurrency_user_isolation_stress(self):
        """FAILING TEST: Stress test user isolation under high concurrent load

        BVJ: Enterprise - Ensures scalability with user isolation
        EXPECTED: FAIL - High concurrency should cause isolation failures
        ISSUE: Factory patterns fail under concurrent load causing isolation violations
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        num_concurrent_users = 15
        num_iterations = 3
        concurrency_violations = []
        for iteration in range(num_iterations):
            iteration_violations = []
            iteration_engines = []
            user_contexts = []
            for i in range(num_concurrent_users):
                context = UserExecutionContext(user_id=f'stress_user_{iteration}_{i}', run_id=f'stress_run_{iteration}_{i}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}', session_id=f'stress_session_{iteration}_{i}_{uuid.uuid4().hex[:8]}', request_id=f'stress_request_{iteration}_{i}_{uuid.uuid4().hex[:8]}')
                user_contexts.append(context)
                self.created_contexts.append(context)

            async def create_and_validate_engine(context, user_index):
                """Create engine and validate isolation under stress."""
                try:
                    start_time = time.time()
                    engine = await factory.create_for_user(context)
                    creation_time = time.time() - start_time
                    engine_context = engine.get_user_context()
                    if engine_context.user_id != context.user_id or engine_context.run_id != context.run_id or engine_context.session_id != context.session_id:
                        return {'success': False, 'user_index': user_index, 'violation_type': 'context_mismatch', 'expected_user_id': context.user_id, 'actual_user_id': engine_context.user_id, 'creation_time': creation_time}
                    return {'success': True, 'engine': engine, 'context': context, 'user_index': user_index, 'creation_time': creation_time}
                except Exception as e:
                    return {'success': False, 'user_index': user_index, 'violation_type': 'creation_failure', 'error': str(e), 'creation_time': time.time() - start_time if 'start_time' in locals() else 0}
            tasks = [create_and_validate_engine(ctx, i) for i, ctx in enumerate(user_contexts)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_engines = []
            failed_creations = []
            for result in results:
                if isinstance(result, dict):
                    if result['success']:
                        successful_engines.append(result)
                        iteration_engines.append(result['engine'])
                        self.created_engines.append(result['engine'])
                    else:
                        failed_creations.append(result)
                        iteration_violations.append(result)
                else:
                    failed_creations.append({'violation_type': 'exception_during_creation', 'error': str(result)})
            for i, engine_result1 in enumerate(successful_engines):
                for j, engine_result2 in enumerate(successful_engines):
                    if i != j:
                        engine1 = engine_result1['engine']
                        engine2 = engine_result2['engine']
                        context1 = engine1.get_user_context()
                        context2 = engine2.get_user_context()
                        if context1.user_id == context2.user_id or context1.run_id == context2.run_id or context1.session_id == context2.session_id:
                            iteration_violations.append({'violation_type': 'cross_engine_context_collision', 'engine1_user': engine_result1['user_index'], 'engine2_user': engine_result2['user_index'], 'colliding_user_id': context1.user_id == context2.user_id, 'colliding_run_id': context1.run_id == context2.run_id, 'colliding_session_id': context1.session_id == context2.session_id})
            if iteration_violations:
                concurrency_violations.append({'iteration': iteration, 'num_users': num_concurrent_users, 'successful_engines': len(successful_engines), 'failed_creations': len(failed_creations), 'violations': iteration_violations})
            for engine in iteration_engines:
                try:
                    await factory.cleanup_engine(engine)
                except Exception:
                    pass
        self.assertEqual(len(concurrency_violations), 0, f'CONCURRENCY ISOLATION VIOLATIONS: Found isolation violations in {len(concurrency_violations)} out of {num_iterations} high-concurrency iterations. Violations: {concurrency_violations}. Factory cannot maintain user isolation under concurrent load.')

    async def test_user_memory_isolation_contamination(self):
        """FAILING TEST: Reproduce memory contamination between user engines

        BVJ: Enterprise - Ensures memory isolation for data security
        EXPECTED: FAIL - User engines contaminate each other's memory
        ISSUE: Memory references shared between user execution contexts
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        except ImportError:
            self.fail('Cannot import ExecutionEngineFactory - SSOT consolidation incomplete')
        factory = ExecutionEngineFactory(websocket_bridge=None)
        self.factory_instances.append(factory)
        memory_contamination_violations = []
        user_engines = []
        num_users = 4
        for i in range(num_users):
            context = UserExecutionContext(user_id=f'memory_test_user_{i}', run_id=f'memory_test_run_{i}_{int(time.time() * 1000)}', session_id=f'memory_test_session_{i}', request_id=f'memory_test_request_{i}')
            self.created_contexts.append(context)
            engine = await factory.create_for_user(context)
            user_engines.append((engine, context, i))
            self.created_engines.append(engine)
        for engine, context, user_index in user_engines:
            unique_data = {'user_specific_data': f'user_{user_index}_secret_data_{uuid.uuid4().hex}', 'user_index': user_index, 'timestamp': time.time()}
            if hasattr(engine, '_user_memory_state'):
                engine._user_memory_state.update(unique_data)
            else:
                engine._user_memory_state = unique_data.copy()
        for i, (engine1, context1, user_index1) in enumerate(user_engines):
            for j, (engine2, context2, user_index2) in enumerate(user_engines):
                if i != j:
                    if hasattr(engine1, '_user_memory_state') and hasattr(engine2, '_user_memory_state'):
                        state1 = engine1._user_memory_state
                        state2 = engine2._user_memory_state
                        if state1 is state2:
                            memory_contamination_violations.append({'engine1_user': user_index1, 'engine2_user': user_index2, 'violation_type': 'shared_memory_reference', 'description': 'Engines share the same memory state object'})
                        if isinstance(state1, dict) and isinstance(state2, dict):
                            user1_data = state1.get('user_specific_data', '')
                            user2_data = state2.get('user_specific_data', '')
                            if user1_data in str(state2) and user1_data != user2_data:
                                memory_contamination_violations.append({'engine1_user': user_index1, 'engine2_user': user_index2, 'violation_type': 'cross_user_data_contamination', 'contaminated_data': user1_data, 'description': f'User {user_index1} data found in User {user_index2} memory'})
        self.assertEqual(len(memory_contamination_violations), 0, f'MEMORY CONTAMINATION DETECTED: Found {len(memory_contamination_violations)} instances of memory contamination between user engines. Violations: {memory_contamination_violations}. Memory contamination violates user data isolation.')
        for engine, _, _ in user_engines:
            try:
                await factory.cleanup_engine(engine)
            except Exception:
                pass

    def _log_test_failure_details(self, test_name: str, failure_details: Dict[str, Any]):
        """Log detailed test failure information for analysis."""
        print(f'\n=== EXECUTION ENGINE FACTORY USER ISOLATION VIOLATION: {test_name} ===')
        print(f'Timestamp: {datetime.now().isoformat()}')
        print(f'Business Impact: HIPAA/SOC2 compliance violation - Enterprise contracts at risk')
        print(f'Issue: #884 Execution Engine Factory User Isolation Failures')
        print('\nFailure Details:')
        for key, value in failure_details.items():
            print(f'  {key}: {value}')
        print('\nCompliance Impact:')
        print('- HIPAA: Cross-user data contamination violates healthcare data protection')
        print('- SOC2: User isolation failures violate security control requirements')
        print('- SEC: Financial data isolation violations for financial services')
        print('\nNext Steps:')
        print('1. Implement proper user context isolation in ExecutionEngineFactory')
        print('2. Remove shared state between user execution engines')
        print('3. Ensure memory isolation between concurrent users')
        print('4. Validate enterprise-grade user isolation under stress')
        print('5. Re-run tests to validate compliance fixes')
        print('=' * 60)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')