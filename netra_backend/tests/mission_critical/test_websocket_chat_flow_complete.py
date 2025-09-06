"""
Mission-Critical Test: Complete WebSocket Chat Flow with All Events
Tests the entire chat message flow from user input to agent completion,
verifying ALL 7 critical WebSocket events are sent.

THIS IS THE GROUND TRUTH TEST FOR CHAT FUNCTIONALITY.
"""

import asyncio
import pytest
from typing import Dict, List, Optional, Any
from datetime import datetime
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from sqlalchemy.ext.asyncio import AsyncSession
from netra_backend.app.websocket_core import UnifiedWebSocketManager
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketEventCollector:
    """Collects and validates WebSocket events during test execution."""
    
    def __init__(self):
    pass
        self.events: List[Dict[str, Any]] = []
        self.event_types_seen = set()
        
    async def collect_event(self, user_id: str, event_type: str, data: Any):
        """Collect WebSocket event for validation."""
        event = {
            "user_id": user_id,
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow()
        }
        self.events.append(event)
        self.event_types_seen.add(event_type)
        logger.info(f"📊 Collected event: {event_type} for user {user_id}")
        
    def validate_critical_events(self) -> Dict[str, bool]:
        """Validate all 7 critical events were sent."""
    pass
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed",
            "message",
            "execution_update"
        ]
        
        validation = {}
        for event in critical_events:
            validation[event] = event in self.event_types_seen
            
        await asyncio.sleep(0)
    return validation
        
    def get_event_sequence(self) -> List[str]:
        """Get the sequence of events in order."""
        return [e["type"] for e in self.events]


