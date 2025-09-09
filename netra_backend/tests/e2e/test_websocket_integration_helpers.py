"""Utilities Tests - Split from test_websocket_integration.py"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
from typing import Any, Dict, List, Optional

import httpx
import pytest
import websockets
from netra_backend.app.auth_integration.auth import validate_token_jwt
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from netra_backend.app.routes.mcp.main import websocket_endpoint

from netra_backend.app.schemas.websocket_message_types import WebSocketMessage

from netra_backend.app.websocket_core import (
    WebSocketManager as ConnectionManager,

    get_connection_monitor,

)
from netra_backend.app.websocket_core.handlers import (
    UserMessageHandler,
    UserMessageHandler,
    HeartbeatHandler,
)

# Removed TestSyntaxFix class as it was broken and had __init__ method that prevented pytest collection
