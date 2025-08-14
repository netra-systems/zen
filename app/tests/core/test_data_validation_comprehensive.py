"""Comprehensive Data Validation Test Suite.

CRITICAL: Tests ALL input validation paths, output format compliance,
schema evolution handling, data sanitization, and boundary conditions.
Essential for security, data integrity, and API contract compliance.
"""

import pytest
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pydantic import ValidationError, BaseModel, Field

from app.schemas.shared_types import (
    ProcessingResult, ErrorContext, ApiResponse, 
    EventContext, ServiceHealth, ToolExecutionContext
)
from app.websocket.validation import MessageValidator
from app.schemas.websocket_message_types import WebSocketValidationError
from app.schemas.registry import WebSocketMessageType


class ValidationTestModel(BaseModel):
    """Test model for validation testing."""
    required_field: str = Field(..., min_length=1, max_length=100)
    optional_field: Optional[str] = Field(default=None, max_length=50)
    numeric_field: int = Field(..., ge=0, le=1000)
    email_field: Optional[str] = Field(default=None, regex=r'^[^@]+@[^@]+\.[^@]+$')


@pytest.fixture
def message_validator():
    """Create MessageValidator instance."""
    return MessageValidator(max_message_size=1024, max_text_length=100)


@pytest.fixture
def sample_valid_data():
    """Sample valid data for testing."""
    return {
        "required_field": "test_value",
        "numeric_field": 42,
        "email_field": "test@example.com"
    }


@pytest.fixture
def injection_test_data():
    """Data with potential injection attacks."""
    return [
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "onclick='alert(1)'",
        "<iframe src='evil.com'></iframe>",
        "'; DROP TABLE users; --",
        "{{7*7}}"  # Template injection
    ]


# Input Validation Tests

def test_required_fields_presence(sample_valid_data):
    """Test required fields validation."""
    # Valid case
    model = ValidationTestModel(**sample_valid_data)
    assert model.required_field == "test_value"
    
    # Missing required field
    invalid_data = sample_valid_data.copy()
    del invalid_data["required_field"]


def test_required_fields_missing_raises_error(sample_valid_data):
    """Test missing required field raises ValidationError."""
    invalid_data = sample_valid_data.copy()
    del invalid_data["required_field"]
    
    with pytest.raises(ValidationError) as exc_info:
        ValidationTestModel(**invalid_data)
    assert "required_field" in str(exc_info.value)


def test_type_correctness_validation(sample_valid_data):
    """Test type validation for all fields."""
    # Invalid string for numeric field
    invalid_data = sample_valid_data.copy()
    invalid_data["numeric_field"] = "not_a_number"
    
    with pytest.raises(ValidationError):
        ValidationTestModel(**invalid_data)


def test_format_validation_email():
    """Test email format validation."""
    invalid_emails = ["invalid", "test@", "@example.com", "test@.com"]
    
    for invalid_email in invalid_emails:
        data = {"required_field": "test", "numeric_field": 1, "email_field": invalid_email}
        with pytest.raises(ValidationError):
            ValidationTestModel(**data)


def test_range_boundary_validation():
    """Test numeric range boundary validation."""
    # Below minimum
    with pytest.raises(ValidationError):
        ValidationTestModel(required_field="test", numeric_field=-1)
    
    # Above maximum  
    with pytest.raises(ValidationError):
        ValidationTestModel(required_field="test", numeric_field=1001)


def test_string_length_boundaries():
    """Test string length boundary validation."""
    # Empty required field
    with pytest.raises(ValidationError):
        ValidationTestModel(required_field="", numeric_field=1)
    
    # Too long required field
    long_string = "x" * 101


def test_long_string_validation():
    """Test validation of overly long strings."""
    long_string = "x" * 101
    
    with pytest.raises(ValidationError):
        ValidationTestModel(required_field=long_string, numeric_field=1)


@pytest.mark.parametrize("injection_payload", [
    "<script>alert('xss')</script>",
    "javascript:alert('xss')", 
    "onclick='alert(1)'",
    "<iframe src='evil.com'></iframe>"
])
def test_injection_attack_prevention(message_validator, injection_payload):
    """Test prevention of injection attacks."""
    malicious_message = {
        "type": "chat_message",
        "payload": {"text": injection_payload}
    }
    
    result = message_validator.validate_message(malicious_message)
    assert isinstance(result, WebSocketValidationError)
    assert result.error_type == "security_error"


# Output Validation Tests

def test_processing_result_structure_compliance():
    """Test ProcessingResult follows expected structure."""
    result = ProcessingResult(status="success", data={"key": "value"})
    
    assert hasattr(result, "status")
    assert hasattr(result, "data")
    assert hasattr(result, "metadata")
    assert hasattr(result, "errors")
    assert hasattr(result, "timestamp")


def test_api_response_field_completeness():
    """Test ApiResponse includes all required fields."""
    response = ApiResponse(success=True, data={"result": "test"})
    
    assert response.success is True
    assert response.data == {"result": "test"}
    assert response.errors == []
    assert response.metadata == {}


