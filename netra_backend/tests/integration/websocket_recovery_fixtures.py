"""
WebSocket Recovery Test Fixtures and Utilities

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Platform/Internal - Shared testing infrastructure
2. **Business Goal**: Development Velocity - Reduces test duplication and maintenance overhead
3. **Value Impact**: Enables consistent, reliable WebSocket recovery testing across modules
4. **Revenue Impact**: Faster development cycles = faster feature delivery = revenue protection

Shared fixtures, mock classes, and utilities for WebSocket state recovery testing.
Centralizes common testing patterns to ensure consistency and reduce maintenance overhead.

All functions  <= 8 lines per CLAUDE.md requirements.
"""

from datetime import datetime, timezone
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import WebSocketMessage
from netra_backend.app.schemas.websocket_models import WebSocketValidationError
from netra_backend.app.websocket_core.types import ConnectionInfo
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core.reconnection_manager import (
    ReconnectionManager,
)
from starlette.websockets import WebSocketDisconnect, WebSocketState
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import asyncio
import json
import random
import time
import uuid
from netra_backend.app.websocket_core.reconnection_types import (
    ReconnectionConfig,
    ReconnectionState,
)
from netra_backend.app.websocket_core import WebSocketManager

logger = central_logger.get_logger(__name__)

# COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
class MockWebSocket:
    """Mock WebSocket for testing state recovery with realistic connection patterns."""
    
    def __init__(self, user_id: str = None):

        self.user_id = user_id or f"test_user_{uuid.uuid4().hex[:8]}"

        self.sent_messages = []

        self.received_messages = []

        self.state = WebSocketState.CONNECTED

        self.close_code = None

        self.disconnect_count = 0

        self.reconnect_count = 0

        self.network_latency_ms = 0

        self.failure_simulation = False
    
    async def send_text(self, message: str) -> None:

        """Mock send text message with network simulation."""

        await self._simulate_network_conditions()

        if self.state != WebSocketState.CONNECTED:

            raise WebSocketDisconnect(code=1001, reason="Connection lost")

        self.sent_messages.append(json.loads(message))
    
    async def send_json(self, data: Dict[str, Any]) -> None:

        """Mock send JSON message with failure simulation."""

        await self._simulate_network_conditions()

        if self.failure_simulation and random.random() < 0.3:

            raise WebSocketDisconnect(code=1006, reason="Abnormal closure")

        if self.state != WebSocketState.CONNECTED:

            raise WebSocketDisconnect(code=1001, reason="Connection lost")

        self.sent_messages.append(data)
    
    async def close(self, code: int = 1000, reason: str = "Normal closure") -> None:

        """Mock connection close."""

        self.state = WebSocketState.DISCONNECTED

        self.close_code = code

        self.disconnect_count += 1
    
    def simulate_disconnect(self, code: int = 1001, reason: str = "Network error") -> None:

        """Simulate unexpected disconnection."""

        self.state = WebSocketState.DISCONNECTED

        self.close_code = code

        self.disconnect_count += 1
    
    def simulate_reconnect(self) -> None:

        """Simulate successful reconnection."""

        self.state = WebSocketState.CONNECTED

        self.close_code = None

        self.reconnect_count += 1
    
    async def _simulate_network_conditions(self) -> None:

        """Simulate network latency and conditions."""

        if self.network_latency_ms > 0:

            await asyncio.sleep(self.network_latency_ms / 1000)

