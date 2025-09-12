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
    # REMOVED_SYNTAX_ERROR: Tests for execution isolation with UserExecutionEngine and ExecutionEngineFactory.

    # REMOVED_SYNTAX_ERROR: This test suite verifies that user execution isolation works correctly and prevents
    # REMOVED_SYNTAX_ERROR: state leakage between concurrent users.

    # REMOVED_SYNTAX_ERROR: Business Value: Ensures production-ready concurrent user support with zero context leakage.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_context import ( )
    # REMOVED_SYNTAX_ERROR: AgentExecutionContext,
    # REMOVED_SYNTAX_ERROR: AgentExecutionResult)
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import ( )
    # REMOVED_SYNTAX_ERROR: UserExecutionContext,
    # REMOVED_SYNTAX_ERROR: InvalidContextError
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_engine_factory import ( )
    # REMOVED_SYNTAX_ERROR: ExecutionEngineFactory,
    # REMOVED_SYNTAX_ERROR: get_execution_engine_factory,
    # REMOVED_SYNTAX_ERROR: user_execution_engine
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.execution_state_store import ( )
    # REMOVED_SYNTAX_ERROR: ExecutionStateStore,
    # REMOVED_SYNTAX_ERROR: get_execution_state_store
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_instance_factory import ( )
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
    # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter,
    # REMOVED_SYNTAX_ERROR: get_agent_instance_factory
    


# REMOVED_SYNTAX_ERROR: class TestUserExecutionEngine:
    # REMOVED_SYNTAX_ERROR: """Test UserExecutionEngine for per-user isolation."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="test_user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: request_id="req_101112"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def different_user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create different user execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="different_user_456",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_789",
    # REMOVED_SYNTAX_ERROR: run_id="run_101112",
    # REMOVED_SYNTAX_ERROR: request_id="req_131415"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_agent_factory():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Mock agent factory with required components."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: return factory

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_emitter():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Mock UserWebSocketEmitter."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_started = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_thinking = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.notify_agent_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: emitter.websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: return emitter

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def agent_execution_context(self, user_context):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create agent execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return AgentExecutionContext( )
    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
    # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def deep_agent_state(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create deep agent state."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: state = Mock(spec=DeepAgentState)
    # REMOVED_SYNTAX_ERROR: state.user_prompt = "Test prompt"
    # REMOVED_SYNTAX_ERROR: return state

# REMOVED_SYNTAX_ERROR: def test_user_execution_engine_creation(self, user_context, mock_agent_factory, mock_websocket_emitter):
    # REMOVED_SYNTAX_ERROR: """Test UserExecutionEngine creation with proper initialization."""
    # Create engine
    # REMOVED_SYNTAX_ERROR: engine = UserExecutionEngine( )
    # REMOVED_SYNTAX_ERROR: context=user_context,
    # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
    # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
    

    # Verify initialization
    # REMOVED_SYNTAX_ERROR: assert engine.context == user_context
    # REMOVED_SYNTAX_ERROR: assert engine.agent_factory == mock_agent_factory
    # REMOVED_SYNTAX_ERROR: assert engine.websocket_emitter == mock_websocket_emitter
    # REMOVED_SYNTAX_ERROR: assert engine.is_active()
    # REMOVED_SYNTAX_ERROR: assert len(engine.active_runs) == 0
    # REMOVED_SYNTAX_ERROR: assert len(engine.run_history) == 0
    # REMOVED_SYNTAX_ERROR: assert engine.max_concurrent == 3  # default

    # Verify engine metadata
    # REMOVED_SYNTAX_ERROR: assert engine.engine_id.startswith("user_engine_")
    # REMOVED_SYNTAX_ERROR: assert user_context.user_id in engine.engine_id
    # REMOVED_SYNTAX_ERROR: assert user_context.run_id in engine.engine_id

