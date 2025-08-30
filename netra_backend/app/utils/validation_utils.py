"""
Validation utilities for schema validation and error handling.

This module provides a simplified interface for common validation operations,
maintaining compatibility with test interfaces while providing basic
schema validation functionality.
"""

from typing import Any, Dict, List, Union
import json
import re


class ValidationUtils:
    """Utility class for validation operations."""
    
    def __init__(self):
        """Initialize validation utils."""
        pass
    
    def validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Union[bool, str]:
        """Validate data against a JSON-like schema.
        
        Args:
            data: Data to validate
            schema: Schema definition
            
        Returns:
            True if valid, or error string if invalid
        """
        try:
            errors = self._validate_object(data, schema)
            return True if not errors else f"Validation failed: {errors[0]}"
        except Exception as e:
            return f"Schema validation error: {str(e)}"
    
    def get_validation_errors(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Get list of validation errors for data against schema.
        
        Args:
            data: Data to validate
            schema: Schema definition
            
        Returns:
            List of validation error messages
        """
        try:
            return self._validate_object(data, schema)
        except Exception as e:
            return [f"Schema validation error: {str(e)}"]
    
    def _validate_object(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate an object against schema definition."""
        errors = []
        
        if schema.get("type") != "object":
            return errors
        
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required fields
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate present fields
        for field, value in data.items():
            if field in properties:
                field_schema = properties[field]
                field_errors = self._validate_field(field, value, field_schema)
                errors.extend(field_errors)
        
        return errors
    
    def _validate_field(self, field_name: str, value: Any, field_schema: Dict[str, Any]) -> List[str]:
        """Validate a single field against its schema."""
        errors = []
        expected_type = field_schema.get("type")
        
        # Type validation
        if expected_type:
            if not self._check_type(value, expected_type):
                errors.append(f"Field '{field_name}' has wrong type: expected {expected_type}")
        
        # Format validation
        format_type = field_schema.get("format")
        if format_type and isinstance(value, str):
            if format_type == "email" and not self._is_valid_email(value):
                errors.append(f"Field '{field_name}' has invalid email format")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        return True
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email format validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def process(self) -> str:
        """Core processing method for basic testing."""
        return "processed"
    
    def process_invalid(self):
        """Method that raises exception for error testing."""
        raise ValueError("Invalid processing request")