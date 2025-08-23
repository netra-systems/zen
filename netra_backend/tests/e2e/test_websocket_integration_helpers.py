"""Utilities Tests - Split from test_websocket_integration.py"""

from netra_backend.app.websocket.unified.manager import UnifiedWebSocketManager as WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import websockets
from netra_backend.app.auth_integration.auth import validate_token_jwt
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from netra_backend.app.routes.mcp.main import websocket_endpoint

from netra_backend.app.schemas.websocket_message_types import WebSocketMessage

from netra_backend.app.websocket.connection_manager import (

    ConnectionManager,

    get_connection_manager,

)
from netra_backend.app.websocket.message_handler_core import (

    ModernReliableMessageHandler,

)

# Removed TestSyntaxFix class as it was broken and had __init__ method that prevented pytest collection
