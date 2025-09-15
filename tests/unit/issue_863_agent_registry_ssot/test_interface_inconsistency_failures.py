"""
Test AgentRegistry Interface Inconsistency Failures (Issue #914)

This test module demonstrates critical interface inconsistencies between the two
AgentRegistry implementations that prevent WebSocket integration and block
the Golden Path user flow.

Business Value: Protects $500K+ ARR by identifying interface conflicts that cause
AttributeError exceptions when agents try to list available agents or set up
WebSocket connections for real-time chat events.

Test Category: Unit (no Docker required)
Purpose: Failing tests to demonstrate interface incompatibility problems
"""
import asyncio
import inspect
import importlib
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock
import pytest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger
logger = get_logger(__name__)

@pytest.mark.unit
class AgentRegistryInterfaceInconsistencyFailuresTests(SSotAsyncTestCase):
    """
    Test interface inconsistencies between AgentRegistry implementations.
    
    These tests are DESIGNED TO FAIL initially to demonstrate how interface
    differences prevent proper WebSocket integration and Golden Path functionality.
    """

    def setup_method(self, method):
        """Setup test environment."""
        self.basic_registry_module = 'netra_backend.app.agents.registry'
        self.advanced_registry_module = 'netra_backend.app.agents.supervisor.agent_registry'
        self.websocket_methods = ['set_websocket_manager', 'set_websocket_bridge', '_notify_agent_event']
        self.discovery_methods = ['list_available_agents', 'get_agent', 'get_agent_class']

    def test_set_websocket_manager_signature_incompatibility(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate set_websocket_manager signature conflicts.
        
        The basic registry has sync method while advanced has async method with
        additional user_context parameter. This prevents consistent WebSocket setup.
        """
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            basic_method = getattr(basic_registry_class, 'set_websocket_manager')
            advanced_method = getattr(advanced_registry_class, 'set_websocket_manager')
            basic_signature = inspect.signature(basic_method)
            advanced_signature = inspect.signature(advanced_method)
            logger.error(f'Basic registry signature: {basic_signature}')
            logger.error(f'Advanced registry signature: {advanced_signature}')
            basic_is_async = asyncio.iscoroutinefunction(basic_method)
            advanced_is_async = asyncio.iscoroutinefunction(advanced_method)
            logger.error(f'Basic registry async: {basic_is_async}')
            logger.error(f'Advanced registry async: {advanced_is_async}')
            basic_params = list(basic_signature.parameters.keys())
            advanced_params = list(advanced_signature.parameters.keys())
            logger.error(f'Basic registry parameters: {basic_params}')
            logger.error(f'Advanced registry parameters: {advanced_params}')
            if basic_is_async != advanced_is_async or len(basic_params) != len(advanced_params) or basic_params != advanced_params:
                signature_diff = f"Basic: {basic_signature} ({('async' if basic_is_async else 'sync')}), Advanced: {advanced_signature} ({('async' if advanced_is_async else 'sync')})"
                self.fail(f'CRITICAL WEBSOCKET INTEGRATION FAILURE: set_websocket_manager methods have incompatible signatures. This prevents consistent WebSocket setup across the codebase, blocking Golden Path real-time events. Signature differences: {signature_diff}')
        except AttributeError as e:
            self.fail(f'Method signature analysis failed due to missing method: {e}')
        except Exception as e:
            self.fail(f'Unexpected error during signature analysis: {e}')
        logger.info('WebSocket manager method signatures are compatible - SSOT compliance achieved')

    def test_list_available_agents_missing_method_failure(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate missing list_available_agents method.
        
        This reproduces the AttributeError: 'AgentRegistry' object has no attribute 'list_available_agents'
        that's currently failing in the mission critical test.
        """
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            basic_has_method = hasattr(basic_registry_class, 'list_available_agents')
            advanced_has_method = hasattr(advanced_registry_class, 'list_available_agents')
            logger.info(f'Basic registry has list_available_agents: {basic_has_method}')
            logger.info(f'Advanced registry has list_available_agents: {advanced_has_method}')
            method_results = {}
            if basic_has_method:
                try:
                    basic_instance = basic_registry_class()
                    basic_result = basic_instance.list_available_agents()
                    method_results['basic'] = {'success': True, 'result': basic_result, 'type': type(basic_result).__name__}
                except Exception as e:
                    method_results['basic'] = {'success': False, 'error': str(e)}
            else:
                method_results['basic'] = {'success': False, 'error': 'Method does not exist'}
            if advanced_has_method:
                try:
                    advanced_instance = advanced_registry_class()
                    advanced_result = advanced_instance.list_available_agents()
                    method_results['advanced'] = {'success': True, 'result': advanced_result, 'type': type(advanced_result).__name__}
                except Exception as e:
                    method_results['advanced'] = {'success': False, 'error': str(e)}
            else:
                method_results['advanced'] = {'success': False, 'error': 'Method does not exist'}
            logger.error(f'Method execution results: {method_results}')
            if not basic_has_method or not advanced_has_method:
                missing_registries = []
                if not basic_has_method:
                    missing_registries.append('basic registry')
                if not advanced_has_method:
                    missing_registries.append('advanced registry')
                self.fail(f"CRITICAL AGENT DISCOVERY FAILURE: list_available_agents method missing from {', '.join(missing_registries)}. This causes AttributeError exceptions in production code that depends on agent discovery, blocking Golden Path functionality. Current test failure is caused by this SSOT violation.")
            if method_results['basic']['success'] and method_results['advanced']['success']:
                basic_type = method_results['basic']['type']
                advanced_type = method_results['advanced']['type']
                if basic_type != advanced_type:
                    self.fail(f'INCONSISTENT RETURN TYPES: list_available_agents returns different types. Basic: {basic_type}, Advanced: {advanced_type}. This causes type-related runtime failures in Golden Path.')
        except Exception as e:
            self.fail(f'Unexpected error during method availability analysis: {e}')
        logger.info('Agent discovery methods are consistent - SSOT compliance achieved')

    def test_websocket_bridge_integration_incompatibility(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate WebSocket bridge integration failures.
        
        This test shows how different registry interfaces prevent proper WebSocket
        bridge setup, blocking real-time agent events in the Golden Path.
        """
        mock_websocket_manager = Mock()
        mock_websocket_bridge = Mock()
        mock_user_context = Mock()
        integration_failures = []
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            try:
                basic_instance = basic_registry_class()
                if hasattr(basic_instance, 'set_websocket_manager'):
                    basic_instance.set_websocket_manager(mock_websocket_manager)
                    logger.info('Basic registry WebSocket manager setup: SUCCESS')
                else:
                    integration_failures.append('Basic registry missing set_websocket_manager')
                if hasattr(basic_instance, 'set_websocket_bridge'):
                    basic_instance.set_websocket_bridge(mock_websocket_bridge)
                    logger.info('Basic registry WebSocket bridge setup: SUCCESS')
                else:
                    integration_failures.append('Basic registry missing set_websocket_bridge')
            except Exception as e:
                integration_failures.append(f'Basic registry integration error: {e}')
                logger.error(f'Basic registry WebSocket integration failed: {e}')
            try:
                advanced_instance = advanced_registry_class()
                if hasattr(advanced_instance, 'set_websocket_manager'):
                    method = getattr(advanced_instance, 'set_websocket_manager')
                    if asyncio.iscoroutinefunction(method):
                        try:
                            asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager, mock_user_context))
                            logger.info('Advanced registry WebSocket manager setup (async with context): SUCCESS')
                        except Exception as e:
                            try:
                                asyncio.get_event_loop().run_until_complete(method(mock_websocket_manager))
                                logger.info('Advanced registry WebSocket manager setup (async): SUCCESS')
                            except Exception as e2:
                                integration_failures.append(f'Advanced registry async setup failed: {e2}')
                    else:
                        try:
                            method(mock_websocket_manager)
                            logger.info('Advanced registry WebSocket manager setup (sync): SUCCESS')
                        except Exception as e:
                            integration_failures.append(f'Advanced registry sync setup failed: {e}')
                else:
                    integration_failures.append('Advanced registry missing set_websocket_manager')
            except Exception as e:
                integration_failures.append(f'Advanced registry integration error: {e}')
                logger.error(f'Advanced registry WebSocket integration failed: {e}')
            if integration_failures:
                failure_summary = '; '.join(integration_failures)
                self.fail(f'CRITICAL WEBSOCKET INTEGRATION FAILURES: {len(integration_failures)} integration issues detected. These prevent proper WebSocket bridge setup, blocking real-time agent events that deliver $500K+ ARR chat functionality. Integration failures: {failure_summary}')
        except Exception as e:
            self.fail(f'Unexpected error during WebSocket integration testing: {e}')
        logger.info('WebSocket bridge integration is compatible across registries - SSOT compliance achieved')

    def test_method_parameter_type_incompatibility(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate method parameter type mismatches.
        
        This test identifies cases where the same method name exists but expects
        different parameter types, causing runtime type errors.
        """
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            basic_methods = {name: getattr(basic_registry_class, name) for name in dir(basic_registry_class) if not name.startswith('_') and callable(getattr(basic_registry_class, name))}
            advanced_methods = {name: getattr(advanced_registry_class, name) for name in dir(advanced_registry_class) if not name.startswith('_') and callable(getattr(advanced_registry_class, name))}
            common_methods = set(basic_methods.keys()) & set(advanced_methods.keys())
            logger.info(f'Common methods between registries: {common_methods}')
            type_incompatibilities = []
            for method_name in common_methods:
                basic_method = basic_methods[method_name]
                advanced_method = advanced_methods[method_name]
                try:
                    basic_signature = inspect.signature(basic_method)
                    advanced_signature = inspect.signature(advanced_method)
                    basic_params = {name: param.annotation for name, param in basic_signature.parameters.items()}
                    advanced_params = {name: param.annotation for name, param in advanced_signature.parameters.items()}
                    param_conflicts = []
                    for param_name in set(basic_params.keys()) & set(advanced_params.keys()):
                        if param_name != 'self':
                            basic_type = basic_params[param_name]
                            advanced_type = advanced_params[param_name]
                            if basic_type != inspect.Parameter.empty and advanced_type != inspect.Parameter.empty and (basic_type != advanced_type):
                                param_conflicts.append(f'{param_name}: basic expects {basic_type}, advanced expects {advanced_type}')
                    if param_conflicts:
                        type_incompatibilities.append({'method': method_name, 'conflicts': param_conflicts})
                except Exception as e:
                    logger.warning(f'Could not analyze method {method_name}: {e}')
            if type_incompatibilities:
                incompatibility_details = []
                for incompatibility in type_incompatibilities:
                    details = f"Method '{incompatibility['method']}': {'; '.join(incompatibility['conflicts'])}"
                    incompatibility_details.append(details)
                self.fail(f"CRITICAL TYPE INCOMPATIBILITY: {len(type_incompatibilities)} methods have parameter type conflicts. This causes TypeError exceptions when code written for one registry is used with the other, creating unpredictable Golden Path failures. Type conflicts: {'; '.join(incompatibility_details)}")
        except Exception as e:
            self.fail(f'Unexpected error during type compatibility analysis: {e}')
        logger.info('Method parameter types are compatible - SSOT compliance achieved')

    async def test_async_sync_method_mismatch_failures(self):
        """
        TEST DESIGNED TO FAIL: Demonstrate async/sync method mismatches.
        
        This test shows how calling async methods synchronously or sync methods
        asynchronously causes failures in production code.
        """
        try:
            basic_module = importlib.import_module(self.basic_registry_module)
            advanced_module = importlib.import_module(self.advanced_registry_module)
            basic_registry_class = getattr(basic_module, 'AgentRegistry')
            advanced_registry_class = getattr(advanced_module, 'AgentRegistry')
            basic_instance = basic_registry_class()
            advanced_instance = advanced_registry_class()
            async_sync_failures = []
            critical_methods = ['set_websocket_manager', 'get_agent', 'register_agent']
            for method_name in critical_methods:
                if hasattr(basic_instance, method_name) and hasattr(advanced_instance, method_name):
                    basic_method = getattr(basic_instance, method_name)
                    advanced_method = getattr(advanced_instance, method_name)
                    basic_is_async = asyncio.iscoroutinefunction(basic_method)
                    advanced_is_async = asyncio.iscoroutinefunction(advanced_method)
                    if basic_is_async != advanced_is_async:
                        async_sync_failures.append({'method': method_name, 'basic_async': basic_is_async, 'advanced_async': advanced_is_async})
                        logger.error(f"Async/sync mismatch in {method_name}: basic={('async' if basic_is_async else 'sync')}, advanced={('async' if advanced_is_async else 'sync')}")
            if async_sync_failures:
                mismatch_details = []
                for failure in async_sync_failures:
                    detail = f"{failure['method']}: basic is {('async' if failure['basic_async'] else 'sync')}, advanced is {('async' if failure['advanced_async'] else 'sync')}"
                    mismatch_details.append(detail)
                self.fail(f"CRITICAL ASYNC/SYNC MISMATCH: {len(async_sync_failures)} methods have async/sync inconsistencies. This causes 'coroutine was never awaited' warnings or 'object is not awaitable' errors when code written for one registry is used with the other, blocking Golden Path execution. Mismatches: {'; '.join(mismatch_details)}")
        except Exception as e:
            self.fail(f'Unexpected error during async/sync analysis: {e}')
        logger.info('Async/sync patterns are consistent across registries - SSOT compliance achieved')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')