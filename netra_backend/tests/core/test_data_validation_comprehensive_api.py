"""Api Tests - Split from test_data_validation_comprehensive.py"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field, ValidationError

from netra_backend.app.schemas.registry import WebSocketMessageType

from netra_backend.app.schemas.shared_types import ApiResponse
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError
from netra_backend.app.websocket_core.utils import validate_message_structure as MessageValidator

def test_api_response_field_completeness():
    """Test ApiResponse includes all required fields."""
    response = ApiResponse(success=True, data={"result": "test"})
    
    assert response.success is True
    assert response.data == {"result": "test"}
    assert response.errors == []
    assert response.metadata == {}
