"""
Test suite for trace persistence functionality.
Tests the integration between ExecutionTracker and ClickHouse persistence.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
)
from netra_backend.app.core.execution_tracker import (
    ExecutionRecord,
    ExecutionState,
    ExecutionTracker,
)
from netra_backend.app.core.trace_persistence import (
    ClickHouseTraceWriter,
    ExecutionPersistence,
    TracePersistenceManager,
)


class TestTracePersistenceManager:
    """Test the TracePersistenceManager class."""
    
    @pytest.mark.asyncio
    async def test_init_persistence_manager(self):
        """Test initialization of TracePersistenceManager."""
        manager = TracePersistenceManager(batch_size=50, flush_interval=10.0)
        
        assert manager.batch_size == 50
        assert manager.flush_interval == 10.0
        assert manager.max_retries == 3
        assert len(manager.execution_buffer) == 0
        assert len(manager.event_buffer) == 0
        assert len(manager.metrics_buffer) == 0
    
    @pytest.mark.asyncio
    async def test_persist_execution_buffer(self):
        """Test that executions are buffered correctly."""
        manager = TracePersistenceManager(batch_size=2)
        
        # Mock the writer
        manager.clickhouse_writer = AsyncMock()
        manager.clickhouse_writer.write_execution_trace = AsyncMock(return_value=True)
        
        # Create test execution record
        record = ExecutionRecord(
            execution_id=uuid4(),
            agent_name="test_agent",
            correlation_id="corr-123",
            thread_id="thread-456",
            user_id="user-789",
            start_time=time.time(),
            state=ExecutionState.COMPLETED,
            last_heartbeat=time.time()
        )
        
        # Persist first record - should be buffered
        await manager.persist_execution(record)
        assert len(manager.execution_buffer) == 1
        manager.clickhouse_writer.write_execution_trace.assert_not_called()
        
        # Persist second record - should trigger flush
        await manager.persist_execution(record)
        assert len(manager.execution_buffer) == 0
        manager.clickhouse_writer.write_execution_trace.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_persist_event_buffer(self):
        """Test that events are buffered and flushed correctly."""
        manager = TracePersistenceManager(batch_size=3)
        
        # Mock the writer
        manager.clickhouse_writer = AsyncMock()
        manager.clickhouse_writer.write_agent_event = AsyncMock(return_value=True)
        
        event = {
            'execution_id': uuid4(),
            'event_type': 'state_change',
            'event_data': {'new_state': 'running'},
            'timestamp': datetime.now(),
            'agent_name': 'test_agent'
        }
        
        # Add events to buffer
        await manager.persist_event(event)
        await manager.persist_event(event)
        assert len(manager.event_buffer) == 2
        
        # Third event should trigger flush
        await manager.persist_event(event)
        assert len(manager.event_buffer) == 0
        manager.clickhouse_writer.write_agent_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_persist_metrics_buffer(self):
        """Test that metrics are buffered and flushed correctly."""
        manager = TracePersistenceManager(batch_size=2)
        
        # Mock the writer
        manager.clickhouse_writer = AsyncMock()
        manager.clickhouse_writer.write_performance_metrics = AsyncMock(return_value=True)
        
        metrics = {
            'execution_id': uuid4(),
            'metric_type': 'duration',
            'metric_value': 123.45,
            'agent_name': 'test_agent'
        }
        
        # Add metrics
        await manager.persist_metrics(metrics)
        assert len(manager.metrics_buffer) == 1
        
        # Second metric triggers flush
        await manager.persist_metrics(metrics)
        assert len(manager.metrics_buffer) == 0
        manager.clickhouse_writer.write_performance_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_flush_all(self):
        """Test that flush_all flushes all buffers."""
        manager = TracePersistenceManager()
        
        # Mock the writer methods
        manager.clickhouse_writer = AsyncMock()
        manager.clickhouse_writer.write_execution_trace = AsyncMock(return_value=True)
        manager.clickhouse_writer.write_agent_event = AsyncMock(return_value=True)
        manager.clickhouse_writer.write_performance_metrics = AsyncMock(return_value=True)
        
        # Add data to all buffers
        manager.execution_buffer.append({'test': 'execution'})
        manager.event_buffer.append({'test': 'event'})
        manager.metrics_buffer.append({'test': 'metrics'})
        
        # Flush all
        await manager.flush_all()
        
        # Verify all buffers are empty
        assert len(manager.execution_buffer) == 0
        assert len(manager.event_buffer) == 0
        assert len(manager.metrics_buffer) == 0
        
        # Verify all writers were called
        manager.clickhouse_writer.write_execution_trace.assert_called_once()
        manager.clickhouse_writer.write_agent_event.assert_called_once()
        manager.clickhouse_writer.write_performance_metrics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test that retry logic works for failed writes."""
        manager = TracePersistenceManager(batch_size=1, max_retries=3)
        
        # Mock writer to fail twice, then succeed
        manager.clickhouse_writer = AsyncMock()
        manager.clickhouse_writer.write_execution_trace = AsyncMock(
            side_effect=[False, False, True]
        )
        
        # Add execution to trigger flush
        record = ExecutionRecord(
            execution_id=uuid4(),
            agent_name="test_agent",
            correlation_id=None,
            thread_id=None,
            user_id=None,
            start_time=time.time(),
            state=ExecutionState.COMPLETED,
            last_heartbeat=time.time()
        )
        
        await manager.persist_execution(record)
        
        # Should have retried and succeeded
        assert manager.clickhouse_writer.write_execution_trace.call_count == 3
        assert manager.stats['retry_count'] == 2
        assert manager.stats['executions_persisted'] == 1
    
    @pytest.mark.asyncio
    async def test_periodic_flush(self):
        """Test that periodic flush task works."""
        manager = TracePersistenceManager(flush_interval=0.1)  # 100ms flush
        
        # Mock writer
        manager.clickhouse_writer = AsyncMock()
        manager.clickhouse_writer.create_tables_if_needed = AsyncMock()
        
        # Start the manager
        await manager.start()
        
        # Add data
        manager.execution_buffer.append({'test': 'data'})
        
        # Mock flush methods
        manager._flush_executions = AsyncMock()
        
        # Wait for periodic flush
        await asyncio.sleep(0.2)
        
        # Stop the manager
        await manager.stop()
        
        # Verify flush was called
        assert manager.stats['flush_count'] >= 1