# REMOVED_SYNTAX_ERROR: def test_user_execution_engine_context_validation(self, mock_agent_factory, mock_websocket_emitter):
    # REMOVED_SYNTAX_ERROR: """Test context validation during engine creation."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test invalid context (None)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(TypeError):
        # REMOVED_SYNTAX_ERROR: UserExecutionEngine( )
        # REMOVED_SYNTAX_ERROR: context=None,
        # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
        # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
        

        # Test invalid context (wrong type)
        # REMOVED_SYNTAX_ERROR: with pytest.raises(TypeError):
            # REMOVED_SYNTAX_ERROR: UserExecutionEngine( )
            # REMOVED_SYNTAX_ERROR: context="not_a_context",
            # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
            # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
            

            # Test missing agent factory
            # REMOVED_SYNTAX_ERROR: valid_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="test", thread_id="thread", run_id="run"
            
            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError):
                # REMOVED_SYNTAX_ERROR: UserExecutionEngine( )
                # REMOVED_SYNTAX_ERROR: context=valid_context,
                # REMOVED_SYNTAX_ERROR: agent_factory=None,
                # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
                

                # Removed problematic line: async def test_execution_context_validation(self, user_context, mock_agent_factory, mock_websocket_emitter):
                    # REMOVED_SYNTAX_ERROR: """Test execution context validation against user context."""
                    # REMOVED_SYNTAX_ERROR: engine = UserExecutionEngine( )
                    # REMOVED_SYNTAX_ERROR: context=user_context,
                    # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                    # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
                    

                    # Valid context (matches user)
                    # REMOVED_SYNTAX_ERROR: valid_agent_context = AgentExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
                    # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id
                    

                    # This should not raise
                    # REMOVED_SYNTAX_ERROR: engine._validate_execution_context(valid_agent_context)

                    # Invalid context (different user)
                    # REMOVED_SYNTAX_ERROR: invalid_agent_context = AgentExecutionContext( )
                    # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
                    # REMOVED_SYNTAX_ERROR: user_id="different_user",
                    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id
                    

                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="User ID mismatch"):
                        # REMOVED_SYNTAX_ERROR: engine._validate_execution_context(invalid_agent_context)

                        # Removed problematic line: async def test_user_isolation_stats(self, user_context, different_user_context,
                        # REMOVED_SYNTAX_ERROR: mock_agent_factory, mock_websocket_emitter):
                            # REMOVED_SYNTAX_ERROR: """Test that execution stats are isolated per user."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # Create engines for different users
                            # REMOVED_SYNTAX_ERROR: engine1 = UserExecutionEngine( )
                            # REMOVED_SYNTAX_ERROR: context=user_context,
                            # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                            # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
                            

                            # REMOVED_SYNTAX_ERROR: engine2 = UserExecutionEngine( )
                            # REMOVED_SYNTAX_ERROR: context=different_user_context,
                            # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                            # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
                            

                            # Modify stats for engine1
                            # REMOVED_SYNTAX_ERROR: engine1.execution_stats['total_executions'] = 5
                            # REMOVED_SYNTAX_ERROR: engine1.execution_stats['successful_executions'] = 4
                            # REMOVED_SYNTAX_ERROR: engine1.execution_stats['execution_times'] = [1.0, 2.0, 3.0, 4.0, 5.0]

                            # Modify stats for engine2 (different values)
                            # REMOVED_SYNTAX_ERROR: engine2.execution_stats['total_executions'] = 10
                            # REMOVED_SYNTAX_ERROR: engine2.execution_stats['successful_executions'] = 8
                            # REMOVED_SYNTAX_ERROR: engine2.execution_stats['execution_times'] = [0.5, 1.5, 2.5]

                            # Get stats for each user
                            # REMOVED_SYNTAX_ERROR: stats1 = engine1.get_user_execution_stats()
                            # REMOVED_SYNTAX_ERROR: stats2 = engine2.get_user_execution_stats()

                            # Verify isolation - stats should be different
                            # REMOVED_SYNTAX_ERROR: assert stats1['total_executions'] == 5
                            # REMOVED_SYNTAX_ERROR: assert stats1['user_id'] == user_context.user_id
                            # REMOVED_SYNTAX_ERROR: assert stats1['avg_execution_time'] == 3.0  # (1+2+3+4+5)/5

                            # REMOVED_SYNTAX_ERROR: assert stats2['total_executions'] == 10
                            # REMOVED_SYNTAX_ERROR: assert stats2['user_id'] == different_user_context.user_id
                            # REMOVED_SYNTAX_ERROR: assert stats2['avg_execution_time'] == pytest.approx(1.5)  # (0.5+1.5+2.5)/3

                            # Verify complete isolation
                            # REMOVED_SYNTAX_ERROR: assert stats1['user_id'] != stats2['user_id']
                            # REMOVED_SYNTAX_ERROR: assert stats1['engine_id'] != stats2['engine_id']
                            # REMOVED_SYNTAX_ERROR: assert stats1['run_id'] != stats2['run_id']

                            # Removed problematic line: async def test_active_runs_isolation(self, user_context, different_user_context,
                            # REMOVED_SYNTAX_ERROR: mock_agent_factory, mock_websocket_emitter):
                                # REMOVED_SYNTAX_ERROR: """Test that active runs are isolated per user."""
                                # Create engines for different users
                                # REMOVED_SYNTAX_ERROR: engine1 = UserExecutionEngine( )
                                # REMOVED_SYNTAX_ERROR: context=user_context,
                                # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                                # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
                                

                                # REMOVED_SYNTAX_ERROR: engine2 = UserExecutionEngine( )
                                # REMOVED_SYNTAX_ERROR: context=different_user_context,
                                # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                                # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
                                

                                # Add active runs to each engine
                                # REMOVED_SYNTAX_ERROR: execution_id_1 = "exec_1"
                                # REMOVED_SYNTAX_ERROR: execution_id_2 = "exec_2"

                                # REMOVED_SYNTAX_ERROR: context_1 = AgentExecutionContext( )
                                # REMOVED_SYNTAX_ERROR: agent_name="agent1",
                                # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                                # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                                # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id
                                

                                # REMOVED_SYNTAX_ERROR: context_2 = AgentExecutionContext( )
                                # REMOVED_SYNTAX_ERROR: agent_name="agent2",
                                # REMOVED_SYNTAX_ERROR: user_id=different_user_context.user_id,
                                # REMOVED_SYNTAX_ERROR: thread_id=different_user_context.thread_id,
                                # REMOVED_SYNTAX_ERROR: run_id=different_user_context.run_id
                                

                                # REMOVED_SYNTAX_ERROR: engine1.active_runs[execution_id_1] = context_1
                                # REMOVED_SYNTAX_ERROR: engine2.active_runs[execution_id_2] = context_2

                                # Verify isolation
                                # REMOVED_SYNTAX_ERROR: assert len(engine1.active_runs) == 1
                                # REMOVED_SYNTAX_ERROR: assert len(engine2.active_runs) == 1
                                # REMOVED_SYNTAX_ERROR: assert execution_id_1 in engine1.active_runs
                                # REMOVED_SYNTAX_ERROR: assert execution_id_2 in engine2.active_runs
                                # REMOVED_SYNTAX_ERROR: assert execution_id_1 not in engine2.active_runs
                                # REMOVED_SYNTAX_ERROR: assert execution_id_2 not in engine1.active_runs

                                # Verify contexts match users
                                # REMOVED_SYNTAX_ERROR: assert engine1.active_runs[execution_id_1].user_id == user_context.user_id
                                # REMOVED_SYNTAX_ERROR: assert engine2.active_runs[execution_id_2].user_id == different_user_context.user_id

                                # Removed problematic line: async def test_websocket_emitter_isolation(self, user_context, different_user_context,
                                # REMOVED_SYNTAX_ERROR: mock_agent_factory):
                                    # REMOVED_SYNTAX_ERROR: """Test that WebSocket emitters are isolated per user."""
                                    # Create separate emitters for each user
                                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
                                    # REMOVED_SYNTAX_ERROR: emitter1.notify_agent_started = AsyncMock(return_value=True)
                                    # REMOVED_SYNTAX_ERROR: emitter1.websocket = TestWebSocketConnection()

                                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
                                    # REMOVED_SYNTAX_ERROR: emitter2.notify_agent_started = AsyncMock(return_value=True)
                                    # REMOVED_SYNTAX_ERROR: emitter2.websocket = TestWebSocketConnection()

                                    # Create engines with different emitters
                                    # REMOVED_SYNTAX_ERROR: engine1 = UserExecutionEngine( )
                                    # REMOVED_SYNTAX_ERROR: context=user_context,
                                    # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                                    # REMOVED_SYNTAX_ERROR: websocket_emitter=emitter1
                                    

                                    # REMOVED_SYNTAX_ERROR: engine2 = UserExecutionEngine( )
                                    # REMOVED_SYNTAX_ERROR: context=different_user_context,
                                    # REMOVED_SYNTAX_ERROR: agent_factory=mock_agent_factory,
                                    # REMOVED_SYNTAX_ERROR: websocket_emitter=emitter2
                                    

                                    # Verify different emitters
                                    # REMOVED_SYNTAX_ERROR: assert engine1.websocket_emitter != engine2.websocket_emitter
                                    # REMOVED_SYNTAX_ERROR: assert engine1.websocket_emitter == emitter1
                                    # REMOVED_SYNTAX_ERROR: assert engine2.websocket_emitter == emitter2

                                    # Test sending notifications
                                    # REMOVED_SYNTAX_ERROR: context1 = AgentExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: agent_name="agent1",
                                    # REMOVED_SYNTAX_ERROR: user_id=user_context.user_id,
                                    # REMOVED_SYNTAX_ERROR: thread_id=user_context.thread_id,
                                    # REMOVED_SYNTAX_ERROR: run_id=user_context.run_id
                                    

                                    # REMOVED_SYNTAX_ERROR: context2 = AgentExecutionContext( )
                                    # REMOVED_SYNTAX_ERROR: agent_name="agent2",
                                    # REMOVED_SYNTAX_ERROR: user_id=different_user_context.user_id,
                                    # REMOVED_SYNTAX_ERROR: thread_id=different_user_context.thread_id,
                                    # REMOVED_SYNTAX_ERROR: run_id=different_user_context.run_id
                                    

                                    # REMOVED_SYNTAX_ERROR: await engine1._send_user_agent_started(context1)
                                    # REMOVED_SYNTAX_ERROR: await engine2._send_user_agent_started(context2)

                                    # Verify each emitter was called for its respective user only
                                    # REMOVED_SYNTAX_ERROR: emitter1.notify_agent_started.assert_called_once()
                                    # REMOVED_SYNTAX_ERROR: emitter2.notify_agent_started.assert_called_once()

                                    # Verify call arguments include correct user info
                                    # REMOVED_SYNTAX_ERROR: call_args_1 = emitter1.notify_agent_started.call_args
                                    # REMOVED_SYNTAX_ERROR: call_args_2 = emitter2.notify_agent_started.call_args

                                    # REMOVED_SYNTAX_ERROR: assert call_args_1[1]['context']['user_id'] == user_context.user_id
                                    # REMOVED_SYNTAX_ERROR: assert call_args_2[1]['context']['user_id'] == different_user_context.user_id


