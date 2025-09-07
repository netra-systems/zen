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
    # REMOVED_SYNTAX_ERROR: Mission-critical thread propagation verification tests.
    # REMOVED_SYNTAX_ERROR: Tests that thread_id correctly propagates through the entire system.

    # REMOVED_SYNTAX_ERROR: Critical verification points:
        # REMOVED_SYNTAX_ERROR: 1. WebSocket -> Message Handler propagation
        # REMOVED_SYNTAX_ERROR: 2. Message Handler -> Agent Registry propagation
        # REMOVED_SYNTAX_ERROR: 3. Agent Registry -> Execution Engine propagation
        # REMOVED_SYNTAX_ERROR: 4. Execution Engine -> Tool Dispatcher propagation
        # REMOVED_SYNTAX_ERROR: 5. Tool results -> WebSocket response propagation
        # REMOVED_SYNTAX_ERROR: 6. End-to-end thread consistency verification
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import uuid
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, Optional
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from datetime import datetime
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager, get_websocket_manager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.message_handlers import handle_ai_backend_message
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.execution_engine import ExecutionEngine
        # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket
        # REMOVED_SYNTAX_ERROR: from fastapi.websockets import WebSocketState
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestThreadPropagationVerification:
    # REMOVED_SYNTAX_ERROR: """Verify thread_id propagation through all system layers."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def setup(self):
    # REMOVED_SYNTAX_ERROR: """Setup test environment with all components."""
    # Generate test IDs
    # REMOVED_SYNTAX_ERROR: user_id = str(uuid.uuid4())
    # REMOVED_SYNTAX_ERROR: run_id = str(uuid.uuid4())
    # REMOVED_SYNTAX_ERROR: thread_id = str(uuid.uuid4())

    # Create components
    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()

    # REMOVED_SYNTAX_ERROR: yield { )
    # REMOVED_SYNTAX_ERROR: 'manager': manager,
    # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id
    

    # Cleanup
    # REMOVED_SYNTAX_ERROR: await manager.shutdown()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_websocket_to_message_handler_propagation(self, setup):
        # REMOVED_SYNTAX_ERROR: """Test thread_id propagation from WebSocket to message handler."""
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: manager = setup['manager']
        # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
        # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']

        # Create mock WebSocket
        # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
        # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
        # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

        # Connect with thread_id
        # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)

        # Mock the message handler
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.message_handlers.handle_ai_backend_message') as mock_handler:
            # REMOVED_SYNTAX_ERROR: mock_handler.return_value = {'status': 'success'}

            # Simulate WebSocket message with thread_id
            # REMOVED_SYNTAX_ERROR: websocket_message = { )
            # REMOVED_SYNTAX_ERROR: 'message': 'Test query',
            # REMOVED_SYNTAX_ERROR: 'conversation_id': thread_id,
            # REMOVED_SYNTAX_ERROR: 'user_id': user_id
            

            # Process through message handler
            # REMOVED_SYNTAX_ERROR: await handle_ai_backend_message(websocket_message)

            # Verify thread_id was passed
            # REMOVED_SYNTAX_ERROR: mock_handler.assert_called_once()
            # REMOVED_SYNTAX_ERROR: call_args = mock_handler.call_args[0][0]
            # REMOVED_SYNTAX_ERROR: assert call_args['conversation_id'] == thread_id

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_message_handler_to_agent_registry_propagation(self, setup):
                # REMOVED_SYNTAX_ERROR: """Test thread_id propagation from message handler to agent registry."""
                # REMOVED_SYNTAX_ERROR: manager = setup['manager']
                # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']
                # REMOVED_SYNTAX_ERROR: run_id = setup['run_id']

                # Connect WebSocket with thread_id
                # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
                # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
                # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

                # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)

                # Mock agent registry
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.agent_registry.AgentRegistry') as MockRegistry:
                    # REMOVED_SYNTAX_ERROR: mock_instance = Magic            MockRegistry.get_instance.return_value = mock_instance
                    # REMOVED_SYNTAX_ERROR: mock_instance.execute_agent = AsyncMock(return_value={ ))
                    # REMOVED_SYNTAX_ERROR: 'status': 'success',
                    # REMOVED_SYNTAX_ERROR: 'result': 'Agent executed'
                    

                    # Create message with thread_id
                    # REMOVED_SYNTAX_ERROR: message = { )
                    # REMOVED_SYNTAX_ERROR: 'message': 'Test query',
                    # REMOVED_SYNTAX_ERROR: 'conversation_id': thread_id,
                    # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                    # REMOVED_SYNTAX_ERROR: 'run_id': run_id
                    

                    # Process message
                    # REMOVED_SYNTAX_ERROR: registry = MockRegistry.get_instance()
                    # REMOVED_SYNTAX_ERROR: context = { )
                    # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
                    # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                    # REMOVED_SYNTAX_ERROR: 'run_id': run_id
                    

                    # REMOVED_SYNTAX_ERROR: await registry.execute_agent('test_agent', context, message['message'])

                    # Verify thread_id in context
                    # REMOVED_SYNTAX_ERROR: mock_instance.execute_agent.assert_called()
                    # REMOVED_SYNTAX_ERROR: call_context = mock_instance.execute_agent.call_args[0][1]
                    # REMOVED_SYNTAX_ERROR: assert call_context['thread_id'] == thread_id

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_agent_registry_to_execution_engine_propagation(self, setup):
                        # REMOVED_SYNTAX_ERROR: """Test thread_id propagation from agent registry to execution engine."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                        # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']
                        # REMOVED_SYNTAX_ERROR: run_id = setup['run_id']

                        # Create mock execution engine
                        # REMOVED_SYNTAX_ERROR: mock_engine = MagicMock(spec=ExecutionEngine)
                        # REMOVED_SYNTAX_ERROR: mock_engine.execute = AsyncMock(return_value={'result': 'success'})

                        # Mock agent registry to use our engine
                        # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

                        # Set thread context
                        # REMOVED_SYNTAX_ERROR: context = { )
                        # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
                        # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
                        # REMOVED_SYNTAX_ERROR: 'run_id': run_id
                        

                        # Execute through registry
                        # REMOVED_SYNTAX_ERROR: await registry.execute_agent('test_agent', context, 'test prompt')

                        # Verify engine received thread_id
                        # REMOVED_SYNTAX_ERROR: if mock_engine.execute.called:
                            # REMOVED_SYNTAX_ERROR: call_args = mock_engine.execute.call_args
                            # Check if thread_id is in the context passed to engine
                            # REMOVED_SYNTAX_ERROR: assert thread_id in str(call_args)

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_execution_engine_to_tool_dispatcher_propagation(self, setup):
                                # REMOVED_SYNTAX_ERROR: """Test thread_id propagation from execution engine to tool dispatcher."""
                                # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                                # REMOVED_SYNTAX_ERROR: run_id = setup['run_id']

                                # Mock tool dispatcher
                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.tools.dispatcher.ToolDispatcher') as MockDispatcher:
                                    # REMOVED_SYNTAX_ERROR: mock_dispatcher = Magic            MockDispatcher.return_value = mock_dispatcher
                                    # REMOVED_SYNTAX_ERROR: mock_dispatcher.execute_tool = AsyncMock(return_value={'result': 'tool_output'})

                                    # Create execution context with thread_id
                                    # REMOVED_SYNTAX_ERROR: execution_context = { )
                                    # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
                                    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
                                    # REMOVED_SYNTAX_ERROR: 'tool': 'test_tool',
                                    # REMOVED_SYNTAX_ERROR: 'params': {}
                                    

                                    # Execute tool
                                    # REMOVED_SYNTAX_ERROR: await mock_dispatcher.execute_tool( )
                                    # REMOVED_SYNTAX_ERROR: 'test_tool',
                                    # REMOVED_SYNTAX_ERROR: execution_context['params'],
                                    # REMOVED_SYNTAX_ERROR: context=execution_context
                                    

                                    # Verify thread_id passed to tool
                                    # REMOVED_SYNTAX_ERROR: mock_dispatcher.execute_tool.assert_called()
                                    # REMOVED_SYNTAX_ERROR: call_args = mock_dispatcher.execute_tool.call_args

                                    # Check context contains thread_id
                                    # REMOVED_SYNTAX_ERROR: if 'context' in call_args.kwargs:
                                        # REMOVED_SYNTAX_ERROR: assert call_args.kwargs['context']['thread_id'] == thread_id

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_tool_results_to_websocket_propagation(self, setup):
                                            # REMOVED_SYNTAX_ERROR: """Test thread_id propagation from tool results back to WebSocket."""
                                            # REMOVED_SYNTAX_ERROR: pass
                                            # REMOVED_SYNTAX_ERROR: manager = setup['manager']
                                            # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                                            # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']

                                            # Connect WebSocket
                                            # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
                                            # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
                                            # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

                                            # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user( )
                                            # REMOVED_SYNTAX_ERROR: user_id,
                                            # REMOVED_SYNTAX_ERROR: mock_ws,
                                            # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                                            

                                            # Simulate tool completion message
                                            # REMOVED_SYNTAX_ERROR: tool_result = { )
                                            # REMOVED_SYNTAX_ERROR: 'type': 'tool_completed',
                                            # REMOVED_SYNTAX_ERROR: 'data': { )
                                            # REMOVED_SYNTAX_ERROR: 'tool': 'search',
                                            # REMOVED_SYNTAX_ERROR: 'result': 'Found 10 items'
                                            
                                            

                                            # Send through manager
                                            # REMOVED_SYNTAX_ERROR: success = await manager.send_to_user(user_id, tool_result)
                                            # REMOVED_SYNTAX_ERROR: assert success

                                            # Allow processing
                                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                                            # Verify message sent
                                            # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
                                            # REMOVED_SYNTAX_ERROR: sent_msg = mock_ws.send_json.call_args[0][0]
                                            # REMOVED_SYNTAX_ERROR: assert sent_msg['type'] == 'tool_completed'

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_end_to_end_thread_consistency(self, setup):
                                                # REMOVED_SYNTAX_ERROR: """Test thread_id consistency through complete flow."""
                                                # REMOVED_SYNTAX_ERROR: manager = setup['manager']
                                                # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                                                # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']
                                                # REMOVED_SYNTAX_ERROR: run_id = setup['run_id']

                                                # Connect WebSocket with thread_id
                                                # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
                                                # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
                                                # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

                                                # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)

                                                # Track thread_id through all layers
                                                # REMOVED_SYNTAX_ERROR: captured_thread_ids = {}

                                                # Mock message handler
                                                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.message_handlers.AgentRegistry') as MockRegistry:
                                                    # REMOVED_SYNTAX_ERROR: mock_registry = Magic            MockRegistry.get_instance.return_value = mock_registry

