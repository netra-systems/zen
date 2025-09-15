"""
Test 1: Singleton to Factory Migration Validation

PURPOSE: Validate complete elimination of singleton patterns in agent factory modules.
ISSUE: #709 - Agent Factory Singleton Legacy remediation
SCOPE: Core SSOT validation for singleton→factory pattern migration

EXPECTED BEHAVIOR:
- BEFORE REMEDIATION: Tests should FAIL (proving SSOT violations exist)
- AFTER REMEDIATION: Tests should PASS (proving SSOT compliance)

Business Value: Platform/Internal - $500K+ ARR protection through proper user isolation
"""
import asyncio
import gc
import inspect
import sys
import time
import weakref
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

@pytest.mark.unit
class TestSingletonToFactoryMigration(SSotAsyncTestCase):
    """
    Test suite validating elimination of singleton patterns in agent factory modules.

    This test suite specifically targets Issue #709 by validating that:
    1. No global singleton instances exist in agent factory modules
    2. Factory creates UNIQUE instances per request
    3. Global `_factory_instance` variables are eliminated
    4. Proper SSOT factory pattern compliance

    CRITICAL: These tests should FAIL before remediation and PASS after.
    """

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        modules_to_reset = ['netra_backend.app.agents.supervisor.agent_instance_factory', 'netra_backend.app.agents.supervisor.execution_engine_factory']
        for module_name in modules_to_reset:
            if module_name in sys.modules:
                del sys.modules[module_name]
        gc.collect()
        self._tracked_instances = []
        self._original_factory_instances = {}
        self.record_metric('test_setup_completed', True)

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
                print(f'Warning: Cleanup failed for instance {instance}: {e}')
        for module_name, original_instance in self._original_factory_instances.items():
            try:
                module = sys.modules.get(module_name)
                if module:
                    setattr(module, '_factory_instance', original_instance)
            except Exception:
                pass
        super().teardown_method(method)

    async def test_no_singleton_instances_exist_agent_instance_factory(self):
        """
        CRITICAL TEST: Validate no singleton instances exist in AgentInstanceFactory.

        This test should FAIL before Issue #709 remediation due to:
        - Global `_factory_instance` variable existence
        - get_agent_instance_factory() returning same instance
        - Shared state between factory calls

        After remediation, this test should PASS by proving:
        - No global singleton variables
        - Each factory creation returns unique instances
        - No shared state between instances
        """
        self.record_metric('test_started', 'test_no_singleton_instances_exist_agent_instance_factory')
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory, get_agent_instance_factory
            module = sys.modules['netra_backend.app.agents.supervisor.agent_instance_factory']
            global_factory_instance = getattr(module, '_factory_instance', None)
            assert global_factory_instance is None, f'SINGLETON VIOLATION: Global _factory_instance exists: {global_factory_instance}. This proves singleton pattern is still active. Expected: None after singleton→factory migration.'
            factory1 = get_agent_instance_factory()
            factory2 = get_agent_instance_factory()
            self._tracked_instances.extend([factory1, factory2])
            assert factory1 is not factory2, f'SINGLETON VIOLATION: get_agent_instance_factory() returns same instance. factory1 id: {id(factory1)}, factory2 id: {id(factory2)}. Expected: Different instances for proper factory pattern.'
            factory1.test_marker = 'factory1_unique_marker'
            assert not hasattr(factory2, 'test_marker'), f"SINGLETON VIOLATION: Shared state detected between factory instances. factory2.test_marker exists: {getattr(factory2, 'test_marker', None)}. Expected: Independent state for each factory instance."
            direct_factory1 = AgentInstanceFactory()
            direct_factory2 = AgentInstanceFactory()
            self._tracked_instances.extend([direct_factory1, direct_factory2])
            assert direct_factory1 is not direct_factory2, f'SINGLETON VIOLATION: Direct AgentInstanceFactory() returns same instance. Expected: Unique instances from direct instantiation.'
            direct_factory1._factory_metrics['test_metric'] = 'factory1_value'
            factory2_metrics = getattr(direct_factory2, '_factory_metrics', {})
            assert 'test_metric' not in factory2_metrics, f"SINGLETON VIOLATION: Factory metrics shared between instances. factory2 metrics contain test_metric: {factory2_metrics.get('test_metric')}. Expected: Independent metrics for each factory instance."
            self.record_metric('singleton_checks_passed', 5)
            self.record_metric('test_result', 'PASS')
        except ImportError as e:
            pytest.fail(f'Cannot import AgentInstanceFactory for testing: {e}')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during singleton validation: {e}')

    async def test_no_singleton_instances_exist_execution_engine_factory(self):
        """
        CRITICAL TEST: Validate no singleton instances exist in ExecutionEngineFactory.

        This test should FAIL before Issue #709 remediation due to:
        - Global `_factory_instance` variable in execution_engine_factory
        - get_execution_engine_factory() returning same instance
        - Shared state between factory instances

        After remediation, this test should PASS by proving SSOT compliance.
        """
        self.record_metric('test_started', 'test_no_singleton_instances_exist_execution_engine_factory')
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, get_execution_engine_factory
            module = sys.modules['netra_backend.app.agents.supervisor.execution_engine_factory']
            global_factory_instance = getattr(module, '_factory_instance', None)
            assert global_factory_instance is None, f'SINGLETON VIOLATION: Global _factory_instance exists in ExecutionEngineFactory: {global_factory_instance}. This proves singleton pattern is still active. Expected: None after singleton→factory migration.'
            mock_bridge = SSotMockFactory.create_mock_websocket_bridge()
            try:
                factory1 = ExecutionEngineFactory(websocket_bridge=mock_bridge)
                factory2 = ExecutionEngineFactory(websocket_bridge=mock_bridge)
                self._tracked_instances.extend([factory1, factory2])
                assert factory1 is not factory2, f'SINGLETON VIOLATION: ExecutionEngineFactory() returns same instance. Expected: Unique instances from direct instantiation.'
                factory1._active_engines['test_engine_1'] = 'engine1'
                assert 'test_engine_1' not in factory2._active_engines, f'SINGLETON VIOLATION: Active engines shared between ExecutionEngineFactory instances. factory2._active_engines contains test_engine_1. Expected: Independent engine tracking per factory instance.'
                factory1._factory_metrics['test_created'] = 100
                assert factory2._factory_metrics.get('test_created', 0) != 100, f'SINGLETON VIOLATION: Factory metrics shared between ExecutionEngineFactory instances. factory2 metrics inherited factory1 values. Expected: Independent metrics per factory instance.'
                self.record_metric('execution_engine_factory_checks_passed', 4)
            except Exception as creation_error:
                pytest.fail(f'ExecutionEngineFactory creation failed (possible singleton dependency): {creation_error}')
            self.record_metric('test_result', 'PASS')
        except ImportError as e:
            pytest.fail(f'Cannot import ExecutionEngineFactory for testing: {e}')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during ExecutionEngineFactory singleton validation: {e}')

    async def test_factory_instance_memory_isolation(self):
        """
        CRITICAL TEST: Validate memory isolation between factory instances.

        This test verifies that factory instances don't share memory or maintain
        references to each other, which would indicate singleton-like behavior.

        Expected to FAIL before remediation due to shared memory/references.
        """
        self.record_metric('test_started', 'test_factory_instance_memory_isolation')
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            factory1 = AgentInstanceFactory()
            factory1_ref = weakref.ref(factory1)
            factory1_id = id(factory1)
            factory2 = AgentInstanceFactory()
            factory2_id = id(factory2)
            self._tracked_instances.extend([factory1, factory2])
            assert factory1_id != factory2_id, f'MEMORY ISOLATION VIOLATION: Factory instances share same memory address. factory1 id: {factory1_id}, factory2 id: {factory2_id}. Expected: Different memory addresses for independent instances.'
            del factory1
            gc.collect()
            assert factory1_ref() is None, f'MEMORY ISOLATION VIOLATION: factory1 still referenced after deletion. This indicates shared references preventing garbage collection. Expected: factory1 to be garbage collected independently.'
            assert hasattr(factory2, '_factory_metrics'), f'MEMORY ISOLATION VIOLATION: factory2 affected by factory1 garbage collection. Expected: factory2 to remain functional after factory1 deletion.'
            factory3 = AgentInstanceFactory()
            factory4 = AgentInstanceFactory()
            self._tracked_instances.extend([factory3, factory4])
            mock_websocket_bridge = SSotMockFactory.create_mock_websocket_bridge()
            mock_agent_registry = SSotMockFactory.create_mock_agent_registry()
            factory3.configure(websocket_bridge=mock_websocket_bridge, agent_registry=mock_agent_registry)
            assert factory4._websocket_bridge is None, f'CONFIGURATION ISOLATION VIOLATION: factory4 inherits factory3 configuration. factory4._websocket_bridge: {factory4._websocket_bridge}. Expected: factory4 to have independent configuration state.'
            self.record_metric('memory_isolation_checks_passed', 3)
            self.record_metric('test_result', 'PASS')
        except ImportError as e:
            pytest.fail(f'Cannot import AgentInstanceFactory for memory testing: {e}')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during memory isolation validation: {e}')

    async def test_concurrent_factory_creation_isolation(self):
        """
        CRITICAL TEST: Validate concurrent factory creation produces isolated instances.

        This test creates factories concurrently to verify no race conditions
        or shared state issues exist. Critical for multi-user production deployment.

        Expected to FAIL before remediation due to singleton race conditions.
        """
        self.record_metric('test_started', 'test_concurrent_factory_creation_isolation')

        async def create_factory_with_marker(marker_id: int) -> Dict[str, Any]:
            """Create factory and return instance info."""
            try:
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                factory = AgentInstanceFactory()
                factory.test_marker = f'concurrent_marker_{marker_id}'
                factory.test_id = marker_id
                self._tracked_instances.append(factory)
                return {'factory': factory, 'id': id(factory), 'marker': factory.test_marker, 'test_id': marker_id, 'metrics_id': id(factory._factory_metrics)}
            except Exception as e:
                return {'error': str(e), 'test_id': marker_id}
        try:
            concurrent_count = 5
            tasks = [create_factory_with_marker(i) for i in range(concurrent_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f'Concurrent factory creation {i} failed: {result}')
                if 'error' in result:
                    pytest.fail(f"Concurrent factory creation {i} error: {result['error']}")
            factory_ids = [result['id'] for result in results]
            unique_ids = set(factory_ids)
            assert len(unique_ids) == concurrent_count, f'CONCURRENT ISOLATION VIOLATION: {concurrent_count - len(unique_ids)} factories share same identity. Factory IDs: {factory_ids}. Expected: All {concurrent_count} factories to have unique identities.'
            for i, result in enumerate(results):
                expected_marker = f'concurrent_marker_{i}'
                actual_marker = result['marker']
                assert actual_marker == expected_marker, f'CONCURRENT ISOLATION VIOLATION: Factory {i} marker corrupted. Expected: {expected_marker}, Got: {actual_marker}. This indicates shared state between concurrent instances.'
            metrics_ids = [result['metrics_id'] for result in results]
            unique_metrics_ids = set(metrics_ids)
            assert len(unique_metrics_ids) == concurrent_count, f'CONCURRENT ISOLATION VIOLATION: {concurrent_count - len(unique_metrics_ids)} factories share same metrics object. Metrics IDs: {metrics_ids}. Expected: All {concurrent_count} factories to have independent metrics.'
            self.record_metric('concurrent_factories_created', concurrent_count)
            self.record_metric('concurrent_isolation_checks_passed', 4)
            self.record_metric('test_result', 'PASS')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during concurrent factory validation: {e}')

    async def test_factory_cleanup_independence(self):
        """
        CRITICAL TEST: Validate factory cleanup doesn't affect other instances.

        This test verifies that cleaning up one factory instance doesn't
        interfere with other factory instances, which would indicate shared state.

        Expected to FAIL before remediation due to shared cleanup state.
        """
        self.record_metric('test_started', 'test_factory_cleanup_independence')
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            factory1 = AgentInstanceFactory()
            factory2 = AgentInstanceFactory()
            factory3 = AgentInstanceFactory()
            self._tracked_instances.extend([factory1, factory2, factory3])
            mock_bridge = SSotMockFactory.create_mock_websocket_bridge()
            for i, factory in enumerate([factory1, factory2, factory3], 1):
                factory.configure(websocket_bridge=mock_bridge)
                factory.test_cleanup_marker = f'factory_{i}_data'
                factory._factory_metrics[f'test_metric_{i}'] = i * 100
            if hasattr(factory1, 'reset_for_testing'):
                factory1.reset_for_testing()
            else:
                factory1._active_contexts.clear()
                factory1._factory_metrics.clear()
                factory1.test_cleanup_marker = None
            assert hasattr(factory2, 'test_cleanup_marker'), f'CLEANUP ISOLATION VIOLATION: factory2 affected by factory1 cleanup. factory2.test_cleanup_marker missing. Expected: factory2 to remain unaffected by factory1 cleanup.'
            assert factory2.test_cleanup_marker == 'factory_2_data', f"CLEANUP ISOLATION VIOLATION: factory2 data corrupted by factory1 cleanup. Expected: 'factory_2_data', Got: {factory2.test_cleanup_marker}. This indicates shared state during cleanup."
            assert factory3._factory_metrics.get('test_metric_3') == 300, f"CLEANUP ISOLATION VIOLATION: factory3 metrics affected by factory1 cleanup. Expected: 300, Got: {factory3._factory_metrics.get('test_metric_3')}. This indicates shared metrics during cleanup."
            try:
                if hasattr(factory2, 'get_factory_metrics'):
                    metrics = factory2.get_factory_metrics()
                    assert 'test_metric_2' in metrics, f'CLEANUP ISOLATION VIOLATION: factory2 functionality broken by factory1 cleanup. Expected: test_metric_2 in metrics, Got: {list(metrics.keys())}.'
            except Exception as e:
                pytest.fail(f'CLEANUP ISOLATION VIOLATION: factory2 broken by factory1 cleanup: {e}')
            self.record_metric('cleanup_isolation_checks_passed', 4)
            self.record_metric('test_result', 'PASS')
        except ImportError as e:
            pytest.fail(f'Cannot import AgentInstanceFactory for cleanup testing: {e}')
        except AssertionError:
            self.record_metric('test_result', 'FAIL_EXPECTED_BEFORE_REMEDIATION')
            raise
        except Exception as e:
            self.record_metric('test_result', 'ERROR')
            pytest.fail(f'Unexpected error during cleanup isolation validation: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')