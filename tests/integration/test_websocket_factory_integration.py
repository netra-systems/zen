# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: WebSocket Factory Integration Tests

# REMOVED_SYNTAX_ERROR: Business Value:
    # REMOVED_SYNTAX_ERROR: - Validates WebSocket factory integration with execution contexts
    # REMOVED_SYNTAX_ERROR: - Tests complete agent event flow through WebSocket
    # REMOVED_SYNTAX_ERROR: - Ensures user isolation and proper event routing
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_bridge_factory import ( )
    # REMOVED_SYNTAX_ERROR: WebSocketBridgeFactory,
    # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter,
    # REMOVED_SYNTAX_ERROR: WebSocketConnectionPool
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_factory import ( )
    # REMOVED_SYNTAX_ERROR: ExecutionFactory,
    # REMOVED_SYNTAX_ERROR: UserExecutionContext
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestWebSocketExecutionIntegration:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket integration with execution factory."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def ws_factory(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create WebSocket factory."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketBridgeFactory()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def exec_factory(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create execution factory."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return ExecutionFactory()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_agent_registry():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock agent registry."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = MagicMock(spec=AgentRegistry)
    # REMOVED_SYNTAX_ERROR: registry.set_websocket_manager = Magic        registry.enhance_tool_dispatcher = Magic        return registry

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_execution_context_creates_emitter(self, ws_factory, exec_factory):
        # REMOVED_SYNTAX_ERROR: """Test execution context properly creates WebSocket emitter."""
        # REMOVED_SYNTAX_ERROR: user_id = "user-123"
        # REMOVED_SYNTAX_ERROR: session_id = "session-456"

        # Create WebSocket connection
        # REMOVED_SYNTAX_ERROR: mock_ws = Magic        mock_ws.websocket = TestWebSocketConnection()
        # REMOVED_SYNTAX_ERROR: mock_ws.state = Magic        mock_ws.state.name = "OPEN"

        # Create emitter
        # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: session_id=session_id,
        # REMOVED_SYNTAX_ERROR: websocket=mock_ws
        

        # Create execution context with emitter
        # REMOVED_SYNTAX_ERROR: context = exec_factory.create_user_context( )
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: session_id=session_id,
        # REMOVED_SYNTAX_ERROR: websocket_emitter=emitter
        

        # Verify context has emitter
        # REMOVED_SYNTAX_ERROR: assert context is not None
        # REMOVED_SYNTAX_ERROR: assert context.user_id == user_id
        # REMOVED_SYNTAX_ERROR: assert context.session_id == session_id
        # REMOVED_SYNTAX_ERROR: assert context.websocket_emitter == emitter

        # Test sending event through context
        # Removed problematic line: await emitter.emit({ ))
        # REMOVED_SYNTAX_ERROR: "type": "execution_started",
        # REMOVED_SYNTAX_ERROR: "data": {"context_id": context.session_id}
        

        # REMOVED_SYNTAX_ERROR: mock_ws.send.assert_called_once()

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_agent_registry_enhances_dispatcher(self, ws_factory, mock_agent_registry):
            # REMOVED_SYNTAX_ERROR: """Test agent registry enhances tool dispatcher with WebSocket."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id = "user-123"

            # Create emitter
            # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: session_id="session-1"
            

            # Set WebSocket manager in registry
            # REMOVED_SYNTAX_ERROR: mock_agent_registry.set_websocket_manager(emitter)

            # Create mock tool dispatcher
            # REMOVED_SYNTAX_ERROR: mock_dispatcher = Magic        mock_dispatcher.execute_tool = AsyncMock(return_value={"status": "success"})

            # Enhance dispatcher
            # REMOVED_SYNTAX_ERROR: mock_agent_registry.enhance_tool_dispatcher.return_value = mock_dispatcher
            # REMOVED_SYNTAX_ERROR: enhanced = mock_agent_registry.enhance_tool_dispatcher(mock_dispatcher)

            # Execute tool
            # REMOVED_SYNTAX_ERROR: result = await enhanced.execute_tool("test_tool", {"param": "value"})

            # REMOVED_SYNTAX_ERROR: assert result == {"status": "success"}
            # REMOVED_SYNTAX_ERROR: mock_agent_registry.set_websocket_manager.assert_called_once_with(emitter)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_complete_agent_event_flow(self, ws_factory, exec_factory):
                # REMOVED_SYNTAX_ERROR: """Test complete agent execution event flow."""
                # REMOVED_SYNTAX_ERROR: user_id = "user-123"
                # REMOVED_SYNTAX_ERROR: session_id = "session-456"

                # Create WebSocket
                # REMOVED_SYNTAX_ERROR: mock_ws = Magic        mock_ws.websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: mock_ws.state = Magic        mock_ws.state.name = "OPEN"

                # Create emitter with WebSocket
                # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
                # REMOVED_SYNTAX_ERROR: user_id=user_id,
                # REMOVED_SYNTAX_ERROR: session_id=session_id,
                # REMOVED_SYNTAX_ERROR: websocket=mock_ws
                

                # Create execution context
                # REMOVED_SYNTAX_ERROR: context = exec_factory.create_user_context( )
                # REMOVED_SYNTAX_ERROR: user_id=user_id,
                # REMOVED_SYNTAX_ERROR: session_id=session_id,
                # REMOVED_SYNTAX_ERROR: websocket_emitter=emitter
                

                # Simulate complete agent lifecycle
                # REMOVED_SYNTAX_ERROR: events = [ )
                # REMOVED_SYNTAX_ERROR: {"type": "agent_started", "data": {"agent": "test_agent", "task": "search"}},
                # REMOVED_SYNTAX_ERROR: {"type": "agent_thinking", "data": {"thought": "Analyzing query..."}},
                # REMOVED_SYNTAX_ERROR: {"type": "tool_executing", "data": {"tool": "search", "params": {"q": "test"}}},
                # REMOVED_SYNTAX_ERROR: {"type": "tool_completed", "data": {"tool": "search", "result": {"hits": 10}}},
                # REMOVED_SYNTAX_ERROR: {"type": "agent_thinking", "data": {"thought": "Processing results..."}},
                # REMOVED_SYNTAX_ERROR: {"type": "agent_completed", "data": {"response": "Found 10 results"}}
                

                # Send all events
                # REMOVED_SYNTAX_ERROR: for event in events:
                    # REMOVED_SYNTAX_ERROR: await emitter.emit(event)

                    # Verify all events were sent
                    # REMOVED_SYNTAX_ERROR: assert mock_ws.send.call_count == len(events)

                    # Verify event order and content
                    # REMOVED_SYNTAX_ERROR: calls = mock_ws.send.call_args_list
                    # REMOVED_SYNTAX_ERROR: for i, call in enumerate(calls):
                        # REMOVED_SYNTAX_ERROR: sent_data = call[0][0]
                        # REMOVED_SYNTAX_ERROR: if isinstance(sent_data, str):
                            # REMOVED_SYNTAX_ERROR: sent_data = json.loads(sent_data)
                            # REMOVED_SYNTAX_ERROR: assert sent_data["type"] == events[i]["type"]

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_concurrent_user_execution(self, ws_factory, exec_factory):
                                # REMOVED_SYNTAX_ERROR: """Test concurrent execution for multiple users."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: users = [ )
                                # REMOVED_SYNTAX_ERROR: ("user-1", "session-1"),
                                # REMOVED_SYNTAX_ERROR: ("user-2", "session-2"),
                                # REMOVED_SYNTAX_ERROR: ("user-3", "session-3")
                                

                                # REMOVED_SYNTAX_ERROR: contexts = []
                                # REMOVED_SYNTAX_ERROR: websockets = []

                                # Create contexts for each user
                                # REMOVED_SYNTAX_ERROR: for user_id, session_id in users:
                                    # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                                    # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                                    # REMOVED_SYNTAX_ERROR: websockets.append(ws)

                                    # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
                                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                    # REMOVED_SYNTAX_ERROR: session_id=session_id,
                                    # REMOVED_SYNTAX_ERROR: websocket=ws
                                    

                                    # REMOVED_SYNTAX_ERROR: context = exec_factory.create_user_context( )
                                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                    # REMOVED_SYNTAX_ERROR: session_id=session_id,
                                    # REMOVED_SYNTAX_ERROR: websocket_emitter=emitter
                                    
                                    # REMOVED_SYNTAX_ERROR: contexts.append(context)

                                    # Each user executes agent concurrently
                                    # REMOVED_SYNTAX_ERROR: tasks = []
                                    # REMOVED_SYNTAX_ERROR: for i, context in enumerate(contexts):
                                        # REMOVED_SYNTAX_ERROR: event = { )
                                        # REMOVED_SYNTAX_ERROR: "type": "agent_started",
                                        # REMOVED_SYNTAX_ERROR: "data": {"user": context.user_id, "index": i}
                                        
                                        # REMOVED_SYNTAX_ERROR: tasks.append(context.websocket_emitter.emit(event))

                                        # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                                        # Each WebSocket should only receive its user's events
                                        # REMOVED_SYNTAX_ERROR: for i, ws in enumerate(websockets):
                                            # REMOVED_SYNTAX_ERROR: assert ws.send.call_count == 1
                                            # REMOVED_SYNTAX_ERROR: call_data = ws.send.call_args[0][0]
                                            # REMOVED_SYNTAX_ERROR: if isinstance(call_data, str):
                                                # REMOVED_SYNTAX_ERROR: call_data = json.loads(call_data)
                                                # REMOVED_SYNTAX_ERROR: assert contexts[i].user_id in str(call_data)

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_error_event_propagation(self, ws_factory):
                                                    # REMOVED_SYNTAX_ERROR: """Test error events are properly propagated."""
                                                    # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                                                    # REMOVED_SYNTAX_ERROR: mock_ws = Magic        mock_ws.websocket = TestWebSocketConnection()
                                                    # REMOVED_SYNTAX_ERROR: mock_ws.state = Magic        mock_ws.state.name = "OPEN"

                                                    # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
                                                    # REMOVED_SYNTAX_ERROR: user_id=user_id,
                                                    # REMOVED_SYNTAX_ERROR: session_id="session-1",
                                                    # REMOVED_SYNTAX_ERROR: websocket=mock_ws
                                                    

                                                    # Send error event
                                                    # REMOVED_SYNTAX_ERROR: error_event = { )
                                                    # REMOVED_SYNTAX_ERROR: "type": "error",
                                                    # REMOVED_SYNTAX_ERROR: "data": { )
                                                    # REMOVED_SYNTAX_ERROR: "message": "Agent execution failed",
                                                    # REMOVED_SYNTAX_ERROR: "code": "AGENT_ERROR",
                                                    # REMOVED_SYNTAX_ERROR: "details": { )
                                                    # REMOVED_SYNTAX_ERROR: "agent": "test_agent",
                                                    # REMOVED_SYNTAX_ERROR: "reason": "Tool timeout"
                                                    
                                                    
                                                    

                                                    # REMOVED_SYNTAX_ERROR: await emitter.emit_error(error_event["data"])

                                                    # Error should be sent immediately
                                                    # REMOVED_SYNTAX_ERROR: mock_ws.send.assert_called_once()
                                                    # REMOVED_SYNTAX_ERROR: sent = mock_ws.send.call_args[0][0]
                                                    # REMOVED_SYNTAX_ERROR: if isinstance(sent, str):
                                                        # REMOVED_SYNTAX_ERROR: sent = json.loads(sent)

                                                        # REMOVED_SYNTAX_ERROR: assert sent["type"] == "error"
                                                        # REMOVED_SYNTAX_ERROR: assert "Agent execution failed" in str(sent)


# REMOVED_SYNTAX_ERROR: class TestWebSocketToolDispatcher:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket integration with tool dispatcher."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock tool dispatcher."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: dispatcher = Magic        dispatcher.websocket = TestWebSocketConnection()
    # Removed problematic line: dispatcher.set_websocket_emitter = Magic        await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return dispatcher

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_tool_dispatcher_sends_events(self, ws_factory, mock_tool_dispatcher):
        # REMOVED_SYNTAX_ERROR: """Test tool dispatcher sends WebSocket events."""
        # REMOVED_SYNTAX_ERROR: user_id = "user-123"

        # Create WebSocket setup
        # REMOVED_SYNTAX_ERROR: mock_ws = Magic        mock_ws.websocket = TestWebSocketConnection()
        # REMOVED_SYNTAX_ERROR: mock_ws.state = Magic        mock_ws.state.name = "OPEN"

        # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: session_id="session-1",
        # REMOVED_SYNTAX_ERROR: websocket=mock_ws
        

        # Set emitter on dispatcher
        # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher.set_websocket_emitter(emitter)

        # Execute tool with WebSocket notifications
        # REMOVED_SYNTAX_ERROR: tool_name = "search"
        # REMOVED_SYNTAX_ERROR: tool_params = {"query": "test"}

        # Simulate tool execution with events
        # Removed problematic line: await emitter.emit({ ))
        # REMOVED_SYNTAX_ERROR: "type": "tool_executing",
        # REMOVED_SYNTAX_ERROR: "data": {"tool": tool_name, "params": tool_params}
        

        # Execute tool
        # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher.execute.return_value = {"result": "success"}
        # REMOVED_SYNTAX_ERROR: result = await mock_tool_dispatcher.execute(tool_name, tool_params)

        # Send completion event
        # Removed problematic line: await emitter.emit({ ))
        # REMOVED_SYNTAX_ERROR: "type": "tool_completed",
        # REMOVED_SYNTAX_ERROR: "data": {"tool": tool_name, "result": result}
        

        # Verify events were sent
        # REMOVED_SYNTAX_ERROR: assert mock_ws.send.call_count == 2
        # REMOVED_SYNTAX_ERROR: calls = mock_ws.send.call_args_list

        # Check executing event
        # REMOVED_SYNTAX_ERROR: executing = json.loads(calls[0][0][0]) if isinstance(calls[0][0][0], str) else calls[0][0][0]
        # REMOVED_SYNTAX_ERROR: assert executing["type"] == "tool_executing"

        # Check completed event
        # REMOVED_SYNTAX_ERROR: completed = json.loads(calls[1][0][0]) if isinstance(calls[1][0][0], str) else calls[1][0][0]
        # REMOVED_SYNTAX_ERROR: assert completed["type"] == "tool_completed"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_enhanced_tool_dispatcher(self, ws_factory):
            # REMOVED_SYNTAX_ERROR: """Test enhanced tool dispatcher with WebSocket wrapper."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id = "user-123"

            # Create emitter
            # REMOVED_SYNTAX_ERROR: mock_ws = Magic        mock_ws.websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: mock_ws.state = Magic        mock_ws.state.name = "OPEN"

            # REMOVED_SYNTAX_ERROR: emitter = await ws_factory.create_user_emitter( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: session_id="session-1",
            # REMOVED_SYNTAX_ERROR: websocket=mock_ws
            

            # Create base tool dispatcher
            # REMOVED_SYNTAX_ERROR: base_dispatcher = Magic        base_dispatcher.execute = AsyncMock(return_value={"status": "success"})

            # Create enhanced dispatcher (wrapper)
# REMOVED_SYNTAX_ERROR: class EnhancedDispatcher:
# REMOVED_SYNTAX_ERROR: def __init__(self, base, ws_emitter):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.base = base
    # REMOVED_SYNTAX_ERROR: self.emitter = ws_emitter

# REMOVED_SYNTAX_ERROR: async def execute(self, tool, params):
    # REMOVED_SYNTAX_ERROR: pass
    # Removed problematic line: await self.emitter.emit({ ))
    # REMOVED_SYNTAX_ERROR: "type": "tool_executing",
    # REMOVED_SYNTAX_ERROR: "data": {"tool": tool, "params": params}
    
    # REMOVED_SYNTAX_ERROR: result = await self.base.execute(tool, params)
    # Removed problematic line: await self.emitter.emit({ ))
    # REMOVED_SYNTAX_ERROR: "type": "tool_completed",
    # REMOVED_SYNTAX_ERROR: "data": {"tool": tool, "result": result}
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return result

    # REMOVED_SYNTAX_ERROR: enhanced = EnhancedDispatcher(base_dispatcher, emitter)

    # Execute tool
    # REMOVED_SYNTAX_ERROR: result = await enhanced.execute("test_tool", {"param": "value"})

    # REMOVED_SYNTAX_ERROR: assert result == {"status": "success"}
    # REMOVED_SYNTAX_ERROR: assert mock_ws.send.call_count == 2  # executing and completed events


# REMOVED_SYNTAX_ERROR: class TestWebSocketConnectionPoolIntegration:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket connection pool integration."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_pool_manages_multiple_connections(self, ws_factory):
        # REMOVED_SYNTAX_ERROR: """Test connection pool manages multiple user connections."""
        # REMOVED_SYNTAX_ERROR: pool = ws_factory.connection_pool

        # Add connections for different users
        # REMOVED_SYNTAX_ERROR: users = ["user-1", "user-2", "user-3"]
        # REMOVED_SYNTAX_ERROR: connections = {}

        # REMOVED_SYNTAX_ERROR: for user_id in users:
            # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
            # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"

            # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
            # REMOVED_SYNTAX_ERROR: connections[user_id] = (conn_id, ws)

            # Verify all connections are tracked
            # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 3

            # Broadcast to specific user
            # REMOVED_SYNTAX_ERROR: await pool.broadcast_to_user("user-1", {"type": "test"})

            # Only user-1's WebSocket should receive
            # REMOVED_SYNTAX_ERROR: connections["user-1"][1].send.assert_called()
            # REMOVED_SYNTAX_ERROR: connections["user-2"][1].send.assert_not_called()
            # REMOVED_SYNTAX_ERROR: connections["user-3"][1].send.assert_not_called()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_connection_cleanup_on_disconnect(self, ws_factory):
                # REMOVED_SYNTAX_ERROR: """Test connections are cleaned up on disconnect."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: pool = ws_factory.connection_pool
                # REMOVED_SYNTAX_ERROR: user_id = "user-123"

                # Add connection
                # REMOVED_SYNTAX_ERROR: ws = Magic        ws.websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: ws.state = Magic        ws.state.name = "OPEN"

                # REMOVED_SYNTAX_ERROR: conn_id = await pool.add_connection(user_id, ws)
                # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 1

                # Simulate disconnect
                # REMOVED_SYNTAX_ERROR: ws.state.name = "CLOSED"

                # Cleanup inactive connections
                # REMOVED_SYNTAX_ERROR: removed = await pool.cleanup_inactive_connections()

                # REMOVED_SYNTAX_ERROR: assert removed > 0
                # REMOVED_SYNTAX_ERROR: assert pool.total_connections == 0
                # REMOVED_SYNTAX_ERROR: ws.close.assert_called()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_connection_limit_per_user(self, ws_factory):
                    # REMOVED_SYNTAX_ERROR: """Test connection limit per user is enforced."""
                    # REMOVED_SYNTAX_ERROR: pool = ws_factory.connection_pool
                    # REMOVED_SYNTAX_ERROR: user_id = "user-123"
                    # REMOVED_SYNTAX_ERROR: max_connections = pool.max_connections_per_user

                    # REMOVED_SYNTAX_ERROR: websockets = []

                    # Add max connections
                    # REMOVED_SYNTAX_ERROR: for i in range(max_connections + 1):
                        # REMOVED_SYNTAX_ERROR: ws = Magic            ws.websocket = TestWebSocketConnection()
                        # REMOVED_SYNTAX_ERROR: ws.state = Magic            ws.state.name = "OPEN"
                        # REMOVED_SYNTAX_ERROR: websockets.append(ws)

                        # REMOVED_SYNTAX_ERROR: await pool.add_connection(user_id, ws)

                        # Oldest connection should be closed
                        # REMOVED_SYNTAX_ERROR: websockets[0].close.assert_called()

                        # Should still have max_connections
                        # REMOVED_SYNTAX_ERROR: user_conns = pool.get_user_connections(user_id)
                        # REMOVED_SYNTAX_ERROR: assert len(user_conns) <= max_connections
                        # REMOVED_SYNTAX_ERROR: pass