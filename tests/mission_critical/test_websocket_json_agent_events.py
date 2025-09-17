class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
        raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        MISSION CRITICAL: WebSocket JSON Agent Events Test Suite

        This test suite verifies that ALL WebSocket events for agent execution serialize correctly
        using the new factory-based patterns. Any failure here BREAKS chat functionality.

        CRITICAL WebSocket Events that MUST work:
        1. agent_started - User must see agent began processing
        2. agent_thinking - Real-time reasoning visibility
        3. tool_executing - Tool usage transparency
        4. tool_completed - Tool results display
        5. agent_completed - User must know when done

        NEW: Factory-Based Pattern Testing:
        - WebSocketBridgeFactory creates per-user emitters
        - UserWebSocketEmitter handles JSON serialization
        - Complete user isolation validation
        - All events must serialize to valid JSON

        Business Value Justification:
        - Segment: Platform/Internal
        - Business Goal: System Stability (prevents chat UI from appearing broken)
        - Value Impact: Ensures 90% of value delivery channel remains functional
        - Strategic Impact: WebSocket events are the primary user feedback mechanism
        '''

        import asyncio
        import json
        import pytest
        import time
        import uuid
        from datetime import datetime, timezone
        from typing import Any, Dict, List
        from shared.isolated_environment import IsolatedEnvironment

                # Import factory-based components
        from netra_backend.app.services.websocket_bridge_factory import ( )
        WebSocketBridgeFactory,
        UserWebSocketEmitter,
        UserWebSocketContext,
        UserWebSocketConnection,
        WebSocketEvent,
        WebSocketConnectionPool
                
        from netra_backend.app.agents.supervisor.execution_factory import ( )
        ExecutionEngineFactory,
        UserExecutionContext,
        ExecutionStatus
                

                # Keep legacy imports for state objects that still exist
        from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult
from netra_backend.app.schemas.websocket_models import ( )
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
BaseWebSocketPayload, AgentUpdatePayload, ToolCall, ToolResult,
AgentCompleted, StreamChunk, StreamComplete
                


class TestWebSocketJSONAgentEvents:
    "Test WebSocket JSON serialization for all critical agent events using factory patterns.""
    pass

    @pytest.fixture
    def mock_connection_pool(self):
        ""Create mock connection pool for testing."

class MockWebSocketConnection:
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.sent_events = []
        self.is_connected = True

    async def send_json(self, data: Dict[str, Any] -> None:
        if not self.is_connected:
        raise ConnectionError("WebSocket disconnected)
        self.sent_events.append(data)

    async def send_text(self, data: str) -> None:
        if not self.is_connected:
        raise ConnectionError(WebSocket disconnected")

    async def ping(self) -> None:
        if not self.is_connected:
        raise ConnectionError("WebSocket disconnected)

    async def close(self) -> None:
        self.is_connected = False

        @property
    def application_state(self):
        return Magic
class MockConnectionPool:
    async def __init__(self):
        self.connections = {}

    async def get_connection(self, connection_id: str, user_id: str):
        key = formatted_string"
        if key not in self.connections:
        self.connections[key] = MockWebSocketConnection(user_id, connection_id)

        connection_info = Magic                connection_info.websocket = self.connections[key]
        await asyncio.sleep(0)
        return connection_info

    def get_mock_connection(self, user_id: str, connection_id: str):
        key = "formatted_string
        return self.connections.get(key)

        return MockConnectionPool()

        @pytest.fixture
    def websocket_factory(self, mock_connection_pool):
        ""Create WebSocket factory configured with mock pool."
        pass
        factory = WebSocketBridgeFactory()
        factory.configure( )
        connection_pool=mock_connection_pool,
        agent_registry=None,  # Per-request pattern
        health_monitor=None
    
        return factory

        @pytest.fixture
    def test_user_context(self):
        "Create test user context.""
        return {
        'user_id': formatted_string",
        'thread_id': "formatted_string,
        'connection_id': formatted_string",
        'run_id': "formatted_string
    

        @pytest.fixture
    def complex_agent_state(self):
        ""Create a complex DeepAgentState for serialization testing."
        pass
        optimizations = OptimizationsResult( )
        optimization_type="cost_optimization,
        recommendations=[Reduce instance sizes", "Use spot instances],
        cost_savings=1250.75,
        performance_improvement=15.5,
        confidence_score=0.92
    

        action_plan = ActionPlanResult( )
        action_plan_summary=Comprehensive optimization plan",
        total_estimated_time="2-3 weeks,
        required_approvals=[Engineering Manager", "Finance],
        actions=[
        {id": 1, "action: Analyze current usage", "priority: high"},
        {"id: 2, action": "Implement changes, priority": "medium}
        ],
        execution_timeline=[
        {week": 1, "tasks: [Analysis", "Planning]},
        {week": 2, "tasks: [Implementation", "Testing]}
    
    

        return DeepAgentState( )
        user_request=Optimize our cloud infrastructure costs",
        chat_thread_id="thread-67890,
        user_id=user-test",
        run_id="run-12345,
        optimizations_result=optimizations,
        action_plan_result=action_plan,
        final_report=Optimization analysis complete with $1,250 potential savings",
        step_count=5,
        messages=[
        {"role: user", "content: Please analyze our costs"},
        {"role: assistant", "content: I"ll analyze your infrastructure costs"}
    
    

@pytest.mark.asyncio
    async def test_factory_agent_started_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
"Test agent_started event JSON serialization using factory pattern."
        # Create emitter
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
        

        # Send agent started notification
await emitter.notify_agent_started("TestAgent", test_user_context['run_id']
await asyncio.sleep(0.1)  # Allow processing

        # Get sent events
mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
        
sent_events = mock_conn.sent_events

assert len(sent_events) > 0, No events were sent

        # Test JSON serialization
event = sent_events[0]
json_str = json.dumps(event)
assert json_str is not None

        # Verify round-trip serialization
deserialized = json.loads(json_str)
assert deserialized["event_type"] == agent_started
assert deserialized["thread_id"] == test_user_context['thread_id']
assert data in deserialized
assert deserialized["data"][run_id] == test_user_context['run_id']

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_agent_thinking_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
""Test agent_thinking event JSON serialization using factory pattern.""
pass
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
            

thinking_text = I need to analyze the users request for cost optimization..."

await emitter.notify_agent_thinking("TestAgent, test_user_context['run_id'], thinking_text)
await asyncio.sleep(0.1)

            # Verify serialization
mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
            
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

            # Test JSON serialization
event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)

assert deserialized[event_type"] == "agent_thinking
assert deserialized[data"]["thinking] == thinking_text
assert deserialized[data"]["run_id] == test_user_context['run_id']

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_tool_executing_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
""Test tool_executing event JSON serialization using factory pattern."
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                

tool_name = "cost_analyzer_tool
tool_input = {query": "analyze costs, period": "30d}

await emitter.notify_tool_executing(TestAgent", test_user_context['run_id'], tool_name, tool_input)
await asyncio.sleep(0.1)

                # Verify serialization
mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                # Test JSON serialization
event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)

assert deserialized["event_type] == tool_executing"
assert deserialized["data][tool_name"] == tool_name
assert deserialized["data][tool_input"]["period] == 30d"
assert "timestamp in deserialized

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_tool_completed_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
""Test tool_completed event JSON serialization using factory pattern."
pass
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                    

tool_name = "cost_analyzer_tool
tool_result = {
analysis": "Found 3 optimization opportunities,
cost_savings": 1250.75,
"recommendations: [Use spot instances", "Reduce storage]
                    

await emitter.notify_tool_completed(TestAgent", test_user_context['run_id'], tool_name, tool_result)
await asyncio.sleep(0.1)

                    # Verify serialization
mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                    
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                    # Test JSON serialization including complex nested data
event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)

assert deserialized["event_type] == tool_completed"
assert deserialized["data][tool_name"] == tool_name
assert deserialized["data][tool_output"]["cost_savings] == 1250.75
assert len(deserialized[data"]["tool_output][recommendations"] == 2

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_agent_completed_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
"Test agent_completed event JSON serialization using factory pattern.""
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                        

completion_result = {
status": "success,
summary": "Cost optimization analysis complete,
total_savings": 1250.75,
"recommendations_count: 5
                        

await emitter.notify_agent_completed(TestAgent", test_user_context['run_id'], completion_result)
await asyncio.sleep(0.1)

                        # Verify serialization
mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                        
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                        # Test JSON serialization
event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)

assert deserialized["event_type] == agent_completed"
assert deserialized["data][result"]["status] == success"
assert deserialized["data][result"]["total_savings] == 1250.75
assert deserialized[data"]["run_id] == test_user_context['run_id']

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_deep_agent_state_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context, complex_agent_state):
""Test DeepAgentState serialization through factory WebSocket events."
pass
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                            

                            # Send complex state through agent completion
await emitter.notify_agent_completed("TestAgent, test_user_context['run_id'], complex_agent_state.__dict__)
await asyncio.sleep(0.1)

mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                            
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                            # Verify it's JSON serializable
event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)

                            # Verify complex nested objects are serialized
result_data = deserialized[data"]["result]
assert result_data[user_request"] == "Optimize our cloud infrastructure costs
assert result_data[run_id"] == "run-12345
assert result_data[step_count"] == 5

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_all_websocket_event_types_serialize(self, websocket_factory, mock_connection_pool, test_user_context):
"Test that all critical WebSocket event types can be JSON serialized through factory pattern.""
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                                

                                # List of all critical events that must work
critical_events = [
(agent_started", lambda x: None emitter.notify_agent_started("TestAgent, test_user_context['run_id']),
(agent_thinking", lambda x: None emitter.notify_agent_thinking("TestAgent, test_user_context['run_id'], Analyzing request")),
("tool_executing, lambda x: None emitter.notify_tool_executing(TestAgent", test_user_context['run_id'], "analysis_tool, {query": "test}),
(tool_completed", lambda x: None emitter.notify_tool_completed("TestAgent, test_user_context['run_id'], analysis_tool", {"result: success"}),
("agent_completed, lambda x: None emitter.notify_agent_completed(TestAgent", test_user_context['run_id'], {"status: complete"})
                                

mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                                

for event_name, send_func in critical_events:
                                    # Clear previous events
mock_conn.sent_events.clear()

                                    # Send the event
await send_func()
await asyncio.sleep(0.1)

                                    # Verify it was sent and is JSON serializable
assert len(mock_conn.sent_events) > 0, "formatted_string

event = mock_conn.sent_events[0]

                                    # Critical: Must be JSON serializable
try:
    json_str = json.dumps(event)
deserialized = json.loads(json_str)
assert deserialized[event_type"] == event_name
except (TypeError, ValueError) as e:
    pytest.fail("formatted_string)

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_special_characters_handling(self, websocket_factory, mock_connection_pool, test_user_context):
""Test factory WebSocket handling of special characters and unicode."
pass
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                                                

                                                # Message with various special characters and unicode
special_thinking = "Hello [U+1F31F] Special chars: [U+00E1][U+00E9][U+00ED][U+00F3][U+00FA] [U+00F1] [U+00E7][U+00C7] [U+4E2D][U+6587] pucck[U+0438][U+0439] [U+0627][U+0644][U+0639][U+0631][U+0628][U+064A][U+0629]

await emitter.notify_agent_thinking(TestAgent", test_user_context['run_id'], special_thinking)
await asyncio.sleep(0.1)

mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                                                
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                                                # Should serialize without issues
event = sent_events[0]
json_str = json.dumps(event, ensure_ascii=False)
deserialized = json.loads(json_str)

                                                # Verify special characters are preserved
assert "[U+1F31F] in deserialized[data"]["thinking]
assert [U+4E2D][U+6587]" in deserialized["data][thinking"]

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_concurrent_serialization(self, websocket_factory, mock_connection_pool):
"Test concurrent serialization doesn't cause issues with factory pattern.""
                                                    # Create multiple emitters for different users
user_contexts = []
emitters = []

for i in range(5):
    user_context = {
'user_id': formatted_string",
'thread_id': "formatted_string,
'connection_id': formatted_string",
'run_id': "formatted_string
                                                        
user_contexts.append(user_context)

emitter = await websocket_factory.create_user_emitter( )
user_id=user_context['user_id'],
thread_id=user_context['thread_id'],
connection_id=user_context['connection_id']
                                                        
emitters.append(emitter)

                                                        Send events concurrently from all emitters
tasks = []
for i, emitter in enumerate(emitters):
    task = emitter.notify_agent_started(formatted_string", user_contexts[i]['run_id']
tasks.append(task)

await asyncio.gather(*tasks)
await asyncio.sleep(0.1)

                                                            # Verify all events were sent and are JSON serializable
for i, user_context in enumerate(user_contexts):
    mock_conn = mock_connection_pool.get_mock_connection( )
user_context['user_id'],
user_context['connection_id']
                                                                
sent_events = mock_conn.sent_events

assert len(sent_events) > 0, "formatted_string

event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)
assert deserialized[event_type"] == "agent_started
assert deserialized[data"]["agent_name] == formatted_string"

                                                                # Clean up all emitters
cleanup_tasks = [emitter.cleanup() for emitter in emitters]
await asyncio.gather(*cleanup_tasks)

@pytest.mark.asyncio
    async def test_factory_message_ordering_preservation(self, websocket_factory, mock_connection_pool, test_user_context):
"Test that factory WebSocket message ordering is preserved during serialization.""
pass
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                                                                    

                                                                    # Send sequence of messages that must maintain order
await emitter.notify_agent_started(TestAgent", test_user_context['run_id']
await emitter.notify_agent_thinking("TestAgent, test_user_context['run_id'], step 1")
await emitter.notify_tool_executing("TestAgent, test_user_context['run_id'], analyzer", {"step: 2}
await emitter.notify_tool_completed(TestAgent", test_user_context['run_id'], "analyzer, {result": "done, step": 3}
await emitter.notify_agent_completed("TestAgent, test_user_context['run_id'], {status": "success, step": 4}

await asyncio.sleep(0.2)  # Allow all events to process

mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                                                                    
sent_events = mock_conn.sent_events

assert len(sent_events) == 5, "formatted_string

                                                                    # Verify order is preserved and all are JSON serializable
expected_types = [agent_started", "agent_thinking, tool_executing", "tool_completed, agent_completed"]

for i, event in enumerate(sent_events):
    json_str = json.dumps(event)
deserialized = json.loads(json_str)
assert deserialized["event_type] == expected_types[i]

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_large_message_handling(self, websocket_factory, mock_connection_pool, test_user_context):
""Test factory handling of large messages."
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                                                                            

                                                                            # Create large tool result
large_result = {
"analysis: x" * 10000,  # 10KB of data
"detailed_recommendations: [rec_ + y * 1000 for _ in range(50)],  # 50KB more
metadata": {
"size: large",
"processing_time: 5000.0,
confidence": 0.95
                                                                            
                                                                            

await emitter.notify_tool_completed("TestAgent, test_user_context['run_id'], large_analyzer", large_result)
await asyncio.sleep(0.1)

mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                                                                            
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                                                                            # Should still serialize correctly
event = sent_events[0]
json_str = json.dumps(event)
assert len(json_str) > 50000  # Should be large

                                                                            # Verify content is preserved
deserialized = json.loads(json_str)
assert len(deserialized["data][tool_output"]["analysis] == 10000
assert len(deserialized[data"]["tool_output][detailed_recommendations"] == 50

await emitter.cleanup()

@pytest.mark.asyncio
    async def test_factory_error_handling_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
"Test that error scenarios still produce valid JSON through factory pattern.""
pass
emitter = await websocket_factory.create_user_emitter( )
user_id=test_user_context['user_id'],
thread_id=test_user_context['thread_id'],
connection_id=test_user_context['connection_id']
                                                                                

                                                                                # Send error notification
error_details = TimeoutError: Tool execution exceeded 30 seconds"

await emitter.notify_agent_error("TestAgent, test_user_context['run_id'], error_details)
await asyncio.sleep(0.1)

mock_conn = mock_connection_pool.get_mock_connection( )
test_user_context['user_id'],
test_user_context['connection_id']
                                                                                
sent_events = mock_conn.sent_events

assert len(sent_events) > 0

                                                                                # Must be JSON serializable even for errors
event = sent_events[0]
json_str = json.dumps(event)
deserialized = json.loads(json_str)

assert deserialized[event_type"] == "agent_error
assert TimeoutError" in deserialized["data][error"]

await emitter.cleanup()

def test_websocket_event_structure_validation(self):
"Test WebSocketEvent structure validation.""
    # Test valid event creation
event = WebSocketEvent( )
event_type=agent_started",
user_id="test_user,
thread_id=test_thread",
data={"agent_name: TestAgent", "run_id: run_123"}
    

    # Verify all required fields exist
assert hasattr(event, 'event_type')
assert hasattr(event, 'user_id')
assert hasattr(event, 'thread_id')
assert hasattr(event, 'data')
assert hasattr(event, 'event_id')
assert hasattr(event, 'timestamp')

    # Test JSON serialization of event structure
event_dict = {
'event_type': event.event_type,
'event_id': event.event_id,
'thread_id': event.thread_id,
'data': event.data,
'timestamp': event.timestamp.isoformat()
    

json_str = json.dumps(event_dict)
deserialized = json.loads(json_str)

assert deserialized['event_type'] == "agent_started
assert deserialized['thread_id'] == test_thread"
assert deserialized['data']['agent_name'] == "TestAgent"
pass
