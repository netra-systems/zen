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
        pass


class TestErrorHandling:
    """Base class for shared error handling tests."""
    
    def test_shared_error_pattern(self):
        """Shared error pattern test."""
        pass
        

class SharedTestErrorHandling:
    """Shared error handling test utilities."""
    
    def test_shared_error_pattern(self):
        """Shared error pattern test."""
        pass