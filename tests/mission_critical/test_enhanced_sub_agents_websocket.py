#!/usr/bin/env python
"""Test enhanced sub-agents WebSocket notifications

Test that the enhanced sub-agents (triage, data, reporting) are properly 
sending WebSocket notifications during their execution.
"""

import asyncio
import os
import sys
import time
import uuid
from typing import Dict, List, Any

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import AsyncMock, MagicMock

# Import sub-agents
from netra_backend.app.agents.triage_sub_agent.agent import TriageSubAgent
from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent 
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.messages: List[Dict] = []
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Record message for validation."""
        self.messages.append({
            'thread_id': thread_id,
            'message': message,
            'event_type': message.get('type', 'unknown'),
            'timestamp': time.time()
        })
        return True
    
    def get_event_types(self, thread_id: str) -> List[str]:
        """Get event types for thread."""
        return [msg['event_type'] for msg in self.messages if msg['thread_id'] == thread_id]
    
    def clear_messages(self):
        """Clear recorded messages."""
        self.messages.clear()


class TestEnhancedSubAgentWebSocket:
    """Test WebSocket notifications in enhanced sub-agents."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment with mock services."""
        # Mock WebSocket manager
        self.mock_ws_manager = MockWebSocketManager()
        
        # Mock LLM manager
        self.mock_llm_manager = AsyncMock(spec=LLMManager)
        
        # Mock tool dispatcher
        self.mock_tool_dispatcher = MagicMock(spec=ToolDispatcher)
        
        yield
        
        # Cleanup
        self.mock_ws_manager.clear_messages()
    
    def _create_test_state(self, user_request: str = "Test request") -> DeepAgentState:
        """Create test state for sub-agent execution."""
        state = DeepAgentState()
        state.user_request = user_request
        state.user_id = "test-user"
        state.chat_thread_id = "test-thread"
        return state
    
    @pytest.mark.asyncio
    async def test_triage_sub_agent_websocket_notifications(self):
        """Test triage sub-agent sends WebSocket notifications."""
        # Create triage sub-agent with WebSocket manager
        agent = TriageSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_manager=self.mock_ws_manager
        )
        
        # Mock the executor to avoid complex dependencies
        agent.executor.execute_triage_workflow = AsyncMock()
        
        # Create test state
        state = self._create_test_state("What's the system status?")
        run_id = str(uuid.uuid4())
        
        # Execute with WebSocket notifications enabled
        await agent.execute(state, run_id, stream_updates=True)
        
        # Verify WebSocket events were sent
        event_types = self.mock_ws_manager.get_event_types("test-thread")
        
        assert "agent_started" in event_types, f"No agent_started event. Got: {event_types}"
        assert "agent_thinking" in event_types, f"No agent_thinking event. Got: {event_types}"
        assert "agent_completed" in event_types, f"No agent_completed event. Got: {event_types}"
        
        # Verify we got multiple thinking notifications
        thinking_count = event_types.count("agent_thinking")
        assert thinking_count >= 1, f"Expected at least 1 thinking event, got {thinking_count}"
    
    @pytest.mark.asyncio
    async def test_data_sub_agent_websocket_notifications(self):
        """Test data sub-agent sends WebSocket notifications."""
        # Create data sub-agent with WebSocket manager
        agent = DataSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_manager=self.mock_ws_manager
        )
        
        # Mock core execute method to avoid database dependencies
        agent.core.execute_data_analysis = AsyncMock(return_value={"status": "success", "data": []})
        
        # Create test state
        state = self._create_test_state("Analyze performance metrics")
        run_id = str(uuid.uuid4())
        
        # Test modern execution pattern (which includes WebSocket notifications)
        result = await agent.execute_with_modern_patterns(state, run_id, stream_updates=True)
        
        # Verify WebSocket events were sent
        event_types = self.mock_ws_manager.get_event_types("test-thread")
        
        assert "agent_started" in event_types, f"No agent_started event. Got: {event_types}"
        assert "agent_thinking" in event_types, f"No agent_thinking event. Got: {event_types}"
        assert "agent_completed" in event_types, f"No agent_completed event. Got: {event_types}"
        
        # Verify execution was successful
        assert result.success, "Data sub-agent execution should succeed"
    
    @pytest.mark.asyncio
    async def test_reporting_sub_agent_websocket_notifications(self):
        """Test reporting sub-agent sends WebSocket notifications."""
        # Create reporting sub-agent with WebSocket manager
        agent = ReportingSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_manager=self.mock_ws_manager
        )
        
        # Mock reliability wrapper to avoid complex LLM dependencies
        agent.reliability.execute_safely = AsyncMock()
        
        # Create test state with all required results
        state = self._create_test_state("Generate final report")
        state.triage_result = {"category": "optimization", "confidence": 0.9}
        state.data_result = {"metrics": {"cpu": 85, "memory": 70}}
        state.action_plan_result = {"recommendations": ["optimize db"]}
        state.optimizations_result = {"applied": ["index_optimization"]}
        
        run_id = str(uuid.uuid4())
        
        # Execute with WebSocket notifications
        await agent.execute(state, run_id, stream_updates=True)
        
        # Verify WebSocket events were sent
        event_types = self.mock_ws_manager.get_event_types("test-thread")
        
        assert "agent_started" in event_types, f"No agent_started event. Got: {event_types}"
        assert "agent_thinking" in event_types, f"No agent_thinking event. Got: {event_types}"
        
        # Verify multiple thinking notifications (from different stages)
        thinking_count = event_types.count("agent_thinking")
        assert thinking_count >= 2, f"Expected at least 2 thinking events for report generation, got {thinking_count}"
    
    @pytest.mark.asyncio
    async def test_data_sub_agent_tool_notifications(self):
        """Test data sub-agent sends tool execution notifications."""
        # Create data sub-agent with WebSocket manager
        agent = DataSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_manager=self.mock_ws_manager
        )
        
        # Mock the helper to return sample data
        agent.helpers.fetch_clickhouse_data = AsyncMock(return_value=[
            {"event_count": 100, "latency_p50": 50, "avg_throughput": 1000}
        ])
        
        # Create test state and setup context
        state = self._create_test_state()
        agent._current_run_id = "test-run"
        agent._current_thread_id = "test-thread"
        
        # Call _fetch_clickhouse_data which should send tool notifications
        result = await agent._fetch_clickhouse_data(
            "SELECT * FROM test_metrics", 
            cache_key="test_cache"
        )
        
        # Verify tool execution events were sent
        event_types = self.mock_ws_manager.get_event_types("test-thread")
        
        assert "tool_executing" in event_types, f"No tool_executing event. Got: {event_types}"
        assert "tool_completed" in event_types, f"No tool_completed event. Got: {event_types}"
        
        # Verify result was returned
        assert result is not None, "Should return query result"
        assert len(result) == 1, "Should return one row of test data"
    
    @pytest.mark.asyncio 
    async def test_enhanced_agents_error_handling_with_websocket(self):
        """Test enhanced agents send error notifications on failure."""
        # Test triage agent error handling
        agent = TriageSubAgent(
            llm_manager=self.mock_llm_manager,
            tool_dispatcher=self.mock_tool_dispatcher,
            websocket_manager=self.mock_ws_manager
        )
        
        # Mock executor to raise an error
        agent.executor.execute_triage_workflow = AsyncMock(side_effect=Exception("Test error"))
        
        state = self._create_test_state("Test request")
        run_id = str(uuid.uuid4())
        
        # Execute should raise error but send WebSocket notifications
        with pytest.raises(Exception, match="Test error"):
            await agent.execute(state, run_id, stream_updates=True)
        
        # Verify error notification was sent
        event_types = self.mock_ws_manager.get_event_types("test-thread")
        
        assert "agent_started" in event_types, "Should send start even on error"
        assert "agent_failed" in event_types, f"Should send error notification. Got: {event_types}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])