# REMOVED_SYNTAX_ERROR: class TestExecutionEngineFactory:
    # REMOVED_SYNTAX_ERROR: """Test ExecutionEngineFactory for managing user engines."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="factory_test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="factory_thread",
    # REMOVED_SYNTAX_ERROR: run_id="factory_run",
    # REMOVED_SYNTAX_ERROR: request_id="factory_req"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def factory(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create execution engine factory."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return ExecutionEngineFactory()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def configured_agent_factory(self):
    # REMOVED_SYNTAX_ERROR: """Mock configured agent instance factory."""
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Mock the global factory
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
    # REMOVED_SYNTAX_ERROR: original_get_factory = factory_module.get_agent_instance_factory
    # REMOVED_SYNTAX_ERROR: factory_module.get_agent_instance_factory = Mock(return_value=factory)

    # REMOVED_SYNTAX_ERROR: yield factory

    # Restore original
    # REMOVED_SYNTAX_ERROR: factory_module.get_agent_instance_factory = original_get_factory

    # Removed problematic line: async def test_factory_create_for_user(self, factory, user_context, configured_agent_factory):
        # REMOVED_SYNTAX_ERROR: """Test factory creates isolated engines for users."""
        # REMOVED_SYNTAX_ERROR: pass
        # Create engine for user
        # REMOVED_SYNTAX_ERROR: engine = await factory.create_for_user(user_context)

        # Verify engine creation
        # REMOVED_SYNTAX_ERROR: assert isinstance(engine, UserExecutionEngine)
        # REMOVED_SYNTAX_ERROR: assert engine.is_active()
        # REMOVED_SYNTAX_ERROR: assert engine.get_user_context() == user_context

        # Verify factory tracking
        # REMOVED_SYNTAX_ERROR: assert len(factory._active_engines) == 1
        # REMOVED_SYNTAX_ERROR: assert factory._factory_metrics['total_engines_created'] == 1
        # REMOVED_SYNTAX_ERROR: assert factory._factory_metrics['active_engines_count'] == 1

        # Removed problematic line: async def test_factory_user_limits(self, factory, configured_agent_factory):
            # REMOVED_SYNTAX_ERROR: """Test factory enforces per-user engine limits."""
            # Set low limit for testing
            # REMOVED_SYNTAX_ERROR: factory._max_engines_per_user = 2

            # REMOVED_SYNTAX_ERROR: user_id = "limited_user"

            # Create contexts for same user
            # REMOVED_SYNTAX_ERROR: contexts = [ )
            # REMOVED_SYNTAX_ERROR: UserExecutionContext(user_id=user_id, thread_id="formatted_string", run_id="formatted_string")
            # REMOVED_SYNTAX_ERROR: for i in range(3)
            

            # First two should succeed
            # REMOVED_SYNTAX_ERROR: engine1 = await factory.create_for_user(contexts[0])
            # REMOVED_SYNTAX_ERROR: engine2 = await factory.create_for_user(contexts[1])

            # REMOVED_SYNTAX_ERROR: assert len(factory._active_engines) == 2

            # Third should fail (exceeds limit)
            # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception, match="reached maximum engine limit"):
                # REMOVED_SYNTAX_ERROR: await factory.create_for_user(contexts[2])

                # Removed problematic line: async def test_factory_user_execution_scope(self, factory, user_context, configured_agent_factory):
                    # REMOVED_SYNTAX_ERROR: """Test factory context manager provides proper isolation."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Track engines created
                    # REMOVED_SYNTAX_ERROR: engines_created = []

                    # REMOVED_SYNTAX_ERROR: async with factory.user_execution_scope(user_context) as engine:
                        # REMOVED_SYNTAX_ERROR: engines_created.append(engine)
                        # REMOVED_SYNTAX_ERROR: assert isinstance(engine, UserExecutionEngine)
                        # REMOVED_SYNTAX_ERROR: assert engine.is_active()
                        # REMOVED_SYNTAX_ERROR: assert engine.get_user_context() == user_context

                        # Verify engine is tracked
                        # REMOVED_SYNTAX_ERROR: assert len(factory._active_engines) == 1

                        # After context exit, engine should be cleaned up
                        # REMOVED_SYNTAX_ERROR: assert not engine.is_active()
                        # REMOVED_SYNTAX_ERROR: assert len(factory._active_engines) == 0
                        # REMOVED_SYNTAX_ERROR: assert factory._factory_metrics['total_engines_cleaned'] == 1

                        # Removed problematic line: async def test_concurrent_user_execution_scopes(self, factory, configured_agent_factory):
                            # REMOVED_SYNTAX_ERROR: """Test concurrent execution scopes for different users."""
                            # Create contexts for different users
                            # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
                            # REMOVED_SYNTAX_ERROR: user_id="concurrent_user_1",
                            # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
                            # REMOVED_SYNTAX_ERROR: run_id="run_1"
                            

                            # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
                            # REMOVED_SYNTAX_ERROR: user_id="concurrent_user_2",
                            # REMOVED_SYNTAX_ERROR: thread_id="thread_2",
                            # REMOVED_SYNTAX_ERROR: run_id="run_2"
                            

                            # Track engines and results
                            # REMOVED_SYNTAX_ERROR: engines = []
                            # REMOVED_SYNTAX_ERROR: results = []

