import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.supervisor import SupervisorAgent
from app.schemas.Agent import AgentRequest, AgentResponse, AgentStatus

@pytest.mark.asyncio
async def test_supervisor_error_handling():
    with patch('app.agents.supervisor.TriageAgent') as mock_triage:
        mock_triage.side_effect = Exception("Agent initialization failed")
        
        supervisor = SupervisorAgent()
        request = AgentRequest(
            message="Test message",
            thread_id="thread_123",
            user_id="user_456"
        )
        
        with pytest.raises(Exception):
            await supervisor.process(request)

@pytest.mark.asyncio
async def test_supervisor_state_management():
    supervisor = SupervisorAgent()
    
    initial_state = supervisor.get_state()
    assert initial_state == {}
    
    supervisor.update_state({"context": "test", "session_id": "123"})
    updated_state = supervisor.get_state()
    assert updated_state["context"] == "test"
    assert updated_state["session_id"] == "123"
    
    supervisor.clear_state()
    assert supervisor.get_state() == {}

@pytest.mark.asyncio
async def test_supervisor_concurrent_requests():
    supervisor = SupervisorAgent()
    
    with patch.object(supervisor, 'process_with_agents', new_callable=AsyncMock) as mock_process:
        mock_process.return_value = AgentResponse(
            status=AgentStatus.COMPLETED,
            result="Processed",
            metadata={}
        )
        
        requests = [
            AgentRequest(message=f"Message {i}", thread_id=f"thread_{i}", user_id="user")
            for i in range(5)
        ]
        
        import asyncio
        responses = await asyncio.gather(*[supervisor.process(req) for req in requests])
        
        assert len(responses) == 5
        assert all(r.status == AgentStatus.COMPLETED for r in responses)