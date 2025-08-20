"""Fixtures Tests - Split from test_message_flow_errors.py"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone
from starlette.websockets import WebSocketDisconnect
from app.tests.integration.test_unified_message_flow import MessageFlowTracker
from app.tests.test_utilities.websocket_mocks import MockWebSocket
from app.core.exceptions_websocket import WebSocketError
from app.logging_config import central_logger
from app.routes.utils.websocket_helpers import accept_websocket_connection
from app.routes.utils.websocket_helpers import receive_message_with_timeout

def error_tracker():
    """Create error flow tracker."""
    return ErrorFlowTracker()
