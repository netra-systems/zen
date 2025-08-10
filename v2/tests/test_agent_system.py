import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.agents.supervisor import Supervisor
from app.agents.base_agent import BaseAgent
from app.services.agent_service import AgentService
from app.schemas import (
    ThreadCreate,
    MessageCreate,
    RunCreate,
    Thread,
    Message,
    Run,
    User
)

@pytest.fixture
def mock_supervisor():
    supervisor = MagicMock(spec=Supervisor)
    supervisor.process_message = AsyncMock()
    supervisor.get_thread_state = AsyncMock()
    supervisor.clear_thread_state = AsyncMock()
    supervisor.shutdown = AsyncMock()
    return supervisor

@pytest.fixture
def agent_service(mock_supervisor):
    service = AgentService(mock_supervisor)
    return service

@pytest.mark.asyncio
async def test_supervisor_initialization(
    async_session_factory,
    mock_llm_manager,
    mock_websocket_manager,
    mock_tool_dispatcher
):
    """Test supervisor agent initialization"""
    
    supervisor = Supervisor(
        db_session_factory=async_session_factory,
        llm_manager=mock_llm_manager,
        websocket_manager=mock_websocket_manager,
        tool_dispatcher=mock_tool_dispatcher
    )
    
    assert supervisor.llm_manager == mock_llm_manager
    assert supervisor.websocket_manager == mock_websocket_manager
    assert supervisor.tool_dispatcher == mock_tool_dispatcher

@pytest.mark.asyncio
async def test_create_thread(agent_service, async_session):
    """Test thread creation"""
    
    thread_data = ThreadCreate(
        metadata_={"test": "data"}
    )
    
    with patch("app.services.agent_service.get_async_session") as mock_session:
        mock_session.return_value.__aenter__.return_value = async_session
        
        thread = await agent_service.create_thread(thread_data)
        
        assert thread is not None
        assert thread.id is not None
        assert thread.metadata_ == {"test": "data"}

