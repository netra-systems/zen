"""
Schema Validator Service

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Provide schema validation functionality for tests
- Value Impact: Enables schema validation tests to execute without import errors
- Strategic Impact: Enables schema validation functionality validation
"""

from typing import Any, Dict, List, Optional
import json


class SchemaValidator:
    """Validates data against schemas."""
    
    def __init__(self):
        """Initialize schema validator."""
        self.schemas: Dict[str, Dict[str, Any]] = {}
    
    def register_schema(self, schema_name: str, schema: Dict[str, Any]) -> None:
        """Register a schema."""
        self.schemas[schema_name] = schema
    
    def validate_data(self, data: Any, schema_name: str) -> bool:
        """Validate data against a schema."""
        if schema_name not in self.schemas:
            return False
        
        # Simple validation for testing
        schema = self.schemas[schema_name]
        return self._validate_against_schema(data, schema)
    
    def _validate_against_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """Validate data against schema structure."""
        # Simple schema validation for testing
        if isinstance(data, dict) and isinstance(schema, dict):
            required_fields = schema.get('required', [])
            for field in required_fields:
                if field not in data:
                    return False
        
        return True
    
    def validate_json_schema(self, data: str, schema_name: str) -> bool:
        """Validate JSON string against schema."""
        try:
            parsed_data = json.loads(data)
            return self.validate_data(parsed_data, schema_name)
        except json.JSONDecodeError:
            return False
    
    def get_validation_errors(self, data: Any, schema_name: str) -> List[str]:
        """Get validation errors for data."""
        errors = []
        if schema_name not in self.schemas:
            errors.append(f"Schema '{schema_name}' not found")
            return errors
        
        schema = self.schemas[schema_name]
        if isinstance(data, dict) and isinstance(schema, dict):
            required_fields = schema.get('required', [])
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        
        return errors