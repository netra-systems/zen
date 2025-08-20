"""Core Tests - Split from test_first_page_load_websocket_integration.py

Business Value Justification (BVJ):
Segment: ALL | Goal: User Onboarding & Retention | Impact: $50K+ MRR Protection
- Prevents first-impression failures during initial page load (Free→Paid conversion)
- Ensures seamless WebSocket connection for real-time AI interactions
- Validates OAuth token transfer for enterprise authentication compliance  
- Tests token refresh during active sessions (Mid/Enterprise retention)
- Multi-tab connection handling for power users (Enterprise features)

Performance Requirements:
- First page load: <3s complete authentication
- WebSocket connection: <2s initialization  
- OAuth token transfer: <500ms synchronization
- Token refresh: <1s without connection drop
- Multi-tab deduplication: <100ms detection
"""

import asyncio
import time
import uuid
import json
import pytest
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import websockets
from websockets.exceptions import ConnectionClosedError
from test_framework.mock_utils import mock_justified
from ..config import TestTier, TestUser, TEST_ENDPOINTS, TEST_SECRETS
from ..jwt_token_helpers import JWTTestHelper
from .websocket_dev_utilities import WebSocketTestClient, ConnectionState
from .auth_flow_manager import AuthCompleteFlowManager

    def __init__(self):
        """Initialize test manager with service endpoints."""
        self.auth_url = "http://localhost:8081"
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        self.jwt_helper = JWTTestHelper()

    def setup_method(self):
        """Setup test environment for each test."""
        self.tester = FirstPageLoadWebSocketTester()
        self.websocket_client = None
