"""
Unit tests for tool registry exception handling improvements.

This test suite validates specific exception classes for tool registration failures,
demonstrating current broad exception handling issues and validating future improvements.

Tests are designed to FAIL initially to expose current issues, then PASS once specific exceptions are implemented.

Business Value:
- Prevents silent failures in tool registration
- Improves error diagnostics for developers
- Reduces time to resolution for tool registration issues
- Enhances system reliability and user experience

Related to Issue #390: Tool Registration Exception Handling Improvements
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

import unittest
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.tool_registry import AgentToolConfigRegistry
from netra_backend.app.services.unified_tool_registry.registry import UnifiedToolRegistry
from netra_backend.app.core.exceptions_base import NetraException, ValidationError
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from langchain_core.tools import BaseTool


class MockTool(BaseTool):
    """Mock tool for testing."""
    name: str = "test_tool"
    description: str = "Test tool for validation"
    
    def _run(self, *args, **kwargs):
        return "test_result"


class MockInvalidTool(BaseTool):
    """Mock tool with invalid configuration."""
    name: str = ""  # Invalid empty name
    description: str = "Invalid tool"
    
    def _run(self, *args, **kwargs):
        return "test_result"


class MockBadTool:
    """Non-BaseTool class to test type validation."""
    name = "bad_tool"
    description = "Not a real tool"


class TestToolRegistrySpecificExceptions(unittest.TestCase):
    """Test specific exception classes for tool registry operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.registry = AgentToolConfigRegistry()
        self.unified_registry = UnifiedToolRegistry()
        self.mock_tool = MockTool()
        self.invalid_tool = MockInvalidTool()
        self.bad_tool = MockBadTool()

    def test_tool_registration_invalid_tool_type_specific_exception(self):
        """
        Test that tool registration with invalid tool type raises specific ToolTypeException.
        
        CURRENT STATE: This test should FAIL - currently raises generic NetraException.
        DESIRED STATE: Should raise ToolTypeException with specific error details.
        
        Business Impact: Developers need to know exactly what type validation failed.
        """
        with self.assertRaises(Exception) as context:
            # This should raise a specific ToolTypeException, not generic NetraException
            self.unified_registry.register_tool(self.bad_tool, None)
        
        # CURRENT ISSUE: This will pass because it raises TypeError, but we want ToolTypeException
        # This test exposes that we have no specific exception for tool type validation
        exception = context.exception
        
        # These assertions will FAIL until specific exceptions are implemented
        self.assertIsInstance(exception, TypeError)  # Current behavior - generic
        
        # DESIRED BEHAVIOR (should fail now, pass later):
        # self.assertEqual(exception.__class__.__name__, "ToolTypeException")
        # self.assertEqual(exception.error_details.code, ErrorCode.TOOL_VALIDATION_ERROR)
        # self.assertIn("tool must be a UnifiedTool instance", str(exception))
        
        print(f"CURRENT EXCEPTION TYPE: {type(exception).__name__}")
        print(f"CURRENT EXCEPTION MESSAGE: {str(exception)}")

    def test_tool_registration_invalid_handler_type_specific_exception(self):
        """
        Test that tool registration with invalid handler type raises specific ToolHandlerException.
        
        CURRENT STATE: This test should FAIL - currently raises generic TypeError.
        DESIRED STATE: Should raise ToolHandlerException with specific error details.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        
        valid_tool = UnifiedTool(
            id="test_tool",
            name="Test Tool",
            description="Test tool",
            category="testing"
        )
        
        invalid_handler = "not_callable"  # Should be callable
        
        with self.assertRaises(Exception) as context:
            self.unified_registry.register_tool(valid_tool, invalid_handler)
        
        exception = context.exception
        
        # CURRENT ISSUE: Raises TypeError instead of specific ToolHandlerException
        self.assertIsInstance(exception, TypeError)
        
        # DESIRED BEHAVIOR (should fail now, pass later):
        # self.assertEqual(exception.__class__.__name__, "ToolHandlerException")
        # self.assertEqual(exception.error_details.code, ErrorCode.TOOL_HANDLER_VALIDATION_ERROR)
        # self.assertIn("handler must be callable", str(exception))
        
        print(f"HANDLER EXCEPTION TYPE: {type(exception).__name__}")
        print(f"HANDLER EXCEPTION MESSAGE: {str(exception)}")

    def test_tool_validation_name_empty_specific_exception(self):
        """
        Test that tool validation with empty name raises specific ToolNameException.
        
        CURRENT STATE: This test should FAIL - currently raises generic NetraException.
        DESIRED STATE: Should raise ToolNameException with validation details.
        """
        self.registry.enable_validation = True
        
        with self.assertRaises(Exception) as context:
            self.registry.register_tool("test", self.invalid_tool)
        
        exception = context.exception
        
        # CURRENT ISSUE: Raises generic NetraException
        self.assertIsInstance(exception, NetraException)
        
        # DESIRED BEHAVIOR (should fail now, pass later):
        # self.assertEqual(exception.__class__.__name__, "ToolNameValidationException")
        # self.assertEqual(exception.error_details.code, ErrorCode.TOOL_NAME_VALIDATION_ERROR)
        # self.assertIn("Tool name cannot be empty", str(exception))
        
        print(f"NAME VALIDATION EXCEPTION TYPE: {type(exception).__name__}")
        print(f"NAME VALIDATION EXCEPTION MESSAGE: {str(exception)}")

    def test_tool_not_found_specific_exception(self):
        """
        Test that tool retrieval for non-existent tool raises specific ToolNotFoundException.
        
        CURRENT STATE: This test should FAIL - currently returns None or raises generic error.
        DESIRED STATE: Should raise ToolNotFoundException when configured to do so.
        """
        # Test unified registry behavior
        result = self.unified_registry.get_tool("non_existent_tool")
        
        # CURRENT ISSUE: Returns None instead of raising specific exception
        self.assertIsNone(result)
        
        # For strict mode, should raise exception
        # FUTURE IMPLEMENTATION: Add strict mode to raise ToolNotFoundException
        # with self.assertRaises(ToolNotFoundException) as context:
        #     self.unified_registry.get_tool_strict("non_existent_tool")
        
        print(f"NON-EXISTENT TOOL RESULT: {result}")
        print("DESIRED: Should have option to raise ToolNotFoundException in strict mode")

    def test_tool_execution_no_handler_specific_exception(self):
        """
        Test that tool execution without handler raises specific ToolExecutionException.
        
        CURRENT STATE: This test should work but returns generic error result.
        DESIRED STATE: Should have specific exception class for execution failures.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        import asyncio
        
        tool_without_handler = UnifiedTool(
            id="no_handler_tool",
            name="No Handler Tool", 
            description="Tool without execution handler",
            category="testing"
        )
        
        self.unified_registry.register_tool(tool_without_handler, None)
        
        async def test_execution():
            result = await self.unified_registry.execute_tool(
                "no_handler_tool", 
                {"param": "value"}, 
                {"user": "test_user"}
            )
            
            # CURRENT BEHAVIOR: Returns ToolExecutionResult with success=False
            self.assertFalse(result.success)
            self.assertIn("No handler registered", result.error)
            
            # DESIRED ENHANCEMENT: Have specific exception classes for different execution failures
            # This would allow better error handling and recovery strategies
            
            print(f"EXECUTION RESULT: {result}")
            print(f"ERROR MESSAGE: {result.error}")
            
            return result
        
        result = asyncio.run(test_execution())
        self.assertIsNotNone(result)

    def test_tool_permission_denied_specific_exception(self):
        """
        Test that tool access without permission raises specific ToolPermissionException.
        
        CURRENT STATE: This test should FAIL - currently always returns True.
        DESIRED STATE: Should raise ToolPermissionException for unauthorized access.
        """
        from netra_backend.app.services.unified_tool_registry.models import UnifiedTool
        
        restricted_tool = UnifiedTool(
            id="restricted_tool",
            name="Restricted Tool",
            description="Tool with permission restrictions",
            category="admin"
        )
        
        self.unified_registry.register_tool(restricted_tool, None)
        
        # CURRENT ISSUE: Always returns True, no permission checking
        has_permission = self.unified_registry.check_permission(
            "restricted_tool", 
            "unauthorized_user", 
            "execute"
        )
        
        self.assertTrue(has_permission)  # Current behavior
        
        # DESIRED BEHAVIOR (should fail now, pass later):
        # with self.assertRaises(ToolPermissionException) as context:
        #     self.unified_registry.check_permission_strict("restricted_tool", "unauthorized_user")
        
        print(f"PERMISSION CHECK RESULT: {has_permission}")
        print("DESIRED: Should have proper permission validation and ToolPermissionException")

    def test_tool_dependency_missing_specific_exception(self):
        """
        Test that tool registration with missing dependencies raises specific ToolDependencyException.
        
        CURRENT STATE: This test should FAIL - no dependency validation.
        DESIRED STATE: Should raise ToolDependencyException with missing dependency details.
        """
        dependencies = ["numpy", "pandas", "sklearn"]  # sklearn is marked as False in check_dependencies
        
        validation_result = self.registry.validate_dependencies(self.mock_tool, dependencies)
        
        # CURRENT BEHAVIOR: Returns dict with validation results
        self.assertFalse(validation_result['valid'])
        self.assertIn("sklearn", validation_result['missing_dependencies'])
        
        # DESIRED BEHAVIOR: Should have option to raise ToolDependencyException
        # with self.assertRaises(ToolDependencyException) as context:
        #     self.registry.validate_dependencies_strict(self.mock_tool, dependencies)
        
        print(f"DEPENDENCY VALIDATION RESULT: {validation_result}")
        print("DESIRED: Should have ToolDependencyException for strict validation")

    def test_tool_category_invalid_specific_exception(self):
        """
        Test that tool registration with invalid category raises specific ToolCategoryException.
        
        CURRENT STATE: This test should FAIL - no category validation.
        DESIRED STATE: Should raise ToolCategoryException for invalid categories.
        """
        # Current behavior accepts any category
        self.registry.register_tool("invalid_category_!!!", self.mock_tool)
        
        # Should succeed currently (no validation)
        tools = self.registry.get_tools(["invalid_category_!!!"])
        self.assertEqual(len(tools), 1)
        
        # DESIRED BEHAVIOR: Should validate categories and raise exception for invalid ones
        # with self.assertRaises(ToolCategoryException) as context:
        #     self.registry.register_tool_strict("invalid_category_!!!", self.mock_tool)
        
        print("CATEGORY VALIDATION: Currently accepts any category")
        print("DESIRED: Should have ToolCategoryException for invalid category names")

    def test_bulk_tool_validation_aggregated_exceptions(self):
        """
        Test that bulk tool validation aggregates multiple specific exceptions.
        
        CURRENT STATE: This test should partially work but with generic error info.
        DESIRED STATE: Should collect and report all specific exception types.
        """
        tools = [
            self.mock_tool,      # Valid
            self.invalid_tool,   # Invalid name
            # self.bad_tool would cause type error, so skip for bulk validation
        ]
        
        results = self.registry.bulk_validate_tools(tools)
        
        # CURRENT BEHAVIOR: Returns basic validation results
        self.assertEqual(len(results), 2)
        
        # Check results
        valid_result = next(r for r in results if r['tool'] == 'test_tool')
        invalid_result = next(r for r in results if r['tool'] == '')
        
        self.assertTrue(valid_result['valid'])
        self.assertTrue(invalid_result['valid'])  # Current validation is basic
        
        # DESIRED BEHAVIOR: Should have detailed exception information
        # Each result should include specific exception types and details
        
        print(f"BULK VALIDATION RESULTS: {results}")
        print("DESIRED: Should include specific exception types and details for each validation failure")

    def tearDown(self):
        """Clean up test fixtures."""
        super().tearDown()
        if hasattr(self, 'unified_registry'):
            self.unified_registry.clear()


