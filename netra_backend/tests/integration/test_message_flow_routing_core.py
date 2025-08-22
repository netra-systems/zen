"""Core Tests - Split from test_message_flow_routing.py"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from logging_config import central_logger

from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.schemas.websocket_models import (
    UserMessagePayload,
    WebSocketMessage,
)

# Add project root to path
from .test_unified_message_flow import MessageFlowTracker
from .websocket_mocks import MockWebSocket

# Add project root to path


class TestSyntaxFix:
    """Test class for orphaned methods"""

    def __init__(self):
        super().__init__()
        self.routing_decisions: List[Dict[str, Any]] = []
        self.agent_invocations: List[Dict[str, Any]] = []

    def log_routing_decision(self, message_type: str, target_agent: str,
                           routing_reason: str) -> None:
        """Log routing decision."""
        decision = {
            "message_type": message_type,
            "target_agent": target_agent,
            "routing_reason": routing_reason,
            "timestamp": datetime.now(timezone.utc),
            "decision_id": str(uuid.uuid4())
        }
        self.routing_decisions.append(decision)

    def log_agent_invocation(self, agent_name: str, method: str,
                           success: bool, duration: float) -> None:
        """Log agent invocation."""
        invocation = {
            "agent_name": agent_name,
            "method": method,
            "success": success,
            "duration": duration,
            "timestamp": datetime.now(timezone.utc)
        }
        self.agent_invocations.append(invocation)
