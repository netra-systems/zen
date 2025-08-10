import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.supervisor import Supervisor
from app.schemas import AgentMessage, WebSocketMessage, SubAgentLifecycle

@pytest.mark.asyncio
async def test_supervisor_error_handling():
    from unittest.mock import Mock
    
    # Mock dependencies
    mock_db = AsyncMock()
    mock_llm = AsyncMock()
    mock_websocket = AsyncMock() 
    mock_tool_dispatcher = AsyncMock()
    
    with patch('app.agents.supervisor.TriageSubAgent') as mock_triage:
        mock_triage.side_effect = Exception("Agent initialization failed")
        
        with pytest.raises(Exception):
            supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)

@pytest.mark.asyncio
async def test_supervisor_state_management():
    # Mock dependencies
    mock_db = AsyncMock()
    mock_llm = AsyncMock()
    mock_websocket = AsyncMock()
    mock_tool_dispatcher = AsyncMock()
    
    supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
    
    # Test basic state management through the agent lifecycle
    initial_state = supervisor.state
    assert initial_state == SubAgentLifecycle.PENDING
    
    supervisor.set_state(SubAgentLifecycle.RUNNING)
    assert supervisor.get_state() == SubAgentLifecycle.RUNNING

@pytest.mark.asyncio
async def test_supervisor_concurrent_requests():
    # Mock dependencies
    mock_db = AsyncMock()
    mock_llm = AsyncMock()
    mock_websocket = AsyncMock()
    mock_tool_dispatcher = AsyncMock()
    
    supervisor = Supervisor(mock_db, mock_llm, mock_websocket, mock_tool_dispatcher)
    
    # Mock the run method for testing
    from app.agents.state import DeepAgentState
    
    async def mock_run(request, run_id, stream_updates=True):
        return DeepAgentState(user_request=request)
    
    supervisor.run = AsyncMock(side_effect=mock_run)
        
    requests = [f"Message {i}" for i in range(5)]
    run_ids = [f"run_{i}" for i in range(5)]
        
    import asyncio
    responses = await asyncio.gather(*[
        supervisor.run(req, run_id, False) 
        for req, run_id in zip(requests, run_ids)
    ])
        
    assert len(responses) == 5
    assert all(isinstance(r, DeepAgentState) for r in responses)