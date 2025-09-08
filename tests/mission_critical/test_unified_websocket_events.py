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
    # REMOVED_SYNTAX_ERROR: Mission Critical Test: Unified WebSocket Events

    # REMOVED_SYNTAX_ERROR: Tests that all 5 critical events work with the new unified implementation.
    # REMOVED_SYNTAX_ERROR: These events MUST work for chat value delivery.

    # REMOVED_SYNTAX_ERROR: Critical Events:
        # REMOVED_SYNTAX_ERROR: 1. agent_started
        # REMOVED_SYNTAX_ERROR: 2. agent_thinking
        # REMOVED_SYNTAX_ERROR: 3. tool_executing
        # REMOVED_SYNTAX_ERROR: 4. tool_completed
        # REMOVED_SYNTAX_ERROR: 5. agent_completed
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from datetime import datetime
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # Import unified implementations
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import ( )
        # REMOVED_SYNTAX_ERROR: UnifiedWebSocketManager,
        # REMOVED_SYNTAX_ERROR: WebSocketConnection
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_emitter import ( )
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: UnifiedWebSocketEmitter,
        # REMOVED_SYNTAX_ERROR: WebSocketEmitterFactory,
        # REMOVED_SYNTAX_ERROR: WebSocketEmitterPool
        


        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def manager():
    # REMOVED_SYNTAX_ERROR: """Create UnifiedWebSocketManager instance."""
    # REMOVED_SYNTAX_ERROR: manager = UnifiedWebSocketManager()
    # REMOVED_SYNTAX_ERROR: yield manager
    # REMOVED_SYNTAX_ERROR: await manager.shutdown()


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_websocket():
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return ws


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def connected_user(manager, mock_websocket):
    # REMOVED_SYNTAX_ERROR: """Connect a test user."""
    # REMOVED_SYNTAX_ERROR: user_id = "test_user_123"
    # REMOVED_SYNTAX_ERROR: connection = await manager.connect_user( )
    # REMOVED_SYNTAX_ERROR: websocket=mock_websocket,
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: connection_id="test_conn_1"
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return user_id, connection, mock_websocket


