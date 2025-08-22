"""Utilities Tests - Split from test_message_flow_auth.py"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from logging_config import central_logger
from netra_backend.app.routes.utils.websocket_helpers import validate_websocket_token

from tests.test_unified_message_flow import MessageFlowTracker
from tests.test_ws_connection_mocks import MockWebSocket

# Add project root to path
from tests.jwt_token_helpers import JWTTestHelper

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
