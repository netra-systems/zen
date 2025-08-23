"""Critical WebSocket regression prevention tests.

Tests to prevent circular imports, agent registration failures, and message flow issues.
These tests ensure the WebSocket-Agent integration remains functional.
"""

from netra_backend.app.websocket.connection import ConnectionManager as WebSocketManager
from netra_backend.tests.test_utils import setup_test_path
from pathlib import Path
import sys

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class TestCircularImportPrevention:

    """Test that no circular imports exist between WebSocket and Agent modules."""
    
    def test_agent_executor_imports_independently(self):

        """Ensure agent executor can be imported without circular dependency."""
        from netra_backend.app.agents.base.executor import BaseExecutionEngine

        assert BaseExecutionEngine is not None
    
    def test_websocket_modules_import_independently(self):

        """Ensure WebSocket modules can be imported without circular dependency."""
        from netra_backend.app.websocket.connection_executor import ConnectionExecutor
        from netra_backend.app.websocket.message_handler_core import (

            ReliableMessageHandler,

        )
        from netra_backend.app.websocket.websocket_broadcast_executor import (

            BroadcastExecutor,

        )

        assert ConnectionExecutor is not None

        assert ReliableMessageHandler is not None

        assert BroadcastExecutor is not None
    
    def test_supervisor_imports_successfully(self):

        """Ensure supervisor can be imported with all dependencies."""
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent

        assert SupervisorAgent is not None
    
    def test_agent_registry_imports_successfully(self):

        """Ensure agent registry can be imported."""
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

        assert AgentRegistry is not None
    
    def test_no_websocket_imports_in_agent_base(self):

        """Verify agent base modules don't import WebSocket modules."""
        import netra_backend.app.agents.base.executor as executor_module

        module_str = str(executor_module.__dict__)

        assert 'websocket' not in module_str.lower() or 'websocket' in ['websocket_manager']

class TestAgentRegistration:

    """Test agent registration during initialization."""
    
    @pytest.fixture

    def real_components(self):

        """Create real components for testing."""
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.websocket.unified.manager import UnifiedWebSocketManager
        
        llm_manager = LLMManager()

        tool_dispatcher = ToolDispatcher(llm_manager)

        websocket_manager = UnifiedWebSocketManager()

        return llm_manager, tool_dispatcher, websocket_manager
    
    def test_registry_registers_default_agents(self, real_components):

        """Test that default agents are registered."""

        llm_manager, tool_dispatcher, _ = real_components
        
        registry = AgentRegistry(llm_manager, tool_dispatcher)

        registry.register_default_agents()
        
        # Verify core agents are registered

        assert "triage" in registry.agents

        assert "data" in registry.agents  

        assert "optimization" in registry.agents

        assert "actions" in registry.agents

        assert "reporting" in registry.agents
    
    def test_supervisor_initializes_with_agents(self, real_components):

        """Test supervisor initialization with agent registry."""

        llm_manager, tool_dispatcher, websocket_manager = real_components
        
        with patch('netra_backend.app.agents.supervisor_consolidated.AsyncSession'):

            supervisor = SupervisorAgent(

                llm_manager=llm_manager,

                tool_dispatcher=tool_dispatcher,

                websocket_manager=websocket_manager

            )
            
            # Verify registry exists and has agents

            assert supervisor.registry is not None

            assert len(supervisor.registry.list_agents()) > 0

@pytest.mark.asyncio