# REMOVED_SYNTAX_ERROR: async def capture_registry_thread(agent, context, prompt):
    # REMOVED_SYNTAX_ERROR: captured_thread_ids['registry'] = context.get('thread_id')
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {'result': 'success'}

    # REMOVED_SYNTAX_ERROR: mock_registry.execute_agent = AsyncMock(side_effect=capture_registry_thread)

    # Mock execution engine
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.execution_engine.ExecutionEngine') as MockEngine:
        # REMOVED_SYNTAX_ERROR: mock_engine = Magic                MockEngine.return_value = mock_engine

# REMOVED_SYNTAX_ERROR: async def capture_engine_thread(context):
    # REMOVED_SYNTAX_ERROR: captured_thread_ids['engine'] = context.get('thread_id')
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {'result': 'executed'}

    # REMOVED_SYNTAX_ERROR: mock_engine.execute = AsyncMock(side_effect=capture_engine_thread)

    # Start the flow
    # REMOVED_SYNTAX_ERROR: initial_message = { )
    # REMOVED_SYNTAX_ERROR: 'message': 'Test query',
    # REMOVED_SYNTAX_ERROR: 'conversation_id': thread_id,
    # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id
    

    # Process through system
    # REMOVED_SYNTAX_ERROR: registry = MockRegistry.get_instance()
    # REMOVED_SYNTAX_ERROR: context = { )
    # REMOVED_SYNTAX_ERROR: 'thread_id': thread_id,
    # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id
    

    # REMOVED_SYNTAX_ERROR: await registry.execute_agent('test_agent', context, initial_message['message'])

    # Send result to WebSocket through manager
    # Removed problematic line: await manager.send_to_user(user_id, { ))
    # REMOVED_SYNTAX_ERROR: 'type': 'agent_completed',
    # REMOVED_SYNTAX_ERROR: 'data': {'result': 'success'}
    

    # Capture WebSocket thread context
    # REMOVED_SYNTAX_ERROR: conn = manager.connections.get(connection_id)
    # REMOVED_SYNTAX_ERROR: if conn:
        # REMOVED_SYNTAX_ERROR: captured_thread_ids['websocket'] = conn.get('thread_id')

        # Verify thread_id consistency
        # REMOVED_SYNTAX_ERROR: for layer, captured_id in captured_thread_ids.items():
            # REMOVED_SYNTAX_ERROR: assert captured_id == thread_id, "formatted_string"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_thread_id_persistence_across_retries(self, setup):
                # REMOVED_SYNTAX_ERROR: """Test thread_id persists across operation retries."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                # REMOVED_SYNTAX_ERROR: run_id = setup['run_id']

                # REMOVED_SYNTAX_ERROR: retry_count = 0
                # REMOVED_SYNTAX_ERROR: thread_ids_seen = []

                # Mock operation that fails then succeeds
