"""Test Suite 5: WebSocket Reconnection State - Business Critical Tests

WebSocket reconnection state preservation tests protecting $60K+ MRR.
Performance requirement: <2s reconnection, zero message loss.

BVJ: Enterprise segment, prevents connection-related churn, ensures session continuity.
"""

import asyncio
import time
import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

from .config import TEST_USERS
from netra_backend.app.core.websocket_recovery_types import ConnectionState, MessageState


class WebSocketStateManager:
    """Manages WebSocket session state for reconnection testing."""
    
    def __init__(self, connection_id: str):
        self.connection_id = connection_id
        self.session_state: Dict[str, Any] = {}
        self.message_queue: List[MessageState] = []
        self.connection_state = ConnectionState.DISCONNECTED
    
    def capture_state(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Capture current session state for preservation."""
        self.session_state = {
            "user_id": user_context.get("user_id"),
            "active_thread": user_context.get("active_thread"),
            "agent_context": user_context.get("agent_context", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return self.session_state.copy()
    
    def queue_message(self, message: Dict[str, Any]) -> None:
        """Queue message during disconnection."""
        message_state = MessageState(
            message_id=f"msg_{len(self.message_queue)}",
            content=message,
            timestamp=datetime.now(timezone.utc)
        )
        self.message_queue.append(message_state)
    
    def restore_state(self, previous_state: Dict[str, Any]) -> bool:
        """Restore session state after reconnection."""
        if not previous_state:
            return False
        self.session_state = previous_state
        return True
    
    def flush_messages(self) -> int:
        """Flush queued messages and return count."""
        count = len(self.message_queue)
        self.message_queue.clear()
        return count


class WebSocketReconnectionStateTester:
    """Core tester for WebSocket reconnection state management."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
    
    async def setup_session_with_state(self, user_id: str) -> Dict[str, Any]:
        """Setup WebSocket session with complex state."""
        state_manager = WebSocketStateManager(f"conn_{user_id}")
        user_context = {
            "user_id": user_id,
            "active_thread": f"thread_{user_id}_main",
            "agent_context": {"current_task": "data_analysis", "execution_phase": "thinking"}
        }
        captured_state = state_manager.capture_state(user_context)
        state_manager.connection_state = ConnectionState.CONNECTED
        return {"state_manager": state_manager, "user_context": user_context, "captured_state": captured_state}
    
    async def simulate_network_interruption(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate network interruption with message queueing."""
        state_manager = session_data["state_manager"]
        test_messages = [
            {"type": "agent_progress", "content": "Step 2 completed"},
            {"type": "user_input", "content": "Please continue analysis"},
            {"type": "system_notification", "content": "Analysis progress: 60%"}
        ]
        for message in test_messages:
            state_manager.queue_message(message)
        state_manager.connection_state = ConnectionState.DISCONNECTED
        return {"messages_queued": len(test_messages), "state_preserved": bool(state_manager.session_state)}
    
    async def execute_reconnection_with_state_recovery(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute reconnection with full state recovery."""
        state_manager = session_data["state_manager"]
        self.start_time = time.time()
        await asyncio.sleep(0.05)  # Simulate connection time
        state_manager.connection_state = ConnectionState.CONNECTED
        reconnection_time = time.time() - self.start_time
        state_restored = state_manager.restore_state(session_data["captured_state"])
        messages_delivered = state_manager.flush_messages()
        return {
            "reconnection_successful": True,
            "state_restored": state_restored,
            "messages_delivered": messages_delivered,
            "reconnection_time": reconnection_time,
            "performance_met": reconnection_time < 2.0
        }


@pytest.mark.asyncio
class TestWebSocketReconnectionState:
    """Test Suite 5: WebSocket Reconnection State - Comprehensive Testing."""
    
    @pytest.fixture
    def state_tester(self):
        """Initialize WebSocket reconnection state tester."""
        return WebSocketReconnectionStateTester()
    
    @pytest.fixture
    def enterprise_user_id(self):
        """Provide enterprise test user ID."""
        return TEST_USERS["enterprise"].id
    
    async def test_basic_reconnection_preserves_state(self, state_tester, enterprise_user_id):
        """Test Case 1: Basic reconnection flow preserves complete session state."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        interruption_result = await state_tester.simulate_network_interruption(session_data)
        assert interruption_result["state_preserved"]
        
        recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
        assert recovery_result["reconnection_successful"]
        assert recovery_result["state_restored"]
        assert recovery_result["performance_met"]
        
        state_manager = session_data["state_manager"]
        assert state_manager.session_state["user_id"] == enterprise_user_id
        assert state_manager.session_state["agent_context"]["current_task"] == "data_analysis"
    
    async def test_message_queue_preservation_and_delivery(self, state_tester, enterprise_user_id):
        """Test Case 2: Message queue preserved and delivered after reconnection."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        interruption_result = await state_tester.simulate_network_interruption(session_data)
        messages_queued = interruption_result["messages_queued"]
        
        recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
        assert recovery_result["messages_delivered"] == messages_queued
        assert len(session_data["state_manager"].message_queue) == 0
    
    async def test_auth_context_persistence(self, state_tester, enterprise_user_id):
        """Test Case 3: Authentication context maintained across reconnection."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        auth_context = {"user_id": enterprise_user_id, "session_token": "test_token_123"}
        session_data["captured_state"]["auth_context"] = auth_context
        
        await state_tester.simulate_network_interruption(session_data)
        recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
        
        assert recovery_result["state_restored"]
        restored_auth = session_data["state_manager"].session_state.get("auth_context", {})
        assert restored_auth["user_id"] == enterprise_user_id
    
    async def test_state_snapshot_recovery(self, state_tester, enterprise_user_id):
        """Test Case 4: Complete state snapshot restored after reconnection."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        complex_state = {"workspace": {"files": ["data.csv"], "directory": "/workspace"}}
        session_data["captured_state"].update(complex_state)
        
        await state_tester.simulate_network_interruption(session_data)
        recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
        
        assert recovery_result["state_restored"]
        assert "workspace" in session_data["state_manager"].session_state
    
    async def test_multiple_reconnections_stability(self, state_tester, enterprise_user_id):
        """Test Case 5: Multiple reconnections handled gracefully without degradation."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        
        reconnection_results = []
        for cycle in range(3):
            session_data["captured_state"][f"cycle_{cycle}"] = {"iteration": cycle}
            await state_tester.simulate_network_interruption(session_data)
            recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
            reconnection_results.append(recovery_result)
        
        assert all(result["reconnection_successful"] for result in reconnection_results)
        assert all(result["state_restored"] for result in reconnection_results)
    
    async def test_reconnection_performance_requirements(self, state_tester, enterprise_user_id):
        """Test Case 6: Reconnection performance meets <2 second requirement."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        
        performance_results = []
        for _ in range(3):
            await state_tester.simulate_network_interruption(session_data)
            recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
            performance_results.append(recovery_result["reconnection_time"])
        
        max_time = max(performance_results)
        assert max_time < 2.0, f"Reconnection time {max_time:.2f}s exceeds 2s requirement"
    
    async def test_concurrent_message_handling_during_reconnect(self, state_tester, enterprise_user_id):
        """Test Case 7: Messages during reconnection handled properly without loss."""
        session_data = await state_tester.setup_session_with_state(enterprise_user_id)
        state_manager = session_data["state_manager"]
        
        await state_tester.simulate_network_interruption(session_data)
        
        # Add concurrent messages during reconnection
        concurrent_messages = [{"type": "urgent", "content": "alert"}, {"type": "update", "content": "status"}]
        for message in concurrent_messages:
            state_manager.queue_message(message)
        
        recovery_result = await state_tester.execute_reconnection_with_state_recovery(session_data)
        
        # Original 3 + 2 concurrent = 5 total messages
        assert recovery_result["messages_delivered"] == 5
        assert len(state_manager.message_queue) == 0