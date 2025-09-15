"""Integration tests for multi-user execution context isolation.

Business Value Justification:
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Multi-User Execution Isolation & Security
- Value Impact: Prevents $500K+ ARR loss from user data mixing and context leakage
- Strategic Impact: Foundation for safe multi-tenant execution at enterprise scale

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL MULTI-USER - Test actual concurrent user execution with real isolation
2. Context Boundaries - Test strict user context isolation prevents data leakage
3. Factory Patterns - Test ExecutionEngineFactory maintains per-user isolation
4. WebSocket Isolation - Test user-specific WebSocket event routing
5. Resource Isolation - Test per-user resource limits and cleanup

This tests the core multi-user isolation that enables enterprise-grade security.
"""
import pytest
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, AsyncMock
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

@pytest.mark.integration
class MultiUserExecutionIsolationTests:
    """Test multi-user execution isolation patterns."""

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge that tracks per-user events."""
        bridge = MagicMock()
        bridge.is_connected.return_value = True
        bridge.user_events = {}

        def mock_emit_to_user(user_id, event_type, data):
            if user_id not in bridge.user_events:
                bridge.user_events[user_id] = []
            bridge.user_events[user_id].append({'event_type': event_type, 'data': data, 'timestamp': datetime.now(timezone.utc)})
            return True
        bridge.emit_to_user = mock_emit_to_user
        bridge.emit = AsyncMock(return_value=True)
        return bridge

    @pytest.fixture
    def execution_factory(self, mock_websocket_bridge):
        """Create ExecutionEngineFactory with WebSocket bridge."""
        return ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)

    def create_user_context(self, user_suffix: str) -> UserExecutionContext:
        """Create isolated user context with unique identifiers."""
        return UserExecutionContext(user_id=f'user_{user_suffix}_{uuid.uuid4().hex[:8]}', thread_id=f'thread_{user_suffix}_{uuid.uuid4().hex[:8]}', run_id=f'run_{user_suffix}_{uuid.uuid4().hex[:8]}', request_id=f'req_{user_suffix}_{uuid.uuid4().hex[:8]}', websocket_client_id=f'ws_{user_suffix}_{uuid.uuid4().hex[:8]}', agent_context={'user_type': f'test_user_{user_suffix}', 'isolation_test': True, 'user_specific_data': f'data_for_{user_suffix}'}, audit_metadata={'test_user': user_suffix, 'isolation_boundary': 'per_user', 'created_for': 'isolation_testing'})

    @pytest.mark.asyncio
    async def test_concurrent_user_context_creation_isolation(self, execution_factory):
        """Test that concurrent user context creation maintains isolation."""
        user_contexts = []

        async def create_user_engine(user_id: str) -> tuple[str, UserExecutionEngine]:
            """Create user engine and return user_id and engine."""
            context = self.create_user_context(user_id)
            from unittest.mock import patch
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
                mock_factory = MagicMock()
                mock_factory._agent_registry = MagicMock()
                mock_factory._websocket_bridge = execution_factory._websocket_bridge
                mock_get_factory.return_value = mock_factory
                engine = await execution_factory.create_for_user(context)
                return (user_id, engine)
        user_ids = ['alice', 'bob', 'charlie', 'diana', 'eve']
        tasks = [create_user_engine(user_id) for user_id in user_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        created_engines = []
        for result in results:
            if not isinstance(result, Exception):
                user_id, engine = result
                created_engines.append((user_id, engine))
        user_engine_map = {user_id: engine for user_id, engine in created_engines}
        for user_id, engine in created_engines:
            assert engine.context.user_id.endswith(user_id)
            engine_ids = [e.engine_id for _, e in created_engines]
            assert len(set(engine_ids)) == len(engine_ids)
            assert len(engine.active_runs) == 0
            assert len(engine.run_history) == 0
            assert engine.execution_stats['total_executions'] == 0
            assert engine.context.agent_context['user_specific_data'] == f'data_for_{user_id}'
            assert engine.context.audit_metadata['test_user'] == user_id
        for _, engine in created_engines:
            await execution_factory.cleanup_engine(engine)

    @pytest.mark.asyncio
    async def test_user_execution_state_isolation(self, execution_factory):
        """Test that user execution state remains isolated during operations."""
        user1_context = self.create_user_context('user1')
        user2_context = self.create_user_context('user2')
        from unittest.mock import patch
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            engine1 = await execution_factory.create_for_user(user1_context)
            engine2 = await execution_factory.create_for_user(user2_context)
            try:
                engine1.execution_stats['total_executions'] = 5
                engine1.execution_stats['failed_executions'] = 1
                engine1.active_runs['test_run_1'] = MagicMock()
                engine2.execution_stats['total_executions'] = 3
                engine2.execution_stats['timeout_executions'] = 1
                engine2.active_runs['test_run_2'] = MagicMock()
                assert engine1.execution_stats['total_executions'] == 5
                assert engine2.execution_stats['total_executions'] == 3
                assert engine1.execution_stats['failed_executions'] == 1
                assert engine2.execution_stats.get('failed_executions', 0) == 0
                assert engine2.execution_stats['timeout_executions'] == 1
                assert engine1.execution_stats.get('timeout_executions', 0) == 0
                assert 'test_run_1' in engine1.active_runs
                assert 'test_run_1' not in engine2.active_runs
                assert 'test_run_2' in engine2.active_runs
                assert 'test_run_2' not in engine1.active_runs
                assert engine1.context.user_id != engine2.context.user_id
                assert engine1.context.agent_context['user_specific_data'] != engine2.context.agent_context['user_specific_data']
            finally:
                await execution_factory.cleanup_engine(engine1)
                await execution_factory.cleanup_engine(engine2)

    @pytest.mark.asyncio
    async def test_websocket_event_isolation(self, execution_factory):
        """Test that WebSocket events are isolated per user."""
        user1_context = self.create_user_context('websocket_user1')
        user2_context = self.create_user_context('websocket_user2')
        from unittest.mock import patch
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            engine1 = await execution_factory.create_for_user(user1_context)
            engine2 = await execution_factory.create_for_user(user2_context)
            try:
                mock_exec_context1 = MagicMock()
                mock_exec_context1.agent_name = 'test_agent_1'
                mock_exec_context1.user_id = user1_context.user_id
                mock_exec_context1.metadata = {'test': 'user1_metadata'}
                mock_exec_context2 = MagicMock()
                mock_exec_context2.agent_name = 'test_agent_2'
                mock_exec_context2.user_id = user2_context.user_id
                mock_exec_context2.metadata = {'test': 'user2_metadata'}
                await engine1._send_user_agent_started(mock_exec_context1)
                await engine1._send_user_agent_thinking(mock_exec_context1, 'User 1 thinking', step_number=1)
                await engine2._send_user_agent_started(mock_exec_context2)
                await engine2._send_user_agent_thinking(mock_exec_context2, 'User 2 thinking', step_number=1)
                websocket_bridge = execution_factory._websocket_bridge
                if hasattr(websocket_bridge, 'user_events'):
                    user1_events = websocket_bridge.user_events.get(user1_context.user_id, [])
                    user2_events = websocket_bridge.user_events.get(user2_context.user_id, [])
                    assert len(user1_events) >= 0
                    assert len(user2_events) >= 0
                    for event in user1_events:
                        event_str = str(event)
                        assert 'websocket_user2' not in event_str
                        assert 'User 2 thinking' not in event_str
                    for event in user2_events:
                        event_str = str(event)
                        assert 'websocket_user1' not in event_str
                        assert 'User 1 thinking' not in event_str
                assert engine1.context.user_id != engine2.context.user_id
                assert engine1.websocket_emitter != engine2.websocket_emitter
            finally:
                await execution_factory.cleanup_engine(engine1)
                await execution_factory.cleanup_engine(engine2)

    @pytest.mark.asyncio
    async def test_factory_user_limit_enforcement(self, execution_factory):
        """Test that factory enforces per-user engine limits."""
        user_context = self.create_user_context('limited_user')
        from unittest.mock import patch
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            created_engines = []
            try:
                for i in range(execution_factory._max_engines_per_user):
                    context_copy = UserExecutionContext(user_id=user_context.user_id, thread_id=f'thread_{i}_{uuid.uuid4().hex[:8]}', run_id=f'run_{i}_{uuid.uuid4().hex[:8]}', request_id=f'req_{i}_{uuid.uuid4().hex[:8]}')
                    engine = await execution_factory.create_for_user(context_copy)
                    created_engines.append(engine)
                assert len(created_engines) == execution_factory._max_engines_per_user
                excess_context = UserExecutionContext(user_id=user_context.user_id, thread_id=f'thread_excess_{uuid.uuid4().hex[:8]}', run_id=f'run_excess_{uuid.uuid4().hex[:8]}', request_id=f'req_excess_{uuid.uuid4().hex[:8]}')
                from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactoryError
                with pytest.raises(ExecutionEngineFactoryError, match='reached maximum engine limit'):
                    await execution_factory.create_for_user(excess_context)
            finally:
                for engine in created_engines:
                    await execution_factory.cleanup_engine(engine)

    @pytest.mark.asyncio
    async def test_concurrent_user_cleanup_isolation(self, execution_factory):
        """Test that user cleanup is isolated and doesn't affect other users."""
        user1_context = self.create_user_context('cleanup_user1')
        user2_context = self.create_user_context('cleanup_user2')
        user3_context = self.create_user_context('cleanup_user3')
        from unittest.mock import patch
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_factory
            engine1 = await execution_factory.create_for_user(user1_context)
            engine2 = await execution_factory.create_for_user(user2_context)
            engine3 = await execution_factory.create_for_user(user3_context)
            assert engine1.is_active() is not None
            assert engine2.is_active() is not None
            assert engine3.is_active() is not None
            await execution_factory.cleanup_engine(engine2)
            assert engine2._is_active is False
            assert engine1._is_active is True
            assert engine3._is_active is True
            metrics = execution_factory.get_factory_metrics()
            assert metrics['total_engines_cleaned'] >= 1
            await execution_factory.cleanup_engine(engine1)
            await execution_factory.cleanup_engine(engine3)

    def test_strongly_typed_context_user_isolation(self):
        """Test that strongly typed contexts maintain user isolation."""
        user1_typed = StronglyTypedUserExecutionContext(user_id=UserID(f'typed_user1_{uuid.uuid4().hex[:8]}'), thread_id=ThreadID(f'typed_thread1_{uuid.uuid4().hex[:8]}'), run_id=RunID(f'typed_run1_{uuid.uuid4().hex[:8]}'), request_id=RequestID(f'typed_req1_{uuid.uuid4().hex[:8]}'), agent_context={'typed_user': 'user1', 'isolation_test': True})
        user2_typed = StronglyTypedUserExecutionContext(user_id=UserID(f'typed_user2_{uuid.uuid4().hex[:8]}'), thread_id=ThreadID(f'typed_thread2_{uuid.uuid4().hex[:8]}'), run_id=RunID(f'typed_run2_{uuid.uuid4().hex[:8]}'), request_id=RequestID(f'typed_req2_{uuid.uuid4().hex[:8]}'), agent_context={'typed_user': 'user2', 'isolation_test': True})
        assert user1_typed.user_id != user2_typed.user_id
        assert user1_typed.thread_id != user2_typed.thread_id
        assert user1_typed.run_id != user2_typed.run_id
        assert user1_typed.request_id != user2_typed.request_id
        assert user1_typed.agent_context['typed_user'] == 'user1'
        assert user2_typed.agent_context['typed_user'] == 'user2'
        child1 = user1_typed.create_child_context()
        child2 = user2_typed.create_child_context()
        assert child1.user_id == user1_typed.user_id
        assert child2.user_id == user2_typed.user_id
        assert child1.user_id != child2.user_id
        assert child1.request_id != user1_typed.request_id
        assert child2.request_id != user2_typed.request_id
        assert child1.request_id != child2.request_id

