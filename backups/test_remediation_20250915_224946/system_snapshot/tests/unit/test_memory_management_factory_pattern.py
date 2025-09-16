"""
Test 5: Memory Management Factory Pattern

PURPOSE: Validate memory efficiency and cleanup of factory pattern implementation.
ISSUE: #709 - Agent Factory Singleton Legacy remediation
SCOPE: Memory management and resource cleanup validation

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: Tests should FAIL (proving memory leaks/poor cleanup exist)
- AFTER REMEDIATION: Tests should PASS (proving proper memory management)

Business Value: Platform/Internal - $500K+ ARR protection through scalable memory management
"""
import asyncio
import gc
import psutil
import sys
import time
import tracemalloc
import weakref
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

@pytest.mark.unit
class MemoryManagementFactoryPatternTests(SSotAsyncTestCase):
    """
    Test suite validating memory management in factory pattern implementation.

    This test suite specifically targets Issue #709 by validating that:
    1. Factory pattern doesn't cause memory leaks
    2. Proper cleanup of factory-created instances
    3. No unbounded memory growth with concurrent users
    4. Garbage collection works properly with factory instances

    CRITICAL: These tests should FAIL before remediation and PASS after.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        tracemalloc.start()
        self._initial_memory = self._get_memory_snapshot()
        self._tracked_instances = []
        self._tracked_contexts = []
        self._tracked_factories = []
        self._weak_references = []
        self._memory_snapshots = []
        self._memory_thresholds = {'max_memory_increase_mb': 50, 'max_instances_retained': 10, 'gc_cleanup_efficiency': 0.9}
        self._mock_dependencies = {'websocket_bridge': SSotMockFactory.create_mock_agent_websocket_bridge(), 'agent_registry': MagicMock(), 'llm_manager': SSotMockFactory.create_mock_llm_manager()}
        self.record_metric('test_setup_completed', True)
        self.record_metric('initial_memory_mb', self._initial_memory['rss_mb'])

    def teardown_method(self, method):
        """Cleanup after each test method."""
        for instance in self._tracked_instances:
            try:
                if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                    if asyncio.iscoroutinefunction(instance.cleanup):
                        asyncio.create_task(instance.cleanup())
                    else:
                        instance.cleanup()
            except Exception as e:
                print(f'Warning: Instance cleanup failed: {e}')
        for context in self._tracked_contexts:
            try:
                if hasattr(context, 'cleanup') and callable(context.cleanup):
                    if asyncio.iscoroutinefunction(context.cleanup):
                        asyncio.create_task(context.cleanup())
                    else:
                        context.cleanup()
            except Exception as e:
                print(f'Warning: Context cleanup failed: {e}')
        for factory in self._tracked_factories:
            try:
                if hasattr(factory, 'reset_for_testing') and callable(factory.reset_for_testing):
                    factory.reset_for_testing()
            except Exception as e:
                print(f'Warning: Factory cleanup failed: {e}')
        gc.collect()
        final_memory = self._get_memory_snapshot()
        memory_increase = final_memory['rss_mb'] - self._initial_memory['rss_mb']
        self.record_metric('final_memory_mb', final_memory['rss_mb'])
        self.record_metric('memory_increase_mb', memory_increase)
        tracemalloc.stop()
        super().teardown_method(method)

    def _get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory usage snapshot."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            snapshot = {'rss_mb': memory_info.rss / 1024 / 1024, 'vms_mb': memory_info.vms / 1024 / 1024, 'timestamp': time.time()}
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                snapshot.update({'traced_current_mb': current / 1024 / 1024, 'traced_peak_mb': peak / 1024 / 1024})
            return snapshot
        except Exception as e:
            return {'rss_mb': 0, 'vms_mb': 0, 'error': str(e), 'timestamp': time.time()}

    async def _create_test_user_context(self, user_id: str) -> Any:
        """Create a test user execution context."""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            context = UserExecutionContext.from_request_supervisor(user_id=f'memory_test_{user_id}', thread_id=f'thread_{user_id}_{int(time.time())}', run_id=f'run_{user_id}_{int(time.time())}')
            self._tracked_contexts.append(context)
            return context
        except ImportError as e:
            pytest.skip(f'Cannot import UserExecutionContext: {e}')

    async def _create_factory_instance(self) -> Any:
        """Create and configure a factory instance."""
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            factory = AgentInstanceFactory()
            factory.configure(websocket_bridge=self._mock_dependencies['websocket_bridge'], agent_registry=self._mock_dependencies['agent_registry'], llm_manager=self._mock_dependencies['llm_manager'])
            self._tracked_factories.append(factory)
            return factory
        except ImportError as e:
            pytest.skip(f'Cannot import AgentInstanceFactory: {e}')

    async def test_factory_instances_cleanup_properly(self):
        """
        CRITICAL TEST: Validate factory instances and their resources cleanup properly.

        This test should FAIL before Issue #709 remediation due to memory leaks
        or improper resource cleanup in singleton patterns.

        After remediation, this test should PASS by proving proper cleanup.
        """
        self.record_metric('test_started', 'test_factory_instances_cleanup_properly')
        try:
            initial_snapshot = self._get_memory_snapshot()
            factories = []
            weak_refs = []
            num_factories = 5
            for i in range(num_factories):
                factory = await self._create_factory_instance()
                factories.append(factory)
                weak_ref = weakref.ref(factory)
                weak_refs.append(weak_ref)
                self._weak_references.append(weak_ref)
                context = await self._create_test_user_context(f'cleanup_user_{i}')
                try:
                    factory_context = await factory.create_user_execution_context(user_id=context.user_id, thread_id=context.thread_id, run_id=context.run_id)
                    agent = await factory.create_agent_instance(agent_name='TriageSubAgent', user_context=context)
                    self._tracked_instances.append(agent)
                except Exception as e:
                    print(f'Warning: Failed to create agent for factory {i}: {e}')
            post_creation_snapshot = self._get_memory_snapshot()
            creation_memory_increase = post_creation_snapshot['rss_mb'] - initial_snapshot['rss_mb']
            alive_refs = sum((1 for ref in weak_refs if ref() is not None))
            assert alive_refs == num_factories, f'MEMORY MANAGEMENT VIOLATION: Not all factory references alive before cleanup. Expected: {num_factories}, Alive: {alive_refs}. This indicates premature garbage collection.'
            for i, factory in enumerate(factories):
                try:
                    if hasattr(factory, 'get_factory_metrics'):
                        metrics = factory.get_factory_metrics()
                        active_contexts = metrics.get('active_contexts', 0)
                        if hasattr(factory, 'cleanup_inactive_contexts'):
                            cleaned = await factory.cleanup_inactive_contexts(max_age_seconds=0)
                            self.record_metric(f'factory_{i}_contexts_cleaned', cleaned)
                    if hasattr(factory, 'reset_for_testing'):
                        factory.reset_for_testing()
                except Exception as e:
                    print(f'Warning: Factory {i} cleanup failed: {e}')
            factories.clear()
            for _ in range(3):
                gc.collect()
            await asyncio.sleep(0.1)
            alive_after_cleanup = sum((1 for ref in weak_refs if ref() is not None))
            cleanup_efficiency = (num_factories - alive_after_cleanup) / num_factories
            assert cleanup_efficiency >= self._memory_thresholds['gc_cleanup_efficiency'], f"MEMORY MANAGEMENT VIOLATION: Poor garbage collection efficiency. Created: {num_factories}, Still alive: {alive_after_cleanup}, Efficiency: {cleanup_efficiency:.1%}. Expected: >= {self._memory_thresholds['gc_cleanup_efficiency']:.1%}. This indicates memory leaks in factory pattern."
            post_cleanup_snapshot = self._get_memory_snapshot()
            cleanup_memory_decrease = post_creation_snapshot['rss_mb'] - post_cleanup_snapshot['rss_mb']
            final_memory_increase = post_cleanup_snapshot['rss_mb'] - initial_snapshot['rss_mb']
            assert final_memory_increase <= self._memory_thresholds['max_memory_increase_mb'], f"MEMORY MANAGEMENT VIOLATION: Excessive memory increase after cleanup. Initial: {initial_snapshot['rss_mb']:.1f}MB, Final: {post_cleanup_snapshot['rss_mb']:.1f}MB, Increase: {final_memory_increase:.1f}MB. Max allowed: {self._memory_thresholds['max_memory_increase_mb']}MB. This indicates memory leaks in factory pattern."
            self.record_metric('factories_created', num_factories)
            self.record_metric('cleanup_efficiency', cleanup_efficiency)
            self.record_metric('memory_cleanup_checks_passed', 5)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during memory cleanup validation: {e}')

    async def test_concurrent_factory_memory_efficiency(self):
        """
        CRITICAL TEST: Validate memory efficiency with concurrent factory usage.

        This test creates multiple factories concurrently and verifies that
        memory usage doesn't grow unbounded.

        Expected to FAIL before remediation due to memory inefficiency.
        """
        self.record_metric('test_started', 'test_concurrent_factory_memory_efficiency')

        async def create_factory_workload(workload_id: int, operations_count: int) -> Dict[str, Any]:
            """Create factory workload with multiple operations."""
            try:
                factory = await self._create_factory_instance()
                workload_data = {'workload_id': workload_id, 'factory_id': id(factory), 'operations': [], 'peak_memory': 0, 'agents_created': 0}
                for op_id in range(operations_count):
                    try:
                        context = await self._create_test_user_context(f'concurrent_{workload_id}_{op_id}')
                        factory_context = await factory.create_user_execution_context(user_id=context.user_id, thread_id=context.thread_id, run_id=context.run_id)
                        agent = await factory.create_agent_instance(agent_name='DataHelperAgent', user_context=context)
                        self._tracked_instances.append(agent)
                        workload_data['agents_created'] += 1
                        current_memory = self._get_memory_snapshot()
                        workload_data['peak_memory'] = max(workload_data['peak_memory'], current_memory['rss_mb'])
                        await factory.cleanup_user_context(factory_context)
                        workload_data['operations'].append({'op_id': op_id, 'memory_mb': current_memory['rss_mb']})
                    except Exception as e:
                        workload_data['operations'].append({'op_id': op_id, 'error': str(e)})
                if hasattr(factory, 'reset_for_testing'):
                    factory.reset_for_testing()
                return workload_data
            except Exception as e:
                return {'workload_id': workload_id, 'error': str(e)}
        try:
            initial_memory = self._get_memory_snapshot()
            concurrent_workloads = 4
            operations_per_workload = 5
            tasks = [create_factory_workload(workload_id, operations_per_workload) for workload_id in range(concurrent_workloads)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failed_workloads = []
            successful_results = []
            for result in results:
                if isinstance(result, Exception):
                    failed_workloads.append(f'Exception: {result}')
                elif 'error' in result:
                    failed_workloads.append(f"Workload {result['workload_id']}: {result['error']}")
                else:
                    successful_results.append(result)
            if failed_workloads:
                pytest.fail(f'CONCURRENT MEMORY VIOLATION: Failed workloads: {failed_workloads}')
            for _ in range(3):
                gc.collect()
            await asyncio.sleep(0.1)
            final_memory = self._get_memory_snapshot()
            total_memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']
            total_operations = sum((result['agents_created'] for result in successful_results))
            memory_per_operation = total_memory_increase / max(total_operations, 1)
            max_memory_per_operation = 5.0
            assert memory_per_operation <= max_memory_per_operation, f'CONCURRENT MEMORY VIOLATION: Excessive memory per operation. Total increase: {total_memory_increase:.1f}MB, Operations: {total_operations}, Per operation: {memory_per_operation:.2f}MB. Max allowed: {max_memory_per_operation}MB. This indicates memory inefficiency in concurrent factory usage.'
            for result in successful_results:
                operations = result['operations']
                if len(operations) > 1:
                    memory_values = [op['memory_mb'] for op in operations if 'memory_mb' in op]
                    if len(memory_values) > 2:
                        first_half_avg = sum(memory_values[:len(memory_values) // 2]) / (len(memory_values) // 2)
                        second_half_avg = sum(memory_values[len(memory_values) // 2:]) / (len(memory_values) - len(memory_values) // 2)
                        memory_growth_rate = (second_half_avg - first_half_avg) / first_half_avg
                        max_growth_rate = 0.2
                        assert memory_growth_rate <= max_growth_rate, f"MEMORY LEAK VIOLATION: Continuous memory growth in workload {result['workload_id']}. First half avg: {first_half_avg:.1f}MB, Second half avg: {second_half_avg:.1f}MB, Growth rate: {memory_growth_rate:.1%}. Max allowed: {max_growth_rate:.1%}. This indicates memory leaks during factory operations."
            factory_ids = [result['factory_id'] for result in successful_results]
            unique_factories = set(factory_ids)
            assert len(unique_factories) == len(successful_results), f'FACTORY EFFICIENCY VIOLATION: Factory instances not unique. Expected: {len(successful_results)} unique factories, Got: {len(unique_factories)} unique. This may indicate singleton behavior instead of factory pattern.'
            self.record_metric('concurrent_workloads', concurrent_workloads)
            self.record_metric('total_operations', total_operations)
            self.record_metric('memory_per_operation_mb', memory_per_operation)
            self.record_metric('concurrent_memory_checks_passed', 5)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during concurrent memory validation: {e}')

    async def test_factory_context_lifecycle_memory_management(self):
        """
        CRITICAL TEST: Validate proper memory management of factory context lifecycle.

        This test verifies that factory contexts (UserExecutionContext) are
        properly created, used, and cleaned up without memory leaks.

        Expected to FAIL before remediation due to context memory leaks.
        """
        self.record_metric('test_started', 'test_factory_context_lifecycle_memory_management')
        try:
            factory = await self._create_factory_instance()
            initial_memory = self._get_memory_snapshot()
            context_lifecycle_data = []
            weak_context_refs = []
            num_contexts = 10
            for i in range(num_contexts):
                try:
                    user_context = await self._create_test_user_context(f'lifecycle_{i}')
                    factory_context = await factory.create_user_execution_context(user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id)
                    weak_ref = weakref.ref(factory_context)
                    weak_context_refs.append(weak_ref)
                    self._weak_references.append(weak_ref)
                    agent = await factory.create_agent_instance(agent_name='TriageSubAgent', user_context=user_context)
                    self._tracked_instances.append(agent)
                    context_data = {'context_id': i, 'user_id': user_context.user_id, 'factory_context_id': id(factory_context), 'agent_id': id(agent), 'created_memory': self._get_memory_snapshot()['rss_mb']}
                    context_lifecycle_data.append(context_data)
                    await factory.cleanup_user_context(factory_context)
                    context_data['cleanup_memory'] = self._get_memory_snapshot()['rss_mb']
                except Exception as e:
                    context_lifecycle_data.append({'context_id': i, 'error': str(e)})
            for _ in range(3):
                gc.collect()
            await asyncio.sleep(0.1)
            errors = [ctx for ctx in context_lifecycle_data if 'error' in ctx]
            if errors:
                pytest.fail(f'CONTEXT LIFECYCLE VIOLATION: Context creation/cleanup errors: {errors}')
            alive_contexts = sum((1 for ref in weak_context_refs if ref() is not None))
            cleanup_efficiency = (num_contexts - alive_contexts) / num_contexts
            assert cleanup_efficiency >= self._memory_thresholds['gc_cleanup_efficiency'], f"CONTEXT MEMORY VIOLATION: Poor context cleanup efficiency. Created: {num_contexts}, Still alive: {alive_contexts}, Efficiency: {cleanup_efficiency:.1%}. Expected: >= {self._memory_thresholds['gc_cleanup_efficiency']:.1%}. This indicates context memory leaks."
            successful_contexts = [ctx for ctx in context_lifecycle_data if 'error' not in ctx]
            if len(successful_contexts) > 2:
                first_context_memory = successful_contexts[0]['created_memory']
                last_context_memory = successful_contexts[-1]['created_memory']
                memory_growth = last_context_memory - first_context_memory
                max_allowed_growth = 20.0
                assert memory_growth <= max_allowed_growth, f'CONTEXT MEMORY VIOLATION: Excessive memory growth during context lifecycle. First context: {first_context_memory:.1f}MB, Last context: {last_context_memory:.1f}MB, Growth: {memory_growth:.1f}MB. Max allowed: {max_allowed_growth}MB. This indicates memory leaks in context lifecycle.'
            memory_after_cleanup = []
            for ctx in successful_contexts:
                if 'created_memory' in ctx and 'cleanup_memory' in ctx:
                    memory_delta = ctx['cleanup_memory'] - ctx['created_memory']
                    memory_after_cleanup.append(memory_delta)
            if memory_after_cleanup:
                avg_memory_delta = sum(memory_after_cleanup) / len(memory_after_cleanup)
                max_increase_per_cleanup = 2.0
                assert avg_memory_delta <= max_increase_per_cleanup, f'CONTEXT CLEANUP VIOLATION: Cleanup increases memory usage. Average memory delta per cleanup: {avg_memory_delta:.2f}MB. Max allowed: {max_increase_per_cleanup}MB. This indicates cleanup is not releasing memory properly.'
            final_memory = self._get_memory_snapshot()
            total_memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']
            assert total_memory_increase <= self._memory_thresholds['max_memory_increase_mb'], f"CONTEXT LIFECYCLE VIOLATION: Excessive total memory increase. Initial: {initial_memory['rss_mb']:.1f}MB, Final: {final_memory['rss_mb']:.1f}MB, Increase: {total_memory_increase:.1f}MB. Max allowed: {self._memory_thresholds['max_memory_increase_mb']}MB. This indicates overall memory management issues."
            self.record_metric('contexts_tested', num_contexts)
            self.record_metric('context_cleanup_efficiency', cleanup_efficiency)
            self.record_metric('total_memory_increase_mb', total_memory_increase)
            self.record_metric('context_lifecycle_checks_passed', 7)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during context lifecycle validation: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')