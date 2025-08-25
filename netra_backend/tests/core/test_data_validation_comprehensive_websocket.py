"""Websocket Tests - Split from test_data_validation_comprehensive.py"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.schemas.registry import WebSocketMessageType
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError

from netra_backend.app.websocket_core.utils import validate_message_structure as MessageValidator

@pytest.fixture
def message_validator():
    """Create MessageValidator instance."""
    return MessageValidator

def test_websocket_message_type_validation(message_validator):
    """Test WebSocket message type validation."""
    # Valid message type
    valid_message = {"type": "chat_message", "payload": {"text": "hello"}}
    result = message_validator(valid_message)
    assert result is True
    
    # Invalid message type (missing type field)
    invalid_message = {"payload": {}}
    result = message_validator(invalid_message)
    assert result is False