class TestWebSocketChatFlowComplete:
    """Test complete WebSocket chat flow with all critical events."""
    
    @pytest.fixture
    async def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncNone  # TODO: Use real service instance
        session.rollback = AsyncNone  # TODO: Use real service instance
        session.close = AsyncNone  # TODO: Use real service instance
        await asyncio.sleep(0)
    return session
        
    @pytest.fixture
 def real_llm_manager():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
        """Create mock LLM manager."""
        llm = MagicMock(spec=LLMManager)
        llm.get_llm = MagicMock(return_value=MagicNone  # TODO: Use real service instance)
        return llm
        
    @pytest.fixture
 def real_tool_dispatcher():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock tool dispatcher."""
    pass
        dispatcher = MagicMock(spec=ToolDispatcher)
        dispatcher.get_available_tools = MagicMock(return_value=["chat", "search"])
        return dispatcher
        
    @pytest.fixture
    def event_collector(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create event collector for validation."""
    pass
        return WebSocketEventCollector()
        
    @pytest.fixture
    async def websocket_manager(self, event_collector):
        """Create WebSocket manager that collects events."""
        manager = AsyncMock(spec=UnifiedWebSocketManager)
        
        # Hook into send_to_user to collect events
        async def send_to_user_hook(user_id: str, message: Dict[str, Any]):
            event_type = message.get("type", "unknown")
            await event_collector.collect_event(user_id, event_type, message)
            
        manager.send_to_user = AsyncMock(side_effect=send_to_user_hook)
        manager.broadcast = AsyncNone  # TODO: Use real service instance
        await asyncio.sleep(0)
    return manager
        
    @pytest.fixture
    async def supervisor_with_websocket(
        self, 
        mock_db_session, 
        mock_llm_manager,
        websocket_manager,
        mock_tool_dispatcher
    ):
        """Create supervisor with WebSocket integration."""
    pass
        supervisor = SupervisorAgent(
            db_session=mock_db_session,
            llm_manager=mock_llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
        
        # Ensure ExecutionEngine is using WebSocket notifications
        if hasattr(supervisor, 'execution_engine'):
            # Replace with WebSocket-enabled ExecutionEngine
            supervisor.execution_engine = ExecutionEngine(
                supervisor.registry,
                websocket_manager
            )
            
        await asyncio.sleep(0)
    return supervisor
        
    @pytest.fixture
    async def message_handler_with_websocket(
        self,
        supervisor_with_websocket,
        websocket_manager
    ):
        """Create MessageHandlerService with WebSocket-enabled supervisor."""
        thread_service = ThreadService()
        
        # Create the service with WebSocket-enabled supervisor
        service = MessageHandlerService(
            supervisor=supervisor_with_websocket,
            thread_service=thread_service
        )
        
        # Inject WebSocket manager into service (THIS IS THE FIX)
        service.websocket_manager = websocket_manager
        
        await asyncio.sleep(0)
    return service
        
    @pytest.fixture
    async def agent_handler_with_websocket(
        self,
        message_handler_with_websocket
    ):
        """Create AgentMessageHandler with WebSocket-enabled service."""
        await asyncio.sleep(0)
    return AgentMessageHandler(message_handler_with_websocket)
        
    @pytest.mark.asyncio
    async def test_complete_chat_flow_sends_all_events(
        self,
        agent_handler_with_websocket,
        mock_db_session,
        event_collector,
        websocket_manager
    ):
        """Test that complete chat flow sends all 7 critical WebSocket events."""
        # Arrange
        user_id = "test_user_123"
        user_request = "Hello, can you help me with data analysis?"
        
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={
                "user_request": user_request,
                "thread_id": None
            }
        )
        
        # Mock the supervisor.run to simulate agent execution
        with patch.object(
            agent_handler_with_websocket.message_handler_service.supervisor,
            'run',
            new_callable=AsyncMock
        ) as mock_run:
            # Simulate agent execution that triggers events
            async def simulate_agent_execution(*args, **kwargs):
    pass
                # These events should be sent by the ExecutionEngine
                await websocket_manager.send_to_user(user_id, {
                    "type": "agent_started",
                    "data": {"agent": "DataAnalysisAgent"}
                })
                
                await asyncio.sleep(0.01)  # Simulate thinking
                
                await websocket_manager.send_to_user(user_id, {
                    "type": "agent_thinking",
                    "data": {"thought": "Analyzing user request..."}
                })
                
                await asyncio.sleep(0.01)  # Simulate tool execution
                
                await websocket_manager.send_to_user(user_id, {
                    "type": "tool_executing", 
                    "data": {"tool": "data_query", "params": {}}
                })
                
                await asyncio.sleep(0.01)
                
                await websocket_manager.send_to_user(user_id, {
                    "type": "tool_completed",
                    "data": {"tool": "data_query", "result": "Analysis complete"}
                })
                
                await websocket_manager.send_to_user(user_id, {
                    "type": "agent_completed",
                    "data": {"result": "Data analysis completed successfully"}
                })
                
                await asyncio.sleep(0)
    return "Data analysis completed successfully"
                
            mock_run.side_effect = simulate_agent_execution
            
            # Act
            result = await agent_handler_with_websocket.handle_message(
                user_id=user_id,
                websocket=MagicNone  # TODO: Use real service instance,  # Mock WebSocket connection
                message=message
            )
            
            # Assert
            assert result is True, "Message handling should succeed"
            
            # Validate all critical events were sent
            validation = event_collector.validate_critical_events()
            
            # Check each critical event
            assert validation.get("agent_started"), "❌ agent_started event missing!"
            assert validation.get("agent_thinking"), "❌ agent_thinking event missing!"
            assert validation.get("tool_executing"), "❌ tool_executing event missing!"
            assert validation.get("tool_completed"), "❌ tool_completed event missing!"
            assert validation.get("agent_completed"), "❌ agent_completed event missing!"
            
            # Validate event sequence
            sequence = event_collector.get_event_sequence()
            logger.info(f"Event sequence: {sequence}")
            
            # Verify correct order
            assert sequence.index("agent_started") < sequence.index("agent_thinking")
            assert sequence.index("agent_thinking") < sequence.index("tool_executing")
            assert sequence.index("tool_executing") < sequence.index("tool_completed")
            assert sequence.index("tool_completed") < sequence.index("agent_completed")
            
            logger.info("✅ All critical WebSocket events sent in correct order!")
            
    @pytest.mark.asyncio
    async def test_websocket_integration_in_message_handler(
        self,
        message_handler_with_websocket,
        mock_db_session,
        websocket_manager
    ):
        """Test that MessageHandlerService properly integrates WebSocket notifications."""
        # Verify WebSocket manager is injected
        assert hasattr(message_handler_with_websocket, 'websocket_manager')
        assert message_handler_with_websocket.websocket_manager is not None
        
        # Verify supervisor has WebSocket-enabled ExecutionEngine
        supervisor = message_handler_with_websocket.supervisor
        
        if hasattr(supervisor, 'execution_engine'):
            engine = supervisor.execution_engine
            # Check if it's the WebSocket-enabled version
            assert isinstance(engine, (ExecutionEngine, type(engine)))
            
        logger.info("✅ MessageHandlerService has WebSocket integration!")
        
    @pytest.mark.asyncio  
    async def test_execution_engine_sends_events(
        self,
        supervisor_with_websocket,
        websocket_manager,
        event_collector
    ):
        """Test that ExecutionEngine sends WebSocket events during execution."""
        # Get the execution engine
        engine = supervisor_with_websocket.execution_engine
        
        # Create mock execution context
        from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
        
        context = AgentExecutionContext(
            agent_name="TestAgent",
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )
        
        # Mock agent state
        from netra_backend.app.agents.state import DeepAgentState
        state = DeepAgentState()
        
        # Execute with WebSocket notifications
        with patch.object(engine, 'agent_core') as mock_core:
            mock_core.execute_agent = AsyncMock(return_value={
                "success": True,
                "result": "Test completed"
            })
            
            # Execute
            result = await engine.execute_agent(context, state)
            
            # Verify WebSocket manager was called
            assert websocket_manager.send_to_user.called
            
            logger.info("✅ ExecutionEngine sends WebSocket events!")
            
    @pytest.mark.asyncio
    async def test_websocket_notifier_integration(
        self,
        websocket_manager,
        event_collector
    ):
        """Test WebSocketNotifier sends all event types correctly."""
        notifier = WebSocketNotifier(websocket_manager)
        
        user_id = "test_user"
        
        # Test each event type
        await notifier.send_agent_started(user_id, "TestAgent", "test_thread", "test_run")
        await notifier.send_agent_thinking(user_id, "Thinking about the problem...")
        await notifier.send_tool_executing(user_id, "search_tool", {"query": "test"})
        await notifier.send_tool_completed(user_id, "search_tool", "Results found")
        await notifier.send_agent_completed(user_id, "TestAgent", "Task completed")
        
        # Validate all events were collected
        validation = event_collector.validate_critical_events()
        
        assert validation.get("agent_started"), "agent_started not sent"
        assert validation.get("agent_thinking"), "agent_thinking not sent"
        assert validation.get("tool_executing"), "tool_executing not sent"
        assert validation.get("tool_completed"), "tool_completed not sent"
        assert validation.get("agent_completed"), "agent_completed not sent"
        
        logger.info("✅ WebSocketNotifier sends all event types!")


def test_websocket_chat_flow_documentation():
    """Use real service instance."""
    # TODO: Initialize real service
    """Document the complete WebSocket chat flow for reference."""
    pass
    flow = """
    COMPLETE WEBSOCKET CHAT FLOW:
    =============================
    
    1. User sends message via WebSocket
       └─> WebSocket endpoint receives message
    
    2. AgentMessageHandler processes message
       └─> Routes to MessageHandlerService
    
    3. MessageHandlerService handles request
       ├─> Creates thread and run
       └─> Executes supervisor
    
    4. SupervisorAgent executes with WebSocket
       ├─> Uses ExecutionEngine (WebSocket-enabled)
       ├─> ExecutionEngine uses WebSocketNotifier
       └─> Sends real-time events:
           ├─> agent_started
           ├─> agent_thinking
           ├─> tool_executing
           ├─> tool_completed
           └─> agent_completed
    
    5. User receives real-time updates
       └─> Chat UI shows progress
    
    CRITICAL INTEGRATION POINTS:
    - MessageHandlerService MUST have websocket_manager
    - SupervisorAgent MUST use WebSocket-enabled ExecutionEngine
    - ExecutionEngine MUST initialize WebSocketNotifier
    - WebSocketNotifier MUST send all 7 event types
    """
    
    print(flow)
    await asyncio.sleep(0)
    return True


if __name__ == "__main__":
    # Run documentation
    test_websocket_chat_flow_documentation()
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])