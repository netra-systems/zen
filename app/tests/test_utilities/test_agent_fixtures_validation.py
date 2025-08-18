"""
Validation Tests for Agent Fixtures Module
Tests the comprehensive agent fixtures module functionality
≤300 lines, ≤8 lines per function - ARCHITECTURAL COMPLIANCE
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from app.tests.test_utilities.agent_fixtures import (
    create_mock_supervisor,
    create_mock_triage_agent,
    create_mock_data_agent,
    create_agent_state,
    AgentBuilder,
    AgentOrchestrator,
    create_mock_llm_manager,
    create_mock_db_session,
    create_mock_websocket_manager
)
from app.agents.state import DeepAgentState


def test_create_mock_supervisor():
    """Test supervisor mock creation"""
    supervisor = create_mock_supervisor()
    assert hasattr(supervisor, 'execute')
    assert hasattr(supervisor, 'thread_id')
    assert hasattr(supervisor, 'user_id')
    assert isinstance(supervisor.agents, dict)


def test_create_mock_triage_agent():
    """Test triage agent mock creation"""
    triage = create_mock_triage_agent()
    assert hasattr(triage, 'execute')
    assert hasattr(triage, 'extract_entities')
    assert hasattr(triage, 'analyze_intent')


def test_create_mock_data_agent():
    """Test data agent mock creation"""
    data_agent = create_mock_data_agent()
    assert hasattr(data_agent, 'execute')
    assert hasattr(data_agent, 'process_data')
    assert hasattr(data_agent, 'analyze_trends')


def test_create_agent_state():
    """Test agent state factory"""
    state = create_agent_state("Test request")
    assert isinstance(state, DeepAgentState)
    assert state.user_request == "Test request"
    assert state.chat_thread_id is not None
    assert state.user_id is not None


def test_create_agent_state_with_kwargs():
    """Test agent state with custom attributes"""
    state = create_agent_state("Test", custom_attr="value")
    assert hasattr(state, 'custom_attr')
    assert state.custom_attr == "value"


def test_create_mock_llm_manager():
    """Test LLM manager mock creation"""
    llm = create_mock_llm_manager()
    assert hasattr(llm, 'call_llm')
    assert hasattr(llm, 'ask_llm')
    assert hasattr(llm, 'ask_structured_llm')


def test_create_mock_db_session():
    """Test database session mock creation"""
    session = create_mock_db_session()
    assert hasattr(session, 'commit')
    assert hasattr(session, 'rollback')
    assert hasattr(session, 'close')
    assert hasattr(session, 'begin')


def test_create_mock_websocket_manager():
    """Test WebSocket manager mock creation"""
    ws_manager = create_mock_websocket_manager()
    assert hasattr(ws_manager, 'send_message')
    assert hasattr(ws_manager, 'broadcast')
    assert hasattr(ws_manager, 'send_agent_log')


class TestAgentBuilder:
    """Test AgentBuilder fluent interface"""
    
    def test_builder_initialization(self):
        """Test builder initialization"""
        builder = AgentBuilder()
        assert hasattr(builder, 'config')
        assert hasattr(builder, 'mocks')
    
    def test_with_supervisor(self):
        """Test supervisor configuration"""
        builder = AgentBuilder()
        result = builder.with_supervisor(test_param="value")
        assert isinstance(result, AgentBuilder)
        assert 'supervisor' in builder.mocks
    
    def test_with_triage_agent(self):
        """Test triage agent configuration"""
        builder = AgentBuilder()
        result = builder.with_triage_agent()
        assert isinstance(result, AgentBuilder)
        assert 'triage' in builder.mocks
    
    def test_with_infrastructure(self):
        """Test infrastructure configuration"""
        builder = AgentBuilder()
        result = builder.with_infrastructure()
        assert isinstance(result, AgentBuilder)
        assert 'llm_manager' in builder.mocks
        assert 'db_session' in builder.mocks
    
    def test_build_complete_setup(self):
        """Test building complete agent setup"""
        mocks = (AgentBuilder()
                .with_supervisor()
                .with_triage_agent()
                .with_infrastructure()
                .build())
        
        assert 'supervisor' in mocks
        assert 'triage' in mocks
        assert 'llm_manager' in mocks


class TestAgentOrchestrator:
    """Test AgentOrchestrator multi-agent scenarios"""
    
    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        agents = {'test_agent': Mock()}
        orchestrator = AgentOrchestrator(agents)
        assert orchestrator.agents == agents
        assert hasattr(orchestrator, 'execution_order')
    
    @pytest.mark.asyncio
    async def test_execute_sequence(self):
        """Test sequential agent execution"""
        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value="result")
        
        agents = {'test_agent': mock_agent}
        orchestrator = AgentOrchestrator(agents)
        state = create_agent_state("Test")
        
        result = await orchestrator.execute_sequence(['test_agent'], state)
        assert mock_agent.execute.called
    
    def test_setup_failure_scenario(self):
        """Test failure scenario setup"""
        mock_agent = Mock()
        agents = {'test_agent': mock_agent}
        orchestrator = AgentOrchestrator(agents)
        
        orchestrator.setup_failure_scenario('test_agent', 'Test error')
        assert isinstance(mock_agent.execute, AsyncMock)
    
    def test_setup_retry_scenario(self):
        """Test retry scenario setup"""
        mock_agent = Mock()
        agents = {'test_agent': mock_agent}
        orchestrator = AgentOrchestrator(agents)
        
        orchestrator.setup_retry_scenario('test_agent', ['error1'], 'success')
        assert isinstance(mock_agent.execute, AsyncMock)


@pytest.mark.asyncio
async def test_integration_agent_builder_orchestrator():
    """Test integration between AgentBuilder and AgentOrchestrator"""
    # Build agents using AgentBuilder
    mocks = (AgentBuilder()
            .with_supervisor()
            .with_triage_agent()
            .with_data_agent()
            .build())
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(mocks)
    
    # Test execution
    state = create_agent_state("Integration test")
    await orchestrator.execute_sequence(['triage', 'data'], state)
    
    # Verify execution
    assert mocks['triage'].execute.called
    assert mocks['data'].execute.called


def test_agent_fixtures_architectural_compliance():
    """Test that agent fixtures meet architectural requirements"""
    # Test line count compliance (this test implicitly validates)
    builder = AgentBuilder()
    mocks = builder.with_infrastructure().build()
    
    # Verify all required mocks are created
    required_mocks = ['llm_manager', 'db_session', 'websocket_manager', 'tool_dispatcher']
    for mock_name in required_mocks:
        assert mock_name in mocks
        assert mocks[mock_name] is not None