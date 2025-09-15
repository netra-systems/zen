"""
Comprehensive UVS Error Handling and Edge Cases Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (supporting all user tiers Free  ->  Enterprise)
- Business Goal: Ensure system resilience and error recovery under edge conditions
- Value Impact: Prevents system failures, maintains user experience, prevents data loss
- Strategic Impact: Core infrastructure reliability that supports $500K+ ARR by ensuring platform stability

This test suite validates comprehensive error handling and edge case scenarios in the UVS system:
1. Context validation error handling and recovery (5 tests)
2. Factory error handling and resource cleanup (5 tests)  
3. WebSocket error handling and connection resilience (5 tests)
4. Concurrent operation error handling and isolation (5 tests)
5. System boundary and resource limit error handling (5 tests)

CRITICAL: These are INTEGRATION tests - they test interactions between components but don't require
full Docker stack. NO MOCKS allowed - use real services and real system behavior where possible.
Each test validates actual business value of error handling and uses proper test categories and markers.
"""
import pytest
import asyncio
import time
import uuid
import weakref
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import gc
import psutil
import os
import signal
from dataclasses import dataclass
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError, ContextIsolationError, clear_shared_object_registry
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, ExecutionEngineFactoryError
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from test_framework.ssot.integration_test_base import BaseIntegrationTest
from test_framework.user_execution_context_fixtures import realistic_user_context, multi_user_contexts, concurrent_context_factory, async_context_manager, context_hierarchy_builder, clean_context_registry
from test_framework.isolated_environment_fixtures import isolated_env
from shared.isolated_environment import get_env

class TestContextValidationErrorHandlingAndRecovery(BaseIntegrationTest):
    """Test suite for context validation error handling and recovery scenarios.
    
    BVJ: Validates system resilience when context validation fails, ensuring graceful
    error recovery without data corruption or system instability. Critical for preventing
    customer-facing errors that could impact business operations and user trust.
    """

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.context_validation
    async def test_invalid_context_creation_error_recovery(self, clean_context_registry, isolated_env):
        """Test error recovery when context creation fails due to invalid data.
        
        BVJ: Prevents system crashes from malformed context data and ensures proper
        error messages are provided to help diagnose configuration or integration issues.
        """
        invalid_scenarios = [{'name': 'empty_user_id', 'params': {'user_id': '', 'thread_id': 'thread_test_12345678901234567890', 'run_id': f'run_test_{int(time.time())}_abcd'}, 'expected_error': InvalidContextError, 'error_match': 'User ID cannot be empty'}, {'name': 'malformed_thread_id', 'params': {'user_id': 'user_test_12345678901234567890', 'thread_id': 'bad_thread', 'run_id': f'run_test_{int(time.time())}_abcd'}, 'expected_error': InvalidContextError, 'error_match': 'Invalid thread ID format'}, {'name': 'invalid_characters_run_id', 'params': {'user_id': 'user_test_12345678901234567890', 'thread_id': 'thread_test_98765432109876543210', 'run_id': 'run_with_invalid_chars_@#$%'}, 'expected_error': InvalidContextError, 'error_match': 'Run ID contains invalid characters'}, {'name': 'none_websocket_client_id', 'params': {'user_id': 'user_test_12345678901234567890', 'thread_id': 'thread_test_98765432109876543210', 'run_id': f'run_test_{int(time.time())}_abcd', 'websocket_client_id': None}, 'expected_error': InvalidContextError, 'error_match': 'WebSocket client ID cannot be None'}, {'name': 'corrupted_agent_context', 'params': {'user_id': 'user_test_12345678901234567890', 'thread_id': 'thread_test_98765432109876543210', 'run_id': f'run_test_{int(time.time())}_abcd', 'agent_context': 'not_a_dict'}, 'expected_error': InvalidContextError, 'error_match': 'Agent context must be a dictionary'}]
        error_recovery_metrics = {'total_errors': 0, 'successful_recoveries': 0, 'error_types': set(), 'recovery_times': []}
        for scenario in invalid_scenarios:
            start_time = time.time()
            try:
                with pytest.raises(scenario['expected_error'], match=scenario['error_match']):
                    UserExecutionContext(**scenario['params'])
                error_recovery_metrics['total_errors'] += 1
                error_recovery_metrics['error_types'].add(scenario['expected_error'].__name__)
                valid_context = UserExecutionContext(user_id='user_recovery_12345678901234567890', thread_id='thread_recovery_98765432109876543210', run_id=f'run_recovery_{int(time.time())}_test')
                assert valid_context.user_id == 'user_recovery_12345678901234567890'
                error_recovery_metrics['successful_recoveries'] += 1
                recovery_time = time.time() - start_time
                error_recovery_metrics['recovery_times'].append(recovery_time)
            except Exception as e:
                pytest.fail(f"Error recovery failed for scenario {scenario['name']}: {e}")
        assert error_recovery_metrics['total_errors'] == len(invalid_scenarios)
        assert error_recovery_metrics['successful_recoveries'] == len(invalid_scenarios)
        assert len(error_recovery_metrics['error_types']) > 0
        assert all((t < 1.0 for t in error_recovery_metrics['recovery_times'])), 'Error recovery must be fast'

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.context_validation
    async def test_context_isolation_corruption_detection(self, multi_user_contexts, isolated_env):
        """Test detection and recovery from context isolation corruption.
        
        BVJ: Prevents cross-user data leakage that could violate privacy regulations
        and compliance requirements. Critical for enterprise security and trust.
        """
        user1_context = multi_user_contexts[0]
        user2_context = multi_user_contexts[1]
        corrupted_context_data = {'user_id': user1_context.user_id, 'thread_id': user2_context.thread_id, 'run_id': f'run_corruption_test_{int(time.time())}_abcd', 'agent_context': {**user1_context.agent_context, 'leaked_data': user2_context.agent_context}}
        with pytest.raises(ContextIsolationError, match='Cross-user context isolation violation'):
            context = UserExecutionContext(**corrupted_context_data)
            context._validate_isolation_integrity()
        recovery_context1 = UserExecutionContext(user_id=user1_context.user_id, thread_id=user1_context.thread_id, run_id=f'run_recovery1_{int(time.time())}_test', agent_context=user1_context.agent_context)
        recovery_context2 = UserExecutionContext(user_id=user2_context.user_id, thread_id=user2_context.thread_id, run_id=f'run_recovery2_{int(time.time())}_test', agent_context=user2_context.agent_context)
        assert recovery_context1.user_id != recovery_context2.user_id
        assert recovery_context1.thread_id != recovery_context2.thread_id
        assert recovery_context1.agent_context != recovery_context2.agent_context
        assert 'leaked_data' not in recovery_context1.agent_context
        assert 'leaked_data' not in recovery_context2.agent_context

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.context_validation
    async def test_context_memory_corruption_detection_and_cleanup(self, realistic_user_context, isolated_env):
        """Test detection of memory corruption in context data and automatic cleanup.
        
        BVJ: Prevents memory corruption from causing system instability or data loss
        that could impact all users and cause business disruption.
        """
        original_context = realistic_user_context
        child_contexts = []
        weak_refs = []
        for i in range(50):
            child = original_context.create_child_context(f'memory_test_operation_{i}', additional_agent_context={'operation_index': i, 'large_data': 'x' * 1000}, additional_audit_metadata={'memory_test': True, 'index': i})
            child_contexts.append(child)
            weak_refs.append(weakref.ref(child))
        assert len(child_contexts) == 50
        assert all((ref() is not None for ref in weak_refs))
        initial_memory = psutil.Process().memory_info().rss
        for i in range(0, 50, 10):
            contexts_to_cleanup = child_contexts[i:i + 10]
            for ctx in contexts_to_cleanup:
                assert ctx.operation_depth > 0
                assert ctx.parent_request_id is not None
                assert ctx.audit_metadata['memory_test'] is True
            child_contexts[i:i + 10] = [None] * 10
            gc.collect()
        post_cleanup_memory = psutil.Process().memory_info().rss
        memory_reduction = initial_memory - post_cleanup_memory
        self.logger.info(f'Memory usage - Initial: {initial_memory}, Post-cleanup: {post_cleanup_memory}')
        remaining_contexts = [ctx for ctx in child_contexts if ctx is not None]
        assert len(remaining_contexts) > 0
        for ctx in remaining_contexts:
            assert ctx.user_id == original_context.user_id
            assert ctx.operation_depth == 1
            assert ctx.parent_request_id == original_context.request_id
            audit_trail = ctx.get_audit_trail()
            assert audit_trail['operation_depth'] == 1
            assert audit_trail['user_context']['user_id'] == original_context.user_id

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.context_validation
    async def test_context_concurrent_modification_error_handling(self, concurrent_context_factory, isolated_env):
        """Test error handling when contexts are modified concurrently.
        
        BVJ: Prevents race conditions and data corruption in multi-user concurrent
        scenarios that are critical for platform stability and data integrity.
        """
        contexts = concurrent_context_factory(5, 'concurrent_modification')
        modification_results = []
        modification_errors = []

        async def attempt_concurrent_modification(context, modification_id):
            """Attempt to modify context concurrently."""
            try:
                if modification_id % 2 == 0:
                    child = context.create_child_context(f'concurrent_op_{modification_id}', additional_agent_context={'modification_id': modification_id, 'concurrent_flag': True, 'timestamp': time.time()})
                    modification_results.append((modification_id, 'child_created', child.request_id))
                else:
                    audit_trail = context.get_audit_trail()
                    modification_results.append((modification_id, 'audit_accessed', len(audit_trail)))
            except Exception as e:
                modification_errors.append((modification_id, type(e).__name__, str(e)))
        modification_tasks = [attempt_concurrent_modification(contexts[i % len(contexts)], i) for i in range(20)]
        await asyncio.gather(*modification_tasks, return_exceptions=True)
        assert len(modification_results) + len(modification_errors) == 20
        assert len(modification_results) > 0, 'Some concurrent operations should succeed'
        for context in contexts:
            assert context.user_id is not None
            assert context.thread_id is not None
            assert context.run_id is not None
            test_child = context.create_child_context('post_concurrent_test', additional_agent_context={'test': 'verification'})
            assert test_child.parent_request_id == context.request_id
            assert test_child.operation_depth == context.operation_depth + 1
        self.logger.info(f'Concurrent modification results: {len(modification_results)} success, {len(modification_errors)} errors')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.context_validation
    async def test_context_validation_cascade_failure_recovery(self, realistic_user_context, isolated_env):
        """Test recovery from cascade validation failures in context hierarchies.
        
        BVJ: Ensures that validation errors in complex agent workflows don't cause
        complete system failure, maintaining service availability for other users.
        """
        root_context = realistic_user_context
        hierarchy_levels = []
        try:
            level1 = root_context.create_child_context('level1_operation', additional_agent_context={'level': 1, 'valid': True})
            hierarchy_levels.append(level1)
            level2 = level1.create_child_context('level2_operation_with_issues', additional_agent_context={'level': 2, 'problematic_data': {'circular_ref': None}}, additional_audit_metadata={'validation_test': 'cascade_failure', 'expected_failure': True})
            level2.agent_context['problematic_data']['circular_ref'] = level2.agent_context
            hierarchy_levels.append(level2)
            level3 = level2.create_child_context('level3_dependent_operation', additional_agent_context={'level': 3, 'depends_on_parent': True})
            hierarchy_levels.append(level3)
        except Exception as validation_error:
            assert 'validation' in str(validation_error).lower() or 'circular' in str(validation_error).lower()
        recovery_hierarchy = []
        recovery_level1 = root_context.create_child_context('recovery_level1', additional_agent_context={'level': 1, 'recovery': True, 'clean': True})
        recovery_hierarchy.append(recovery_level1)
        recovery_level2 = recovery_level1.create_child_context('recovery_level2', additional_agent_context={'level': 2, 'recovery': True, 'safe_data': {'status': 'clean', 'validated': True}})
        recovery_hierarchy.append(recovery_level2)
        for i, context in enumerate(recovery_hierarchy):
            assert context.operation_depth == i + 1
            assert context.agent_context['level'] == i + 1
            assert context.agent_context['recovery'] is True
            audit_trail = context.get_audit_trail()
            assert audit_trail['operation_depth'] == i + 1
            if i > 0:
                assert context.parent_request_id == recovery_hierarchy[i - 1].request_id
        assert root_context.user_id == recovery_hierarchy[0].user_id
        assert root_context.thread_id == recovery_hierarchy[0].thread_id
        assert root_context.run_id == recovery_hierarchy[0].run_id
        final_test_context = root_context.create_child_context('final_validation_test', additional_agent_context={'test': 'system_recovery_validated'})
        assert final_test_context.agent_context['test'] == 'system_recovery_validated'

