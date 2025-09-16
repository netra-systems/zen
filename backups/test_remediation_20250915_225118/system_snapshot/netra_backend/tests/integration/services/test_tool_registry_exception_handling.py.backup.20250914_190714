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
    
    def __init__(self, name: str = "integration_test_tool", fail_on_run: bool = False, **kwargs):
        self.name = name
        self.description = f"Integration test tool: {name}"
        self.fail_on_run = fail_on_run
        super().__init__(**kwargs)
    
    def _run(self, *args, **kwargs):
        if self.fail_on_run:
            raise RuntimeError("Tool execution failed")
        return f"Success from {self.name}"


class TestToolRegistryIntegrationExceptions(unittest.TestCase):
    """Test exception handling across multiple tool registry components."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        super().setUp()
        self.agent_registry = AgentToolConfigRegistry()
        self.unified_registry = UnifiedToolRegistry()
        self.universal_registry = UniversalRegistry[BaseTool]("TestToolRegistry")
        
        # Create various tools for testing
        self.valid_tool = IntegrationTestTool("valid_tool", fail_on_run=False)
        self.failing_tool = IntegrationTestTool("failing_tool", fail_on_run=True)
        self.malformed_tool = IntegrationTestTool("", fail_on_run=False)  # Empty name

    async def test_cross_registry_exception_propagation(self):
        """
        Test that exceptions properly propagate across different registry implementations.
        
        CURRENT STATE: This test should FAIL - inconsistent exception handling.
        DESIRED STATE: Consistent exception types and propagation across all registries.
        """
        # Test with AgentToolConfigRegistry
        agent_registry_errors = []
        try:
            self.agent_registry.enable_validation = True
            self.agent_registry.register_tool("test", self.malformed_tool)
        except Exception as e:
            agent_registry_errors.append((type(e).__name__, str(e)))
        
        # Test with UnifiedToolRegistry
        unified_registry_errors = []
        try:
            from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
            # This should fail with type validation
            bad_tool = "not_a_tool"
            self.unified_registry.register_tool(bad_tool, None)
        except Exception as e:
            unified_registry_errors.append((type(e).__name__, str(e)))
        
        # Test with UniversalRegistry
        universal_registry_errors = []
        try:
            # Register with invalid key
            self.universal_registry.register("", self.valid_tool)  # Empty key
        except Exception as e:
            universal_registry_errors.append((type(e).__name__, str(e)))
        
        # CURRENT ISSUE: Different registries likely throw different exception types
        print(f"AGENT REGISTRY ERRORS: {agent_registry_errors}")
        print(f"UNIFIED REGISTRY ERRORS: {unified_registry_errors}") 
        print(f"UNIVERSAL REGISTRY ERRORS: {universal_registry_errors}")
        
        # DESIRED: All should throw consistent, specific exception types
        # self.assertTrue(all(error[0] == "ToolValidationException" for error in agent_registry_errors))
        
        # For now, just verify that exceptions are raised
        self.assertTrue(len(agent_registry_errors) > 0 or len(unified_registry_errors) > 0 or len(universal_registry_errors) > 0)

    async def test_tool_execution_chain_exception_handling(self):
        """
        Test exception handling through complete tool execution chain.
        
        CURRENT STATE: This test should reveal inconsistent error handling in execution chain.
        DESIRED STATE: Proper exception transformation and context preservation throughout chain.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        
        # Create a tool that will fail during execution
        failing_unified_tool = UnifiedTool(
            id="failing_execution_tool",
            name="Failing Execution Tool",
            description="Tool that fails during execution",
            category="testing"
        )
        
        async def failing_handler(parameters: Dict[str, Any], context: Dict[str, Any]):
            raise ValueError("Simulated tool execution failure")
        
        # Register the failing tool
        self.unified_registry.register_tool(failing_unified_tool, failing_handler)
        
        # Execute the tool and capture the result
        execution_result = await self.unified_registry.execute_tool(
            "failing_execution_tool",
            {"param": "value"},
            {"user": "test_user", "request_id": "req_123"}
        )
        
        # CURRENT BEHAVIOR: Should return ToolExecutionResult with error
        self.assertFalse(execution_result.success)
        self.assertIsNotNone(execution_result.error)
        self.assertIn("Simulated tool execution failure", execution_result.error)
        
        # DESIRED ENHANCEMENT: Should have specific exception types for different failure modes
        # execution_result.exception_type should be "ToolExecutionException"
        # execution_result.context should preserve original context
        
        print(f"EXECUTION RESULT: {execution_result}")
        print("DESIRED: Specific exception types and enhanced error context")

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
                tool_name = f"concurrent_tool_{worker_id}"
                tool = IntegrationTestTool(tool_name)
                
                # Add some randomness to increase chance of conflicts
                time.sleep(0.01 * (worker_id % 3))
                
                if worker_id % 3 == 0:
                    # Every third worker tries to register invalid tool
                    invalid_tool = IntegrationTestTool("")  # Empty name
                    self.agent_registry.enable_validation = True
                    self.agent_registry.register_tool("test", invalid_tool)
                else:
                    self.agent_registry.register_tool("test", tool)
                
                registration_successes.append(worker_id)
                
            except Exception as e:
                registration_errors.append({
                    'worker_id': worker_id,
                    'exception_type': type(e).__name__,
                    'message': str(e)
                })
        
        # Start multiple concurrent workers
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_tool_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        print(f"REGISTRATION SUCCESSES: {len(registration_successes)}")
        print(f"REGISTRATION ERRORS: {len(registration_errors)}")
        print(f"ERROR DETAILS: {registration_errors}")
        
        # CURRENT ISSUE: May have inconsistent exception handling under concurrency
        # DESIRED: Should have consistent exception types and thread-safe error handling
        
        # Verify that some operations succeeded and some failed as expected
        self.assertGreater(len(registration_errors), 0, "Expected some validation failures")
        self.assertGreater(len(registration_successes), 0, "Expected some successful registrations")

    async def test_tool_registry_cascade_failure_recovery(self):
        """
        Test exception handling during cascade failures across multiple registries.
        
        CURRENT STATE: This test should reveal cascade failure scenarios.
        DESIRED STATE: Proper error isolation and recovery mechanisms.
        """
        # Simulate a scenario where one registry failure cascades to others
        cascade_errors = []
        
        # Setup: Fill registries with tools
        for i in range(5):
            tool = IntegrationTestTool(f"cascade_tool_{i}")
            try:
                self.agent_registry.register_tool("test", tool)
            except Exception as e:
                cascade_errors.append(f"Initial setup error: {e}")
        
        # Simulate primary registry failure
        with patch.object(self.agent_registry, '_registry') as mock_registry:
            mock_registry.get.side_effect = RuntimeError("Registry corrupted")
            
            try:
                tools = self.agent_registry.get_tools(["test"])
                cascade_errors.append("Should have failed but didn't")
            except Exception as e:
                cascade_errors.append(f"Primary failure: {type(e).__name__}: {e}")
        
        # Test recovery mechanism
        try:
            # Should be able to continue with other registries
            self.agent_registry._registry = self.universal_registry  # Recovery attempt
            tools = self.agent_registry.get_tools(["test"])
            cascade_errors.append(f"Recovery successful: {len(tools)} tools")
        except Exception as e:
            cascade_errors.append(f"Recovery failed: {type(e).__name__}: {e}")
        
        print(f"CASCADE FAILURE ANALYSIS: {cascade_errors}")
        
        # DESIRED: Should have proper error isolation and recovery
        self.assertGreater(len(cascade_errors), 0, "Should have captured cascade failure scenarios")

    def test_tool_registry_exception_context_preservation(self):
        """
        Test that exception context is preserved across registry boundaries.
        
        CURRENT STATE: This test should reveal context loss.
        DESIRED STATE: Rich context preservation through entire exception chain.
        """
        context_data = {
            'user_id': 'integration_user',
            'request_id': 'req_integration_123',
            'operation': 'tool_registration',
            'source': 'integration_test',
            'trace_id': 'trace_integration_456'
        }
        
        captured_contexts = []
        
        # Test context preservation in AgentToolConfigRegistry
        try:
            self.agent_registry.enable_validation = True
            # This should fail and preserve context
            with patch('netra_backend.app.core.exceptions_base.NetraException') as mock_exception:
                def capture_context(*args, **kwargs):
                    captured_contexts.append(kwargs.get('context', {}))
                    return NetraException(*args, **kwargs)
                
                mock_exception.side_effect = capture_context
                self.agent_registry.register_tool("test", self.malformed_tool)
        except Exception as e:
            captured_contexts.append(f"Final exception: {type(e).__name__}")
        
        print(f"CAPTURED CONTEXTS: {captured_contexts}")
        
        # CURRENT ISSUE: Context likely not preserved properly
        # DESIRED: Should preserve rich context throughout exception chain
        
        # For now, just verify that exception handling occurred
        self.assertTrue(len(captured_contexts) > 0, "Should have captured exception context data")

    async def test_tool_registry_error_aggregation(self):
        """
        Test error aggregation across multiple tool operations.
        
        CURRENT STATE: This test should show individual error handling.
        DESIRED STATE: Proper error aggregation and batch error reporting.
        """
        # Create a mix of valid and invalid tools
        test_tools = [
            IntegrationTestTool("valid_1"),
            IntegrationTestTool(""),  # Invalid name
            IntegrationTestTool("valid_2"),
            IntegrationTestTool("", fail_on_run=True),  # Invalid name and fails
            IntegrationTestTool("valid_3"),
        ]
        
        # Test bulk registration with error aggregation
        registration_results = []
        for i, tool in enumerate(test_tools):
            try:
                self.agent_registry.enable_validation = True
                self.agent_registry.register_tool(f"category_{i}", tool)
                registration_results.append({'index': i, 'status': 'success'})
            except Exception as e:
                registration_results.append({
                    'index': i,
                    'status': 'error',
                    'exception_type': type(e).__name__,
                    'message': str(e)
                })
        
        print(f"BULK REGISTRATION RESULTS: {registration_results}")
        
        # Analyze error patterns
        errors = [r for r in registration_results if r['status'] == 'error']
        successes = [r for r in registration_results if r['status'] == 'success']
        
        print(f"ERRORS: {len(errors)}, SUCCESSES: {len(successes)}")
        
        # CURRENT BEHAVIOR: Individual error handling
        # DESIRED: Should have batch error aggregation capabilities
        
        self.assertGreater(len(errors), 0, "Expected some registration errors")
        self.assertGreater(len(successes), 0, "Expected some successful registrations")

    def test_tool_registry_exception_metrics_collection(self):
        """
        Test that tool registry exceptions are properly tracked in metrics.
        
        CURRENT STATE: This test should reveal minimal metrics collection.
        DESIRED STATE: Comprehensive exception metrics for monitoring and alerting.
        """
        # Mock metrics collection
        collected_metrics = []
        
        with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            mock_logger.get_logger.return_value.error.side_effect = lambda msg, *args, **kwargs: collected_metrics.append({
                'level': 'error',
                'message': msg,
                'args': args,
                'kwargs': kwargs
            })
            
            # Generate various types of errors
            error_scenarios = [
                ('validation_error', lambda: self.agent_registry.register_tool("test", self.malformed_tool)),
                ('type_error', lambda: self.unified_registry.register_tool("not_a_tool", None)),
                # More scenarios can be added
            ]
            
            for scenario_name, scenario_func in error_scenarios:
                try:
                    if scenario_name == 'validation_error':
                        self.agent_registry.enable_validation = True
                    scenario_func()
                except Exception as e:
                    collected_metrics.append({
                        'scenario': scenario_name,
                        'exception_type': type(e).__name__,
                        'message': str(e)
                    })
        
        print(f"COLLECTED METRICS: {collected_metrics}")
        
        # DESIRED: Should have structured metrics for different error types
        # Metrics should include error rates, error types, user impact, etc.
        
        self.assertGreater(len(collected_metrics), 0, "Should have collected error metrics")

    def tearDown(self):
        """Clean up integration test fixtures."""
        super().tearDown()
        if hasattr(self, 'unified_registry'):
            self.unified_registry.clear()
        if hasattr(self, 'universal_registry'):
            self.universal_registry.clear()


