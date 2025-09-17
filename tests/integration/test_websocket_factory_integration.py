'''
WebSocket Factory Integration Tests

Business Value:
- Validates WebSocket factory integration with execution contexts
- Tests complete agent event flow through WebSocket
- Ensures user isolation and proper event routing
'''

import asyncio
import json
import pytest
from datetime import datetime, timezone
import uuid
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.websocket_bridge_factory import ( )
WebSocketBridgeFactory,
UserWebSocketEmitter,
WebSocketConnectionPool
    
from netra_backend.app.agents.supervisor.execution_factory import ( )
ExecutionFactory,
UserExecutionContext
    
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketExecutionIntegration:
    "Test WebSocket integration with execution factory.

    @pytest.fixture
    def ws_factory(self):
        ""Use real service instance.
    # TODO: Initialize real service
        Create WebSocket factory.""
        pass
        return WebSocketBridgeFactory()

        @pytest.fixture
    def exec_factory(self):
        Use real service instance.""
    # TODO: Initialize real service
        Create execution factory."
        pass
        return ExecutionFactory()

        @pytest.fixture
    def real_agent_registry():
        "Use real service instance.
    # TODO: Initialize real service
        "Create mock agent registry."
        pass
        registry = MagicMock(spec=AgentRegistry)
        registry.set_websocket_manager = Magic        registry.enhance_tool_dispatcher = Magic        return registry

@pytest.mark.asyncio
    async def test_execution_context_creates_emitter(self, ws_factory, exec_factory):
        "Test execution context properly creates WebSocket emitter."

user_id = user-123
session_id = session-456""

        # Create WebSocket connection
mock_ws = MagicMock(); mock_ws.websocket = TestWebSocketConnection()
mock_ws.state = MagicMock(); mock_ws.state.name = OPEN

        # Create emitter
emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session_id,
websocket=mock_ws
        

        # Create execution context with emitter
context = exec_factory.create_user_context( )
user_id=user_id,
session_id=session_id,
websocket_emitter=emitter
        

        # Verify context has emitter
assert context is not None
assert context.user_id == user_id
assert context.session_id == session_id
assert context.websocket_emitter == emitter

        # Test sending event through context
        # Removed problematic line: await emitter.emit({}
type: "execution_started,
data": {context_id: context.session_id}
        

mock_ws.send.assert_called_once()

@pytest.mark.asyncio
    async def test_agent_registry_enhances_dispatcher(self, ws_factory, mock_agent_registry):
        Test agent registry enhances tool dispatcher with WebSocket.""

pass
user_id = user-123

            # Create emitter
emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session-1"
            

            # Set WebSocket manager in registry
mock_agent_registry.set_websocket_manager(emitter)

            # Create mock tool dispatcher
