"""Api Tests - Split from test_data_validation_comprehensive.py"""

import pytest
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from pydantic import ValidationError, BaseModel, Field
from app.schemas.shared_types import ApiResponse
from app.websocket.validation import MessageValidator
from app.schemas.websocket_message_types import WebSocketValidationError
from app.schemas.registry import WebSocketMessageType

def test_api_response_field_completeness():
    """Test ApiResponse includes all required fields."""
    response = ApiResponse(success=True, data={"result": "test"})
    
    assert response.success is True
    assert response.data == {"result": "test"}
    assert response.errors == []
    assert response.metadata == {}