def test_error_context_data_consistency():
    """Test ErrorContext maintains data consistency."""
    context = ErrorContext(trace_id="123", operation="test_op")
    
    assert context.trace_id == "123"
    assert context.operation == "test_op"
    assert isinstance(context.timestamp, datetime)


def test_service_health_format_standardization():
    """Test ServiceHealth follows standard format."""
    health = ServiceHealth(service_name="test_service", status="healthy")
    
    assert health.service_name == "test_service"
    assert health.status == "healthy"
    assert isinstance(health.timestamp, datetime)


def test_output_size_limits(message_validator):
    """Test output size limit enforcement."""
    large_payload = "x" * 2000  # Exceeds max_text_length of 100
    message = {"type": "chat_message", "payload": {"text": large_payload}}
    
    result = message_validator.validate_message(message)
    assert isinstance(result, WebSocketValidationError)


# Schema Evolution Tests

def test_backward_compatibility_optional_fields():
    """Test backward compatibility with optional fields."""
    # Old format without optional fields
    old_data = {"required_field": "test", "numeric_field": 42}
    model = ValidationTestModel(**old_data)
    
    assert model.optional_field is None
    assert model.email_field is None


def test_forward_compatibility_extra_fields():
    """Test forward compatibility ignores extra fields."""
    # Future format with extra field
    future_data = {
        "required_field": "test",
        "numeric_field": 42,
        "future_field": "ignored"
    }
    
    model = ValidationTestModel(**future_data)
    assert model.required_field == "test"


def test_schema_migration_field_renaming():
    """Test schema migration with field name changes."""
    # Simulate old field name mapping
    old_format = {"old_required": "test", "numeric_field": 42}
    
    # Map old to new format
    new_format = {
        "required_field": old_format["old_required"],
        "numeric_field": old_format["numeric_field"]
    }
    
    model = ValidationTestModel(**new_format)
    assert model.required_field == "test"


def test_deprecation_handling_graceful():
    """Test graceful handling of deprecated fields."""
    # Deprecated field should be ignored
    deprecated_data = {
        "required_field": "test",
        "numeric_field": 42,
        "deprecated_field": "ignored"
    }
    
    model = ValidationTestModel(**deprecated_data)
    assert not hasattr(model, "deprecated_field")


# Edge Cases and Boundary Conditions

def test_empty_input_handling():
    """Test handling of empty inputs."""
    with pytest.raises(ValidationError):
        ValidationTestModel(**{})


def test_null_values_handling():
    """Test handling of null/None values."""
    # None for optional field should be fine
    data = {"required_field": "test", "numeric_field": 42, "optional_field": None}
    model = ValidationTestModel(**data)
    assert model.optional_field is None


def test_unicode_character_handling():
    """Test Unicode character support."""
    unicode_data = {
        "required_field": "测试数据",  # Chinese characters
        "numeric_field": 42,
        "optional_field": "café"  # Accented characters
    }
    
    model = ValidationTestModel(**unicode_data)
    assert model.required_field == "测试数据"


def test_special_characters_validation():
    """Test validation with special characters."""
    special_chars = "!@#$%^&*()_+-=[]{}|;:'\",.<>?/"
    
    data = {"required_field": special_chars, "numeric_field": 42}
    model = ValidationTestModel(**data)
    assert model.required_field == special_chars


def test_maximum_size_input_boundaries():
    """Test maximum size input boundaries."""
    max_size_data = {
        "required_field": "x" * 100,  # Exactly max length
        "numeric_field": 1000,  # Exactly max value
        "optional_field": "y" * 50  # Exactly max length
    }
    
    model = ValidationTestModel(**max_size_data)
    assert len(model.required_field) == 100


def test_websocket_message_type_validation(message_validator):
    """Test WebSocket message type validation."""
    # Valid message type
    valid_message = {"type": "chat_message", "payload": {"text": "hello"}}
    result = message_validator.validate_message(valid_message)
    assert result is True
    
    # Invalid message type
    invalid_message = {"type": "invalid_type", "payload": {}}
    result = message_validator.validate_message(invalid_message)
    assert isinstance(result, WebSocketValidationError)


def test_message_sanitization_comprehensive(message_validator):
    """Test comprehensive message sanitization."""
    dangerous_message = {
        "type": "chat_message",
        "payload": {
            "text": "<script>alert('xss')</script>",
            "user_input": "safe text"
        }
    }
    
    sanitized = message_validator.sanitize_message(dangerous_message)
    assert "<script>" not in sanitized["payload"]["text"]
    assert "&lt;script&gt;" in sanitized["payload"]["text"]


def test_nested_data_structure_validation():
    """Test validation of nested data structures."""
    nested_data = {
        "event_id": "test123",
        "event_type": "validation_test",
        "source": "test_suite",
        "data": {
            "nested_field": "value",
            "deep_nesting": {"level2": {"level3": "deep_value"}}
        }
    }
    
    context = EventContext(**nested_data)
    assert context.data["nested_field"] == "value"