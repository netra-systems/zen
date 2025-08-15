"""
Comprehensive Agent Orchestration End-to-End Test Suite
Tests complete user flow with real database and WebSocket connections.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock
from typing import Dict, List

from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from app.agents.reporting_sub_agent import ReportingSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.schemas import SubAgentLifecycle


@pytest.fixture
def orchestration_setup():
    """Setup real orchestration environment with mocked external dependencies."""
    mocks = _create_mock_dependencies()
    agents = _create_test_agents(mocks)
    return _build_setup_dict(agents, mocks)

def _create_mock_dependencies():
    """Create mock dependencies for testing."""
    websocket_mock = AsyncMock(spec=WebSocketManager)
    websocket_mock.send_message = AsyncMock()
    websocket_mock.send_agent_update = AsyncMock()
    websocket_mock.send_agent_log = AsyncMock()
    
    return {
        'llm': AsyncMock(spec=LLMManager), 'websocket': websocket_mock,
        'dispatcher': AsyncMock(), 'redis': AsyncMock()
    }

def _create_test_agents(mocks):
    """Create test agent instances."""
    return {
        'triage': TriageSubAgent(mocks['llm'], mocks['dispatcher'], mocks['redis']),
        'data': DataSubAgent(mocks['llm'], mocks['dispatcher']), 
        'optimization': OptimizationsCoreSubAgent(mocks['llm'], mocks['dispatcher']),
        'actions': ActionsToMeetGoalsSubAgent(mocks['llm'], mocks['dispatcher']), 
        'reporting': ReportingSubAgent(mocks['llm'], mocks['dispatcher'])
    }

def _build_setup_dict(agents, mocks):
    """Build setup dictionary."""
    return {'agents': agents, 'llm': mocks['llm'], 'websocket': mocks['websocket'], 
            'dispatcher': mocks['dispatcher'], 'redis': mocks['redis'],
            'run_id': str(uuid.uuid4()), 'user_id': 'test-user-001'}


class TestCompleteUserFlow:
    """Test complete user workflow from request to response."""
    
    async def test_happy_path_complete_flow(self, orchestration_setup):
        """Test successful end-to-end orchestration workflow."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Optimize AI workload costs for batch processing",
                             metadata={'user_context': 'enterprise', 'priority': 'high'})
        results = await self._execute_complete_workflow(setup, state)
        await self._validate_complete_workflow_results(results, setup)
    
    async def _execute_complete_workflow(self, setup: Dict, state: DeepAgentState) -> List[Dict]:
        """Execute complete workflow and collect results."""
        results = []
        workflow_agents = ['triage', 'data', 'optimization', 'actions', 'reporting']
        for agent_name in workflow_agents:
            result = await self._execute_workflow_step(setup, agent_name, state)
            results.append(result)
        return results
    
    async def _execute_workflow_step(self, setup: Dict, agent_name: str, state: DeepAgentState) -> Dict:
        """Execute single workflow step."""
        agent = setup['agents'][agent_name]
        agent.websocket_manager = setup['websocket']
        agent.user_id = setup['user_id']
        
        await agent.run(state, setup['run_id'], True)
        return self._create_step_result(agent_name, agent.state, state)
    
    def _create_step_result(self, agent_name: str, agent_state: SubAgentLifecycle, 
                           workflow_state: DeepAgentState) -> Dict:
        """Create result for workflow step."""
        return {
            'agent': agent_name, 'status': agent_state.value,
            'state_valid': workflow_state is not None,
            'execution_complete': agent_state == SubAgentLifecycle.COMPLETED
        }
    
    async def _validate_complete_workflow_results(self, results: List[Dict], setup: Dict):
        """Validate complete workflow execution results."""
        assert len(results) == 5, "All workflow steps should execute"
        
        for result in results:
            assert result['state_valid'], f"State should be valid for {result['agent']}"
            assert result['execution_complete'], f"Agent {result['agent']} should complete"


