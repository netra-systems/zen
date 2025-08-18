"""
Comprehensive Agent Fixtures Module
Consolidates agent-related mock patterns from 40+ test files
≤300 lines, ≤8 lines per function - ARCHITECTURAL COMPLIANCE
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Type
from unittest.mock import Mock, AsyncMock, MagicMock
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


# Core Agent Mock Factories (≤8 lines each)

def create_mock_supervisor() -> Mock:
    """Create supervisor agent mock with standard methods"""
    supervisor = Mock()
    supervisor.execute = AsyncMock(return_value=_get_default_state())
    supervisor.route_to_agent = AsyncMock()
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    supervisor.agents = _create_agent_registry()
    return supervisor


def create_mock_triage_agent() -> Mock:
    """Create triage agent mock with result generation"""
    triage = Mock()
    triage.execute = AsyncMock(return_value=_get_triage_result())
    triage.extract_entities = AsyncMock(return_value=_get_entities())
    triage.analyze_intent = AsyncMock(return_value=_get_intent())
    return triage


def create_mock_data_agent() -> Mock:
    """Create data sub-agent mock with processing capabilities"""
    data_agent = Mock()
    data_agent.execute = AsyncMock(return_value=_get_data_result())
    data_agent.process_data = AsyncMock(return_value={"processed": True})
    data_agent.analyze_trends = AsyncMock(return_value={"trends": "upward"})
    return data_agent


def create_mock_supply_researcher() -> Mock:
    """Create supply researcher agent mock"""
    researcher = Mock()
    researcher.execute = AsyncMock(return_value=_get_research_result())
    researcher.generate_queries = Mock(return_value=["pricing", "capabilities"])
    researcher.extract_data = AsyncMock(return_value=[{"data": "extracted"}])
    return researcher


# Agent State Factories (≤8 lines each)

def create_agent_state(user_request: str = "Test request", **kwargs) -> DeepAgentState:
    """Create agent state with customizable attributes"""
    state = DeepAgentState(
        user_request=user_request,
        chat_thread_id=kwargs.get('thread_id', str(uuid.uuid4())),
        user_id=kwargs.get('user_id', str(uuid.uuid4()))
    )
    _apply_state_kwargs(state, kwargs)
    return state


def create_triage_state(**kwargs) -> DeepAgentState:
    """Create state with triage result"""
    state = create_agent_state(**kwargs)
    state.triage_result = _get_triage_result()
    return state


def create_data_state(**kwargs) -> DeepAgentState:
    """Create state with data processing result"""
    state = create_agent_state(**kwargs)
    state.data_result = _get_data_result()
    return state


def create_optimization_state(**kwargs) -> DeepAgentState:
    """Create state with optimization result"""
    state = create_agent_state(**kwargs)
    state.optimizations_result = _get_optimization_result()
    return state


# Infrastructure Mock Factories (≤8 lines each)

def create_mock_llm_manager() -> Mock:
    """Create LLM manager mock with response patterns"""
    llm = Mock(spec=LLMManager)
    llm.call_llm = AsyncMock(return_value=_get_llm_response())
    llm.ask_llm = AsyncMock(return_value=json.dumps(_get_structured_response()))
    llm.ask_structured_llm = AsyncMock(return_value=_get_triage_result())
    return llm


def create_mock_db_session() -> AsyncMock:
    """Create database session mock with transaction support"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    _setup_db_transaction(session)
    return session


def create_mock_websocket_manager() -> Mock:
    """Create WebSocket manager mock"""
    ws_manager = Mock()
    ws_manager.send_message = AsyncMock()
    ws_manager.broadcast = AsyncMock()
    ws_manager.send_agent_log = AsyncMock()
    ws_manager.send_sub_agent_update = AsyncMock()
    return ws_manager


def create_mock_tool_dispatcher() -> Mock:
    """Create tool dispatcher mock"""
    dispatcher = Mock(spec=ToolDispatcher)
    dispatcher.dispatch_tool = AsyncMock(return_value=_get_tool_result())
    return dispatcher


# Agent Builder Class (≤8 lines per method)

class AgentBuilder:
    """Fluent interface for building complex agent configurations"""
    
    def __init__(self):
        self.config = {}
        self.mocks = {}
    
    def with_supervisor(self, **kwargs) -> 'AgentBuilder':
        """Add supervisor configuration"""
        self.mocks['supervisor'] = create_mock_supervisor()
        self.config['supervisor_config'] = kwargs
        return self
    
    def with_triage_agent(self, result_data: Dict[str, Any] = None) -> 'AgentBuilder':
        """Add triage agent with custom result"""
        self.mocks['triage'] = create_mock_triage_agent()
        if result_data:
            self.mocks['triage'].execute.return_value = create_triage_state(**result_data)
        return self
    
    def with_data_agent(self, processing_data: Dict[str, Any] = None) -> 'AgentBuilder':
        """Add data agent with custom processing result"""
        self.mocks['data'] = create_mock_data_agent()
        if processing_data:
            self.mocks['data'].process_data.return_value = processing_data
        return self
    
    def with_infrastructure(self) -> 'AgentBuilder':
        """Add standard infrastructure mocks"""
        self.mocks.update({
            'llm_manager': create_mock_llm_manager(),
            'db_session': create_mock_db_session(),
            'websocket_manager': create_mock_websocket_manager(),
            'tool_dispatcher': create_mock_tool_dispatcher()
        })
        return self
    
    def build(self) -> Dict[str, Mock]:
        """Build the configured agent mocks"""
        return self.mocks


