"""Fixtures Tests - Split from test_thread_agent_integration.py"""

import pytest
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.thread_service import ThreadService
from app.services.agent_service import AgentService
from app.services.state_persistence import state_persistence_service
from app.agents.supervisor_consolidated import SupervisorAgent
from app.agents.data_sub_agent.agent import DataSubAgent
from app.schemas.agent_state import StatePersistenceRequest, CheckpointType, AgentPhase
from app.db.models_postgres import Thread, Message, Run
from app.core.exceptions_agent import AgentError

def mock_supervisor_agent():
    """Mock supervisor agent for testing."""
    agent = Mock(spec=SupervisorAgent)
    agent.process_request = AsyncMock()
    agent.delegate_to_subagent = AsyncMock()
    agent.finalize_response = AsyncMock()
    return agent

def mock_data_sub_agent():
    """Mock data sub-agent for testing."""
    agent = Mock(spec=DataSubAgent)
    agent.analyze_data = AsyncMock()
    agent.generate_insights = AsyncMock()
    agent.create_recommendations = AsyncMock()
    return agent
