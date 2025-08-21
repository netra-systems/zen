"""Websocket Tests - Split from test_data_validation_comprehensive.py"""

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