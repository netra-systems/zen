"""Core_1 Tests - Split from test_data_validation_comprehensive.py"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.schemas.registry import WebSocketMessageType
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError

# Add project root to path
from netra_backend.app.websocket.validation import MessageValidator

# Add project root to path

def sample_valid_data():
    """Sample valid data for testing."""
    return {
        "required_field": "test_value",
        "numeric_field": 42,
        "email_field": "test@example.com"
    }

def sample_valid_data():
    """Sample valid data for testing."""
    return {
        "required_field": "test_value",
        "numeric_field": 42,
        "email_field": "test@example.com"
    }

def message_validator():
    """Create MessageValidator instance."""
    return MessageValidator(max_message_size=1024, max_text_length=100)

def message_validator():
    """Create MessageValidator instance."""
    return MessageValidator(max_message_size=1024, max_text_length=100)

def test_required_fields_presence(sample_valid_data):
    """Test required fields validation."""
    # Valid case
    model = ValidationTestModel(**sample_valid_data)
    assert model.required_field == "test_value"
    
    # Missing required field
    invalid_data = sample_valid_data.copy()
    del invalid_data["required_field"]

def test_type_correctness_validation(sample_valid_data):
    """Test type validation for all fields."""
    # Invalid string for numeric field
    invalid_data = sample_valid_data.copy()
    invalid_data["numeric_field"] = "not_a_number"
    
    with pytest.raises(ValidationError):
        ValidationTestModel(**invalid_data)

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

def test_injection_attack_prevention(message_validator, injection_payload):
    """Test prevention of injection attacks."""
    malicious_message = {
        "type": "chat_message",
        "payload": {"text": injection_payload}
    }
    
    result = message_validator.validate_message(malicious_message)
    assert isinstance(result, WebSocketValidationError)
    assert result.error_type == "security_error"

def test_processing_result_structure_compliance():
    """Test ProcessingResult follows expected structure."""
    result = ProcessingResult(status="success", data={"key": "value"})
    
    assert hasattr(result, "status")
    assert hasattr(result, "data")
    assert hasattr(result, "metadata")
    assert hasattr(result, "errors")
    assert hasattr(result, "timestamp")

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
# )  # Orphaned closing parenthesis