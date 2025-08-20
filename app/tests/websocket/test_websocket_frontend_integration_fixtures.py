"""Fixtures Tests - Split from test_websocket_frontend_integration.py"""

import asyncio
import json
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import websockets

def mock_react():
    """Provide mocked React functionality."""
    return MockReact()

def mock_auth_context():
    """Provide mock authentication context."""
    return MockAuthContext()

def mock_websocket():
    """Provide mock WebSocket."""
    with patch('builtins.WebSocket', mock_websocket_class):
        yield MockWebSocket
