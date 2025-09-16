"""Unit tests for execution engine lifecycle and resource management.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Resource Management & System Stability
- Value Impact: Prevents memory leaks and resource exhaustion that cause system failures
- Strategic Impact: Essential for production stability and multi-tenant resource isolation

CRITICAL REQUIREMENTS per CLAUDE.md:
1. REAL LIFECYCLE - Test actual engine lifecycle with real resource management
2. Memory Management - Test proper cleanup prevents memory leaks
3. Factory Patterns - Test ExecutionEngineFactory lifecycle management
4. Timeout Handling - Test engine timeout and cleanup mechanisms
5. Resource Limits - Test per-user resource limits and enforcement

This tests the critical lifecycle management that ensures production stability.
"""
import pytest
import asyncio
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, ExecutionEngineFactoryError
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext, AgentExecutionResult, PipelineStep
from netra_backend.app.schemas.agent_models import DeepAgentState

class ExecutionEngineLifecycleTests:
    """Test execution engine lifecycle management."""

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge."""
        bridge = MagicMock()
        bridge.is_connected.return_value = True
        bridge.emit = AsyncMock(return_value=True)
        return bridge

    @pytest.fixture
    def mock_agent_factory(self, mock_websocket_bridge):
        """Create mock agent factory."""
        factory = MagicMock()
        factory._agent_registry = MagicMock()
        factory._websocket_bridge = mock_websocket_bridge
        factory.create_agent_instance = AsyncMock()
        return factory

    @pytest.fixture
    def user_context(self) -> UserExecutionContext:
        """Create user execution context for testing."""
        return UserExecutionContext(user_id=f'lifecycle_user_{uuid.uuid4().hex[:12]}', thread_id=f'lifecycle_thread_{uuid.uuid4().hex[:12]}', run_id=f'lifecycle_run_{uuid.uuid4().hex[:12]}', request_id=f'lifecycle_req_{uuid.uuid4().hex[:12]}', websocket_client_id=f'lifecycle_ws_{uuid.uuid4().hex[:12]}')

    @pytest.fixture
    def mock_websocket_emitter(self):
        """Create mock WebSocket emitter."""
        emitter = MagicMock()
        emitter.notify_agent_started = AsyncMock(return_value=True)
        emitter.notify_agent_thinking = AsyncMock(return_value=True)
        emitter.notify_agent_completed = AsyncMock(return_value=True)
        emitter.cleanup = AsyncMock()
        return emitter

    def test_execution_engine_initialization_lifecycle(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test execution engine initialization and initial state."""
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_emitter)
        assert engine._is_active is True
        assert engine.is_active() is False
        assert isinstance(engine.created_at, datetime)
        assert engine.created_at.tzinfo is not None
        assert len(engine.active_runs) == 0
        assert len(engine.run_history) == 0
        assert engine.execution_stats['total_executions'] == 0
        assert engine.execution_stats['concurrent_executions'] == 0
        assert engine.engine_id.startswith(f'user_engine_{user_context.user_id}')
        assert user_context.run_id in engine.engine_id
        assert engine.context == user_context
        assert engine.get_user_context() == user_context

    @pytest.mark.asyncio
    async def test_execution_engine_cleanup_lifecycle(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test execution engine cleanup and resource deallocation."""
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_emitter)
        engine.execution_stats['total_executions'] = 5
        engine.execution_stats['failed_executions'] = 1
        engine.active_runs['test_run'] = MagicMock()
        engine.run_history.append(MagicMock())
        assert engine._is_active is True
        assert len(engine.active_runs) == 1
        assert len(engine.run_history) == 1
        await engine.cleanup()
        assert engine._is_active is False
        assert engine.is_active() is False
        assert len(engine.active_runs) == 0
        assert len(engine.run_history) == 0
        assert len(engine.execution_stats) == 0
        mock_websocket_emitter.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_execution_engine_multiple_cleanup_calls(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test that multiple cleanup calls are handled gracefully."""
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_emitter)
        await engine.cleanup()
        assert engine._is_active is False
        await engine.cleanup()
        assert engine._is_active is False
        mock_websocket_emitter.cleanup.assert_called()

    @pytest.mark.asyncio
    async def test_execution_engine_active_runs_tracking(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test that active runs are tracked correctly during lifecycle."""
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_emitter)
        exec_context = AgentExecutionContext(user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id, request_id=user_context.request_id, agent_name='test_agent', step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
        execution_id = f'exec_{uuid.uuid4().hex[:8]}'
        exec_context.execution_id = execution_id
        engine.active_runs[execution_id] = exec_context
        engine.execution_stats['concurrent_executions'] += 1
        assert len(engine.active_runs) == 1
        assert execution_id in engine.active_runs
        assert engine.is_active() is True
        assert engine.execution_stats['concurrent_executions'] == 1
        engine.active_runs.pop(execution_id)
        engine.execution_stats['concurrent_executions'] -= 1
        assert len(engine.active_runs) == 0
        assert execution_id not in engine.active_runs
        assert engine.is_active() is False
        assert engine.execution_stats['concurrent_executions'] == 0

    def test_execution_engine_history_size_limit(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test that run history respects size limits."""
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_emitter)
        max_history = UserExecutionEngine.MAX_HISTORY_SIZE
        for i in range(max_history + 10):
            mock_result = MagicMock()
            mock_result.agent_name = f'agent_{i}'
            mock_result.success = True
            mock_result.execution_time = 1.0
            engine._update_user_history(mock_result)
        assert len(engine.run_history) == max_history
        first_result = engine.run_history[0]
        last_result = engine.run_history[-1]
        assert int(first_result.agent_name.split('_')[1]) >= 10
        assert last_result.agent_name == f'agent_{max_history + 9}'

    def test_execution_engine_stats_calculations(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test execution statistics calculations during lifecycle."""
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_agent_factory, websocket_emitter=mock_websocket_emitter)
        engine.execution_stats['queue_wait_times'] = [0.5, 1.2, 0.8, 2.1]
        engine.execution_stats['execution_times'] = [2.3, 1.5, 3.2, 1.8, 2.7]
        engine.execution_stats['total_executions'] = 5
        engine.execution_stats['failed_executions'] = 1
        stats = engine.get_user_execution_stats()
        expected_avg_queue_wait = sum([0.5, 1.2, 0.8, 2.1]) / 4
        expected_max_queue_wait = max([0.5, 1.2, 0.8, 2.1])
        expected_avg_execution_time = sum([2.3, 1.5, 3.2, 1.8, 2.7]) / 5
        expected_max_execution_time = max([2.3, 1.5, 3.2, 1.8, 2.7])
        assert stats['avg_queue_wait_time'] == expected_avg_queue_wait
        assert stats['max_queue_wait_time'] == expected_max_queue_wait
        assert stats['avg_execution_time'] == expected_avg_execution_time
        assert stats['max_execution_time'] == expected_max_execution_time
        assert stats['user_id'] == user_context.user_id
        assert stats['engine_id'] == engine.engine_id
        assert stats['total_executions'] == 5
        assert stats['failed_executions'] == 1
        assert stats['is_active'] is True

class ExecutionEngineFactoryLifecycleTests:
    """Test ExecutionEngineFactory lifecycle management."""

    @pytest.fixture
    def mock_websocket_bridge(self):
        """Create mock WebSocket bridge."""
        bridge = MagicMock()
        bridge.is_connected.return_value = True
        bridge.emit = AsyncMock(return_value=True)
        return bridge

    @pytest.fixture
    def execution_factory(self, mock_websocket_bridge):
        """Create ExecutionEngineFactory for testing."""
        return ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)

    def test_factory_initialization_lifecycle(self, mock_websocket_bridge):
        """Test factory initialization and initial state."""
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        assert factory._websocket_bridge == mock_websocket_bridge
        assert len(factory._active_engines) == 0
        assert factory._cleanup_task is None
        assert not factory._shutdown_event.is_set()
        metrics = factory.get_factory_metrics()
        assert metrics['total_engines_created'] == 0
        assert metrics['total_engines_cleaned'] == 0
        assert metrics['active_engines_count'] == 0
        assert metrics['creation_errors'] == 0
        assert metrics['cleanup_errors'] == 0
        assert factory._max_engines_per_user == 2
        assert factory._engine_timeout_seconds == 300
        assert factory._cleanup_interval == 60

    @pytest.mark.asyncio
    async def test_factory_engine_creation_lifecycle(self, execution_factory):
        """Test factory engine creation and lifecycle tracking."""
        user_context = UserExecutionContext(user_id=f'factory_user_{uuid.uuid4().hex[:12]}', thread_id=f'factory_thread_{uuid.uuid4().hex[:12]}', run_id=f'factory_run_{uuid.uuid4().hex[:12]}', request_id=f'factory_req_{uuid.uuid4().hex[:12]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            initial_metrics = execution_factory.get_factory_metrics()
            assert initial_metrics['active_engines_count'] == 0
            engine = await execution_factory.create_for_user(user_context)
            assert engine is not None
            assert isinstance(engine, UserExecutionEngine)
            assert len(execution_factory._active_engines) == 1
            updated_metrics = execution_factory.get_factory_metrics()
            assert updated_metrics['total_engines_created'] == 1
            assert updated_metrics['active_engines_count'] == 1
            assert execution_factory._cleanup_task is not None
            assert not execution_factory._cleanup_task.done()
            await execution_factory.cleanup_engine(engine)
            assert len(execution_factory._active_engines) == 0
            final_metrics = execution_factory.get_factory_metrics()
            assert final_metrics['total_engines_cleaned'] == 1
            assert final_metrics['active_engines_count'] == 0

    @pytest.mark.asyncio
    async def test_factory_user_execution_scope_lifecycle(self, execution_factory):
        """Test factory user execution scope context manager lifecycle."""
        user_context = UserExecutionContext(user_id=f'scope_user_{uuid.uuid4().hex[:12]}', thread_id=f'scope_thread_{uuid.uuid4().hex[:12]}', run_id=f'scope_run_{uuid.uuid4().hex[:12]}', request_id=f'scope_req_{uuid.uuid4().hex[:12]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine_created = None
            engine_active_during_scope = None
            async with execution_factory.user_execution_scope(user_context) as engine:
                engine_created = engine
                engine_active_during_scope = engine._is_active
                assert engine is not None
                assert engine._is_active is True
                assert len(execution_factory._active_engines) == 1
            assert engine_created is not None
            assert engine_active_during_scope is True
            await asyncio.sleep(0.1)
            assert len(execution_factory._active_engines) == 0

    @pytest.mark.asyncio
    async def test_factory_cleanup_loop_lifecycle(self, execution_factory):
        """Test factory background cleanup loop lifecycle."""
        user_context = UserExecutionContext(user_id=f'cleanup_user_{uuid.uuid4().hex[:12]}', thread_id=f'cleanup_thread_{uuid.uuid4().hex[:12]}', run_id=f'cleanup_run_{uuid.uuid4().hex[:12]}', request_id=f'cleanup_req_{uuid.uuid4().hex[:12]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine = await execution_factory.create_for_user(user_context)
            assert execution_factory._cleanup_task is not None
            assert not execution_factory._cleanup_task.done()
            engine._is_active = False
            await asyncio.sleep(0.2)
            assert not execution_factory._cleanup_task.done()
            await execution_factory.cleanup_engine(engine)

    @pytest.mark.asyncio
    async def test_factory_shutdown_lifecycle(self, execution_factory):
        """Test factory shutdown and resource cleanup lifecycle."""
        user_context = UserExecutionContext(user_id=f'shutdown_user_{uuid.uuid4().hex[:12]}', thread_id=f'shutdown_thread_{uuid.uuid4().hex[:12]}', run_id=f'shutdown_run_{uuid.uuid4().hex[:12]}', request_id=f'shutdown_req_{uuid.uuid4().hex[:12]}')
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            engine1 = await execution_factory.create_for_user(user_context)
            user_context2 = UserExecutionContext(user_id=f'shutdown_user2_{uuid.uuid4().hex[:12]}', thread_id=f'shutdown_thread2_{uuid.uuid4().hex[:12]}', run_id=f'shutdown_run2_{uuid.uuid4().hex[:12]}', request_id=f'shutdown_req2_{uuid.uuid4().hex[:12]}')
            engine2 = await execution_factory.create_for_user(user_context2)
            assert len(execution_factory._active_engines) == 2
            assert execution_factory._cleanup_task is not None
            await execution_factory.shutdown()
            assert len(execution_factory._active_engines) == 0
            assert execution_factory._shutdown_event.is_set()
            if execution_factory._cleanup_task:
                assert execution_factory._cleanup_task.done()
            metrics = execution_factory.get_factory_metrics()
            assert metrics['active_engines_count'] == 0

class ExecutionEngineResourceManagementTests:
    """Test execution engine resource management and limits."""

    @pytest.mark.asyncio
    async def test_execution_engine_timeout_handling(self):
        """Test execution engine handles timeouts correctly."""
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        mock_emitter = MagicMock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        mock_emitter.cleanup = AsyncMock()
        user_context = UserExecutionContext(user_id=f'timeout_user_{uuid.uuid4().hex[:12]}', thread_id=f'timeout_thread_{uuid.uuid4().hex[:12]}', run_id=f'timeout_run_{uuid.uuid4().hex[:12]}', request_id=f'timeout_req_{uuid.uuid4().hex[:12]}')
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_factory, websocket_emitter=mock_emitter)
        original_timeout = engine.AGENT_EXECUTION_TIMEOUT
        engine.AGENT_EXECUTION_TIMEOUT = 0.1
        try:
            exec_context = AgentExecutionContext(user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id, request_id=user_context.request_id, agent_name='timeout_test_agent', step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
            mock_state = MagicMock()

            async def slow_execution(*args, **kwargs):
                await asyncio.sleep(0.5)
                return MagicMock(success=True)
            engine.agent_core = MagicMock()
            engine.agent_core.execute_agent = slow_execution
            result = await engine.execute_agent(exec_context, mock_state)
            assert result is not None
            assert result.success is False
            assert 'timed out' in result.error.lower()
            assert result.execution_time == engine.AGENT_EXECUTION_TIMEOUT
            assert result.metadata.get('timeout') is True
            assert engine.execution_stats['timeout_executions'] == 1
            assert engine.execution_stats['failed_executions'] == 1
        finally:
            engine.AGENT_EXECUTION_TIMEOUT = original_timeout

    def test_execution_engine_semaphore_resource_control(self):
        """Test execution engine semaphore controls concurrent resources."""
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        mock_emitter = MagicMock()
        user_context = UserExecutionContext(user_id=f'semaphore_user_{uuid.uuid4().hex[:12]}', thread_id=f'semaphore_thread_{uuid.uuid4().hex[:12]}', run_id=f'semaphore_run_{uuid.uuid4().hex[:12]}', request_id=f'semaphore_req_{uuid.uuid4().hex[:12]}')
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_factory, websocket_emitter=mock_emitter)
        assert engine.semaphore._value == engine.max_concurrent
        assert engine.max_concurrent == 3
        assert not engine.semaphore.locked()

        async def test_semaphore_limit():
            acquired_count = 0
            for i in range(engine.max_concurrent + 2):
                try:
                    engine.semaphore.acquire_nowait()
                    acquired_count += 1
                except:
                    break
            assert acquired_count == engine.max_concurrent
            for i in range(acquired_count):
                engine.semaphore.release()
        asyncio.run(test_semaphore_limit())

    @pytest.mark.asyncio
    async def test_execution_engine_resource_cleanup_on_failure(self):
        """Test that resources are cleaned up properly on execution failures."""
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        mock_emitter = MagicMock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        mock_emitter.cleanup = AsyncMock()
        user_context = UserExecutionContext(user_id=f'failure_user_{uuid.uuid4().hex[:12]}', thread_id=f'failure_thread_{uuid.uuid4().hex[:12]}', run_id=f'failure_run_{uuid.uuid4().hex[:12]}', request_id=f'failure_req_{uuid.uuid4().hex[:12]}')
        engine = UserExecutionEngine(context=user_context, agent_factory=mock_factory, websocket_emitter=mock_emitter)
        exec_context = AgentExecutionContext(user_id=user_context.user_id, thread_id=user_context.thread_id, run_id=user_context.run_id, request_id=user_context.request_id, agent_name='failure_test_agent', step=PipelineStep.INITIALIZATION, execution_timestamp=datetime.now(timezone.utc), pipeline_step_num=1)
        mock_state = MagicMock()

        async def failing_execution(*args, **kwargs):
            raise RuntimeError('Simulated execution failure')
        engine.agent_core = MagicMock()
        engine.agent_core.execute_agent = failing_execution
        initial_concurrent = engine.execution_stats['concurrent_executions']
        initial_active_runs = len(engine.active_runs)
        with pytest.raises(RuntimeError, match='Agent execution failed'):
            await engine.execute_agent(exec_context, mock_state)
        assert engine.execution_stats['concurrent_executions'] == initial_concurrent
        assert len(engine.active_runs) == initial_active_runs
        assert engine.execution_stats['failed_executions'] == 1
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')