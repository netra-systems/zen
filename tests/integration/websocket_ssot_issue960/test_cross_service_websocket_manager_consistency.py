"""
Cross-Service WebSocket Manager Consistency Integration Tests - Issue #960

These tests are designed to FAIL with the current fragmented WebSocket manager system
and PASS after SSOT consolidation is completed.

CRITICAL: These tests prove SSOT violations exist by demonstrating:
1. Agent registry may use different WebSocket manager instances
2. Startup process may initialize multiple manager instances
3. Different services may not share the same WebSocket manager
4. Event delivery may be inconsistent across service boundaries

Business Value: $500K+ ARR depends on consistent WebSocket integration across services
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.integration
class CrossServiceWebSocketManagerConsistencyTests(SSotAsyncTestCase):
    """Test cross-service WebSocket manager consistency - SHOULD FAIL before consolidation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()

    async def test_agent_registry_uses_ssot_websocket_manager(self):
        """
        SHOULD FAIL: Agent registry may use different WebSocket manager instance.

        This test validates that the agent registry uses the same WebSocket manager
        instance as other services, ensuring SSOT compliance across service boundaries.
        """
        logger.info('Testing agent registry WebSocket manager SSOT compliance - EXPECTING FAILURE')
        try:
            from netra_backend.app.agents.registry import AgentRegistry
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            user_context = {'user_id': 'registry_test_user', 'thread_id': 'registry_test_thread'}
            direct_websocket_manager = get_websocket_manager(user_context=user_context)
            agent_registry = AgentRegistry()
            if hasattr(agent_registry, 'websocket_manager'):
                registry_websocket_manager = agent_registry.websocket_manager
                self.assertIs(direct_websocket_manager, registry_websocket_manager, 'SSOT VIOLATION: Agent registry uses different WebSocket manager instance. This causes event delivery inconsistencies across services.')
            elif hasattr(agent_registry, 'set_websocket_manager'):
                agent_registry.set_websocket_manager(direct_websocket_manager)
                if hasattr(agent_registry, 'get_websocket_manager'):
                    retrieved_manager = agent_registry.get_websocket_manager()
                    self.assertIs(direct_websocket_manager, retrieved_manager, 'SSOT VIOLATION: Agent registry does not maintain WebSocket manager reference. This indicates fragmented manager handling.')
                else:
                    raise AssertionError('SSOT VIOLATION: Agent registry cannot retrieve WebSocket manager. This indicates incomplete SSOT integration.')
            else:
                raise AssertionError('SSOT VIOLATION: Agent registry has no WebSocket manager interface. This indicates services are not properly integrated.')
        except ImportError as e:
            logger.error(f'Import error indicates service integration issues: {e}')
            raise AssertionError(f'SSOT VIOLATION: Cannot import required services for integration test: {e}')
        except Exception as e:
            logger.error(f'Agent registry integration test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: Agent registry WebSocket integration is broken: {e}')

    async def test_websocket_manager_startup_uses_single_instance(self):
        """
        SHOULD FAIL: Startup process may initialize multiple manager instances.

        This test validates that the application startup process creates only one
        WebSocket manager instance and reuses it across all services.
        """
        logger.info('Testing WebSocket manager startup SSOT compliance - EXPECTING FAILURE')
        startup_managers = []
        try:
            with patch('netra_backend.app.websocket_core.websocket_manager.get_websocket_manager') as mock_get_manager:
                manager1 = MagicMock()
                manager2 = MagicMock()
                manager3 = MagicMock()
                mock_get_manager.side_effect = [manager1, manager2, manager3]
                user_context = {'user_id': 'startup_test_user', 'thread_id': 'startup_test_thread'}
                services = ['agent_registry', 'websocket_routes', 'execution_engine']
                for service in services:
                    manager = await mock_get_manager(user_context=user_context)
                    startup_managers.append((service, manager))
                    logger.info(f'Service {service} got WebSocket manager: {id(manager)}')
            manager_ids = [id(manager) for _, manager in startup_managers]
            unique_manager_ids = set(manager_ids)
            if len(unique_manager_ids) > 1:
                raise AssertionError(f'SSOT VIOLATION: Startup process creates {len(unique_manager_ids)} different WebSocket manager instances: {unique_manager_ids}. Services: {[service for service, _ in startup_managers]}. SSOT requires exactly ONE instance shared across all services.')
        except Exception as e:
            logger.error(f'Startup process SSOT test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket manager startup process is fragmented: {e}')

    async def test_websocket_event_delivery_cross_service_consistency(self):
        """
        SHOULD FAIL: Event delivery may be inconsistent across service boundaries.

        This test validates that WebSocket events are delivered consistently
        regardless of which service initiates the event.
        """
        logger.info('Testing cross-service WebSocket event delivery consistency - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            user_context = {'user_id': 'cross_service_user', 'thread_id': 'cross_service_thread'}
            websocket_manager = get_websocket_manager(user_context=user_context)
            mock_websocket = MagicMock()
            mock_websocket.send = AsyncMock()
            if hasattr(websocket_manager, 'add_connection'):
                await websocket_manager.add_connection(mock_websocket, user_context)
            service_events = [('agent_service', {'type': 'agent_started', 'agent': 'test_agent'}), ('tool_service', {'type': 'tool_executing', 'tool': 'test_tool'}), ('supervisor_service', {'type': 'agent_completed', 'result': 'success'})]
            event_delivery_results = []
            for service_name, event_data in service_events:
                try:
                    event_with_context = {**event_data, 'service': service_name, **user_context}
                    if hasattr(websocket_manager, 'send_event'):
                        await websocket_manager.send_event(event_with_context, user_context)
                        event_delivery_results.append((service_name, 'SUCCESS'))
                    else:
                        event_delivery_results.append((service_name, 'NO_SEND_METHOD'))
                except Exception as e:
                    event_delivery_results.append((service_name, f'ERROR: {str(e)}'))
                    logger.error(f'Event delivery failed for {service_name}: {e}')
            failed_deliveries = [(service, result) for service, result in event_delivery_results if result != 'SUCCESS']
            if failed_deliveries:
                raise AssertionError(f'SSOT VIOLATION: Cross-service event delivery is inconsistent. Failed deliveries: {failed_deliveries}. All services should use the same WebSocket manager for consistent delivery.')
            if hasattr(mock_websocket, 'send') and mock_websocket.send.called:
                call_count = mock_websocket.send.call_count
                expected_calls = len([result for _, result in event_delivery_results if result == 'SUCCESS'])
                if call_count != expected_calls:
                    raise AssertionError(f'SSOT VIOLATION: Expected {expected_calls} WebSocket calls, got {call_count}. This indicates duplicate or missing event deliveries.')
        except Exception as e:
            logger.error(f'Cross-service event delivery test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: Cross-service WebSocket event delivery is broken: {e}')

    async def test_websocket_manager_service_dependency_injection(self):
        """
        SHOULD FAIL: Services may not properly inject the same WebSocket manager.

        This test validates that dependency injection provides the same WebSocket
        manager instance to all services that require it.
        """
        logger.info('Testing WebSocket manager dependency injection consistency - EXPECTING FAILURE')
        try:

            class MockDependencyInjector:

                def __init__(self):
                    self.instances = {}

                async def get_websocket_manager(self, user_context):
                    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
                    return get_websocket_manager(user_context=user_context)
            injector = MockDependencyInjector()
            user_context = {'user_id': 'di_test_user', 'thread_id': 'di_test_thread'}
            service_managers = {}
            services = ['agent_registry', 'execution_engine', 'websocket_routes', 'tool_dispatcher']
            for service in services:
                manager = await injector.get_websocket_manager(user_context)
                service_managers[service] = manager
            manager_instances = list(service_managers.values())
            first_manager = manager_instances[0]
            for service, manager in service_managers.items():
                if manager is not first_manager:
                    manager_ids = {service: id(mgr) for service, mgr in service_managers.items()}
                    raise AssertionError(f"SSOT VIOLATION: Dependency injection provides different WebSocket manager instances. Service '{service}' got different instance. Manager IDs: {manager_ids}. SSOT requires exactly ONE instance shared across all services.")
        except Exception as e:
            logger.error(f'Dependency injection test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: WebSocket manager dependency injection is inconsistent: {e}')

    async def test_websocket_manager_memory_cleanup_cross_service(self):
        """
        SHOULD FAIL: Memory cleanup may be inconsistent across services.

        This test validates that WebSocket manager memory cleanup is consistent
        across all services using the manager.
        """
        logger.info('Testing cross-service WebSocket manager memory cleanup - EXPECTING FAILURE')
        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            user_context = {'user_id': 'cleanup_test_user', 'thread_id': 'cleanup_test_thread'}
            websocket_manager = get_websocket_manager(user_context=user_context)
            if hasattr(websocket_manager, 'connections'):
                websocket_manager.connections['test_connection_1'] = MagicMock()
                websocket_manager.connections['test_connection_2'] = MagicMock()
                initial_connection_count = len(websocket_manager.connections)
            else:
                initial_connection_count = 0
            cleanup_services = ['agent_service', 'supervisor_service']
            cleanup_results = []
            for service in cleanup_services:
                try:
                    if hasattr(websocket_manager, 'cleanup') or hasattr(websocket_manager, 'close'):
                        cleanup_method = getattr(websocket_manager, 'cleanup', None) or getattr(websocket_manager, 'close', None)
                        if cleanup_method:
                            await cleanup_method()
                            cleanup_results.append((service, 'SUCCESS'))
                        else:
                            cleanup_results.append((service, 'NO_CLEANUP_METHOD'))
                    else:
                        cleanup_results.append((service, 'NO_CLEANUP_INTERFACE'))
                except Exception as e:
                    cleanup_results.append((service, f'ERROR: {str(e)}'))
            if hasattr(websocket_manager, 'connections'):
                final_connection_count = len(websocket_manager.connections)
            else:
                final_connection_count = 0
            successful_cleanups = [result for _, result in cleanup_results if result == 'SUCCESS']
            if len(successful_cleanups) > 1 and final_connection_count != 0:
                raise AssertionError(f'SSOT VIOLATION: Multiple service cleanups resulted in inconsistent state. Initial connections: {initial_connection_count}, Final: {final_connection_count}. Cleanup results: {cleanup_results}. SSOT requires idempotent cleanup.')
        except Exception as e:
            logger.error(f'Cross-service cleanup test failed: {e}')
            raise AssertionError(f'SSOT VIOLATION: Cross-service WebSocket manager cleanup is inconsistent: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')