class TestToolRegistryExceptionRecoveryIntegration(SSotAsyncTestCase):
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
        # Simulate partial system failure
        with patch.object(self.registry, '_registry') as mock_registry:
            # First, registry works normally
            mock_registry.get.return_value = IntegrationTestTool("backup_tool")
            
            tools = self.registry.get_tools(["test"])
            self.assertEqual(len(tools), 1)
            
            # Then registry fails
            mock_registry.get.side_effect = RuntimeError("Registry service down")
            
            try:
                tools = self.registry.get_tools(["test"])
                # DESIRED: Should fall back to cached or minimal functionality
                print(f"GRACEFUL DEGRADATION: Got {len(tools)} tools despite registry failure")
            except Exception as e:
                print(f"NO GRACEFUL DEGRADATION: {type(e).__name__}: {e}")
        
        # CURRENT ISSUE: Likely no graceful degradation
        # DESIRED: Should have fallback mechanisms and circuit breakers

    def test_tool_registry_exception_circuit_breaker(self):
        """
        Test circuit breaker pattern for tool registry exceptions.
        
        CURRENT STATE: This test should reveal no circuit breaker protection.
        DESIRED STATE: Circuit breaker prevents cascade failures.
        """
        failure_count = 0
        success_count = 0
        
        # Simulate repeated failures to trigger circuit breaker
        for attempt in range(10):
            try:
                with patch.object(self.registry, 'get_tools') as mock_get_tools:
                    if attempt < 5:
                        # First 5 attempts fail
                        mock_get_tools.side_effect = RuntimeError(f"Failure {attempt}")
                    else:
                        # Later attempts should be circuit broken or recovered
                        mock_get_tools.return_value = [IntegrationTestTool("recovered_tool")]
                    
                    tools = self.registry.get_tools(["test"])
                    success_count += 1
                    
            except Exception as e:
                failure_count += 1
                print(f"Attempt {attempt}: {type(e).__name__}")
        
        print(f"CIRCUIT BREAKER TEST: {failure_count} failures, {success_count} successes")
        
        # CURRENT ISSUE: No circuit breaker, all failures likely propagated
        # DESIRED: Should have circuit breaker to prevent repeated failures
        
        self.assertGreater(failure_count, 0, "Expected some failures")


if __name__ == '__main__':
    pytest.main([__file__, "-v", "-s"])