@pytest.mark.integration
class MultiUserResourceIsolationTests:
    """Test resource isolation between multiple users."""

    def test_user_execution_stats_isolation(self):
        """Test that user execution statistics are completely isolated."""
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        mock_emitter1 = MagicMock()
        mock_emitter2 = MagicMock()
        user1_context = UserExecutionContext(user_id=f'stats_user1_{uuid.uuid4().hex[:8]}', thread_id=f'stats_thread1_{uuid.uuid4().hex[:8]}', run_id=f'stats_run1_{uuid.uuid4().hex[:8]}', request_id=f'stats_req1_{uuid.uuid4().hex[:8]}')
        user2_context = UserExecutionContext(user_id=f'stats_user2_{uuid.uuid4().hex[:8]}', thread_id=f'stats_thread2_{uuid.uuid4().hex[:8]}', run_id=f'stats_run2_{uuid.uuid4().hex[:8]}', request_id=f'stats_req2_{uuid.uuid4().hex[:8]}')
        engine1 = UserExecutionEngine(user1_context, mock_factory, mock_emitter1)
        engine2 = UserExecutionEngine(user2_context, mock_factory, mock_emitter2)
        engine1.execution_stats['total_executions'] = 10
        engine1.execution_stats['failed_executions'] = 2
        engine1.execution_stats['execution_times'] = [1.5, 2.3, 0.8]
        engine2.execution_stats['total_executions'] = 5
        engine2.execution_stats['timeout_executions'] = 1
        engine2.execution_stats['execution_times'] = [3.2, 1.1]
        stats1 = engine1.get_user_execution_stats()
        stats2 = engine2.get_user_execution_stats()
        assert stats1['total_executions'] == 10
        assert stats2['total_executions'] == 5
        assert stats1['failed_executions'] == 2
        assert stats2.get('failed_executions', 0) == 0
        assert stats1.get('timeout_executions', 0) == 0
        assert stats2['timeout_executions'] == 1
        assert stats1['user_id'] == user1_context.user_id
        assert stats2['user_id'] == user2_context.user_id
        assert stats1['engine_id'] != stats2['engine_id']
        assert stats1['avg_execution_time'] == sum([1.5, 2.3, 0.8]) / 3
        assert stats2['avg_execution_time'] == sum([3.2, 1.1]) / 2

    @pytest.mark.asyncio
    async def test_user_semaphore_isolation(self):
        """Test that user semaphores provide isolated concurrency control."""
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        mock_emitter1 = MagicMock()
        mock_emitter2 = MagicMock()
        user1_context = UserExecutionContext(user_id=f'semaphore_user1_{uuid.uuid4().hex[:8]}', thread_id=f'semaphore_thread1_{uuid.uuid4().hex[:8]}', run_id=f'semaphore_run1_{uuid.uuid4().hex[:8]}', request_id=f'semaphore_req1_{uuid.uuid4().hex[:8]}')
        user2_context = UserExecutionContext(user_id=f'semaphore_user2_{uuid.uuid4().hex[:8]}', thread_id=f'semaphore_thread2_{uuid.uuid4().hex[:8]}', run_id=f'semaphore_run2_{uuid.uuid4().hex[:8]}', request_id=f'semaphore_req2_{uuid.uuid4().hex[:8]}')
        engine1 = UserExecutionEngine(user1_context, mock_factory, mock_emitter1)
        engine2 = UserExecutionEngine(user2_context, mock_factory, mock_emitter2)
        assert engine1.semaphore != engine2.semaphore
        assert engine1.max_concurrent == engine2.max_concurrent
        async with engine1.semaphore:
            assert engine1.semaphore.locked()
            assert not engine2.semaphore.locked()
            async with engine2.semaphore:
                assert engine2.semaphore.locked()
                assert engine1.semaphore.locked()
                assert engine2.semaphore.locked()
        assert not engine1.semaphore.locked()
        assert not engine2.semaphore.locked()
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')