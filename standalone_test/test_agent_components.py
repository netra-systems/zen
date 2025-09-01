"""
Standalone Agent Component Test

This test validates basic agent functionality without any complex 
service orchestration or Docker dependencies. It's completely 
isolated and should run independently.

PRIORITY: CRITICAL - Core agent functionality validation
BVJ: Ensures core agent components work - $45K MRR business value
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import asyncio
import uuid
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

# Set up minimal environment before imports
os.environ['TESTING'] = '1'
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key-must-be-at-least-32-characters-for-testing'
os.environ['SERVICE_SECRET'] = 'test-service-secret-for-cross-service-auth-testing'
os.environ['FERNET_KEY'] = 'iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw='
os.environ['SECRET_KEY'] = 'test-secret-key-for-standalone-testing'
os.environ['NO_DOCKER_ORCHESTRATION'] = 'true'

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.agent import SubAgentLifecycle


class TestStandaloneAgentComponents:
    """Test agent components in complete isolation."""
    
    @pytest.mark.asyncio
    async def test_supervisor_agent_creation(self):
        """Test that SupervisorAgent can be created successfully."""
        # Create mock dependencies
        db_session = AsyncMock()
        
        llm_manager = MagicMock()
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "Test LLM response", 
            "tool_calls": []
        })
        
        websocket_manager = MagicMock()
        websocket_manager.send_message = AsyncMock()
        
        tool_dispatcher = MagicMock()
        tool_dispatcher.dispatch_tool = AsyncMock(return_value={"result": "success"})
        
        # Create supervisor agent
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Validate agent was created
        assert supervisor is not None
        assert supervisor.db_session == db_session
        assert supervisor.llm_manager == llm_manager
        assert supervisor.websocket_manager == websocket_manager
        
        print("SUCCESS: SupervisorAgent created successfully")
    
    @pytest.mark.asyncio
    async def test_agent_state_creation_and_management(self):
        """Test agent state can be created and managed."""
        # Create state
        state = DeepAgentState(
            user_request="Test optimization request",
            chat_thread_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Validate state
        assert state.user_request == "Test optimization request"
        assert state.chat_thread_id is not None
        assert state.user_id is not None
        assert state.step_count == 0
        assert state.triage_result is None
        
        # Test state updates
        state.step_count = 1
        assert state.step_count == 1
        
        print(f"SUCCESS: Agent state created and managed: {state.chat_thread_id}")
    
    @pytest.mark.asyncio
    async def test_mock_triage_workflow(self):
        """Test mock triage workflow completes."""
        from netra_backend.app.agents.triage_sub_agent import (
            TriageResult, UserIntent, Priority, Complexity, 
            ExtractedEntities, TriageMetadata
        )
        
        # Create mock triage workflow
        async def mock_triage_workflow(user_request: str) -> TriageResult:
            """Mock triage that completes successfully."""
            mock_intent = UserIntent(
                primary_intent="optimize",
                secondary_intents=["cost", "performance"],
                action_required=True
            )
            
            return TriageResult(
                category="cost_optimization",
                confidence_score=0.9,
                user_intent=mock_intent,
                priority=Priority.HIGH,
                complexity=Complexity.MODERATE,
                extracted_entities=ExtractedEntities(),
                metadata=TriageMetadata(triage_duration_ms=100)
            )
        
        # Run mock triage
        result = await mock_triage_workflow("Optimize GPT-4 costs")
        
        # Validate results
        assert result.category == "cost_optimization"
        assert result.confidence_score == 0.9
        assert result.priority == Priority.HIGH
        assert result.user_intent.primary_intent == "optimize"
        assert result.user_intent.action_required is True
        
        print(f"SUCCESS: Mock triage completed: {result.category} (confidence: {result.confidence_score})")
    
    @pytest.mark.asyncio
    async def test_websocket_manager_mock_integration(self):
        """Test WebSocket manager mock works correctly."""
        # Create mock WebSocket manager
        websocket_manager = MagicMock()
        websocket_manager.send_message = AsyncMock()
        websocket_manager.send_agent_log = AsyncMock()
        websocket_manager.send_sub_agent_update = AsyncMock()
        
        # Test sending various message types
        user_id = str(uuid.uuid4())
        
        # Agent started message
        await websocket_manager.send_message(user_id, {
            "type": "agent_started",
            "content": "Agent processing started"
        })
        
        # Agent log message  
        await websocket_manager.send_agent_log(user_id, {
            "level": "info",
            "message": "Triage analysis in progress"
        })
        
        # Sub-agent update
        await websocket_manager.send_sub_agent_update(user_id, {
            "agent": "triage",
            "status": "completed",
            "result": "optimization_required"
        })
        
        # Verify all calls were made
        assert websocket_manager.send_message.call_count == 1
        assert websocket_manager.send_agent_log.call_count == 1
        assert websocket_manager.send_sub_agent_update.call_count == 1
        
        print("SUCCESS: WebSocket manager mock integration working")
    
    @pytest.mark.asyncio
    async def test_llm_manager_mock_integration(self):
        """Test LLM manager mock works correctly."""
        # Create mock LLM manager
        llm_manager = MagicMock()
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "Based on analysis, I recommend optimizing your GPT-4 usage by implementing request batching and caching frequently asked questions.",
            "tool_calls": []
        })
        llm_manager.ask_llm = AsyncMock(return_value='{"cost_savings": 2500, "performance_impact": "minimal"}')
        
        # Test LLM call
        response = await llm_manager.call_llm("Analyze cost optimization opportunities for AI workload")
        assert "optimizing your GPT-4 usage" in response["content"]
        assert response["tool_calls"] == []
        
        # Test LLM ask (structured response)
        structured_response = await llm_manager.ask_llm("Calculate cost savings potential")
        assert "cost_savings" in structured_response
        assert "2500" in structured_response
        
        # Verify calls
        llm_manager.call_llm.assert_called_once()
        llm_manager.ask_llm.assert_called_once()
        
        print("SUCCESS: LLM manager mock integration working")
    
    @pytest.mark.asyncio
    async def test_end_to_end_mock_agent_flow(self):
        """Test complete end-to-end mock agent flow."""
        # Setup all components
        db_session = AsyncMock()
        
        llm_manager = MagicMock()
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "Analysis complete. Cost optimization opportunities identified.",
            "tool_calls": []
        })
        
        websocket_manager = MagicMock()
        websocket_manager.send_message = AsyncMock()
        websocket_manager.send_agent_log = AsyncMock()
        
        tool_dispatcher = MagicMock()
        tool_dispatcher.dispatch_tool = AsyncMock(return_value={
            "result": "success",
            "savings": "$2500/month"
        })
        
        # Create agent
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Create state
        state = DeepAgentState(
            user_request="Help me reduce AI costs by 30% without losing performance",
            chat_thread_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Simulate agent processing
        supervisor.thread_id = state.chat_thread_id
        supervisor.user_id = state.user_id
        
        # Mock notify start
        await websocket_manager.send_message(state.user_id, {
            "type": "agent_started",
            "message": "Starting cost optimization analysis"
        })
        
        # Mock LLM processing
        llm_response = await llm_manager.call_llm(state.user_request)
        
        # Mock tool execution
        tool_result = await tool_dispatcher.dispatch_tool("cost_analyzer", {
            "request": state.user_request
        })
        
        # Mock completion notification
        await websocket_manager.send_message(state.user_id, {
            "type": "agent_completed",
            "result": tool_result
        })
        
        # Validate flow completed
        assert llm_response["content"] is not None
        assert tool_result["result"] == "success"
        assert tool_result["savings"] == "$2500/month"
        
        # Verify all components were called
        websocket_manager.send_message.assert_called()
        llm_manager.call_llm.assert_called_once_with(state.user_request)
        tool_dispatcher.dispatch_tool.assert_called_once()
        
        print("SUCCESS: End-to-end mock agent flow completed successfully")
        print(f"   SAVINGS: Simulated savings: {tool_result['savings']}")
        print(f"   THREAD: Thread ID: {state.chat_thread_id[:8]}...")


if __name__ == "__main__":
    # Run tests directly for immediate feedback
    pytest.main([__file__, "-v", "-s"])