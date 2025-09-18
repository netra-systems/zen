'''
Test suite to verify the frontend message input bug fix.
Tests that messages sent via input field properly start agents.
'''

import pytest
import asyncio
import json
from typing import Dict, Any
from test_framework.utils.websocket import create_test_message, create_websocket_mock
from test_framework.mocks.websocket import WebSocketMock
from shared.isolated_environment import IsolatedEnvironment

class TestChatMessageInputFix:
    """Test that message input properly starts agents like example prompts do."""

    @pytest.fixture
    async def ws_client(self):
        """Create WebSocket test client."""
        client = WebSocketTestClient()
        await client.connect()
        yield client
        await client.disconnect()

    async def test_message_input_sends_start_agent_for_new_conversation(self, ws_client):
        """Test that typing a message in input field sends start_agent for new conversations."""
        pass
        # Simulate user typing a message in a new conversation (no thread_id)
        test_message = "Help me optimize my AI costs"

        # Send message like the input field would
        # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": test_message,
        "thread_id": None,
        "context": {"source": "message_input"},
        "settings": {}
        
        

        # Wait for agent_started event
        agent_started = await ws_client.wait_for_event("agent_started", timeout=5)
        assert agent_started is not None, "Should receive agent_started event"
        assert agent_started.get("payload", {}).get("status") == "started"

        # Wait for agent response
        agent_thinking = await ws_client.wait_for_event("agent_thinking", timeout=10)
        assert agent_thinking is not None, "Agent should start processing"

    async def test_message_input_sends_user_message_for_existing_thread(self, ws_client):
        """Test that subsequent messages use user_message type."""
            # First, start a conversation
        thread_id = "test-thread-123"
        first_message = "What is cloud optimization?"

            # Send first message (should use start_agent)
            # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": first_message,
        "thread_id": thread_id,
        "context": {"source": "message_input"},
        "settings": {}
            
            

            # Wait for agent to start
        await ws_client.wait_for_event("agent_started", timeout=5)

            # Simulate agent completion
        await asyncio.sleep(1)

            # Send follow-up message (should use user_message)
        follow_up = "Can you give me specific examples?"
            # Removed problematic line: await ws_client.send_json({)
        "type": "user_message",
        "payload": { )
        "content": follow_up,
        "references": [],
        "thread_id": thread_id
            
            

            # Should still process the message
        response = await ws_client.wait_for_event("agent_thinking", timeout=10)
        assert response is not None, "Follow-up message should be processed"

    async def test_example_prompt_behavior_matches_input(self, ws_client):
        """Test that example prompts and message input have consistent behavior."""
        pass
                Example prompt behavior (from ExamplePrompts.tsx)
        example_prompt = "Analyze my cloud infrastructure for cost optimization opportunities"

                # Send like example prompt does
                # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": example_prompt,
        "thread_id": None,
        "context": {"source": "example_prompt"},
        "settings": {}
                
                

        example_response = await ws_client.wait_for_event("agent_started", timeout=5)
        assert example_response is not None

                # Clear any pending events
        await asyncio.sleep(1)

                # Now test message input with same pattern
        input_message = "Review my AI model deployment costs"

                # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": input_message,
        "thread_id": None,
        "context": {"source": "message_input"},
        "settings": {}
                
                

        input_response = await ws_client.wait_for_event("agent_started", timeout=5)
        assert input_response is not None

                # Both should have similar response structure
        assert example_response.get("type") == input_response.get("type")
        assert "payload" in example_response and "payload" in input_response

    async def test_empty_message_not_sent(self, ws_client):
        """Test that empty or whitespace-only messages are not sent."""
                    # These should not trigger any agent activity
        invalid_messages = ["", " ", "   ", " )
        ", "\t"]

        for invalid_msg in invalid_messages:
                        # Attempt to send invalid message
                        # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": invalid_msg,
        "thread_id": None,
        "context": {"source": "message_input"},
        "settings": {}
                        
                        

                        # Should not receive agent_started within timeout
        try:
        response = await asyncio.wait_for( )
        ws_client.wait_for_event("agent_started"),
        timeout=2
                            
        assert False, "formatted_string"
        except asyncio.TimeoutError:
        pass  # Expected - no response for empty messages

    async def test_message_with_thread_switching(self, ws_client):
        """Test message sending when switching between threads."""
        pass
        thread1 = "thread-001"
        thread2 = "thread-002"

                                    # Start first thread
                                    # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": "First thread message",
        "thread_id": thread1,
        "context": {"source": "message_input"},
        "settings": {}
                                    
                                    

        await ws_client.wait_for_event("agent_started", timeout=5)

                                    # Switch to second thread (new conversation)
                                    # Removed problematic line: await ws_client.send_json({)
        "type": "start_agent",
        "payload": { )
        "user_request": "Second thread message",
        "thread_id": thread2,
        "context": {"source": "message_input"},
        "settings": {}
                                    
                                    

        response = await ws_client.wait_for_event("agent_started", timeout=5)
        assert response is not None, "Should start agent for new thread"

                                    # Go back to first thread (existing conversation)
                                    # Removed problematic line: await ws_client.send_json({)
        "type": "user_message",
        "payload": { )
        "content": "Continue first thread",
        "references": [],
        "thread_id": thread1
                                    
                                    

                                    # Should process as continuation
        thinking = await ws_client.wait_for_event("agent_thinking", timeout=10)
        assert thinking is not None, "Should continue existing thread conversation"


        if __name__ == "__main__":
        pytest.main([__file__, "-v", "--tb=short"])
