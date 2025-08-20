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
from app.websocket.connection_manager import ConnectionManager
from app.websocket.message_handler_core import ModernReliableMessageHandler
from app.ws_manager import WebSocketManager
from app.auth_integration.auth import validate_token
from app.schemas.websocket_message_types import WebSocketMessage
from app.routes.websockets import websocket_endpoint
from app.routes.websockets import websocket_endpoint

    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
        self.accepted = False
