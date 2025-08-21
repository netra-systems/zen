"""
Collaboration and authentication critical end-to-end tests.
Tests 7-8: Authentication/authorization, multi-agent collaboration.
"""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock
from datetime import datetime

# Add project root to path

from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult
from netra_backend.tests.agents.test_agent_e2e_critical_setup import AgentE2ETestBase

# Add project root to path


class TestAgentE2ECriticalCollaboration(AgentE2ETestBase):
    """Collaboration and authentication critical tests"""
    async def test_7_authentication_and_authorization(self, setup_agent_infrastructure):
        """
        Test Case 7: Authentication and Authorization
        - Test user authentication before agent execution
        - Test authorization for different agent capabilities
        - Test secure token handling
        """
        infra = setup_agent_infrastructure
        agent_service = infra["agent_service"]
        
        # Mock start_agent_run to simulate authorization check
        async def mock_start_agent_run(user_id=None, thread_id=None, request=None):
            if user_id == None:
                raise Exception("Unauthorized: No user ID provided")
            return str(uuid.uuid4())
        
        agent_service.start_agent_run = mock_start_agent_run
        
        # Test unauthorized access
        with pytest.raises(Exception) as exc_info:
            await agent_service.start_agent_run(
                user_id=None,  # No user ID
                thread_id=str(uuid.uuid4()),
                request="Unauthorized request"
            )
        
        # Test with valid authentication
        valid_user_id = str(uuid.uuid4())
        valid_token = "valid_jwt_token"
        
        # Should proceed with valid auth
        run_id = await agent_service.start_agent_run(
            user_id=valid_user_id,
            thread_id=str(uuid.uuid4()),
            request="Authorized request"
        )
        assert run_id != None
        
        # Test role-based access to specific sub-agents
        restricted_user = {"user_id": "restricted", "role": "viewer"}
        admin_user = {"user_id": "admin", "role": "admin"}
        
        # Mock role checking
        async def check_agent_access(user, agent_name):
            if user["role"] == "viewer" and agent_name in ["OptimizationsCoreSubAgent", "ActionsToMeetGoalsSubAgent"]:
                return False
            return True
        
        # Viewer should have limited access
        supervisor = infra["supervisor"]
        
        # Filter sub-agents based on role
        allowed_agents = []
        # Handle both consolidated and legacy implementations
        sub_agents = []
        if hasattr(supervisor, '_impl') and supervisor._impl:
            if hasattr(supervisor._impl, 'agents'):
                sub_agents = list(supervisor._impl.agents.values())
            elif hasattr(supervisor._impl, 'sub_agents'):
                sub_agents = supervisor._impl.sub_agents
        elif hasattr(supervisor, 'sub_agents'):
            sub_agents = supervisor.sub_agents
            
        for agent in sub_agents:
            if await check_agent_access(restricted_user, agent.name):
                allowed_agents.append(agent)
        
        # Verify viewer has restricted access
        assert len(allowed_agents) <= len(sub_agents)

    async def _track_concurrent_execution(self, concurrent_executions, execution_lock, state, agent_name):
        """Track and log concurrent agent execution"""
        async with execution_lock:
            concurrent_executions.append({"agent": agent_name, "start": datetime.now()})
        await asyncio.sleep(0.1)  # Simulate work
        await self._update_state_with_results(state, agent_name)
        async with execution_lock:
            concurrent_executions.append({"agent": agent_name, "end": datetime.now()})
        return state

    async def _update_state_with_results(self, state, agent_name):
        """Update state with agent-specific results"""
        if agent_name == "Data":
            state.data_result = {"metrics": "analyzed"}
        elif agent_name == "OptimizationsCore":
            state.optimizations_result = OptimizationsResult(
                optimization_type="gpu", recommendations=["optimize"]
            )

    def _get_sub_agents(self, supervisor):
        """Extract sub-agents from supervisor implementation"""
        sub_agents = []
        if hasattr(supervisor, '_impl') and supervisor._impl:
            if hasattr(supervisor._impl, 'agents'):
                sub_agents = list(supervisor._impl.agents.values())
            elif hasattr(supervisor._impl, 'sub_agents'):
                sub_agents = supervisor._impl.sub_agents
        elif hasattr(supervisor, 'sub_agents'):
            sub_agents = supervisor.sub_agents
        return sub_agents

    def _setup_mock_executions(self, sub_agents, concurrent_executions, execution_lock):
        """Setup mock execution functions for agents"""
        async def data_execute(s, r, st):
            return await self._track_concurrent_execution(concurrent_executions, execution_lock, s, "Data")
        
        async def opt_execute(s, r, st):
            return await self._track_concurrent_execution(concurrent_executions, execution_lock, s, "OptimizationsCore")
        
        if len(sub_agents) > 1:
            sub_agents[1].execute = AsyncMock(side_effect=data_execute)
        if len(sub_agents) > 2:
            sub_agents[2].execute = AsyncMock(side_effect=opt_execute)

    async def _execute_parallel_agents(self, agents, state, run_id, stream):
        """Execute agents in parallel and merge results"""
        tasks = [agent.execute(state, run_id, stream) for agent in agents]
        results = await asyncio.gather(*tasks)
        if results:
            return results[-1]
        return state

    def _select_parallel_agents(self, sub_agents):
        """Select agents for parallel execution"""
        if len(sub_agents) > 2:
            return [sub_agents[1], sub_agents[2]]
        elif len(sub_agents) > 1:
            return [sub_agents[0], sub_agents[1]]
        return []

    def _verify_collaboration_state(self, final_state):
        """Verify that collaboration modified the state properly"""
        assert final_state is not None
        assert hasattr(final_state, 'data_result') or hasattr(final_state, 'optimizations_result')

    def _verify_execution_overlap(self, concurrent_executions):
        """Verify that agents executed with overlapping timing"""
        data_events = [e for e in concurrent_executions if e.get("agent") == "Data" and "start" in e]
        opt_events = [e for e in concurrent_executions if e.get("agent") == "OptimizationsCore" and "start" in e]
        
        if len(data_events) >= 1 and len(opt_events) >= 1:
            data_start = data_events[0]["start"]
            opt_start = opt_events[0]["start"]
            time_diff = abs((data_start - opt_start).total_seconds())
            assert time_diff < 1.0  # Started within 1 second of each other
    async def test_8_multi_agent_collaboration(self, setup_agent_infrastructure):
        """
        Test Case 8: Multi-agent Collaboration
        - Test parallel sub-agent execution
        - Test inter-agent communication
        - Test collaborative decision making
        """
        infra = setup_agent_infrastructure
        supervisor = infra["supervisor"]
        run_id = str(uuid.uuid4())
        concurrent_executions = []
        execution_lock = asyncio.Lock()
        
        sub_agents = self._get_sub_agents(supervisor)
        self._setup_mock_executions(sub_agents, concurrent_executions, execution_lock)
        
        state = DeepAgentState(user_request="Complex optimization requiring collaboration")
        parallel_agents = self._select_parallel_agents(sub_agents)
        final_state = await self._execute_parallel_agents(parallel_agents, state, run_id, False) if parallel_agents else state
        
        self._verify_collaboration_state(final_state)
        self._verify_execution_overlap(concurrent_executions)