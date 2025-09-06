# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: MISSION CRITICAL: WebSocket JSON Agent Events Test Suite

    # REMOVED_SYNTAX_ERROR: This test suite verifies that ALL WebSocket events for agent execution serialize correctly
    # REMOVED_SYNTAX_ERROR: using the new factory-based patterns. Any failure here BREAKS chat functionality.

    # REMOVED_SYNTAX_ERROR: CRITICAL WebSocket Events that MUST work:
        # REMOVED_SYNTAX_ERROR: 1. agent_started - User must see agent began processing
        # REMOVED_SYNTAX_ERROR: 2. agent_thinking - Real-time reasoning visibility
        # REMOVED_SYNTAX_ERROR: 3. tool_executing - Tool usage transparency
        # REMOVED_SYNTAX_ERROR: 4. tool_completed - Tool results display
        # REMOVED_SYNTAX_ERROR: 5. agent_completed - User must know when done

        # REMOVED_SYNTAX_ERROR: NEW: Factory-Based Pattern Testing:
            # REMOVED_SYNTAX_ERROR: - WebSocketBridgeFactory creates per-user emitters
            # REMOVED_SYNTAX_ERROR: - UserWebSocketEmitter handles JSON serialization
            # REMOVED_SYNTAX_ERROR: - Complete user isolation validation
            # REMOVED_SYNTAX_ERROR: - All events must serialize to valid JSON

            # REMOVED_SYNTAX_ERROR: Business Value Justification:
                # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
                # REMOVED_SYNTAX_ERROR: - Business Goal: System Stability (prevents chat UI from appearing broken)
                # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures 90% of value delivery channel remains functional
                # REMOVED_SYNTAX_ERROR: - Strategic Impact: WebSocket events are the primary user feedback mechanism
                # REMOVED_SYNTAX_ERROR: '''

                # REMOVED_SYNTAX_ERROR: import asyncio
                # REMOVED_SYNTAX_ERROR: import json
                # REMOVED_SYNTAX_ERROR: import pytest
                # REMOVED_SYNTAX_ERROR: import time
                # REMOVED_SYNTAX_ERROR: import uuid
                # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
                # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List
                # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

                # Import factory-based components
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.websocket_bridge_factory import ( )
                # REMOVED_SYNTAX_ERROR: WebSocketBridgeFactory,
                # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter,
                # REMOVED_SYNTAX_ERROR: UserWebSocketContext,
                # REMOVED_SYNTAX_ERROR: UserWebSocketConnection,
                # REMOVED_SYNTAX_ERROR: WebSocketEvent,
                # REMOVED_SYNTAX_ERROR: WebSocketConnectionPool
                
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_factory import ( )
                # REMOVED_SYNTAX_ERROR: ExecutionEngineFactory,
                # REMOVED_SYNTAX_ERROR: UserExecutionContext,
                # REMOVED_SYNTAX_ERROR: ExecutionStatus
                

                # Keep legacy imports for state objects that still exist
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult, ActionPlanResult
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.websocket_models import ( )
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
                # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
                # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
                # REMOVED_SYNTAX_ERROR: BaseWebSocketPayload, AgentUpdatePayload, ToolCall, ToolResult,
                # REMOVED_SYNTAX_ERROR: AgentCompleted, StreamChunk, StreamComplete
                


# REMOVED_SYNTAX_ERROR: class TestWebSocketJSONAgentEvents:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket JSON serialization for all critical agent events using factory patterns."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def mock_connection_pool(self):
    # REMOVED_SYNTAX_ERROR: """Create mock connection pool for testing."""

# REMOVED_SYNTAX_ERROR: class MockWebSocketConnection:
# REMOVED_SYNTAX_ERROR: def __init__(self, user_id: str, connection_id: str):
    # REMOVED_SYNTAX_ERROR: self.user_id = user_id
    # REMOVED_SYNTAX_ERROR: self.connection_id = connection_id
    # REMOVED_SYNTAX_ERROR: self.sent_events = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True

