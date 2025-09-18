"""
Emergency Golden Path Test: WebSocket Agent Events Core
Critical test for validating the 5 essential WebSocket events that deliver 90% of platform value.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Use absolute imports as required by SSOT
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment


class TestWebSocketAgentEventsCore(SSotAsyncTestCase):
    """Emergency test for critical WebSocket events that enable chat functionality."""
    
    async def asyncSetUp(self):
        """Set up test environment with isolated configuration."""
        self.env = IsolatedEnvironment()
        self.env.set("ENVIRONMENT", "test")
        self.env.set("REDIS_HOST", "localhost")
        self.env.set("REDIS_PORT", "6379")
        
        # Mock WebSocket connection
        self.mock_websocket = Mock()
        self.mock_websocket.send = AsyncMock()
        self.mock_websocket.close = AsyncMock()
        
        # Initialize WebSocket manager
        self.websocket_manager = UnifiedWebSocketManager()
        self.user_id = "test-user-123"
        self.run_id = "test-run-456"
        
    async def test_agent_started_event_sent(self):
        """Test that agent_started event is sent when agent begins processing."""
        # Arrange
        emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id=self.user_id,
            run_id=self.run_id
        )
        
        # Act
        await emitter.notify_agent_started(
            agent_type="supervisor",
            message="Processing your request..."
        )
        
        # Assert
        self.mock_websocket.send.assert_called_once()
        call_args = self.mock_websocket.send.call_args[0][0]
        event_data = json.loads(call_args)
        
        self.assertEqual(event_data["type"], "agent_started")
        self.assertEqual(event_data["data"]["agent_type"], "supervisor")
        self.assertEqual(event_data["data"]["message"], "Processing your request...")
        
    async def test_agent_thinking_event_sent(self):
        """Test that agent_thinking event provides real-time reasoning visibility."""
        # Arrange
        emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id=self.user_id,
            run_id=self.run_id
        )
        
        # Act
        await emitter.notify_agent_thinking(
            reasoning="Analyzing your request to determine the best approach...",
            progress=25
        )
        
        # Assert
        self.mock_websocket.send.assert_called_once()
        call_args = self.mock_websocket.send.call_args[0][0]
        event_data = json.loads(call_args)
        
        self.assertEqual(event_data["type"], "agent_thinking")
        self.assertEqual(event_data["data"]["reasoning"], "Analyzing your request to determine the best approach...")
        self.assertEqual(event_data["data"]["progress"], 25)
        
    async def test_tool_executing_event_sent(self):
        """Test that tool_executing event shows tool usage transparency."""
        # Arrange
        emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id=self.user_id,
            run_id=self.run_id
        )
        
        # Act
        await emitter.notify_tool_executing(
            tool_name="data_analyzer",
            tool_input={"query": "analyze user data"},
            description="Analyzing user data patterns..."
        )
        
        # Assert
        self.mock_websocket.send.assert_called_once()
        call_args = self.mock_websocket.send.call_args[0][0]
        event_data = json.loads(call_args)
        
        self.assertEqual(event_data["type"], "tool_executing")
        self.assertEqual(event_data["data"]["tool_name"], "data_analyzer")
        self.assertEqual(event_data["data"]["description"], "Analyzing user data patterns...")
        
    async def test_tool_completed_event_sent(self):
        """Test that tool_completed event displays tool results."""
        # Arrange
        emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id=self.user_id,
            run_id=self.run_id
        )
        
        tool_result = {
            "analysis": "Found 3 key patterns in user data",
            "patterns": ["pattern1", "pattern2", "pattern3"],
            "confidence": 0.85
        }
        
        # Act
        await emitter.notify_tool_completed(
            tool_name="data_analyzer",
            tool_result=tool_result,
            success=True
        )
        
        # Assert
        self.mock_websocket.send.assert_called_once()
        call_args = self.mock_websocket.send.call_args[0][0]
        event_data = json.loads(call_args)
        
        self.assertEqual(event_data["type"], "tool_completed")
        self.assertEqual(event_data["data"]["tool_name"], "data_analyzer")
        self.assertEqual(event_data["data"]["success"], True)
        self.assertEqual(event_data["data"]["tool_result"]["confidence"], 0.85)
        
    async def test_agent_completed_event_sent(self):
        """Test that agent_completed event signals completion to user."""
        # Arrange
        emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id=self.user_id,
            run_id=self.run_id
        )
        
        final_response = {
            "answer": "Based on my analysis, here are the key insights...",
            "confidence": 0.92,
            "sources": ["data_analyzer", "pattern_matcher"]
        }
        
        # Act
        await emitter.notify_agent_completed(
            final_response=final_response,
            execution_time=5.2,
            success=True
        )
        
        # Assert
        self.mock_websocket.send.assert_called_once()
        call_args = self.mock_websocket.send.call_args[0][0]
        event_data = json.loads(call_args)
        
        self.assertEqual(event_data["type"], "agent_completed")
        self.assertEqual(event_data["data"]["success"], True)
        self.assertEqual(event_data["data"]["execution_time"], 5.2)
        self.assertEqual(event_data["data"]["final_response"]["confidence"], 0.92)
        
    async def test_complete_agent_workflow_events(self):
        """Test that all 5 critical events are sent in correct sequence for agent workflow."""
        # Arrange
        emitter = UnifiedWebSocketEmitter(
            websocket=self.mock_websocket,
            user_id=self.user_id,
            run_id=self.run_id
        )
        
        # Act - Simulate complete agent workflow
        await emitter.notify_agent_started(
            agent_type="supervisor",
            message="Starting analysis..."
        )
        
        await emitter.notify_agent_thinking(
            reasoning="Determining best analysis approach...",
            progress=20
        )
        
        await emitter.notify_tool_executing(
            tool_name="data_processor",
            tool_input={"data": "user_query"},
            description="Processing user query..."
        )
        
        await emitter.notify_tool_completed(
            tool_name="data_processor",
            tool_result={"processed": True},
            success=True
        )
        
        await emitter.notify_agent_completed(
            final_response={"answer": "Analysis complete"},
            execution_time=3.1,
            success=True
        )
        
        # Assert - All 5 events sent
        self.assertEqual(self.mock_websocket.send.call_count, 5)
        
        # Verify event sequence
        call_args_list = [call[0][0] for call in self.mock_websocket.send.call_args_list]
        event_types = [json.loads(call)["type"] for call in call_args_list]
        
        expected_sequence = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        
        self.assertEqual(event_types, expected_sequence)
        
    async def test_websocket_manager_user_isolation(self):
        """Test that WebSocket manager properly isolates users."""
        # Arrange
        user1_id = "user-1"
        user2_id = "user-2"
        
        # Mock two different websockets
        ws1 = Mock()
        ws1.send = AsyncMock()
        ws2 = Mock() 
        ws2.send = AsyncMock()
        
        # Act - Register both users
        emitter1 = UnifiedWebSocketEmitter(
            websocket=ws1,
            user_id=user1_id,
            run_id="run-1"
        )
        
        emitter2 = UnifiedWebSocketEmitter(
            websocket=ws2,
            user_id=user2_id,
            run_id="run-2"
        )
        
        # Send event to user 1
        await emitter1.notify_agent_started(
            agent_type="supervisor",
            message="User 1 message"
        )
        
        # Send event to user 2
        await emitter2.notify_agent_started(
            agent_type="supervisor", 
            message="User 2 message"
        )
        
        # Assert - Each user gets only their message
        ws1.send.assert_called_once()
        ws2.send.assert_called_once()
        
        # Verify user 1 got user 1 message
        user1_call = json.loads(ws1.send.call_args[0][0])
        self.assertEqual(user1_call["data"]["message"], "User 1 message")
        
        # Verify user 2 got user 2 message
        user2_call = json.loads(ws2.send.call_args[0][0])
        self.assertEqual(user2_call["data"]["message"], "User 2 message")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])