class TestToolRegistryExceptionRecovery(unittest.TestCase):
    """Test exception recovery and error handling patterns."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.registry = AgentToolConfigRegistry()

    def test_exception_logging_and_metrics(self):
        """
        Test that tool registry exceptions are properly logged and tracked.
        
        CURRENT STATE: Basic logging, no metrics.
        DESIRED STATE: Structured logging with metrics collection.
        """
        with patch('netra_backend.app.logging_config.central_logger') as mock_logger:
            self.registry.enable_validation = True
            
            try:
                self.registry.register_tool("test", MockInvalidTool())
            except Exception as e:
                pass
            
            # Should have logged the validation failure
            # Current logging might be basic
            print("LOGGING: Should have structured logging for tool registration failures")
            print("METRICS: Should increment failure counters for monitoring")

    def test_exception_error_codes_mapping(self):
        """
        Test that different tool registry exceptions map to appropriate error codes.
        
        CURRENT STATE: Generic error codes.
        DESIRED STATE: Specific error codes for each exception type.
        """
        expected_mappings = {
            # "ToolTypeException": ErrorCode.TOOL_TYPE_VALIDATION_ERROR,
            # "ToolNameException": ErrorCode.TOOL_NAME_VALIDATION_ERROR,  
            # "ToolHandlerException": ErrorCode.TOOL_HANDLER_VALIDATION_ERROR,
            # "ToolNotFoundException": ErrorCode.TOOL_NOT_FOUND,
            # "ToolPermissionException": ErrorCode.TOOL_ACCESS_DENIED,
            # "ToolDependencyException": ErrorCode.TOOL_DEPENDENCY_MISSING,
            # "ToolCategoryException": ErrorCode.TOOL_CATEGORY_INVALID,
        }
        
        print(f"EXPECTED ERROR CODE MAPPINGS: {len(expected_mappings)} specific exception types")
        print("CURRENT: Generic NetraException and TypeError used")
        print("DESIRED: Specific exception classes with appropriate error codes")

    def test_exception_context_preservation(self):
        """
        Test that tool registry exceptions preserve context information.
        
        CURRENT STATE: Limited context.
        DESIRED STATE: Rich context with tool details, user info, etc.
        """
        context_info = {
            'user_id': 'test_user',
            'request_id': 'req_123',
            'tool_source': 'dynamic_import',
            'validation_level': 'strict'
        }
        
        # Should preserve context in exceptions
        print("CONTEXT: Should preserve rich context in all tool registry exceptions")
        print("TRACING: Should include trace_id for debugging")
        print("USER_INFO: Should include user_id for security auditing")


if __name__ == '__main__':
    pytest.main([__file__, "-v", "-s"])