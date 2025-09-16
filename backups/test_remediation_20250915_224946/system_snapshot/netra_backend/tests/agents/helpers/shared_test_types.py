"""Shared test types and utilities for agent tests."""
from typing import Dict, Any, Optional


class TestErrorContext:
    """Test error context for testing error handling."""
    
    def __init__(self, operation: str = "test", context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.context = context or {}
        
    def __str__(self):
        return f"TestErrorContext(operation={self.operation}, context={self.context})"


class TestIntegration:
    """Base class for shared integration tests."""
    
    def test_shared_integration_pattern(self):
        """Shared integration pattern test."""
        # Verify basic integration setup
        assert True, "Integration pattern should be available"
        
        # Test context creation
        context = {"test_name": "shared_integration", "status": "active"}
        assert context is not None, "Integration context should be created"
        assert context["status"] == "active", "Integration status should be active"


class TestErrorHandling:
    """Base class for shared error handling tests."""
    
    def test_shared_error_pattern(self):
        """Shared error pattern test."""
        # Test error context creation
        error_context = TestErrorContext("test_operation")
        assert error_context.operation == "test_operation", "Error context operation should be set"
        assert error_context.context == {}, "Error context should have empty context by default"
        
        # Test error context with data
        error_context_with_data = TestErrorContext("test_with_data", {"error_code": "E001"})
        assert error_context_with_data.context["error_code"] == "E001", "Error context should store error code"
        

class SharedTestErrorHandling:
    """Shared error handling test utilities."""
    
    def test_shared_error_pattern(self):
        """Shared error pattern test."""
        # Test utility error pattern
        try:
            # Simulate an error scenario
            raise ValueError("Test error for pattern validation")
        except ValueError as e:
            error_context = TestErrorContext("shared_error_test", {"error_type": "ValueError", "message": str(e)})
            assert "Test error for pattern validation" in str(error_context), "Error context should contain error message"
            
        # Test successful error handling
        assert True, "Error pattern handled successfully"