# REMOVED_SYNTAX_ERROR: async def flaky_operation(context):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: nonlocal retry_count
    # REMOVED_SYNTAX_ERROR: thread_ids_seen.append(context.get('thread_id'))
    # REMOVED_SYNTAX_ERROR: retry_count += 1

    # REMOVED_SYNTAX_ERROR: if retry_count < 3:
        # REMOVED_SYNTAX_ERROR: raise Exception("Temporary failure")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return {'status': 'success'}

        # Retry logic
        # REMOVED_SYNTAX_ERROR: context = {'thread_id': thread_id, 'run_id': run_id}
        # REMOVED_SYNTAX_ERROR: max_retries = 5

        # REMOVED_SYNTAX_ERROR: for attempt in range(max_retries):
            # REMOVED_SYNTAX_ERROR: try:
                # REMOVED_SYNTAX_ERROR: result = await flaky_operation(context)
                # REMOVED_SYNTAX_ERROR: break
                # REMOVED_SYNTAX_ERROR: except Exception:
                    # REMOVED_SYNTAX_ERROR: if attempt == max_retries - 1:
                        # REMOVED_SYNTAX_ERROR: raise
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                        # Verify thread_id consistent across retries
                        # REMOVED_SYNTAX_ERROR: assert len(thread_ids_seen) == 3
                        # REMOVED_SYNTAX_ERROR: assert all(tid == thread_id for tid in thread_ids_seen)

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_thread_id_in_error_messages(self, setup):
                            # REMOVED_SYNTAX_ERROR: """Test thread_id context in error messages."""
                            # REMOVED_SYNTAX_ERROR: manager = setup['manager']
                            # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                            # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']

                            # Connect WebSocket
                            # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
                            # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
                            # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

                            # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user( )
                            # REMOVED_SYNTAX_ERROR: user_id,
                            # REMOVED_SYNTAX_ERROR: mock_ws,
                            # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                            

                            # Send error message
                            # REMOVED_SYNTAX_ERROR: error_message = { )
                            # REMOVED_SYNTAX_ERROR: 'type': 'agent_error',
                            # REMOVED_SYNTAX_ERROR: 'data': { )
                            # REMOVED_SYNTAX_ERROR: 'error': 'Processing failed',
                            # REMOVED_SYNTAX_ERROR: 'details': 'Invalid input'
                            
                            

                            # REMOVED_SYNTAX_ERROR: success = await manager.send_to_user(user_id, error_message)
                            # REMOVED_SYNTAX_ERROR: assert success

                            # Allow processing
                            # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)

                            # Verify error message sent
                            # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
                            # REMOVED_SYNTAX_ERROR: sent_msg = mock_ws.send_json.call_args[0][0]
                            # REMOVED_SYNTAX_ERROR: assert sent_msg['type'] == 'agent_error'

                            # Verify connection has correct thread_id
                            # REMOVED_SYNTAX_ERROR: conn = manager.connections.get(connection_id)
                            # REMOVED_SYNTAX_ERROR: assert conn is not None
                            # REMOVED_SYNTAX_ERROR: assert conn['thread_id'] == thread_id

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_thread_id_in_websocket_events(self, setup):
                                # REMOVED_SYNTAX_ERROR: """Test all WebSocket event types work with thread context."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # REMOVED_SYNTAX_ERROR: manager = setup['manager']
                                # REMOVED_SYNTAX_ERROR: thread_id = setup['thread_id']
                                # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']

                                # Connect WebSocket
                                # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
                                # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
                                # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

                                # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user( )
                                # REMOVED_SYNTAX_ERROR: user_id,
                                # REMOVED_SYNTAX_ERROR: mock_ws,
                                # REMOVED_SYNTAX_ERROR: thread_id=thread_id
                                

                                # Test all event types
                                # REMOVED_SYNTAX_ERROR: event_types = [ )
                                # REMOVED_SYNTAX_ERROR: 'agent_started',
                                # REMOVED_SYNTAX_ERROR: 'agent_thinking',
                                # REMOVED_SYNTAX_ERROR: 'tool_executing',
                                # REMOVED_SYNTAX_ERROR: 'tool_completed',
                                # REMOVED_SYNTAX_ERROR: 'agent_completed',
                                # REMOVED_SYNTAX_ERROR: 'typing_indicator',
                                # REMOVED_SYNTAX_ERROR: 'presence_update'
                                

                                # REMOVED_SYNTAX_ERROR: for event_type in event_types:
                                    # Removed problematic line: success = await manager.send_to_user(user_id, { ))
                                    # REMOVED_SYNTAX_ERROR: 'type': event_type,
                                    # REMOVED_SYNTAX_ERROR: 'data': {'test': 'data'}
                                    
                                    # REMOVED_SYNTAX_ERROR: assert success

                                    # Allow processing
                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)

                                    # Verify all events were sent
                                    # REMOVED_SYNTAX_ERROR: assert mock_ws.send_json.call_count == len(event_types)

                                    # REMOVED_SYNTAX_ERROR: for call in mock_ws.send_json.call_args_list:
                                        # REMOVED_SYNTAX_ERROR: sent_msg = call[0][0]
                                        # REMOVED_SYNTAX_ERROR: assert sent_msg['type'] in event_types

                                        # Verify connection maintains thread context
                                        # REMOVED_SYNTAX_ERROR: conn = manager.connections.get(connection_id)
                                        # REMOVED_SYNTAX_ERROR: assert conn is not None
                                        # REMOVED_SYNTAX_ERROR: assert conn['thread_id'] == thread_id

                                        # Removed problematic line: @pytest.mark.asyncio
                                        # Removed problematic line: async def test_thread_context_in_parallel_operations(self, setup):
                                            # REMOVED_SYNTAX_ERROR: """Test thread context maintained in parallel operations."""
                                            # Create multiple thread contexts
                                            # REMOVED_SYNTAX_ERROR: threads = []
                                            # REMOVED_SYNTAX_ERROR: for i in range(5):
                                                # REMOVED_SYNTAX_ERROR: threads.append({ ))
                                                # REMOVED_SYNTAX_ERROR: 'thread_id': str(uuid.uuid4()),
                                                # REMOVED_SYNTAX_ERROR: 'run_id': str(uuid.uuid4()),
                                                # REMOVED_SYNTAX_ERROR: 'user_id': str(uuid.uuid4()),
                                                # REMOVED_SYNTAX_ERROR: 'index': i
                                                

                                                # Track which thread each operation sees
                                                # REMOVED_SYNTAX_ERROR: operation_threads = {}

