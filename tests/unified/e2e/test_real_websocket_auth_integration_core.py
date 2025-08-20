"""Core Tests - Split from test_real_websocket_auth_integration.py

Business Value Justification (BVJ):
1. Segment: Enterprise & Growth (Critical for $50K+ MRR protection)
2. Business Goal: Prevent authentication failures during real-time agent interactions
3. Value Impact: Ensures seamless AI agent communication without auth interruptions
4. Revenue Impact: Protects revenue by validating cross-service token validation

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (focused on critical auth flows)
- Function size: <25 lines each (modular authentication steps)
- Real services only (Auth:8001, Backend:8000, WebSocket)
- <10 seconds per test execution
- Comprehensive token lifecycle testing
"""

import asyncio
import time
import uuid
from typing import Dict, Optional, List
import pytest
import httpx
import websockets
from websockets.exceptions import ConnectionClosedError
from ..jwt_token_helpers import JWTTestHelper
from ..config import TEST_USERS
from datetime import datetime, timedelta, timezone

    def __init__(self):
        """Initialize auth tester with service endpoints."""
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000" 
        self.websocket_url = "ws://localhost:8000/ws"
        self.jwt_helper = JWTTestHelper()

    def create_mock_jwt_token_for_fallback(self) -> str:
        """Create mock JWT token when Auth service unavailable."""
        payload = self.jwt_helper.create_valid_payload()
        return self.jwt_helper.create_token(payload)

    def __init__(self, auth_tester: RealWebSocketAuthTester):
        """Initialize concurrent tester."""
        self.auth_tester = auth_tester
        self.active_connections: List[Dict] = []

    def auth_tester(self):
        """Initialize real WebSocket authentication tester."""
        return RealWebSocketAuthTester()

    def expiry_manager(self):
        """Initialize token expiry manager."""
        return TokenExpiryManager()

    def concurrent_tester(self, auth_tester):
        """Initialize concurrent connection tester."""
        return ConcurrentConnectionTester(auth_tester)
