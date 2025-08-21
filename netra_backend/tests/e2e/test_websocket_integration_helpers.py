"""Utilities Tests - Split from test_websocket_integration.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import pytest
import websockets
import httpx
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from main import app

# Add project root to path
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add project root to path

from netra_backend.app.websocket.connection_manager import get_connection_manager, ModernConnectionManager
from netra_backend.app.websocket.message_handler_core import ModernReliableMessageHandler
from ws_manager import WebSocketManager
from auth_integration.auth import validate_token_jwt
from netra_backend.app.schemas.websocket_message_types import WebSocketMessage
from routes.mcp.main import websocket_endpoint

# Add project root to path


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
        self.accepted = False