# REMOVED_SYNTAX_ERROR: async def user1_task():
    # REMOVED_SYNTAX_ERROR: async with factory.user_execution_scope(user1_context) as engine:
        # REMOVED_SYNTAX_ERROR: engines.append(('user1', engine))
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Simulate work
        # REMOVED_SYNTAX_ERROR: results.append(('user1', engine.get_user_execution_stats()))

# REMOVED_SYNTAX_ERROR: async def user2_task():
    # REMOVED_SYNTAX_ERROR: async with factory.user_execution_scope(user2_context) as engine:
        # REMOVED_SYNTAX_ERROR: engines.append(('user2', engine))
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)  # Simulate work
        # REMOVED_SYNTAX_ERROR: results.append(('user2', engine.get_user_execution_stats()))

        # Run concurrently
        # REMOVED_SYNTAX_ERROR: await asyncio.gather(user1_task(), user2_task())

        # Verify results
        # REMOVED_SYNTAX_ERROR: assert len(engines) == 2
        # REMOVED_SYNTAX_ERROR: assert len(results) == 2

        # Verify engines were isolated
        # REMOVED_SYNTAX_ERROR: user1_engine = next(engine for label, engine in engines if label == 'user1')
        # REMOVED_SYNTAX_ERROR: user2_engine = next(engine for label, engine in engines if label == 'user2')

        # REMOVED_SYNTAX_ERROR: assert user1_engine != user2_engine
        # REMOVED_SYNTAX_ERROR: assert user1_engine.get_user_context().user_id == "concurrent_user_1"
        # REMOVED_SYNTAX_ERROR: assert user2_engine.get_user_context().user_id == "concurrent_user_2"

        # Verify stats are isolated
        # REMOVED_SYNTAX_ERROR: user1_stats = next(stats for label, stats in results if label == 'user1')
        # REMOVED_SYNTAX_ERROR: user2_stats = next(stats for label, stats in results if label == 'user2')

        # REMOVED_SYNTAX_ERROR: assert user1_stats['user_id'] == "concurrent_user_1"
        # REMOVED_SYNTAX_ERROR: assert user2_stats['user_id'] == "concurrent_user_2"
        # REMOVED_SYNTAX_ERROR: assert user1_stats['engine_id'] != user2_stats['engine_id']

        # Removed problematic line: async def test_factory_metrics_tracking(self, factory, configured_agent_factory):
            # REMOVED_SYNTAX_ERROR: """Test factory properly tracks metrics."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="metrics_user",
            # REMOVED_SYNTAX_ERROR: thread_id="metrics_thread",
            # REMOVED_SYNTAX_ERROR: run_id="metrics_run"
            

            # Initial metrics
            # REMOVED_SYNTAX_ERROR: initial_metrics = factory.get_factory_metrics()
            # REMOVED_SYNTAX_ERROR: assert initial_metrics['total_engines_created'] == 0
            # REMOVED_SYNTAX_ERROR: assert initial_metrics['active_engines_count'] == 0

            # Create engine
            # REMOVED_SYNTAX_ERROR: engine = await factory.create_for_user(user_context)

            # Check metrics after creation
            # REMOVED_SYNTAX_ERROR: creation_metrics = factory.get_factory_metrics()
            # REMOVED_SYNTAX_ERROR: assert creation_metrics['total_engines_created'] == 1
            # REMOVED_SYNTAX_ERROR: assert creation_metrics['active_engines_count'] == 1

            # Cleanup engine
            # REMOVED_SYNTAX_ERROR: await factory.cleanup_engine(engine)

            # Check metrics after cleanup
            # REMOVED_SYNTAX_ERROR: cleanup_metrics = factory.get_factory_metrics()
            # REMOVED_SYNTAX_ERROR: assert cleanup_metrics['total_engines_created'] == 1
            # REMOVED_SYNTAX_ERROR: assert cleanup_metrics['total_engines_cleaned'] == 1
            # REMOVED_SYNTAX_ERROR: assert cleanup_metrics['active_engines_count'] == 0