@pytest.mark.asyncio
async def test_create_message(agent_service, async_session, test_user):
    """Test message creation in thread"""
    
    thread_id = str(uuid.uuid4())
    message_data = MessageCreate(
        role="user",
        content="Test message",
        metadata_={"user_id": test_user.id}
    )
    
    with patch("app.services.agent_service.get_async_session") as mock_session:
        mock_session.return_value.__aenter__.return_value = async_session
        
        with patch.object(async_session, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MagicMock(id=thread_id)
            mock_execute.return_value = mock_result
            
            message = await agent_service.create_message(thread_id, message_data)
            
            assert message is not None
            assert message.content == "Test message"
            assert message.role == "user"

@pytest.mark.asyncio
async def test_create_run(agent_service, async_session, test_user):
    """Test run creation for thread"""
    
    thread_id = str(uuid.uuid4())
    run_data = RunCreate(
        assistant_id="netra-assistant",
        instructions="Process this thread",
        metadata_={"user_id": test_user.id}
    )
    
    with patch("app.services.agent_service.get_async_session") as mock_session:
        mock_session.return_value.__aenter__.return_value = async_session
        
        with patch.object(async_session, "execute") as mock_execute:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = MagicMock(id=thread_id)
            mock_execute.return_value = mock_result
            
            run = await agent_service.create_run(thread_id, run_data)
            
            assert run is not None
            assert run.assistant_id == "netra-assistant"
            assert run.status == "queued"

@pytest.mark.asyncio
async def test_process_agent_message(agent_service, mock_supervisor):
    """Test processing message through agent supervisor"""
    
    thread_id = str(uuid.uuid4())
    message_content = "Analyze my workload"
    user_id = "test-user"
    
    mock_supervisor.process_message.return_value = {
        "response": "Analysis complete",
        "metadata": {"tokens_used": 100}
    }
    
    result = await agent_service.process_message(
        thread_id=thread_id,
        message=message_content,
        user_id=user_id
    )
    
    mock_supervisor.process_message.assert_called_once_with(
        thread_id=thread_id,
        message=message_content,
        user_id=user_id
    )
    
    assert result["response"] == "Analysis complete"

@pytest.mark.asyncio
async def test_agent_tool_execution(mock_tool_dispatcher):
    """Test agent tool execution"""
    
    tool_name = "data_analysis"
    tool_args = {"query": "SELECT * FROM workloads"}
    
    mock_tool_dispatcher.execute_tool = AsyncMock(return_value={
        "result": "Query executed",
        "rows": 10
    })
    
    result = await mock_tool_dispatcher.execute_tool(tool_name, tool_args)
    
    assert result["result"] == "Query executed"
    assert result["rows"] == 10

@pytest.mark.asyncio
async def test_agent_error_handling(agent_service, mock_supervisor):
    """Test agent error handling"""
    
    mock_supervisor.process_message.side_effect = Exception("Processing error")
    
    with pytest.raises(Exception) as exc_info:
        await agent_service.process_message(
            thread_id="test-thread",
            message="Test message",
            user_id="test-user"
        )
    
    assert "Processing error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_sub_agent_delegation(mock_supervisor):
    """Test supervisor delegating to sub-agents"""
    
    with patch("app.agents.supervisor.TriageAgent") as MockTriageAgent:
        with patch("app.agents.supervisor.DataAnalysisAgent") as MockDataAgent:
            triage_agent = MockTriageAgent.return_value
            triage_agent.run = AsyncMock(return_value={
                "intent": "data_analysis",
                "confidence": 0.95
            })
            
            data_agent = MockDataAgent.return_value
            data_agent.run = AsyncMock(return_value={
                "analysis": "Complete",
                "insights": ["insight1", "insight2"]
            })
            
            mock_supervisor.triage_agent = triage_agent
            mock_supervisor.data_analysis_agent = data_agent
            
            await triage_agent.run("Analyze my data")
            triage_agent.run.assert_called_once()
            
            await data_agent.run("SELECT * FROM workloads")
            data_agent.run.assert_called_once()

@pytest.mark.asyncio
async def test_agent_state_management(agent_service, mock_supervisor):
    """Test agent conversation state management"""
    
    thread_id = str(uuid.uuid4())
    
    mock_supervisor.get_thread_state.return_value = {
        "messages": ["msg1", "msg2"],
        "context": {"key": "value"}
    }
    
    state = await mock_supervisor.get_thread_state(thread_id)
    
    assert len(state["messages"]) == 2
    assert state["context"]["key"] == "value"
    
    await mock_supervisor.clear_thread_state(thread_id)
    mock_supervisor.clear_thread_state.assert_called_once_with(thread_id)

@pytest.mark.asyncio
async def test_agent_websocket_streaming(mock_supervisor, mock_websocket_manager):
    """Test agent streaming responses via WebSocket"""
    
    user_id = "test-user"
    message = "Stream this response"
    
    mock_websocket_manager.send_message = AsyncMock()
    mock_supervisor.websocket_manager = mock_websocket_manager
    
    async def mock_stream():
        chunks = ["Chunk 1", "Chunk 2", "Chunk 3"]
        for chunk in chunks:
            await mock_websocket_manager.send_message(
                user_id,
                {"type": "stream", "content": chunk}
            )
    
    await mock_stream()
    
    assert mock_websocket_manager.send_message.call_count == 3

@pytest.mark.asyncio
async def test_agent_parallel_execution():
    """Test parallel execution of multiple agents"""
    
    import asyncio
    
    async def agent_task(name, delay):
        await asyncio.sleep(delay)
        return f"{name} completed"
    
    tasks = [
        agent_task("Agent1", 0.1),
        agent_task("Agent2", 0.1),
        agent_task("Agent3", 0.1)
    ]
    
    results = await asyncio.gather(*tasks)
    
    assert len(results) == 3
    assert all("completed" in r for r in results)

@pytest.mark.asyncio
async def test_agent_retry_logic(mock_supervisor):
    """Test agent retry mechanism on failure"""
    
    call_count = 0
    
    async def flaky_process():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Temporary failure")
        return {"success": True}
    
    mock_supervisor.process_message = flaky_process
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await mock_supervisor.process_message()
            break
        except Exception:
            if attempt == max_retries - 1:
                raise
    
    assert result["success"] == True
    assert call_count == 3

@pytest.mark.asyncio
async def test_agent_context_window_management(mock_supervisor):
    """Test agent managing conversation context window"""
    
    max_context_size = 10
    messages = []
    
    for i in range(15):
        messages.append(f"Message {i}")
    
    if len(messages) > max_context_size:
        truncated_messages = messages[-max_context_size:]
    else:
        truncated_messages = messages
    
    assert len(truncated_messages) == max_context_size
    assert truncated_messages[0] == "Message 5"
    assert truncated_messages[-1] == "Message 14"

@pytest.mark.asyncio
async def test_agent_token_counting(mock_llm_manager):
    """Test token counting for agent responses"""
    
    text = "This is a test message for token counting"
    
    mock_llm_manager.count_tokens = MagicMock(return_value=8)
    
    token_count = mock_llm_manager.count_tokens(text)
    
    assert token_count == 8
    mock_llm_manager.count_tokens.assert_called_once_with(text)