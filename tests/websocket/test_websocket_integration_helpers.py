"""Utilities Tests - Split from test_websocket_integration.py"""

import asyncio
import json
import pytest
import websockets
import time
from typing import Dict, Any
from unittest.mock import patch, AsyncMock
from test_framework.mock_utils import mock_justified
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.db.postgres import get_async_db
from app.clients.auth_client import auth_client
from app.core.websocket_cors import get_websocket_cors_handler
from app.core.websocket_cors import get_websocket_cors_handler
from app.core.websocket_cors import get_websocket_cors_handler
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager
from fastapi import HTTPException
from app.routes.websocket_secure import SecureWebSocketManager
from fastapi import HTTPException
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager, SECURE_WEBSOCKET_CONFIG
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager, SECURE_WEBSOCKET_CONFIG
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import get_secure_websocket_manager
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager
from app.routes.websocket_secure import SecureWebSocketManager

            def __init__(self):
                self.headers = {"authorization": f"Bearer {valid_jwt_token}"}

            def __init__(self):
                self.headers = {"sec-websocket-protocol": f"jwt.{valid_jwt_token}, chat"}

            def __init__(self):
                self.headers = {}

            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []

            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []

            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []

            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []

            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False
                self.close_code = None
                self.close_reason = None

            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False

            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []

            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False

            def __init__(self):
                self.application_state = "CONNECTED"
                self.closed = False

            def __init__(self):
                self.application_state = "CONNECTED"
                self.sent_messages = []

            def __init__(self):
                self.application_state = "CONNECTED"
                self.send_error = False

                def __init__(self):
                    self.headers = {"authorization": f"Bearer {valid_jwt_token}"}
