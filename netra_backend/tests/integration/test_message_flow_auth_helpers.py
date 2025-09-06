from unittest.mock import Mock, patch, MagicMock

"""Utilities Tests - Split from test_message_flow_auth.py"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
import pytest
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.websocket_helpers import validate_websocket_token

# Removed WebSocket mock import - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

from netra_backend.tests.integration.jwt_token_helpers import JWTTestHelper

# Global JWT helper instance
jwt_helper = JWTTestHelper()

def create_test_token(user_id: str) -> str:
    """Create a valid test token."""
    return jwt_helper.create_test_token(user_id, f"{user_id}@example.com")

def create_expired_token(user_id: str) -> str:
    """Create an expired test token."""
    return jwt_helper.create_expired_token(user_id)

def create_invalid_token(user_id: str) -> str:
    """Create an invalid test token."""
    return f"invalid_token_{user_id}"

class AuthFlowTracker:
    """Helper for tracking authentication flows."""
    
    def __init__(self):
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

                class TestWebSocketAuthMock(Mock):
                    """Extended mock WebSocket for auth testing."""
    
                    def __init__(self, user_id=None):
                        super().__init__()
                        self.user_id = user_id or self._generate_user_id()
                        self.sent_messages = []
