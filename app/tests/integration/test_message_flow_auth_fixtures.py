"""Fixtures Tests - Split from test_message_flow_auth.py"""

import asyncio
import json
import jwt
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone, timedelta
from tests.unified.jwt_token_helpers import JWTTestHelper
from app.tests.integration.test_unified_message_flow import MessageFlowTracker
from app.logging_config import central_logger
from app.tests.services.test_ws_connection_mocks import MockWebSocket
import time
from app.routes.utils.websocket_helpers import validate_websocket_token

def auth_tracker():
    """Create authentication flow tracker."""
    return AuthFlowTracker()
