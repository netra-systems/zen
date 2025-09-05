"""Utilities Tests - Split from test_unified_message_flow.py"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import tracemalloc
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from netra_backend.app.logging_config import central_logger
from netra_backend.app.routes.utils.websocket_helpers import decode_token_payload
from starlette.websockets import WebSocketDisconnect

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.schemas.core_enums import AgentStatus, WebSocketMessageType
# Removed WebSocket mock import - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
from test_framework.real_services import get_real_services

from netra_backend.tests.integration.jwt_token_helpers import JWTTestHelper
from test_framework.fixtures.message_flow import MessageFlowTracker

# Global JWT helper instance
jwt_helper = JWTTestHelper()
logger = central_logger

def create_test_token(user_id: str) -> str:
    """Create a valid test token."""
    return jwt_helper.create_test_token(user_id, f"{user_id}@example.com")

class MessageFlowTestHelper:
    """Helper class for testing message flows."""
    
    def __init__(self):
        self.flow_log: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, float] = {}
        self.error_count = 0

    def log_step(self, step: str, data: Dict[str, Any]) -> None:
        """Log flow step with timestamp."""
        entry = {
            "step": step,
            "timestamp": time.time(),
            "data": data,
            "step_id": str(uuid.uuid4())
        }
        self.flow_log.append(entry)
        logger.info(f"[FLOW TRACKER] {step}: {data}")

    def start_timer(self, operation: str) -> str:
        """Start performance timer."""
        timer_id = f"{operation}_{uuid.uuid4().hex[:8]}"
        self.performance_metrics[f"{timer_id}_start"] = time.time()
        return timer_id

    def end_timer(self, timer_id: str) -> float:
        """End timer and return duration."""
        end_time = time.time()
        start_time = self.performance_metrics.get(f"{timer_id}_start", end_time)
        duration = end_time - start_time
        self.performance_metrics[timer_id] = duration
        return duration

    def _verify_complete_flow(self, tracker: MessageFlowTracker, duration: float) -> None:
        """Verify complete message flow."""
        assert len(tracker.flow_log) >= 5, "Missing flow steps"
        assert duration < 5.0, f"Flow too slow: {duration}s"
        assert tracker.error_count == 0, f"Flow had {tracker.error_count} errors"
        
        # Verify flow sequence
        expected_steps = [
            "frontend_message_created",
            "websocket_auth_completed", 
            "message_routed_to_agent_service",
            "agent_processing_completed",
            "response_delivered_to_frontend"
        ]
        
        actual_steps = [entry["step"] for entry in tracker.flow_log]
        for step in expected_steps:
            assert step in actual_steps, f"Missing flow step: {step}"

class TestWebSocketMock(Mock):
    """Extended mock WebSocket for testing."""
    
    def __init__(self, user_id=None):
        super().__init__()
        self.user_id = user_id or self._generate_user_id()
        self.sent_messages = []