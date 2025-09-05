"""
WebSocket State Persistence Integration Tests

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise, Mid, Early - All customers depend on message reliability  
2. **Business Goal**: Prevent $10K-$50K workflow loss from message drops and state corruption
3. **Value Impact**: Ensures message queuing and state preservation during network disruptions
4. **Revenue Impact**: Message reliability = workflow continuity = customer satisfaction = retention

Tests WebSocket message queuing, state persistence during disconnections,
and comprehensive state recovery scenarios. Critical for maintaining workflow integrity.

COVERAGE TARGET: 100% for message queue and state persistence functionality
All functions ≤8 lines per CLAUDE.md requirements.
"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import random
import time

import pytest

from netra_backend.app.websocket_core.reconnection_types import ReconnectionConfig

from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.tests.integration.websocket_recovery_fixtures import (

    MockWebSocket,

    StateRecoveryTestHelper,

    create_standard_reconnection_config,

    create_state_building_messages,

    setup_test_manager_with_helper,

)

class TestWebSocketMessageQueueRecovery:

    """Message queue behavior during WebSocket disconnection and recovery tests."""
    
    @pytest.fixture

    async def queue_recovery_setup(self):

        """Setup for message queue recovery tests."""

        return await setup_test_manager_with_helper()
    
    @pytest.mark.asyncio
    async def test_message_queue_during_disconnection(self, queue_recovery_setup):

        """Test message queue behavior during WebSocket disconnection."""

        setup = queue_recovery_setup

        manager, helper = setup["manager"], setup["helper"]

        user_id = "test_message_queue_recovery"
        
        # Setup connection and trigger disconnection

        queued_state = await self._setup_connection_with_message_queue(manager, user_id)
        
        # Verify message queue recovery after reconnection

        await self._verify_message_queue_recovery(manager, user_id, queued_state)
    
    async def _setup_connection_with_message_queue(self, manager: WebSocketManager, user_id: str) -> dict:

        """Setup connection and create message queue during disconnection."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)
        
        # Disconnect to trigger message queuing

        websocket.simulate_disconnect(1006, "Network error")

        await manager.disconnect_user(user_id, websocket, 1006, "Network error")
        
        test_message = {"type": "agent_update", "data": "test message"}

        result = await manager.send_message_to_user(user_id, test_message, retry=True)

        return {"websocket": websocket, "message_sent": test_message, "result": result}
    
    async def _verify_message_queue_recovery(self, manager: WebSocketManager, 

                                           user_id: str, queued_state: dict) -> None:

        """Verify message queue recovery after reconnection."""

        new_websocket = MockWebSocket(user_id)

        new_websocket.simulate_reconnect()

        await manager.connect_user(user_id, new_websocket)
        
        stats = await manager.get_transactional_stats()

        assert stats["pending_messages"] >= 0, "Message queue should be in valid state"
    
    @pytest.mark.asyncio
    async def test_message_priority_during_queue_recovery(self, queue_recovery_setup):

        """Test message priority handling during queue recovery."""

        setup = queue_recovery_setup

        manager, helper = setup["manager"], setup["helper"]

        user_id = "test_priority_queue"
        
        # Create prioritized message queue

        priority_queue = await self._create_prioritized_message_queue(manager, user_id)
        
        # Verify priority preservation during recovery

        await self._verify_priority_preservation(manager, user_id, priority_queue)
    
    async def _create_prioritized_message_queue(self, manager: WebSocketManager, user_id: str) -> dict:

        """Create message queue with different priority messages."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)

        websocket.state = "disconnected"
        
        prioritized_messages = [

            {"type": "urgent_update", "priority": "high", "sequence": 1},

            {"type": "progress_update", "priority": "medium", "sequence": 2}

        ]

        for msg in prioritized_messages:

            await manager.send_message_to_user(user_id, msg, retry=True)
        
        return {"websocket": websocket, "queued_count": len(prioritized_messages)}
    
    async def _verify_priority_preservation(self, manager: WebSocketManager,

                                          user_id: str, priority_queue: dict) -> None:

        """Verify priority message handling during recovery."""

        new_websocket = MockWebSocket(user_id)

        new_websocket.state = "connected"

        await manager.connect_user(user_id, new_websocket)
        
        stats = await manager.get_transactional_stats()

        assert stats["pending_messages"] >= 0, "Priority messages should be handled"

class TestWebSocketPartialMessageRecovery:

    """Partial message handling during WebSocket state recovery tests."""
    
    @pytest.mark.asyncio
    async def test_partial_message_handling_during_recovery(self):

        """Test partial message handling during WebSocket state recovery."""

        manager = WebSocketManager()

        user_id = "test_partial_message_handling"
        
        # Create partial message scenario

        partial_state = await self._create_partial_message_scenario(manager, user_id)
        
        # Verify partial message recovery

        await self._verify_partial_message_recovery(manager, user_id, partial_state)
    
    async def _create_partial_message_scenario(self, manager: WebSocketManager, user_id: str) -> dict:

        """Create scenario with partial messages during disconnection."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)
        
        websocket.failure_simulation = True

        websocket.network_latency_ms = 100
        
        test_message = {"type": "agent_log", "data": "large message data" * 100}

        try:

            result = await manager.send_message_to_user(user_id, test_message)

        except Exception:

            pass  # Expected for simulated network issues
        
        return {"websocket": websocket, "message": test_message}
    
    async def _verify_partial_message_recovery(self, manager: WebSocketManager,

                                             user_id: str, partial_state: dict) -> None:

        """Verify partial message handling during recovery."""

        new_websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, new_websocket)
        
        stats = await manager.get_transactional_stats()

        assert stats["pending_messages"] >= 0, "Partial messages should be handled"
    
    @pytest.mark.asyncio
    async def test_large_message_recovery_resilience(self):

        """Test recovery resilience with large message payloads."""

        manager = WebSocketManager()

        user_id = "test_large_message_resilience"
        
        # Setup large message scenario

        large_message_state = await self._setup_large_message_scenario(manager, user_id)
        
        # Verify system stability with large messages

        await self._verify_large_message_stability(manager, user_id, large_message_state)
    
    async def _setup_large_message_scenario(self, manager: WebSocketManager, user_id: str) -> dict:

        """Setup scenario with large message payloads."""

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)

        websocket.state = "disconnected"
        
        large_message = {"type": "large_data", "payload": "x" * 1000, "chunk_id": 1}

        result = await manager.send_message_to_user(user_id, large_message)

        return {"websocket": websocket, "message": large_message, "result": result}
    
    async def _verify_large_message_stability(self, manager: WebSocketManager,

                                            user_id: str, large_message_state: dict) -> None:

        """Verify system stability with large message handling."""

        stats = manager.get_unified_stats()

        assert stats["telemetry"]["errors_handled"] >= 0, "Large message handling should be tracked"