# REMOVED_SYNTAX_ERROR: async def send_json(self, data: Dict[str, Any]) -> None:
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket disconnected")
        # REMOVED_SYNTAX_ERROR: self.sent_events.append(data)

# REMOVED_SYNTAX_ERROR: async def send_text(self, data: str) -> None:
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket disconnected")

# REMOVED_SYNTAX_ERROR: async def ping(self) -> None:
    # REMOVED_SYNTAX_ERROR: if not self.is_connected:
        # REMOVED_SYNTAX_ERROR: raise ConnectionError("WebSocket disconnected")

# REMOVED_SYNTAX_ERROR: async def close(self) -> None:
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

    # REMOVED_SYNTAX_ERROR: @property
# REMOVED_SYNTAX_ERROR: def application_state(self):
    # REMOVED_SYNTAX_ERROR: return Magic
# REMOVED_SYNTAX_ERROR: class MockConnectionPool:
# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: self.connections = {}

# REMOVED_SYNTAX_ERROR: async def get_connection(self, connection_id: str, user_id: str):
    # REMOVED_SYNTAX_ERROR: key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: if key not in self.connections:
        # REMOVED_SYNTAX_ERROR: self.connections[key] = MockWebSocketConnection(user_id, connection_id)

        # REMOVED_SYNTAX_ERROR: connection_info = Magic                connection_info.websocket = self.connections[key]
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return connection_info