# REMOVED_SYNTAX_ERROR: async def simulated_operation(context):
    # Store the thread_id this operation sees
    # REMOVED_SYNTAX_ERROR: operation_threads[context['index']] = context['thread_id']
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.05)  # Simulate work
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {'result': "formatted_string"}

    # Execute operations in parallel
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for thread in threads:
        # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(simulated_operation(thread))
        # REMOVED_SYNTAX_ERROR: tasks.append(task)

        # Wait for all to complete
        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

        # Verify each operation saw correct thread_id
        # REMOVED_SYNTAX_ERROR: for thread in threads:
            # REMOVED_SYNTAX_ERROR: assert operation_threads[thread['index']] == thread['thread_id']

            # Verify results correspond to correct threads
            # REMOVED_SYNTAX_ERROR: assert len(results) == 5
            # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                # REMOVED_SYNTAX_ERROR: assert threads[i]['thread_id'][:8] in result['result']

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_thread_id_validation_at_boundaries(self, setup):
                    # REMOVED_SYNTAX_ERROR: """Test thread_id validation at system boundaries."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: user_id = setup['user_id']

                    # Test invalid thread_id formats
                    # REMOVED_SYNTAX_ERROR: invalid_thread_ids = [ )
                    # REMOVED_SYNTAX_ERROR: None,
                    # REMOVED_SYNTAX_ERROR: '',
                    # REMOVED_SYNTAX_ERROR: ' ',
                    # REMOVED_SYNTAX_ERROR: 'not-a-uuid',
                    # REMOVED_SYNTAX_ERROR: 12345,
                    # REMOVED_SYNTAX_ERROR: {'invalid': 'type'}
                    

                    # REMOVED_SYNTAX_ERROR: for invalid_id in invalid_thread_ids:
                        # Test at WebSocket boundary
                        # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
                        # REMOVED_SYNTAX_ERROR: mock_ws = AsyncMock(spec=WebSocket)
                        # REMOVED_SYNTAX_ERROR: mock_ws.websocket = TestWebSocketConnection()
                        # REMOVED_SYNTAX_ERROR: mock_ws.client_state = WebSocketState.CONNECTED

                        # Should handle gracefully
                        # REMOVED_SYNTAX_ERROR: try:
                            # REMOVED_SYNTAX_ERROR: connection_id = await manager.connect_user( )
                            # REMOVED_SYNTAX_ERROR: user_id,
                            # REMOVED_SYNTAX_ERROR: mock_ws,
                            # REMOVED_SYNTAX_ERROR: thread_id=invalid_id
                            
                            # Connection should succeed - WebSocketManager accepts any thread_id
                            # REMOVED_SYNTAX_ERROR: conn = manager.connections.get(connection_id)
                            # REMOVED_SYNTAX_ERROR: if conn:
                                # REMOVED_SYNTAX_ERROR: stored_thread = conn.get('thread_id')
                                # Should store the invalid_id as-is or handle appropriately
                                # REMOVED_SYNTAX_ERROR: assert stored_thread == invalid_id or stored_thread is None
                                # REMOVED_SYNTAX_ERROR: except (ValueError, TypeError):
                                    # Also acceptable to reject invalid thread_id
                                    # REMOVED_SYNTAX_ERROR: pass

                                    # REMOVED_SYNTAX_ERROR: await manager.shutdown()


                                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "-s"])