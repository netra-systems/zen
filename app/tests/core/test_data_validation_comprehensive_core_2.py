"""Core_2 Tests - Split from test_data_validation_comprehensive.py"""

import pytest
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pydantic import ValidationError, BaseModel, Field
from app.schemas.shared_types import (
from app.websocket.validation import MessageValidator
from app.schemas.websocket_message_types import WebSocketValidationError
from app.schemas.registry import WebSocketMessageType

def message_validator():
    """Create MessageValidator instance."""
    return MessageValidator(max_message_size=1024, max_text_length=100)

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
