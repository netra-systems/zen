"""Websocket Tests - Split from test_data_validation_comprehensive.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pydantic import ValidationError, BaseModel, Field

# Add project root to path

from netra_backend.app.websocket.validation import MessageValidator
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError
from netra_backend.app.schemas.registry import WebSocketMessageType

# Add project root to path

def message_validator():
    """Create MessageValidator instance."""
    return MessageValidator(max_message_size=1024, max_text_length=100)

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
# )  # Orphaned closing parenthesis