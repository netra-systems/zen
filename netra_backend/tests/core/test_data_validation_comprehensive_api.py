"""Api Tests - Split from test_data_validation_comprehensive.py"""

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

# Add project root to path
from netra_backend.app.schemas.shared_types import ApiResponse
from netra_backend.app.schemas.websocket_message_types import WebSocketValidationError
from netra_backend.app.websocket.validation import MessageValidator

# Add project root to path

def test_api_response_field_completeness():
    """Test ApiResponse includes all required fields."""
    response = ApiResponse(success=True, data={"result": "test"})
    
    assert response.success is True
    assert response.data == {"result": "test"}
    assert response.errors == []
    assert response.metadata == {}