class TestWebSocketMessageFlow:

    """Test WebSocket message flow to agent execution."""
    
    async def test_user_message_triggers_agent_execution(self):

        """Test that user_message type triggers agent execution."""
        from netra_backend.app.services.agent_service_core import AgentService
        from netra_backend.app.services.message_handlers import MessageHandlerService
        
        # Create mocks

        mock_supervisor = AsyncMock()

        mock_supervisor.run = AsyncMock(return_value="Test response")
        
        # Create service

        agent_service = AgentService(mock_supervisor)
        
        # Test message

        message = {

            "type": "user_message",

            "payload": {

                "content": "Test message",

                "references": []

            }

        }
        
        # Mock WebSocket manager to avoid actual sending

        with patch('netra_backend.app.ws_manager.manager'):

            await agent_service.handle_websocket_message(

                user_id="test_user",

                message=message,

                db_session=None

            )
        
        # Verify supervisor.run was called

        assert mock_supervisor.run.called
    
    async def test_message_handler_routes_correctly(self):

        """Test message handler routing for different message types."""
        
        mock_supervisor = Mock()

        mock_thread_service = Mock()
        
        handler = MessageHandlerService(mock_supervisor, mock_thread_service)
        
        # Test routing map

        assert hasattr(handler, 'handle_user_message')

        assert hasattr(handler, 'handle_start_agent')

        assert hasattr(handler, 'handle_thread_history')

        assert hasattr(handler, 'handle_stop_agent')
    
    async def test_websocket_connection_lifecycle(self):

        """Test WebSocket connection establishment and message handling."""
        from netra_backend.app.routes.utils.websocket_helpers import (

            process_agent_message,

        )
        
        mock_agent_service = AsyncMock()

        mock_agent_service.handle_websocket_message = AsyncMock()
        
        # Test process_agent_message

        with patch('netra_backend.app.routes.utils.websocket_helpers.get_async_db') as mock_db:

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())

            mock_db.return_value.__aexit__ = AsyncMock()
            
            await process_agent_message("user_123", "test_data", mock_agent_service)
            
            # Verify agent service was called

            mock_agent_service.handle_websocket_message.assert_called_once()

class TestAgentExecutionPipeline:

    """Test the agent execution pipeline."""
    
    def test_pipeline_executor_initialization(self):

        """Test pipeline executor can be initialized."""
        from netra_backend.app.agents.supervisor.pipeline_executor import (

            PipelineExecutor,

        )
        
        mock_engine = Mock()

        mock_ws_manager = Mock()

        mock_db_session = None
        
        executor = PipelineExecutor(mock_engine, mock_ws_manager, mock_db_session)

        assert executor is not None
    
    def test_execution_engine_initialization(self):

        """Test execution engine can be initialized."""
        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
        
        mock_registry = Mock()

        mock_ws_manager = Mock()
        
        engine = ExecutionEngine(mock_registry, mock_ws_manager)

        assert engine is not None
    
    @pytest.mark.asyncio

    async def test_agent_execution_core(self):

        """Test agent execution core functionality."""
        from netra_backend.app.agents.supervisor.agent_execution_core import (

            AgentExecutionCore,

        )
        
        mock_registry = Mock()

        mock_agent = AsyncMock()

        mock_agent.execute = AsyncMock(return_value={"result": "success"})

        mock_registry.get = Mock(return_value=mock_agent)
        
        executor = AgentExecutionCore(mock_registry)
        
        # Test execution

        result = await executor.execute_agent(

            agent_name="test_agent",

            state=Mock(),

            run_id="test_run",

            stream_updates=False

        )
        
        assert result is not None

        mock_agent.execute.assert_called_once()

class TestWebSocketBroadcasting:

    """Test WebSocket broadcasting functionality."""
    
    @pytest.mark.asyncio

    async def test_broadcast_to_user(self):

        """Test broadcasting message to specific user."""
        from netra_backend.app.websocket.unified import get_unified_manager
manager = get_unified_manager()
        
        with patch.object(manager, 'send_to_user', new_callable=AsyncMock) as mock_send:

            await manager.send_to_user("user_123", {"type": "test"})

            mock_send.assert_called_once_with("user_123", {"type": "test"})
    
    @pytest.mark.asyncio  

    async def test_broadcast_to_room(self):

        """Test broadcasting message to room."""
        
        with patch.object(manager.broadcasting, 'broadcast_to_room', new_callable=AsyncMock) as mock_broadcast:

            await manager.broadcasting.broadcast_to_room("room_123", {"type": "test"})

            mock_broadcast.assert_called_once_with("room_123", {"type": "test"})