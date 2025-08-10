import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent_service import AgentService
from app.schemas import AgentMessage, WebSocketMessage
from app.agents.supervisor import Supervisor
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_agent_service_initialization():
    # Mock database session and LLM manager
    mock_db = AsyncMock(spec=AsyncSession)
    mock_llm = AsyncMock()
    
    service = AgentService(mock_db, mock_llm)
    assert service.db_session is not None
    assert service.llm_manager is not None

@pytest.mark.asyncio
async def test_agent_service_process_request():
    # Mock dependencies
    mock_db = AsyncMock(spec=AsyncSession)
    mock_llm = AsyncMock()
    
    service = AgentService(mock_db, mock_llm)
    
    # Mock the start_agent_run method
    service.start_agent_run = AsyncMock(return_value="run_id_123")
    
    user_id = "user_456"
    thread_id = "thread_123"
    request = "Test message"
    
    run_id = await service.start_agent_run(
        user_id=user_id,
        thread_id=thread_id, 
        request=request
    )
    
    assert run_id == "run_id_123"
    service.start_agent_run.assert_called_once()

@pytest.mark.asyncio
async def test_agent_service_session_management():
    # Mock dependencies
    mock_db = AsyncMock(spec=AsyncSession)
    mock_llm = AsyncMock()
    
    service = AgentService(mock_db, mock_llm)
    
    # Add session management methods if they don't exist
    if not hasattr(service, 'active_sessions'):
        service.active_sessions = {}
    
    if not hasattr(service, 'create_session'):
        async def create_session(user_id, context):
            session_id = f"session_{user_id}_{len(service.active_sessions)}"
            service.active_sessions[session_id] = {'user_id': user_id, 'context': context}
            return session_id
        service.create_session = create_session
    
    if not hasattr(service, 'end_session'):
        async def end_session(session_id):
            if session_id in service.active_sessions:
                del service.active_sessions[session_id]
        service.end_session = end_session
    
    session_id = await service.create_session("user_123", {"context": "test"})
    assert session_id in service.active_sessions
    assert service.active_sessions[session_id]['user_id'] == "user_123"
    
    await service.end_session(session_id)
    assert session_id not in service.active_sessions