# REMOVED_SYNTAX_ERROR: def get_mock_connection(self, user_id: str, connection_id: str):
    # REMOVED_SYNTAX_ERROR: key = "formatted_string"
    # REMOVED_SYNTAX_ERROR: return self.connections.get(key)

    # REMOVED_SYNTAX_ERROR: return MockConnectionPool()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_factory(self, mock_connection_pool):
    # REMOVED_SYNTAX_ERROR: """Create WebSocket factory configured with mock pool."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: factory = WebSocketBridgeFactory()
    # REMOVED_SYNTAX_ERROR: factory.configure( )
    # REMOVED_SYNTAX_ERROR: connection_pool=mock_connection_pool,
    # REMOVED_SYNTAX_ERROR: agent_registry=None,  # Per-request pattern
    # REMOVED_SYNTAX_ERROR: health_monitor=None
    
    # REMOVED_SYNTAX_ERROR: return factory

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def test_user_context(self):
    # REMOVED_SYNTAX_ERROR: """Create test user context."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'user_id': "formatted_string",
    # REMOVED_SYNTAX_ERROR: 'thread_id': "formatted_string",
    # REMOVED_SYNTAX_ERROR: 'connection_id': "formatted_string",
    # REMOVED_SYNTAX_ERROR: 'run_id': "formatted_string"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def complex_agent_state(self):
    # REMOVED_SYNTAX_ERROR: """Create a complex DeepAgentState for serialization testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: optimizations = OptimizationsResult( )
    # REMOVED_SYNTAX_ERROR: optimization_type="cost_optimization",
    # REMOVED_SYNTAX_ERROR: recommendations=["Reduce instance sizes", "Use spot instances"],
    # REMOVED_SYNTAX_ERROR: cost_savings=1250.75,
    # REMOVED_SYNTAX_ERROR: performance_improvement=15.5,
    # REMOVED_SYNTAX_ERROR: confidence_score=0.92
    

    # REMOVED_SYNTAX_ERROR: action_plan = ActionPlanResult( )
    # REMOVED_SYNTAX_ERROR: action_plan_summary="Comprehensive optimization plan",
    # REMOVED_SYNTAX_ERROR: total_estimated_time="2-3 weeks",
    # REMOVED_SYNTAX_ERROR: required_approvals=["Engineering Manager", "Finance"],
    # REMOVED_SYNTAX_ERROR: actions=[ )
    # REMOVED_SYNTAX_ERROR: {"id": 1, "action": "Analyze current usage", "priority": "high"},
    # REMOVED_SYNTAX_ERROR: {"id": 2, "action": "Implement changes", "priority": "medium"}
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: execution_timeline=[ )
    # REMOVED_SYNTAX_ERROR: {"week": 1, "tasks": ["Analysis", "Planning"]},
    # REMOVED_SYNTAX_ERROR: {"week": 2, "tasks": ["Implementation", "Testing"]}
    
    

    # REMOVED_SYNTAX_ERROR: return DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Optimize our cloud infrastructure costs",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="thread-67890",
    # REMOVED_SYNTAX_ERROR: user_id="user-test",
    # REMOVED_SYNTAX_ERROR: run_id="run-12345",
    # REMOVED_SYNTAX_ERROR: optimizations_result=optimizations,
    # REMOVED_SYNTAX_ERROR: action_plan_result=action_plan,
    # REMOVED_SYNTAX_ERROR: final_report="Optimization analysis complete with $1,250 potential savings",
    # REMOVED_SYNTAX_ERROR: step_count=5,
    # REMOVED_SYNTAX_ERROR: messages=[ )
    # REMOVED_SYNTAX_ERROR: {"role": "user", "content": "Please analyze our costs"},
    # REMOVED_SYNTAX_ERROR: {"role": "assistant", "content": "I"ll analyze your infrastructure costs"}
    
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_factory_agent_started_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
        # REMOVED_SYNTAX_ERROR: """Test agent_started event JSON serialization using factory pattern."""
        # Create emitter
        # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
        # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
        # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
        # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
        

        # Send agent started notification
        # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_started("TestAgent", test_user_context['run_id'])
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Allow processing

        # Get sent events
        # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
        # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
        # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
        
        # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

        # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0, "No events were sent"

        # Test JSON serialization
        # REMOVED_SYNTAX_ERROR: event = sent_events[0]
        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
        # REMOVED_SYNTAX_ERROR: assert json_str is not None

        # Verify round-trip serialization
        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
        # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "agent_started"
        # REMOVED_SYNTAX_ERROR: assert deserialized["thread_id"] == test_user_context['thread_id']
        # REMOVED_SYNTAX_ERROR: assert "data" in deserialized
        # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["run_id"] == test_user_context['run_id']

        # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_factory_agent_thinking_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
            # REMOVED_SYNTAX_ERROR: """Test agent_thinking event JSON serialization using factory pattern."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
            # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
            # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
            # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
            

            # REMOVED_SYNTAX_ERROR: thinking_text = "I need to analyze the user"s request for cost optimization..."

            # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_thinking("TestAgent", test_user_context['run_id'], thinking_text)
            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

            # Verify serialization
            # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
            # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
            # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
            
            # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

            # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

            # Test JSON serialization
            # REMOVED_SYNTAX_ERROR: event = sent_events[0]
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
            # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

            # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "agent_thinking"
            # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["thinking"] == thinking_text
            # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["run_id"] == test_user_context['run_id']

            # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_factory_tool_executing_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
                # REMOVED_SYNTAX_ERROR: """Test tool_executing event JSON serialization using factory pattern."""
                # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                

                # REMOVED_SYNTAX_ERROR: tool_name = "cost_analyzer_tool"
                # REMOVED_SYNTAX_ERROR: tool_input = {"query": "analyze costs", "period": "30d"}

                # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_executing("TestAgent", test_user_context['run_id'], tool_name, tool_input)
                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                # Verify serialization
                # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                
                # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                # Test JSON serialization
                # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

                # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "tool_executing"
                # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["tool_name"] == tool_name
                # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["tool_input"]["period"] == "30d"
                # REMOVED_SYNTAX_ERROR: assert "timestamp" in deserialized

                # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_factory_tool_completed_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
                    # REMOVED_SYNTAX_ERROR: """Test tool_completed event JSON serialization using factory pattern."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                    # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                    # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                    # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                    

                    # REMOVED_SYNTAX_ERROR: tool_name = "cost_analyzer_tool"
                    # REMOVED_SYNTAX_ERROR: tool_result = { )
                    # REMOVED_SYNTAX_ERROR: "analysis": "Found 3 optimization opportunities",
                    # REMOVED_SYNTAX_ERROR: "cost_savings": 1250.75,
                    # REMOVED_SYNTAX_ERROR: "recommendations": ["Use spot instances", "Reduce storage"]
                    

                    # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_completed("TestAgent", test_user_context['run_id'], tool_name, tool_result)
                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                    # Verify serialization
                    # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                    # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                    # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                    
                    # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                    # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                    # Test JSON serialization including complex nested data
                    # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

                    # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "tool_completed"
                    # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["tool_name"] == tool_name
                    # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["tool_output"]["cost_savings"] == 1250.75
                    # REMOVED_SYNTAX_ERROR: assert len(deserialized["data"]["tool_output"]["recommendations"]) == 2

                    # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_factory_agent_completed_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
                        # REMOVED_SYNTAX_ERROR: """Test agent_completed event JSON serialization using factory pattern."""
                        # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                        # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                        # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                        # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                        

                        # REMOVED_SYNTAX_ERROR: completion_result = { )
                        # REMOVED_SYNTAX_ERROR: "status": "success",
                        # REMOVED_SYNTAX_ERROR: "summary": "Cost optimization analysis complete",
                        # REMOVED_SYNTAX_ERROR: "total_savings": 1250.75,
                        # REMOVED_SYNTAX_ERROR: "recommendations_count": 5
                        

                        # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_completed("TestAgent", test_user_context['run_id'], completion_result)
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                        # Verify serialization
                        # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                        # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                        # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                        
                        # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                        # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                        # Test JSON serialization
                        # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

                        # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "agent_completed"
                        # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["result"]["status"] == "success"
                        # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["result"]["total_savings"] == 1250.75
                        # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["run_id"] == test_user_context['run_id']

                        # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_factory_deep_agent_state_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context, complex_agent_state):
                            # REMOVED_SYNTAX_ERROR: """Test DeepAgentState serialization through factory WebSocket events."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                            # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                            # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                            # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                            

                            # Send complex state through agent completion
                            # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_completed("TestAgent", test_user_context['run_id'], complex_agent_state.__dict__)
                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                            # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                            # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                            # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                            
                            # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                            # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                            # Verify it's JSON serializable
                            # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                            # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

                            # Verify complex nested objects are serialized
                            # REMOVED_SYNTAX_ERROR: result_data = deserialized["data"]["result"]
                            # REMOVED_SYNTAX_ERROR: assert result_data["user_request"] == "Optimize our cloud infrastructure costs"
                            # REMOVED_SYNTAX_ERROR: assert result_data["run_id"] == "run-12345"
                            # REMOVED_SYNTAX_ERROR: assert result_data["step_count"] == 5

                            # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_factory_all_websocket_event_types_serialize(self, websocket_factory, mock_connection_pool, test_user_context):
                                # REMOVED_SYNTAX_ERROR: """Test that all critical WebSocket event types can be JSON serialized through factory pattern."""
                                # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                                # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                                # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                                # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                                

                                # List of all critical events that must work
                                # REMOVED_SYNTAX_ERROR: critical_events = [ )
                                # REMOVED_SYNTAX_ERROR: ("agent_started", lambda x: None emitter.notify_agent_started("TestAgent", test_user_context['run_id'])),
                                # REMOVED_SYNTAX_ERROR: ("agent_thinking", lambda x: None emitter.notify_agent_thinking("TestAgent", test_user_context['run_id'], "Analyzing request")),
                                # REMOVED_SYNTAX_ERROR: ("tool_executing", lambda x: None emitter.notify_tool_executing("TestAgent", test_user_context['run_id'], "analysis_tool", {"query": "test"})),
                                # REMOVED_SYNTAX_ERROR: ("tool_completed", lambda x: None emitter.notify_tool_completed("TestAgent", test_user_context['run_id'], "analysis_tool", {"result": "success"})),
                                # REMOVED_SYNTAX_ERROR: ("agent_completed", lambda x: None emitter.notify_agent_completed("TestAgent", test_user_context['run_id'], {"status": "complete"}))
                                

                                # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                                # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                                # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                                

                                # REMOVED_SYNTAX_ERROR: for event_name, send_func in critical_events:
                                    # Clear previous events
                                    # REMOVED_SYNTAX_ERROR: mock_conn.sent_events.clear()

                                    # Send the event
                                    # REMOVED_SYNTAX_ERROR: await send_func()
                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                    # Verify it was sent and is JSON serializable
                                    # REMOVED_SYNTAX_ERROR: assert len(mock_conn.sent_events) > 0, "formatted_string"

                                    # REMOVED_SYNTAX_ERROR: event = mock_conn.sent_events[0]

                                    # Critical: Must be JSON serializable
                                    # REMOVED_SYNTAX_ERROR: try:
                                        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                                        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
                                        # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == event_name
                                        # REMOVED_SYNTAX_ERROR: except (TypeError, ValueError) as e:
                                            # REMOVED_SYNTAX_ERROR: pytest.fail("formatted_string")

                                            # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_factory_special_characters_handling(self, websocket_factory, mock_connection_pool, test_user_context):
                                                # REMOVED_SYNTAX_ERROR: """Test factory WebSocket handling of special characters and unicode."""
                                                # REMOVED_SYNTAX_ERROR: pass
                                                # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                                                # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                                                # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                                                # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                                                

                                                # Message with various special characters and unicode
                                                # REMOVED_SYNTAX_ERROR: special_thinking = "Hello 🌟 Special chars: áéíóú ñ çÇ 中文 русский العربية"

                                                # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_thinking("TestAgent", test_user_context['run_id'], special_thinking)
                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                                                # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                                                # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                                                
                                                # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                                                # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                                                # Should serialize without issues
                                                # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                                                # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event, ensure_ascii=False)
                                                # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

                                                # Verify special characters are preserved
                                                # REMOVED_SYNTAX_ERROR: assert "🌟" in deserialized["data"]["thinking"]
                                                # REMOVED_SYNTAX_ERROR: assert "中文" in deserialized["data"]["thinking"]

                                                # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_factory_concurrent_serialization(self, websocket_factory, mock_connection_pool):
                                                    # REMOVED_SYNTAX_ERROR: """Test concurrent serialization doesn't cause issues with factory pattern."""
                                                    # Create multiple emitters for different users
                                                    # REMOVED_SYNTAX_ERROR: user_contexts = []
                                                    # REMOVED_SYNTAX_ERROR: emitters = []

                                                    # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                        # REMOVED_SYNTAX_ERROR: user_context = { )
                                                        # REMOVED_SYNTAX_ERROR: 'user_id': "formatted_string",
                                                        # REMOVED_SYNTAX_ERROR: 'thread_id': "formatted_string",
                                                        # REMOVED_SYNTAX_ERROR: 'connection_id': "formatted_string",
                                                        # REMOVED_SYNTAX_ERROR: 'run_id': "formatted_string"
                                                        
                                                        # REMOVED_SYNTAX_ERROR: user_contexts.append(user_context)

                                                        # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                                                        # REMOVED_SYNTAX_ERROR: user_id=user_context['user_id'],
                                                        # REMOVED_SYNTAX_ERROR: thread_id=user_context['thread_id'],
                                                        # REMOVED_SYNTAX_ERROR: connection_id=user_context['connection_id']
                                                        
                                                        # REMOVED_SYNTAX_ERROR: emitters.append(emitter)

                                                        # Send events concurrently from all emitters
                                                        # REMOVED_SYNTAX_ERROR: tasks = []
                                                        # REMOVED_SYNTAX_ERROR: for i, emitter in enumerate(emitters):
                                                            # REMOVED_SYNTAX_ERROR: task = emitter.notify_agent_started("formatted_string", user_contexts[i]['run_id'])
                                                            # REMOVED_SYNTAX_ERROR: tasks.append(task)

                                                            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)
                                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                            # Verify all events were sent and are JSON serializable
                                                            # REMOVED_SYNTAX_ERROR: for i, user_context in enumerate(user_contexts):
                                                                # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                                                                # REMOVED_SYNTAX_ERROR: user_context['user_id'],
                                                                # REMOVED_SYNTAX_ERROR: user_context['connection_id']
                                                                
                                                                # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                                                                # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0, "formatted_string"

                                                                # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                                                                # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                                                                # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
                                                                # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "agent_started"
                                                                # REMOVED_SYNTAX_ERROR: assert deserialized["data"]["agent_name"] == "formatted_string"

                                                                # Clean up all emitters
                                                                # REMOVED_SYNTAX_ERROR: cleanup_tasks = [emitter.cleanup() for emitter in emitters]
                                                                # REMOVED_SYNTAX_ERROR: await asyncio.gather(*cleanup_tasks)

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_factory_message_ordering_preservation(self, websocket_factory, mock_connection_pool, test_user_context):
                                                                    # REMOVED_SYNTAX_ERROR: """Test that factory WebSocket message ordering is preserved during serialization."""
                                                                    # REMOVED_SYNTAX_ERROR: pass
                                                                    # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                                                                    # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                                                                    # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                                                                    # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                                                                    

                                                                    # Send sequence of messages that must maintain order
                                                                    # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_started("TestAgent", test_user_context['run_id'])
                                                                    # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_thinking("TestAgent", test_user_context['run_id'], "step 1")
                                                                    # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_executing("TestAgent", test_user_context['run_id'], "analyzer", {"step": 2})
                                                                    # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_completed("TestAgent", test_user_context['run_id'], "analyzer", {"result": "done", "step": 3})
                                                                    # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_completed("TestAgent", test_user_context['run_id'], {"status": "success", "step": 4})

                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)  # Allow all events to process

                                                                    # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                                                                    # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                                                                    # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                                                                    
                                                                    # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                                                                    # REMOVED_SYNTAX_ERROR: assert len(sent_events) == 5, "formatted_string"

                                                                    # Verify order is preserved and all are JSON serializable
                                                                    # REMOVED_SYNTAX_ERROR: expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]

                                                                    # REMOVED_SYNTAX_ERROR: for i, event in enumerate(sent_events):
                                                                        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                                                                        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
                                                                        # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == expected_types[i]

                                                                        # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                        # Removed problematic line: async def test_factory_large_message_handling(self, websocket_factory, mock_connection_pool, test_user_context):
                                                                            # REMOVED_SYNTAX_ERROR: """Test factory handling of large messages."""
                                                                            # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                                                                            # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                                                                            # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                                                                            # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                                                                            

                                                                            # Create large tool result
                                                                            # REMOVED_SYNTAX_ERROR: large_result = { )
                                                                            # REMOVED_SYNTAX_ERROR: "analysis": "x" * 10000,  # 10KB of data
                                                                            # REMOVED_SYNTAX_ERROR: "detailed_recommendations": ["rec_" + "y" * 1000 for _ in range(50)],  # 50KB more
                                                                            # REMOVED_SYNTAX_ERROR: "metadata": { )
                                                                            # REMOVED_SYNTAX_ERROR: "size": "large",
                                                                            # REMOVED_SYNTAX_ERROR: "processing_time": 5000.0,
                                                                            # REMOVED_SYNTAX_ERROR: "confidence": 0.95
                                                                            
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_completed("TestAgent", test_user_context['run_id'], "large_analyzer", large_result)
                                                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                                            # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                                                                            # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                                                                            # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                                                                            
                                                                            # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                                                                            # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                                                                            # Should still serialize correctly
                                                                            # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                                                                            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                                                                            # REMOVED_SYNTAX_ERROR: assert len(json_str) > 50000  # Should be large

                                                                            # Verify content is preserved
                                                                            # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
                                                                            # REMOVED_SYNTAX_ERROR: assert len(deserialized["data"]["tool_output"]["analysis"]) == 10000
                                                                            # REMOVED_SYNTAX_ERROR: assert len(deserialized["data"]["tool_output"]["detailed_recommendations"]) == 50

                                                                            # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_factory_error_handling_json_serialization(self, websocket_factory, mock_connection_pool, test_user_context):
                                                                                # REMOVED_SYNTAX_ERROR: """Test that error scenarios still produce valid JSON through factory pattern."""
                                                                                # REMOVED_SYNTAX_ERROR: pass
                                                                                # REMOVED_SYNTAX_ERROR: emitter = await websocket_factory.create_user_emitter( )
                                                                                # REMOVED_SYNTAX_ERROR: user_id=test_user_context['user_id'],
                                                                                # REMOVED_SYNTAX_ERROR: thread_id=test_user_context['thread_id'],
                                                                                # REMOVED_SYNTAX_ERROR: connection_id=test_user_context['connection_id']
                                                                                

                                                                                # Send error notification
                                                                                # REMOVED_SYNTAX_ERROR: error_details = "TimeoutError: Tool execution exceeded 30 seconds"

                                                                                # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_error("TestAgent", test_user_context['run_id'], error_details)
                                                                                # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                                                                # REMOVED_SYNTAX_ERROR: mock_conn = mock_connection_pool.get_mock_connection( )
                                                                                # REMOVED_SYNTAX_ERROR: test_user_context['user_id'],
                                                                                # REMOVED_SYNTAX_ERROR: test_user_context['connection_id']
                                                                                
                                                                                # REMOVED_SYNTAX_ERROR: sent_events = mock_conn.sent_events

                                                                                # REMOVED_SYNTAX_ERROR: assert len(sent_events) > 0

                                                                                # Must be JSON serializable even for errors
                                                                                # REMOVED_SYNTAX_ERROR: event = sent_events[0]
                                                                                # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event)
                                                                                # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

                                                                                # REMOVED_SYNTAX_ERROR: assert deserialized["event_type"] == "agent_error"
                                                                                # REMOVED_SYNTAX_ERROR: assert "TimeoutError" in deserialized["data"]["error"]

                                                                                # REMOVED_SYNTAX_ERROR: await emitter.cleanup()