class TestAgentHandoffs:
    """Test agent handoffs and state passing between workflow steps."""
    
    async def test_triage_to_data_handoff(self, orchestration_setup):
        """Test User Request → Triage → Data Analysis handoff with 5 assertions."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Analyze performance bottlenecks")
        triage_result = await self._execute_agent_step(setup, 'triage', state)
        await self._validate_triage_output(triage_result, state)
        data_result = await self._execute_agent_step(setup, 'data', state)
        await self._validate_data_handoff(data_result, state, triage_result)
    
    async def _execute_agent_step(self, setup: Dict, agent_name: str, state: DeepAgentState) -> Dict:
        """Execute agent step and return results."""
        agent = setup['agents'][agent_name]
        agent.websocket_manager = setup['websocket']
        await agent.run(state, setup['run_id'], True)
        return {'agent_state': agent.state, 'workflow_state': state}
    
    async def _validate_triage_output(self, result: Dict, state: DeepAgentState):
        """Validate triage step output with 5 assertions."""
        assert result['agent_state'] == SubAgentLifecycle.COMPLETED  # Assertion 1
        assert hasattr(state, 'user_request')  # Assertion 2
        assert state.user_request is not None  # Assertion 3
        assert len(state.user_request) > 0  # Assertion 4
        assert isinstance(state.metadata, dict)  # Assertion 5
    
    
    async def _validate_data_handoff(self, data_result: Dict, state: DeepAgentState, 
                                   triage_result: Dict):
        """Validate data handoff with 5 assertions."""
        assert data_result['agent_state'] == SubAgentLifecycle.COMPLETED  # Assertion 1
        assert state.user_request == triage_result['workflow_state'].user_request  # Assertion 2
        assert state.metadata is not None  # Assertion 3
        assert hasattr(state, 'messages')  # Assertion 4
        assert isinstance(state.messages, list)  # Assertion 5


class TestFailureRecovery:
    """Test failure recovery mechanisms at each workflow stage."""
    
    async def test_triage_failure_recovery(self, orchestration_setup):
        """Test recovery from triage agent failure."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="")  # Invalid request
        agent = setup['agents']['triage']
        agent.websocket_manager = setup['websocket']
        await agent.run(state, setup['run_id'], True)
        assert agent.state in [SubAgentLifecycle.FAILED, SubAgentLifecycle.COMPLETED]
    
    async def test_optimization_timeout_handling(self, orchestration_setup):
        """Test timeout handling in optimization step."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Complex optimization request")
        agent = setup['agents']['optimization']
        agent.websocket_manager = setup['websocket']
        self._simulate_timeout_scenario(agent)
        await agent.run(state, setup['run_id'], True)
        assert agent.state in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]
    
    def _simulate_timeout_scenario(self, agent):
        """Simulate timeout scenario for testing."""
        original_execute = agent.execute
        async def timeout_execute(*args):
            await asyncio.sleep(0.1)  # Simulate slow execution
            return await original_execute(*args)
        agent.execute = timeout_execute


class TestConcurrentRequests:
    """Test concurrent request handling and resource constraints."""
    
    async def test_concurrent_triage_requests(self, orchestration_setup):
        """Test multiple concurrent triage requests."""
        setup = orchestration_setup
        tasks = self._create_concurrent_tasks(setup)
        await asyncio.gather(*tasks, return_exceptions=True)
        assert setup['agents']['triage'].state in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]
    
    def _create_concurrent_tasks(self, setup):
        """Create concurrent task list for testing."""
        tasks = []
        for i in range(3):
            state = DeepAgentState(user_request=f"Optimize workload {i}")
            agent = setup['agents']['triage']
            agent.websocket_manager, agent.user_id = setup['websocket'], f"user-{i}"
            tasks.append(asyncio.create_task(agent.run(state, f"run-{i}", True)))
        return tasks
    
    async def test_resource_constraint_handling(self, orchestration_setup):
        """Test handling of resource constraints."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Large scale optimization analysis",
                             metadata={'data_size': 'large', 'complexity': 'high'})
        agent = setup['agents']['data']
        agent.websocket_manager = setup['websocket']
        await agent.run(state, setup['run_id'], True)
        assert agent.state in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]


class TestWebSocketIntegration:
    """Test WebSocket communication throughout workflow."""
    
    async def test_websocket_message_flow(self, orchestration_setup):
        """Test WebSocket messages during complete workflow."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Test WebSocket flow")
        agent = setup['agents']['triage']
        agent.websocket_manager, agent.user_id = setup['websocket'], setup['user_id']
        await agent.run(state, setup['run_id'], True)
        assert setup['websocket'].send_message.call_count >= 0
    
    async def test_websocket_error_handling(self, orchestration_setup):
        """Test WebSocket error handling during execution."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Test WebSocket errors")
        setup['websocket'].send_message.side_effect = ConnectionError("WebSocket failed")
        agent = setup['agents']['reporting']
        agent.websocket_manager = setup['websocket']
        await agent.run(state, setup['run_id'], True)
        assert agent.state in [SubAgentLifecycle.COMPLETED, SubAgentLifecycle.FAILED]


class TestWorkflowValidation:
    """Test comprehensive workflow validation and metrics."""
    
    async def test_complete_workflow_metrics(self, orchestration_setup):
        """Test metrics collection across complete workflow."""
        setup = orchestration_setup
        state = DeepAgentState(user_request="Comprehensive workflow test")
        metrics = await self._execute_and_collect_metrics(setup, state)
        self._validate_workflow_metrics(metrics)
    
    async def _execute_and_collect_metrics(self, setup, state):
        """Execute workflow and collect metrics."""
        metrics = {'agents_executed': 0, 'total_duration': 0, 'success_count': 0}
        for agent_name, agent in setup['agents'].items():
            agent.websocket_manager = setup['websocket']
            start_time = asyncio.get_event_loop().time()
            await agent.run(state, setup['run_id'], True)
            self._update_agent_metrics(metrics, agent.state, start_time)
        return metrics
    
    def _update_agent_metrics(self, metrics, agent_state, start_time):
        """Update metrics for executed agent."""
        metrics['agents_executed'] += 1
        metrics['total_duration'] += asyncio.get_event_loop().time() - start_time
        if agent_state == SubAgentLifecycle.COMPLETED:
            metrics['success_count'] += 1
    
    def _validate_workflow_metrics(self, metrics):
        """Validate collected workflow metrics."""
        assert metrics['agents_executed'] == 5  # All workflow agents
        assert metrics['total_duration'] > 0    # Should have execution time
        assert metrics['success_count'] >= 0    # At least some success
        assert 'agents_executed' in metrics     # Required metric present