# REMOVED_SYNTAX_ERROR: class TestExecutionStateStore:
    # REMOVED_SYNTAX_ERROR: """Test ExecutionStateStore for global monitoring."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def store(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create execution state store."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return ExecutionStateStore()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def user_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create test user context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="store_test_user",
    # REMOVED_SYNTAX_ERROR: thread_id="store_thread",
    # REMOVED_SYNTAX_ERROR: run_id="store_run"
    

    # Removed problematic line: async def test_execution_recording(self, store, user_context):
        # REMOVED_SYNTAX_ERROR: """Test execution start/complete recording."""
        # REMOVED_SYNTAX_ERROR: execution_id = "test_execution_123"
        # REMOVED_SYNTAX_ERROR: agent_name = "test_agent"

        # Record execution start
        # REMOVED_SYNTAX_ERROR: await store.record_execution_start( )
        # REMOVED_SYNTAX_ERROR: execution_id=execution_id,
        # REMOVED_SYNTAX_ERROR: user_context=user_context,
        # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
        # REMOVED_SYNTAX_ERROR: metadata={'test': True}
        

        # Verify record created
        # REMOVED_SYNTAX_ERROR: assert execution_id in store._execution_records
        # REMOVED_SYNTAX_ERROR: record = store._execution_records[execution_id]
        # REMOVED_SYNTAX_ERROR: assert record.user_id == user_context.user_id
        # REMOVED_SYNTAX_ERROR: assert record.agent_name == agent_name
        # REMOVED_SYNTAX_ERROR: assert record.completed_at is None
        # REMOVED_SYNTAX_ERROR: assert record.success is False  # Not completed yet

        # Create execution result
        # REMOVED_SYNTAX_ERROR: result = AgentExecutionResult( )
        # REMOVED_SYNTAX_ERROR: success=True,
        # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
        # REMOVED_SYNTAX_ERROR: execution_time=2.5,
        # REMOVED_SYNTAX_ERROR: data={'result': 'success'}
        

        # Record execution complete
        # REMOVED_SYNTAX_ERROR: await store.record_execution_complete(execution_id, result)

        # Verify record updated
        # REMOVED_SYNTAX_ERROR: record = store._execution_records[execution_id]
        # REMOVED_SYNTAX_ERROR: assert record.completed_at is not None
        # REMOVED_SYNTAX_ERROR: assert record.duration_seconds == 2.5
        # REMOVED_SYNTAX_ERROR: assert record.success is True
        # REMOVED_SYNTAX_ERROR: assert record.error is None

        # Removed problematic line: async def test_user_stats_tracking(self, store):
            # REMOVED_SYNTAX_ERROR: """Test user statistics tracking."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: user_context1 = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="stats_user_1",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_1",
            # REMOVED_SYNTAX_ERROR: run_id="run_1"
            

            # REMOVED_SYNTAX_ERROR: user_context2 = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="stats_user_2",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_2",
            # REMOVED_SYNTAX_ERROR: run_id="run_2"
            

            # Record executions for user 1
            # REMOVED_SYNTAX_ERROR: await store.record_execution_start("exec_1", user_context1, "agent1")
            # REMOVED_SYNTAX_ERROR: await store.record_execution_start("exec_2", user_context1, "agent2")

            # Complete one successfully, one failed
            # REMOVED_SYNTAX_ERROR: success_result = AgentExecutionResult(success=True, agent_name="agent1", execution_time=1.0)
            # REMOVED_SYNTAX_ERROR: failed_result = AgentExecutionResult(success=False, agent_name="agent2", execution_time=2.0, error="Failed")

            # REMOVED_SYNTAX_ERROR: await store.record_execution_complete("exec_1", success_result)
            # REMOVED_SYNTAX_ERROR: await store.record_execution_complete("exec_2", failed_result)

            # Record execution for user 2
            # REMOVED_SYNTAX_ERROR: await store.record_execution_start("exec_3", user_context2, "agent3")
            # REMOVED_SYNTAX_ERROR: user2_result = AgentExecutionResult(success=True, agent_name="agent3", execution_time=3.0)
            # REMOVED_SYNTAX_ERROR: await store.record_execution_complete("exec_3", user2_result)

            # Check user stats
            # REMOVED_SYNTAX_ERROR: user1_stats = store.get_user_stats("stats_user_1")
            # REMOVED_SYNTAX_ERROR: user2_stats = store.get_user_stats("stats_user_2")

            # Verify user 1 stats
            # REMOVED_SYNTAX_ERROR: assert user1_stats['total_executions'] == 2
            # REMOVED_SYNTAX_ERROR: assert user1_stats['successful_executions'] == 1
            # REMOVED_SYNTAX_ERROR: assert user1_stats['failed_executions'] == 1
            # REMOVED_SYNTAX_ERROR: assert user1_stats['success_rate'] == 0.5
            # REMOVED_SYNTAX_ERROR: assert user1_stats['avg_execution_time'] == 1.5  # (1.0 + 2.0) / 2

            # Verify user 2 stats
            # REMOVED_SYNTAX_ERROR: assert user2_stats['total_executions'] == 1
            # REMOVED_SYNTAX_ERROR: assert user2_stats['successful_executions'] == 1
            # REMOVED_SYNTAX_ERROR: assert user2_stats['failed_executions'] == 0
            # REMOVED_SYNTAX_ERROR: assert user2_stats['success_rate'] == 1.0
            # REMOVED_SYNTAX_ERROR: assert user2_stats['avg_execution_time'] == 3.0

