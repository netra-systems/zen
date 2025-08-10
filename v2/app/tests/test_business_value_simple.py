"""
Simple business value test to debug the RUNNING issue
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import uuid

from app.agents.supervisor import Supervisor
from app.agents.triage_sub_agent import TriageSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_simple_triage_agent():
    """Test just the triage agent to debug the RUNNING issue"""
    
    # Create minimal mocks
    db_session = AsyncMock(spec=AsyncSession)
    
    llm_manager = Mock(spec=LLMManager)
    llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
        "category": "optimization",
        "analysis": "Test"
    }))
    
    # Mock tool dispatcher
    tool_dispatcher = Mock()
    
    # Create triage agent
    triage_agent = TriageSubAgent(llm_manager, tool_dispatcher)
    
    # Create state
    state = DeepAgentState(user_request="Test request")
    
    # Mock websocket manager for agent
    triage_agent.websocket_manager = Mock()
    triage_agent.websocket_manager.send_message = AsyncMock()
    triage_agent.websocket_manager.send_agent_log = AsyncMock()
    triage_agent.user_id = "test_user"
    
    run_id = str(uuid.uuid4())
    
    # Try to execute triage agent directly
    try:
        # The execute method should not raise an exception
        await triage_agent.execute(state, run_id, stream_updates=False)
        print(f"Triage completed successfully. State: {state.triage_result}")
    except Exception as e:
        print(f"Triage failed with error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
    
    # Check state was modified
    assert state.triage_result is not None
    print(f"Final triage result: {state.triage_result}")


@pytest.mark.asyncio 
async def test_supervisor_with_mock_agents():
    """Test supervisor with fully mocked agents"""
    
    # Create mocks
    db_session = AsyncMock(spec=AsyncSession)
    
    llm_manager = Mock(spec=LLMManager)
    llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
        "category": "test",
        "result": "success"
    }))
    
    websocket_manager = Mock()
    websocket_manager.send_message = AsyncMock()
    websocket_manager.send_error = AsyncMock()
    websocket_manager.send_sub_agent_update = AsyncMock()
    websocket_manager.send_agent_log = AsyncMock()
    
    tool_dispatcher = Mock()
    tool_dispatcher.dispatch_tool = AsyncMock(return_value={"status": "success"})
    
    # Create supervisor
    with patch('app.services.state_persistence_service.state_persistence_service'):
        supervisor = Supervisor(db_session, llm_manager, websocket_manager, tool_dispatcher)
        supervisor.thread_id = str(uuid.uuid4())
        supervisor.user_id = str(uuid.uuid4())
    
    run_id = str(uuid.uuid4())
    
    # Mock all agents to just pass through
    if hasattr(supervisor, '_impl') and supervisor._impl:
        impl = supervisor._impl
        if hasattr(impl, 'agents'):
            # For consolidated implementation with agents dict
            for name, agent in impl.agents.items():
                print(f"Mocking agent: {name}")
                # Create a proper async mock that doesn't raise
                async def mock_execute(state, rid, stream):
                    print(f"Mock execute called for agent")
                    # Don't return anything, execute returns None
                    pass
                agent.execute = mock_execute
        elif hasattr(impl, 'sub_agents'):
            # For legacy with sub_agents list
            for agent in impl.sub_agents:
                print(f"Mocking agent: {agent.name}")
                async def mock_execute(state, rid, stream):
                    print(f"Mock execute called for {agent.name}")
                    pass
                agent.execute = mock_execute
    
    # Try to run supervisor
    try:
        with patch('app.services.state_persistence_service.state_persistence_service.save_agent_state', AsyncMock()):
            with patch('app.services.state_persistence_service.state_persistence_service.load_agent_state', AsyncMock(return_value=None)):
                with patch('app.services.state_persistence_service.state_persistence_service.get_thread_context', AsyncMock(return_value=None)):
                    result = await supervisor.run("Test request", run_id, stream_updates=False)
                    print(f"Supervisor completed. Result: {result}")
    except Exception as e:
        print(f"Supervisor failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Check what the actual error is
        if str(e) == "RUNNING":
            print("ERROR: The string 'RUNNING' is being raised as an exception!")
            print("This suggests the agent state enum value is being raised instead of a proper exception")


if __name__ == "__main__":
    asyncio.run(test_simple_triage_agent())
    asyncio.run(test_supervisor_with_mock_agents())