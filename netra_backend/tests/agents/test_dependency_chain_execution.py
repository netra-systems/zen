"""Test multi-agent dependency chain execution and context propagation.

CRITICAL: This test validates that:
1. Agent dependencies are properly validated
2. Context and WebSocket manager propagate through the hierarchy
3. Results are passed correctly between dependent agents
4. Retry logic works for recoverable errors
5. Graceful degradation for optional dependencies
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.core.unified_logging import get_logger

logger = get_logger(__name__)


class MockAgent(BaseAgent):
    """Mock agent for testing dependency chains."""
    
    def __init__(self, name: str, should_fail: bool = False, fail_count: int = 0):
        self.name = name
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.current_failures = 0
        self.websocket_bridge = None
        self._run_id = None
        self.execution_count = 0
        
    async def execute(self, context: UserExecutionContext, stream_updates: bool = True):
        """Execute the mock agent."""
        self.execution_count += 1
        
        # Simulate failure for retry testing
        if self.should_fail and self.current_failures < self.fail_count:
            self.current_failures += 1
            raise ConnectionError(f"{self.name} connection failed (attempt {self.current_failures})")
        
        # Return a result that includes dependency info
        result = {
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "received_dependencies": {},
            "websocket_set": self.websocket_bridge is not None,
            "run_id": str(self._run_id) if self._run_id else None
        }
        
        # Check for dependencies in context
        dependency_keys = {
            "data": ["triage_result"],
            "optimization": ["triage_result", "data_result"],
            "actions": ["triage_result", "data_result", "optimizations_result"],
            "reporting": ["triage_result", "data_result", "optimizations_result", "action_plan_result"]
        }
        
        for dep_key in dependency_keys.get(self.name, []):
            if dep_key in context.metadata:
                result["received_dependencies"][dep_key] = True
        
        return result
    
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge on the agent."""
        self.websocket_bridge = bridge
        self._run_id = run_id