# REMOVED_SYNTAX_ERROR: def test_global_stats(self, store):
    # REMOVED_SYNTAX_ERROR: """Test global statistics calculation."""
    # Initial stats
    # REMOVED_SYNTAX_ERROR: initial_stats = store.get_global_stats()
    # REMOVED_SYNTAX_ERROR: assert initial_stats['total_executions'] == 0
    # REMOVED_SYNTAX_ERROR: assert initial_stats['successful_executions'] == 0
    # REMOVED_SYNTAX_ERROR: assert initial_stats['active_users'] == 0

    # Update internal stats manually for testing
    # REMOVED_SYNTAX_ERROR: store._system_stats.total_executions = 10
    # REMOVED_SYNTAX_ERROR: store._system_stats.successful_executions = 8
    # REMOVED_SYNTAX_ERROR: store._system_stats.failed_executions = 2
    # REMOVED_SYNTAX_ERROR: store._system_stats.concurrent_executions = 3

    # Add some user stats
    # REMOVED_SYNTAX_ERROR: store._user_stats['user1'] =         store._user_stats['user1'].concurrent_executions = 2
    # REMOVED_SYNTAX_ERROR: store._user_stats['user2'] =         store._user_stats['user2'].concurrent_executions = 1
    # REMOVED_SYNTAX_ERROR: store._user_stats['user3'] =         store._user_stats['user3'].concurrent_executions = 0  # Inactive

    # Get updated stats
    # REMOVED_SYNTAX_ERROR: stats = store.get_global_stats()

    # REMOVED_SYNTAX_ERROR: assert stats['total_executions'] == 10
    # REMOVED_SYNTAX_ERROR: assert stats['successful_executions'] == 8
    # REMOVED_SYNTAX_ERROR: assert stats['failed_executions'] == 2
    # REMOVED_SYNTAX_ERROR: assert stats['success_rate'] == 0.8
    # REMOVED_SYNTAX_ERROR: assert stats['concurrent_executions'] == 3
    # REMOVED_SYNTAX_ERROR: assert stats['active_users'] == 2  # user1 and user2 have concurrent > 0
    # REMOVED_SYNTAX_ERROR: assert stats['total_users_seen'] == 3

