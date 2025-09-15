"""
Shared fixtures for error propagation E2E tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure
- Value Impact: Shared infrastructure for error propagation testing
- Strategic/Revenue Impact: Enables comprehensive error handling validation
"""

import asyncio
import json
import logging

# Add project root to path for imports
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest


from tests.e2e.config import TEST_ENDPOINTS, TEST_USERS
from test_framework.http_client import (
    ClientConfig,
    ConnectionState,
)
from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient
from tests.e2e.service_orchestrator import E2EServiceOrchestrator

logger = logging.getLogger(__name__)

@dataclass
class ErrorCorrelationContext:
    """Context for tracking error correlation across services."""
    correlation_id: str
    user_id: str
    operation: str
    start_time: datetime
    service_errors: List[Dict[str, Any]]
    error_messages: List[str]
    recovery_attempts: int = 0

@dataclass 
class ErrorPropagationMetrics:
    """Metrics for error propagation testing."""
    total_errors: int
    correlated_errors: int
    recovery_successes: int
    user_friendly_messages: int
    avg_propagation_time: float

@pytest.fixture
async def service_orchestrator():
    """Create and setup service orchestrator."""
    orchestrator = E2EServiceOrchestrator()
    await orchestrator.setup()
    yield orchestrator
    await orchestrator.cleanup()

@pytest.fixture
async def real_websocket_client():
    """Create real WebSocket client."""
    config = ClientConfig(
        backend_url=TEST_ENDPOINTS["backend"],
        websocket_url=TEST_ENDPOINTS["websocket"],
        auth_url=TEST_ENDPOINTS["auth"]
    )
    client = RealWebSocketClient(config)
    yield client
    await client.disconnect()

@pytest.fixture
async def real_http_client():
    """Create real HTTP client."""
    client = RealHTTPClient(TEST_ENDPOINTS["backend"])
    yield client
    await client.close()

@pytest.fixture
def error_correlation_context():
    """Create error correlation context."""
    return ErrorCorrelationContext(
        correlation_id=str(uuid.uuid4()),
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        operation="test_operation",
        start_time=datetime.now(timezone.utc),
        service_errors=[],
        error_messages=[]
    )

@pytest.fixture
def test_user():
    """Get test user configuration."""
    return TEST_USERS[0]  # Use first test user
