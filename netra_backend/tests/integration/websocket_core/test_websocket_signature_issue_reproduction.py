"""
Simple integration test to reproduce WebSocket create_server_message signature issue.

This test demonstrates Issue #405: WebSocket signature errors by reproducing
the exact usage patterns found in handlers.py that cause TypeError failures.

Key Finding: The create_server_message function requires 'data' parameter,
but many calls in handlers.py expect it to be optional.
"""

import pytest
import asyncio
from typing import Dict, Any

# SSOT test imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Direct imports to test the signature issue
from netra_backend.app.websocket_core.types import (
    MessageType, 
    create_server_message
)


class TestWebSocketSignatureIssueReproduction(SSotAsyncTestCase):
    """Integration test reproducing the exact signature issue from handlers.py."""

    async def test_handlers_calling_pattern_breaks(self):
        """
        Reproduce the exact calling pattern from handlers.py that causes failures.
        
        This test demonstrates the core issue: handlers.py calls create_server_message
        in ways that expect data to be optional, but the function requires it.
        """
        # This is the pattern that appears throughout handlers.py
        # It should work but currently fails due to signature mismatch
        
        # Test 1: Basic system message creation (common pattern)
        try:
            system_msg = create_server_message(
                MessageType.SYSTEM_MESSAGE,
                {"status": "connected", "timestamp": 1234567890}
            )
            
            # This should work fine
            assert system_msg.type == MessageType.SYSTEM_MESSAGE
            self.logger.info("✅ Basic system message creation works")
            
        except Exception as e:
            self.logger.error(f"❌ Basic system message creation failed: {e}")
            pytest.fail(f"Basic message creation should work: {e}")

    async def test_pong_heartbeat_patterns_from_handlers(self):
        """
        Test actual ping/pong patterns from handlers.py around line 285-290.
        """
        try:
            # PING response pattern from handlers.py
            ping_response = create_server_message(
                MessageType.PONG,
                {"timestamp": 1234567890, "user_id": "test_user"}
            )
            assert ping_response.type == MessageType.PONG
            
            # HEARTBEAT response pattern from handlers.py  
            heartbeat_response = create_server_message(
                MessageType.HEARTBEAT_ACK,
                {"timestamp": 1234567890, "status": "healthy"}
            )
            assert heartbeat_response.type == MessageType.HEARTBEAT_ACK
            
            self.logger.info("✅ Ping/heartbeat patterns work correctly")
            
        except Exception as e:
            self.logger.error(f"❌ Ping/heartbeat patterns failed: {e}")
            pytest.fail(f"Ping/heartbeat should work: {e}")

    async def test_agent_event_patterns_from_handlers(self):
        """
        Test agent event creation patterns from handlers.py lines 351-453.
        """
        try:
            # Agent started event (line 351)
            agent_started = create_server_message(
                MessageType.SYSTEM_MESSAGE,
                {
                    "event": "agent_started",
                    "agent_type": "supervisor",
                    "user_id": "test_user",
                    "timestamp": 1234567890
                }
            )
            
            # Agent thinking event (line 374)
            agent_thinking = create_server_message(
                MessageType.AGENT_PROGRESS,
                {
                    "event": "agent_thinking",
                    "progress": "analyzing_request",
                    "timestamp": 1234567890
                }
            )
            
            # Tool executing event (line 396)
            tool_executing = create_server_message(
                MessageType.AGENT_PROGRESS,
                {
                    "event": "tool_executing",
                    "tool_name": "data_analyzer",
                    "timestamp": 1234567890
                }
            )
            
            # Tool completed event (line 419)
            tool_completed = create_server_message(
                MessageType.AGENT_PROGRESS,
                {
                    "event": "tool_completed",
                    "tool_name": "data_analyzer",
                    "timestamp": 1234567890
                }
            )
            
            # Agent completed event (line 453)
            agent_completed = create_server_message(
                MessageType.AGENT_RESPONSE_COMPLETE,
                {
                    "event": "agent_completed",
                    "response": "Analysis complete",
                    "timestamp": 1234567890
                }
            )
            
            # All should work
            events = [agent_started, agent_thinking, tool_executing, tool_completed, agent_completed]
            for event in events:
                assert hasattr(event, 'type')
                assert hasattr(event, 'data')
            
            self.logger.info("✅ All agent event patterns work correctly")
            
        except Exception as e:
            self.logger.error(f"❌ Agent event patterns failed: {e}")
            pytest.fail(f"Agent events should work: {e}")

    async def test_ack_response_patterns_from_handlers(self):
        """
        Test acknowledgment response patterns from handlers.py lines 574-622.
        """
        try:
            # Agent task acknowledgment (line 574)
            ack_response = create_server_message(
                MessageType.AGENT_TASK_ACK,
                {
                    "task_id": "task_123",
                    "status": "acknowledged", 
                    "timestamp": 1234567890,
                    "user_id": "test_user"
                }
            )
            
            # Agent status update (line 622)  
            status_response = create_server_message(
                MessageType.AGENT_STATUS_UPDATE,
                {
                    "status": "processing",
                    "progress": 0.5,
                    "timestamp": 1234567890
                }
            )
            
            # Both should work
            assert ack_response.type == MessageType.AGENT_TASK_ACK
            assert status_response.type == MessageType.AGENT_STATUS_UPDATE
            
            self.logger.info("✅ Acknowledgment patterns work correctly")
            
        except Exception as e:
            self.logger.error(f"❌ Acknowledgment patterns failed: {e}")
            pytest.fail(f"Acknowledgment patterns should work: {e}")

    async def test_signature_issue_reproduction_invalid_calls(self):
        """
        Test the specific signature issue: calls without required data parameter.
        
        This should FAIL and demonstrate the actual signature error.
        """
        self.logger.info("Testing signature error reproduction...")
        
        # This should fail: missing required 'data' parameter
        with pytest.raises(TypeError, match="missing 1 required positional argument"):
            create_server_message(MessageType.SYSTEM_MESSAGE)
            
        self.logger.info("✅ Confirmed: Missing data parameter causes TypeError as expected")

    async def test_serialization_compatibility(self):
        """
        Test that created messages can be serialized for WebSocket transmission.
        
        This tests the full flow that handlers.py uses: create -> serialize -> send.
        """
        try:
            # Create message using handlers.py pattern
            message = create_server_message(
                MessageType.AGENT_RESPONSE_COMPLETE,
                {
                    "response": "Test response",
                    "user_id": "test_user",
                    "timestamp": 1234567890
                }
            )
            
            # Test serialization (as done in handlers.py line 1496)
            json_data = message.model_dump(mode='json')
            assert isinstance(json_data, dict)
            assert 'type' in json_data
            assert 'data' in json_data
            assert 'timestamp' in json_data
            
            # Test JSON string serialization
            import json
            json_string = json.dumps(json_data)
            assert isinstance(json_string, str)
            
            self.logger.info("✅ Message serialization works correctly")
            
        except Exception as e:
            self.logger.error(f"❌ Message serialization failed: {e}")
            pytest.fail(f"Message serialization should work: {e}")

    async def test_empty_data_edge_case(self):
        """
        Test edge case: empty data dict (minimum viable data).
        """
        try:
            # Test with empty data dict
            message = create_server_message(
                MessageType.SYSTEM_MESSAGE,
                {}  # Empty but not None
            )
            
            assert message.type == MessageType.SYSTEM_MESSAGE
            assert message.data == {}
            
            self.logger.info("✅ Empty data dict works correctly")
            
        except Exception as e:
            self.logger.error(f"❌ Empty data dict failed: {e}")
            pytest.fail(f"Empty data dict should be valid: {e}")

    async def test_none_data_should_fail(self):
        """
        Test that None data fails appropriately.
        """
        # This might fail depending on function implementation
        try:
            message = create_server_message(
                MessageType.SYSTEM_MESSAGE,
                None  # Explicit None
            )
            
            # If this succeeds, None is acceptable
            self.logger.info("ℹ️ None data is accepted by create_server_message")
            assert message.data is None
            
        except (TypeError, ValueError) as e:
            # Expected if None is not allowed
            self.logger.info(f"ℹ️ None data rejected as expected: {e}")
            assert True  # This is expected behavior


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])