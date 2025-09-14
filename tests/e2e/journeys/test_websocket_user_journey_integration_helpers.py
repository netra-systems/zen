"""Utilities Tests - Split from test_websocket_user_journey_integration.py

Business Value Justification (BVJ):
Segment: ALL | Goal: User Journey Optimization & Retention | Impact: $50K+ MRR Protection
- Validates thread creation for first-time users (Free -> Paid conversion critical)
- Ensures message queuing during auth transitions (prevents message loss)
- Tests session persistence across page refreshes (Mid/Enterprise retention)
- Validates reconnection flow when auth tokens expire (prevents session drops)
- Ensures first AI agent response delivery (demonstrates platform value)

Performance Requirements:
- Thread initialization: <2s for new users
- Message queue processing: <500ms during auth transitions
- Session persistence: <1s cross-service synchronization
- Token refresh reconnection: <3s complete flow
- First agent response: <5s end-to-end delivery
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError

# Removed mock import - using real service testing per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services
from tests.e2e.config import TEST_ENDPOINTS, TEST_SECRETS, CustomerTier, TestUser
from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.integration.websocket_dev_utilities import (
    ConnectionState,
    WebSocketClientSimulator,
)
from tests.e2e.jwt_token_helpers import JWTTestHelper


class TestWebSocketUserJourneyer:
    """Test manager for WebSocket user journey testing."""

    def __init__(self):
        """Initialize test manager with service endpoints."""
        self.auth_url = "http://localhost:8081"
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        self.jwt_helper = JWTTestHelper()

    def setup_method(self):
        """Setup test environment for each test."""
        self.tester = WebSocketUserJourneyTester()
        self.websocket_client = None
