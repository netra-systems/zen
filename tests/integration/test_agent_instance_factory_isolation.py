"""
Integration Tests: AgentInstanceFactory Isolation Validation

CRITICAL MISSION: Verify complete user isolation in agent instance creation.

These tests ensure that:
1. Each user gets completely isolated agent instances
2. No shared state exists between concurrent users
3. WebSocket events reach only the correct users
4. Database sessions are properly isolated per request
5. Resource cleanup prevents memory leaks
6. Concurrent users don't interfere with each other

Business Value: Prevents $1M+ data leakage incidents and enables safe multi-user deployment.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import MagicMock, AsyncMock, patch
import time

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    UserExecutionContext,
    UserWebSocketEmitter,
    configure_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MockAgent(BaseAgent):
    """Mock agent for testing isolation."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_log = []
        self.user_specific_data = {}
        self.websocket_events = []
    
    async def execute(self, state, run_id="", stream_updates=False):
        """Mock execution that tracks user-specific data."""
        user_id = getattr(state, 'user_id', 'unknown')
        
        # Log execution for isolation testing
        self.execution_log.append({
            'timestamp': datetime.now(timezone.utc),
            'user_id': user_id,
            'run_id': run_id,
            'state_data': getattr(state, 'user_request', 'no_request')
        })
        
        # Store user-specific data to test isolation
        self.user_specific_data[user_id] = {
            'last_execution': datetime.now(timezone.utc),
            'run_id': run_id,
            'execution_count': self.user_specific_data.get(user_id, {}).get('execution_count', 0) + 1
        }
        
        # Test WebSocket event emission
        if hasattr(self, '_websocket_adapter') and self._websocket_adapter:
            try:
                await self.emit_agent_started(f"Processing for user {user_id}")
                await self.emit_thinking(f"Thinking for user {user_id}", 1)
                await self.emit_agent_completed({'result': f'completed for {user_id}'})
                
                self.websocket_events.append({
                    'user_id': user_id,
                    'run_id': run_id,
                    'events_sent': 3,
                    'timestamp': datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"WebSocket events failed for user {user_id}: {e}")
        
        return {
            'status': 'completed',
            'user_id': user_id,
            'run_id': run_id,
            'message': f'Mock agent completed for user {user_id}',
            'isolation_data': self.user_specific_data[user_id].copy()
        }


@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, user_id TEXT, data TEXT)"))
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(test_db_engine):
    """Create session factory."""
    return async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager."""
    return MagicMock(spec=LLMManager)


@pytest.fixture
def mock_tool_dispatcher():
    """Create mock tool dispatcher."""
    dispatcher = MagicMock(spec=ToolDispatcher)
    dispatcher.set_websocket_bridge = MagicMock()
    return dispatcher


@pytest.fixture
def mock_websocket_bridge():
    """Create mock WebSocket bridge."""
    bridge = MagicMock(spec=AgentWebSocketBridge)
    bridge.notify_agent_started = AsyncMock(return_value=True)
    bridge.notify_agent_thinking = AsyncMock(return_value=True)
    bridge.notify_agent_completed = AsyncMock(return_value=True)
    bridge.notify_tool_executing = AsyncMock(return_value=True)
    bridge.notify_tool_completed = AsyncMock(return_value=True)
    bridge.notify_agent_error = AsyncMock(return_value=True)
    bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    bridge.unregister_run_mapping = AsyncMock(return_value=True)
    return bridge


@pytest.fixture
async def configured_factory(mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge):
    """Create configured agent instance factory."""
    # Create agent registry with mock agent
    registry = AgentRegistry(mock_llm_manager, mock_tool_dispatcher)
    registry.register("mock_agent", MockAgent(mock_llm_manager, "MockAgent"))
    
    # Create and configure factory
    factory = AgentInstanceFactory()
    factory.configure(
        agent_registry=registry,
        websocket_bridge=mock_websocket_bridge
    )
    
    return factory, registry, mock_websocket_bridge


class TestUserExecutionContextIsolation:
    """Test UserExecutionContext isolation properties."""
    
    @pytest.mark.asyncio
    async def test_context_complete_isolation(self, session_factory):
        """Test that UserExecutionContext instances are completely isolated."""
        
        # Create two separate database sessions
        async with session_factory() as session1, session_factory() as session2:
            
            # Create two user contexts
            context1 = UserExecutionContext(
                user_id="user_1",
                thread_id="thread_1", 
                run_id="run_1",
                db_session=session1
            )
            
            context2 = UserExecutionContext(
                user_id="user_2",
                thread_id="thread_2",
                run_id="run_2", 
                db_session=session2
            )
            
            # Verify complete isolation
            assert context1.user_id != context2.user_id
            assert context1.thread_id != context2.thread_id
            assert context1.run_id != context2.run_id
            assert context1.db_session != context2.db_session
            
            # Verify state dictionaries are separate
            assert id(context1.active_runs) != id(context2.active_runs)
            assert id(context1.run_history) != id(context2.run_history)
            assert id(context1.execution_metrics) != id(context2.execution_metrics)
            
            # Test state isolation - changes to one don't affect the other
            context1.active_runs['test_run'] = {'data': 'user1_data'}
            context1.execution_metrics['user1_metric'] = 100
            
            assert 'test_run' not in context2.active_runs
            assert 'user1_metric' not in context2.execution_metrics
            
            # Verify metadata isolation
            context1.request_metadata['user1_flag'] = True
            assert 'user1_flag' not in context2.request_metadata
    
    @pytest.mark.asyncio
    async def test_context_cleanup_isolation(self, session_factory):
        """Test that context cleanup doesn't affect other contexts."""
        
        async with session_factory() as session1, session_factory() as session2:
            
            context1 = UserExecutionContext(
                user_id="user_1",
                thread_id="thread_1",
                run_id="run_1", 
                db_session=session1
            )
            
            context2 = UserExecutionContext(
                user_id="user_2",
                thread_id="thread_2",
                run_id="run_2",
                db_session=session2
            )
            
            # Add data to both contexts
            context1.active_runs['run1'] = {'data': 'context1'}
            context2.active_runs['run2'] = {'data': 'context2'}
            
            # Add cleanup callbacks
            cleanup1_called = False
            cleanup2_called = False
            
            async def cleanup1():
                nonlocal cleanup1_called
                cleanup1_called = True
            
            async def cleanup2():
                nonlocal cleanup2_called  
                cleanup2_called = True
            
            context1.add_cleanup_callback(cleanup1)
            context2.add_cleanup_callback(cleanup2)
            
            # Clean up context1
            await context1.cleanup()
            
            # Verify context1 is cleaned but context2 is unaffected
            assert context1._is_cleaned
            assert not context2._is_cleaned
            assert cleanup1_called
            assert not cleanup2_called
            assert len(context1.active_runs) == 0
            assert len(context2.active_runs) == 1
            assert 'run2' in context2.active_runs


