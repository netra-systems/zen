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

from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.state import DeepAgentState


class TestExecutionEngineLifecycle:
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
        return UserExecutionContext(
            user_id=f"lifecycle_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"lifecycle_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"lifecycle_run_{uuid.uuid4().hex[:12]}",
            request_id=f"lifecycle_req_{uuid.uuid4().hex[:12]}",
            websocket_client_id=f"lifecycle_ws_{uuid.uuid4().hex[:12]}"
        )
    
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
        # Create UserExecutionEngine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Validate initial lifecycle state
        assert engine._is_active is True
        assert engine.is_active() is False  # No active runs initially
        assert isinstance(engine.created_at, datetime)
        assert engine.created_at.tzinfo is not None
        
        # Validate initial resource state
        assert len(engine.active_runs) == 0
        assert len(engine.run_history) == 0
        assert engine.execution_stats['total_executions'] == 0
        assert engine.execution_stats['concurrent_executions'] == 0
        
        # Validate engine ID generation
        assert engine.engine_id.startswith(f"user_engine_{user_context.user_id}")
        assert user_context.run_id in engine.engine_id
        
        # Validate user context assignment
        assert engine.context == user_context
        assert engine.get_user_context() == user_context
    
    @pytest.mark.asyncio
    async def test_execution_engine_cleanup_lifecycle(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test execution engine cleanup and resource deallocation."""
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Simulate some execution state
        engine.execution_stats['total_executions'] = 5
        engine.execution_stats['failed_executions'] = 1
        engine.active_runs['test_run'] = MagicMock()
        engine.run_history.append(MagicMock())
        
        # Validate engine is active before cleanup
        assert engine._is_active is True
        assert len(engine.active_runs) == 1
        assert len(engine.run_history) == 1
        
        # Cleanup engine
        await engine.cleanup()
        
        # Validate cleanup completed
        assert engine._is_active is False
        assert engine.is_active() is False
        assert len(engine.active_runs) == 0
        assert len(engine.run_history) == 0
        assert len(engine.execution_stats) == 0
        
        # Validate WebSocket emitter cleanup was called
        mock_websocket_emitter.cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execution_engine_multiple_cleanup_calls(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test that multiple cleanup calls are handled gracefully."""
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # First cleanup
        await engine.cleanup()
        assert engine._is_active is False
        
        # Second cleanup should not raise errors
        await engine.cleanup()
        assert engine._is_active is False
        
        # WebSocket emitter cleanup should still have been called once
        # (assuming the implementation handles multiple calls gracefully)
        mock_websocket_emitter.cleanup.assert_called()
    
    @pytest.mark.asyncio
    async def test_execution_engine_active_runs_tracking(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test that active runs are tracked correctly during lifecycle."""
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Create mock execution context
        exec_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            request_id=user_context.request_id,
            agent_name="test_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Simulate adding active run during execution
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        exec_context.execution_id = execution_id
        engine.active_runs[execution_id] = exec_context
        engine.execution_stats['concurrent_executions'] += 1
        
        # Validate active run tracking
        assert len(engine.active_runs) == 1
        assert execution_id in engine.active_runs
        assert engine.is_active() is True  # Has active runs
        assert engine.execution_stats['concurrent_executions'] == 1
        
        # Remove active run (simulate completion)
        engine.active_runs.pop(execution_id)
        engine.execution_stats['concurrent_executions'] -= 1
        
        # Validate active run removal
        assert len(engine.active_runs) == 0
        assert execution_id not in engine.active_runs
        assert engine.is_active() is False  # No active runs
        assert engine.execution_stats['concurrent_executions'] == 0
    
    def test_execution_engine_history_size_limit(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test that run history respects size limits."""
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Add results beyond the history limit
        max_history = UserExecutionEngine.MAX_HISTORY_SIZE
        
        for i in range(max_history + 10):
            mock_result = MagicMock()
            mock_result.agent_name = f"agent_{i}"
            mock_result.success = True
            mock_result.execution_time = 1.0
            
            engine._update_user_history(mock_result)
        
        # Validate history size is limited
        assert len(engine.run_history) == max_history
        
        # Validate most recent results are kept (FIFO behavior)
        first_result = engine.run_history[0]
        last_result = engine.run_history[-1]
        
        # The first result should be from the middle of our additions (old ones dropped)
        assert int(first_result.agent_name.split('_')[1]) >= 10
        
        # The last result should be the most recent
        assert last_result.agent_name == f"agent_{max_history + 9}"
    
    def test_execution_engine_stats_calculations(self, user_context, mock_agent_factory, mock_websocket_emitter):
        """Test execution statistics calculations during lifecycle."""
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Add execution statistics
        engine.execution_stats['queue_wait_times'] = [0.5, 1.2, 0.8, 2.1]
        engine.execution_stats['execution_times'] = [2.3, 1.5, 3.2, 1.8, 2.7]
        engine.execution_stats['total_executions'] = 5
        engine.execution_stats['failed_executions'] = 1
        
        # Get calculated statistics
        stats = engine.get_user_execution_stats()
        
        # Validate calculations
        expected_avg_queue_wait = sum([0.5, 1.2, 0.8, 2.1]) / 4
        expected_max_queue_wait = max([0.5, 1.2, 0.8, 2.1])
        expected_avg_execution_time = sum([2.3, 1.5, 3.2, 1.8, 2.7]) / 5
        expected_max_execution_time = max([2.3, 1.5, 3.2, 1.8, 2.7])
        
        assert stats['avg_queue_wait_time'] == expected_avg_queue_wait
        assert stats['max_queue_wait_time'] == expected_max_queue_wait
        assert stats['avg_execution_time'] == expected_avg_execution_time
        assert stats['max_execution_time'] == expected_max_execution_time
        
        # Validate user-specific metadata
        assert stats['user_id'] == user_context.user_id
        assert stats['engine_id'] == engine.engine_id
        assert stats['total_executions'] == 5
        assert stats['failed_executions'] == 1
        assert stats['is_active'] is True


class TestExecutionEngineFactoryLifecycle:
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
        # Create factory
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        # Validate initial state
        assert factory._websocket_bridge == mock_websocket_bridge
        assert len(factory._active_engines) == 0
        assert factory._cleanup_task is None
        assert not factory._shutdown_event.is_set()
        
        # Validate initial metrics
        metrics = factory.get_factory_metrics()
        assert metrics['total_engines_created'] == 0
        assert metrics['total_engines_cleaned'] == 0
        assert metrics['active_engines_count'] == 0
        assert metrics['creation_errors'] == 0
        assert metrics['cleanup_errors'] == 0
        
        # Validate configuration
        assert factory._max_engines_per_user == 2
        assert factory._engine_timeout_seconds == 300
        assert factory._cleanup_interval == 60
    
    @pytest.mark.asyncio
    async def test_factory_engine_creation_lifecycle(self, execution_factory):
        """Test factory engine creation and lifecycle tracking."""
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"factory_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"factory_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"factory_run_{uuid.uuid4().hex[:12]}",
            request_id=f"factory_req_{uuid.uuid4().hex[:12]}"
        )
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Initial metrics
            initial_metrics = execution_factory.get_factory_metrics()
            assert initial_metrics['active_engines_count'] == 0
            
            # Create engine
            engine = await execution_factory.create_for_user(user_context)
            
            # Validate engine creation
            assert engine is not None
            assert isinstance(engine, UserExecutionEngine)
            
            # Validate factory tracking
            assert len(execution_factory._active_engines) == 1
            
            # Validate metrics updated
            updated_metrics = execution_factory.get_factory_metrics()
            assert updated_metrics['total_engines_created'] == 1
            assert updated_metrics['active_engines_count'] == 1
            
            # Validate cleanup task started
            assert execution_factory._cleanup_task is not None
            assert not execution_factory._cleanup_task.done()
            
            # Cleanup engine
            await execution_factory.cleanup_engine(engine)
            
            # Validate cleanup
            assert len(execution_factory._active_engines) == 0
            
            # Validate metrics after cleanup
            final_metrics = execution_factory.get_factory_metrics()
            assert final_metrics['total_engines_cleaned'] == 1
            assert final_metrics['active_engines_count'] == 0
    
    @pytest.mark.asyncio
    async def test_factory_user_execution_scope_lifecycle(self, execution_factory):
        """Test factory user execution scope context manager lifecycle."""
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"scope_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"scope_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"scope_run_{uuid.uuid4().hex[:12]}",
            request_id=f"scope_req_{uuid.uuid4().hex[:12]}"
        )
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Track lifecycle events
            engine_created = None
            engine_active_during_scope = None
            
            # Use context manager
            async with execution_factory.user_execution_scope(user_context) as engine:
                engine_created = engine
                engine_active_during_scope = engine._is_active
                
                # Validate engine is active during scope
                assert engine is not None
                assert engine._is_active is True
                assert len(execution_factory._active_engines) == 1
            
            # After context manager exit, engine should be cleaned up
            assert engine_created is not None
            assert engine_active_during_scope is True
            
            # Give a moment for cleanup to complete
            await asyncio.sleep(0.1)
            
            # Validate cleanup occurred
            assert len(execution_factory._active_engines) == 0
    
    @pytest.mark.asyncio
    async def test_factory_cleanup_loop_lifecycle(self, execution_factory):
        """Test factory background cleanup loop lifecycle."""
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"cleanup_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"cleanup_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"cleanup_run_{uuid.uuid4().hex[:12]}",
            request_id=f"cleanup_req_{uuid.uuid4().hex[:12]}"
        )
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create engine to trigger cleanup task creation
            engine = await execution_factory.create_for_user(user_context)
            
            # Validate cleanup task is running
            assert execution_factory._cleanup_task is not None
            assert not execution_factory._cleanup_task.done()
            
            # Manually trigger engine as inactive (simulate timeout)
            engine._is_active = False
            
            # Wait for cleanup loop to run (short wait)
            await asyncio.sleep(0.2)
            
            # The cleanup loop should still be running
            assert not execution_factory._cleanup_task.done()
            
            # Cleanup manually to ensure test cleanup
            await execution_factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_factory_shutdown_lifecycle(self, execution_factory):
        """Test factory shutdown and resource cleanup lifecycle."""
        # Create user context and engine
        user_context = UserExecutionContext(
            user_id=f"shutdown_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"shutdown_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"shutdown_run_{uuid.uuid4().hex[:12]}",
            request_id=f"shutdown_req_{uuid.uuid4().hex[:12]}"
        )
        
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.get_agent_instance_factory') as mock_get_factory:
            mock_agent_factory = MagicMock()
            mock_agent_factory._agent_registry = MagicMock()
            mock_agent_factory._websocket_bridge = execution_factory._websocket_bridge
            mock_get_factory.return_value = mock_agent_factory
            
            # Create multiple engines
            engine1 = await execution_factory.create_for_user(user_context)
            
            # Create different context for second engine
            user_context2 = UserExecutionContext(
                user_id=f"shutdown_user2_{uuid.uuid4().hex[:12]}",
                thread_id=f"shutdown_thread2_{uuid.uuid4().hex[:12]}",
                run_id=f"shutdown_run2_{uuid.uuid4().hex[:12]}",
                request_id=f"shutdown_req2_{uuid.uuid4().hex[:12]}"
            )
            engine2 = await execution_factory.create_for_user(user_context2)
            
            # Validate engines are active
            assert len(execution_factory._active_engines) == 2
            assert execution_factory._cleanup_task is not None
            
            # Shutdown factory
            await execution_factory.shutdown()
            
            # Validate shutdown completed
            assert len(execution_factory._active_engines) == 0
            assert execution_factory._shutdown_event.is_set()
            
            # Validate cleanup task completed
            if execution_factory._cleanup_task:
                assert execution_factory._cleanup_task.done()
            
            # Validate metrics updated
            metrics = execution_factory.get_factory_metrics()
            assert metrics['active_engines_count'] == 0