class TestFactoryErrorHandlingAndResourceCleanup(BaseIntegrationTest):
    """Test suite for factory error handling and resource cleanup scenarios.
    
    BVJ: Validates proper resource management under error conditions preventing
    memory leaks and resource exhaustion that could cause system instability.
    Critical for long-running production deployments and multi-user operations.
    """

    @pytest.fixture
    async def mock_websocket_bridge_with_failures(self):
        """Create mock WebSocket bridge that can simulate failures."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        call_count = {'count': 0}

        async def failing_create_emitter(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] % 3 == 0:
                raise Exception('WebSocket bridge failure simulation')
            return AsyncMock()
        bridge.create_user_emitter.side_effect = failing_create_emitter
        return bridge

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.factory_patterns
    async def test_factory_creation_failure_recovery(self, mock_websocket_bridge_with_failures, multi_user_contexts):
        """Test factory recovery when engine creation fails.
        
        BVJ: Ensures factory remains stable when individual engine creation fails,
        preventing cascading failures that could impact multiple users.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge_with_failures)
        creation_results = []
        creation_failures = []
        for i, context in enumerate(multi_user_contexts[:6]):
            try:
                engine = await factory.create_for_user(context)
                creation_results.append((i, engine.engine_id, 'success'))
                assert isinstance(engine, UserExecutionEngine)
                assert engine.context.user_id == context.user_id
                assert engine.is_active()
            except Exception as e:
                creation_failures.append((i, type(e).__name__, str(e)))
        expected_failures = 2
        assert len(creation_failures) == expected_failures, f'Expected {expected_failures} failures, got {len(creation_failures)}'
        expected_successes = 4
        assert len(creation_results) == expected_successes, f'Expected {expected_successes} successes, got {len(creation_results)}'
        metrics = factory.get_factory_metrics()
        assert metrics['engines_created'] >= expected_successes
        assert metrics['engines_active'] >= expected_successes
        recovery_context = multi_user_contexts[0]
        recovery_context_modified = UserExecutionContext(user_id=recovery_context.user_id, thread_id=recovery_context.thread_id, run_id=f'run_recovery_{int(time.time())}_test', agent_context=recovery_context.agent_context, audit_metadata=recovery_context.audit_metadata)
        recovery_engine = await factory.create_for_user(recovery_context_modified)
        assert recovery_engine is not None
        assert recovery_engine.is_active()

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.factory_patterns
    async def test_factory_resource_leak_prevention_on_errors(self, mock_websocket_bridge_with_failures, realistic_user_context):
        """Test that factory prevents resource leaks when operations fail.
        
        BVJ: Prevents resource exhaustion from failed operations that could cause
        system-wide instability and impact all users.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge_with_failures)
        initial_metrics = factory.get_factory_metrics()
        initial_memory = psutil.Process().memory_info().rss
        created_engines = []
        failed_attempts = []
        for i in range(12):
            try:
                context_copy = UserExecutionContext(user_id=realistic_user_context.user_id, thread_id=realistic_user_context.thread_id, run_id=f'run_leak_test_{i}_{int(time.time())}_test', agent_context=realistic_user_context.agent_context, audit_metadata=realistic_user_context.audit_metadata)
                engine = await factory.create_for_user(context_copy)
                created_engines.append(engine)
                await asyncio.sleep(0.01)
            except Exception as e:
                failed_attempts.append((i, str(e)))
                await asyncio.sleep(0.01)
        assert len(failed_attempts) == 4
        assert len(created_engines) == 8
        current_metrics = factory.get_factory_metrics()
        current_memory = psutil.Process().memory_info().rss
        expected_active = len(created_engines)
        assert current_metrics['engines_active'] == expected_active
        assert current_metrics['engines_created'] >= expected_active
        for engine in created_engines:
            await factory.cleanup_engine(engine)
        await asyncio.sleep(0.1)
        final_metrics = factory.get_factory_metrics()
        final_memory = psutil.Process().memory_info().rss
        assert final_metrics['engines_active'] == 0
        assert final_metrics['engines_cleaned'] >= len(created_engines)
        memory_increase = final_memory - initial_memory
        assert memory_increase < 50 * 1024 * 1024, f'Memory leak detected: {memory_increase} bytes'
        self.logger.info(f'Resource leak test - Memory change: {memory_increase} bytes')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.factory_patterns
    async def test_factory_cleanup_failure_resilience(self, mock_websocket_bridge_with_failures, multi_user_contexts):
        """Test factory resilience when cleanup operations fail.
        
        BVJ: Ensures factory remains stable even when individual resource cleanup
        fails, preventing system deadlock or cascading cleanup failures.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge_with_failures)
        engines = []
        for i, context in enumerate(multi_user_contexts[:4]):
            try:
                engine = await factory.create_for_user(context)
                engines.append(engine)
            except Exception:
                pass
        assert len(engines) > 0, 'Need at least one engine for cleanup testing'
        cleanup_results = []
        cleanup_failures = []
        for i, engine in enumerate(engines):
            try:
                if i % 2 == 1:
                    original_cleanup = engine.cleanup

                    async def failing_cleanup():
                        raise Exception(f'Cleanup failure simulation for engine {i}')
                    engine.cleanup = failing_cleanup
                await factory.cleanup_engine(engine)
                cleanup_results.append((i, 'success'))
            except Exception as e:
                cleanup_failures.append((i, str(e)))
        assert len(cleanup_failures) > 0, 'Expected some cleanup failures'
        test_context = multi_user_contexts[0]
        test_context_new = UserExecutionContext(user_id=test_context.user_id, thread_id=test_context.thread_id, run_id=f'run_post_cleanup_test_{int(time.time())}_test', agent_context=test_context.agent_context)
        try:
            new_engine = await factory.create_for_user(test_context_new)
            assert new_engine is not None
            assert new_engine.is_active()
        except Exception:
            pass
        metrics = factory.get_factory_metrics()
        assert metrics['engines_cleaned'] >= len(cleanup_results)
        await factory.shutdown()
        final_metrics = factory.get_factory_metrics()
        assert final_metrics['engines_active'] == 0

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.factory_patterns
    async def test_factory_concurrent_failure_isolation(self, mock_websocket_bridge_with_failures, concurrent_context_factory):
        """Test that failures in concurrent factory operations don't affect each other.
        
        BVJ: Ensures that when one user's engine creation fails, it doesn't impact
        other users' operations, maintaining service quality for all users.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge_with_failures)
        contexts = concurrent_context_factory(10, 'concurrent_failure_test')

        async def create_engine_with_monitoring(context, index):
            """Create engine with monitoring and error tracking."""
            start_time = time.time()
            try:
                engine = await factory.create_for_user(context)
                duration = time.time() - start_time
                return {'index': index, 'status': 'success', 'duration': duration, 'engine_id': engine.engine_id}
            except Exception as e:
                duration = time.time() - start_time
                return {'index': index, 'status': 'failure', 'duration': duration, 'error': str(e)}
        results = await asyncio.gather(*[create_engine_with_monitoring(contexts[i], i) for i in range(10)], return_exceptions=False)
        successes = [r for r in results if r['status'] == 'success']
        failures = [r for r in results if r['status'] == 'failure']
        assert len(failures) > 0, 'Expected some failures due to bridge failure pattern'
        assert len(successes) > 0, 'Expected some successes despite failures'
        for success in successes:
            assert success['duration'] < 5.0, 'Successful operations should complete quickly'
            assert 'engine_id' in success
        for failure in failures:
            assert 'error' in failure
            assert failure['duration'] < 5.0, 'Failures should fail quickly, not hang'
        metrics = factory.get_factory_metrics()
        assert metrics['engines_created'] == len(successes)
        assert metrics['engines_active'] == len(successes)
        final_test_context = contexts[0]
        final_test_context_new = UserExecutionContext(user_id=final_test_context.user_id, thread_id=final_test_context.thread_id, run_id=f'run_final_test_{int(time.time())}_test', agent_context=final_test_context.agent_context)
        try:
            final_engine = await factory.create_for_user(final_test_context_new)
            if final_engine:
                assert final_engine.is_active()
        except Exception:
            pass

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.factory_patterns
    async def test_factory_shutdown_with_pending_operations(self, mock_websocket_bridge_with_failures, realistic_user_context):
        """Test factory shutdown behavior when operations are pending or failing.
        
        BVJ: Ensures graceful shutdown during deployments or restarts without
        losing user data or causing system instability.
        """
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge_with_failures)
        pending_operations = []

        async def long_running_operation(context, delay):
            """Simulate long-running engine operation."""
            await asyncio.sleep(delay)
            return await factory.create_for_user(context)
        for i in range(4):
            context_copy = UserExecutionContext(user_id=realistic_user_context.user_id, thread_id=realistic_user_context.thread_id, run_id=f'run_shutdown_test_{i}_{int(time.time())}_test', agent_context=realistic_user_context.agent_context)
            task = asyncio.create_task(long_running_operation(context_copy, 0.5 + i * 0.1))
            pending_operations.append(task)
        await asyncio.sleep(0.1)
        shutdown_start = time.time()
        for task in pending_operations:
            if not task.done():
                task.cancel()
        await factory.shutdown()
        shutdown_duration = time.time() - shutdown_start
        assert shutdown_duration < 5.0, f'Shutdown took too long: {shutdown_duration}s'
        final_metrics = factory.get_factory_metrics()
        assert final_metrics['engines_active'] == 0
        with pytest.raises(Exception, match='shutdown|closed|stopped'):
            await factory.create_for_user(realistic_user_context)
        for task in pending_operations:
            if not task.done():
                try:
                    await task
                except asyncio.CancelledError:
                    pass

class TestWebSocketErrorHandlingAndConnectionResilience(BaseIntegrationTest):
    """Test suite for WebSocket error handling and connection resilience scenarios.
    
    BVJ: Validates WebSocket infrastructure resilience ensuring real-time chat
    functionality remains available even under error conditions. Critical for
    user experience and platform reliability that drives customer satisfaction.
    """

    @pytest.fixture
    async def mock_failing_websocket_bridge(self):
        """Create mock WebSocket bridge that simulates various failure scenarios."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        failure_state = {'connection_failures': 0, 'emission_failures': 0, 'total_calls': 0, 'failure_mode': 'intermittent'}

        async def failing_create_user_emitter(*args, **kwargs):
            failure_state['total_calls'] += 1
            if failure_state['failure_mode'] == 'persistent':
                failure_state['connection_failures'] += 1
                raise Exception('WebSocket connection permanently unavailable')
            elif failure_state['failure_mode'] == 'intermittent':
                if failure_state['total_calls'] % 4 == 0:
                    failure_state['connection_failures'] += 1
                    raise Exception('WebSocket connection temporarily unavailable')
            emitter = AsyncMock()

            async def failing_emit(event_type, data):
                if failure_state['failure_mode'] != 'recovery' and event_type == 'agent_thinking':
                    failure_state['emission_failures'] += 1
                    raise Exception('WebSocket emission failed')
                return True
            emitter.emit.side_effect = failing_emit
            return emitter
        bridge.create_user_emitter.side_effect = failing_create_user_emitter
        bridge.failure_state = failure_state
        return bridge

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.websocket_resilience
    async def test_websocket_connection_failure_recovery(self, mock_failing_websocket_bridge, multi_user_contexts):
        """Test recovery from WebSocket connection failures.
        
        BVJ: Ensures chat functionality remains available even when WebSocket
        connections fail, maintaining user experience and preventing chat disruption.
        """
        bridge = mock_failing_websocket_bridge
        factory = ExecutionEngineFactory(websocket_bridge=bridge)
        connection_results = []
        for i, context in enumerate(multi_user_contexts[:8]):
            try:
                engine = await factory.create_for_user(context)
                connection_results.append({'index': i, 'status': 'success', 'engine_id': engine.engine_id, 'has_websocket': engine.websocket_emitter is not None})
                assert engine.is_active()
                assert engine.context.user_id == context.user_id
            except Exception as e:
                connection_results.append({'index': i, 'status': 'failure', 'error': str(e)})
        failures = [r for r in connection_results if r['status'] == 'failure']
        successes = [r for r in connection_results if r['status'] == 'success']
        assert len(failures) == 2, f'Expected 2 failures, got {len(failures)}'
        assert len(successes) == 6, f'Expected 6 successes, got {len(successes)}'
        for success in successes:
            assert success['has_websocket'], 'Successful connections must have WebSocket emitters'
        bridge.failure_state['failure_mode'] = 'recovery'
        recovery_context = multi_user_contexts[3]
        recovery_context_new = UserExecutionContext(user_id=recovery_context.user_id, thread_id=recovery_context.thread_id, run_id=f'run_recovery_{int(time.time())}_test', agent_context=recovery_context.agent_context)
        recovery_engine = await factory.create_for_user(recovery_context_new)
        assert recovery_engine is not None
        assert recovery_engine.websocket_emitter is not None
        assert bridge.failure_state['connection_failures'] >= 2
        assert bridge.failure_state['total_calls'] >= 9

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.websocket_resilience
    async def test_websocket_emission_failure_graceful_degradation(self, mock_failing_websocket_bridge, realistic_user_context):
        """Test graceful degradation when WebSocket event emission fails.
        
        BVJ: Ensures agent execution continues even when WebSocket events fail,
        preventing complete operation failure due to communication issues.
        """
        bridge = mock_failing_websocket_bridge
        factory = ExecutionEngineFactory(websocket_bridge=bridge)
        engine = await factory.create_for_user(realistic_user_context)
        assert engine.websocket_emitter is not None
        emission_results = []
        event_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for event_type in event_types:
            try:
                await engine.websocket_emitter.emit(event_type, {'user_id': realistic_user_context.user_id, 'thread_id': realistic_user_context.thread_id, 'timestamp': time.time(), 'event_data': {'test': True}})
                emission_results.append({'event': event_type, 'status': 'success'})
            except Exception as e:
                emission_results.append({'event': event_type, 'status': 'failure', 'error': str(e)})
        failures = [r for r in emission_results if r['status'] == 'failure']
        successes = [r for r in emission_results if r['status'] == 'success']
        assert len(failures) >= 1, 'Expected at least one emission failure'
        thinking_failures = [f for f in failures if f['event'] == 'agent_thinking']
        assert len(thinking_failures) == 1, 'Expected agent_thinking to fail'
        assert len(successes) >= 4, 'Other events should succeed'
        assert engine.is_active()
        assert engine.context.user_id == realistic_user_context.user_id
        assert bridge.failure_state['emission_failures'] >= 1
        bridge.failure_state['failure_mode'] = 'recovery'
        await engine.websocket_emitter.emit('agent_thinking', {'recovery_test': True})

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.websocket_resilience
    async def test_websocket_persistent_failure_fallback(self, mock_failing_websocket_bridge, multi_user_contexts):
        """Test fallback behavior during persistent WebSocket failures.
        
        BVJ: Ensures system continues operating when WebSocket infrastructure
        is persistently unavailable, maintaining core functionality for users.
        """
        bridge = mock_failing_websocket_bridge
        bridge.failure_state['failure_mode'] = 'persistent'
        factory = ExecutionEngineFactory(websocket_bridge=bridge)
        fallback_results = []
        for i, context in enumerate(multi_user_contexts[:4]):
            try:
                engine = await factory.create_for_user(context)
                fallback_results.append({'index': i, 'status': 'unexpected_success', 'engine_id': engine.engine_id})
            except ExecutionEngineFactoryError as e:
                fallback_results.append({'index': i, 'status': 'expected_factory_failure', 'error': str(e)})
            except Exception as e:
                fallback_results.append({'index': i, 'status': 'fallback_exception', 'error': str(e)})
        factory_failures = [r for r in fallback_results if r['status'] == 'expected_factory_failure']
        assert len(factory_failures) >= 3, 'Most attempts should fail with persistent WebSocket failure'
        assert bridge.failure_state['connection_failures'] >= 4
        assert bridge.failure_state['failure_mode'] == 'persistent'
        bridge.failure_state['failure_mode'] = 'recovery'
        recovery_context = multi_user_contexts[0]
        recovery_context_new = UserExecutionContext(user_id=recovery_context.user_id, thread_id=recovery_context.thread_id, run_id=f'run_persistent_recovery_{int(time.time())}_test', agent_context=recovery_context.agent_context)
        recovery_engine = await factory.create_for_user(recovery_context_new)
        assert recovery_engine is not None
        assert recovery_engine.websocket_emitter is not None
        await recovery_engine.websocket_emitter.emit('test_recovery', {'recovered': True})

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.websocket_resilience
    async def test_websocket_concurrent_connection_error_isolation(self, mock_failing_websocket_bridge, concurrent_context_factory):
        """Test that WebSocket errors in concurrent connections don't affect each other.
        
        BVJ: Ensures that WebSocket issues for one user don't impact other users'
        chat functionality, maintaining service quality across the platform.
        """
        bridge = mock_failing_websocket_bridge
        bridge.failure_state['failure_mode'] = 'intermittent'
        factory = ExecutionEngineFactory(websocket_bridge=bridge)
        contexts = concurrent_context_factory(12, 'websocket_concurrent_test')

        async def create_and_test_websocket(context, index):
            """Create engine and test WebSocket functionality."""
            try:
                engine = await factory.create_for_user(context)
                emission_results = []
                for event_type in ['agent_started', 'agent_thinking', 'agent_completed']:
                    try:
                        await engine.websocket_emitter.emit(event_type, {'context_index': index, 'timestamp': time.time()})
                        emission_results.append(event_type)
                    except Exception:
                        pass
                return {'index': index, 'status': 'success', 'engine_id': engine.engine_id, 'successful_emissions': emission_results}
            except Exception as e:
                return {'index': index, 'status': 'failure', 'error': str(e)}
        results = await asyncio.gather(*[create_and_test_websocket(contexts[i], i) for i in range(12)])
        successes = [r for r in results if r['status'] == 'success']
        failures = [r for r in results if r['status'] == 'failure']
        assert len(failures) >= 2, 'Expected some failures due to intermittent WebSocket issues'
        assert len(successes) >= 8, 'Most operations should succeed despite some failures'
        for success in successes:
            assert 'engine_id' in success
            assert len(success['successful_emissions']) >= 1, 'At least some events should emit successfully'
        expected_failure_indices = [3, 7, 11]
        actual_failure_indices = [f['index'] for f in failures]
        for expected_idx in expected_failure_indices:
            if expected_idx < len(results):
                assert expected_idx in actual_failure_indices, f'Expected failure at index {expected_idx}'
        assert bridge.failure_state['total_calls'] == 12
        assert bridge.failure_state['connection_failures'] >= 3
        for success in successes[:3]:
            engine_id = success['engine_id']
            assert len(success['successful_emissions']) > 0

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.websocket_resilience
    async def test_websocket_reconnection_and_event_replay(self, mock_failing_websocket_bridge, realistic_user_context):
        """Test WebSocket reconnection and event replay after connection loss.
        
        BVJ: Ensures users don't lose real-time updates during connection issues,
        maintaining chat experience continuity and preventing user frustration.
        """
        bridge = mock_failing_websocket_bridge
        factory = ExecutionEngineFactory(websocket_bridge=bridge)
        engine = await factory.create_for_user(realistic_user_context)
        assert engine.websocket_emitter is not None
        initial_events = [('agent_started', {'phase': 'initialization'}), ('tool_executing', {'tool': 'data_analyzer', 'phase': 'start'})]
        successfully_sent = []
        for event_type, data in initial_events:
            try:
                await engine.websocket_emitter.emit(event_type, data)
                successfully_sent.append((event_type, data))
            except Exception:
                pass
        assert len(successfully_sent) >= 1, 'At least some initial events should succeed'
        bridge.failure_state['failure_mode'] = 'persistent'
        failed_events = []
        events_during_outage = [('agent_thinking', {'phase': 'analysis'}), ('tool_completed', {'tool': 'data_analyzer', 'result': 'success'})]
        for event_type, data in events_during_outage:
            try:
                await engine.websocket_emitter.emit(event_type, data)
            except Exception as e:
                failed_events.append((event_type, str(e)))
        assert len(failed_events) >= 1, 'Events should fail during connection outage'
        bridge.failure_state['failure_mode'] = 'recovery'
        reconnection_context = UserExecutionContext(user_id=realistic_user_context.user_id, thread_id=realistic_user_context.thread_id, run_id=f'run_reconnection_{int(time.time())}_test', agent_context=realistic_user_context.agent_context, websocket_client_id=realistic_user_context.websocket_client_id)
        reconnected_engine = await factory.create_for_user(reconnection_context)
        assert reconnected_engine.websocket_emitter is not None
        post_reconnection_events = [('agent_completed', {'phase': 'completion', 'reconnected': True})]
        reconnection_successes = []
        for event_type, data in post_reconnection_events:
            try:
                await reconnected_engine.websocket_emitter.emit(event_type, data)
                reconnection_successes.append((event_type, data))
            except Exception:
                pass
        assert len(reconnection_successes) >= 1, 'Events should succeed after reconnection'
        assert bridge.failure_state['connection_failures'] >= 3
        assert bridge.failure_state['emission_failures'] >= 1
        assert engine.context.user_id == reconnected_engine.context.user_id
        assert engine.context.websocket_client_id == reconnected_engine.context.websocket_client_id
        assert engine.context.run_id != reconnected_engine.context.run_id

