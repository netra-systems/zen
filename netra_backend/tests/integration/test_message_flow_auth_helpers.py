"""Utilities Tests - Split from test_message_flow_auth.py"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import asyncio
import json
import jwt
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone, timedelta

# Add project root to path

from netra_backend.tests.unified.jwt_token_helpers import JWTTestHelper
from netra_backend.tests.integration.test_unified_message_flow import MessageFlowTracker
from logging_config import central_logger
from netra_backend.tests.services.test_ws_connection_mocks import MockWebSocket
import time
from routes.utils.websocket_helpers import validate_websocket_token

# Add project root to path

def create_test_token(user_id: str) -> str:
    """Create a valid test token."""
    return jwt_helper.create_access_token(user_id, f"{user_id}@example.com")

def create_expired_token(user_id: str) -> str:
    """Create an expired test token."""
    payload = jwt_helper.create_expired_payload()
    payload["sub"] = user_id
    payload["email"] = f"{user_id}@example.com"
    return jwt_helper.create_token(payload)

def create_invalid_token(user_id: str) -> str:
    """Create an invalid test token."""
    return f"invalid_token_{user_id}"

    def __init__(self):
        super().__init__()
        self.auth_attempts: List[Dict[str, Any]] = []
        self.failed_auth_count = 0

    def log_auth_attempt(self, user_id: str, token_valid: bool, 
                        error: Optional[str] = None) -> None:
        """Log authentication attempt."""
        attempt = {
            "user_id": user_id,
            "token_valid": token_valid,
            "timestamp": datetime.now(timezone.utc),
            "error": error
        }
        self.auth_attempts.append(attempt)
        
        if not token_valid:
            self.failed_auth_count += 1

    def get_auth_success_rate(self) -> float:
        """Calculate authentication success rate."""
        if not self.auth_attempts:
            return 0.0
        
        successful = sum(1 for attempt in self.auth_attempts if attempt["token_valid"])
        return successful / len(self.auth_attempts)

        def __init__(self, user_id=None):
            self.user_id = user_id
            self.sent_messages = []