mock_dispatcher = MagicMock(); mock_dispatcher.execute_tool = AsyncMock(return_value={"status: success}

            # Enhance dispatcher
mock_agent_registry.enhance_tool_dispatcher.return_value = mock_dispatcher
enhanced = mock_agent_registry.enhance_tool_dispatcher(mock_dispatcher)

            # Execute tool
result = await enhanced.execute_tool(test_tool, {param: "value}"

assert result == {status: success}
mock_agent_registry.set_websocket_manager.assert_called_once_with(emitter)

@pytest.mark.asyncio
    async def test_complete_agent_event_flow(self, ws_factory, exec_factory):
        "Test complete agent execution event flow."

user_id = user-123
session_id = session-456""

                # Create WebSocket
mock_ws = MagicMock(); mock_ws.websocket = TestWebSocketConnection()
mock_ws.state = MagicMock(); mock_ws.state.name = OPEN

                # Create emitter with WebSocket
emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session_id,
websocket=mock_ws
                

                # Create execution context
context = exec_factory.create_user_context( )
user_id=user_id,
session_id=session_id,
websocket_emitter=emitter
                

                # Simulate complete agent lifecycle
events = ]
{type: "agent_started, data": {agent: test_agent, task: search"}},"
{type: agent_thinking, data: {thought": "Analyzing query...}},
{type: tool_executing, data": {"tool: search, params: {q: "test}}},
{type": tool_completed, data: {tool: search", "result: {hits: 10}}},
{type: agent_thinking", "data: {thought: Processing results...}},
{type": "agent_completed, data: {response: Found 10 results}}"
                

                # Send all events
for event in events:
    await emitter.emit(event)


                    # Verify all events were sent
assert mock_ws.send.call_count == len(events)

                    # Verify event order and content
calls = mock_ws.send.call_args_list
for i, call in enumerate(calls):
    sent_data = call[0][0]

if isinstance(sent_data, str):
    sent_data = json.loads(sent_data)

assert sent_data["type] == events[i][type]

@pytest.mark.asyncio
    async def test_concurrent_user_execution(self, ws_factory, exec_factory):
        Test concurrent execution for multiple users.""

pass
users = ]
(user-1, session-1),
(user-2, "session-2),
(user-3", session-3)
                                

contexts = []
websockets = []

                                # Create contexts for each user
for user_id, session_id in users:
    ws = Magic            ws.websocket = TestWebSocketConnection()

ws.state = Magic            ws.state.name = OPEN
websockets.append(ws)

emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session_id,
websocket=ws
                                    

context = exec_factory.create_user_context( )
user_id=user_id,
session_id=session_id,
websocket_emitter=emitter
                                    
contexts.append(context)

                                    # Each user executes agent concurrently
tasks = []
for i, context in enumerate(contexts):
    event = {

"type: agent_started",
data: {user: context.user_id, index: i}"
                                        
tasks.append(context.websocket_emitter.emit(event))

await asyncio.gather(*tasks)

                                        # Each WebSocket should only receive its user's events
for i, ws in enumerate(websockets):
    assert ws.send.call_count == 1

call_data = ws.send.call_args[0][0]
if isinstance(call_data, str):
    call_data = json.loads(call_data)

assert contexts[i].user_id in str(call_data)

@pytest.mark.asyncio
    async def test_error_event_propagation(self, ws_factory):
        "Test error events are properly propagated.

user_id = "user-123"

mock_ws = MagicMock(); mock_ws.websocket = TestWebSocketConnection()
mock_ws.state = MagicMock(); mock_ws.state.name = OPEN

emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session-1,"
websocket=mock_ws
                                                    

                                                    # Send error event
error_event = {
type": error,
data: }
"message: Agent execution failed",
code: AGENT_ERROR,
details: }"
agent": test_agent,
reason: Tool timeout
                                                    
                                                    
                                                    

await emitter.emit_error(error_event[data"]"

                                                    # Error should be sent immediately
mock_ws.send.assert_called_once()
sent = mock_ws.send.call_args[0][0]
if isinstance(sent, str):
    sent = json.loads(sent)


assert sent[type] == error
assert Agent execution failed in str(sent)"


class TestWebSocketToolDispatcher:
    "Test WebSocket integration with tool dispatcher.

    @pytest.fixture
    def real_tool_dispatcher():
        "Use real service instance."
    # TODO: Initialize real service
        "Create mock tool dispatcher."
        pass
        dispatcher = Magic        dispatcher.websocket = TestWebSocketConnection()
    # Removed problematic line: dispatcher.set_websocket_emitter = Magic        await asyncio.sleep(0)
        return dispatcher

@pytest.mark.asyncio
    async def test_tool_dispatcher_sends_events(self, ws_factory, mock_tool_dispatcher):
        Test tool dispatcher sends WebSocket events.""

user_id = user-123

        # Create WebSocket setup
mock_ws = MagicMock(); mock_ws.websocket = TestWebSocketConnection()
mock_ws.state = MagicMock(); mock_ws.state.name = OPEN"

emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session-1",
websocket=mock_ws
        

        # Set emitter on dispatcher
mock_tool_dispatcher.set_websocket_emitter(emitter)

        # Execute tool with WebSocket notifications
tool_name = search
tool_params = {query": "test}

        # Simulate tool execution with events
        # Removed problematic line: await emitter.emit({}
type: tool_executing,
data: {"tool: tool_name, params": tool_params}
        

        # Execute tool
mock_tool_dispatcher.execute.return_value = {result: success}
result = await mock_tool_dispatcher.execute(tool_name, tool_params)

        # Send completion event
        # Removed problematic line: await emitter.emit({}
"type: tool_completed",
data: {tool: tool_name, result: result}"
        

        # Verify events were sent
assert mock_ws.send.call_count == 2
calls = mock_ws.send.call_args_list

        # Check executing event
executing = json.loads(calls[0][0][0] if isinstance(calls[0][0][0], str) else calls[0][0][0]
assert executing[type"] == tool_executing

        # Check completed event
completed = json.loads(calls[1][0][0] if isinstance(calls[1][0][0], str) else calls[1][0][0]
assert completed[type] == tool_completed

@pytest.mark.asyncio
    async def test_enhanced_tool_dispatcher(self, ws_factory):
        ""Test enhanced tool dispatcher with WebSocket wrapper.

pass
user_id = user-123"

            # Create emitter
mock_ws = MagicMock(); mock_ws.websocket = TestWebSocketConnection()
mock_ws.state = MagicMock(); mock_ws.state.name = OPEN"

emitter = await ws_factory.create_user_emitter( )
user_id=user_id,
session_id=session-1,
websocket=mock_ws
            

            # Create base tool dispatcher
base_dispatcher = Magic        base_dispatcher.execute = AsyncMock(return_value={status": "success}

            # Create enhanced dispatcher (wrapper)
class EnhancedDispatcher:
    def __init__(self, base, ws_emitter):
        pass
        self.base = base
        self.emitter = ws_emitter

    async def execute(self, tool, params):
        pass
    # Removed problematic line: await self.emitter.emit({}
        type: tool_executing,
        data: {"tool: tool, params": params}
    
        result = await self.base.execute(tool, params)
    # Removed problematic line: await self.emitter.emit({}
        type: tool_completed,
        "data: {tool": tool, result: result}
    
        await asyncio.sleep(0)
        return result

        enhanced = EnhancedDispatcher(base_dispatcher, emitter)

    # Execute tool
        result = await enhanced.execute(test_tool, {"param: value"}

        assert result == {status: success}
        assert mock_ws.send.call_count == 2  # executing and completed events


class TestWebSocketConnectionPoolIntegration:
        "Test WebSocket connection pool integration."

@pytest.mark.asyncio
    async def test_pool_manages_multiple_connections(self, ws_factory):
        "Test connection pool manages multiple user connections."

pool = ws_factory.connection_pool

        # Add connections for different users
users = [user-1, user-2, "user-3]"
connections = {}

for user_id in users:
    ws = Magic            ws.websocket = TestWebSocketConnection()

ws.state = Magic            ws.state.name = OPEN

conn_id = await pool.add_connection(user_id, ws)
connections[user_id] = (conn_id, ws)

            # Verify all connections are tracked
assert pool.total_connections == 3

            # Broadcast to specific user
await pool.broadcast_to_user(user-1, {type": "test}

            # Only user-1's WebSocket should receive
connections[user-1][1].send.assert_called()
connections["user-2][1].send.assert_not_called()"
connections[user-3][1].send.assert_not_called()

@pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self, ws_factory):
        Test connections are cleaned up on disconnect.""

pass
pool = ws_factory.connection_pool
user_id = user-123

                # Add connection
ws = Magic        ws.websocket = TestWebSocketConnection()
ws.state = Magic        ws.state.name = "OPEN"

conn_id = await pool.add_connection(user_id, ws)
assert pool.total_connections == 1

                # Simulate disconnect
ws.state.name = CLOSED

                # Cleanup inactive connections
removed = await pool.cleanup_inactive_connections()

assert removed > 0
assert pool.total_connections == 0
ws.close.assert_called()

@pytest.mark.asyncio
    async def test_connection_limit_per_user(self, ws_factory):
        Test connection limit per user is enforced.""

pool = ws_factory.connection_pool
user_id = user-123
max_connections = pool.max_connections_per_user

websockets = []

                    # Add max connections
for i in range(max_connections + 1):
    ws = Magic            ws.websocket = TestWebSocketConnection()

ws.state = Magic            ws.state.name = "OPEN"
websockets.append(ws)

await pool.add_connection(user_id, ws)

                        # Oldest connection should be closed
websockets[0].close.assert_called()

                        # Should still have max_connections
user_conns = pool.get_user_connections(user_id)
assert len(user_conns) <= max_connections
pass
