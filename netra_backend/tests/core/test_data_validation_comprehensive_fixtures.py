"""Fixtures Tests - Split from test_data_validation_comprehensive.py"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.schemas.registry import WebSocketMessageType
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError

from netra_backend.app.websocket_core.utils import validate_message_structure as MessageValidator

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
# )  # Orphaned closing parenthesis