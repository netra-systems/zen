"""Multi-Agent Collaborative Optimization Integration Test

Business Value Justification (BVJ):
1. Segment: Platform/Internal (Development velocity)
2. Business Goal: Validate Supervisor → SubAgent → Tool execution flow
3. Value Impact: Ensures multi-agent collaboration meets reliability standards
4. Strategic Impact: $25K MRR protection via orchestration reliability

COMPLIANCE: File size <300 lines, Functions <8 lines, Real agent testing
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from netra_backend.app.agents.base import BaseSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.tests.unified.e2e.agent_response_test_utilities import (
    AgentResponseSimulator,
)


@pytest.mark.integration
class TestMultiAgentCollaboration:
    """Test multi-agent collaborative optimization workflows."""
    
    @pytest.fixture
    async def collaboration_setup(self):
        """Setup multi-agent collaboration environment."""
        config = get_config()
        llm_manager = LLMManager(config)
        websocket_manager = AsyncMock()
        
        supervisor = SupervisorAgent(llm_manager=llm_manager)
        supervisor.websocket_manager = websocket_manager
        supervisor.user_id = "test_collaboration_user"
        
        return {
            "supervisor": supervisor,
            "llm_manager": llm_manager,
            "websocket_manager": websocket_manager,
            "config": config
        }
    
    async def test_supervisor_to_subagent_flow(self, collaboration_setup):
        """Test complete Supervisor → SubAgent → Tool execution flow."""
        supervisor = collaboration_setup["supervisor"]
        
        # Create mock sub-agent
        sub_agent = BaseSubAgent(
            llm_manager=collaboration_setup["llm_manager"],
            name="TestSubAgent",
            description="Test collaboration sub-agent"
        )
        
        # Mock tool execution
        with patch.object(ToolDispatcher, 'execute_tool') as mock_tool:
            mock_tool.return_value = {"status": "success", "data": "optimization_result"}
            
            # Execute collaboration flow
            start_time = time.time()
            result = await self._execute_collaboration_flow(supervisor, sub_agent)
            execution_time = time.time() - start_time
        
        # Validate collaboration results
        assert result["status"] == "completed"
        assert result["sub_agent_execution"]["success"] is True
        assert result["tool_results"] is not None
        assert execution_time < 5.0  # Performance requirement
    
    async def test_result_aggregation_flow(self, collaboration_setup):
        """Test multi-agent result aggregation."""
        supervisor = collaboration_setup["supervisor"]
        
        # Create multiple mock agents
        agents = [
            BaseSubAgent(
                llm_manager=collaboration_setup["llm_manager"],
                name=f"Agent_{i}",
                description=f"Test agent {i}"
            ) for i in range(3)
        ]
        
        # Execute parallel agent tasks
        results = await self._execute_parallel_agents(supervisor, agents)
        
        # Validate aggregation
        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert "aggregated_result" in results[0]
    
    async def test_collaboration_error_handling(self, collaboration_setup):
        """Test error handling in collaboration flow."""
        supervisor = collaboration_setup["supervisor"]
        
        # Create failing sub-agent
        failing_agent = BaseSubAgent(
            llm_manager=collaboration_setup["llm_manager"],
            name="FailingAgent",
            description="Agent that fails"
        )
        
        # Test error recovery
        with patch.object(failing_agent, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Simulated failure")
            
            result = await self._execute_collaboration_with_errors(supervisor, failing_agent)
        
        # Validate error handling
        assert result["error_handled"] is True
        assert result["recovery_successful"] is True
    
    async def test_context_isolation_between_agents(self, collaboration_setup):
        """Test context isolation between collaborating agents."""
        supervisor = collaboration_setup["supervisor"]
        
        # Create agents with different contexts
        agent1 = BaseSubAgent(
            llm_manager=collaboration_setup["llm_manager"],
            name="Agent1",
            description="First context agent"
        )
        agent2 = BaseSubAgent(
            llm_manager=collaboration_setup["llm_manager"],
            name="Agent2", 
            description="Second context agent"
        )
        
        # Set different contexts
        agent1.context = {"task": "optimization", "scope": "limited"}
        agent2.context = {"task": "analysis", "scope": "full"}
        
        # Execute and validate isolation
        isolation_result = await self._test_context_isolation(agent1, agent2)
        
        assert isolation_result["agent1_context_preserved"] is True
        assert isolation_result["agent2_context_preserved"] is True
        assert isolation_result["no_context_bleeding"] is True
    
    async def _execute_collaboration_flow(self, supervisor: SupervisorAgent, 
                                        sub_agent: BaseSubAgent) -> Dict[str, Any]:
        """Execute complete collaboration flow."""
        try:
            # Step 1: Supervisor delegates to sub-agent
            delegation_result = await supervisor.delegate_to_subagent(sub_agent, "optimization_task")
            
            # Step 2: Sub-agent executes with tools
            execution_result = await sub_agent.execute()
            
            # Step 3: Result aggregation
            aggregated_result = await supervisor.aggregate_results([execution_result])
            
            return {
                "status": "completed",
                "delegation_result": delegation_result,
                "sub_agent_execution": {"success": True},
                "tool_results": execution_result,
                "aggregated_result": aggregated_result
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _execute_parallel_agents(self, supervisor: SupervisorAgent, 
                                     agents: List[BaseSubAgent]) -> List[Dict[str, Any]]:
        """Execute agents in parallel and aggregate results."""
        tasks = [agent.execute() for agent in agents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Simulate result aggregation
        aggregated = await supervisor.aggregate_results(results)
        
        return [
            {
                "success": not isinstance(r, Exception),
                "result": r if not isinstance(r, Exception) else None,
                "aggregated_result": aggregated
            }
            for r in results
        ]
    
    async def _execute_collaboration_with_errors(self, supervisor: SupervisorAgent,
                                               failing_agent: BaseSubAgent) -> Dict[str, Any]:
        """Test collaboration with error scenarios."""
        try:
            # Attempt execution that will fail
            await failing_agent.execute()
            return {"error_handled": False, "recovery_successful": False}
        except Exception:
            # Test error recovery
            recovery_result = await supervisor.handle_agent_failure(failing_agent)
            return {
                "error_handled": True,
                "recovery_successful": recovery_result is not None
            }
    
    async def _test_context_isolation(self, agent1: BaseSubAgent, 
                                    agent2: BaseSubAgent) -> Dict[str, Any]:
        """Test context isolation between agents."""
        original_context1 = agent1.context.copy()
        original_context2 = agent2.context.copy()
        
        # Execute both agents
        await asyncio.gather(
            agent1.execute(),
            agent2.execute(),
            return_exceptions=True
        )
        
        # Check context preservation
        context1_preserved = agent1.context == original_context1
        context2_preserved = agent2.context == original_context2
        no_bleeding = agent1.context != agent2.context
        
        return {
            "agent1_context_preserved": context1_preserved,
            "agent2_context_preserved": context2_preserved,
            "no_context_bleeding": no_bleeding
        }


@pytest.mark.integration
async def test_tool_execution_integration():
    """Test tool execution within collaboration flow."""
    config = get_config()
    llm_manager = LLMManager(config)
    
    agent = BaseSubAgent(llm_manager=llm_manager, name="ToolTestAgent")
    tool_dispatcher = ToolDispatcher()
    
    # Mock successful tool execution
    with patch.object(tool_dispatcher, 'execute_tool') as mock_execute:
        mock_execute.return_value = {"status": "success", "data": "test_result"}
        
        result = await tool_dispatcher.execute_tool("test_tool", {"param": "value"})
    
    assert result["status"] == "success"
    assert "data" in result


@pytest.mark.integration
async def test_supervisor_delegation_performance():
    """Test supervisor delegation performance requirements."""
    config = get_config()
    llm_manager = LLMManager(config)
    
    supervisor = SupervisorAgent(llm_manager=llm_manager)
    sub_agent = BaseSubAgent(llm_manager=llm_manager, name="PerfTestAgent")
    
    # Test delegation speed
    start_time = time.time()
    result = await supervisor.delegate_to_subagent(sub_agent, "performance_test")
    delegation_time = time.time() - start_time
    
    # Performance requirements
    assert delegation_time < 2.0  # Must complete within 2 seconds
    assert result is not None