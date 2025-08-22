"""Agent Tests - Email validation tests for agent data processing"""

# Add project root to path
import sys
from pathlib import Path

from tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, EmailStr, Field, ValidationError

from app.schemas.registry import WebSocketMessageType
from app.schemas.websocket_message_types import WebSocketValidationError

# Add project root to path
from app.websocket.validation import MessageValidator

# Add project root to path


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