class TestExecutionPersistence:
    """Test the ExecutionPersistence high-level interface."""
    
    @pytest.mark.asyncio
    async def test_write_execution_start(self):
        """Test writing execution start event."""
        persistence = ExecutionPersistence()
        
        # Mock the manager
        persistence.manager = AsyncMock()
        persistence._started = True
        
        exec_id = uuid4()
        context = {
            'agent_name': 'test_agent',
            'user_id': 'user123',
            'thread_id': 'thread456'
        }
        
        result = await persistence.write_execution_start(exec_id, context)
        
        assert result is True
        persistence.manager.persist_event.assert_called_once()
        
        # Verify the event structure
        call_args = persistence.manager.persist_event.call_args[0][0]
        assert call_args['execution_id'] == exec_id
        assert call_args['event_type'] == 'execution_start'
        assert call_args['agent_name'] == 'test_agent'
    
    @pytest.mark.asyncio
    async def test_write_execution_update(self):
        """Test writing execution state update."""
        persistence = ExecutionPersistence()
        persistence.manager = AsyncMock()
        persistence._started = True
        
        exec_id = uuid4()
        
        result = await persistence.write_execution_update(
            exec_id, 
            'running',
            {'agent_name': 'test_agent'}
        )
        
        assert result is True
        persistence.manager.persist_event.assert_called_once()
        
        call_args = persistence.manager.persist_event.call_args[0][0]
        assert call_args['event_type'] == 'state_change'
        assert call_args['event_data']['new_state'] == 'running'
    
    @pytest.mark.asyncio
    async def test_write_execution_complete(self):
        """Test writing execution completion."""
        persistence = ExecutionPersistence()
        persistence.manager = AsyncMock()
        persistence._started = True
        
        exec_id = uuid4()
        result = {
            'agent_name': 'test_agent',
            'user_id': 'user123',
            'state': 'completed',
            'duration': 10.5
        }
        
        success = await persistence.write_execution_complete(exec_id, result)
        
        assert success is True
        persistence.manager.persist_event.assert_called_once()
        
        call_args = persistence.manager.persist_event.call_args[0][0]
        assert call_args['event_type'] == 'execution_complete'
        assert call_args['event_data'] == result
    
    @pytest.mark.asyncio
    async def test_write_performance_metrics(self):
        """Test writing performance metrics."""
        persistence = ExecutionPersistence()
        persistence.manager = AsyncMock()
        persistence._started = True
        
        exec_id = uuid4()
        metrics = {
            'duration_seconds': 10.5,
            'memory_usage_mb': 256,
            'heartbeat_count': 5,
            'agent_name': 'test_agent'
        }
        
        result = await persistence.write_performance_metrics(exec_id, metrics)
        
        assert result is True
        # Should be called 3 times (for numeric metrics only)
        assert persistence.manager.persist_metrics.call_count == 3


