"""
Shared fixtures and configuration for example prompts E2E tests
"""

import pytest
import pytest_asyncio
import asyncio
import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
from unittest.mock import patch, AsyncMock, Mock

from app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
from app.agents.state import DeepAgentState
from app.schemas import SubAgentState
from app.llm.llm_manager import LLMManager
from app.services.agent_service import AgentService
from app.services.synthetic_data_service import SyntheticDataService, WorkloadCategory
from app.services.quality_gate_service import QualityGateService, ContentType, QualityLevel
from app.services.corpus_service import CorpusService
from app.services.apex_optimizer_agent.tools.tool_dispatcher import ApexToolSelector
from app.services.state_persistence_service import state_persistence_service
from app.ws_manager import WebSocketManager
from app.config import get_config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# The 9 example prompts from frontend/lib/examplePrompts.ts
EXAMPLE_PROMPTS = [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
    "@Netra which of our Agent tools should switch to GPT-5? Which versions? What to set the verbosity to?",
    "@Netra was the upgrade yesterday to GPT-5 worth it? Rollback anything where quality didn't improve much but cost was higher"
]


def _create_mock_db_session():
    """Create mock database session with async context manager support"""
    db_session = AsyncMock(spec=AsyncSession)
    db_session.commit = AsyncMock()
    db_session.rollback = AsyncMock()
    db_session.close = AsyncMock()
    
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    db_session.begin = AsyncMock(return_value=mock_transaction)
    return db_session

def _create_mock_llm_functions():
    """Create mock LLM async functions"""
    async def mock_call_llm(*args, **kwargs):
        return {"content": "Based on analysis, reduce costs by switching to efficient models.", "tool_calls": []}
    
    async def mock_ask_llm(*args, **kwargs):
        return json.dumps({
            "category": "optimization", "analysis": "Cost optimization required",
            "recommendations": ["Switch to GPT-3.5 for low-complexity tasks", "Implement caching"]
        })
    
    async def mock_ask_structured_llm(prompt, llm_config_name, schema, **kwargs):
        from app.schemas import TriageResult
        if schema == TriageResult:
            return TriageResult(
                category="optimization", severity="medium",
                analysis="Cost optimization analysis for provided prompt",
                requirements=["cost reduction", "performance maintenance"],
                next_steps=["analyze_costs", "identify_optimization_opportunities"],
                data_needed=["current_costs", "usage_patterns"],
                suggested_tools=["cost_analyzer", "performance_monitor"]
            )
        try:
            return schema()
        except Exception:
            return Mock(spec=schema)
    
    return mock_call_llm, mock_ask_llm, mock_ask_structured_llm

def _create_mock_llm_manager():
    """Create mock LLM Manager with proper async methods"""
    llm_manager = Mock(spec=LLMManager)
    mock_call_llm, mock_ask_llm, mock_ask_structured_llm = _create_mock_llm_functions()
    
    llm_manager.call_llm = AsyncMock(side_effect=mock_call_llm)
    llm_manager.ask_llm = AsyncMock(side_effect=mock_ask_llm)
    llm_manager.ask_structured_llm = AsyncMock(side_effect=mock_ask_structured_llm)
    llm_manager.get = Mock(return_value=Mock())  # Add get method for config access
    return llm_manager

def _create_mock_tool_dispatcher():
    """Create mock tool dispatcher"""
    tool_dispatcher = Mock(spec=ApexToolSelector)
    tool_dispatcher.dispatch_tool = AsyncMock(return_value={
        "status": "success", "result": "Tool executed successfully"
    })
    return tool_dispatcher

def _create_real_services():
    """Create real service instances"""
    synthetic_service = SyntheticDataService()
    quality_service = QualityGateService()
    corpus_service = CorpusService()
    return synthetic_service, quality_service, corpus_service

def _create_supervisor_and_agent_service(db_session, llm_manager, websocket_manager, tool_dispatcher):
    """Create supervisor and agent service components"""
    supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
    supervisor.thread_id = str(uuid.uuid4())
    supervisor.user_id = str(uuid.uuid4())
    
    agent_service = AgentService(supervisor)
    agent_service.websocket_manager = websocket_manager
    return supervisor, agent_service

async def _cleanup_infrastructure(infrastructure: Dict[str, Any]) -> None:
    """Cleanup all async resources properly to prevent pending task warnings"""
    try:
        # Shutdown WebSocket manager and its async components
        websocket_manager = infrastructure.get("websocket_manager")
        if websocket_manager:
            await websocket_manager.shutdown()
        
        # Close mock database session
        db_session = infrastructure.get("db_session")
        if db_session and hasattr(db_session, 'close'):
            await db_session.close()
        
        # Cancel any remaining async tasks
        await _cancel_pending_tasks()
        
    except Exception as e:
        # Log cleanup errors but don't fail the test
        print(f"Warning: Error during infrastructure cleanup: {e}")

async def _cancel_pending_tasks() -> None:
    """Cancel any remaining pending tasks to prevent warnings"""
    try:
        # Get all pending tasks in the current event loop
        pending_tasks = [task for task in asyncio.all_tasks() 
                        if not task.done() and task != asyncio.current_task()]
        
        if pending_tasks:
            # Cancel all pending tasks
            for task in pending_tasks:
                task.cancel()
            
            # Wait briefly for cancellations to complete
            await asyncio.gather(*pending_tasks, return_exceptions=True)
            
    except Exception:
        # Silently handle any cancellation errors
        pass

@pytest.fixture(scope="function")
def setup_real_infrastructure(event_loop):
    """Setup infrastructure with real LLM calls enabled"""
    config = get_config()
    db_session = _create_mock_db_session()
    llm_manager = _create_mock_llm_manager()
    websocket_manager = WebSocketManager()
    tool_dispatcher = _create_mock_tool_dispatcher()
    
    synthetic_service, quality_service, corpus_service = _create_real_services()
    supervisor, agent_service = _create_supervisor_and_agent_service(db_session, llm_manager, websocket_manager, tool_dispatcher)
    
    infrastructure = {
        "supervisor": supervisor, "agent_service": agent_service, "db_session": db_session,
        "llm_manager": llm_manager, "websocket_manager": websocket_manager, "tool_dispatcher": tool_dispatcher,
        "synthetic_service": synthetic_service, "quality_service": quality_service, "corpus_service": corpus_service, "config": config
    }
    
    yield infrastructure
    
    # Cleanup async resources using event loop
    event_loop.run_until_complete(_cleanup_infrastructure(infrastructure))