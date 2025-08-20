"""Utilities Tests - Split from test_unified_message_flow.py"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import AsyncMock, patch, Mock
import pytest
from datetime import datetime, timezone
from tests.unified.jwt_token_helpers import JWTTestHelper
from app.schemas.websocket_models import (
from app.schemas.core_enums import WebSocketMessageType, AgentStatus
from app.logging_config import central_logger
from app.tests.services.test_ws_connection_mocks import MockWebSocket
import asyncio
from app.routes.utils.websocket_helpers import decode_token_payload
from starlette.websockets import WebSocketDisconnect
import tracemalloc
from app.agents.supervisor_consolidated import SupervisorAgent

def create_test_token(user_id: str) -> str:
    """Create a valid test token."""
    return jwt_helper.create_access_token(user_id, f"{user_id}@example.com")

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

        def __init__(self, user_id=None):
            self.user_id = user_id
            self.sent_messages = []