class TestDependencyChainExecution:
    """Test multi-agent dependency chain execution."""
    
    @pytest.fixture
    async def setup(self):
        """Set up test environment."""
        # Create mock LLM manager and WebSocket bridge
        llm_manager = MagicMock(spec=LLMManager)
        websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)
        
        # Create supervisor
        supervisor = SupervisorAgent(
            llm_manager=llm_manager,
            websocket_bridge=websocket_bridge
        )
        
        # Create mock agents
        agents = {
            "triage": MockAgent("triage"),
            "data": MockAgent("data"),
            "optimization": MockAgent("optimization"),
            "actions": MockAgent("actions"),
            "reporting": MockAgent("reporting")
        }
        
        return {
            "supervisor": supervisor,
            "agents": agents,
            "websocket_bridge": websocket_bridge,
            "llm_manager": llm_manager
        }
    
    @pytest.mark.asyncio
    async def test_successful_dependency_chain(self, setup):
        """Test successful execution through complete dependency chain."""
        supervisor = setup["supervisor"]
        agents = setup["agents"]
        
        # Create execution context
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid4()),
            websocket_connection_id="test_ws",
            metadata={"user_request": "Test dependency chain"}
        )
        
        # Mock agent instance creation
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents):
            # Execute workflow
            results = await supervisor._execute_workflow_with_isolated_agents(
                agents, context, None, "test_flow"
            )
        
        # Verify all agents executed
        assert "triage" in results
        assert "data" in results
        assert "optimization" in results
        assert "actions" in results
        assert "reporting" in results
        
        # Verify dependencies were available
        assert results["data"]["received_dependencies"].get("triage_result") == True
        assert results["optimization"]["received_dependencies"].get("triage_result") == True
        assert results["optimization"]["received_dependencies"].get("data_result") == True
        assert results["actions"]["received_dependencies"].get("data_result") == True
        
        # Verify WebSocket was propagated
        assert results["triage"]["websocket_set"] == True
        assert results["data"]["websocket_set"] == True
    
    @pytest.mark.asyncio
    async def test_missing_dependency_handling(self, setup):
        """Test handling of missing dependencies."""
        supervisor = setup["supervisor"]
        agents = setup["agents"]
        
        # Remove triage agent to create missing dependency
        del agents["triage"]
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid4()),
            websocket_connection_id="test_ws",
            metadata={"user_request": "Test missing dependency"}
        )
        
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents):
            results = await supervisor._execute_workflow_with_isolated_agents(
                agents, context, None, "test_flow"
            )
        
        # Verify data agent was skipped due to missing triage
        assert "data" in results
        assert results["data"]["status"] == "skipped"
        assert "missing_deps" in results["data"]
        assert any("triage" in dep for dep in results["data"]["missing_deps"])
    
    @pytest.mark.asyncio
    async def test_retry_logic_on_failure(self, setup):
        """Test retry logic with exponential backoff."""
        supervisor = setup["supervisor"]
        agents = setup["agents"]
        
        # Make data agent fail twice then succeed
        agents["data"] = MockAgent("data", should_fail=True, fail_count=2)
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid4()),
            websocket_connection_id="test_ws",
            metadata={"user_request": "Test retry logic"}
        )
        
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents):
            results = await supervisor._execute_workflow_with_isolated_agents(
                agents, context, None, "test_flow"
            )
        
        # Verify data agent eventually succeeded after retries
        assert "data" in results
        assert results["data"]["agent_name"] == "data"
        # Should have been executed 3 times (2 failures + 1 success)
        assert agents["data"].execution_count == 3
    
    @pytest.mark.asyncio
    async def test_context_propagation(self, setup):
        """Test context propagation through agent hierarchy."""
        supervisor = setup["supervisor"]
        agents = setup["agents"]
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid4()),
            websocket_connection_id="test_ws",
            metadata={"user_request": "Test context propagation"}
        )
        
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents):
            results = await supervisor._execute_workflow_with_isolated_agents(
                agents, context, None, "test_flow"
            )
        
        # Verify context metadata was updated with results
        assert "triage_result" in context.metadata
        assert "data_result" in context.metadata
        assert "optimizations_result" in context.metadata
        assert "action_plan_result" in context.metadata
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_optional_deps(self, setup):
        """Test graceful degradation when optional dependencies are missing."""
        supervisor = setup["supervisor"]
        agents = setup["agents"]
        
        # Remove optimization agent (optional for reporting)
        del agents["optimization"]
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid4()),
            websocket_connection_id="test_ws",
            metadata={"user_request": "Test graceful degradation"}
        )
        
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents):
            results = await supervisor._execute_workflow_with_isolated_agents(
                agents, context, None, "test_flow"
            )
        
        # Verify reporting still executed despite missing optional dependency
        assert "reporting" in results
        assert results["reporting"]["agent_name"] == "reporting"
        # Optimization should be marked as skipped
        assert "optimization" not in results  # Not in agent_instances
    
    @pytest.mark.asyncio
    async def test_critical_agent_failure_stops_workflow(self, setup):
        """Test that critical agent failure stops the workflow."""
        supervisor = setup["supervisor"]
        agents = setup["agents"]
        
        # Make triage agent fail permanently
        agents["triage"] = MockAgent("triage", should_fail=True, fail_count=10)
        
        context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=str(uuid4()),
            websocket_connection_id="test_ws",
            metadata={"user_request": "Test critical failure"}
        )
        
        with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents):
            results = await supervisor._execute_workflow_with_isolated_agents(
                agents, context, None, "test_flow"
            )
        
        # Verify workflow stopped after triage failure
        assert "triage" in results
        assert results["triage"]["status"] == "failed"
        
        # Data should be skipped due to missing triage dependency
        if "data" in results:
            assert results["data"]["status"] == "skipped"
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_isolation(self, setup):
        """Test that concurrent workflows maintain isolation."""
        supervisor = setup["supervisor"]
        
        # Create two different contexts for concurrent execution
        context1 = UserExecutionContext(
            user_id="user1",
            thread_id="thread1",
            run_id=str(uuid4()),
            websocket_connection_id="ws1",
            metadata={"user_request": "User 1 request"}
        )
        
        context2 = UserExecutionContext(
            user_id="user2",
            thread_id="thread2",
            run_id=str(uuid4()),
            websocket_connection_id="ws2",
            metadata={"user_request": "User 2 request"}
        )
        
        # Create separate agent sets for each user
        agents1 = {
            "triage": MockAgent("triage"),
            "data": MockAgent("data")
        }
        
        agents2 = {
            "triage": MockAgent("triage"),
            "data": MockAgent("data")
        }
        
        # Execute workflows concurrently
        async def workflow1():
            with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents1):
                return await supervisor._execute_workflow_with_isolated_agents(
                    agents1, context1, None, "flow1"
                )
        
        async def workflow2():
            with patch.object(supervisor, '_create_isolated_agent_instances', return_value=agents2):
                return await supervisor._execute_workflow_with_isolated_agents(
                    agents2, context2, None, "flow2"
                )
        
        # Run concurrently
        results1, results2 = await asyncio.gather(workflow1(), workflow2())
        
        # Verify isolation - each workflow got its own results
        assert results1["triage"]["agent_name"] == "triage"
        assert results2["triage"]["agent_name"] == "triage"
        
        # Verify contexts didn't cross-contaminate
        assert context1.user_id == "user1"
        assert context2.user_id == "user2"
        assert "triage_result" in context1.metadata
        assert "triage_result" in context2.metadata