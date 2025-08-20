"""Utilities Tests - Split from test_websocket_frontend_integration.py"""

import asyncio
import json
import pytest
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import websockets

def mock_websocket_class(url):
    ws = MockWebSocket()
    ws.url = url
    return ws

    def createContext(default_value=None):
        return Mock()

    def useContext(context):
        return Mock()

    def useEffect(effect, deps):
        effect()

    def useState(initial_value):
        return [initial_value, Mock()]

    def useCallback(callback, deps):
        return callback

    def useRef(initial_value):
        ref = Mock()
        ref.current = initial_value
        return ref

    def useMemo(factory, deps):
        return factory()

    def __init__(self, token="mock_valid_token"):
        self.token = token

    def __init__(self):
        self.url = ""
        self.readyState = 1  # OPEN
        self.onopen = None
        self.onmessage = None
        self.onclose = None
        self.onerror = None
        self.messages_sent = []
        self.should_fail = False

    def send(self, data):
        if self.should_fail:
            raise Exception("Mock WebSocket error")
        self.messages_sent.append(json.loads(data))
        
        # Simulate server responses
        message = json.loads(data)
        if message.get("type") == "ping":
            # Simulate pong response
            pong_response = {"type": "pong", "timestamp": time.time()}
            if self.onmessage:
                mock_event = Mock()
                mock_event.data = json.dumps(pong_response)
                self.onmessage(mock_event)

    def close(self, code=1000, reason=""):
        self.readyState = 3  # CLOSED
        if self.onclose:
            mock_event = Mock()
            mock_event.code = code
            mock_event.reason = reason
            self.onclose(mock_event)

    def simulate_open(self):
        if self.onopen:
            self.onopen(Mock())

    def simulate_message(self, message_data):
        if self.onmessage:
            mock_event = Mock()
            mock_event.data = json.dumps(message_data)
            self.onmessage(mock_event)

    def simulate_error(self):
        if self.onerror:
            self.onerror(Mock())
