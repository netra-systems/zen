"""Fixtures Tests - Split from test_llm_agent_integration.py"""

import pytest
import pytest_asyncio
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import uuid
from datetime import datetime
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.state import DeepAgentState
from llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService
from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.agents.triage_sub_agent import (
    TriageResult, Priority, Complexity, UserIntent,
    ExtractedEntities, TriageMetadata
)
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
import time


@pytest.fixture
def mock_llm_manager():
        """Create properly mocked LLM manager"""
        llm_manager = Mock(spec=LLMManager)
        
        # Mock standard LLM responses
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "I'll help you optimize your AI workload",
            "tool_calls": []
        })
        
        # Mock structured responses for triage
        llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
            "category": "optimization",
            "confidence": 0.95,
            "requires_data": True,
            "requires_optimization": True,
            "requires_actions": True,
            "analysis": "User needs AI workload optimization"
        }))
        
        # Mock structured LLM for triage agent
        from app.agents.triage_sub_agent import (
            TriageResult, Priority, Complexity, UserIntent,
            ExtractedEntities, TriageMetadata
        )
        
        llm_manager.ask_structured_llm = AsyncMock(return_value=TriageResult(
            category="AI Optimization",
            confidence_score=0.95,
            priority=Priority.HIGH,
            complexity=Complexity.MODERATE,
            is_admin_mode=False,
            extracted_entities=ExtractedEntities(
                models_mentioned=["GPT-4", "Claude"],
                metrics_mentioned=["latency", "throughput"],
                time_ranges=[]  # Empty list or proper dict format
            ),
            user_intent=UserIntent(
                primary_intent="optimize",
                secondary_intents=["analyze", "monitor"]
            ),
            tool_recommendations=[],  # Empty list or proper ToolRecommendation objects
            metadata=TriageMetadata(
                triage_duration_ms=150,
                cache_hit=False,
                fallback_used=False,
                retry_count=0
            )
        ))
        
        return llm_manager

@pytest.fixture
def mock_db_session():
    """Create mock database session"""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    return session

@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager"""
    ws_manager = Mock()
    ws_manager.send_message = AsyncMock()
    ws_manager.broadcast = AsyncMock()
    ws_manager.send_agent_log = AsyncMock()
    ws_manager.send_error = AsyncMock()
    ws_manager.send_sub_agent_update = AsyncMock()
    return ws_manager

@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher"""
    from app.agents.tool_dispatcher import ToolDispatcher
    dispatcher = Mock(spec=ToolDispatcher)
    dispatcher.dispatch_tool = AsyncMock(return_value={
        "status": "success",
        "result": {"data": "Tool execution successful"}
    })
    return dispatcher

@pytest.fixture
def supervisor_agent(mock_db_session, mock_llm_manager, 
                    mock_websocket_manager, mock_tool_dispatcher):
        """Create supervisor agent with all dependencies mocked"""
        # Patch state persistence to avoid hanging
        with patch('app.agents.supervisor_consolidated.state_persistence_service') as mock_persistence:
            mock_persistence.save_agent_state = AsyncMock(return_value=True)
            mock_persistence.load_agent_state = AsyncMock(return_value=None)
            mock_persistence.get_thread_context = AsyncMock(return_value=None)
            
            supervisor = SupervisorAgent(
                mock_db_session,
                mock_llm_manager,
                mock_websocket_manager,
                mock_tool_dispatcher
            )
            
            # Set required IDs
            supervisor.thread_id = str(uuid.uuid4())
            supervisor.user_id = str(uuid.uuid4())
            
            # Mock the execution engine to prevent hanging
            supervisor.engine.execute_pipeline = AsyncMock(return_value=[])
            
            return supervisor
