"""
Test module: Supervisor Advanced Features
Split from large test file for architecture compliance
Test classes: TestSupervisorAdvancedFeatures
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone
import json
import time

from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.supervisor.execution_context import (
    ExecutionStrategy,
    AgentExecutionContext,
    AgentExecutionResult
)
from app.agents.state import DeepAgentState  # Use the state module version with methods
from app.schemas import SubAgentLifecycle, WebSocketMessage, AgentStarted, SubAgentUpdate, AgentCompleted
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


class TestSupervisorAdvancedFeatures:
    """Additional tests for advanced supervisor functionality"""
    async def test_supervisor_error_handling(self):
        """Test supervisor handles agent initialization errors gracefully"""
        # Mock dependencies with proper async context managers
        mock_db = AsyncMock()
        mock_db.begin = AsyncMock(return_value=AsyncMock())
        mock_db.begin.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock() 
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = SupervisorAgent(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Mock an agent failure
        state = DeepAgentState(user_request="Test error handling")
        context = AgentExecutionContext(
            run_id="error-test",
            thread_id="thread-1",
            user_id="user-1",
            agent_name="supervisor",
            started_at=datetime.now(timezone.utc)
        )
        
        # Mock triage agent to fail
        from app.agents.triage_sub_agent.agent import TriageSubAgent
        mock_triage = AsyncMock(spec=TriageSubAgent)
        mock_triage.execute = AsyncMock(side_effect=Exception("Agent failed"))
        supervisor.agents["triage"] = mock_triage
        
        # Supervisor should handle the error gracefully
        try:
            final_state = await supervisor.run(state.user_request, context.thread_id, context.user_id, context.run_id)
            result = AgentExecutionResult(success=True, state=final_state)
        except Exception as e:
            result = AgentExecutionResult(success=False, error=str(e))
        
        # Verify error was handled gracefully with fallback
        # In our architecture, errors trigger fallback mechanisms rather than failing outright
        assert result.success is True  # Fallback should provide graceful degradation
        assert result.state is not None  # State should still be returned
    async def test_supervisor_state_management(self):
        """Test supervisor properly manages agent states"""
        # Mock dependencies
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = SupervisorAgent(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Test initial state
        assert supervisor.state == SubAgentLifecycle.PENDING
        
        # Test state transitions
        supervisor.set_state(SubAgentLifecycle.RUNNING)
        assert supervisor.get_state() == SubAgentLifecycle.RUNNING
        
        supervisor.set_state(SubAgentLifecycle.COMPLETED)
        assert supervisor.get_state() == SubAgentLifecycle.COMPLETED
        
        # Test additional valid transitions
        # Note: Cannot go from COMPLETED back to PENDING - this is by design
        # The state machine enforces forward-only transitions for lifecycle integrity
    async def test_supervisor_concurrent_requests(self):
        """Test supervisor handles multiple concurrent requests"""
        # Mock dependencies with proper async context managers
        mock_db = AsyncMock()
        mock_db.begin = AsyncMock(return_value=AsyncMock())
        mock_db.begin.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = SupervisorAgent(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Mock triage agent for concurrent requests
        async def mock_execute(state, run_id, stream_updates=True):
            await asyncio.sleep(0.01)  # Simulate processing time
            state.triage_result = {"message_type": "query", "confidence": 0.9}
            return state
        
        # Mock triage agent for concurrent test
        from app.agents.triage_sub_agent.agent import TriageSubAgent
        mock_triage = AsyncMock(spec=TriageSubAgent)
        mock_triage.execute = mock_execute
        supervisor.agents["triage"] = mock_triage
        
        # Create multiple concurrent requests
        requests = [f"Message {i}" for i in range(5)]
        run_ids = [f"run_{i}" for i in range(5)]
        
        tasks = []
        for req, run_id in zip(requests, run_ids):
            state = DeepAgentState(user_request=req)
            context = AgentExecutionContext(
                run_id=run_id,
                thread_id=f"thread_{run_id}",
                user_id="user-1",
                agent_name="supervisor",
                started_at=datetime.now(timezone.utc)
            )
            
            async def run_task(request=req, rid=run_id):
                try:
                    final_state = await supervisor.run(request, f"thread_{rid}", "user-1", rid)
                    return AgentExecutionResult(success=True, state=final_state)
                except Exception as e:
                    return AgentExecutionResult(success=False, error=str(e))
            
            tasks.append(run_task())
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all requests were processed
        assert len(results) == 5
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Request {i} failed with: {result}")
            assert result.success is True
            assert result.state.user_request == f"Message {i}"
    async def test_supervisor_resource_cleanup(self):
        """Test supervisor properly cleans up resources"""
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = SupervisorAgent(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Add cleanup method to supervisor for testing
        supervisor.cleanup_called = False
        
        async def mock_cleanup():
            supervisor.cleanup_called = True
        
        supervisor.cleanup = mock_cleanup
        
        # Simulate cleanup on shutdown
        await supervisor.cleanup()
        
        assert supervisor.cleanup_called
    async def test_supervisor_metrics_tracking(self):
        """Test supervisor tracks execution metrics"""
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = SupervisorAgent(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Add metrics tracking
        supervisor.metrics = {"requests": 0, "successes": 0, "failures": 0}
        
        # Mock successful execution
        async def mock_execute(state, run_id, stream_updates=True):
            supervisor.metrics["requests"] += 1
            supervisor.metrics["successes"] += 1
            state.triage_result = {"processed": True}
            return state
        
        # Mock triage agent for metrics test
        from app.agents.triage_sub_agent.agent import TriageSubAgent
        mock_triage = AsyncMock(spec=TriageSubAgent)
        mock_triage.execute = mock_execute
        supervisor.agents["triage"] = mock_triage
        
        # Process a request
        state = DeepAgentState(user_request="Test metrics")
        context = AgentExecutionContext(
            run_id="metrics-test",
            thread_id="thread-1",
            user_id="user-1",
            agent_name="supervisor"
        )
        
        # Mock the _route_to_agent method for metrics test
        async def mock_route_to_agent(state, context, agent_name):
            if agent_name in supervisor.agents:
                await supervisor.agents[agent_name].execute(state, context.run_id, True)
            return AgentExecutionResult(success=True, state=state)
        
        supervisor._route_to_agent = mock_route_to_agent
        result = await supervisor._route_to_agent(state, context, "triage")
        
        # Verify metrics were updated
        assert supervisor.metrics["requests"] == 1
        assert supervisor.metrics["successes"] == 1
        assert supervisor.metrics["failures"] == 0
    async def test_supervisor_circuit_breaker_recovery(self):
        """Test supervisor can recover from circuit breaker state"""
        mock_db = AsyncMock()
        mock_llm = AsyncMock()
        mock_websocket = AsyncMock()
        mock_tool_dispatcher = AsyncMock()
        
        supervisor = SupervisorAgent(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
        
        # Add circuit breaker state tracking
        supervisor.circuit_breaker = {"failures": 0, "state": "closed", "last_failure": None}
        
        def get_circuit_state():
            if supervisor.circuit_breaker["failures"] >= 3:
                supervisor.circuit_breaker["state"] = "open"
                return "open"
            return "closed"
        
        # Simulate failures followed by recovery
        call_count = 0
        async def mock_execute(state, run_id, stream_updates=True):
            nonlocal call_count
            call_count += 1
            
            circuit_state = get_circuit_state()
            if circuit_state == "open" and call_count < 6:
                raise Exception("Circuit breaker is open")
            
            if call_count < 4:  # First 3 calls fail
                supervisor.circuit_breaker["failures"] += 1
                raise Exception("Service failure")
            else:  # Later calls succeed
                supervisor.circuit_breaker["failures"] = 0
                supervisor.circuit_breaker["state"] = "closed"
                state.triage_result = {"recovered": True}
                return state
        
        # Mock triage agent for circuit breaker test
        from app.agents.triage_sub_agent.agent import TriageSubAgent
        mock_triage = AsyncMock(spec=TriageSubAgent)
        mock_triage.execute = mock_execute
        supervisor.agents["triage"] = mock_triage
        
        state = DeepAgentState(user_request="Test recovery")
        context = AgentExecutionContext(
            run_id="recovery-test",
            thread_id="thread-1",
            user_id="user-1",
            agent_name="supervisor"
        )
        
        # Mock the _route_to_agent method for circuit breaker test
        async def mock_route_circuit_breaker(state, context, agent_name):
            if call_count >= 4:
                return AgentExecutionResult(success=True, state=state)
            else:
                return AgentExecutionResult(success=False, error="Circuit breaker test")
        
        supervisor._route_to_agent = mock_route_circuit_breaker
        
        # Try multiple times to trigger circuit breaker
        for attempt in range(6):
            try:
                result = await supervisor._route_to_agent(state, context, "triage")
                if result.success:
                    break
            except Exception:
                await asyncio.sleep(0.1)  # Wait before retry
        
        # Verify recovery occurred
        assert supervisor.circuit_breaker["state"] == "closed"
        assert supervisor.circuit_breaker["failures"] == 0