"""Agent Tests - Email validation tests for agent data processing"""

import pytest
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pydantic import ValidationError, BaseModel, Field, EmailStr
from netra_backend.app.websocket.validation import MessageValidator
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError
from netra_backend.app.schemas.registry import WebSocketMessageType


class EmailValidationModel(BaseModel):
    """Test model for email validation."""
    required_field: str
    numeric_field: int
    email_field: EmailStr
    

def test_format_validation_email():
    """Test email format validation."""
    invalid_emails = ["invalid", "test@", "@example.com", "test@.com"]
    
    for invalid_email in invalid_emails:
        data = {"required_field": "test", "numeric_field": 1, "email_field": invalid_email}
        with pytest.raises(ValidationError):
            EmailValidationModel(**data)


def test_valid_email_validation():
    """Test that valid emails pass validation."""
    valid_data = {
        "required_field": "test", 
        "numeric_field": 1, 
        "email_field": "test@example.com"
    }
    # This should not raise an exception
    model = EmailValidationModel(**valid_data)
    assert model.email_field == "test@example.com"