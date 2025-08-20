"""Fixtures Tests - Split from test_data_validation_comprehensive.py"""

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

def sample_valid_data():
    """Sample valid data for testing."""
    return {
        "required_field": "test_value",
        "numeric_field": 42,
        "email_field": "test@example.com"
    }

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
