"""
Model Selection Workflow Setup Helpers
Setup functions and fixtures for model selection testing
"""

from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.state import AgentMetadata, DeepAgentState
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core import WebSocketManager
from typing import Dict
import pytest
import uuid

@pytest.fixture

def model_selection_setup(real_llm_manager, real_websocket_manager, real_tool_dispatcher):

    """Setup real agent environment for model selection testing."""
    # Import additional agents to avoid circular dependencies
    from netra_backend.app.agents.actions_to_meet_goals_sub_agent import (

        ActionsToMeetGoalsSubAgent,

    )
    from netra_backend.app.agents.optimizations_core_sub_agent import (

        OptimizationsCoreSubAgent,

    )
    from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
    
    agents = {

        'triage': TriageSubAgent(real_llm_manager, real_tool_dispatcher, None),

        'data': DataSubAgent(real_llm_manager, real_tool_dispatcher),

        'optimization': OptimizationsCoreSubAgent(real_llm_manager, real_tool_dispatcher),

        'actions': ActionsToMeetGoalsSubAgent(real_llm_manager, real_tool_dispatcher),

        'reporting': ReportingSubAgent(real_llm_manager, real_tool_dispatcher)

    }

    return _build_model_setup(agents, real_llm_manager, real_websocket_manager)

async def _create_real_llm_manager() -> LLMManager:

    """Create real LLM manager instance."""

    manager = LLMManager()

    await manager.initialize()

    return manager

def _create_websocket_manager() -> WebSocketManager:

    """Create WebSocket manager instance."""

    return WebSocketManager()

def _create_agent_instances(llm: LLMManager, ws: WebSocketManager) -> Dict:

    """Create agent instances with real LLM."""

    return {

        'triage': TriageSubAgent(llm, None, None),

        'data': DataSubAgent(llm, None),

        'optimization': OptimizationsCoreSubAgent(llm, None),

        'actions': ActionsToMeetGoalsSubAgent(llm, None),

        'reporting': ReportingSubAgent(llm, None)

    }

def _build_model_setup(agents: Dict, llm: LLMManager, ws: WebSocketManager) -> Dict:

    """Build complete setup dictionary."""

    return {

        'agents': agents, 'llm': llm, 'websocket': ws,

        'run_id': str(uuid.uuid4()), 'user_id': 'model-test-user'

    }