class TestExecutionTrackerIntegration:
    """Test integration between ExecutionTracker and persistence."""
    
    @pytest.mark.asyncio
    async def test_tracker_with_persistence(self):
        """Test that ExecutionTracker integrates with persistence."""
        tracker = ExecutionTracker()
        
        # Mock persistence
        with patch('netra_backend.app.core.trace_persistence.get_execution_persistence') as mock_get_persistence:
            mock_persistence = AsyncMock()
            mock_get_persistence.return_value = mock_persistence
            
            # Start monitoring (should initialize persistence)
            await tracker.start_monitoring()
            
            # Register an execution
            exec_id = await tracker.register_execution(
                agent_name="test_agent",
                user_id="user123",
                timeout_seconds=30
            )
            
            # Verify persistence was called
            mock_persistence.ensure_started.assert_called_once()
            mock_persistence.write_execution_start.assert_called_once()
            
            # Complete execution
            await tracker.complete_execution(exec_id)
            
            # Verify completion was persisted
            assert mock_persistence.persist_execution_record.called
            assert mock_persistence.write_execution_complete.called
            assert mock_persistence.write_performance_metrics.called
    
    @pytest.mark.asyncio
    async def test_tracker_timeout_persistence(self):
        """Test that timeouts are persisted correctly."""
        tracker = ExecutionTracker()
        
        with patch('netra_backend.app.core.trace_persistence.get_execution_persistence') as mock_get_persistence:
            mock_persistence = AsyncMock()
            mock_get_persistence.return_value = mock_persistence
            
            await tracker.start_monitoring()
            
            # Create an execution that will timeout
            exec_id = await tracker.register_execution(
                agent_name="slow_agent",
                timeout_seconds=0.1  # Very short timeout
            )
            
            await tracker.start_execution(exec_id)
            
            # Wait for timeout
            await asyncio.sleep(0.2)
            
            # Check for timeout
            await tracker._check_executions()
            
            # Verify timeout was persisted
            execution = tracker.get_execution(exec_id)
            assert execution.state == ExecutionState.TIMEOUT
            assert mock_persistence.write_execution_complete.called


