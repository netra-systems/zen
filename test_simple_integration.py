"""
Simple integration test to validate basic split architecture functionality.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock

from netra_backend.app.agents.supervisor.agent_class_registry import create_test_registry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.models.user_execution_context import UserExecutionContext


class SimpleTestAgent(BaseAgent):
    """Simple test agent for validation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_count = 0
    
    async def execute(self, state, run_id):
        self.execution_count += 1
        return state


@pytest.mark.asyncio
async def test_agent_class_registry_basic():
    """Test basic AgentClassRegistry functionality."""
    registry = create_test_registry()
    
    # Register agent
    registry.register("test_agent", SimpleTestAgent, "Test agent")
    registry.freeze()
    
    # Verify registration
    assert registry.has_agent_class("test_agent")
    assert registry.get_agent_class("test_agent") == SimpleTestAgent
    assert registry.is_frozen()


@pytest.mark.asyncio
async def test_user_execution_context_validation():
    """Test UserExecutionContext validation."""
    # Valid context
    context = UserExecutionContext(
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run",
        request_id="test_request"
    )
    
    assert context.user_id == "test_user"
    assert context.thread_id == "test_thread"
    assert context.run_id == "test_run"
    
    # Invalid context
    with pytest.raises(ValueError):
        UserExecutionContext(
            user_id="None",  # Invalid
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )


@pytest.mark.asyncio
async def test_basic_agent_instance_factory():
    """Test basic AgentInstanceFactory functionality."""
    # Create mock dependencies
    mock_registry = MagicMock()
    mock_registry.get = MagicMock(return_value=SimpleTestAgent())
    mock_registry.llm_manager = MagicMock()
    mock_registry.tool_dispatcher = MagicMock()
    
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
    mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    mock_websocket_bridge.unregister_run_mapping = AsyncMock(return_value=True)
    
    # Create factory
    factory = AgentInstanceFactory()
    factory.configure(mock_registry, mock_websocket_bridge)
    
    # Create mock session
    mock_session = MagicMock()
    
    # Test context creation
    context = await factory.create_user_execution_context(
        user_id="test_user",
        thread_id="test_thread", 
        run_id="test_run",
        db_session=mock_session
    )
    
    assert context.user_id == "test_user"
    assert context.db_session == mock_session
    assert context.websocket_emitter is not None
    
    # Test agent creation
    agent = await factory.create_agent_instance("test_agent", context)
    assert agent is not None
    
    # Test cleanup
    await factory.cleanup_user_context(context)
    assert context._is_cleaned


if __name__ == "__main__":
    asyncio.run(test_agent_class_registry_basic())
    asyncio.run(test_user_execution_context_validation())
    asyncio.run(test_basic_agent_instance_factory())
    print("✅ All simple integration tests passed!")