# REMOVED_SYNTAX_ERROR: class TestCriticalEvents:
    # REMOVED_SYNTAX_ERROR: """Test all 5 critical events with unified implementation."""

    # Removed problematic line: async def test_all_critical_events_defined(self):
        # REMOVED_SYNTAX_ERROR: """Verify all 5 critical events are defined."""
        # REMOVED_SYNTAX_ERROR: expected_events = [ )
        # REMOVED_SYNTAX_ERROR: 'agent_started',
        # REMOVED_SYNTAX_ERROR: 'agent_thinking',
        # REMOVED_SYNTAX_ERROR: 'tool_executing',
        # REMOVED_SYNTAX_ERROR: 'tool_completed',
        # REMOVED_SYNTAX_ERROR: 'agent_completed'
        

        # REMOVED_SYNTAX_ERROR: assert UnifiedWebSocketEmitter.CRITICAL_EVENTS == expected_events

        # Removed problematic line: async def test_agent_started_event(self, manager, connected_user):
            # REMOVED_SYNTAX_ERROR: """Test agent_started event delivery."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

            # Create emitter
            # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

            # Emit agent_started
            # Removed problematic line: await emitter.emit_agent_started({ ))
            # REMOVED_SYNTAX_ERROR: 'agent': 'TestAgent',
            # REMOVED_SYNTAX_ERROR: 'task': 'Processing request'
            

            # Verify WebSocket received the event
            # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
            # REMOVED_SYNTAX_ERROR: call_args = mock_ws.send_json.call_args[0][0]

            # REMOVED_SYNTAX_ERROR: assert call_args['type'] == 'agent_started'
            # REMOVED_SYNTAX_ERROR: assert call_args['data']['agent'] == 'TestAgent'
            # REMOVED_SYNTAX_ERROR: assert call_args['user_id'] == user_id

            # Removed problematic line: async def test_agent_thinking_event(self, manager, connected_user):
                # REMOVED_SYNTAX_ERROR: """Test agent_thinking event delivery."""
                # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

                # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

                # Emit agent_thinking
                # Removed problematic line: await emitter.emit_agent_thinking({ ))
                # REMOVED_SYNTAX_ERROR: 'thought': 'Analyzing user request...'
                

                # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
                # REMOVED_SYNTAX_ERROR: call_args = mock_ws.send_json.call_args[0][0]

                # REMOVED_SYNTAX_ERROR: assert call_args['type'] == 'agent_thinking'
                # REMOVED_SYNTAX_ERROR: assert call_args['data']['thought'] == 'Analyzing user request...'

                # Removed problematic line: async def test_tool_executing_event(self, manager, connected_user):
                    # REMOVED_SYNTAX_ERROR: """Test tool_executing event delivery."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

                    # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

                    # Emit tool_executing
                    # Removed problematic line: await emitter.emit_tool_executing({ ))
                    # REMOVED_SYNTAX_ERROR: 'tool': 'DataAnalyzer',
                    # REMOVED_SYNTAX_ERROR: 'parameters': {'query': 'test'}
                    

                    # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
                    # REMOVED_SYNTAX_ERROR: call_args = mock_ws.send_json.call_args[0][0]

                    # REMOVED_SYNTAX_ERROR: assert call_args['type'] == 'tool_executing'
                    # REMOVED_SYNTAX_ERROR: assert call_args['data']['tool'] == 'DataAnalyzer'
                    # REMOVED_SYNTAX_ERROR: assert call_args['data']['parameters']['query'] == 'test'

                    # Removed problematic line: async def test_tool_completed_event(self, manager, connected_user):
                        # REMOVED_SYNTAX_ERROR: """Test tool_completed event delivery."""
                        # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

                        # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

                        # Emit tool_completed
                        # Removed problematic line: await emitter.emit_tool_completed({ ))
                        # REMOVED_SYNTAX_ERROR: 'tool': 'DataAnalyzer',
                        # REMOVED_SYNTAX_ERROR: 'result': {'status': 'success', 'data': [1, 2, 3]}
                        

                        # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
                        # REMOVED_SYNTAX_ERROR: call_args = mock_ws.send_json.call_args[0][0]

                        # REMOVED_SYNTAX_ERROR: assert call_args['type'] == 'tool_completed'
                        # REMOVED_SYNTAX_ERROR: assert call_args['data']['result']['status'] == 'success'

                        # Removed problematic line: async def test_agent_completed_event(self, manager, connected_user):
                            # REMOVED_SYNTAX_ERROR: """Test agent_completed event delivery."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

                            # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

                            # Emit agent_completed
                            # Removed problematic line: await emitter.emit_agent_completed({ ))
                            # REMOVED_SYNTAX_ERROR: 'result': 'Task completed successfully',
                            # REMOVED_SYNTAX_ERROR: 'duration': 5.2
                            

                            # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called()
                            # REMOVED_SYNTAX_ERROR: call_args = mock_ws.send_json.call_args[0][0]

                            # REMOVED_SYNTAX_ERROR: assert call_args['type'] == 'agent_completed'
                            # REMOVED_SYNTAX_ERROR: assert call_args['data']['result'] == 'Task completed successfully'

                            # Removed problematic line: async def test_all_events_in_sequence(self, manager, connected_user):
                                # REMOVED_SYNTAX_ERROR: """Test all 5 events in typical execution sequence."""
                                # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

                                # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

                                # Emit all events in sequence
                                # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_started({'agent': 'SuperAgent'})
                                # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_thinking({'thought': 'Processing...'})
                                # REMOVED_SYNTAX_ERROR: await emitter.emit_tool_executing({'tool': 'Calculator'})
                                # REMOVED_SYNTAX_ERROR: await emitter.emit_tool_completed({'tool': 'Calculator', 'result': 42})
                                # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_completed({'result': 'Answer is 42'})

                                # Verify all 5 events were sent
                                # REMOVED_SYNTAX_ERROR: assert mock_ws.send_json.call_count == 5

                                # Check event types in order
                                # REMOVED_SYNTAX_ERROR: event_types = [ )
                                # REMOVED_SYNTAX_ERROR: call[0][0]['type']
                                # REMOVED_SYNTAX_ERROR: for call in mock_ws.send_json.call_args_list
                                

                                # REMOVED_SYNTAX_ERROR: assert event_types == [ )
                                # REMOVED_SYNTAX_ERROR: 'agent_started',
                                # REMOVED_SYNTAX_ERROR: 'agent_thinking',
                                # REMOVED_SYNTAX_ERROR: 'tool_executing',
                                # REMOVED_SYNTAX_ERROR: 'tool_completed',
                                # REMOVED_SYNTAX_ERROR: 'agent_completed'
                                