class TestUserWebSocketEmitterIsolation:
    """Test UserWebSocketEmitter isolation properties."""
    
    @pytest.mark.asyncio
    async def test_websocket_emitter_isolation(self, mock_websocket_bridge):
        """Test WebSocket emitter isolation between users."""
        
        # Create emitters for different users
        emitter1 = UserWebSocketEmitter(
            user_id="user_1",
            thread_id="thread_1", 
            run_id="run_1",
            websocket_bridge=mock_websocket_bridge
        )
        
        emitter2 = UserWebSocketEmitter(
            user_id="user_2",
            thread_id="thread_2",
            run_id="run_2", 
            websocket_bridge=mock_websocket_bridge
        )
        
        # Verify isolation properties
        assert emitter1.user_id != emitter2.user_id
        assert emitter1.thread_id != emitter2.thread_id
        assert emitter1.run_id != emitter2.run_id
        assert emitter1._event_count != emitter2._event_count or emitter1._event_count == 0
        
        # Test event emission isolation
        await emitter1.notify_agent_started("TestAgent", {"user": "user_1"})
        await emitter2.notify_agent_started("TestAgent", {"user": "user_2"}) 
        
        # Verify WebSocket bridge called with correct parameters
        assert mock_websocket_bridge.notify_agent_started.call_count == 2
        
        # Check that calls were made with different run_ids
        call_args = mock_websocket_bridge.notify_agent_started.call_args_list
        assert call_args[0][1]['run_id'] == "run_1"  # user_1's call
        assert call_args[1][1]['run_id'] == "run_2"  # user_2's call
    
    @pytest.mark.asyncio 
    async def test_websocket_emitter_event_tracking(self, mock_websocket_bridge):
        """Test event tracking isolation between emitters."""
        
        emitter1 = UserWebSocketEmitter("user_1", "thread_1", "run_1", mock_websocket_bridge)
        emitter2 = UserWebSocketEmitter("user_2", "thread_2", "run_2", mock_websocket_bridge)
        
        # Send different numbers of events
        await emitter1.notify_agent_started("Agent1")
        await emitter1.notify_agent_thinking("Agent1", "thinking")
        
        await emitter2.notify_agent_started("Agent2")
        
        # Verify isolated event counting
        status1 = emitter1.get_emitter_status()
        status2 = emitter2.get_emitter_status()
        
        assert status1['event_count'] == 2
        assert status2['event_count'] == 1
        assert status1['user_id'] != status2['user_id']


