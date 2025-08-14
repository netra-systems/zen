"""Shared fixtures for agent tests."""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.llm_manager import LLMManager
from app.ws_manager import WebSocketManager
from app.config import get_config
from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.tool_dispatcher import ToolDispatcher
from app.services.agent_service import AgentService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.quality_gate_service import QualityGateService
from app.services.corpus_service import CorpusService
import json


@pytest.fixture
def setup_real_infrastructure():
    """Setup infrastructure for real LLM tests."""
    config = get_config()
    
    # Mock database session
    db_session = AsyncMock(spec=AsyncSession)
    db_session.commit = AsyncMock()
    db_session.rollback = AsyncMock()
    db_session.close = AsyncMock()
    
    # Create LLM Manager mock with realistic responses
    llm_manager = Mock(spec=LLMManager)
    
    async def mock_call_llm(*args, **kwargs):
        return {
            "content": "Based on analysis, reduce costs by switching to efficient models.",
            "tool_calls": []
        }
    
    async def mock_ask_llm(*args, **kwargs):
        return json.dumps({
            "category": "optimization",
            "analysis": "Cost optimization required",
            "recommendations": ["Switch to GPT-3.5 for low-complexity tasks", "Implement caching"]
        })
    
    async def mock_ask_structured_llm(prompt, llm_config_name, schema, **kwargs):
        from app.agents.triage_sub_agent.models import TriageResult
        if schema == TriageResult or hasattr(schema, '__name__') and 'TriageResult' in schema.__name__:
            return TriageResult(
                category="optimization",
                severity="medium",
                analysis="Cost optimization analysis for provided prompt",
                requirements=["cost reduction", "performance maintenance"],
                next_steps=["analyze_costs", "identify_optimization_opportunities"],
                data_needed=["current_costs", "usage_patterns"],
                suggested_tools=["cost_analyzer", "performance_monitor"]
            )
        # For other schemas, return a generic instance
        try:
            return schema()
        except:
            return Mock()
    
    llm_manager.call_llm = mock_call_llm
    llm_manager.ask_llm = mock_ask_llm
    llm_manager.ask_structured_llm = mock_ask_structured_llm
    llm_manager.get = Mock(return_value=Mock())
    
    # Create WebSocket Manager
    websocket_manager = WebSocketManager()
    
    # Create Tool Dispatcher mock
    tool_dispatcher = Mock(spec=ToolDispatcher)
    tool_dispatcher.dispatch_tool = AsyncMock(return_value={
        "status": "success",
        "result": "Tool executed successfully"
    })
    tool_dispatcher.has_tool = Mock(return_value=True)
    
    # Create services
    synthetic_service = SyntheticDataService()
    quality_service = QualityGateService()
    corpus_service = CorpusService()
    
    # Create mock state persistence service
    state_persistence_service = Mock()
    state_persistence_service.save_state = AsyncMock()
    state_persistence_service.load_state = AsyncMock(return_value=None)
    
    # Create mock apex tool selector
    apex_tool_selector = Mock()
    apex_tool_selector.select_tools = AsyncMock(return_value=[])
    apex_tool_selector.dispatch_tool = AsyncMock(return_value={"status": "success"})
    
    # Create Supervisor
    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    
    # Create Agent Service
    agent_service = AgentService(supervisor)
    agent_service.websocket_manager = websocket_manager
    
    return {
        "supervisor": supervisor,
        "agent_service": agent_service,
        "db_session": db_session,
        "llm_manager": llm_manager,
        "websocket_manager": websocket_manager,
        "tool_dispatcher": tool_dispatcher,
        "synthetic_service": synthetic_service,
        "quality_service": quality_service,
        "quality_gate_service": quality_service,  # Alias for test runner
        "corpus_service": corpus_service,
        "state_persistence_service": state_persistence_service,
        "apex_tool_selector": apex_tool_selector,
        "config": config
    }