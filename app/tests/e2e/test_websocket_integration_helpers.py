"""Utilities Tests - Split from test_websocket_integration.py"""

import asyncio
import json
import pytest
import websockets
import httpx
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.websocket.connection_manager import get_connection_manager, ModernConnectionManager
from app.websocket.message_handler_core import ModernReliableMessageHandler
from app.ws_manager import WebSocketManager
from app.auth_integration.auth import validate_token_jwt
from app.schemas.websocket_message_types import WebSocketMessage
from app.routes.mcp.main import websocket_endpoint


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
        self.accepted = False
