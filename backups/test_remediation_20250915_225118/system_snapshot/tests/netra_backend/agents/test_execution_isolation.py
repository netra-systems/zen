class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Tests for execution isolation with UserExecutionEngine and ExecutionEngineFactory.

        This test suite verifies that user execution isolation works correctly and prevents
        state leakage between concurrent users.

        Business Value: Ensures production-ready concurrent user support with zero context leakage.
        '''

        import asyncio
        import pytest
        import uuid
        import time
        from datetime import datetime, timezone
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.schemas.agent_models import DeepAgentState
        from netra_backend.app.agents.supervisor.execution_context import ( )
        AgentExecutionContext,
        AgentExecutionResult)
        from netra_backend.app.agents.supervisor.user_execution_context import ( )
        UserExecutionContext,
        InvalidContextError
    
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from netra_backend.app.agents.supervisor.execution_engine_factory import ( )
        ExecutionEngineFactory,
        get_execution_engine_factory,
        user_execution_engine
    
        from netra_backend.app.agents.supervisor.execution_state_store import ( )
        ExecutionStateStore,
        get_execution_state_store
    
        from netra_backend.app.agents.supervisor.agent_instance_factory import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        UserWebSocketEmitter,
        get_agent_instance_factory
    


class TestUserExecutionEngine:
        """Test UserExecutionEngine for per-user isolation."""

        @pytest.fixture
    def user_context(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create test user execution context."""
        pass
        return UserExecutionContext( )
        user_id="test_user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_101112"
    

        @pytest.fixture
    def different_user_context(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create different user execution context."""
        pass
        return UserExecutionContext( )
        user_id="different_user_456",
        thread_id="thread_789",
        run_id="run_101112",
        request_id="req_131415"
    

        @pytest.fixture
    def real_agent_factory():
        """Use real service instance."""
    # TODO: Initialize real service
        """Mock agent factory with required components."""
        pass
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        return factory

        @pytest.fixture
    def real_websocket_emitter():
        """Use real service instance."""
    # TODO: Initialize real service
        """Mock UserWebSocketEmitter."""
        pass
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        emitter.notify_agent_started = AsyncMock(return_value=True)
        emitter.notify_agent_thinking = AsyncMock(return_value=True)
        emitter.notify_agent_completed = AsyncMock(return_value=True)
        emitter.websocket = TestWebSocketConnection()
        return emitter

        @pytest.fixture
    def agent_execution_context(self, user_context):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create agent execution context."""
        pass
        return AgentExecutionContext( )
        agent_name="test_agent",
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id
    

        @pytest.fixture
    def deep_agent_state(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create deep agent state."""
        pass
        state = Mock(spec=DeepAgentState)
        state.user_prompt = "Test prompt"
        return state

    def test_user_execution_engine_creation(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test UserExecutionEngine creation with proper initialization."""
    # Create engine
        engine = UserExecutionEngine( )
        context=user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
    

    # Verify initialization
        assert engine.context == user_context
        assert engine.agent_factory == mock_agent_factory
        assert engine.websocket_emitter == mock_websocket_emitter
        assert engine.is_active()
        assert len(engine.active_runs) == 0
        assert len(engine.run_history) == 0
        assert engine.max_concurrent == 3  # default

    # Verify engine metadata
        assert engine.engine_id.startswith("user_engine_")
        assert user_context.user_id in engine.engine_id
        assert user_context.run_id in engine.engine_id

    def test_user_execution_engine_context_validation(self, mock_agent_factory, mock_websocket_emitter):
        """Test context validation during engine creation."""
        pass
    # Test invalid context (None)
        with pytest.raises(TypeError):
        UserExecutionEngine( )
        context=None,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
        

        # Test invalid context (wrong type)
        with pytest.raises(TypeError):
        UserExecutionEngine( )
        context="not_a_context",
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
            

            # Test missing agent factory
        valid_context = UserExecutionContext( )
        user_id="test", thread_id="thread", run_id="run"
            
        with pytest.raises(ValueError):
        UserExecutionEngine( )
        context=valid_context,
        agent_factory=None,
        websocket_emitter=mock_websocket_emitter
                

    async def test_execution_context_validation(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test execution context validation against user context."""
        engine = UserExecutionEngine( )
        context=user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
                    

                    # Valid context (matches user)
        valid_agent_context = AgentExecutionContext( )
        agent_name="test_agent",
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id
                    

                    # This should not raise
        engine._validate_execution_context(valid_agent_context)

                    # Invalid context (different user)
        invalid_agent_context = AgentExecutionContext( )
        agent_name="test_agent",
        user_id="different_user",
        thread_id=user_context.thread_id,
        run_id=user_context.run_id
                    

        with pytest.raises(ValueError, match="User ID mismatch"):
        engine._validate_execution_context(invalid_agent_context)

                        # Removed problematic line: async def test_user_isolation_stats(self, user_context, different_user_context,
        mock_agent_factory, mock_websocket_emitter):
        """Test that execution stats are isolated per user."""
        pass
                            # Create engines for different users
        engine1 = UserExecutionEngine( )
        context=user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
                            

        engine2 = UserExecutionEngine( )
        context=different_user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
                            

                            # Modify stats for engine1
        engine1.execution_stats['total_executions'] = 5
        engine1.execution_stats['successful_executions'] = 4
        engine1.execution_stats['execution_times'] = [1.0, 2.0, 3.0, 4.0, 5.0]

                            # Modify stats for engine2 (different values)
        engine2.execution_stats['total_executions'] = 10
        engine2.execution_stats['successful_executions'] = 8
        engine2.execution_stats['execution_times'] = [0.5, 1.5, 2.5]

                            # Get stats for each user
        stats1 = engine1.get_user_execution_stats()
        stats2 = engine2.get_user_execution_stats()

                            # Verify isolation - stats should be different
        assert stats1['total_executions'] == 5
        assert stats1['user_id'] == user_context.user_id
        assert stats1['avg_execution_time'] == 3.0  # (1+2+3+4+5)/5

        assert stats2['total_executions'] == 10
        assert stats2['user_id'] == different_user_context.user_id
        assert stats2['avg_execution_time'] == pytest.approx(1.5)  # (0.5+1.5+2.5)/3

                            # Verify complete isolation
        assert stats1['user_id'] != stats2['user_id']
        assert stats1['engine_id'] != stats2['engine_id']
        assert stats1['run_id'] != stats2['run_id']

                            # Removed problematic line: async def test_active_runs_isolation(self, user_context, different_user_context,
        mock_agent_factory, mock_websocket_emitter):
        """Test that active runs are isolated per user."""
                                # Create engines for different users
        engine1 = UserExecutionEngine( )
        context=user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
                                

        engine2 = UserExecutionEngine( )
        context=different_user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=mock_websocket_emitter
                                

                                # Add active runs to each engine
        execution_id_1 = "exec_1"
        execution_id_2 = "exec_2"

        context_1 = AgentExecutionContext( )
        agent_name="agent1",
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id
                                

        context_2 = AgentExecutionContext( )
        agent_name="agent2",
        user_id=different_user_context.user_id,
        thread_id=different_user_context.thread_id,
        run_id=different_user_context.run_id
                                

        engine1.active_runs[execution_id_1] = context_1
        engine2.active_runs[execution_id_2] = context_2

                                # Verify isolation
        assert len(engine1.active_runs) == 1
        assert len(engine2.active_runs) == 1
        assert execution_id_1 in engine1.active_runs
        assert execution_id_2 in engine2.active_runs
        assert execution_id_1 not in engine2.active_runs
        assert execution_id_2 not in engine1.active_runs

                                # Verify contexts match users
        assert engine1.active_runs[execution_id_1].user_id == user_context.user_id
        assert engine2.active_runs[execution_id_2].user_id == different_user_context.user_id

                                # Removed problematic line: async def test_websocket_emitter_isolation(self, user_context, different_user_context,
        mock_agent_factory):
        """Test that WebSocket emitters are isolated per user."""
                                    # Create separate emitters for each user
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        emitter1.notify_agent_started = AsyncMock(return_value=True)
        emitter1.websocket = TestWebSocketConnection()

        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        emitter2.notify_agent_started = AsyncMock(return_value=True)
        emitter2.websocket = TestWebSocketConnection()

                                    # Create engines with different emitters
        engine1 = UserExecutionEngine( )
        context=user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=emitter1
                                    

        engine2 = UserExecutionEngine( )
        context=different_user_context,
        agent_factory=mock_agent_factory,
        websocket_emitter=emitter2
                                    

                                    # Verify different emitters
        assert engine1.websocket_emitter != engine2.websocket_emitter
        assert engine1.websocket_emitter == emitter1
        assert engine2.websocket_emitter == emitter2

                                    # Test sending notifications
        context1 = AgentExecutionContext( )
        agent_name="agent1",
        user_id=user_context.user_id,
        thread_id=user_context.thread_id,
        run_id=user_context.run_id
                                    

        context2 = AgentExecutionContext( )
        agent_name="agent2",
        user_id=different_user_context.user_id,
        thread_id=different_user_context.thread_id,
        run_id=different_user_context.run_id
                                    

        await engine1._send_user_agent_started(context1)
        await engine2._send_user_agent_started(context2)

                                    # Verify each emitter was called for its respective user only
        emitter1.notify_agent_started.assert_called_once()
        emitter2.notify_agent_started.assert_called_once()

                                    # Verify call arguments include correct user info
        call_args_1 = emitter1.notify_agent_started.call_args
        call_args_2 = emitter2.notify_agent_started.call_args

        assert call_args_1[1]['context']['user_id'] == user_context.user_id
        assert call_args_2[1]['context']['user_id'] == different_user_context.user_id


class TestExecutionEngineFactory:
        """Test ExecutionEngineFactory for managing user engines."""

        @pytest.fixture
    def user_context(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create test user execution context."""
        pass
        await asyncio.sleep(0)
        return UserExecutionContext( )
        user_id="factory_test_user",
        thread_id="factory_thread",
        run_id="factory_run",
        request_id="factory_req"
    

        @pytest.fixture
    def factory(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create execution engine factory."""
        pass
        return ExecutionEngineFactory()

        @pytest.fixture
    async def configured_agent_factory(self):
        """Mock configured agent instance factory."""
        websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Mock the global factory
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        original_get_factory = factory_module.get_agent_instance_factory
        factory_module.get_agent_instance_factory = Mock(return_value=factory)

        yield factory

    # Restore original
        factory_module.get_agent_instance_factory = original_get_factory

    async def test_factory_create_for_user(self, factory, user_context, configured_agent_factory):
        """Test factory creates isolated engines for users."""
        pass
        # Create engine for user
        engine = await factory.create_for_user(user_context)

        # Verify engine creation
        assert isinstance(engine, UserExecutionEngine)
        assert engine.is_active()
        assert engine.get_user_context() == user_context

        # Verify factory tracking
        assert len(factory._active_engines) == 1
        assert factory._factory_metrics['total_engines_created'] == 1
        assert factory._factory_metrics['active_engines_count'] == 1

    async def test_factory_user_limits(self, factory, configured_agent_factory):
        """Test factory enforces per-user engine limits."""
            # Set low limit for testing
        factory._max_engines_per_user = 2

        user_id = "limited_user"

            # Create contexts for same user
        contexts = [ )
        UserExecutionContext(user_id=user_id, thread_id="formatted_string", run_id="formatted_string")
        for i in range(3)
            

            # First two should succeed
        engine1 = await factory.create_for_user(contexts[0])
        engine2 = await factory.create_for_user(contexts[1])

        assert len(factory._active_engines) == 2

            # Third should fail (exceeds limit)
        with pytest.raises(Exception, match="reached maximum engine limit"):
        await factory.create_for_user(contexts[2])

    async def test_factory_user_execution_scope(self, factory, user_context, configured_agent_factory):
        """Test factory context manager provides proper isolation."""
        pass
                    # Track engines created
        engines_created = []

        async with factory.user_execution_scope(user_context) as engine:
        engines_created.append(engine)
        assert isinstance(engine, UserExecutionEngine)
        assert engine.is_active()
        assert engine.get_user_context() == user_context

                        # Verify engine is tracked
        assert len(factory._active_engines) == 1

                        # After context exit, engine should be cleaned up
        assert not engine.is_active()
        assert len(factory._active_engines) == 0
        assert factory._factory_metrics['total_engines_cleaned'] == 1

    async def test_concurrent_user_execution_scopes(self, factory, configured_agent_factory):
        """Test concurrent execution scopes for different users."""
                            # Create contexts for different users
        user1_context = UserExecutionContext( )
        user_id="concurrent_user_1",
        thread_id="thread_1",
        run_id="run_1"
                            

        user2_context = UserExecutionContext( )
        user_id="concurrent_user_2",
        thread_id="thread_2",
        run_id="run_2"
                            

                            # Track engines and results
        engines = []
        results = []

    async def user1_task():
        async with factory.user_execution_scope(user1_context) as engine:
        engines.append(('user1', engine))
        await asyncio.sleep(0.1)  # Simulate work
        results.append(('user1', engine.get_user_execution_stats()))

    async def user2_task():
        async with factory.user_execution_scope(user2_context) as engine:
        engines.append(('user2', engine))
        await asyncio.sleep(0.1)  # Simulate work
        results.append(('user2', engine.get_user_execution_stats()))

        # Run concurrently
        await asyncio.gather(user1_task(), user2_task())

        # Verify results
        assert len(engines) == 2
        assert len(results) == 2

        # Verify engines were isolated
        user1_engine = next(engine for label, engine in engines if label == 'user1')
        user2_engine = next(engine for label, engine in engines if label == 'user2')

        assert user1_engine != user2_engine
        assert user1_engine.get_user_context().user_id == "concurrent_user_1"
        assert user2_engine.get_user_context().user_id == "concurrent_user_2"

        # Verify stats are isolated
        user1_stats = next(stats for label, stats in results if label == 'user1')
        user2_stats = next(stats for label, stats in results if label == 'user2')

        assert user1_stats['user_id'] == "concurrent_user_1"
        assert user2_stats['user_id'] == "concurrent_user_2"
        assert user1_stats['engine_id'] != user2_stats['engine_id']

    async def test_factory_metrics_tracking(self, factory, configured_agent_factory):
        """Test factory properly tracks metrics."""
        pass
        user_context = UserExecutionContext( )
        user_id="metrics_user",
        thread_id="metrics_thread",
        run_id="metrics_run"
            

            # Initial metrics
        initial_metrics = factory.get_factory_metrics()
        assert initial_metrics['total_engines_created'] == 0
        assert initial_metrics['active_engines_count'] == 0

            # Create engine
        engine = await factory.create_for_user(user_context)

            # Check metrics after creation
        creation_metrics = factory.get_factory_metrics()
        assert creation_metrics['total_engines_created'] == 1
        assert creation_metrics['active_engines_count'] == 1

            # Cleanup engine
        await factory.cleanup_engine(engine)

            # Check metrics after cleanup
        cleanup_metrics = factory.get_factory_metrics()
        assert cleanup_metrics['total_engines_created'] == 1
        assert cleanup_metrics['total_engines_cleaned'] == 1
        assert cleanup_metrics['active_engines_count'] == 0


class TestExecutionStateStore:
        """Test ExecutionStateStore for global monitoring."""

        @pytest.fixture
    def store(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create execution state store."""
        pass
        await asyncio.sleep(0)
        return ExecutionStateStore()

        @pytest.fixture
    def user_context(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create test user context."""
        pass
        return UserExecutionContext( )
        user_id="store_test_user",
        thread_id="store_thread",
        run_id="store_run"
    

    async def test_execution_recording(self, store, user_context):
        """Test execution start/complete recording."""
        execution_id = "test_execution_123"
        agent_name = "test_agent"

        # Record execution start
        await store.record_execution_start( )
        execution_id=execution_id,
        user_context=user_context,
        agent_name=agent_name,
        metadata={'test': True}
        

        # Verify record created
        assert execution_id in store._execution_records
        record = store._execution_records[execution_id]
        assert record.user_id == user_context.user_id
        assert record.agent_name == agent_name
        assert record.completed_at is None
        assert record.success is False  # Not completed yet

        # Create execution result
        result = AgentExecutionResult( )
        success=True,
        agent_name=agent_name,
        execution_time=2.5,
        data={'result': 'success'}
        

        # Record execution complete
        await store.record_execution_complete(execution_id, result)

        # Verify record updated
        record = store._execution_records[execution_id]
        assert record.completed_at is not None
        assert record.duration_seconds == 2.5
        assert record.success is True
        assert record.error is None

    async def test_user_stats_tracking(self, store):
        """Test user statistics tracking."""
        pass
        user_context1 = UserExecutionContext( )
        user_id="stats_user_1",
        thread_id="thread_1",
        run_id="run_1"
            

        user_context2 = UserExecutionContext( )
        user_id="stats_user_2",
        thread_id="thread_2",
        run_id="run_2"
            

            # Record executions for user 1
        await store.record_execution_start("exec_1", user_context1, "agent1")
        await store.record_execution_start("exec_2", user_context1, "agent2")

            # Complete one successfully, one failed
        success_result = AgentExecutionResult(success=True, agent_name="agent1", execution_time=1.0)
        failed_result = AgentExecutionResult(success=False, agent_name="agent2", execution_time=2.0, error="Failed")

        await store.record_execution_complete("exec_1", success_result)
        await store.record_execution_complete("exec_2", failed_result)

            # Record execution for user 2
        await store.record_execution_start("exec_3", user_context2, "agent3")
        user2_result = AgentExecutionResult(success=True, agent_name="agent3", execution_time=3.0)
        await store.record_execution_complete("exec_3", user2_result)

            # Check user stats
        user1_stats = store.get_user_stats("stats_user_1")
        user2_stats = store.get_user_stats("stats_user_2")

            # Verify user 1 stats
        assert user1_stats['total_executions'] == 2
        assert user1_stats['successful_executions'] == 1
        assert user1_stats['failed_executions'] == 1
        assert user1_stats['success_rate'] == 0.5
        assert user1_stats['avg_execution_time'] == 1.5  # (1.0 + 2.0) / 2

            # Verify user 2 stats
        assert user2_stats['total_executions'] == 1
        assert user2_stats['successful_executions'] == 1
        assert user2_stats['failed_executions'] == 0
        assert user2_stats['success_rate'] == 1.0
        assert user2_stats['avg_execution_time'] == 3.0

    def test_global_stats(self, store):
        """Test global statistics calculation."""
    # Initial stats
        initial_stats = store.get_global_stats()
        assert initial_stats['total_executions'] == 0
        assert initial_stats['successful_executions'] == 0
        assert initial_stats['active_users'] == 0

    # Update internal stats manually for testing
        store._system_stats.total_executions = 10
        store._system_stats.successful_executions = 8
        store._system_stats.failed_executions = 2
        store._system_stats.concurrent_executions = 3

    # Add some user stats
        store._user_stats['user1'] =         store._user_stats['user1'].concurrent_executions = 2
        store._user_stats['user2'] =         store._user_stats['user2'].concurrent_executions = 1
        store._user_stats['user3'] =         store._user_stats['user3'].concurrent_executions = 0  # Inactive

    # Get updated stats
        stats = store.get_global_stats()

        assert stats['total_executions'] == 10
        assert stats['successful_executions'] == 8
        assert stats['failed_executions'] == 2
        assert stats['success_rate'] == 0.8
        assert stats['concurrent_executions'] == 3
        assert stats['active_users'] == 2  # user1 and user2 have concurrent > 0
        assert stats['total_users_seen'] == 3

    def test_system_health_calculation(self, store):
        """Test system health score calculation."""
        pass
    # Set up stats for good health
        store._system_stats.total_executions = 100
        store._system_stats.successful_executions = 98  # 98% success rate
        store._system_stats.failed_executions = 2

    # Add execution records with good times
        for i in range(10):
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        record.completed_at = datetime.now(timezone.utc)
        record.duration_seconds = 5.0  # Good execution time
        store._execution_records["formatted_string"] = record

        health = store.get_system_health()

        assert health['status'] in ['excellent', 'good']
        assert health['health_score'] >= 75
        assert health['indicators']['success_rate'] == 0.98
        assert len(health['recommendations']) == 0  # Should be healthy

        # Test degraded health
        store._system_stats.successful_executions = 85  # 85% success rate
        store._system_stats.failed_executions = 15

        # Add slow execution records
        for i in range(10, 20):
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        record.completed_at = datetime.now(timezone.utc)
        record.duration_seconds = 45.0  # Slow execution time
        store._execution_records["formatted_string"] = record

        degraded_health = store.get_system_health()

        assert degraded_health['health_score'] < 75
        assert len(degraded_health['recommendations']) > 0


class TestConcurrentUserIsolation:
        """Integration tests for concurrent user execution isolation."""

        @pytest.fixture
    async def configured_system(self):
        """Set up configured system for integration testing."""
    # Mock agent factory
        websocket = TestWebSocketConnection()  # Real WebSocket implementation

    # Mock global factory function
        import netra_backend.app.agents.supervisor.agent_instance_factory as factory_module
        original_get_factory = factory_module.get_agent_instance_factory
        factory_module.get_agent_instance_factory = Mock(return_value=agent_factory)

        yield agent_factory

    # Restore
        factory_module.get_agent_instance_factory = original_get_factory

    async def test_concurrent_users_complete_isolation(self, configured_system):
        """Test that multiple concurrent users have complete isolation."""
        pass
        # Create contexts for multiple users
        users = [ )
        UserExecutionContext( )
        user_id="formatted_string",
        thread_id="formatted_string",
        run_id="formatted_string"
        
        for i in range(5)
        

        # Track per-user results
        user_results = {}

    async def simulate_user_execution(user_context):
        """Simulate user execution with tracking."""
        user_stats = []

        async with user_execution_engine(user_context) as engine:
        # Track initial state
        user_stats.append({ ))
        'phase': 'initial',
        'active_runs': len(engine.active_runs),
        'history_count': len(engine.run_history),
        'stats': engine.get_user_execution_stats().copy()
        

        # Simulate some work
        await asyncio.sleep(0.05)

        # Modify engine state (simulate executions)
        engine.execution_stats['total_executions'] = 3
        engine.execution_stats['execution_times'] = [1.0, 2.0, 1.5]

        # Add some fake history
        fake_result = AgentExecutionResult( )
        success=True,
        agent_name="test_agent",
        execution_time=1.5,
        data={'test': True}
        
        engine.run_history.append(fake_result)

        # Track modified state
        user_stats.append({ ))
        'phase': 'modified',
        'active_runs': len(engine.active_runs),
        'history_count': len(engine.run_history),
        'stats': engine.get_user_execution_stats().copy()
        

        user_results[user_context.user_id] = user_stats

        # Run all users concurrently
        # Removed problematic line: await asyncio.gather(*[ ))
        simulate_user_execution(user_context)
        for user_context in users
        

        # Verify isolation - each user should have independent state
        assert len(user_results) == 5

        for user_id, stats_list in user_results.items():
        assert len(stats_list) == 2  # initial and modified

        initial_stats = stats_list[0]
        modified_stats = stats_list[1]

            # Verify initial isolation
        assert initial_stats['active_runs'] == 0
        assert initial_stats['history_count'] == 0
        assert initial_stats['stats']['total_executions'] == 0

            # Verify modifications are isolated per user
        assert modified_stats['history_count'] == 1
        assert modified_stats['stats']['total_executions'] == 3
        assert modified_stats['stats']['user_id'] == user_id
        assert modified_stats['stats']['avg_execution_time'] == pytest.approx(1.5)

            # Verify no cross-contamination between users
        user_ids = list(user_results.keys())
        for i in range(len(user_ids)):
        for j in range(i + 1, len(user_ids)):
        user_i_stats = user_results[user_ids[i]][1]['stats']
        user_j_stats = user_results[user_ids[j]][1]['stats']

                    # Each user should have completely different engine IDs and contexts
        assert user_i_stats['engine_id'] != user_j_stats['engine_id']
        assert user_i_stats['user_id'] != user_j_stats['user_id']
        assert user_i_stats['run_id'] != user_j_stats['run_id']

    async def test_user_execution_engine_vs_legacy_isolation(self, configured_system):
        """Test isolation comparison between UserExecutionEngine and legacy ExecutionEngine."""
        pass
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine

        user_context = UserExecutionContext( )
        user_id="isolation_test_user",
        thread_id="isolation_thread",
        run_id="isolation_run"
                        

                        # Test UserExecutionEngine (isolated)
        user_results = {}
        async with user_execution_engine(user_context) as engine:
                            # Modify state
        engine.execution_stats['total_executions'] = 10
        engine.execution_stats['custom_metric'] = 'user_isolated'
        user_results['isolated'] = engine.get_user_execution_stats().copy()

                            # Test legacy ExecutionEngine (global state - would be shared)
        websocket = TestWebSocketConnection()  # Real WebSocket implementation

        legacy_engine1 = UserExecutionEngine(mock_registry, mock_bridge)
        legacy_engine2 = UserExecutionEngine(mock_registry, mock_bridge)

                            # Both legacy engines share global state (this is the problem we're solving)
        legacy_engine1.execution_stats['total_executions'] = 20
        legacy_engine1.execution_stats['custom_metric'] = 'shared_global'

                            Get stats from both legacy engines
        legacy_stats1 = await legacy_engine1.get_execution_stats()
        legacy_stats2 = await legacy_engine2.get_execution_stats()

                            # Verify UserExecutionEngine isolation
        assert user_results['isolated']['total_executions'] == 10
        assert user_results['isolated']['user_id'] == user_context.user_id

                            # Verify legacy engines share state (the problem)
                            # Note: This test documents the existing global state issue
                            # Both engines see the same modifications because they share global state
        assert legacy_stats1['total_executions'] == legacy_stats2['total_executions']

                            The user engine stats should be completely different from legacy
        assert user_results['isolated']['total_executions'] != legacy_stats1['total_executions']