# Agent Orchestrator Class (≤8 lines per method)

class AgentOrchestrator:
    """Handles multi-agent testing scenarios"""
    
    def __init__(self, agents: Dict[str, Mock]):
        self.agents = agents
        self.execution_order = []
    
    async def execute_sequence(self, agent_names: List[str], state: DeepAgentState) -> DeepAgentState:
        """Execute agents in sequence"""
        current_state = state
        for name in agent_names:
            agent = self.agents.get(name)
            if agent:
                current_state = await agent.execute(current_state)
        return current_state
    
    def setup_failure_scenario(self, agent_name: str, error_msg: str) -> None:
        """Setup agent to fail with specific error"""
        agent = self.agents.get(agent_name)
        if agent:
            agent.execute = AsyncMock(side_effect=Exception(error_msg))
    
    def setup_retry_scenario(self, agent_name: str, failures: List[str], success_data: Any) -> None:
        """Setup agent with retry behavior"""
        agent = self.agents.get(agent_name)
        if agent:
            side_effects = [Exception(err) for err in failures] + [success_data]
            agent.execute = AsyncMock(side_effect=side_effects)


# Helper Functions (≤8 lines each)

def _get_default_state() -> DeepAgentState:
    """Get default agent state"""
    return DeepAgentState(
        user_request="Test request",
        chat_thread_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4())
    )


def _get_triage_result() -> Dict[str, Any]:
    """Get mock triage result"""
    return {
        "category": "optimization",
        "confidence_score": 0.95,
        "priority": "high",
        "complexity": "moderate"
    }


def _get_data_result() -> Dict[str, Any]:
    """Get mock data processing result"""
    return {
        "processed": True,
        "confidence_score": 0.9,
        "trends": "upward",
        "anomalies": []
    }


def _get_optimization_result() -> Dict[str, Any]:
    """Get mock optimization result"""
    return {
        "optimization_type": "performance",
        "recommendations": ["Use gradient checkpointing", "Reduce batch size"],
        "confidence_score": 0.85
    }


def _get_research_result() -> Dict[str, Any]:
    """Get mock research result"""
    return {
        "research_type": "pricing",
        "provider": "openai",
        "data_extracted": [{"pricing_input": Decimal("30")}],
        "confidence_score": 0.8
    }


def _get_llm_response() -> Dict[str, Any]:
    """Get basic LLM response"""
    return {
        "content": "I'll help you optimize your AI workload",
        "tool_calls": []
    }


def _get_structured_response() -> Dict[str, Any]:
    """Get structured LLM response"""
    return {
        "category": "optimization",
        "confidence": 0.95,
        "requires_data": True,
        "analysis": "User needs AI workload optimization"
    }


def _get_tool_result() -> Dict[str, Any]:
    """Get tool execution result"""
    return {
        "status": "success",
        "result": {"data": "Tool execution successful"}
    }


def _get_entities() -> Dict[str, Any]:
    """Get extracted entities"""
    return {
        "models_mentioned": ["GPT-4", "Claude"],
        "metrics_mentioned": ["latency", "throughput"],
        "time_ranges": []
    }


def _get_intent() -> Dict[str, Any]:
    """Get user intent analysis"""
    return {
        "primary_intent": "optimize",
        "secondary_intents": ["analyze", "monitor"]
    }


def _create_agent_registry() -> Dict[str, Mock]:
    """Create agent registry for supervisor"""
    return {
        "triage": create_mock_triage_agent(),
        "data": create_mock_data_agent(),
        "optimization": Mock(),
        "supply_researcher": create_mock_supply_researcher()
    }


def _apply_state_kwargs(state: DeepAgentState, kwargs: Dict[str, Any]) -> None:
    """Apply keyword arguments to state"""
    for key, value in kwargs.items():
        if key not in ['thread_id', 'user_id']:
            setattr(state, key, value)


def _setup_db_transaction(session: AsyncMock) -> None:
    """Setup database transaction mocks"""
    async_context = AsyncMock()
    async_context.__aenter__ = AsyncMock(return_value=async_context)
    async_context.__aexit__ = AsyncMock(return_value=None)
    session.begin = Mock(return_value=async_context)


# Pytest Fixtures (≤8 lines each)

@pytest.fixture
def agent_builder() -> AgentBuilder:
    """Provide agent builder fixture"""
    return AgentBuilder()


@pytest.fixture
def mock_agent_infrastructure() -> Dict[str, Mock]:
    """Provide standard agent infrastructure mocks"""
    return AgentBuilder().with_infrastructure().build()


@pytest.fixture
def complete_agent_setup() -> Dict[str, Mock]:
    """Provide complete agent setup with all components"""
    return (AgentBuilder()
            .with_supervisor()
            .with_triage_agent()
            .with_data_agent()
            .with_infrastructure()
            .build())