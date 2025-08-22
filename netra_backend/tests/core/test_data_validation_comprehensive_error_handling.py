"""Error_Handling Tests - Split from test_data_validation_comprehensive.py"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

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

def test_required_fields_missing_raises_error(sample_valid_data):
    """Test missing required field raises ValidationError."""
    invalid_data = sample_valid_data.copy()
    del invalid_data["required_field"]
    
    with pytest.raises(ValidationError) as exc_info:
        ValidationTestModel(**invalid_data)
    assert "required_field" in str(exc_info.value)

def test_error_context_data_consistency():
    """Test ErrorContext maintains data consistency."""
    context = ErrorContext(trace_id="123", operation="test_op")
    
    assert context.trace_id == "123"
    assert context.operation == "test_op"
    assert isinstance(context.timestamp, datetime)
# )  # Orphaned closing parenthesis