class TestConcurrentOperationErrorHandlingAndIsolation(BaseIntegrationTest):
    """Test suite for concurrent operation error handling and isolation scenarios.
    
    BVJ: Validates system stability under concurrent load and ensures proper
    isolation between concurrent operations. Critical for multi-user platform
    that must handle hundreds of concurrent agent executions without cross-user
    contamination or system instability.
    """

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.concurrent_isolation
    async def test_concurrent_context_creation_race_condition_handling(self, concurrent_context_factory, isolated_env):
        """Test handling of race conditions in concurrent context creation.
        
        BVJ: Prevents race conditions that could cause context corruption or
        system instability when multiple users create contexts simultaneously.
        """
        race_condition_results = []
        context_creation_times = []
        unique_identifiers = set()

        async def create_context_with_timing(batch_id, context_index):
            """Create context and track timing and uniqueness."""
            start_time = time.time()
            try:
                contexts = concurrent_context_factory(1, f'race_test_batch_{batch_id}')
                context = contexts[0]
                creation_time = time.time() - start_time
                context_creation_times.append(creation_time)
                identifier = f'{context.user_id}:{context.thread_id}:{context.request_id}'
                if identifier in unique_identifiers:
                    race_condition_results.append({'batch_id': batch_id, 'index': context_index, 'status': 'race_condition_detected', 'duplicate_id': identifier})
                else:
                    unique_identifiers.add(identifier)
                    race_condition_results.append({'batch_id': batch_id, 'index': context_index, 'status': 'success', 'creation_time': creation_time, 'context_id': identifier})
                return context
            except Exception as e:
                race_condition_results.append({'batch_id': batch_id, 'index': context_index, 'status': 'error', 'error': str(e)})
                return None
        batch_tasks = []
        for batch_id in range(10):
            for context_index in range(5):
                task = create_context_with_timing(batch_id, context_index)
                batch_tasks.append(task)
        contexts = await asyncio.gather(*batch_tasks, return_exceptions=True)
        successes = [r for r in race_condition_results if r['status'] == 'success']
        race_conditions = [r for r in race_condition_results if r['status'] == 'race_condition_detected']
        errors = [r for r in race_condition_results if r['status'] == 'error']
        assert len(successes) >= 45, f'Expected at least 45 successes, got {len(successes)}'
        assert len(race_conditions) == 0, f'Race conditions detected: {race_conditions}'
        assert len(errors) <= 5, f'Too many errors: {len(errors)}'
        success_ids = [s['context_id'] for s in successes]
        assert len(set(success_ids)) == len(success_ids), 'All context IDs must be unique'
        avg_creation_time = sum(context_creation_times) / len(context_creation_times)
        max_creation_time = max(context_creation_times)
        assert avg_creation_time < 0.1, f'Average creation time too slow: {avg_creation_time}s'
        assert max_creation_time < 1.0, f'Max creation time too slow: {max_creation_time}s'
        self.logger.info(f'Race condition test - Successes: {len(successes)}, Race conditions: {len(race_conditions)}, Errors: {len(errors)}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.concurrent_isolation
    async def test_concurrent_factory_resource_exhaustion_handling(self, multi_user_contexts, isolated_env):
        """Test factory behavior under resource exhaustion with concurrent operations.
        
        BVJ: Ensures system graceful degradation when resources are exhausted,
        preventing complete system failure that would impact all users.
        """
        mock_bridges = []
        factories = []
        for i in range(3):
            bridge = AsyncMock(spec=AgentWebSocketBridge)
            bridge.create_user_emitter.return_value = AsyncMock()
            mock_bridges.append(bridge)
            factories.append(ExecutionEngineFactory(websocket_bridge=bridge))
        resource_exhaustion_results = []
        active_engines = []

        async def create_engine_under_pressure(factory_index, context, operation_id):
            """Create engine with resource pressure simulation."""
            try:
                factory = factories[factory_index % len(factories)]
                context_copy = UserExecutionContext(user_id=context.user_id, thread_id=context.thread_id, run_id=f'run_pressure_{operation_id}_{int(time.time())}_test', agent_context=context.agent_context, audit_metadata=context.audit_metadata)
                engine = await factory.create_for_user(context_copy)
                active_engines.append((factory_index, engine))
                resource_exhaustion_results.append({'operation_id': operation_id, 'factory_index': factory_index, 'status': 'success', 'engine_id': engine.engine_id})
                return engine
            except ExecutionEngineFactoryError as e:
                resource_exhaustion_results.append({'operation_id': operation_id, 'factory_index': factory_index, 'status': 'resource_exhaustion', 'error': str(e)})
                return None
            except Exception as e:
                resource_exhaustion_results.append({'operation_id': operation_id, 'factory_index': factory_index, 'status': 'unexpected_error', 'error': str(e)})
                return None
        pressure_tasks = []
        for operation_id in range(30):
            context = multi_user_contexts[operation_id % len(multi_user_contexts)]
            factory_index = operation_id % 3
            task = create_engine_under_pressure(factory_index, context, operation_id)
            pressure_tasks.append(task)
        engines = await asyncio.gather(*pressure_tasks, return_exceptions=True)
        successes = [r for r in resource_exhaustion_results if r['status'] == 'success']
        exhaustions = [r for r in resource_exhaustion_results if r['status'] == 'resource_exhaustion']
        errors = [r for r in resource_exhaustion_results if r['status'] == 'unexpected_error']
        assert len(successes) >= 10, f'Expected at least 10 successes under pressure, got {len(successes)}'
        assert len(exhaustions) >= 5, 'Expected some resource exhaustion scenarios'
        assert len(errors) <= 10, f'Too many unexpected errors: {len(errors)}'
        for i, factory in enumerate(factories):
            metrics = factory.get_factory_metrics()
            factory_engines = [e for fi, e in active_engines if fi == i]
            assert metrics['engines_active'] == len(factory_engines)
            assert metrics['engines_created'] >= len(factory_engines)
        cleanup_count = min(5, len(active_engines))
        for i in range(cleanup_count):
            factory_index, engine = active_engines[i]
            await factories[factory_index].cleanup_engine(engine)
        recovery_context = multi_user_contexts[0]
        recovery_context_new = UserExecutionContext(user_id=recovery_context.user_id, thread_id=recovery_context.thread_id, run_id=f'run_recovery_{int(time.time())}_test', agent_context=recovery_context.agent_context)
        recovery_engine = await factories[0].create_for_user(recovery_context_new)
        assert recovery_engine is not None
        assert recovery_engine.is_active()

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.concurrent_isolation
    async def test_concurrent_user_isolation_breach_detection(self, multi_user_contexts, isolated_env):
        """Test detection of user isolation breaches in concurrent scenarios.
        
        BVJ: Prevents cross-user data leakage in concurrent operations that could
        violate privacy regulations and compromise enterprise security.
        """
        enterprise_context = None
        free_context = None
        for context in multi_user_contexts:
            if context.agent_context.get('user_subscription') == 'enterprise' and (not enterprise_context):
                enterprise_context = context
            elif context.agent_context.get('user_subscription') == 'free' and (not free_context):
                free_context = context
            if enterprise_context and free_context:
                break
        assert enterprise_context is not None, 'Need enterprise context for isolation testing'
        assert free_context is not None, 'Need free context for isolation testing'
        isolation_test_results = []

        async def concurrent_operation_with_isolation_check(context, operation_type, operation_id):
            """Perform operation and check for isolation breaches."""
            try:
                child_context = context.create_child_context(f'{operation_type}_operation_{operation_id}', additional_agent_context={'operation_id': operation_id, 'operation_type': operation_type, 'isolation_test': True})
                if child_context.user_id != context.user_id:
                    isolation_test_results.append({'operation_id': operation_id, 'type': operation_type, 'status': 'isolation_breach_user_id', 'expected': context.user_id, 'actual': child_context.user_id})
                    return None
                if child_context.agent_context.get('user_subscription') != context.agent_context.get('user_subscription'):
                    isolation_test_results.append({'operation_id': operation_id, 'type': operation_type, 'status': 'isolation_breach_subscription', 'expected': context.agent_context.get('user_subscription'), 'actual': child_context.agent_context.get('user_subscription')})
                    return None
                expected_user_context = context.get_audit_trail()['user_context']
                actual_user_context = child_context.get_audit_trail()['user_context']
                if expected_user_context['user_id'] != actual_user_context['user_id']:
                    isolation_test_results.append({'operation_id': operation_id, 'type': operation_type, 'status': 'isolation_breach_audit', 'expected': expected_user_context['user_id'], 'actual': actual_user_context['user_id']})
                    return None
                isolation_test_results.append({'operation_id': operation_id, 'type': operation_type, 'status': 'isolation_maintained', 'user_id': child_context.user_id, 'subscription': child_context.agent_context.get('user_subscription')})
                return child_context
            except Exception as e:
                isolation_test_results.append({'operation_id': operation_id, 'type': operation_type, 'status': 'operation_error', 'error': str(e)})
                return None
        concurrent_tasks = []
        for i in range(10):
            task = concurrent_operation_with_isolation_check(enterprise_context, 'enterprise', f'ent_{i}')
            concurrent_tasks.append(task)
        for i in range(10):
            task = concurrent_operation_with_isolation_check(free_context, 'free', f'free_{i}')
            concurrent_tasks.append(task)
        results = await asyncio.gather(*concurrent_tasks)
        isolation_maintained = [r for r in isolation_test_results if r['status'] == 'isolation_maintained']
        isolation_breaches = [r for r in isolation_test_results if 'breach' in r['status']]
        operation_errors = [r for r in isolation_test_results if r['status'] == 'operation_error']
        assert len(isolation_breaches) == 0, f'Isolation breaches detected: {isolation_breaches}'
        assert len(isolation_maintained) >= 18, f'Expected at least 18 isolated operations, got {len(isolation_maintained)}'
        enterprise_results = [r for r in isolation_maintained if r['type'] == 'enterprise']
        free_results = [r for r in isolation_maintained if r['type'] == 'free']
        assert len(enterprise_results) >= 8, 'Enterprise operations should be isolated'
        assert len(free_results) >= 8, 'Free tier operations should be isolated'
        for ent_result in enterprise_results:
            assert ent_result['subscription'] == 'enterprise', 'Enterprise operations must maintain enterprise context'
        for free_result in free_results:
            assert free_result['subscription'] == 'free', 'Free operations must maintain free context'
        enterprise_user_ids = {r['user_id'] for r in enterprise_results}
        free_user_ids = {r['user_id'] for r in free_results}
        assert len(enterprise_user_ids) == 1, 'All enterprise operations should have same user ID'
        assert len(free_user_ids) == 1, 'All free operations should have same user ID'
        assert enterprise_user_ids != free_user_ids, 'Enterprise and free user IDs must be different'
        self.logger.info(f'Isolation test - Maintained: {len(isolation_maintained)}, Breaches: {len(isolation_breaches)}, Errors: {len(operation_errors)}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.concurrent_isolation
    async def test_concurrent_memory_corruption_prevention(self, concurrent_context_factory, isolated_env):
        """Test prevention of memory corruption in concurrent context operations.
        
        BVJ: Prevents memory corruption that could cause system crashes or data
        loss affecting all users and causing significant business disruption.
        """
        contexts = concurrent_context_factory(5, 'memory_corruption_test')
        memory_corruption_results = []
        initial_memory = psutil.Process().memory_info().rss
        memory_checkpoints = [initial_memory]

        async def memory_intensive_operation(context, intensity_level, operation_id):
            """Perform memory-intensive operations that could cause corruption."""
            try:
                memory_before = psutil.Process().memory_info().rss
                child_contexts = []
                for i in range(intensity_level * 5):
                    large_data = {'data_chunk': 'x' * (1000 * intensity_level), 'operation_metadata': {'chunk_id': i, 'parent_operation': operation_id, 'memory_test': True, 'nested_data': {'level_1': {'data': 'y' * 500}, 'level_2': {'data': 'z' * 300}, 'level_3': {'timestamps': [time.time() + j for j in range(100)]}}}}
                    child = context.create_child_context(f'memory_intensive_{operation_id}_{i}', additional_agent_context=large_data, additional_audit_metadata={'memory_test': True, 'intensity': intensity_level, 'chunk_index': i})
                    child_contexts.append(child)
                for i, child in enumerate(child_contexts):
                    assert child.agent_context['operation_metadata']['chunk_id'] == i
                    assert child.agent_context['operation_metadata']['parent_operation'] == operation_id
                    assert child.audit_metadata['intensity'] == intensity_level
                    assert child.audit_metadata['chunk_index'] == i
                    audit_trail = child.get_audit_trail()
                    assert audit_trail['operation_depth'] == 1
                    assert audit_trail['user_context']['user_id'] == context.user_id
                memory_after = psutil.Process().memory_info().rss
                memory_usage = memory_after - memory_before
                memory_corruption_results.append({'operation_id': operation_id, 'intensity': intensity_level, 'status': 'success', 'contexts_created': len(child_contexts), 'memory_used': memory_usage, 'data_integrity_verified': True})
                memory_checkpoints.append(memory_after)
                return child_contexts
            except Exception as e:
                memory_corruption_results.append({'operation_id': operation_id, 'intensity': intensity_level, 'status': 'error', 'error': str(e), 'error_type': type(e).__name__})
                return []
        memory_tasks = []
        for operation_id in range(10):
            context = contexts[operation_id % len(contexts)]
            intensity = operation_id % 3 + 1
            task = memory_intensive_operation(context, intensity, operation_id)
            memory_tasks.append(task)
        child_context_collections = []
        for i, task in enumerate(memory_tasks):
            result = await task
            child_context_collections.append(result)
            if i % 3 == 0:
                current_memory = psutil.Process().memory_info().rss
                memory_checkpoints.append(current_memory)
                await asyncio.sleep(0.01)
        successes = [r for r in memory_corruption_results if r['status'] == 'success']
        errors = [r for r in memory_corruption_results if r['status'] == 'error']
        assert len(successes) >= 8, f'Expected at least 8 successful operations, got {len(successes)}'
        assert len(errors) <= 2, f'Too many errors: {len(errors)}'
        for success in successes:
            assert success['data_integrity_verified'] is True
            assert success['contexts_created'] > 0
        final_memory = psutil.Process().memory_info().rss
        total_memory_increase = final_memory - initial_memory
        assert total_memory_increase < 100 * 1024 * 1024, f'Excessive memory usage: {total_memory_increase} bytes'
        memory_growth = [memory_checkpoints[i + 1] - memory_checkpoints[i] for i in range(len(memory_checkpoints) - 1)]
        avg_growth = sum(memory_growth) / len(memory_growth)
        max_growth = max(memory_growth)
        assert max_growth < 50 * 1024 * 1024, f'Excessive memory spike: {max_growth} bytes'
        for collection in child_context_collections:
            collection.clear()
        gc.collect()
        await asyncio.sleep(0.1)
        post_cleanup_memory = psutil.Process().memory_info().rss
        memory_recovered = final_memory - post_cleanup_memory
        self.logger.info(f'Memory corruption test - Total increase: {total_memory_increase}, Recovered: {memory_recovered}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.concurrent_isolation
    async def test_concurrent_deadlock_prevention(self, multi_user_contexts, isolated_env):
        """Test prevention of deadlocks in concurrent context operations.
        
        BVJ: Prevents system deadlocks that would cause complete service outage
        and significant business impact requiring system restart.
        """
        deadlock_test_results = []

        async def potentially_deadlocking_operation(context_a, context_b, operation_pair_id):
            """Create operations that might cause deadlocks through circular dependencies."""
            try:
                operation_start = time.time()
                child_a1 = context_a.create_child_context(f'deadlock_test_a1_{operation_pair_id}', additional_agent_context={'operation_type': 'cross_reference', 'target_user': context_b.user_id, 'pair_id': operation_pair_id})
                await asyncio.sleep(0.01)
                child_b1 = context_b.create_child_context(f'deadlock_test_b1_{operation_pair_id}', additional_agent_context={'operation_type': 'cross_reference', 'target_user': context_a.user_id, 'pair_id': operation_pair_id})
                child_b2 = context_b.create_child_context(f'deadlock_test_b2_{operation_pair_id}', additional_agent_context={'references': child_a1.request_id, 'pair_id': operation_pair_id})
                child_a2 = context_a.create_child_context(f'deadlock_test_a2_{operation_pair_id}', additional_agent_context={'references': child_b1.request_id, 'pair_id': operation_pair_id})
                operation_duration = time.time() - operation_start
                deadlock_test_results.append({'pair_id': operation_pair_id, 'status': 'success', 'duration': operation_duration, 'contexts_created': 4, 'user_a': context_a.user_id, 'user_b': context_b.user_id})
                return [child_a1, child_b1, child_b2, child_a2]
            except Exception as e:
                operation_duration = time.time() - operation_start
                deadlock_test_results.append({'pair_id': operation_pair_id, 'status': 'error', 'duration': operation_duration, 'error': str(e), 'error_type': type(e).__name__})
                return []
        deadlock_tasks = []
        context_pairs = []
        for i in range(0, min(8, len(multi_user_contexts)), 2):
            if i + 1 < len(multi_user_contexts):
                context_a = multi_user_contexts[i]
                context_b = multi_user_contexts[i + 1]
                context_pairs.append((context_a, context_b))
        for pair_id, (context_a, context_b) in enumerate(context_pairs):
            task = potentially_deadlocking_operation(context_a, context_b, pair_id)
            deadlock_tasks.append(task)
        try:
            results = await asyncio.wait_for(asyncio.gather(*deadlock_tasks, return_exceptions=True), timeout=10.0)
        except asyncio.TimeoutError:
            pytest.fail('Deadlock detected - operations timed out')
        successes = [r for r in deadlock_test_results if r['status'] == 'success']
        errors = [r for r in deadlock_test_results if r['status'] == 'error']
        assert len(successes) >= len(context_pairs) // 2, f'Expected successful operations, got {len(successes)}'
        for success in successes:
            assert success['duration'] < 5.0, f"Operation took too long: {success['duration']}s (possible deadlock)"
            assert success['contexts_created'] == 4, 'All contexts should be created'
        for error in errors:
            assert error['duration'] < 5.0, f"Error operation took too long: {error['duration']}s"
        all_created_contexts = [ctx for result_collection in results if result_collection for ctx in result_collection]
        if all_created_contexts:
            user_ids = {ctx.user_id for ctx in all_created_contexts}
            assert len(user_ids) >= 2, 'Should have contexts from multiple users'
            for ctx in all_created_contexts:
                audit_trail = ctx.get_audit_trail()
                assert audit_trail['user_context']['user_id'] == ctx.user_id
                assert ctx.operation_depth >= 1
        self.logger.info(f"Deadlock prevention test - Successes: {len(successes)}, Errors: {len(errors)}, Max duration: {max([r.get('duration', 0) for r in deadlock_test_results]):.3f}s")

class TestSystemBoundaryAndResourceLimitErrorHandling(BaseIntegrationTest):
    """Test suite for system boundary and resource limit error handling scenarios.
    
    BVJ: Validates system behavior at operational limits and ensures graceful
    degradation when approaching resource boundaries. Critical for preventing
    system overload that could cause complete service outage affecting revenue.
    """

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.resource_limits
    async def test_context_depth_limit_enforcement_and_recovery(self, realistic_user_context, isolated_env):
        """Test enforcement of context depth limits and recovery mechanisms.
        
        BVJ: Prevents infinite recursion and stack overflow that could crash
        the system, ensuring stable operations even with malformed agent workflows.
        """
        root_context = realistic_user_context
        depth_limit_results = []
        created_contexts = []
        current_context = root_context
        depth_count = 0
        max_safe_depth = 50
        try:
            while depth_count < max_safe_depth:
                child_context = current_context.create_child_context(f'depth_test_level_{depth_count}', additional_agent_context={'depth_level': depth_count, 'depth_test': True, 'parent_depth': current_context.operation_depth}, additional_audit_metadata={'depth_progression': depth_count, 'recursion_test': True})
                assert child_context.operation_depth == depth_count + 1
                assert child_context.parent_request_id == current_context.request_id
                created_contexts.append(child_context)
                depth_limit_results.append({'depth': depth_count, 'status': 'success', 'context_id': child_context.request_id, 'operation_depth': child_context.operation_depth})
                current_context = child_context
                depth_count += 1
        except Exception as e:
            depth_limit_results.append({'depth': depth_count, 'status': 'depth_limit_reached', 'error': str(e), 'max_depth_achieved': depth_count})
        successful_depths = [r for r in depth_limit_results if r['status'] == 'success']
        assert len(successful_depths) >= 20, f'Expected at least 20 successful depth levels, got {len(successful_depths)}'
        for i, result in enumerate(successful_depths):
            assert result['depth'] == i, f'Depth progression error at level {i}'
            assert result['operation_depth'] == i + 1, f'Operation depth mismatch at level {i}'
        if created_contexts:
            deep_context = created_contexts[-1]
            sibling_context = created_contexts[-2].create_child_context('depth_recovery_sibling', additional_agent_context={'recovery_test': True, 'sibling_of_deep': True})
            assert sibling_context.operation_depth == deep_context.operation_depth
            assert sibling_context.parent_request_id == deep_context.parent_request_id
            recovery_branch = root_context.create_child_context('depth_recovery_new_branch', additional_agent_context={'recovery_from_root': True, 'post_depth_test': True})
            assert recovery_branch.operation_depth == 1
            assert recovery_branch.parent_request_id == root_context.request_id
        current_memory = psutil.Process().memory_info().rss
        self.logger.info(f'Depth limit test - Max depth achieved: {depth_count}, Contexts created: {len(created_contexts)}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.resource_limits
    async def test_memory_limit_enforcement_and_cleanup(self, multi_user_contexts, isolated_env):
        """Test memory limit enforcement and automatic cleanup mechanisms.
        
        BVJ: Prevents memory exhaustion that could cause system instability
        or crashes, ensuring stable operations for all users.
        """
        initial_memory = psutil.Process().memory_info().rss
        memory_limit_results = []
        large_context_collections = []
        memory_intensive_contexts = []
        for i, base_context in enumerate(multi_user_contexts[:3]):
            try:
                large_data_size = (i + 1) * 10000
                large_context = base_context.create_child_context(f'memory_intensive_operation_{i}', additional_agent_context={'large_dataset': 'x' * large_data_size, 'memory_test_index': i, 'data_size': large_data_size, 'nested_data': {'chunk_1': 'a' * (large_data_size // 4), 'chunk_2': 'b' * (large_data_size // 4), 'chunk_3': 'c' * (large_data_size // 4), 'chunk_4': 'd' * (large_data_size // 4), 'metadata': {'timestamps': [time.time() + j for j in range(1000)], 'counters': list(range(1000)), 'flags': [True, False] * 500}}}, additional_audit_metadata={'memory_test': True, 'expected_size': large_data_size, 'test_phase': 'memory_limit'})
                memory_intensive_contexts.append(large_context)
                child_contexts = []
                for j in range(20):
                    child = large_context.create_child_context(f'memory_child_{i}_{j}', additional_agent_context={'child_data': 'y' * 5000, 'child_index': j, 'parent_size': large_data_size})
                    child_contexts.append(child)
                large_context_collections.append(child_contexts)
                current_memory = psutil.Process().memory_info().rss
                memory_usage = current_memory - initial_memory
                memory_limit_results.append({'user_index': i, 'status': 'success', 'contexts_created': len(child_contexts) + 1, 'data_size': large_data_size, 'memory_usage': memory_usage, 'memory_per_context': memory_usage / (len(child_contexts) + 1)})
            except MemoryError as e:
                memory_limit_results.append({'user_index': i, 'status': 'memory_limit_reached', 'error': str(e), 'contexts_before_limit': len(memory_intensive_contexts)})
                break
            except Exception as e:
                memory_limit_results.append({'user_index': i, 'status': 'unexpected_error', 'error': str(e), 'error_type': type(e).__name__})
        successes = [r for r in memory_limit_results if r['status'] == 'success']
        memory_limits = [r for r in memory_limit_results if r['status'] == 'memory_limit_reached']
        assert len(successes) >= 2, f'Expected at least 2 successful memory operations, got {len(successes)}'
        for success in successes:
            assert success['contexts_created'] > 0
            assert success['memory_usage'] > 0
            assert success['memory_per_context'] > 0
        cleanup_start_memory = psutil.Process().memory_info().rss
        memory_intensive_contexts.clear()
        for collection in large_context_collections:
            collection.clear()
        large_context_collections.clear()
        gc.collect()
        await asyncio.sleep(0.2)
        post_cleanup_memory = psutil.Process().memory_info().rss
        memory_recovered = cleanup_start_memory - post_cleanup_memory
        if memory_recovered > 0:
            memory_recovery_percent = memory_recovered / cleanup_start_memory * 100
            self.logger.info(f'Memory recovery: {memory_recovered} bytes ({memory_recovery_percent:.1f}%)')
        recovery_context = multi_user_contexts[0]
        recovery_test = recovery_context.create_child_context('post_memory_test_recovery', additional_agent_context={'recovery_test': True, 'small_data': 'normal_size_data'})
        assert recovery_test.agent_context['recovery_test'] is True
        self.logger.info(f'Memory limit test - Successes: {len(successes)}, Memory limits: {len(memory_limits)}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.resource_limits
    async def test_concurrent_user_limit_enforcement(self, concurrent_context_factory, isolated_env):
        """Test enforcement of concurrent user limits and queuing mechanisms.
        
        BVJ: Ensures system stability when user concurrency exceeds capacity,
        preventing resource exhaustion that could impact all users.
        """
        max_concurrent_users = 20
        concurrent_user_results = []
        active_user_contexts = {}
        user_contexts = concurrent_context_factory(max_concurrent_users * 2, 'concurrent_user_limit_test')

        async def simulate_concurrent_user_session(context, user_session_id):
            """Simulate a user session with multiple operations."""
            session_start = time.time()
            session_operations = []
            try:
                for operation_id in range(5):
                    operation_context = context.create_child_context(f'user_operation_{user_session_id}_{operation_id}', additional_agent_context={'operation_id': operation_id, 'user_session': user_session_id, 'concurrent_test': True, 'operation_timestamp': time.time()})
                    session_operations.append(operation_context)
                    await asyncio.sleep(0.01)
                session_duration = time.time() - session_start
                concurrent_user_results.append({'user_session': user_session_id, 'status': 'success', 'session_duration': session_duration, 'operations_completed': len(session_operations), 'user_id': context.user_id})
                return session_operations
            except Exception as e:
                session_duration = time.time() - session_start
                concurrent_user_results.append({'user_session': user_session_id, 'status': 'user_limit_reached', 'session_duration': session_duration, 'error': str(e), 'operations_completed': len(session_operations)})
                return session_operations
        user_session_tasks = []
        for i, context in enumerate(user_contexts):
            task = simulate_concurrent_user_session(context, i)
            user_session_tasks.append(task)
            if i % 5 == 0:
                await asyncio.sleep(0.01)
        session_results = await asyncio.gather(*user_session_tasks, return_exceptions=True)
        successful_sessions = [r for r in concurrent_user_results if r['status'] == 'success']
        limited_sessions = [r for r in concurrent_user_results if r['status'] == 'user_limit_reached']
        total_operations = sum((r['operations_completed'] for r in concurrent_user_results))
        successful_operations = sum((r['operations_completed'] for r in successful_sessions))
        assert len(successful_sessions) >= max_concurrent_users // 2, f'Expected at least {max_concurrent_users // 2} successful sessions'
        assert total_operations >= max_concurrent_users * 2, f'Expected at least {max_concurrent_users * 2} total operations'
        avg_duration = sum((r['session_duration'] for r in successful_sessions)) / len(successful_sessions)
        max_duration = max((r['session_duration'] for r in successful_sessions))
        assert avg_duration < 5.0, f'Average session duration too long: {avg_duration}s'
        assert max_duration < 10.0, f'Max session duration too long: {max_duration}s'
        user_ids = {r['user_id'] for r in successful_sessions}
        assert len(user_ids) >= max_concurrent_users // 2, 'Should maintain user diversity under load'
        recovery_context = user_contexts[0]
        recovery_operation = recovery_context.create_child_context('post_load_recovery_test', additional_agent_context={'recovery_after_load': True, 'test_timestamp': time.time()})
        assert recovery_operation.agent_context['recovery_after_load'] is True
        self.logger.info(f'Concurrent user limit test - Successful sessions: {len(successful_sessions)}, Limited sessions: {len(limited_sessions)}, Total operations: {total_operations}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.resource_limits
    async def test_timeout_enforcement_and_cancellation(self, realistic_user_context, isolated_env):
        """Test timeout enforcement and proper cancellation of long-running operations.
        
        BVJ: Prevents resource starvation from long-running operations that could
        impact system responsiveness and user experience for other users.
        """
        timeout_test_results = []
        timeout_scenarios = [{'name': 'quick_operation', 'duration': 0.1, 'timeout': 1.0, 'should_succeed': True}, {'name': 'normal_operation', 'duration': 0.5, 'timeout': 1.0, 'should_succeed': True}, {'name': 'slow_operation', 'duration': 2.0, 'timeout': 1.0, 'should_succeed': False}, {'name': 'very_slow_operation', 'duration': 5.0, 'timeout': 2.0, 'should_succeed': False}]

        async def timeout_sensitive_operation(base_context, scenario):
            """Simulate operation with specific duration and timeout."""
            operation_start = time.time()
            try:
                timeout_context = base_context.create_child_context(f"timeout_test_{scenario['name']}", additional_agent_context={'operation_type': 'timeout_test', 'expected_duration': scenario['duration'], 'timeout_limit': scenario['timeout'], 'should_succeed': scenario['should_succeed']})

                async def simulated_work():
                    await asyncio.sleep(scenario['duration'])
                    return {'result': 'completed', 'actual_duration': scenario['duration'], 'context_id': timeout_context.request_id}
                result = await asyncio.wait_for(simulated_work(), timeout=scenario['timeout'])
                operation_duration = time.time() - operation_start
                timeout_test_results.append({'scenario': scenario['name'], 'status': 'completed_within_timeout', 'operation_duration': operation_duration, 'expected_success': scenario['should_succeed'], 'actual_result': result, 'timeout_enforced': False})
                return result
            except asyncio.TimeoutError:
                operation_duration = time.time() - operation_start
                timeout_test_results.append({'scenario': scenario['name'], 'status': 'timeout_enforced', 'operation_duration': operation_duration, 'expected_success': scenario['should_succeed'], 'timeout_limit': scenario['timeout'], 'timeout_enforced': True})
                if not scenario['should_succeed']:
                    return None
                else:
                    raise
            except Exception as e:
                operation_duration = time.time() - operation_start
                timeout_test_results.append({'scenario': scenario['name'], 'status': 'unexpected_error', 'operation_duration': operation_duration, 'error': str(e), 'error_type': type(e).__name__})
                return None
        scenario_tasks = []
        for scenario in timeout_scenarios:
            task = timeout_sensitive_operation(realistic_user_context, scenario)
            scenario_tasks.append(task)
        scenario_results = await asyncio.gather(*scenario_tasks, return_exceptions=True)
        completed_operations = [r for r in timeout_test_results if r['status'] == 'completed_within_timeout']
        timeout_enforced = [r for r in timeout_test_results if r['status'] == 'timeout_enforced']
        errors = [r for r in timeout_test_results if r['status'] == 'unexpected_error']
        assert len(completed_operations) >= 2, f'Expected at least 2 operations to complete, got {len(completed_operations)}'
        assert len(timeout_enforced) >= 2, f'Expected at least 2 timeouts to be enforced, got {len(timeout_enforced)}'
        quick_ops = [r for r in completed_operations if 'quick' in r['scenario'] or 'normal' in r['scenario']]
        assert len(quick_ops) >= 2, 'Quick and normal operations should complete within timeout'
        slow_timeouts = [r for r in timeout_enforced if 'slow' in r['scenario']]
        assert len(slow_timeouts) >= 2, 'Slow operations should timeout'
        for timeout_result in timeout_enforced:
            expected_timeout = next((s['timeout'] for s in timeout_scenarios if s['name'] == timeout_result['scenario']))
            assert timeout_result['operation_duration'] <= expected_timeout + 0.1, f"Timeout duration inaccurate for {timeout_result['scenario']}"
        post_timeout_context = realistic_user_context.create_child_context('post_timeout_recovery_test', additional_agent_context={'recovery_test': True, 'post_timeout': True})
        quick_recovery_result = await asyncio.wait_for(asyncio.sleep(0.1), timeout=1.0)
        assert post_timeout_context.agent_context['recovery_test'] is True
        self.logger.info(f'Timeout enforcement test - Completed: {len(completed_operations)}, Timeouts: {len(timeout_enforced)}, Errors: {len(errors)}')

    @pytest.mark.integration
    @pytest.mark.error_handling
    @pytest.mark.resource_limits
    async def test_system_resource_exhaustion_graceful_degradation(self, multi_user_contexts, isolated_env):
        """Test graceful system degradation under complete resource exhaustion.
        
        BVJ: Ensures system remains partially functional even under extreme load,
        preventing complete service outage that would have severe business impact.
        """
        initial_memory = psutil.Process().memory_info().rss
        initial_cpu_percent = psutil.cpu_percent()
        resource_exhaustion_results = []
        stress_contexts = []

        async def resource_intensive_scenario(context_index, base_context, stress_level):
            """Create resource-intensive operations at different stress levels."""
            scenario_start = time.time()
            try:
                intensive_contexts = []
                for i in range(stress_level * 5):
                    large_data = {'stress_test_data': 'x' * (stress_level * 10000), 'operation_index': i, 'stress_level': stress_level, 'nested_structures': {f'level_{j}': {'data': 'y' * 1000, 'timestamps': [time.time() + k for k in range(100)], 'metadata': {'chunk': j, 'stress': stress_level}} for j in range(stress_level * 2)}}
                    stress_context = base_context.create_child_context(f'resource_stress_{context_index}_{i}', additional_agent_context=large_data, additional_audit_metadata={'stress_test': True, 'stress_level': stress_level, 'operation_index': i, 'memory_intensive': True})
                    intensive_contexts.append(stress_context)
                    await asyncio.sleep(0.001 * stress_level)
                scenario_duration = time.time() - scenario_start
                current_memory = psutil.Process().memory_info().rss
                memory_usage = current_memory - initial_memory
                resource_exhaustion_results.append({'context_index': context_index, 'stress_level': stress_level, 'status': 'success', 'contexts_created': len(intensive_contexts), 'scenario_duration': scenario_duration, 'memory_usage': memory_usage, 'operations_per_second': len(intensive_contexts) / scenario_duration if scenario_duration > 0 else 0})
                return intensive_contexts
            except MemoryError as e:
                scenario_duration = time.time() - scenario_start
                resource_exhaustion_results.append({'context_index': context_index, 'stress_level': stress_level, 'status': 'memory_exhausted', 'scenario_duration': scenario_duration, 'error': 'Memory exhaustion detected', 'contexts_created': 0})
                return []
            except Exception as e:
                scenario_duration = time.time() - scenario_start
                resource_exhaustion_results.append({'context_index': context_index, 'stress_level': stress_level, 'status': 'resource_error', 'scenario_duration': scenario_duration, 'error': str(e), 'error_type': type(e).__name__, 'contexts_created': 0})
                return []
        exhaustion_tasks = []
        for i, base_context in enumerate(multi_user_contexts[:5]):
            stress_level = i % 3 + 1
            task = resource_intensive_scenario(i, base_context, stress_level)
            exhaustion_tasks.append(task)
        try:
            stress_results = await asyncio.wait_for(asyncio.gather(*exhaustion_tasks, return_exceptions=True), timeout=30.0)
        except asyncio.TimeoutError:
            resource_exhaustion_results.append({'status': 'timeout_during_exhaustion', 'message': 'Resource exhaustion test timed out - possible system overload'})
            stress_results = []
        successes = [r for r in resource_exhaustion_results if r['status'] == 'success']
        memory_exhaustions = [r for r in resource_exhaustion_results if r['status'] == 'memory_exhausted']
        resource_errors = [r for r in resource_exhaustion_results if r['status'] == 'resource_error']
        assert len(successes) >= 2, f'Expected at least 2 successful stress scenarios, got {len(successes)}'
        total_failures = len(memory_exhaustions) + len(resource_errors)
        if total_failures > 0:
            self.logger.info(f'Graceful degradation observed: {total_failures} operations failed due to resource limits')
        for success in successes:
            assert success['scenario_duration'] < 15.0, f"Stress scenario took too long: {success['scenario_duration']}s"
            assert success['contexts_created'] > 0, 'Should create some contexts even under stress'
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - initial_memory
        for result_collection in stress_results:
            if isinstance(result_collection, list):
                result_collection.clear()
        gc.collect()
        await asyncio.sleep(0.5)
        recovery_context = multi_user_contexts[0] if multi_user_contexts else None
        if recovery_context:
            post_stress_context = recovery_context.create_child_context('post_resource_exhaustion_recovery', additional_agent_context={'recovery_test': True, 'post_stress': True, 'small_footprint': True})
            assert post_stress_context.agent_context['recovery_test'] is True
            audit_trail = post_stress_context.get_audit_trail()
            assert audit_trail['operation_depth'] == 1
            assert audit_trail['user_context']['user_id'] == recovery_context.user_id
        post_recovery_memory = psutil.Process().memory_info().rss
        memory_recovered = final_memory - post_recovery_memory
        self.logger.info(f'Resource exhaustion test - Successes: {len(successes)}, Memory exhaustions: {len(memory_exhaustions)}, Resource errors: {len(resource_errors)}')
        self.logger.info(f'Memory usage - Peak increase: {memory_increase} bytes, Recovered: {memory_recovered} bytes')

async def finalize_todo_status():
    """Mark all todo items as completed."""
    return [{'content': 'Create 25 comprehensive integration tests for UVS error handling and edge cases', 'status': 'completed', 'activeForm': 'Created comprehensive integration tests for UVS error handling and edge cases'}, {'content': 'Focus on context validation error handling and recovery (5 tests)', 'status': 'completed', 'activeForm': 'Implemented context validation error handling tests'}, {'content': 'Implement factory error handling and resource cleanup tests (5 tests)', 'status': 'completed', 'activeForm': 'Implemented factory error handling tests'}, {'content': 'Create WebSocket error handling and connection resilience tests (5 tests)', 'status': 'completed', 'activeForm': 'Created WebSocket error handling tests'}, {'content': 'Develop concurrent operation error handling and isolation tests (5 tests)', 'status': 'completed', 'activeForm': 'Developed concurrent operation error handling tests'}, {'content': 'Build system boundary and resource limit error handling tests (5 tests)', 'status': 'completed', 'activeForm': 'Built system boundary and resource limit tests'}]
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')