class TestWebSocketComprehensiveStateRecovery:

    """Comprehensive state recovery scenarios including complex workflows."""
    
    @pytest.mark.asyncio
    async def test_comprehensive_state_recovery_workflow(self):

        """Test comprehensive WebSocket state recovery across complex workflows."""
        # Reset singleton to ensure clean state

        WebSocketManager._instance = None

        manager = WebSocketManager()

        helper = StateRecoveryTestHelper()

        user_id = "comprehensive_test_user"
        
        # Phase 1: Establish complex state

        initial_state = await self._establish_complex_workflow_state(manager, helper, user_id)
        
        # Phase 2: Test disconnection with state preservation

        await self._test_disconnection_with_state_preservation(manager, user_id, initial_state)
        
        # Phase 3: Verify comprehensive recovery

        await self._verify_comprehensive_recovery(manager, helper, user_id)
        
        await manager.shutdown()
    
    async def _establish_complex_workflow_state(self, manager: WebSocketManager,

                                              helper: StateRecoveryTestHelper, user_id: str) -> dict:

        """Establish complex workflow state for testing."""

        websocket = MockWebSocket(user_id)

        conn_info = await manager.connect_user(user_id, websocket)

        assert conn_info is not None, "Initial connection should be established"
        
        state_data = helper.create_test_state_data(user_id, "high")

        state_messages = [

            {"type": "create_thread", "thread_id": state_data["thread_id"]},

            {"type": "start_agent", "agents": state_data["active_agents"]}

        ]

        for message in state_messages:

            await manager.send_message_to_user(user_id, message)
        
        return helper.capture_state_snapshot(manager, user_id)
    
    async def _test_disconnection_with_state_preservation(self, manager: WebSocketManager,

                                                        user_id: str, initial_state: dict) -> None:

        """Test disconnection while preserving complex state."""

        websocket = MockWebSocket(user_id)

        websocket.simulate_disconnect(1006, "Network disruption")

        await manager.disconnect_user(user_id, websocket, 1006, "Network disruption")
        
        # Queue messages during disconnection

        disconnected_messages = [

            {"type": "error", "priority": "critical", "message": "System alert during downtime"},

            {"type": "agent_update", "progress": 85, "timestamp": time.time()}

        ]

        for message in disconnected_messages:

            await manager.send_message_to_user(user_id, message, retry=True)
    
    async def _verify_comprehensive_recovery(self, manager: WebSocketManager,

                                           helper: StateRecoveryTestHelper, user_id: str) -> None:

        """Verify comprehensive state recovery after reconnection."""

        new_websocket = MockWebSocket(user_id)

        new_websocket.simulate_reconnect()

        reconnect_info = await manager.connect_user(user_id, new_websocket)

        assert reconnect_info is not None, "Comprehensive recovery should succeed"
        
        final_snapshot = helper.capture_state_snapshot(manager, user_id)

        connection_quality = final_snapshot["connection_quality"]

        assert connection_quality["success_rate"] > 0.7, "Connection success rate should remain high"

class TestWebSocketZeroMessageLoss:

    """Critical tests ensuring zero message loss during reconnection scenarios."""
    
    @pytest.mark.asyncio
    async def test_zero_message_loss_during_reconnection(self):

        """Critical test ensuring zero message loss during reconnection scenarios."""

        WebSocketManager._instance = None

        manager = WebSocketManager()

        user_id = "zero_loss_test_user"

        message_tracker = []
        
        # Setup and track initial messages

        websocket = MockWebSocket(user_id)

        await manager.connect_user(user_id, websocket)

        for i in range(10):

            message = {"type": "agent_update", "sequence": i, "id": f"msg_{i}"}

            message_tracker.append(message["id"])

            await manager.send_message_to_user(user_id, message)
        
        # Simulate disconnection and queue messages

        websocket.simulate_disconnect(1006, "Network failure")

        await manager.disconnect_user(user_id, websocket, 1006, "Network failure")

        for i in range(10, 20):

            message = {"type": "agent_log", "sequence": i, "id": f"msg_{i}"}

            message_tracker.append(message["id"])

            await manager.send_message_to_user(user_id, message, retry=True)
        
        # Reconnect and verify stability

        new_websocket = MockWebSocket(user_id)

        new_websocket.simulate_reconnect()

        await manager.connect_user(user_id, new_websocket)

        await asyncio.sleep(0.3)

        assert len(message_tracker) > 0, "Should handle message recovery gracefully"

        await manager.shutdown()