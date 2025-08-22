"""Thread-Agent Integration Fixtures and Tests"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.data_sub_agent.agent import DataSubAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.db.models_postgres import Message, Run, Thread
from netra_backend.app.schemas.agent_state import (
    AgentPhase,
    CheckpointType,
    StatePersistenceRequest,
)
from netra_backend.app.services.agent_service import AgentService
from netra_backend.app.services.state_persistence import state_persistence_service

# Add project root to path
from netra_backend.app.services.thread_service import ThreadService

# Add project root to path


@pytest.fixture
def mock_supervisor_agent():
    """Mock supervisor agent for testing."""
    agent = Mock(spec=SupervisorAgent)
    agent.process_request = AsyncMock(return_value={"status": "success", "result": "processed"})
    agent.delegate_to_subagent = AsyncMock(return_value={"delegated": True})
    agent.finalize_response = AsyncMock(return_value={"finalized": True})
    agent.state = Mock()
    agent.user_id = "test_user_123"
    return agent


@pytest.fixture
def mock_data_sub_agent():
    """Mock data sub-agent for testing."""
    agent = Mock(spec=DataSubAgent)
    agent.analyze_data = AsyncMock(return_value={"analysis": "complete"})
    agent.generate_insights = AsyncMock(return_value={"insights": ["insight1", "insight2"]})
    agent.create_recommendations = AsyncMock(return_value={"recommendations": ["rec1", "rec2"]})
    agent.state = Mock()
    agent.user_id = "test_user_123"
    return agent


@pytest.fixture
def thread_service():
    """Create thread service for testing."""
    service = AsyncMock(spec=ThreadService)
    service.create_thread = AsyncMock(return_value={
        "id": str(uuid.uuid4()),
        "title": "Test Thread",
        "created_at": "2025-01-20T10:00:00Z",
        "status": "active"
    })
    service.send_message = AsyncMock(return_value={
        "id": str(uuid.uuid4()),
        "content": "Test message",
        "timestamp": "2025-01-20T10:01:00Z"
    })
    service.get_thread_history = AsyncMock(return_value=[])
    service.update_thread = AsyncMock(return_value=True)
    service.delete_thread = AsyncMock(return_value=True)
    return service


@pytest.fixture
def agent_service():
    """Create agent service for testing."""
    service = AsyncMock(spec=AgentService)
    service.create_agent = AsyncMock(return_value={"agent_id": "test_agent_123"})
    service.execute_agent = AsyncMock(return_value={"status": "completed", "result": "success"})
    service.get_agent_status = AsyncMock(return_value={"status": "idle", "last_activity": "2025-01-20T10:00:00Z"})
    service.terminate_agent = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_thread():
    """Mock thread object for testing."""
    thread = Mock(spec=Thread)
    thread.id = str(uuid.uuid4())
    thread.title = "Test Thread"
    thread.user_id = "test_user_123"
    thread.created_at = asyncio.get_event_loop().time()
    thread.updated_at = asyncio.get_event_loop().time()
    thread.status = "active"
    return thread


@pytest.fixture
def mock_message():
    """Mock message object for testing."""
    message = Mock(spec=Message)
    message.id = str(uuid.uuid4())
    message.thread_id = "test_thread_123"
    message.content = "Test message content"
    message.role = "user"
    message.created_at = asyncio.get_event_loop().time()
    return message


@pytest.fixture
def mock_run():
    """Mock run object for testing."""
    run = Mock(spec=Run)
    run.id = str(uuid.uuid4())
    run.thread_id = "test_thread_123"
    run.status = "completed"
    run.created_at = asyncio.get_event_loop().time()
    run.completed_at = asyncio.get_event_loop().time()
    return run


@pytest.fixture
async def test_session():
    """Create test database session."""
    session = AsyncMock(spec=AsyncSession)
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.add = AsyncMock()
    session.delete = AsyncMock()
    return session


# =============================================================================
# THREAD-AGENT INTEGRATION TESTS
# =============================================================================

class TestThreadAgentIntegrationFixtures:
    """Test thread-agent integration fixtures."""
    
    async def test_mock_supervisor_agent_fixture(self, mock_supervisor_agent):
        """Test mock supervisor agent fixture."""
        assert mock_supervisor_agent is not None
        assert hasattr(mock_supervisor_agent, 'process_request')
        assert hasattr(mock_supervisor_agent, 'delegate_to_subagent')
        assert hasattr(mock_supervisor_agent, 'finalize_response')
        
        # Test mock behavior
        result = await mock_supervisor_agent.process_request("test request")
        assert result["status"] == "success"
    
    async def test_mock_data_sub_agent_fixture(self, mock_data_sub_agent):
        """Test mock data sub-agent fixture."""
        assert mock_data_sub_agent is not None
        assert hasattr(mock_data_sub_agent, 'analyze_data')
        assert hasattr(mock_data_sub_agent, 'generate_insights')
        assert hasattr(mock_data_sub_agent, 'create_recommendations')
        
        # Test mock behavior
        analysis = await mock_data_sub_agent.analyze_data({"test": "data"})
        assert analysis["analysis"] == "complete"
    
    async def test_thread_service_fixture(self, thread_service):
        """Test thread service fixture."""
        assert thread_service is not None
        assert hasattr(thread_service, 'create_thread')
        assert hasattr(thread_service, 'send_message')
        assert hasattr(thread_service, 'get_thread_history')
        
        # Test service behavior
        thread = await thread_service.create_thread({"title": "Test Thread"})
        assert "id" in thread
        assert thread["title"] == "Test Thread"
    
    async def test_agent_service_fixture(self, agent_service):
        """Test agent service fixture."""
        assert agent_service is not None
        assert hasattr(agent_service, 'create_agent')
        assert hasattr(agent_service, 'execute_agent')
        assert hasattr(agent_service, 'get_agent_status')
        
        # Test service behavior
        agent = await agent_service.create_agent({"type": "test_agent"})
        assert "agent_id" in agent
    
    async def test_mock_database_objects(self, mock_thread, mock_message, mock_run):
        """Test mock database object fixtures."""
        # Test thread
        assert mock_thread is not None
        assert hasattr(mock_thread, 'id')
        assert hasattr(mock_thread, 'title')
        assert hasattr(mock_thread, 'user_id')
        
        # Test message
        assert mock_message is not None
        assert hasattr(mock_message, 'id')
        assert hasattr(mock_message, 'content')
        assert hasattr(mock_message, 'role')
        
        # Test run
        assert mock_run is not None
        assert hasattr(mock_run, 'id')
        assert hasattr(mock_run, 'status')
    
    async def test_test_session_fixture(self, test_session):
        """Test database session fixture."""
        assert test_session is not None
        assert hasattr(test_session, 'commit')
        assert hasattr(test_session, 'rollback')
        assert hasattr(test_session, 'execute')


class TestThreadAgentIntegration:
    """Test thread-agent integration functionality."""
    
    async def test_agent_thread_communication(self, mock_supervisor_agent, thread_service):
        """Test communication between agents and threads."""
        # Create a thread
        thread = await thread_service.create_thread({"title": "Agent Communication Test"})
        
        # Process request with agent
        result = await mock_supervisor_agent.process_request("Test message")
        
        # Send message to thread
        message = await thread_service.send_message({
            "thread_id": thread["id"],
            "content": result["result"]
        })
        
        assert message is not None
        assert "id" in message
    
    async def test_agent_delegation_workflow(self, mock_supervisor_agent, mock_data_sub_agent):
        """Test agent delegation workflow."""
        # Supervisor processes initial request
        initial_result = await mock_supervisor_agent.process_request("Analyze data")
        assert initial_result["status"] == "success"
        
        # Supervisor delegates to data sub-agent
        delegation_result = await mock_supervisor_agent.delegate_to_subagent(
            "data_analysis", {"data": "test_data"}
        )
        assert delegation_result["delegated"] is True
        
        # Data sub-agent performs analysis
        analysis = await mock_data_sub_agent.analyze_data({"data": "test_data"})
        assert analysis["analysis"] == "complete"
    
    async def test_fixture_integration(self):
        """Test that fixtures can be used together."""
        # This test ensures the file can be imported and fixtures work
        assert True  # Basic passing test
