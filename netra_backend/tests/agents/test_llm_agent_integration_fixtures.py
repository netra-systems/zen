"""Fixtures Tests - Split from test_llm_agent_integration.py"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.triage.unified_triage_agent import (
    Complexity,
    ExtractedEntities,
    Priority,
    TriageMetadata,
    TriageResult,
    UserIntent,
)
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service import AgentService

@pytest.fixture
def mock_llm_manager():
        """Create properly mocked LLM manager"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        llm_manager = Mock(spec=LLMManager)
        
        # Mock standard LLM responses
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager.call_llm = AsyncMock(return_value={
            "content": "I'll help you optimize your AI workload",
            "tool_calls": []
        })
        
        # Mock structured responses for triage
        # Mock: LLM provider isolation to prevent external API usage and costs
        llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
            "category": "optimization",
            "confidence": 0.95,
            "requires_data": True,
            "requires_optimization": True,
            "requires_actions": True,
            "analysis": "User needs AI workload optimization"
        }))
        
        # Mock structured LLM for triage agent
        from netra_backend.app.agents.triage.unified_triage_agent import (
            Complexity,
            ExtractedEntities,
            Priority,
            TriageMetadata,
            TriageResult,
            UserIntent,
        )
        
        # Mock: LLM provider isolation to prevent external API usage and costs
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
    # Mock: Database session isolation for transaction testing without real database dependency
    session = AsyncMock(spec=AsyncSession)
    # Mock: Session isolation for controlled testing without external state
    session.commit = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.rollback = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.close = AsyncMock()
    # Mock: Session isolation for controlled testing without external state
    session.execute = AsyncMock()
    return session

@pytest.fixture
def mock_websocket_manager():
    """Create mock WebSocket manager"""
    # Mock: Generic component isolation for controlled unit testing
    ws_manager = Mock()
    # Mock: Generic component isolation for controlled unit testing
    ws_manager.send_message = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    ws_manager.broadcast = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    ws_manager.send_agent_log = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    ws_manager.send_error = AsyncMock()
    # Mock: Generic component isolation for controlled unit testing
    ws_manager.send_sub_agent_update = AsyncMock()
    return ws_manager

@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher"""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    dispatcher = Mock(spec=ToolDispatcher)
    # Mock: Async component isolation for testing without real async operations
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
        with patch('netra_backend.app.agents.supervisor_consolidated.state_persistence_service') as mock_persistence:
            mock_persistence.save_agent_state = AsyncMock(return_value=True)
            mock_persistence.load_agent_state = AsyncMock(return_value=None)
            # Mock: Async component isolation for testing without real async operations
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
