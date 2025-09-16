"""
Unit Test for Validation Utilities Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Data Integrity and API Reliability
- Value Impact: Ensures valid data processing for agent inputs and API responses
- Strategic Impact: Prevents data corruption that could disrupt Golden Path user workflows

CRITICAL: NO MOCKS except for external dependencies. Tests use real business logic.
Tests validation functions that ensure data quality in Golden Path interactions.
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.utils.validation_utils import ValidationUtils


class ValidationUtilsTests(SSotBaseTestCase):
    """Test suite for ValidationUtils following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.validation_utils = ValidationUtils()
        self.record_metric("test_category", "data_validation")
    
    def test_schema_validation_success(self):
        """
        Test successful schema validation for valid data.
        
        BVJ: Ensures agent input data meets required format for reliable processing
        """
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "email"]
        }
        
        valid_data = {
            "name": "Test User",
            "age": 30,
            "email": "test@example.com"
        }
        
        result = self.validation_utils.validate_schema(valid_data, schema)
        assert result is True
        self.record_metric("schema_validation_success", "passed")
    
    def test_schema_validation_missing_required_field(self):
        """
        Test schema validation catches missing required fields.
        
        BVJ: Prevents incomplete agent requests that would cause Golden Path failures
        """
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "email"]
        }
        
        invalid_data = {
            "name": "Test User"
            # Missing required email field
        }
        
        result = self.validation_utils.validate_schema(invalid_data, schema)
        assert isinstance(result, str)
        assert "Missing required field: email" in result
        self.record_metric("required_field_validation", "passed")
    
    def test_schema_validation_wrong_type(self):
        """
        Test schema validation catches type mismatches.
        
        BVJ: Ensures agent data types match expected formats for proper processing
        """
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
                "active": {"type": "boolean"}
            }
        }
        
        invalid_data = {
            "age": "thirty",  # Should be integer
            "active": "yes"   # Should be boolean
        }
        
        errors = self.validation_utils.get_validation_errors(invalid_data, schema)
        
        assert len(errors) >= 2
        assert any("age" in error and "wrong type" in error for error in errors)
        assert any("active" in error and "wrong type" in error for error in errors)
        self.record_metric("type_validation_accuracy", "passed")
    
    def test_email_format_validation(self):
        """
        Test email format validation within schema.
        
        BVJ: Ensures valid user emails for Golden Path authentication and communication
        """
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"}
            }
        }
        
        # Valid email
        valid_data = {"email": "user@example.com"}
        result = self.validation_utils.validate_schema(valid_data, schema)
        assert result is True
        
        # Invalid email
        invalid_data = {"email": "not-an-email"}
        errors = self.validation_utils.get_validation_errors(invalid_data, schema)
        assert any("invalid email format" in error for error in errors)
        
        self.record_metric("email_format_validation", "passed")
    
    def test_process_method_basic_functionality(self):
        """
        Test basic processing method for core functionality.
        
        BVJ: Validates core processing interface used throughout Golden Path
        """
        result = self.validation_utils.process()
        assert result == "processed"
        self.record_metric("basic_processing", "passed")
    
    def test_process_invalid_error_handling(self):
        """
        Test error handling in processing methods.
        
        BVJ: Ensures graceful error handling that doesn't crash Golden Path workflows
        """
        with self.expect_exception(ValueError, "Invalid processing request"):
            self.validation_utils.process_invalid()
        
        self.record_metric("error_handling_validation", "passed")