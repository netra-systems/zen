"""Core Tests - Split from test_cors_integration.py"""

import os
import pytest
import asyncio
import httpx
import websockets
import json
from typing import Dict, Any, Optional
from unittest.mock import patch
from app.core.middleware_setup import get_cors_origins, is_origin_allowed
from app.core.middleware_setup import get_cors_origins, is_origin_allowed


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def mock_backend_server_url(self):
        """Get backend server URL for testing."""
        return os.getenv("BACKEND_URL", "http://localhost:8000")

    def mock_auth_server_url(self):
        """Get auth server URL for testing."""
        return os.getenv("AUTH_URL", "http://localhost:8081")

    def frontend_origin(self):
        """Frontend origin that makes cross-origin requests."""
        return "http://localhost:3001"

    def websocket_url(self):
        """Get WebSocket URL for testing."""
        return os.getenv("WS_URL", "ws://localhost:8000/ws")

    def backend_url(self):
        return os.getenv("BACKEND_URL", "http://localhost:8000")

    def auth_url(self):
        return os.getenv("AUTH_URL", "http://localhost:8081")
