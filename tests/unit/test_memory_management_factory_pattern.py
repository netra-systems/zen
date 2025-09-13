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


class TestMemoryManagementFactoryPattern(SSotAsyncTestCase):
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

        # Start memory tracing
        tracemalloc.start()

        # Get initial memory snapshot
        self._initial_memory = self._get_memory_snapshot()

        # Track created instances for cleanup
        self._tracked_instances = []
        self._tracked_contexts = []
        self._tracked_factories = []
        self._weak_references = []

        # Memory tracking
        self._memory_snapshots = []
        self._memory_thresholds = {
            'max_memory_increase_mb': 50,  # Max 50MB increase during test
            'max_instances_retained': 10,  # Max 10 instances should be retained
            'gc_cleanup_efficiency': 0.9   # 90% of objects should be cleaned up
        }

        # Mock dependencies for testing
        self._mock_dependencies = {
            'websocket_bridge': SSotMockFactory.create_mock_agent_websocket_bridge(),
            'agent_registry': MagicMock(),  # Simple mock for agent registry
            'llm_manager': SSotMockFactory.create_mock_llm_manager()
        }

        self.record_metric("test_setup_completed", True)
        self.record_metric("initial_memory_mb", self._initial_memory['rss_mb'])

    def teardown_method(self, method):
        """Cleanup after each test method."""
        # Clean up all tracked instances
        for instance in self._tracked_instances:
            try:
                if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                    if asyncio.iscoroutinefunction(instance.cleanup):
                        asyncio.create_task(instance.cleanup())
                    else:
                        instance.cleanup()
            except Exception as e:
                print(f"Warning: Instance cleanup failed: {e}")

        # Clean up contexts
        for context in self._tracked_contexts:
            try:
                if hasattr(context, 'cleanup') and callable(context.cleanup):
                    if asyncio.iscoroutinefunction(context.cleanup):
                        asyncio.create_task(context.cleanup())
                    else:
                        context.cleanup()
            except Exception as e:
                print(f"Warning: Context cleanup failed: {e}")

        # Clean up factories
        for factory in self._tracked_factories:
            try:
                if hasattr(factory, 'reset_for_testing') and callable(factory.reset_for_testing):
                    factory.reset_for_testing()
            except Exception as e:
                print(f"Warning: Factory cleanup failed: {e}")

        # Force garbage collection
        gc.collect()

        # Get final memory snapshot
        final_memory = self._get_memory_snapshot()
        memory_increase = final_memory['rss_mb'] - self._initial_memory['rss_mb']

        self.record_metric("final_memory_mb", final_memory['rss_mb'])
        self.record_metric("memory_increase_mb", memory_increase)

        # Stop memory tracing
        tracemalloc.stop()

        super().teardown_method(method)

    def _get_memory_snapshot(self) -> Dict[str, Any]:
        """Get current memory usage snapshot."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()

            snapshot = {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident set size in MB
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual memory size in MB
                'timestamp': time.time()
            }

            # Add tracemalloc info if available
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                snapshot.update({
                    'traced_current_mb': current / 1024 / 1024,
                    'traced_peak_mb': peak / 1024 / 1024
                })

            return snapshot

        except Exception as e:
            return {
                'rss_mb': 0,
                'vms_mb': 0,
                'error': str(e),
                'timestamp': time.time()
            }

    async def _create_test_user_context(self, user_id: str) -> Any:
        """Create a test user execution context."""
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            context = UserExecutionContext.from_request_supervisor(
                user_id=f"memory_test_{user_id}",
                thread_id=f"thread_{user_id}_{int(time.time())}",
                run_id=f"run_{user_id}_{int(time.time())}"
            )

            self._tracked_contexts.append(context)
            return context

        except ImportError as e:
            pytest.skip(f"Cannot import UserExecutionContext: {e}")

    async def _create_factory_instance(self) -> Any:
        """Create and configure a factory instance."""
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory

            factory = AgentInstanceFactory()
            factory.configure(
                websocket_bridge=self._mock_dependencies['websocket_bridge'],
                agent_registry=self._mock_dependencies['agent_registry'],
                llm_manager=self._mock_dependencies['llm_manager']
            )

            self._tracked_factories.append(factory)
            return factory

        except ImportError as e:
            pytest.skip(f"Cannot import AgentInstanceFactory: {e}")

    async def test_factory_instances_cleanup_properly(self):
        """
        CRITICAL TEST: Validate factory instances and their resources cleanup properly.

        This test should FAIL before Issue #709 remediation due to memory leaks
        or improper resource cleanup in singleton patterns.

        After remediation, this test should PASS by proving proper cleanup.
        """
        self.record_metric("test_started", "test_factory_instances_cleanup_properly")

        try:
            # CRITICAL CHECK 1: Create multiple factories and track memory
            initial_snapshot = self._get_memory_snapshot()
            factories = []
            weak_refs = []

            num_factories = 5
            for i in range(num_factories):
                factory = await self._create_factory_instance()
                factories.append(factory)

                # Create weak reference to track garbage collection
                weak_ref = weakref.ref(factory)
                weak_refs.append(weak_ref)
                self._weak_references.append(weak_ref)

                # Create user contexts and agents to ensure full cleanup testing
                context = await self._create_test_user_context(f"cleanup_user_{i}")

                try:
                    # Create factory context
                    factory_context = await factory.create_user_execution_context(
                        user_id=context.user_id,
                        thread_id=context.thread_id,
                        run_id=context.run_id
                    )

                    # Create agent
                    agent = await factory.create_agent_instance(
                        agent_name='TriageSubAgent',
                        user_context=context
                    )
                    self._tracked_instances.append(agent)

                except Exception as e:
                    print(f"Warning: Failed to create agent for factory {i}: {e}")

            # Take memory snapshot after creation
            post_creation_snapshot = self._get_memory_snapshot()
            creation_memory_increase = post_creation_snapshot['rss_mb'] - initial_snapshot['rss_mb']

            # CRITICAL CHECK 2: Verify all weak references are alive
            alive_refs = sum(1 for ref in weak_refs if ref() is not None)
            assert alive_refs == num_factories, (
                f"MEMORY MANAGEMENT VIOLATION: Not all factory references alive before cleanup. "
                f"Expected: {num_factories}, Alive: {alive_refs}. "
                f"This indicates premature garbage collection."
            )

            # CRITICAL CHECK 3: Clean up factories explicitly
            for i, factory in enumerate(factories):
                try:
                    # Get factory metrics before cleanup
                    if hasattr(factory, 'get_factory_metrics'):
                        metrics = factory.get_factory_metrics()
                        active_contexts = metrics.get('active_contexts', 0)

                        # Clean up active contexts
                        if hasattr(factory, 'cleanup_inactive_contexts'):
                            cleaned = await factory.cleanup_inactive_contexts(max_age_seconds=0)
                            self.record_metric(f"factory_{i}_contexts_cleaned", cleaned)

                    # Reset factory for testing
                    if hasattr(factory, 'reset_for_testing'):
                        factory.reset_for_testing()

                except Exception as e:
                    print(f"Warning: Factory {i} cleanup failed: {e}")

            # Clear strong references to factories
            factories.clear()

            # Force garbage collection
            for _ in range(3):  # Multiple GC cycles to ensure thorough cleanup
                gc.collect()

            # Small delay to allow cleanup
            await asyncio.sleep(0.1)

            # CRITICAL CHECK 4: Verify garbage collection of factories
            # This should FAIL before remediation - factories not properly cleaned up
            alive_after_cleanup = sum(1 for ref in weak_refs if ref() is not None)
            cleanup_efficiency = (num_factories - alive_after_cleanup) / num_factories

            assert cleanup_efficiency >= self._memory_thresholds['gc_cleanup_efficiency'], (
                f"MEMORY MANAGEMENT VIOLATION: Poor garbage collection efficiency. "
                f"Created: {num_factories}, Still alive: {alive_after_cleanup}, "
                f"Efficiency: {cleanup_efficiency:.1%}. "
                f"Expected: >= {self._memory_thresholds['gc_cleanup_efficiency']:.1%}. "
                f"This indicates memory leaks in factory pattern."
            )

            # CRITICAL CHECK 5: Verify memory is reclaimed
            post_cleanup_snapshot = self._get_memory_snapshot()
            cleanup_memory_decrease = post_creation_snapshot['rss_mb'] - post_cleanup_snapshot['rss_mb']

            # Memory should decrease or at least not increase significantly after cleanup
            final_memory_increase = post_cleanup_snapshot['rss_mb'] - initial_snapshot['rss_mb']

            # This should FAIL before remediation - memory not properly reclaimed
            assert final_memory_increase <= self._memory_thresholds['max_memory_increase_mb'], (
                f"MEMORY MANAGEMENT VIOLATION: Excessive memory increase after cleanup. "
                f"Initial: {initial_snapshot['rss_mb']:.1f}MB, "
                f"Final: {post_cleanup_snapshot['rss_mb']:.1f}MB, "
                f"Increase: {final_memory_increase:.1f}MB. "
                f"Max allowed: {self._memory_thresholds['max_memory_increase_mb']}MB. "
                f"This indicates memory leaks in factory pattern."
            )

            self.record_metric("factories_created", num_factories)
            self.record_metric("cleanup_efficiency", cleanup_efficiency)
            self.record_metric("memory_cleanup_checks_passed", 5)
            self.record_metric("test_result", "PASS")

        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during memory cleanup validation: {e}")

    async def test_concurrent_factory_memory_efficiency(self):
        """
        CRITICAL TEST: Validate memory efficiency with concurrent factory usage.

        This test creates multiple factories concurrently and verifies that
        memory usage doesn't grow unbounded.

        Expected to FAIL before remediation due to memory inefficiency.
        """
        self.record_metric("test_started", "test_concurrent_factory_memory_efficiency")

        async def create_factory_workload(workload_id: int, operations_count: int) -> Dict[str, Any]:
            """Create factory workload with multiple operations."""
            try:
                # Create factory
                factory = await self._create_factory_instance()
                workload_data = {
                    'workload_id': workload_id,
                    'factory_id': id(factory),
                    'operations': [],
                    'peak_memory': 0,
                    'agents_created': 0
                }

                # Perform multiple operations
                for op_id in range(operations_count):
                    try:
                        # Create user context
                        context = await self._create_test_user_context(f"concurrent_{workload_id}_{op_id}")

                        # Create factory context
                        factory_context = await factory.create_user_execution_context(
                            user_id=context.user_id,
                            thread_id=context.thread_id,
                            run_id=context.run_id
                        )

                        # Create agent
                        agent = await factory.create_agent_instance(
                            agent_name='DataHelperAgent',
                            user_context=context
                        )
                        self._tracked_instances.append(agent)

                        workload_data['agents_created'] += 1

                        # Track memory during operation
                        current_memory = self._get_memory_snapshot()
                        workload_data['peak_memory'] = max(
                            workload_data['peak_memory'],
                            current_memory['rss_mb']
                        )

                        # Clean up this operation
                        await factory.cleanup_user_context(factory_context)

                        workload_data['operations'].append({
                            'op_id': op_id,
                            'memory_mb': current_memory['rss_mb']
                        })

                    except Exception as e:
                        workload_data['operations'].append({
                            'op_id': op_id,
                            'error': str(e)
                        })

                # Clean up factory
                if hasattr(factory, 'reset_for_testing'):
                    factory.reset_for_testing()

                return workload_data

            except Exception as e:
                return {'workload_id': workload_id, 'error': str(e)}

        try:
            # CRITICAL CHECK 1: Execute concurrent factory workloads
            initial_memory = self._get_memory_snapshot()

            concurrent_workloads = 4
            operations_per_workload = 5

            tasks = [
                create_factory_workload(workload_id, operations_per_workload)
                for workload_id in range(concurrent_workloads)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # CRITICAL CHECK 2: Verify all workloads succeeded
            failed_workloads = []
            successful_results = []

            for result in results:
                if isinstance(result, Exception):
                    failed_workloads.append(f"Exception: {result}")
                elif 'error' in result:
                    failed_workloads.append(f"Workload {result['workload_id']}: {result['error']}")
                else:
                    successful_results.append(result)

            if failed_workloads:
                pytest.fail(f"CONCURRENT MEMORY VIOLATION: Failed workloads: {failed_workloads}")

            # Force garbage collection after all workloads
            for _ in range(3):
                gc.collect()

            await asyncio.sleep(0.1)

            # CRITICAL CHECK 3: Verify memory efficiency
            final_memory = self._get_memory_snapshot()
            total_memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']

            total_operations = sum(result['agents_created'] for result in successful_results)

            # This should FAIL before remediation - excessive memory per operation
            memory_per_operation = total_memory_increase / max(total_operations, 1)
            max_memory_per_operation = 5.0  # Max 5MB per operation

            assert memory_per_operation <= max_memory_per_operation, (
                f"CONCURRENT MEMORY VIOLATION: Excessive memory per operation. "
                f"Total increase: {total_memory_increase:.1f}MB, "
                f"Operations: {total_operations}, "
                f"Per operation: {memory_per_operation:.2f}MB. "
                f"Max allowed: {max_memory_per_operation}MB. "
                f"This indicates memory inefficiency in concurrent factory usage."
            )

            # CRITICAL CHECK 4: Verify no memory leaks between operations
            for result in successful_results:
                operations = result['operations']
                if len(operations) > 1:
                    # Check memory doesn't continuously increase
                    memory_values = [
                        op['memory_mb'] for op in operations
                        if 'memory_mb' in op
                    ]

                    if len(memory_values) > 2:
                        # Memory shouldn't increase linearly (indicating leaks)
                        first_half_avg = sum(memory_values[:len(memory_values)//2]) / (len(memory_values)//2)
                        second_half_avg = sum(memory_values[len(memory_values)//2:]) / (len(memory_values) - len(memory_values)//2)

                        memory_growth_rate = (second_half_avg - first_half_avg) / first_half_avg

                        # This should FAIL before remediation - memory continuously growing
                        max_growth_rate = 0.2  # Max 20% growth during operations
                        assert memory_growth_rate <= max_growth_rate, (
                            f"MEMORY LEAK VIOLATION: Continuous memory growth in workload {result['workload_id']}. "
                            f"First half avg: {first_half_avg:.1f}MB, "
                            f"Second half avg: {second_half_avg:.1f}MB, "
                            f"Growth rate: {memory_growth_rate:.1%}. "
                            f"Max allowed: {max_growth_rate:.1%}. "
                            f"This indicates memory leaks during factory operations."
                        )

            # CRITICAL CHECK 5: Verify factory instances don't accumulate
            # Check that factory instances are properly cleaned up
            factory_ids = [result['factory_id'] for result in successful_results]
            unique_factories = set(factory_ids)

            # Should have unique factories (not reusing same instance)
            assert len(unique_factories) == len(successful_results), (
                f"FACTORY EFFICIENCY VIOLATION: Factory instances not unique. "
                f"Expected: {len(successful_results)} unique factories, "
                f"Got: {len(unique_factories)} unique. "
                f"This may indicate singleton behavior instead of factory pattern."
            )

            self.record_metric("concurrent_workloads", concurrent_workloads)
            self.record_metric("total_operations", total_operations)
            self.record_metric("memory_per_operation_mb", memory_per_operation)
            self.record_metric("concurrent_memory_checks_passed", 5)
            self.record_metric("test_result", "PASS")

        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during concurrent memory validation: {e}")

    async def test_factory_context_lifecycle_memory_management(self):
        """
        CRITICAL TEST: Validate proper memory management of factory context lifecycle.

        This test verifies that factory contexts (UserExecutionContext) are
        properly created, used, and cleaned up without memory leaks.

        Expected to FAIL before remediation due to context memory leaks.
        """
        self.record_metric("test_started", "test_factory_context_lifecycle_memory_management")

        try:
            # CRITICAL CHECK 1: Create factory and track context lifecycle
            factory = await self._create_factory_instance()
            initial_memory = self._get_memory_snapshot()

            context_lifecycle_data = []
            weak_context_refs = []

            num_contexts = 10

            # CRITICAL CHECK 2: Create multiple contexts with full lifecycle
            for i in range(num_contexts):
                try:
                    # Create user context
                    user_context = await self._create_test_user_context(f"lifecycle_{i}")

                    # Create factory context
                    factory_context = await factory.create_user_execution_context(
                        user_id=user_context.user_id,
                        thread_id=user_context.thread_id,
                        run_id=user_context.run_id
                    )

                    # Track with weak reference
                    weak_ref = weakref.ref(factory_context)
                    weak_context_refs.append(weak_ref)
                    self._weak_references.append(weak_ref)

                    # Create agent using this context
                    agent = await factory.create_agent_instance(
                        agent_name='TriageSubAgent',
                        user_context=user_context
                    )
                    self._tracked_instances.append(agent)

                    # Record context data
                    context_data = {
                        'context_id': i,
                        'user_id': user_context.user_id,
                        'factory_context_id': id(factory_context),
                        'agent_id': id(agent),
                        'created_memory': self._get_memory_snapshot()['rss_mb']
                    }

                    context_lifecycle_data.append(context_data)

                    # Immediately clean up this context
                    await factory.cleanup_user_context(factory_context)

                    # Record cleanup memory
                    context_data['cleanup_memory'] = self._get_memory_snapshot()['rss_mb']

                except Exception as e:
                    context_lifecycle_data.append({
                        'context_id': i,
                        'error': str(e)
                    })

            # CRITICAL CHECK 3: Force garbage collection
            for _ in range(3):
                gc.collect()

            await asyncio.sleep(0.1)

            # CRITICAL CHECK 4: Verify context cleanup efficiency
            errors = [ctx for ctx in context_lifecycle_data if 'error' in ctx]
            if errors:
                pytest.fail(f"CONTEXT LIFECYCLE VIOLATION: Context creation/cleanup errors: {errors}")

            # Check weak references - most should be garbage collected
            alive_contexts = sum(1 for ref in weak_context_refs if ref() is not None)
            cleanup_efficiency = (num_contexts - alive_contexts) / num_contexts

            # This should FAIL before remediation - contexts not properly cleaned up
            assert cleanup_efficiency >= self._memory_thresholds['gc_cleanup_efficiency'], (
                f"CONTEXT MEMORY VIOLATION: Poor context cleanup efficiency. "
                f"Created: {num_contexts}, Still alive: {alive_contexts}, "
                f"Efficiency: {cleanup_efficiency:.1%}. "
                f"Expected: >= {self._memory_thresholds['gc_cleanup_efficiency']:.1%}. "
                f"This indicates context memory leaks."
            )

            # CRITICAL CHECK 5: Verify memory doesn't continuously grow
            successful_contexts = [ctx for ctx in context_lifecycle_data if 'error' not in ctx]

            if len(successful_contexts) > 2:
                first_context_memory = successful_contexts[0]['created_memory']
                last_context_memory = successful_contexts[-1]['created_memory']
                memory_growth = last_context_memory - first_context_memory

                # This should FAIL before remediation - memory continuously growing
                max_allowed_growth = 20.0  # Max 20MB growth during context lifecycle
                assert memory_growth <= max_allowed_growth, (
                    f"CONTEXT MEMORY VIOLATION: Excessive memory growth during context lifecycle. "
                    f"First context: {first_context_memory:.1f}MB, "
                    f"Last context: {last_context_memory:.1f}MB, "
                    f"Growth: {memory_growth:.1f}MB. "
                    f"Max allowed: {max_allowed_growth}MB. "
                    f"This indicates memory leaks in context lifecycle."
                )

            # CRITICAL CHECK 6: Verify cleanup reduces memory usage
            memory_after_cleanup = []
            for ctx in successful_contexts:
                if 'created_memory' in ctx and 'cleanup_memory' in ctx:
                    memory_delta = ctx['cleanup_memory'] - ctx['created_memory']
                    memory_after_cleanup.append(memory_delta)

            if memory_after_cleanup:
                avg_memory_delta = sum(memory_after_cleanup) / len(memory_after_cleanup)

                # Cleanup should not significantly increase memory (should decrease or stay same)
                max_increase_per_cleanup = 2.0  # Max 2MB increase per cleanup
                assert avg_memory_delta <= max_increase_per_cleanup, (
                    f"CONTEXT CLEANUP VIOLATION: Cleanup increases memory usage. "
                    f"Average memory delta per cleanup: {avg_memory_delta:.2f}MB. "
                    f"Max allowed: {max_increase_per_cleanup}MB. "
                    f"This indicates cleanup is not releasing memory properly."
                )

            # CRITICAL CHECK 7: Verify final memory usage is reasonable
            final_memory = self._get_memory_snapshot()
            total_memory_increase = final_memory['rss_mb'] - initial_memory['rss_mb']

            assert total_memory_increase <= self._memory_thresholds['max_memory_increase_mb'], (
                f"CONTEXT LIFECYCLE VIOLATION: Excessive total memory increase. "
                f"Initial: {initial_memory['rss_mb']:.1f}MB, "
                f"Final: {final_memory['rss_mb']:.1f}MB, "
                f"Increase: {total_memory_increase:.1f}MB. "
                f"Max allowed: {self._memory_thresholds['max_memory_increase_mb']}MB. "
                f"This indicates overall memory management issues."
            )

            self.record_metric("contexts_tested", num_contexts)
            self.record_metric("context_cleanup_efficiency", cleanup_efficiency)
            self.record_metric("total_memory_increase_mb", total_memory_increase)
            self.record_metric("context_lifecycle_checks_passed", 7)
            self.record_metric("test_result", "PASS")

        except AssertionError:
            self.record_metric("test_result", "FAIL_EXPECTED_BEFORE_REMEDIATION")
            raise
        except Exception as e:
            self.record_metric("test_result", "ERROR")
            pytest.fail(f"Unexpected error during context lifecycle validation: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
