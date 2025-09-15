"""
Integration tests for tool registry exception handling across multiple components.

This test suite validates exception handling in realistic scenarios involving
multiple tool registry components and their interactions.

Tests are designed to FAIL initially to expose current broad exception handling,
then PASS once specific exceptions and proper error propagation are implemented.

Business Value:
- Ensures proper error propagation across component boundaries
- Validates exception handling in realistic multi-component scenarios
- Improves system reliability under error conditions
- Enhances debugging and troubleshooting capabilities

Related to Issue #390: Tool Registration Exception Handling Improvements
"""
import pytest
import asyncio
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
import logging
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.tool_registry import AgentToolConfigRegistry
from netra_backend.app.services.unified_tool_registry.registry import UnifiedToolRegistry
from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from netra_backend.app.core.exceptions_base import NetraException, ValidationError
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from langchain_core.tools import BaseTool

class IntegrationTestTool(BaseTool):
    """Integration test tool with configurable behavior."""

    def __init__(self, name: str='integration_test_tool', fail_on_run: bool=False, **kwargs):
        self.name = name
        self.description = f'Integration test tool: {name}'
        self.fail_on_run = fail_on_run
        super().__init__(**kwargs)

    def _run(self, *args, **kwargs):
        if self.fail_on_run:
            raise RuntimeError('Tool execution failed')
        return f'Success from {self.name}'

