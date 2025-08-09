import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent_service import AgentService
from app.schemas.Agent import AgentRequest, AgentResponse, AgentStatus
from app.agents.supervisor import SupervisorAgent

@pytest.mark.asyncio
async def test_agent_service_initialization():
    with patch('app.services.agent_service.SupervisorAgent') as mock_supervisor:
        service = AgentService()
        assert service.supervisor is not None
        assert service.active_sessions == {}

@pytest.mark.asyncio
async def test_agent_service_process_request():
    with patch('app.services.agent_service.SupervisorAgent') as mock_supervisor:
        mock_instance = AsyncMock()
        mock_instance.process.return_value = AgentResponse(
            status=AgentStatus.COMPLETED,
            result="Test result",
            metadata={"tool_calls": 2}
        )
        mock_supervisor.return_value = mock_instance
        
        service = AgentService()
        request = AgentRequest(
            message="Test message",
            thread_id="thread_123",
            user_id="user_456"
        )
        
        response = await service.process_request(request)
        assert response.status == AgentStatus.COMPLETED
        assert response.result == "Test result"
        mock_instance.process.assert_called_once()

@pytest.mark.asyncio
async def test_agent_service_session_management():
    service = AgentService()
    
    session_id = await service.create_session("user_123", {"context": "test"})
    assert session_id in service.active_sessions
    assert service.active_sessions[session_id]['user_id'] == "user_123"
    
    await service.end_session(session_id)
    assert session_id not in service.active_sessions