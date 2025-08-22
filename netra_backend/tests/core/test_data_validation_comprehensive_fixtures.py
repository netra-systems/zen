"""Fixtures Tests - Split from test_data_validation_comprehensive.py"""

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