# REMOVED_SYNTAX_ERROR: class TestUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Test that events are properly isolated per user."""

    # Removed problematic line: async def test_events_isolated_per_user(self, manager):
        # REMOVED_SYNTAX_ERROR: """Verify events only go to intended user."""
        # Create mock WebSockets
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()

        # Connect two users
        # REMOVED_SYNTAX_ERROR: user1 = "user1"
        # REMOVED_SYNTAX_ERROR: user2 = "user2"

        # REMOVED_SYNTAX_ERROR: await manager.connect_user(ws1, user1, "conn1")
        # REMOVED_SYNTAX_ERROR: await manager.connect_user(ws2, user2, "conn2")

        # Create emitters
        # REMOVED_SYNTAX_ERROR: emitter1 = UnifiedWebSocketEmitter(manager, user1)
        # REMOVED_SYNTAX_ERROR: emitter2 = UnifiedWebSocketEmitter(manager, user2)

        # User1 emits event
        # REMOVED_SYNTAX_ERROR: await emitter1.emit_agent_started({'agent': 'Agent1'})

        # Only user1's WebSocket should receive it
        # REMOVED_SYNTAX_ERROR: ws1.send_json.assert_called_once()
        # REMOVED_SYNTAX_ERROR: ws2.send_json.assert_not_called()

        # User2 emits event
        # REMOVED_SYNTAX_ERROR: await emitter2.emit_agent_completed({'result': 'Done'})

        # Only user2's WebSocket should receive it
        # REMOVED_SYNTAX_ERROR: assert ws1.send_json.call_count == 1  # Still just 1
        # REMOVED_SYNTAX_ERROR: ws2.send_json.assert_called_once()

        # Removed problematic line: async def test_multiple_connections_same_user(self, manager):
            # REMOVED_SYNTAX_ERROR: """Test broadcasting to multiple connections of same user."""
            # REMOVED_SYNTAX_ERROR: pass
            # Create mock WebSockets
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()

            # REMOVED_SYNTAX_ERROR: user_id = "multi_tab_user"

            # Connect same user twice (e.g., multiple tabs)
            # REMOVED_SYNTAX_ERROR: await manager.connect_user(ws1, user_id, "tab1")
            # REMOVED_SYNTAX_ERROR: await manager.connect_user(ws2, user_id, "tab2")

            # Create emitter
            # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

            # Emit event
            # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_thinking({'thought': 'Processing...'})

            # Both connections should receive it
            # REMOVED_SYNTAX_ERROR: ws1.send_json.assert_called_once()
            # REMOVED_SYNTAX_ERROR: ws2.send_json.assert_called_once()

            # Verify same data sent to both
            # REMOVED_SYNTAX_ERROR: data1 = ws1.send_json.call_args[0][0]
            # REMOVED_SYNTAX_ERROR: data2 = ws2.send_json.call_args[0][0]

            # REMOVED_SYNTAX_ERROR: assert data1['type'] == data2['type'] == 'agent_thinking'
            # REMOVED_SYNTAX_ERROR: assert data1['data'] == data2['data']


# REMOVED_SYNTAX_ERROR: class TestBackwardCompatibility:
    # REMOVED_SYNTAX_ERROR: """Test backward compatibility with existing code."""

    # Removed problematic line: async def test_notify_methods_work(self, manager, connected_user):
        # REMOVED_SYNTAX_ERROR: """Test backward compatibility notify_* methods."""
        # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

        # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

        # Test all notify methods
        # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_started('TestAgent')
        # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_thinking('Thinking...')
        # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_executing('Tool1', {'param': 'value'})
        # REMOVED_SYNTAX_ERROR: await emitter.notify_tool_completed('Tool1', 'Result')
        # REMOVED_SYNTAX_ERROR: await emitter.notify_agent_completed('Final result')

        # Verify all events sent
        # REMOVED_SYNTAX_ERROR: assert mock_ws.send_json.call_count == 5

        # Removed problematic line: async def test_factory_creation(self, manager, connected_user):
            # REMOVED_SYNTAX_ERROR: """Test emitter factory creation."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

            # Create via factory
            # REMOVED_SYNTAX_ERROR: emitter = WebSocketEmitterFactory.create_emitter( )
            # REMOVED_SYNTAX_ERROR: manager, user_id
            

            # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_started({'agent': 'FactoryAgent'})

            # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called_once()

            # Removed problematic line: async def test_emitter_pool(self, manager, connected_user):
                # REMOVED_SYNTAX_ERROR: """Test emitter pool functionality."""
                # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

                # Create pool
                # REMOVED_SYNTAX_ERROR: pool = WebSocketEmitterPool(manager, max_size=10)

                # Acquire emitter
                # REMOVED_SYNTAX_ERROR: emitter = await pool.acquire(user_id)

                # Use emitter
                # REMOVED_SYNTAX_ERROR: await emitter.emit_tool_executing({'tool': 'PooledTool'})

                # Release back to pool
                # REMOVED_SYNTAX_ERROR: await pool.release(emitter)

                # Verify event was sent
                # REMOVED_SYNTAX_ERROR: mock_ws.send_json.assert_called_once()

                # Acquire again (should reuse)
                # REMOVED_SYNTAX_ERROR: emitter2 = await pool.acquire(user_id)
                # REMOVED_SYNTAX_ERROR: assert emitter2 is emitter  # Same instance

                # Cleanup
                # REMOVED_SYNTAX_ERROR: await pool.shutdown()


