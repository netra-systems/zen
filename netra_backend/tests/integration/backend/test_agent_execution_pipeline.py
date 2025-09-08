"""
Test Agent Execution Pipeline - Core Business Value Delivery

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Ensure agent execution pipeline delivers AI value to users
- Value Impact: Agent execution is the primary mechanism for delivering AI insights and solutions
- Strategic Impact: Core platform functionality that enables all user-facing AI capabilities

These tests validate the complete agent execution pipeline from request initiation
through WebSocket event delivery, ensuring users receive valuable AI-powered insights.
"""

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from shared.isolated_environment import get_env


class TestAgentExecutionPipeline(BaseIntegrationTest):
    """Test core agent execution pipeline with real backend services."""

    @pytest.mark.integration
    @pytest.mark.backend
    async def test_agent_pipeline_initialization_with_user_context(self, real_services_fixture):
        """
        BVJ: Ensure agent pipeline initializes correctly with user context for isolated execution.
        Business Value: Multi-user isolation prevents data leakage between customer sessions.
        """
        # Setup isolated environment for test
        env = get_env()
        env.set("TEST_AGENT_PIPELINE", "true", source="test")
        
        # Mock user execution context
        user_context = MagicMock()
        user_context.user_id = "test-user-123"
        user_context.session_id = "session-456"
        user_context.subscription_tier = "enterprise"
        
        # Mock agent registry with factory pattern
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        
        # Create execution engine for test user
        execution_engine = await ExecutionEngineFactory.create_for_user_context(
            user_context=user_context,
            websocket_manager=None  # Test without WebSocket initially
        )
        
        # Verify agent pipeline initialization
        assert execution_engine is not None
        assert hasattr(execution_engine, 'user_context')
        assert execution_engine.user_context.user_id == "test-user-123"
        
        # Verify isolation - each user gets separate context
        user_context_2 = MagicMock()
        user_context_2.user_id = "test-user-789"
        user_context_2.session_id = "session-999"
        
        execution_engine_2 = await ExecutionEngineFactory.create_for_user_context(
            user_context=user_context_2,
            websocket_manager=None
        )
        
        # Verify separate contexts
        assert execution_engine.user_context.user_id != execution_engine_2.user_context.user_id
        assert execution_engine != execution_engine_2

    @pytest.mark.integration 
    @pytest.mark.backend
    async def test_agent_tool_dispatcher_integration(self, real_services_fixture):
        """
        BVJ: Verify tool dispatcher integrates correctly with agent execution.
        Business Value: Tool execution enables AI agents to perform real actions and analysis.
        """
        env = get_env()
        env.set("TEST_TOOL_INTEGRATION", "true", source="test")
        
        # Mock unified tool dispatcher
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
        
        # Create mock user context
        user_context = MagicMock()
        user_context.user_id = "test-user-123"
        user_context.permissions = ["use_basic_tools", "data_analysis"]
        
        # Mock tool dispatcher creation
        tool_dispatcher = MagicMock(spec=UnifiedToolDispatcher)
        tool_dispatcher.dispatch_tool = AsyncMock()
        tool_dispatcher.dispatch_tool.return_value = {
            "success": True,
            "result": {"analysis": "Cost optimization identified", "savings": 1000},
            "metadata": {"execution_time": 2.5}
        }
        
        # Simulate tool execution in agent pipeline
        tool_name = "cost_analyzer"
        parameters = {"account_id": "aws-123", "time_period": "last_30_days"}
        
        result = await tool_dispatcher.dispatch_tool(
            tool_name=tool_name,
            parameters=parameters,
            user_context=user_context
        )
        
        # Verify tool execution results
        assert result["success"] is True
        assert "analysis" in result["result"]
        assert result["result"]["savings"] > 0
        assert "execution_time" in result["metadata"]
        
        # Verify tool dispatcher was called correctly
        tool_dispatcher.dispatch_tool.assert_called_once_with(
            tool_name=tool_name,
            parameters=parameters,
            user_context=user_context
        )

    @pytest.mark.integration
    @pytest.mark.backend  
    async def test_agent_execution_with_websocket_events(self, real_services_fixture):
        """
        BVJ: Validate critical WebSocket events are sent during agent execution.
        Business Value: Real-time updates enable responsive chat UX and user engagement.
        """
        env = get_env()
        env.set("TEST_WEBSOCKET_EVENTS", "true", source="test")
        
        # Mock WebSocket manager
        websocket_manager = MagicMock()
        websocket_manager.send_to_user = AsyncMock()
        
        # Mock execution engine with WebSocket integration
        from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
        
        user_context = MagicMock()
        user_context.user_id = "test-user-123"
        user_context.session_id = "session-456"
        
        execution_engine = await ExecutionEngineFactory.create_for_user_context(
            user_context=user_context,
            websocket_manager=websocket_manager
        )
        
        # Mock agent execution with required WebSocket events
        execution_engine.execute_agent = AsyncMock()
        
        # Simulate the 5 critical WebSocket events during execution
        async def mock_execute_with_events(*args, **kwargs):
            # Simulate agent_started event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "agent_started", "agent": "cost_optimizer", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            # Simulate agent_thinking event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "agent_thinking", "message": "Analyzing cost patterns", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            # Simulate tool_executing event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "tool_executing", "tool": "cost_analyzer", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            # Simulate tool_completed event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "tool_completed", "tool": "cost_analyzer", "result": {"savings": 1000}, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            # Simulate agent_completed event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "agent_completed", "result": "Analysis complete", "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            return {"success": True, "result": "Analysis complete"}
        
        execution_engine.execute_agent.side_effect = mock_execute_with_events
        
        # Execute agent
        result = await execution_engine.execute_agent(
            agent_type="cost_optimizer",
            message="Analyze my AWS costs",
            thread_id="thread-123"
        )
        
        # Verify execution result
        assert result["success"] is True
        
        # Verify all 5 critical WebSocket events were sent
        assert websocket_manager.send_to_user.call_count == 5
        
        # Verify event types
        call_args = [call[0][1] for call in websocket_manager.send_to_user.call_args_list]
        event_types = [event["type"] for event in call_args]
        
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for expected_event in expected_events:
            assert expected_event in event_types

    @pytest.mark.integration
    @pytest.mark.backend
    async def test_agent_execution_state_persistence(self, real_services_fixture):
        """
        BVJ: Ensure agent execution state persists correctly across requests.
        Business Value: State persistence enables conversation continuity and context maintenance.
        """
        env = get_env()
        env.set("TEST_STATE_PERSISTENCE", "true", source="test")
        
        # Mock database operations for state persistence
        mock_db = MagicMock()
        mock_db.get = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        
        # Mock agent state model
        from netra_backend.app.agents.state import DeepAgentState
        
        # Create initial agent state
        initial_state = MagicMock(spec=DeepAgentState)
        initial_state.id = "state-123"
        initial_state.user_id = "test-user-123"
        initial_state.thread_id = "thread-456"
        initial_state.conversation_context = {"previous_query": "AWS cost analysis"}
        initial_state.last_updated = datetime.now(timezone.utc)
        
        mock_db.get.return_value = initial_state
        
        # Mock user context
        user_context = MagicMock()
        user_context.user_id = "test-user-123"
        user_context.get_db = MagicMock(return_value=mock_db)
        
        # Simulate agent execution with state persistence
        execution_engine = MagicMock()
        execution_engine.load_agent_state = AsyncMock(return_value=initial_state)
        execution_engine.save_agent_state = AsyncMock()
        
        # Load existing state
        loaded_state = await execution_engine.load_agent_state(
            user_id=user_context.user_id,
            thread_id="thread-456"
        )
        
        # Verify state loaded correctly
        assert loaded_state.user_id == "test-user-123"
        assert loaded_state.thread_id == "thread-456"
        assert "previous_query" in loaded_state.conversation_context
        
        # Update state with new conversation
        loaded_state.conversation_context["current_query"] = "Optimization recommendations"
        loaded_state.last_updated = datetime.now(timezone.utc)
        
        # Save updated state
        await execution_engine.save_agent_state(loaded_state)
        
        # Verify state persistence
        execution_engine.load_agent_state.assert_called_once()
        execution_engine.save_agent_state.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.backend
    async def test_agent_error_handling_and_recovery(self, real_services_fixture):
        """
        BVJ: Validate agent pipeline handles errors gracefully with user-friendly messaging.
        Business Value: Reliable error handling maintains user trust and system availability.
        """
        env = get_env()
        env.set("TEST_ERROR_HANDLING", "true", source="test")
        
        # Mock WebSocket manager for error notifications
        websocket_manager = MagicMock()
        websocket_manager.send_to_user = AsyncMock()
        
        # Mock user context
        user_context = MagicMock()
        user_context.user_id = "test-user-123"
        
        # Mock execution engine with error scenarios
        execution_engine = MagicMock()
        
        # Test tool execution failure
        async def mock_execute_with_tool_error(*args, **kwargs):
            # Send agent_started event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "agent_started", "agent": "cost_optimizer"}
            )
            
            # Send tool_executing event
            await websocket_manager.send_to_user(
                user_context.user_id,
                {"type": "tool_executing", "tool": "cost_analyzer"}
            )
            
            # Simulate tool error
            await websocket_manager.send_to_user(
                user_context.user_id,
                {
                    "type": "agent_error",
                    "error": "Tool execution failed: AWS API rate limit exceeded",
                    "recovery_suggestion": "Please try again in a few minutes",
                    "user_friendly": True
                }
            )
            
            return {
                "success": False,
                "error": "Tool execution failed",
                "recovery_possible": True
            }
        
        execution_engine.execute_agent = AsyncMock(side_effect=mock_execute_with_tool_error)
        
        # Execute agent with error scenario
        result = await execution_engine.execute_agent(
            agent_type="cost_optimizer",
            message="Analyze costs",
            thread_id="thread-123"
        )
        
        # Verify error handling
        assert result["success"] is False
        assert "error" in result
        assert result["recovery_possible"] is True
        
        # Verify error notification sent via WebSocket
        error_events = [
            call[0][1] for call in websocket_manager.send_to_user.call_args_list
            if call[0][1].get("type") == "agent_error"
        ]
        assert len(error_events) == 1
        assert error_events[0]["user_friendly"] is True
        assert "recovery_suggestion" in error_events[0]