class StateRecoveryTestHelper:

    """Advanced helper for state recovery testing scenarios."""
    
    def __init__(self):

        self.state_snapshots = {}

        self.recovery_metrics = {}

        self.message_queues = {}

        self.reconnection_timers = {}

        self.network_conditions = {}
    
    def create_test_state_data(self, user_id: str, complexity_level: str = "medium") -> Dict[str, Any]:

        """Create test state data with varying complexity levels."""

        thread_id = f"thread_{uuid.uuid4().hex[:8]}"

        base_data = {

            "user_id": user_id, "thread_id": thread_id, "session_id": str(uuid.uuid4()),

            "active_agents": ["TriageAgent", "DataAgent"], "progress": 65,

            "pending_messages": [], "last_activity": datetime.now(timezone.utc)

        }
        
        if complexity_level == "high":

            base_data.update({

                "active_workflows": [f"workflow_{i}" for i in range(3)],

                "subscription_channels": ["alerts", "progress", "completion"],

                "auth_context": {"token": f"token_{user_id}", "expires": time.time() + 3600}

            })

        return base_data
    
    def capture_state_snapshot(self, manager: WebSocketManager, user_id: str) -> Dict[str, Any]:

        """Capture comprehensive state snapshot for recovery verification."""

        stats = manager.get_unified_stats()

        snapshot = {

            "connections": stats.get("active_connections", 0), "pending_messages": len(manager.pending_messages),

            "sending_messages": len(manager.sending_messages), "telemetry": stats.get("telemetry", {}),

            "timestamp": time.time(), "connection_quality": self._assess_connection_quality(manager)

        }

        self.state_snapshots[user_id] = snapshot

        return snapshot
    
    def _assess_connection_quality(self, manager: WebSocketManager) -> Dict[str, Any]:

        """Assess connection quality metrics."""

        telemetry = manager.telemetry

        return {

            "error_rate": telemetry.get("errors_handled", 0) / max(1, telemetry.get("messages_sent", 1)),

            "success_rate": 1.0 - (telemetry.get("circuit_breaks", 0) / max(1, telemetry.get("connections_opened", 1)))

        }
    
    def simulate_network_disruption(self, websocket: MockWebSocket, pattern: str = "intermittent") -> None:

        """Simulate various network disruption patterns."""

        if pattern == "intermittent":

            websocket.failure_simulation = True

            websocket.network_latency_ms = random.randint(100, 500)

        elif pattern == "high_latency":

            websocket.network_latency_ms = random.randint(1000, 3000)

        elif pattern == "packet_loss":

            websocket.failure_simulation = True

class NetworkConditionSimulator:

    """Simulate various network conditions for realistic testing."""
    
    @staticmethod

    def simulate_intermittent_connectivity(websocket: MockWebSocket, failure_rate: float = 0.3) -> None:

        """Simulate intermittent connectivity issues."""

        websocket.failure_simulation = True

        websocket.network_latency_ms = random.randint(50, 300)
    
    @staticmethod

    def simulate_high_latency_network(websocket: MockWebSocket, latency_ms: int = 1000) -> None:

        """Simulate high latency network conditions."""

        websocket.network_latency_ms = latency_ms
    
    @staticmethod

    def simulate_packet_loss(websocket: MockWebSocket, loss_rate: float = 0.1) -> None:

        """Simulate packet loss conditions."""

        websocket.failure_simulation = True
        # Implementation would involve random failures based on loss_rate

class ReconnectionMetricsCollector:

    """Collect and analyze reconnection metrics for testing."""
    
    def __init__(self):

        self.metrics = {

            "connection_attempts": 0,

            "successful_connections": 0,

            "failed_connections": 0,

            "total_reconnection_time": 0,

            "backoff_violations": 0,

            "message_recovery_rate": 0

        }
    
    def record_connection_attempt(self, success: bool, duration: float) -> None:

        """Record connection attempt metrics."""

        self.metrics["connection_attempts"] += 1

        self.metrics["total_reconnection_time"] += duration
        
        if success:

            self.metrics["successful_connections"] += 1

        else:

            self.metrics["failed_connections"] += 1
    
    def get_success_rate(self) -> float:

        """Calculate connection success rate."""

        if self.metrics["connection_attempts"] == 0:

            return 0.0

        return self.metrics["successful_connections"] / self.metrics["connection_attempts"]
    
    def get_average_reconnection_time(self) -> float:

        """Calculate average reconnection time."""

        if self.metrics["successful_connections"] == 0:

            return 0.0

        return self.metrics["total_reconnection_time"] / self.metrics["successful_connections"]

def create_standard_reconnection_config() -> ReconnectionConfig:

    """Create standard reconnection config for testing."""

    return ReconnectionConfig(

        initial_delay_ms=100,  # Fast reconnection for testing

        max_delay_ms=1000,

        backoff_multiplier=1.5,

        max_attempts=5,

        jitter_factor=0.1

    )

def create_state_building_messages(state_data: Dict[str, Any]) -> List[Dict[str, Any]]:

    """Create messages to build session state."""

    return [

        {"type": "session_start", "thread_id": state_data["thread_id"], "user_id": state_data["user_id"]},

        {"type": "agent_activation", "agents": state_data["active_agents"]},

        {"type": "progress_update", "progress": state_data["progress"]}

    ]

async def setup_test_manager_with_helper():

    """Setup unified WebSocket manager for state recovery testing."""

    manager = WebSocketManager()

    helper = StateRecoveryTestHelper()

    return {"manager": manager, "helper": helper}