# REMOVED_SYNTAX_ERROR: def test_system_health_calculation(self, store):
    # REMOVED_SYNTAX_ERROR: """Test system health score calculation."""
    # REMOVED_SYNTAX_ERROR: pass
    # Set up stats for good health
    # REMOVED_SYNTAX_ERROR: store._system_stats.total_executions = 100
    # REMOVED_SYNTAX_ERROR: store._system_stats.successful_executions = 98  # 98% success rate
    # REMOVED_SYNTAX_ERROR: store._system_stats.failed_executions = 2

    # Add execution records with good times
    # REMOVED_SYNTAX_ERROR: for i in range(10):
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
        # REMOVED_SYNTAX_ERROR: record.completed_at = datetime.now(timezone.utc)
        # REMOVED_SYNTAX_ERROR: record.duration_seconds = 5.0  # Good execution time
        # REMOVED_SYNTAX_ERROR: store._execution_records["formatted_string"] = record

        # REMOVED_SYNTAX_ERROR: health = store.get_system_health()

        # REMOVED_SYNTAX_ERROR: assert health['status'] in ['excellent', 'good']
        # REMOVED_SYNTAX_ERROR: assert health['health_score'] >= 75
        # REMOVED_SYNTAX_ERROR: assert health['indicators']['success_rate'] == 0.98
        # REMOVED_SYNTAX_ERROR: assert len(health['recommendations']) == 0  # Should be healthy

        # Test degraded health
        # REMOVED_SYNTAX_ERROR: store._system_stats.successful_executions = 85  # 85% success rate
        # REMOVED_SYNTAX_ERROR: store._system_stats.failed_executions = 15

        # Add slow execution records
        # REMOVED_SYNTAX_ERROR: for i in range(10, 20):
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
            # REMOVED_SYNTAX_ERROR: record.completed_at = datetime.now(timezone.utc)
            # REMOVED_SYNTAX_ERROR: record.duration_seconds = 45.0  # Slow execution time
            # REMOVED_SYNTAX_ERROR: store._execution_records["formatted_string"] = record

            # REMOVED_SYNTAX_ERROR: degraded_health = store.get_system_health()

            # REMOVED_SYNTAX_ERROR: assert degraded_health['health_score'] < 75
            # REMOVED_SYNTAX_ERROR: assert len(degraded_health['recommendations']) > 0


# REMOVED_SYNTAX_ERROR: class TestConcurrentUserIsolation:
    # REMOVED_SYNTAX_ERROR: """Integration tests for concurrent user execution isolation."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def configured_system(self):
    # REMOVED_SYNTAX_ERROR: """Set up configured system for integration testing."""
    # Mock agent factory
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Mock global factory function
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
    # REMOVED_SYNTAX_ERROR: original_get_factory = factory_module.get_agent_instance_factory
    # REMOVED_SYNTAX_ERROR: factory_module.get_agent_instance_factory = Mock(return_value=agent_factory)

    # REMOVED_SYNTAX_ERROR: yield agent_factory

    # Restore
    # REMOVED_SYNTAX_ERROR: factory_module.get_agent_instance_factory = original_get_factory

    # Removed problematic line: async def test_concurrent_users_complete_isolation(self, configured_system):
        # REMOVED_SYNTAX_ERROR: """Test that multiple concurrent users have complete isolation."""
        # REMOVED_SYNTAX_ERROR: pass
        # Create contexts for multiple users
        # REMOVED_SYNTAX_ERROR: users = [ )
        # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: for i in range(5)
        

        # Track per-user results
        # REMOVED_SYNTAX_ERROR: user_results = {}