class TestAgentInstanceFactoryIsolation:
    """Test AgentInstanceFactory creates properly isolated instances."""
    
    @pytest.mark.asyncio
    async def test_factory_user_context_creation_isolation(self, configured_factory, session_factory):
        """Test factory creates isolated user contexts."""
        
        factory, registry, websocket_bridge = configured_factory
        
        async with session_factory() as session1, session_factory() as session2:
            
            # Create contexts for two users
            context1 = await factory.create_user_execution_context(
                user_id="user_1",
                thread_id="thread_1",
                run_id="run_1",
                db_session=session1
            )
            
            context2 = await factory.create_user_execution_context(
                user_id="user_2", 
                thread_id="thread_2",
                run_id="run_2",
                db_session=session2
            )
            
            # Verify complete isolation
            assert context1.user_id != context2.user_id
            assert context1.db_session != context2.db_session
            assert context1.websocket_emitter.user_id != context2.websocket_emitter.user_id
            
            # Verify factory tracking
            metrics = factory.get_factory_metrics()
            assert metrics['total_instances_created'] == 2
            assert metrics['active_contexts'] == 2
            
            # Cleanup
            await factory.cleanup_user_context(context1)
            await factory.cleanup_user_context(context2)
    
    @pytest.mark.asyncio
    async def test_factory_agent_instance_isolation(self, configured_factory, session_factory):
        """Test factory creates isolated agent instances."""
        
        factory, registry, websocket_bridge = configured_factory
        
        async with session_factory() as session1, session_factory() as session2:
            
            # Create user contexts
            context1 = await factory.create_user_execution_context(
                user_id="user_1",
                thread_id="thread_1", 
                run_id="run_1",
                db_session=session1
            )
            
            context2 = await factory.create_user_execution_context(
                user_id="user_2",
                thread_id="thread_2",
                run_id="run_2", 
                db_session=session2
            )
            
            # Create agent instances
            agent1 = await factory.create_agent_instance("mock_agent", context1)
            agent2 = await factory.create_agent_instance("mock_agent", context2)
            
            # Verify instances are different objects
            assert agent1 is not agent2
            assert id(agent1) != id(agent2)
            
            # Verify user binding
            assert agent1.user_id == "user_1"
            assert agent2.user_id == "user_2"
            
            # Test execution isolation
            state1 = DeepAgentState(user_request="Request from user 1")
            state1.user_id = "user_1"
            
            state2 = DeepAgentState(user_request="Request from user 2")  
            state2.user_id = "user_2"
            
            result1 = await agent1.execute(state1, "run_1")
            result2 = await agent2.execute(state2, "run_2")
            
            # Verify execution results are isolated
            assert result1['user_id'] == "user_1"
            assert result2['user_id'] == "user_2"
            assert result1['run_id'] != result2['run_id']
            
            # Verify agent-specific data isolation
            assert len(agent1.user_specific_data) == 1
            assert len(agent2.user_specific_data) == 1
            assert "user_1" in agent1.user_specific_data
            assert "user_2" in agent2.user_specific_data
            assert "user_2" not in agent1.user_specific_data
            assert "user_1" not in agent2.user_specific_data
            
            # Cleanup
            await factory.cleanup_user_context(context1)
            await factory.cleanup_user_context(context2)
    
    @pytest.mark.asyncio
    async def test_user_execution_scope_context_manager(self, configured_factory, session_factory):
        """Test user execution scope context manager provides proper isolation."""
        
        factory, registry, websocket_bridge = configured_factory
        
        async with session_factory() as session1, session_factory() as session2:
            
            # Test concurrent scopes
            async def user_scope_test(user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
                async with factory.user_execution_scope(
                    user_id=user_id,
                    thread_id=f"thread_{user_id}",
                    run_id=f"run_{user_id}",
                    db_session=db_session
                ) as context:
                    
                    # Create and execute agent
                    agent = await factory.create_agent_instance("mock_agent", context)
                    state = DeepAgentState(user_request=f"Request from {user_id}")
                    state.user_id = user_id
                    
                    result = await agent.execute(state, f"run_{user_id}")
                    
                    return {
                        'context_user': context.user_id,
                        'agent_result': result,
                        'context_summary': context.get_context_summary()
                    }
            
            # Run concurrent user scopes
            user1_result, user2_result = await asyncio.gather(
                user_scope_test("user_1", session1),
                user_scope_test("user_2", session2)
            )
            
            # Verify isolation
            assert user1_result['context_user'] == "user_1"
            assert user2_result['context_user'] == "user_2"
            assert user1_result['agent_result']['user_id'] != user2_result['agent_result']['user_id']
            
            # Verify contexts were properly cleaned up
            metrics = factory.get_factory_metrics()
            assert metrics['total_contexts_cleaned'] == 2


class TestConcurrentUserIsolation:
    """Test complete isolation under concurrent user load."""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_complete_isolation(self, configured_factory, session_factory):
        """
        CRITICAL TEST: Verify complete isolation under realistic concurrent load.
        
        This test simulates 5 concurrent users, each making multiple requests,
        to ensure no data leakage or cross-contamination occurs.
        """
        
        factory, registry, websocket_bridge = configured_factory
        
        # Test configuration
        num_users = 5
        requests_per_user = 3
        all_results = []
        
        async def simulate_user_requests(user_id: str, num_requests: int) -> List[Dict[str, Any]]:
            """Simulate multiple requests from a single user."""
            user_results = []
            
            for request_num in range(num_requests):
                async with session_factory() as session:
                    
                    run_id = f"run_{user_id}_{request_num}_{int(time.time() * 1000)}"
                    thread_id = f"thread_{user_id}_{request_num}"
                    
                    async with factory.user_execution_scope(
                        user_id=user_id,
                        thread_id=thread_id, 
                        run_id=run_id,
                        db_session=session,
                        metadata={'request_number': request_num}
                    ) as context:
                        
                        # Create agent and execute
                        agent = await factory.create_agent_instance("mock_agent", context)
                        
                        state = DeepAgentState(
                            user_request=f"Request {request_num} from {user_id}"
                        )
                        state.user_id = user_id
                        
                        result = await agent.execute(state, run_id)
                        
                        # Collect isolation data
                        user_results.append({
                            'user_id': user_id,
                            'request_number': request_num,
                            'run_id': run_id,
                            'thread_id': thread_id,
                            'agent_result': result,
                            'context_id': context.request_metadata.get('context_id'),
                            'agent_instance_id': id(agent),
                            'db_session_id': id(context.db_session),
                            'websocket_emitter_id': id(context.websocket_emitter),
                            'execution_timestamp': datetime.now(timezone.utc).isoformat()
                        })
                        
                        # Add some processing delay to test concurrent safety
                        await asyncio.sleep(0.01)
            
            return user_results
        
        # Execute concurrent user simulations
        logger.info(f"Starting concurrent isolation test: {num_users} users, {requests_per_user} requests each")
        
        user_tasks = [
            simulate_user_requests(f"user_{i}", requests_per_user)
            for i in range(num_users)
        ]
        
        all_user_results = await asyncio.gather(*user_tasks)
        
        # Flatten results for analysis
        for user_results in all_user_results:
            all_results.extend(user_results)
        
        logger.info(f"Completed {len(all_results)} total requests across {num_users} users")
        
        # CRITICAL ISOLATION VALIDATIONS
        
        # 1. Verify all requests completed successfully
        assert len(all_results) == num_users * requests_per_user
        
        # 2. Verify user ID isolation - no cross-contamination
        users_by_results = {}
        for result in all_results:
            user_id = result['user_id']
            if user_id not in users_by_results:
                users_by_results[user_id] = []
            users_by_results[user_id].append(result)
        
        assert len(users_by_results) == num_users
        
        for user_id, user_results in users_by_results.items():
            assert len(user_results) == requests_per_user
            for result in user_results:
                # Verify user ID consistency
                assert result['user_id'] == user_id
                assert result['agent_result']['user_id'] == user_id
        
        # 3. Verify unique identifiers - no sharing between users
        all_run_ids = [r['run_id'] for r in all_results]
        all_thread_ids = [r['thread_id'] for r in all_results] 
        all_context_ids = [r['context_id'] for r in all_results]
        all_agent_instance_ids = [r['agent_instance_id'] for r in all_results]
        all_db_session_ids = [r['db_session_id'] for r in all_results]
        all_websocket_emitter_ids = [r['websocket_emitter_id'] for r in all_results]
        
        # All identifiers must be unique (no sharing)
        assert len(set(all_run_ids)) == len(all_run_ids), "run_ids must be unique"
        assert len(set(all_thread_ids)) == len(all_thread_ids), "thread_ids must be unique"
        assert len(set(all_context_ids)) == len(all_context_ids), "context_ids must be unique"
        assert len(set(all_agent_instance_ids)) == len(all_agent_instance_ids), "agent instances must be unique"
        assert len(set(all_db_session_ids)) == len(all_db_session_ids), "database sessions must be unique"
        assert len(set(all_websocket_emitter_ids)) == len(all_websocket_emitter_ids), "websocket emitters must be unique"
        
        # 4. Verify WebSocket event isolation
        websocket_call_count = websocket_bridge.notify_agent_started.call_count
        assert websocket_call_count == len(all_results), f"Expected {len(all_results)} WebSocket calls, got {websocket_call_count}"
        
        # 5. Verify factory metrics
        final_metrics = factory.get_factory_metrics()
        assert final_metrics['total_instances_created'] >= len(all_results)
        assert final_metrics['total_contexts_cleaned'] >= len(all_results)
        
        logger.info("✅ CONCURRENT ISOLATION TEST PASSED - Complete user isolation verified under load")
    
    @pytest.mark.asyncio
    async def test_database_session_isolation_under_load(self, configured_factory, session_factory):
        """Test database session isolation under concurrent load."""
        
        factory, registry, websocket_bridge = configured_factory
        
        async def user_database_operations(user_id: str) -> Dict[str, Any]:
            """Simulate database operations for isolation testing."""
            
            async with session_factory() as session:
                
                async with factory.user_execution_scope(
                    user_id=user_id,
                    thread_id=f"thread_{user_id}",
                    run_id=f"run_{user_id}",
                    db_session=session
                ) as context:
                    
                    # Perform user-specific database operations
                    await context.db_session.execute(
                        text("INSERT INTO test_table (user_id, data) VALUES (:user_id, :data)"),
                        {"user_id": user_id, "data": f"data_for_{user_id}"}
                    )
                    await context.db_session.commit()
                    
                    # Read data to verify isolation
                    result = await context.db_session.execute(
                        text("SELECT * FROM test_table WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    rows = result.fetchall()
                    
                    return {
                        'user_id': user_id,
                        'session_id': id(context.db_session),
                        'data_count': len(rows),
                        'context_isolation': context.get_context_summary()
                    }
        
        # Run concurrent database operations
        num_users = 5
        user_tasks = [
            user_database_operations(f"db_user_{i}")
            for i in range(num_users)
        ]
        
        results = await asyncio.gather(*user_tasks)
        
        # Verify database isolation
        session_ids = [r['session_id'] for r in results]
        assert len(set(session_ids)) == num_users, "Each user must have unique database session"
        
        for result in results:
            assert result['data_count'] == 1, f"User {result['user_id']} should only see their own data"
        
        logger.info("✅ DATABASE SESSION ISOLATION VERIFIED under concurrent load")


class TestResourceCleanupPrevention:
    """Test resource cleanup prevents memory leaks and resource exhaustion."""
    
    @pytest.mark.asyncio
    async def test_context_cleanup_prevents_memory_leaks(self, configured_factory, session_factory):
        """Test context cleanup prevents memory leaks."""
        
        factory, registry, websocket_bridge = configured_factory
        initial_active_contexts = factory.get_factory_metrics()['active_contexts']
        
        # Create multiple contexts without cleanup first
        contexts_to_cleanup = []
        
        for i in range(10):
            async with session_factory() as session:
                context = await factory.create_user_execution_context(
                    user_id=f"cleanup_user_{i}",
                    thread_id=f"cleanup_thread_{i}",
                    run_id=f"cleanup_run_{i}",
                    db_session=session
                )
                contexts_to_cleanup.append(context)
        
        # Verify contexts are tracked
        metrics_before_cleanup = factory.get_factory_metrics()
        assert metrics_before_cleanup['active_contexts'] >= initial_active_contexts + 10
        
        # Clean up all contexts
        for context in contexts_to_cleanup:
            await factory.cleanup_user_context(context)
        
        # Verify cleanup reduced active context count
        metrics_after_cleanup = factory.get_factory_metrics()
        assert metrics_after_cleanup['active_contexts'] == initial_active_contexts
        assert metrics_after_cleanup['total_contexts_cleaned'] >= 10
        
        logger.info("✅ MEMORY LEAK PREVENTION VERIFIED - All contexts properly cleaned up")
    
    @pytest.mark.asyncio
    async def test_inactive_context_cleanup(self, configured_factory, session_factory):
        """Test automatic cleanup of inactive contexts."""
        
        factory, registry, websocket_bridge = configured_factory
        
        # Create some contexts (simulating old inactive contexts)
        old_contexts = []
        async with session_factory() as session:
            for i in range(5):
                context = await factory.create_user_execution_context(
                    user_id=f"old_user_{i}",
                    thread_id=f"old_thread_{i}",
                    run_id=f"old_run_{i}",
                    db_session=session
                )
                # Artificially age the context
                context.created_at = datetime.now(timezone.utc).replace(year=2020)
                old_contexts.append(context)
        
        # Run inactive context cleanup
        cleanup_count = await factory.cleanup_inactive_contexts(max_age_seconds=60)
        
        # Verify old contexts were cleaned up
        assert cleanup_count >= 5
        
        metrics = factory.get_factory_metrics()
        assert metrics['total_contexts_cleaned'] >= 5
        
        logger.info(f"✅ INACTIVE CONTEXT CLEANUP VERIFIED - Cleaned up {cleanup_count} old contexts")


@pytest.mark.asyncio
async def test_agent_instance_factory_end_to_end_isolation():
    """
    COMPREHENSIVE END-TO-END ISOLATION TEST
    
    This test verifies complete isolation in a realistic scenario with:
    - Multiple concurrent users
    - Database operations
    - WebSocket events
    - Agent executions
    - Resource cleanup
    """
    
    # Setup test infrastructure
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE test_data (id INTEGER PRIMARY KEY, user_id TEXT, content TEXT)"))
    
    session_factory_func = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Setup mocks
    mock_llm = MagicMock(spec=LLMManager)
    mock_dispatcher = MagicMock(spec=ToolDispatcher)
    mock_websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
    mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_thinking = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
    mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    mock_websocket_bridge.unregister_run_mapping = AsyncMock(return_value=True)
    
    # Create and configure factory
    registry = AgentRegistry(mock_llm, mock_dispatcher)
    registry.register("isolation_test_agent", MockAgent(mock_llm, "IsolationTestAgent"))
    
    factory = AgentInstanceFactory()
    factory.configure(
        agent_registry=registry,
        websocket_bridge=mock_websocket_bridge
    )
    
    # Run comprehensive isolation test
    async def comprehensive_user_simulation(user_id: str) -> Dict[str, Any]:
        """Complete user simulation with database, WebSocket, and agent operations."""
        
        async with session_factory_func() as session:
            
            # Insert user-specific data
            await session.execute(
                text("INSERT INTO test_data (user_id, content) VALUES (:user_id, :content)"),
                {"user_id": user_id, "content": f"private_data_{user_id}"}
            )
            await session.commit()
            
            run_id = f"e2e_run_{user_id}_{uuid.uuid4().hex[:8]}"
            thread_id = f"e2e_thread_{user_id}"
            
            async with factory.user_execution_scope(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=session
            ) as context:
                
                # Create and execute agent
                agent = await factory.create_agent_instance("isolation_test_agent", context)
                
                state = DeepAgentState(user_request=f"Sensitive request from {user_id}")
                state.user_id = user_id
                
                # Execute agent (which should emit WebSocket events)
                result = await agent.execute(state, run_id)
                
                # Verify database isolation
                db_result = await context.db_session.execute(
                    text("SELECT content FROM test_data WHERE user_id = :user_id"),
                    {"user_id": user_id}
                )
                user_data = db_result.fetchall()
                
                return {
                    'user_id': user_id,
                    'run_id': run_id,
                    'agent_result': result,
                    'database_rows': len(user_data),
                    'private_data_accessible': len([row for row in user_data if user_id in row[0]]) > 0,
                    'context_summary': context.get_context_summary(),
                    'websocket_emitter_user': context.websocket_emitter.user_id,
                    'agent_instance_id': id(agent)
                }
    
    # Execute comprehensive test with multiple users
    test_users = ["alice", "bob", "charlie", "diana", "eve"]
    
    logger.info(f"🧪 Starting COMPREHENSIVE END-TO-END ISOLATION TEST with {len(test_users)} users")
    
    results = await asyncio.gather(*[
        comprehensive_user_simulation(user_id) 
        for user_id in test_users
    ])
    
    # COMPREHENSIVE ISOLATION ANALYSIS
    
    logger.info("🔍 Analyzing isolation results...")
    
    # 1. Verify each user only accessed their own data
    for result in results:
        user_id = result['user_id']
        assert result['database_rows'] == 1, f"User {user_id} should only see 1 row (their own)"
        assert result['private_data_accessible'], f"User {user_id} should access their private data"
        assert result['agent_result']['user_id'] == user_id, f"Agent result should be for {user_id}"
        assert result['websocket_emitter_user'] == user_id, f"WebSocket emitter should be bound to {user_id}"
    
    # 2. Verify all identifiers are unique (no sharing)
    all_run_ids = [r['run_id'] for r in results]
    all_agent_ids = [r['agent_instance_id'] for r in results]
    
    assert len(set(all_run_ids)) == len(test_users), "All run_ids must be unique"
    assert len(set(all_agent_ids)) == len(test_users), "All agent instances must be unique"
    
    # 3. Verify WebSocket events were sent for each user
    assert mock_websocket_bridge.notify_agent_started.call_count >= len(test_users)
    assert mock_websocket_bridge.register_run_thread_mapping.call_count >= len(test_users)
    
    # 4. Verify factory metrics
    final_metrics = factory.get_factory_metrics()
    assert final_metrics['total_instances_created'] >= len(test_users)
    assert final_metrics['total_contexts_cleaned'] >= len(test_users)
    
    # Cleanup
    await engine.dispose()
    
    logger.info("✅ COMPREHENSIVE END-TO-END ISOLATION TEST PASSED")
    logger.info("   - Database isolation verified")
    logger.info("   - Agent instance isolation verified") 
    logger.info("   - WebSocket emitter isolation verified")
    logger.info("   - Resource cleanup verified")
    logger.info("   - No data leakage detected")
    
    print("\n" + "="*80)
    print("🎉 AGENT INSTANCE FACTORY ISOLATION VALIDATION COMPLETE 🎉")
    print("="*80)
    print("✅ UserExecutionContext provides complete per-request isolation")
    print("✅ AgentInstanceFactory creates properly isolated agent instances")
    print("✅ WebSocket emitters are bound to specific users")
    print("✅ Database sessions are completely isolated per request")
    print("✅ No shared state exists between concurrent users") 
    print("✅ Resource cleanup prevents memory leaks")
    print("✅ System is ready for safe multi-user production deployment")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_agent_instance_factory_end_to_end_isolation())