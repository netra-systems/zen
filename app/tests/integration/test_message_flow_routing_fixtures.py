"""Fixtures Tests - Split from test_message_flow_routing.py"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock, patch, Mock, MagicMock
import pytest
from datetime import datetime, timezone
from app.tests.integration.test_unified_message_flow import MessageFlowTracker
from app.tests.test_utilities.websocket_mocks import MockWebSocket
from app.schemas.websocket_models import WebSocketMessage, UserMessagePayload
from app.schemas.core_enums import WebSocketMessageType
from app.logging_config import central_logger

def routing_tracker():
    """Create routing flow tracker."""
    return RoutingFlowTracker()
