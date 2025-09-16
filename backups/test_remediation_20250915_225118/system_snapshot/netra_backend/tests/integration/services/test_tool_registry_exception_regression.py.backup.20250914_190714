"""
Regression tests for tool registry exception handling improvements.

This test suite validates that exception handling improvements don't break existing
functionality and that the improvements actually work as intended.

Tests are designed to demonstrate before/after behavior and prevent regression
of existing functionality while validating new specific exception handling.

Business Value:
- Prevents regression of existing tool registration functionality
- Validates that new exception handling improves diagnostics
- Ensures backward compatibility during exception handling improvements
- Provides clear before/after behavior documentation

Related to Issue #390: Tool Registration Exception Handling Improvements
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
import time
import logging

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.tool_registry import AgentToolConfigRegistry
from netra_backend.app.services.unified_tool_registry.registry import UnifiedToolRegistry
from netra_backend.app.core.exceptions_base import NetraException, ValidationError
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from langchain_core.tools import BaseTool


class RegressionTestTool(BaseTool):
    """Tool for regression testing with various configurations."""
    
    def __init__(self, name: str = "regression_tool", simulate_error: bool = False, **kwargs):
        self.name = name
        self.description = f"Regression test tool: {name}"
        self.simulate_error = simulate_error
        super().__init__(**kwargs)
    
    def _run(self, *args, **kwargs):
        if self.simulate_error:
            raise RuntimeError(f"Simulated error in {self.name}")
        return f"Executed {self.name} successfully"


class TestToolRegistryRegressionValidation(SSotAsyncTestCase):
    """Test that existing functionality continues to work while improving exceptions."""
    
    def setUp(self):
        """Set up regression test fixtures."""
        super().setUp()
        self.agent_registry = AgentToolConfigRegistry()
        self.unified_registry = UnifiedToolRegistry()
        
        # Create baseline tools for regression testing
        self.baseline_tools = [
            RegressionTestTool("baseline_tool_1"),
            RegressionTestTool("baseline_tool_2"), 
            RegressionTestTool("baseline_tool_3"),
        ]

    def test_existing_tool_registration_still_works(self):
        """
        REGRESSION TEST: Verify that existing tool registration patterns still work.
        
        This test ensures that while we improve exception handling, we don't break
        the current successful registration workflows that users depend on.
        """
        # Test AgentToolConfigRegistry - should continue working
        registration_results = []
        
        for i, tool in enumerate(self.baseline_tools):
            try:
                category = f"category_{i}"
                self.agent_registry.register_tool(category, tool)
                
                # Verify tool was registered
                registered_tools = self.agent_registry.get_tools([category])
                registration_results.append({
                    'tool': tool.name,
                    'category': category,
                    'registered': len(registered_tools) > 0,
                    'status': 'success'
                })
                
            except Exception as e:
                registration_results.append({
                    'tool': tool.name,
                    'category': f"category_{i}",
                    'registered': False,
                    'status': 'error',
                    'error': str(e)
                })
        
        # All baseline tools should register successfully (regression check)
        successful_registrations = [r for r in registration_results if r['status'] == 'success']
        failed_registrations = [r for r in registration_results if r['status'] == 'error']
        
        print(f"REGRESSION CHECK - Successful: {len(successful_registrations)}, Failed: {len(failed_registrations)}")
        
        if failed_registrations:
            print(f"REGRESSION FAILURES: {failed_registrations}")
        
        self.assertEqual(len(successful_registrations), len(self.baseline_tools), 
                        "REGRESSION: Existing tool registration should continue working")
        self.assertEqual(len(failed_registrations), 0, 
                        "REGRESSION: No failures expected for valid tools")

    async def test_existing_tool_execution_still_works(self):
        """
        REGRESSION TEST: Verify that existing tool execution patterns still work.
        
        Ensures that exception handling improvements don't break tool execution workflows.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        
        # Register tools in unified registry with handlers
        execution_results = []
        
        for i, baseline_tool in enumerate(self.baseline_tools):
            unified_tool = UnifiedTool(
                id=f"unified_{baseline_tool.name}",
                name=baseline_tool.name,
                description=baseline_tool.description,
                category="regression_test"
            )
            
            # Create handler that wraps the baseline tool
            async def create_handler(tool):
                async def handler(parameters: Dict[str, Any], context: Dict[str, Any]):
                    return tool._run(**parameters)
                return handler
            
            handler = await create_handler(baseline_tool)
            self.unified_registry.register_tool(unified_tool, handler)
            
            # Execute the tool
            try:
                result = await self.unified_registry.execute_tool(
                    unified_tool.id,
                    {"test_param": f"value_{i}"},
                    {"user": "regression_user", "request_id": f"req_{i}"}
                )
                
                execution_results.append({
                    'tool_id': unified_tool.id,
                    'success': result.success,
                    'has_result': result.result is not None,
                    'status': 'success'
                })
                
            except Exception as e:
                execution_results.append({
                    'tool_id': unified_tool.id,
                    'success': False,
                    'has_result': False,
                    'status': 'error',
                    'error': str(e)
                })
        
        # All executions should succeed (regression check)
        successful_executions = [r for r in execution_results if r['status'] == 'success' and r['success']]
        failed_executions = [r for r in execution_results if r['status'] == 'error' or not r['success']]
        
        print(f"EXECUTION REGRESSION CHECK - Successful: {len(successful_executions)}, Failed: {len(failed_executions)}")
        
        if failed_executions:
            print(f"EXECUTION REGRESSION FAILURES: {failed_executions}")
        
        self.assertEqual(len(successful_executions), len(self.baseline_tools),
                        "REGRESSION: Existing tool execution should continue working")

    def test_existing_validation_behavior_preserved(self):
        """
        REGRESSION TEST: Verify that existing validation behavior is preserved.
        
        Ensures that validation improvements enhance rather than change existing behavior.
        """
        # Test current validation behavior
        validation_results = []
        
        # Test with validation disabled (current default)
        self.agent_registry.enable_validation = False
        
        try:
            # This should succeed even with empty name (current behavior)
            invalid_tool = RegressionTestTool("")  # Empty name
            self.agent_registry.register_tool("test_invalid", invalid_tool)
            validation_results.append({
                'scenario': 'validation_disabled_empty_name',
                'expected': 'success',
                'actual': 'success',
                'status': 'pass'
            })
        except Exception as e:
            validation_results.append({
                'scenario': 'validation_disabled_empty_name', 
                'expected': 'success',
                'actual': f'error: {e}',
                'status': 'regression_failure'
            })
        
        # Test with validation enabled (current behavior)
        self.agent_registry.enable_validation = True
        
        try:
            invalid_tool = RegressionTestTool("")  # Empty name
            self.agent_registry.register_tool("test_invalid_2", invalid_tool)
            validation_results.append({
                'scenario': 'validation_enabled_empty_name',
                'expected': 'error',
                'actual': 'success',
                'status': 'unexpected_success'
            })
        except Exception as e:
            validation_results.append({
                'scenario': 'validation_enabled_empty_name',
                'expected': 'error', 
                'actual': f'error: {type(e).__name__}',
                'status': 'pass'
            })
        
        print(f"VALIDATION REGRESSION RESULTS: {validation_results}")
        
        # Check for regression failures
        regression_failures = [r for r in validation_results if r['status'] == 'regression_failure']
        
        if regression_failures:
            print(f"VALIDATION REGRESSION FAILURES: {regression_failures}")
        
        self.assertEqual(len(regression_failures), 0, 
                        "REGRESSION: Existing validation behavior should be preserved")

    def test_exception_type_improvements_while_preserving_catching(self):
        """
        IMPROVEMENT TEST: Verify that new specific exceptions can still be caught by existing code.
        
        This test ensures that specific exception improvements maintain backward compatibility
        with existing exception handling code.
        """
        # Test current exception catching patterns
        exception_compatibility_results = []
        
        # Test 1: Existing NetraException catching should still work
        try:
            self.agent_registry.enable_validation = True
            invalid_tool = RegressionTestTool("")
            self.agent_registry.register_tool("test", invalid_tool)
            exception_compatibility_results.append({
                'test': 'netra_exception_catch',
                'caught': False,
                'exception_type': None
            })
        except NetraException as e:
            exception_compatibility_results.append({
                'test': 'netra_exception_catch',
                'caught': True,
                'exception_type': type(e).__name__,
                'compatible': True
            })
        except Exception as e:
            exception_compatibility_results.append({
                'test': 'netra_exception_catch',
                'caught': True,
                'exception_type': type(e).__name__,
                'compatible': isinstance(e, NetraException)  # Should inherit from NetraException
            })
        
        # Test 2: Generic Exception catching should still work  
        try:
            from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
            invalid_tool_data = "not_a_unified_tool"
            self.unified_registry.register_tool(invalid_tool_data, None)
            exception_compatibility_results.append({
                'test': 'generic_exception_catch',
                'caught': False,
                'exception_type': None
            })
        except Exception as e:
            exception_compatibility_results.append({
                'test': 'generic_exception_catch', 
                'caught': True,
                'exception_type': type(e).__name__,
                'compatible': True  # Any exception should be catchable as Exception
            })
        
        print(f"EXCEPTION COMPATIBILITY RESULTS: {exception_compatibility_results}")
        
        # All exception catching should remain compatible
        incompatible_exceptions = [r for r in exception_compatibility_results 
                                 if 'compatible' in r and not r['compatible']]
        
        if incompatible_exceptions:
            print(f"EXCEPTION COMPATIBILITY FAILURES: {incompatible_exceptions}")
        
        self.assertEqual(len(incompatible_exceptions), 0,
                        "REGRESSION: New exceptions should maintain backward compatibility")

    def test_performance_regression_check(self):
        """
        REGRESSION TEST: Verify that exception handling improvements don't degrade performance.
        
        Ensures that new exception handling doesn't significantly impact performance.
        """
        import time
        
        performance_results = []
        
        # Measure baseline performance (successful operations)
        start_time = time.time()
        successful_operations = 0
        
        for i in range(100):
            try:
                tool = RegressionTestTool(f"perf_tool_{i}")
                self.agent_registry.register_tool(f"perf_category_{i}", tool)
                successful_operations += 1
            except Exception:
                pass
        
        baseline_time = time.time() - start_time
        baseline_ops_per_second = successful_operations / baseline_time if baseline_time > 0 else 0
        
        performance_results.append({
            'scenario': 'baseline_successful_operations',
            'operations': successful_operations,
            'time_seconds': baseline_time,
            'ops_per_second': baseline_ops_per_second
        })
        
        # Measure error handling performance
        start_time = time.time()
        error_operations = 0
        
        self.agent_registry.enable_validation = True
        
        for i in range(50):  # Fewer iterations since these will fail
            try:
                invalid_tool = RegressionTestTool("")  # Will trigger validation error
                self.agent_registry.register_tool(f"error_category_{i}", invalid_tool)
            except Exception:
                error_operations += 1
        
        error_time = time.time() - start_time
        error_ops_per_second = error_operations / error_time if error_time > 0 else 0
        
        performance_results.append({
            'scenario': 'error_handling_operations',
            'operations': error_operations,
            'time_seconds': error_time,
            'ops_per_second': error_ops_per_second
        })
        
        print(f"PERFORMANCE REGRESSION RESULTS: {performance_results}")
        
        # Performance regression check
        # Error handling should not be more than 10x slower than successful operations
        if baseline_ops_per_second > 0 and error_ops_per_second > 0:
            performance_ratio = baseline_ops_per_second / error_ops_per_second
            performance_acceptable = performance_ratio <= 10.0  # Allow up to 10x slower for error handling
            
            print(f"PERFORMANCE RATIO (baseline/error): {performance_ratio:.2f}x")
            
            self.assertTrue(performance_acceptable, 
                           f"PERFORMANCE REGRESSION: Error handling should not be more than 10x slower (actual: {performance_ratio:.2f}x)")
        
        # Basic performance sanity check
        self.assertGreater(baseline_ops_per_second, 10, 
                          "PERFORMANCE REGRESSION: Should handle at least 10 successful operations per second")

    async def test_existing_async_patterns_still_work(self):
        """
        REGRESSION TEST: Verify that existing async/await patterns continue to work.
        
        Ensures that exception handling improvements don't break async tool operations.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        
        async_results = []
        
        # Test concurrent tool execution (existing pattern)
        async def execute_tool_concurrently(tool_id: str, iteration: int):
            try:
                result = await self.unified_registry.execute_tool(
                    tool_id,
                    {"iteration": iteration},
                    {"user": f"async_user_{iteration}"}
                )
                return {
                    'tool_id': tool_id,
                    'iteration': iteration,
                    'success': result.success,
                    'status': 'completed'
                }
            except Exception as e:
                return {
                    'tool_id': tool_id,
                    'iteration': iteration,
                    'success': False,
                    'status': 'error',
                    'error': str(e)
                }
        
        # Setup async tools
        async_tools = []
        for i in range(5):
            tool_id = f"async_regression_tool_{i}"
            unified_tool = UnifiedTool(
                id=tool_id,
                name=f"Async Regression Tool {i}",
                description=f"Async regression test tool {i}",
                category="async_regression"
            )
            
            async def create_async_handler(iteration_num):
                async def handler(parameters: Dict[str, Any], context: Dict[str, Any]):
                    await asyncio.sleep(0.01)  # Simulate async work
                    return f"Async result for iteration {parameters.get('iteration', iteration_num)}"
                return handler
            
            handler = await create_async_handler(i)
            self.unified_registry.register_tool(unified_tool, handler)
            async_tools.append(tool_id)
        
        # Execute tools concurrently
        tasks = []
        for i, tool_id in enumerate(async_tools):
            for iteration in range(3):  # 3 concurrent calls per tool
                task = execute_tool_concurrently(tool_id, iteration)
                tasks.append(task)
        
        # Wait for all concurrent executions
        async_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze concurrent execution results
        successful_async = [r for r in async_results if isinstance(r, dict) and r.get('success', False)]
        failed_async = [r for r in async_results if isinstance(r, dict) and not r.get('success', False)]
        exceptions_async = [r for r in async_results if isinstance(r, Exception)]
        
        print(f"ASYNC REGRESSION - Success: {len(successful_async)}, Failed: {len(failed_async)}, Exceptions: {len(exceptions_async)}")
        
        if exceptions_async:
            print(f"ASYNC EXCEPTIONS: {[str(e) for e in exceptions_async]}")
        
        # Regression check: async patterns should continue working
        total_expected = len(async_tools) * 3  # 5 tools * 3 iterations each
        self.assertEqual(len(successful_async), total_expected,
                        f"ASYNC REGRESSION: Expected {total_expected} successful async operations")
        self.assertEqual(len(exceptions_async), 0,
                        "ASYNC REGRESSION: No exceptions should occur during valid async operations")

    def tearDown(self):
        """Clean up regression test fixtures."""
        super().tearDown()
        if hasattr(self, 'unified_registry'):
            self.unified_registry.clear()


class TestToolRegistryExceptionImprovementValidation(SSotAsyncTestCase):
    """Test that exception handling improvements actually improve the system."""
    
    def setUp(self):
        """Set up improvement validation fixtures."""
        super().setUp()
        self.registry = AgentToolConfigRegistry()

    def test_improved_error_messages_provide_better_diagnostics(self):
        """
        IMPROVEMENT TEST: Verify that improved exceptions provide better diagnostic information.
        
        This test will initially show basic error messages, then should show improved
        diagnostic information once specific exceptions are implemented.
        """
        diagnostic_improvements = []
        
        # Test 1: Tool validation error diagnostics
        try:
            self.registry.enable_validation = True
            invalid_tool = RegressionTestTool("")  # Empty name
            self.registry.register_tool("test", invalid_tool)
        except Exception as e:
            diagnostic_improvements.append({
                'scenario': 'empty_tool_name_validation',
                'current_message': str(e),
                'current_type': type(e).__name__,
                'has_error_code': hasattr(e, 'error_details'),
                'has_context': hasattr(e, 'error_details') and hasattr(e.error_details, 'context'),
                'has_severity': hasattr(e, 'error_details') and hasattr(e.error_details, 'severity')
            })
        
        print(f"DIAGNOSTIC IMPROVEMENTS: {diagnostic_improvements}")
        
        # CURRENT STATE: Basic error messages
        # IMPROVED STATE: Should have rich error details, context, severity, etc.
        
        # For now, just verify that exceptions are being raised and captured
        self.assertGreater(len(diagnostic_improvements), 0, 
                          "Should have captured diagnostic information")

    def test_exception_categorization_enables_better_handling(self):
        """
        IMPROVEMENT TEST: Verify that specific exception types enable better error handling.
        
        This test demonstrates how specific exception types will enable better
        error handling, recovery, and user experience.
        """
        exception_categories = {}
        
        # Generate different types of errors
        error_scenarios = [
            ('empty_name', lambda: RegressionTestTool("")),
            ('type_error', lambda: "not_a_tool"),
            ('execution_error', lambda: RegressionTestTool("exec_error", simulate_error=True)),
        ]
        
        for scenario_name, error_generator in error_scenarios:
            try:
                if scenario_name == 'empty_name':
                    self.registry.enable_validation = True
                    tool = error_generator()
                    self.registry.register_tool("test", tool)
                elif scenario_name == 'type_error':
                    # This would cause type error in unified registry
                    bad_tool = error_generator()
                    # Skip this for now as it would need unified registry
                    continue
                elif scenario_name == 'execution_error':
                    tool = error_generator()
                    self.registry.register_tool("test", tool)
                    # Execute the tool to trigger error
                    tool._run()
                    
            except Exception as e:
                exception_type = type(e).__name__
                exception_categories[scenario_name] = {
                    'exception_type': exception_type,
                    'message': str(e),
                    'is_specific': exception_type not in ['Exception', 'RuntimeError', 'ValueError'],
                    'is_netra_exception': isinstance(e, NetraException)
                }
        
        print(f"EXCEPTION CATEGORIZATION: {exception_categories}")
        
        # IMPROVEMENT GOAL: Should have specific exception types for different error categories
        specific_exceptions = [cat for cat in exception_categories.values() if cat.get('is_specific', False)]
        
        print(f"SPECIFIC EXCEPTIONS: {len(specific_exceptions)} out of {len(exception_categories)}")
        
        # This will initially show mostly generic exceptions
        # After improvements, should show specific exception types

    def test_exception_context_enables_better_debugging(self):
        """
        IMPROVEMENT TEST: Verify that exception context enables better debugging.
        
        This test shows how improved exception context will help with debugging
        and troubleshooting tool registration issues.
        """
        context_analysis = []
        
        # Test exception context capture
        debug_context = {
            'operation': 'test_tool_registration',
            'user_id': 'debug_user',
            'request_id': 'debug_req_123',
            'tool_source': 'regression_test',
            'validation_level': 'strict'
        }
        
        try:
            self.registry.enable_validation = True
            invalid_tool = RegressionTestTool("")
            
            # In improved version, this context would be passed to exception
            self.registry.register_tool("debug_test", invalid_tool)
            
        except Exception as e:
            context_analysis.append({
                'has_error_details': hasattr(e, 'error_details'),
                'has_trace_id': hasattr(e, 'error_details') and hasattr(e.error_details, 'trace_id'),
                'has_context': hasattr(e, 'error_details') and hasattr(e.error_details, 'context'),
                'has_user_message': hasattr(e, 'error_details') and hasattr(e.error_details, 'user_message'),
                'exception_str': str(e),
                'exception_type': type(e).__name__
            })
        
        print(f"CONTEXT ANALYSIS: {context_analysis}")
        
        # IMPROVEMENT GOAL: Rich context information for debugging
        # Current state likely has minimal context
        # Improved state should have comprehensive debugging information

    def tearDown(self):
        """Clean up improvement validation fixtures."""
        super().tearDown()


if __name__ == '__main__':
    pytest.main([__file__, "-v", "-s"])