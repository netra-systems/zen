"""
Shared fixtures for error propagation E2E tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure
- Value Impact: Shared infrastructure for error propagation testing
- Strategic/Revenue Impact: Enables comprehensive error handling validation
"""

import pytest
import asyncio
import uuid
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.unified.e2e.service_orchestrator import E2EServiceOrchestrator
from tests.unified.e2e.real_websocket_client import RealWebSocketClient
from tests.unified.e2e.real_client_types import ClientConfig, ConnectionState
from tests.unified.e2e.config import TEST_USERS, TEST_ENDPOINTS
from tests.unified.e2e.real_http_client import RealHTTPClient

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