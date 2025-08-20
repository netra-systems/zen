"""Managers Tests - Split from test_real_websocket_auth_integration.py

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
        """Initialize expiry manager."""
        self.jwt_helper = JWTTestHelper()

    def create_expired_jwt_token(self) -> str:
        """Create expired JWT token for rejection testing."""
        expired_payload = self.jwt_helper.create_expired_payload()
        return self.jwt_helper.create_token(expired_payload)

    def create_short_lived_token(self, seconds: int = 5) -> str:
        """Create JWT token with short expiry for refresh testing."""
        from datetime import datetime, timedelta, timezone
        payload = self.jwt_helper.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        return self.jwt_helper.create_token(payload)

    def create_invalid_signature_token(self) -> str:
        """Create token with invalid signature for security testing."""
        payload = self.jwt_helper.create_valid_payload()
        valid_token = self.jwt_helper.create_token(payload)
        parts = valid_token.split('.')
        return f"{parts[0]}.{parts[1]}.invalid_signature_for_testing"