# REMOVED_SYNTAX_ERROR: async def simulate_user_execution(user_context):
    # REMOVED_SYNTAX_ERROR: """Simulate user execution with tracking."""
    # REMOVED_SYNTAX_ERROR: user_stats = []

    # REMOVED_SYNTAX_ERROR: async with user_execution_engine(user_context) as engine:
        # Track initial state
        # REMOVED_SYNTAX_ERROR: user_stats.append({ ))
        # REMOVED_SYNTAX_ERROR: 'phase': 'initial',
        # REMOVED_SYNTAX_ERROR: 'active_runs': len(engine.active_runs),
        # REMOVED_SYNTAX_ERROR: 'history_count': len(engine.run_history),
        # REMOVED_SYNTAX_ERROR: 'stats': engine.get_user_execution_stats().copy()
        

        # Simulate some work
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.05)

        # Modify engine state (simulate executions)
        # REMOVED_SYNTAX_ERROR: engine.execution_stats['total_executions'] = 3
        # REMOVED_SYNTAX_ERROR: engine.execution_stats['execution_times'] = [1.0, 2.0, 1.5]

        # Add some fake history
        # REMOVED_SYNTAX_ERROR: fake_result = AgentExecutionResult( )
        # REMOVED_SYNTAX_ERROR: success=True,
        # REMOVED_SYNTAX_ERROR: agent_name="test_agent",
        # REMOVED_SYNTAX_ERROR: execution_time=1.5,
        # REMOVED_SYNTAX_ERROR: data={'test': True}
        
        # REMOVED_SYNTAX_ERROR: engine.run_history.append(fake_result)

        # Track modified state
        # REMOVED_SYNTAX_ERROR: user_stats.append({ ))
        # REMOVED_SYNTAX_ERROR: 'phase': 'modified',
        # REMOVED_SYNTAX_ERROR: 'active_runs': len(engine.active_runs),
        # REMOVED_SYNTAX_ERROR: 'history_count': len(engine.run_history),
        # REMOVED_SYNTAX_ERROR: 'stats': engine.get_user_execution_stats().copy()
        

        # REMOVED_SYNTAX_ERROR: user_results[user_context.user_id] = user_stats

        # Run all users concurrently
        # Removed problematic line: await asyncio.gather(*[ ))
        # REMOVED_SYNTAX_ERROR: simulate_user_execution(user_context)
        # REMOVED_SYNTAX_ERROR: for user_context in users
        

        # Verify isolation - each user should have independent state
        # REMOVED_SYNTAX_ERROR: assert len(user_results) == 5

        # REMOVED_SYNTAX_ERROR: for user_id, stats_list in user_results.items():
            # REMOVED_SYNTAX_ERROR: assert len(stats_list) == 2  # initial and modified

            # REMOVED_SYNTAX_ERROR: initial_stats = stats_list[0]
            # REMOVED_SYNTAX_ERROR: modified_stats = stats_list[1]

            # Verify initial isolation
            # REMOVED_SYNTAX_ERROR: assert initial_stats['active_runs'] == 0
            # REMOVED_SYNTAX_ERROR: assert initial_stats['history_count'] == 0
            # REMOVED_SYNTAX_ERROR: assert initial_stats['stats']['total_executions'] == 0

            # Verify modifications are isolated per user
            # REMOVED_SYNTAX_ERROR: assert modified_stats['history_count'] == 1
            # REMOVED_SYNTAX_ERROR: assert modified_stats['stats']['total_executions'] == 3
            # REMOVED_SYNTAX_ERROR: assert modified_stats['stats']['user_id'] == user_id
            # REMOVED_SYNTAX_ERROR: assert modified_stats['stats']['avg_execution_time'] == pytest.approx(1.5)

            # Verify no cross-contamination between users
            # REMOVED_SYNTAX_ERROR: user_ids = list(user_results.keys())
            # REMOVED_SYNTAX_ERROR: for i in range(len(user_ids)):
                # REMOVED_SYNTAX_ERROR: for j in range(i + 1, len(user_ids)):
                    # REMOVED_SYNTAX_ERROR: user_i_stats = user_results[user_ids[i]][1]['stats']
                    # REMOVED_SYNTAX_ERROR: user_j_stats = user_results[user_ids[j]][1]['stats']

                    # Each user should have completely different engine IDs and contexts
                    # REMOVED_SYNTAX_ERROR: assert user_i_stats['engine_id'] != user_j_stats['engine_id']
                    # REMOVED_SYNTAX_ERROR: assert user_i_stats['user_id'] != user_j_stats['user_id']
                    # REMOVED_SYNTAX_ERROR: assert user_i_stats['run_id'] != user_j_stats['run_id']

                    # Removed problematic line: async def test_user_execution_engine_vs_legacy_isolation(self, configured_system):
                        # REMOVED_SYNTAX_ERROR: """Test isolation comparison between UserExecutionEngine and legacy ExecutionEngine."""
                        # REMOVED_SYNTAX_ERROR: pass
                        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine

                        # REMOVED_SYNTAX_ERROR: user_context = UserExecutionContext( )
                        # REMOVED_SYNTAX_ERROR: user_id="isolation_test_user",
                        # REMOVED_SYNTAX_ERROR: thread_id="isolation_thread",
                        # REMOVED_SYNTAX_ERROR: run_id="isolation_run"
                        

                        # Test UserExecutionEngine (isolated)
                        # REMOVED_SYNTAX_ERROR: user_results = {}
                        # REMOVED_SYNTAX_ERROR: async with user_execution_engine(user_context) as engine:
                            # Modify state
                            # REMOVED_SYNTAX_ERROR: engine.execution_stats['total_executions'] = 10
                            # REMOVED_SYNTAX_ERROR: engine.execution_stats['custom_metric'] = 'user_isolated'
                            # REMOVED_SYNTAX_ERROR: user_results['isolated'] = engine.get_user_execution_stats().copy()

                            # Test legacy ExecutionEngine (global state - would be shared)
                            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation

                            # REMOVED_SYNTAX_ERROR: legacy_engine1 = ExecutionEngine(mock_registry, mock_bridge)
                            # REMOVED_SYNTAX_ERROR: legacy_engine2 = ExecutionEngine(mock_registry, mock_bridge)

                            # Both legacy engines share global state (this is the problem we're solving)
                            # REMOVED_SYNTAX_ERROR: legacy_engine1.execution_stats['total_executions'] = 20
                            # REMOVED_SYNTAX_ERROR: legacy_engine1.execution_stats['custom_metric'] = 'shared_global'

                            # Get stats from both legacy engines
                            # REMOVED_SYNTAX_ERROR: legacy_stats1 = await legacy_engine1.get_execution_stats()
                            # REMOVED_SYNTAX_ERROR: legacy_stats2 = await legacy_engine2.get_execution_stats()

                            # Verify UserExecutionEngine isolation
                            # REMOVED_SYNTAX_ERROR: assert user_results['isolated']['total_executions'] == 10
                            # REMOVED_SYNTAX_ERROR: assert user_results['isolated']['user_id'] == user_context.user_id

                            # Verify legacy engines share state (the problem)
                            # Note: This test documents the existing global state issue
                            # Both engines see the same modifications because they share global state
                            # REMOVED_SYNTAX_ERROR: assert legacy_stats1['total_executions'] == legacy_stats2['total_executions']

                            # The user engine stats should be completely different from legacy
                            # REMOVED_SYNTAX_ERROR: assert user_results['isolated']['total_executions'] != legacy_stats1['total_executions']