class TestAgentExecutionCoreMetrics:
    """Test metric collection in AgentExecutionCore."""
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test that AgentExecutionCore collects metrics."""
        # Mock registry and websocket bridge
        registry = MagicMock()
        websocket_bridge = AsyncMock()
        
        # Create execution core
        exec_core = AgentExecutionCore(registry, websocket_bridge)
        
        # Mock the persistence
        exec_core.persistence = AsyncMock()
        
        # Mock execution tracker
        exec_core.execution_tracker = AsyncMock()
        exec_core.execution_tracker.register_execution = AsyncMock(return_value=uuid4())
        exec_core.execution_tracker.start_execution = AsyncMock()
        exec_core.execution_tracker.complete_execution = AsyncMock()
        exec_core.execution_tracker.collect_metrics = AsyncMock(return_value={
            'execution_id': 'test',
            'duration_seconds': 5.0
        })
        
        # Create test context and state
        context = AgentExecutionContext(
            run_id="run123",
            thread_id="thread456",
            user_id="user789",
            agent_name="test_agent"
        )
        
        state = DeepAgentState()
        state.user_id = "user789"
        
        # Mock agent
        test_agent = AsyncMock()
        test_agent.execute = AsyncMock(return_value=AgentExecutionResult(
            success=True,
            state=state,
            duration=1.0
        ))
        registry.get = MagicMock(return_value=test_agent)
        
        # Execute agent
        result = await exec_core.execute_agent(context, state, timeout=30)
        
        # Verify metrics were collected and persisted
        exec_core.execution_tracker.collect_metrics.assert_called()
        exec_core.persistence.write_performance_metrics.assert_called()
        
        # Verify result has metrics
        assert result.metrics is not None
        assert 'execution_time_ms' in result.metrics
    
    @pytest.mark.asyncio
    async def test_metrics_on_failure(self):
        """Test that metrics are collected even on failure."""
        registry = MagicMock()
        websocket_bridge = AsyncMock()
        
        exec_core = AgentExecutionCore(registry, websocket_bridge)
        exec_core.persistence = AsyncMock()
        exec_core.execution_tracker = AsyncMock()
        exec_core.execution_tracker.register_execution = AsyncMock(return_value=uuid4())
        exec_core.execution_tracker.collect_metrics = AsyncMock(return_value={})
        
        context = AgentExecutionContext(
            run_id="run123",
            thread_id="thread456",
            user_id="user789",
            agent_name="failing_agent"
        )
        
        state = DeepAgentState()
        
        # Mock agent that fails
        failing_agent = AsyncMock()
        failing_agent.execute = AsyncMock(side_effect=Exception("Test failure"))
        registry.get = MagicMock(return_value=failing_agent)
        
        # Execute should handle the failure
        result = await exec_core.execute_agent(context, state, timeout=30)
        
        # Verify failure
        assert result.success is False
        assert "Test failure" in result.error
        
        # Verify metrics were still collected
        assert result.metrics is not None
        assert 'execution_time_ms' in result.metrics


@pytest.mark.asyncio
async def test_clickhouse_trace_writer():
    """Test ClickHouseTraceWriter functionality."""
    writer = ClickHouseTraceWriter()
    
    # Mock ClickHouse client
    with patch('netra_backend.app.core.trace_persistence.get_clickhouse_client') as mock_get_client:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.execute = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Test table creation
        await writer.create_tables_if_needed()
        
        # Verify tables were created
        assert mock_client.execute.call_count >= 3  # execution_traces, agent_events, execution_metrics
        
        # Test writing execution trace
        records = [{
            'execution_id': uuid4(),
            'agent_name': 'test',
            'state': 'completed',
            'start_time': time.time(),
            'end_time': time.time(),
            'duration': 1.0
        }]
        
        result = await writer.write_execution_trace(records)
        assert result is True
        
        # Test writing events
        events = [{
            'execution_id': uuid4(),
            'event_type': 'test_event',
            'event_data': {},
            'timestamp': datetime.now(),
            'agent_name': 'test'
        }]
        
        result = await writer.write_agent_event(events)
        assert result is True
        
        # Test writing metrics
        metrics = [{
            'execution_id': uuid4(),
            'metric_type': 'duration',
            'metric_value': 10.5,
            'agent_name': 'test'
        }]
        
        result = await writer.write_performance_metrics(metrics)
        assert result is True