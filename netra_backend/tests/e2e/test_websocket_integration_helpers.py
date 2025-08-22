"""Utilities Tests - Split from test_websocket_integration.py"""

# Add project root to path

from app.websocket.connection import ConnectionManager as WebSocketManager
from tests.test_utils import setup_test_path
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))


setup_test_path()

import asyncio
import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import websockets
from auth_integration.auth import validate_token_jwt
from fastapi.testclient import TestClient
from main import app
from routes.mcp.main import websocket_endpoint
from ws_manager import WebSocketManager

from app.schemas.websocket_message_types import WebSocketMessage

# Add project root to path
from app.websocket.connection_manager import (

    ConnectionManager,

    get_connection_manager,

)
from app.websocket.message_handler_core import (

    ModernReliableMessageHandler,

)

# Add project root to path


class TestSyntaxFix:

    """Test class for orphaned methods"""


    def __init__(self):

        self.messages_sent = []

        self.messages_received = []

        self.closed = False

        self.accepted = False
