"""Core Tests - Split from test_message_flow_auth.py"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import jwt
import pytest
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.websocket_helpers import validate_websocket_token

from netra_backend.tests.integration.test_unified_message_flow import MessageFlowTracker
from netra_backend.tests.integration.test_ws_connection_mocks import MockWebSocket

from netra_backend.tests.integration.jwt_token_helpers import JWTTestHelper

class TestSyntaxFix:
    """Test class for orphaned methods"""

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
