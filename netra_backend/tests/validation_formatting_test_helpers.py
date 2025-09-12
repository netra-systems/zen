"""
Test helpers for validation and formatting utilities testing.
Provides setup, assertion, and fixture functions for validation and formatting utility tests.
"""

from typing import Any, Dict

class ValidationTestHelpers:
    """Helper functions for validation utility testing."""
    
    @staticmethod
    def create_user_schema() -> Dict[str, Any]:
        """Create user validation schema."""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "integer", "minimum": 0},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age"]
        }
    
    @staticmethod
    def create_valid_user() -> Dict[str, Any]:
        """Create valid user data."""
        return {"name": "John", "age": 30, "email": "john@example.com"}
    
    @staticmethod
    def create_invalid_user() -> Dict[str, Any]:
        """Create invalid user data."""
        return {"name": "John"}

class FormattingTestHelpers:
    """Helper functions for formatting utility testing."""
    
    @staticmethod
    def assert_number_formatting(formatted: str, expected: str):
        """Assert number formatting matches expected."""
        assert formatted == expected
    
    @staticmethod
    def assert_currency_formatting(formatted: str, currency: str):
        """Assert currency formatting includes symbol."""
        symbols = {"USD": "$", "EUR": "[U+20AC]"}
        assert symbols[currency] in formatted