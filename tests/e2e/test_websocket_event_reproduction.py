"""
Test to reproduce WebSocket event emission failure in agent execution.
This test validates that all required WebSocket events are emitted during agent lifecycle.
"""

import asyncio
import pytest
from typing import List, Set
from unittest.mock import MagicMock, AsyncMock, patch

from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.execution_engine import ExecutionEngine
from netra_backend.app.services.tool_dispatcher import UnifiedToolDispatcher


@pytest.mark.asyncio
class TestWebSocketEventReproduction:
    """Reproduce missing WebSocket events during agent execution."""
    
    REQUIRED_EVENTS = {
        'agent_started',
        'agent_thinking', 
        'agent_completed',
        'tool_executing',
        'tool_completed'
    }
    
    async def test_websocket_events_missing_reproduction(self):
        """
        Reproduce the missing WebSocket events issue.
        This test should FAIL initially, demonstrating the problem.
        """
        # Track emitted events
        emitted_events: List[str] = []
        
        # Create mock WebSocket manager that tracks events
        mock_ws_manager = MagicMock()
        mock_ws_manager.send_event = AsyncMock(side_effect=lambda event_type, **kwargs: 
                                              emitted_events.append(event_type))
        
        # Set up agent registry with WebSocket manager
        registry = AgentRegistry()
        registry.set_websocket_manager(mock_ws_manager)
        
        # Create a simple test agent
        test_agent_config = {
            "name": "test_agent",
            "description": "Test agent for WebSocket validation",
            "tools": ["calculator"],
            "system_prompt": "You are a test agent"
        }
        
        # Register the test agent
        registry.register_agent("test_agent", test_agent_config)
        
        # Get the agent instance
        agent = registry.get_agent("test_agent")
        
        # Create execution context
        test_context = {
            "user_id": "test_user_123",
            "session_id": "test_session_456",
            "run_id": "test_run_789"
        }
        
        # Execute agent with a simple task
        test_message = "Calculate 2 + 2"
        
        # This should trigger WebSocket events but currently doesn't
        try:
            # Attempt to execute the agent
            # Note: This may fail if Factory pattern isn't properly implemented
            result = await agent.execute(test_message, context=test_context)
        except Exception as e:
            # Even if execution fails, we should have gotten some events
            print(f"Execution failed with: {e}")
        
        # Check which events were emitted
        emitted_event_types = set(emitted_events)
        missing_events = self.REQUIRED_EVENTS - emitted_event_types
        
        # This assertion should FAIL, proving the issue exists
        assert not missing_events, f"Missing required WebSocket events: {missing_events}"
    
    async def test_execution_engine_websocket_initialization(self):
        """Test that ExecutionEngine properly initializes WebSocket support."""
        
        # Track if WebSocketNotifier is initialized
        websocket_initialized = False
        
        # Try to create ExecutionEngine with Factory pattern
        try:
            # This should use Factory pattern per USER_CONTEXT_ARCHITECTURE.md
            from netra_backend.app.services.execution_factory import ExecutionContextFactory
            
            factory = ExecutionContextFactory()
            user_context = {
                "user_id": "test_user",
                "session_id": "test_session",
                "run_id": "test_run"
            }
            
            # Create execution engine with user context
            engine = factory.create_execution_engine(user_context)
            
            # Check if WebSocketNotifier is properly initialized
            websocket_initialized = hasattr(engine, 'websocket_notifier') and \
                                  engine.websocket_notifier is not None
            
        except ImportError:
            # Factory pattern not implemented
            pytest.fail("ExecutionContextFactory not found - Factory pattern not implemented")
        except Exception as e:
            pytest.fail(f"Failed to create ExecutionEngine with Factory: {e}")
        
        assert websocket_initialized, "ExecutionEngine doesn't have WebSocketNotifier initialized"
    
    async def test_tool_dispatcher_websocket_enhancement(self):
        """Test that tool dispatcher is properly enhanced with WebSocket support."""
        from netra_backend.app.agents.supervisor.user_execution_context import create_test_user_context
        
        # Create test user context for request-scoped dispatcher
        user_context = create_test_user_context()
        
        # Create request-scoped tool dispatcher
        dispatcher = UnifiedToolDispatcher.create_request_scoped(user_context)
        
        # Create mock WebSocket manager
        mock_ws_manager = MagicMock()
        mock_ws_manager.send_event = AsyncMock()
        
        # Enhance dispatcher with WebSocket
        dispatcher.set_websocket_manager(mock_ws_manager)
        
        # Track tool events
        tool_events = []
        mock_ws_manager.send_event.side_effect = lambda event_type, **kwargs: \
                                                tool_events.append(event_type)
        
        # Execute a tool
        test_tool_call = {
            "tool": "calculator",
            "input": {"expression": "2 + 2"}
        }
        
        # This should emit tool_executing and tool_completed events
        result = await dispatcher.execute_tool(test_tool_call)
        
        # Check for tool events
        assert 'tool_executing' in tool_events, "tool_executing event not emitted"
        assert 'tool_completed' in tool_events, "tool_completed event not emitted"
    
    async def test_agent_registry_run_id_issue(self):
        """Test that AgentRegistry doesn't use placeholder run_id."""
        
        registry = AgentRegistry()
        mock_ws_manager = MagicMock()
        
        # Set WebSocket manager
        registry.set_websocket_manager(mock_ws_manager)
        
        # Check if tool dispatcher was enhanced with proper run_id
        tool_dispatcher = registry._tool_dispatcher
        
        # This should NOT use 'registry' as run_id
        if hasattr(tool_dispatcher, 'websocket_bridge'):
            bridge = tool_dispatcher.websocket_bridge
            assert bridge.run_id != 'registry', \
                   "AgentRegistry using placeholder 'registry' run_id instead of user context"
    
    async def test_factory_pattern_compliance(self):
        """Test that Factory pattern from USER_CONTEXT_ARCHITECTURE.md is implemented."""
        
        # Check for Factory implementation
        try:
            from netra_backend.app.services.execution_factory import ExecutionContextFactory
            from netra_backend.app.services.websocket_factory import WebSocketManagerFactory
            
            # Both factories should exist for proper isolation
            assert ExecutionContextFactory is not None, "ExecutionContextFactory not found"
            assert WebSocketManagerFactory is not None, "WebSocketManagerFactory not found"
            
        except ImportError as e:
            pytest.fail(f"Factory pattern not implemented: {e}")


if __name__ == "__main__":
    # Run the reproduction test
    asyncio.run(TestWebSocketEventReproduction().test_websocket_events_missing_reproduction())