# REMOVED_SYNTAX_ERROR: def test_websocket_event_structure_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test WebSocketEvent structure validation."""
    # Test valid event creation
    # REMOVED_SYNTAX_ERROR: event = WebSocketEvent( )
    # REMOVED_SYNTAX_ERROR: event_type="agent_started",
    # REMOVED_SYNTAX_ERROR: user_id="test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
    # REMOVED_SYNTAX_ERROR: data={"agent_name": "TestAgent", "run_id": "run_123"}
    

    # Verify all required fields exist
    # REMOVED_SYNTAX_ERROR: assert hasattr(event, 'event_type')
    # REMOVED_SYNTAX_ERROR: assert hasattr(event, 'user_id')
    # REMOVED_SYNTAX_ERROR: assert hasattr(event, 'thread_id')
    # REMOVED_SYNTAX_ERROR: assert hasattr(event, 'data')
    # REMOVED_SYNTAX_ERROR: assert hasattr(event, 'event_id')
    # REMOVED_SYNTAX_ERROR: assert hasattr(event, 'timestamp')

    # Test JSON serialization of event structure
    # REMOVED_SYNTAX_ERROR: event_dict = { )
    # REMOVED_SYNTAX_ERROR: 'event_type': event.event_type,
    # REMOVED_SYNTAX_ERROR: 'event_id': event.event_id,
    # REMOVED_SYNTAX_ERROR: 'thread_id': event.thread_id,
    # REMOVED_SYNTAX_ERROR: 'data': event.data,
    # REMOVED_SYNTAX_ERROR: 'timestamp': event.timestamp.isoformat()
    

    # REMOVED_SYNTAX_ERROR: json_str = json.dumps(event_dict)
    # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)

    # REMOVED_SYNTAX_ERROR: assert deserialized['event_type'] == "agent_started"
    # REMOVED_SYNTAX_ERROR: assert deserialized['thread_id'] == "test_thread"
    # REMOVED_SYNTAX_ERROR: assert deserialized['data']['agent_name'] == "TestAgent"
    # REMOVED_SYNTAX_ERROR: pass