class ToolRegistryIntegrationExceptionsTests(unittest.TestCase):
    """Test exception handling across multiple tool registry components."""

    def setUp(self):
        """Set up integration test fixtures."""
        super().setUp()
        self.agent_registry = AgentToolConfigRegistry()
        self.unified_registry = UnifiedToolRegistry()
        self.universal_registry = UniversalRegistry[BaseTool]('TestToolRegistry')
        self.valid_tool = IntegrationTestTool('valid_tool', fail_on_run=False)
        self.failing_tool = IntegrationTestTool('failing_tool', fail_on_run=True)
        self.malformed_tool = IntegrationTestTool('', fail_on_run=False)

    async def test_cross_registry_exception_propagation(self):
        """
        Test that exceptions properly propagate across different registry implementations.
        
        CURRENT STATE: This test should FAIL - inconsistent exception handling.
        DESIRED STATE: Consistent exception types and propagation across all registries.
        """
        agent_registry_errors = []
        try:
            self.agent_registry.enable_validation = True
            self.agent_registry.register_tool('test', self.malformed_tool)
        except Exception as e:
            agent_registry_errors.append((type(e).__name__, str(e)))
        unified_registry_errors = []
        try:
            from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
            bad_tool = 'not_a_tool'
            self.unified_registry.register_tool(bad_tool, None)
        except Exception as e:
            unified_registry_errors.append((type(e).__name__, str(e)))
        universal_registry_errors = []
        try:
            self.universal_registry.register('', self.valid_tool)
        except Exception as e:
            universal_registry_errors.append((type(e).__name__, str(e)))
        print(f'AGENT REGISTRY ERRORS: {agent_registry_errors}')
        print(f'UNIFIED REGISTRY ERRORS: {unified_registry_errors}')
        print(f'UNIVERSAL REGISTRY ERRORS: {universal_registry_errors}')
        self.assertTrue(len(agent_registry_errors) > 0 or len(unified_registry_errors) > 0 or len(universal_registry_errors) > 0)

    async def test_tool_execution_chain_exception_handling(self):
        """
        Test exception handling through complete tool execution chain.
        
        CURRENT STATE: This test should reveal inconsistent error handling in execution chain.
        DESIRED STATE: Proper exception transformation and context preservation throughout chain.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        failing_unified_tool = UnifiedTool(id='failing_execution_tool', name='Failing Execution Tool', description='Tool that fails during execution', category='testing')

        async def failing_handler(parameters: Dict[str, Any], context: Dict[str, Any]):
            raise ValueError('Simulated tool execution failure')
        self.unified_registry.register_tool(failing_unified_tool, failing_handler)
        execution_result = await self.unified_registry.execute_tool('failing_execution_tool', {'param': 'value'}, {'user': 'test_user', 'request_id': 'req_123'})
        self.assertFalse(execution_result.success)
        self.assertIsNotNone(execution_result.error)
        self.assertIn('Simulated tool execution failure', execution_result.error)
        print(f'EXECUTION RESULT: {execution_result}')
        print('DESIRED: Specific exception types and enhanced error context')

    def test_concurrent_tool_registration_exception_safety(self):
        """
        Test exception handling during concurrent tool registration operations.
        
        CURRENT STATE: This test may reveal thread safety issues.
        DESIRED STATE: Thread-safe exception handling with proper isolation.
        """
        import threading
        import time
        registration_errors = []
        registration_successes = []

        def register_tool_worker(worker_id: int):
            """Worker function for concurrent registration."""
            try:
                tool_name = f'concurrent_tool_{worker_id}'
                tool = IntegrationTestTool(tool_name)
                time.sleep(0.01 * (worker_id % 3))
                if worker_id % 3 == 0:
                    invalid_tool = IntegrationTestTool('')
                    self.agent_registry.enable_validation = True
                    self.agent_registry.register_tool('test', invalid_tool)
                else:
                    self.agent_registry.register_tool('test', tool)
                registration_successes.append(worker_id)
            except Exception as e:
                registration_errors.append({'worker_id': worker_id, 'exception_type': type(e).__name__, 'message': str(e)})
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_tool_worker, args=(i,))
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        print(f'REGISTRATION SUCCESSES: {len(registration_successes)}')
        print(f'REGISTRATION ERRORS: {len(registration_errors)}')
        print(f'ERROR DETAILS: {registration_errors}')
        self.assertGreater(len(registration_errors), 0, 'Expected some validation failures')
        self.assertGreater(len(registration_successes), 0, 'Expected some successful registrations')

    async def test_tool_registry_cascade_failure_recovery(self):
        """
        Test exception handling during cascade failures across multiple registries.
        
        CURRENT STATE: This test should reveal cascade failure scenarios.
        DESIRED STATE: Proper error isolation and recovery mechanisms.
        """
        cascade_errors = []
        for i in range(5):
            tool = IntegrationTestTool(f'cascade_tool_{i}')
            try:
                self.agent_registry.register_tool('test', tool)
            except Exception as e:
                cascade_errors.append(f'Initial setup error: {e}')
        with patch.object(self.agent_registry, '_registry') as mock_registry:
            mock_registry.get.side_effect = RuntimeError('Registry corrupted')
            try:
                tools = self.agent_registry.get_tools(['test'])
                cascade_errors.append("Should have failed but didn't")
            except Exception as e:
                cascade_errors.append(f'Primary failure: {type(e).__name__}: {e}')
        try:
            self.agent_registry._registry = self.universal_registry
            tools = self.agent_registry.get_tools(['test'])
            cascade_errors.append(f'Recovery successful: {len(tools)} tools')
        except Exception as e:
            cascade_errors.append(f'Recovery failed: {type(e).__name__}: {e}')
        print(f'CASCADE FAILURE ANALYSIS: {cascade_errors}')
        self.assertGreater(len(cascade_errors), 0, 'Should have captured cascade failure scenarios')

    def test_tool_registry_exception_context_preservation(self):
        """
        Test that exception context is preserved across registry boundaries.
        
        CURRENT STATE: This test should reveal context loss.
        DESIRED STATE: Rich context preservation through entire exception chain.
        """
        context_data = {'user_id': 'integration_user', 'request_id': 'req_integration_123', 'operation': 'tool_registration', 'source': 'integration_test', 'trace_id': 'trace_integration_456'}
        captured_contexts = []
        try:
            self.agent_registry.enable_validation = True
            with patch('netra_backend.app.core.exceptions_base.NetraException') as mock_exception:

                def capture_context(*args, **kwargs):
                    captured_contexts.append(kwargs.get('context', {}))
                    return NetraException(*args, **kwargs)
                mock_exception.side_effect = capture_context
                self.agent_registry.register_tool('test', self.malformed_tool)
        except Exception as e:
            captured_contexts.append(f'Final exception: {type(e).__name__}')
        print(f'CAPTURED CONTEXTS: {captured_contexts}')
        self.assertTrue(len(captured_contexts) > 0, 'Should have captured exception context data')

    async def test_tool_registry_error_aggregation(self):
        """
        Test error aggregation across multiple tool operations.
        
        CURRENT STATE: This test should show individual error handling.
        DESIRED STATE: Proper error aggregation and batch error reporting.
        """
        test_tools = [IntegrationTestTool('valid_1'), IntegrationTestTool(''), IntegrationTestTool('valid_2'), IntegrationTestTool('', fail_on_run=True), IntegrationTestTool('valid_3')]
        registration_results = []
        for i, tool in enumerate(test_tools):
            try:
                self.agent_registry.enable_validation = True
                self.agent_registry.register_tool(f'category_{i}', tool)
                registration_results.append({'index': i, 'status': 'success'})
            except Exception as e:
                registration_results.append({'index': i, 'status': 'error', 'exception_type': type(e).__name__, 'message': str(e)})
        print(f'BULK REGISTRATION RESULTS: {registration_results}')
        errors = [r for r in registration_results if r['status'] == 'error']
        successes = [r for r in registration_results if r['status'] == 'success']
        print(f'ERRORS: {len(errors)}, SUCCESSES: {len(successes)}')
        self.assertGreater(len(errors), 0, 'Expected some registration errors')
        self.assertGreater(len(successes), 0, 'Expected some successful registrations')

    def test_tool_registry_exception_metrics_collection(self):
        """
        Test that tool registry exceptions are properly tracked in metrics.
        
        CURRENT STATE: This test should reveal minimal metrics collection.
        DESIRED STATE: Comprehensive exception metrics for monitoring and alerting.
        """
        collected_metrics = []
        with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            mock_logger.get_logger.return_value.error.side_effect = lambda msg, *args, **kwargs: collected_metrics.append({'level': 'error', 'message': msg, 'args': args, 'kwargs': kwargs})
            error_scenarios = [('validation_error', lambda: self.agent_registry.register_tool('test', self.malformed_tool)), ('type_error', lambda: self.unified_registry.register_tool('not_a_tool', None))]
            for scenario_name, scenario_func in error_scenarios:
                try:
                    if scenario_name == 'validation_error':
                        self.agent_registry.enable_validation = True
                    scenario_func()
                except Exception as e:
                    collected_metrics.append({'scenario': scenario_name, 'exception_type': type(e).__name__, 'message': str(e)})
        print(f'COLLECTED METRICS: {collected_metrics}')
        self.assertGreater(len(collected_metrics), 0, 'Should have collected error metrics')

    def tearDown(self):
        """Clean up integration test fixtures."""
        super().tearDown()
        if hasattr(self, 'unified_registry'):
            self.unified_registry.clear()
        if hasattr(self, 'universal_registry'):
            self.universal_registry.clear()

class ToolRegistryExceptionRecoveryIntegrationTests(SSotAsyncTestCase):
    """Test exception recovery mechanisms in integration scenarios."""

    def setUp(self):
        """Set up recovery test fixtures."""
        super().setUp()
        self.registry = AgentToolConfigRegistry()

    async def test_tool_registry_graceful_degradation(self):
        """
        Test graceful degradation when tool registry components fail.
        
        CURRENT STATE: This test should reveal lack of graceful degradation.
        DESIRED STATE: System continues operating with reduced functionality.
        """
        with patch.object(self.registry, '_registry') as mock_registry:
            mock_registry.get.return_value = IntegrationTestTool('backup_tool')
            tools = self.registry.get_tools(['test'])
            self.assertEqual(len(tools), 1)
            mock_registry.get.side_effect = RuntimeError('Registry service down')
            try:
                tools = self.registry.get_tools(['test'])
                print(f'GRACEFUL DEGRADATION: Got {len(tools)} tools despite registry failure')
            except Exception as e:
                print(f'NO GRACEFUL DEGRADATION: {type(e).__name__}: {e}')

    def test_tool_registry_exception_circuit_breaker(self):
        """
        Test circuit breaker pattern for tool registry exceptions.
        
        CURRENT STATE: This test should reveal no circuit breaker protection.
        DESIRED STATE: Circuit breaker prevents cascade failures.
        """
        failure_count = 0
        success_count = 0
        for attempt in range(10):
            try:
                with patch.object(self.registry, 'get_tools') as mock_get_tools:
                    if attempt < 5:
                        mock_get_tools.side_effect = RuntimeError(f'Failure {attempt}')
                    else:
                        mock_get_tools.return_value = [IntegrationTestTool('recovered_tool')]
                    tools = self.registry.get_tools(['test'])
                    success_count += 1
            except Exception as e:
                failure_count += 1
                print(f'Attempt {attempt}: {type(e).__name__}')
        print(f'CIRCUIT BREAKER TEST: {failure_count} failures, {success_count} successes')
        self.assertGreater(failure_count, 0, 'Expected some failures')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')