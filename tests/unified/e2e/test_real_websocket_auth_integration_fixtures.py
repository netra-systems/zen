"""Fixtures Tests - Split from test_real_websocket_auth_integration.py

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

    def auth_tester(self):
        """Initialize real WebSocket authentication tester."""
        return RealWebSocketAuthTester()

    def expiry_manager(self):
        """Initialize token expiry manager."""
        return TokenExpiryManager()

    def concurrent_tester(self, auth_tester):
        """Initialize concurrent connection tester."""
        return ConcurrentConnectionTester(auth_tester)
