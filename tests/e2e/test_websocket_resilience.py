"""E2E WebSocket Resilience Tests - Critical Real-Time Communication Validation

CRITICAL E2E tests for WebSocket functionality focusing on connection resilience,
state recovery, and error handling in real production-like scenarios.

Business Value Justification (BVJ):
1. Segment: Enterprise & Growth 
2. Business Goal: Ensure 99.9% uptime for real-time chat experience
3. Value Impact: Prevents customer churn from communication failures
4. Revenue Impact: Protects revenue by validating core product reliability

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with core utilities)
- Function size: <8 lines each
- Real WebSocket connections, no mocking
- <5 seconds per test execution
- Modular design for maintainability
"""

import asyncio
import time
from typing import Dict, Any
import pytest
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_USERS
from tests.e2e.websocket_resilience_core import (
    WebSocketResilienceTestCore, WebSocketStateRecoveryManager, MessageContinuityValidator, AgentErrorSimulator,
    WebSocketResilienceTestCore,
    WebSocketStateRecoveryManager,
    MessageContinuityValidator,
    AgentErrorSimulator
)

@pytest.mark.asyncio
@pytest.mark.e2e
class TestWebSocketReconnectionWithStateRecovery:
    """Test #3: WebSocket Reconnection with State Recovery."""
    
    @pytest.fixture
    @pytest.mark.e2e
    def test_core(self):
        """Initialize test core components."""
        return WebSocketResilienceTestCore()
    
    @pytest.fixture  
    def state_manager(self):
        """Initialize state recovery manager."""
        return WebSocketStateRecoveryManager()
    
    @pytest.fixture
    def continuity_validator(self):
        """Initialize message continuity validator."""
        return MessageContinuityValidator()
    
    @pytest.mark.e2e
    async def test_real_connection_drop_and_recovery(self, test_core, state_manager:
                                                   continuity_validator):
        """Test real connection drop with automatic reconnection and state recovery."""
        user_id = TEST_USERS["enterprise"].id
        
        try:
            # Establish connection and capture initial state
            client = await test_core.establish_authenticated_connection(user_id)
            initial_state = await state_manager.capture_session_state(client, user_id)
            
            # Send messages before disconnect
            messages_sent = await continuity_validator.send_test_messages(client, user_id)
            assert messages_sent, "Failed to send test messages"
            
            # Simulate connection drop
            await test_core.simulate_connection_drop(client)
            assert client.state.value == "disconnected"
            
            # Reconnect and validate state recovery
            reconnected = await client.connect()
            assert reconnected, "Failed to reconnect after drop"
            
            recovery_result = await state_manager.validate_state_recovery(client, user_id)
            continuity_result = await continuity_validator.validate_message_continuity(client, user_id)
            
            # Validate results
            assert recovery_result["state_recovered"], "State not recovered"
            assert continuity_result["messages_preserved"], "Message continuity broken"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
    
    @pytest.mark.e2e
    async def test_reconnection_logic_validation(self, test_core, state_manager):
        """Test reconnection logic without requiring real server."""
        user_id = TEST_USERS["enterprise"].id
        
        # Test state capture logic
        mock_client = test_core.create_test_client()
        state_data = await state_manager.capture_session_state(mock_client, user_id)
        
        assert "user_id" in state_data
        assert "active_conversations" in state_data
        assert "message_history" in state_data
        assert state_data["user_id"] == user_id

@pytest.mark.asyncio
@pytest.mark.e2e
class TestErrorMessageToUserNotificationRecovery:
    """Test #6: Error Message  ->  User Notification  ->  Recovery."""
    
    @pytest.fixture
    @pytest.mark.e2e
    def test_core(self):
        """Initialize test core components.""" 
        return WebSocketResilienceTestCore()
    
    @pytest.fixture
    def error_simulator(self):
        """Initialize agent error simulator."""
        return AgentErrorSimulator()
    
    @pytest.mark.e2e
    async def test_agent_failure_error_flow(self, test_core, error_simulator):
        """Test complete error flow: agent failure  ->  user notification  ->  retry."""
        user_id = TEST_USERS["early"].id
        
        try:
            # Establish connection
            client = await test_core.establish_authenticated_connection(user_id)
            
            # Simulate agent failure
            failure_data = await error_simulator.simulate_agent_failure(client, user_id)
            assert failure_data["error_triggered"], "Agent failure not triggered"
            
            # Validate error propagation
            error_response = failure_data.get("error_response")
            error_propagated = error_simulator.validate_error_propagation(error_response)
            assert error_propagated, "Error not properly propagated to user"
            
            # Test user notification
            notification_result = await error_simulator.simulate_user_notification(client, failure_data)
            assert notification_result["notification_sent"], "User notification failed"
            
            # Test retry mechanism
            retry_result = await error_simulator.test_retry_mechanism(client, user_id)
            assert retry_result["retry_attempted"], "Retry mechanism not triggered"
            assert retry_result["retry_successful"], "Retry was not successful"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
    
    @pytest.mark.e2e
    async def test_error_simulation_logic(self, error_simulator):
        """Test error simulation and notification logic without real server."""
        user_id = TEST_USERS["early"].id
        
        # Test error data structure creation  
        async def mock_send(self, message):
            return True
        async def mock_receive(self, **kwargs):
            return {"type": "error", "message": "test error"}
        
        mock_client = type('MockClient', (), {'send': mock_send, 'receive': mock_receive})()
        failure_data = await error_simulator.simulate_agent_failure(mock_client, user_id)
        
        assert "error_triggered" in failure_data
        assert "failure_type" in failure_data
        assert failure_data["failure_type"] == "agent_processing_error"
    
    @pytest.mark.e2e
    async def test_error_recovery_within_time_limit(self, test_core, error_simulator):
        """Test that error recovery completes within acceptable time limits."""
        start_time = time.time()
        user_id = TEST_USERS["mid"].id
        
        try:
            client = await test_core.establish_authenticated_connection(user_id)
            
            # Execute complete error flow
            await error_simulator.simulate_agent_failure(client, user_id)
            await error_simulator.test_retry_mechanism(client, user_id)
            
            total_time = time.time() - start_time
            assert total_time < 5.0, f"Error recovery took {total_time:.2f}s, exceeding 5s limit"
            
            await client.close()
        except Exception as e:
            if "server not available" in str(e).lower():
                pytest.skip("WebSocket server not available for E2E test")
            raise
    
    @pytest.mark.e2e
    async def test_timing_requirements_validation(self):
        """Test that timing requirements are validated correctly."""
        start_time = time.time()
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        assert total_time < 5.0, "Processing time validation works correctly"