class TestExecutionEngineResourceManagement:
    """Test execution engine resource management and limits."""
    
    @pytest.mark.asyncio
    async def test_execution_engine_timeout_handling(self):
        """Test execution engine handles timeouts correctly."""
        # Create mock components
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        
        mock_emitter = MagicMock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        mock_emitter.cleanup = AsyncMock()
        
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"timeout_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"timeout_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"timeout_run_{uuid.uuid4().hex[:12]}",
            request_id=f"timeout_req_{uuid.uuid4().hex[:12]}"
        )
        
        # Create engine with very short timeout for testing
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Override timeout for testing
        original_timeout = engine.AGENT_EXECUTION_TIMEOUT
        engine.AGENT_EXECUTION_TIMEOUT = 0.1  # 100ms timeout
        
        try:
            # Create mock execution context
            exec_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name="timeout_test_agent",
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=1
            )
            
            # Create mock state
            mock_state = MagicMock()
            
            # Mock agent core to simulate long-running operation
            async def slow_execution(*args, **kwargs):
                await asyncio.sleep(0.5)  # Longer than timeout
                return MagicMock(success=True)
            
            engine.agent_core = MagicMock()
            engine.agent_core.execute_agent = slow_execution
            
            # Execute agent (should timeout)
            result = await engine.execute_agent(exec_context, mock_state)
            
            # Validate timeout result
            assert result is not None
            assert result.success is False
            assert "timed out" in result.error.lower()
            assert result.execution_time == engine.AGENT_EXECUTION_TIMEOUT
            assert result.metadata.get('timeout') is True
            
            # Validate timeout statistics updated
            assert engine.execution_stats['timeout_executions'] == 1
            assert engine.execution_stats['failed_executions'] == 1
            
        finally:
            # Restore original timeout
            engine.AGENT_EXECUTION_TIMEOUT = original_timeout
    
    def test_execution_engine_semaphore_resource_control(self):
        """Test execution engine semaphore controls concurrent resources."""
        # Create mock components
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        
        mock_emitter = MagicMock()
        
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"semaphore_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"semaphore_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"semaphore_run_{uuid.uuid4().hex[:12]}",
            request_id=f"semaphore_req_{uuid.uuid4().hex[:12]}"
        )
        
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Validate semaphore initialized with default concurrency limit
        assert engine.semaphore._value == engine.max_concurrent
        assert engine.max_concurrent == 3  # Default value
        
        # Test semaphore resource control
        assert not engine.semaphore.locked()
        
        # Acquire semaphore resources up to limit
        async def test_semaphore_limit():
            acquired_count = 0
            
            # Try to acquire more than the limit
            for i in range(engine.max_concurrent + 2):
                try:
                    engine.semaphore.acquire_nowait()
                    acquired_count += 1
                except:
                    break
            
            # Should only acquire up to the limit
            assert acquired_count == engine.max_concurrent
            
            # Release all acquired resources
            for i in range(acquired_count):
                engine.semaphore.release()
        
        # Run the semaphore test
        asyncio.run(test_semaphore_limit())
    
    @pytest.mark.asyncio
    async def test_execution_engine_resource_cleanup_on_failure(self):
        """Test that resources are cleaned up properly on execution failures."""
        # Create mock components
        mock_factory = MagicMock()
        mock_factory._agent_registry = MagicMock()
        mock_factory._websocket_bridge = MagicMock()
        
        mock_emitter = MagicMock()
        mock_emitter.notify_agent_started = AsyncMock(return_value=True)
        mock_emitter.notify_agent_thinking = AsyncMock(return_value=True)
        mock_emitter.notify_agent_completed = AsyncMock(return_value=True)
        mock_emitter.cleanup = AsyncMock()
        
        # Create user context
        user_context = UserExecutionContext(
            user_id=f"failure_user_{uuid.uuid4().hex[:12]}",
            thread_id=f"failure_thread_{uuid.uuid4().hex[:12]}",
            run_id=f"failure_run_{uuid.uuid4().hex[:12]}",
            request_id=f"failure_req_{uuid.uuid4().hex[:12]}"
        )
        
        # Create engine
        engine = UserExecutionEngine(
            context=user_context,
            agent_factory=mock_factory,
            websocket_emitter=mock_emitter
        )
        
        # Create mock execution context
        exec_context = AgentExecutionContext(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id,
            request_id=user_context.request_id,
            agent_name="failure_test_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Create mock state
        mock_state = MagicMock()
        
        # Mock agent core to simulate failure
        async def failing_execution(*args, **kwargs):
            raise RuntimeError("Simulated execution failure")
        
        engine.agent_core = MagicMock()
        engine.agent_core.execute_agent = failing_execution
        
        # Track initial state
        initial_concurrent = engine.execution_stats['concurrent_executions']
        initial_active_runs = len(engine.active_runs)
        
        # Execute agent (should fail)
        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await engine.execute_agent(exec_context, mock_state)
        
        # Validate resources were cleaned up despite failure
        assert engine.execution_stats['concurrent_executions'] == initial_concurrent
        assert len(engine.active_runs) == initial_active_runs
        assert engine.execution_stats['failed_executions'] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])