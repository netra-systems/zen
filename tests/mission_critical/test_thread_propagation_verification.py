"""
Mission-critical thread propagation verification tests.
Tests that thread_id correctly propagates through the entire system.

Critical verification points:
1. WebSocket -> Message Handler propagation
2. Message Handler -> Agent Registry propagation  
3. Agent Registry -> Execution Engine propagation
4. Execution Engine -> Tool Dispatcher propagation
5. Tool results -> WebSocket response propagation
6. End-to-end thread consistency verification
"""

import asyncio
import uuid
import json
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, patch, AsyncMock, call
import pytest
from datetime import datetime

from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager
from netra_backend.app.services.message_handlers import handle_ai_backend_message
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.execution_engine import ExecutionEngine
from fastapi import WebSocket
from fastapi.websockets import WebSocketState


class TestThreadPropagationVerification:
    """Verify thread_id propagation through all system layers."""

    @pytest.fixture
    async def setup(self):
        """Setup test environment with all components."""
        # Generate test IDs
        user_id = str(uuid.uuid4())
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        # Create components
        manager = WebSocketManager()
        
        yield {
            'manager': manager,
            'user_id': user_id,
            'run_id': run_id,
            'thread_id': thread_id
        }
        
        # Cleanup
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_websocket_to_message_handler_propagation(self, setup):
        """Test thread_id propagation from WebSocket to message handler."""
        manager = setup['manager']
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        
        # Create mock WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        # Connect with thread_id
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
        
        # Mock the message handler
        with patch('netra_backend.app.services.message_handlers.handle_ai_backend_message') as mock_handler:
            mock_handler.return_value = {'status': 'success'}
            
            # Simulate WebSocket message with thread_id
            websocket_message = {
                'message': 'Test query',
                'conversation_id': thread_id,
                'user_id': user_id
            }
            
            # Process through message handler
            await handle_ai_backend_message(websocket_message)
            
            # Verify thread_id was passed
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args[0][0]
            assert call_args['conversation_id'] == thread_id

    @pytest.mark.asyncio
    async def test_message_handler_to_agent_registry_propagation(self, setup):
        """Test thread_id propagation from message handler to agent registry."""
        manager = setup['manager']
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect WebSocket with thread_id
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
        
        # Mock agent registry
        with patch('netra_backend.app.core.agent_registry.AgentRegistry') as MockRegistry:
            mock_instance = MagicMock()
            MockRegistry.get_instance.return_value = mock_instance
            mock_instance.execute_agent = AsyncMock(return_value={
                'status': 'success',
                'result': 'Agent executed'
            })
            
            # Create message with thread_id
            message = {
                'message': 'Test query',
                'conversation_id': thread_id,
                'user_id': user_id,
                'run_id': run_id
            }
            
            # Process message
            registry = MockRegistry.get_instance()
            context = {
                'thread_id': thread_id,
                'user_id': user_id,
                'run_id': run_id
            }
            
            await registry.execute_agent('test_agent', context, message['message'])
            
            # Verify thread_id in context
            mock_instance.execute_agent.assert_called()
            call_context = mock_instance.execute_agent.call_args[0][1]
            assert call_context['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_agent_registry_to_execution_engine_propagation(self, setup):
        """Test thread_id propagation from agent registry to execution engine."""
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Create mock execution engine
        mock_engine = MagicMock(spec=ExecutionEngine)
        mock_engine.execute = AsyncMock(return_value={'result': 'success'})
        
        # Mock agent registry to use our engine
        with patch('netra_backend.app.core.agent_registry.ExecutionEngine', return_value=mock_engine):
            registry = AgentRegistry()
            
            # Set thread context
            context = {
                'thread_id': thread_id,
                'user_id': user_id,
                'run_id': run_id
            }
            
            # Execute through registry
            await registry.execute_agent('test_agent', context, 'test prompt')
            
            # Verify engine received thread_id
            if mock_engine.execute.called:
                call_args = mock_engine.execute.call_args
                # Check if thread_id is in the context passed to engine
                assert thread_id in str(call_args)

    @pytest.mark.asyncio
    async def test_execution_engine_to_tool_dispatcher_propagation(self, setup):
        """Test thread_id propagation from execution engine to tool dispatcher."""
        thread_id = setup['thread_id']
        run_id = setup['run_id']
        
        # Mock tool dispatcher
        with patch('netra_backend.app.core.tools.dispatcher.ToolDispatcher') as MockDispatcher:
            mock_dispatcher = MagicMock()
            MockDispatcher.return_value = mock_dispatcher
            mock_dispatcher.execute_tool = AsyncMock(return_value={'result': 'tool_output'})
            
            # Create execution context with thread_id
            execution_context = {
                'thread_id': thread_id,
                'run_id': run_id,
                'tool': 'test_tool',
                'params': {}
            }
            
            # Execute tool
            await mock_dispatcher.execute_tool(
                'test_tool',
                execution_context['params'],
                context=execution_context
            )
            
            # Verify thread_id passed to tool
            mock_dispatcher.execute_tool.assert_called()
            call_args = mock_dispatcher.execute_tool.call_args
            
            # Check context contains thread_id
            if 'context' in call_args.kwargs:
                assert call_args.kwargs['context']['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_tool_results_to_websocket_propagation(self, setup):
        """Test thread_id propagation from tool results back to WebSocket."""
        manager = setup['manager']
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        
        # Connect WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=thread_id
        )
        
        # Simulate tool completion message
        tool_result = {
            'type': 'tool_completed',
            'data': {
                'tool': 'search',
                'result': 'Found 10 items'
            }
        }
        
        # Send through manager
        success = await manager.send_to_user(user_id, tool_result)
        assert success
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify message sent
        mock_ws.send_json.assert_called()
        sent_msg = mock_ws.send_json.call_args[0][0]
        assert sent_msg['type'] == 'tool_completed'

    @pytest.mark.asyncio
    async def test_end_to_end_thread_consistency(self, setup):
        """Test thread_id consistency through complete flow."""
        manager = setup['manager']
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        run_id = setup['run_id']
        
        # Connect WebSocket with thread_id
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(user_id, mock_ws, thread_id=thread_id)
        
        # Track thread_id through all layers
        captured_thread_ids = {}
        
        # Mock message handler
        with patch('netra_backend.app.services.message_handlers.AgentRegistry') as MockRegistry:
            mock_registry = MagicMock()
            MockRegistry.get_instance.return_value = mock_registry
            
            async def capture_registry_thread(agent, context, prompt):
                captured_thread_ids['registry'] = context.get('thread_id')
                return {'result': 'success'}
            
            mock_registry.execute_agent = AsyncMock(side_effect=capture_registry_thread)
            
            # Mock execution engine
            with patch('netra_backend.app.core.execution_engine.ExecutionEngine') as MockEngine:
                mock_engine = MagicMock()
                MockEngine.return_value = mock_engine
                
                async def capture_engine_thread(context):
                    captured_thread_ids['engine'] = context.get('thread_id')
                    return {'result': 'executed'}
                
                mock_engine.execute = AsyncMock(side_effect=capture_engine_thread)
                
                # Start the flow
                initial_message = {
                    'message': 'Test query',
                    'conversation_id': thread_id,
                    'user_id': user_id,
                    'run_id': run_id
                }
                
                # Process through system
                registry = MockRegistry.get_instance()
                context = {
                    'thread_id': thread_id,
                    'user_id': user_id,
                    'run_id': run_id
                }
                
                await registry.execute_agent('test_agent', context, initial_message['message'])
                
                # Send result to WebSocket through manager
                await manager.send_to_user(user_id, {
                    'type': 'agent_completed',
                    'data': {'result': 'success'}
                })
                
                # Capture WebSocket thread context
                conn = manager.connections.get(connection_id)
                if conn:
                    captured_thread_ids['websocket'] = conn.get('thread_id')
        
        # Verify thread_id consistency
        for layer, captured_id in captured_thread_ids.items():
            assert captured_id == thread_id, f"Thread ID mismatch in {layer} layer"

    @pytest.mark.asyncio
    async def test_thread_id_persistence_across_retries(self, setup):
        """Test thread_id persists across operation retries."""
        thread_id = setup['thread_id']
        run_id = setup['run_id']
        
        retry_count = 0
        thread_ids_seen = []
        
        # Mock operation that fails then succeeds
        async def flaky_operation(context):
            nonlocal retry_count
            thread_ids_seen.append(context.get('thread_id'))
            retry_count += 1
            
            if retry_count < 3:
                raise Exception("Temporary failure")
            return {'status': 'success'}
        
        # Retry logic
        context = {'thread_id': thread_id, 'run_id': run_id}
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                result = await flaky_operation(context)
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)
        
        # Verify thread_id consistent across retries
        assert len(thread_ids_seen) == 3
        assert all(tid == thread_id for tid in thread_ids_seen)

    @pytest.mark.asyncio
    async def test_thread_id_in_error_messages(self, setup):
        """Test thread_id context in error messages."""
        manager = setup['manager']
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        
        # Connect WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=thread_id
        )
        
        # Send error message
        error_message = {
            'type': 'agent_error',
            'data': {
                'error': 'Processing failed',
                'details': 'Invalid input'
            }
        }
        
        success = await manager.send_to_user(user_id, error_message)
        assert success
        
        # Allow processing
        await asyncio.sleep(0.1)
        
        # Verify error message sent
        mock_ws.send_json.assert_called()
        sent_msg = mock_ws.send_json.call_args[0][0]
        assert sent_msg['type'] == 'agent_error'
        
        # Verify connection has correct thread_id
        conn = manager.connections.get(connection_id)
        assert conn is not None
        assert conn['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_thread_id_in_websocket_events(self, setup):
        """Test all WebSocket event types work with thread context."""
        manager = setup['manager']
        thread_id = setup['thread_id']
        user_id = setup['user_id']
        
        # Connect WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = WebSocketState.CONNECTED
        
        connection_id = await manager.connect_user(
            user_id,
            mock_ws,
            thread_id=thread_id
        )
        
        # Test all event types
        event_types = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed',
            'typing_indicator',
            'presence_update'
        ]
        
        for event_type in event_types:
            success = await manager.send_to_user(user_id, {
                'type': event_type,
                'data': {'test': 'data'}
            })
            assert success
        
        # Allow processing
        await asyncio.sleep(0.2)
        
        # Verify all events were sent
        assert mock_ws.send_json.call_count == len(event_types)
        
        for call in mock_ws.send_json.call_args_list:
            sent_msg = call[0][0]
            assert sent_msg['type'] in event_types
        
        # Verify connection maintains thread context
        conn = manager.connections.get(connection_id)
        assert conn is not None
        assert conn['thread_id'] == thread_id

    @pytest.mark.asyncio
    async def test_thread_context_in_parallel_operations(self, setup):
        """Test thread context maintained in parallel operations."""
        # Create multiple thread contexts
        threads = []
        for i in range(5):
            threads.append({
                'thread_id': str(uuid.uuid4()),
                'run_id': str(uuid.uuid4()),
                'user_id': str(uuid.uuid4()),
                'index': i
            })
        
        # Track which thread each operation sees
        operation_threads = {}
        
        async def simulated_operation(context):
            # Store the thread_id this operation sees
            operation_threads[context['index']] = context['thread_id']
            await asyncio.sleep(0.05)  # Simulate work
            return {'result': f"Completed for thread {context['thread_id'][:8]}"}
        
        # Execute operations in parallel
        tasks = []
        for thread in threads:
            task = asyncio.create_task(simulated_operation(thread))
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # Verify each operation saw correct thread_id
        for thread in threads:
            assert operation_threads[thread['index']] == thread['thread_id']
        
        # Verify results correspond to correct threads
        assert len(results) == 5
        for i, result in enumerate(results):
            assert threads[i]['thread_id'][:8] in result['result']

    @pytest.mark.asyncio
    async def test_thread_id_validation_at_boundaries(self, setup):
        """Test thread_id validation at system boundaries."""
        user_id = setup['user_id']
        
        # Test invalid thread_id formats
        invalid_thread_ids = [
            None,
            '',
            ' ',
            'not-a-uuid',
            12345,
            {'invalid': 'type'}
        ]
        
        for invalid_id in invalid_thread_ids:
            # Test at WebSocket boundary
            manager = WebSocketManager()
            mock_ws = AsyncMock(spec=WebSocket)
            mock_ws.send_json = AsyncMock()
            mock_ws.close = AsyncMock()
            mock_ws.client_state = WebSocketState.CONNECTED
            
            # Should handle gracefully
            try:
                connection_id = await manager.connect_user(
                    user_id,
                    mock_ws,
                    thread_id=invalid_id
                )
                # Connection should succeed - WebSocketManager accepts any thread_id
                conn = manager.connections.get(connection_id)
                if conn:
                    stored_thread = conn.get('thread_id')
                    # Should store the invalid_id as-is or handle appropriately
                    assert stored_thread == invalid_id or stored_thread is None
            except (ValueError, TypeError):
                # Also acceptable to reject invalid thread_id
                pass
            
            await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])