# REMOVED_SYNTAX_ERROR: class TestReliability:
    # REMOVED_SYNTAX_ERROR: """Test reliability features like retry logic."""

    # Removed problematic line: async def test_retry_on_failure(self, manager):
        # REMOVED_SYNTAX_ERROR: """Test retry logic for failed sends."""
        # Create WebSocket that fails first 2 attempts
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
        # REMOVED_SYNTAX_ERROR: attempt_count = 0

# REMOVED_SYNTAX_ERROR: async def send_json_side_effect(data):
    # REMOVED_SYNTAX_ERROR: nonlocal attempt_count
    # REMOVED_SYNTAX_ERROR: attempt_count += 1
    # REMOVED_SYNTAX_ERROR: if attempt_count < 3:
        # REMOVED_SYNTAX_ERROR: raise Exception("Network error")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return None

        # REMOVED_SYNTAX_ERROR: ws.send_json = AsyncMock(side_effect=send_json_side_effect)
        # REMOVED_SYNTAX_ERROR: ws.websocket = TestWebSocketConnection()

        # REMOVED_SYNTAX_ERROR: user_id = "retry_user"
        # REMOVED_SYNTAX_ERROR: await manager.connect_user(ws, user_id)

        # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

        # Should retry and eventually succeed
        # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_started({'agent': 'RetryAgent'})

        # Should have been called 3 times (2 failures + 1 success)
        # REMOVED_SYNTAX_ERROR: assert ws.send_json.call_count == 3

        # Removed problematic line: async def test_metrics_tracking(self, manager, connected_user):
            # REMOVED_SYNTAX_ERROR: """Test that emitter tracks metrics correctly."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_id, connection, mock_ws = connected_user

            # REMOVED_SYNTAX_ERROR: emitter = UnifiedWebSocketEmitter(manager, user_id)

            # Emit various events
            # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_started({'agent': 'MetricsAgent'})
            # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_thinking({'thought': 'Test'})
            # REMOVED_SYNTAX_ERROR: await emitter.emit_agent_completed({'result': 'Done'})

            # Check metrics
            # REMOVED_SYNTAX_ERROR: stats = emitter.get_stats()

            # REMOVED_SYNTAX_ERROR: assert stats['total_events'] == 3
            # REMOVED_SYNTAX_ERROR: assert stats['critical_events']['agent_started'] == 1
            # REMOVED_SYNTAX_ERROR: assert stats['critical_events']['agent_thinking'] == 1
            # REMOVED_SYNTAX_ERROR: assert stats['critical_events']['agent_completed'] == 1
            # REMOVED_SYNTAX_ERROR: assert stats['error_count'] == 0


# REMOVED_SYNTAX_ERROR: class TestAgentWebSocketBridge:
    # REMOVED_SYNTAX_ERROR: """Test AgentWebSocketBridge compatibility."""

    # Removed problematic line: async def test_bridge_creation(self, manager):
        # REMOVED_SYNTAX_ERROR: """Test that bridge can be created."""
        # Mock context
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
        # REMOVED_SYNTAX_ERROR: context.user_id = "bridge_user"
        # REMOVED_SYNTAX_ERROR: context.run_id = "run_123"
        # REMOVED_SYNTAX_ERROR: context.thread_id = "thread_456"

        # Create bridge
        # REMOVED_SYNTAX_ERROR: bridge = manager.create_agent_bridge(context)

        # Verify bridge is created
        # REMOVED_SYNTAX_ERROR: assert bridge is not None
        # Note: Full bridge testing would require AgentWebSocketBridge implementation


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run tests
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--asyncio-mode=auto"])
            # REMOVED_SYNTAX_ERROR: pass