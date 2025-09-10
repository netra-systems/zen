"""
Comprehensive tests for ClickHouse schema and trace writer
Tests table creation, data writing, batching, and querying
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from typing import Dict, Any
import json
from shared.isolated_environment import IsolatedEnvironment

# Try to import ClickHouse modules, skip if not available
clickhouse_available = True
try:
    from netra_backend.app.db.clickhouse_schema import (
        ClickHouseTraceSchema,
        create_clickhouse_schema,
        verify_clickhouse_schema
    )
    from netra_backend.app.db.clickhouse_trace_writer import (
        ClickHouseTraceWriter,
        TraceContext,
        EventType,
        ExecutionStatus,
        ErrorType,
        MetricType
    )
except (ImportError, ModuleNotFoundError) as e:
    clickhouse_available = False
    # Create dummy classes for testing when ClickHouse is not available
    ClickHouseTraceSchema = None
    ClickHouseTraceWriter = None


# Skip all tests if ClickHouse is not available
pytestmark = pytest.mark.skipif(not clickhouse_available, reason="ClickHouse driver not available")

@pytest.fixture
async def clickhouse_schema():
    """Create test schema instance."""
    schema = ClickHouseTraceSchema(
        host='localhost',
        port=9000,
        database='netra_traces_test',
        user='default',
        password=''
    )
    
    # Clean up before test
    await schema.drop_all_tables()
    
    yield schema
    
    # Clean up after test
    await schema.drop_all_tables()
    schema.close()


@pytest.fixture
async def clickhouse_writer():
    """Create test writer instance."""
    writer = ClickHouseTraceWriter(
        host='localhost',
        port=9000,
        database='netra_traces_test',
        user='default',
        password='',
        batch_size=10,  # Small batch for testing
        flush_interval=1.0  # Fast flush for testing
    )
    
    await writer.start()
    
    yield writer
    
    await writer.stop()


class TestClickHouseSchema:
    """Test ClickHouse schema management."""
    
    @pytest.mark.asyncio
    async def test_create_tables(self, clickhouse_schema):
        """Test creating all tables and views."""
        # Create tables
        result = await clickhouse_schema.create_tables()
        assert result is True
        
        # Verify all tables exist
        verification = await clickhouse_schema.verify_schema()
        
        # Check database
        assert verification.get('database') is True
        
        # Check all tables
        for table in clickhouse_schema.TABLES:
            assert verification.get(table) is True
            assert verification.get(f"{table}_structure") is True
        
        # Check materialized views
        for view in clickhouse_schema.MATERIALIZED_VIEWS:
            assert verification.get(view) is True
    
    @pytest.mark.asyncio
    async def test_get_table_stats(self, clickhouse_schema):
        """Test getting table statistics."""
        # Create tables first
        await clickhouse_schema.create_tables()
        
        # Get stats (should be empty initially)
        stats = await clickhouse_schema.get_table_stats()
        
        # Check all tables have stats
        for table in clickhouse_schema.TABLES:
            assert table in stats
            assert stats[table] == 0  # Empty tables
        
        # Check database stats
        assert 'total_bytes' in stats
        assert 'total_rows' in stats
    
    @pytest.mark.asyncio
    async def test_get_table_columns(self, clickhouse_schema):
        """Test getting column information."""
        # Create tables first
        await clickhouse_schema.create_tables()
        
        # Check agent_executions columns
        columns = await clickhouse_schema.get_table_columns('agent_executions')
        assert len(columns) > 0
        
        # Verify key columns exist
        column_names = [col['name'] for col in columns]
        assert 'trace_id' in column_names
        assert 'execution_id' in column_names
        assert 'user_id' in column_names
        assert 'agent_type' in column_names
        assert 'status' in column_names
    
    @pytest.mark.asyncio
    async def test_truncate_table(self, clickhouse_schema):
        """Test truncating a table."""
        # Create tables first
        await clickhouse_schema.create_tables()
        
        # Truncate agent_executions table
        result = await clickhouse_schema.truncate_table('agent_executions')
        assert result is True
        
        # Verify table still exists but is empty
        stats = await clickhouse_schema.get_table_stats()
        assert stats['agent_executions'] == 0
    
    @pytest.mark.asyncio
    async def test_optimize_tables(self, clickhouse_schema):
        """Test optimizing tables."""
        # Create tables first
        await clickhouse_schema.create_tables()
        
        # Optimize all tables
        results = await clickhouse_schema.optimize_tables()
        
        # Check all tables were optimized
        for table in clickhouse_schema.TABLES:
            assert table in results
            assert results[table] is True


class TestClickHouseTraceWriter:
    """Test ClickHouse trace writer functionality."""
    
    @pytest.mark.asyncio
    async def test_write_execution(self, clickhouse_schema, clickhouse_writer):
        """Test writing execution records."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        # Write execution
        trace_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        user_id = "test_user"
        
        await clickhouse_writer.write_execution(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            agent_type="test_agent",
            agent_name="Test Agent",
            status=ExecutionStatus.RUNNING,
            start_time=datetime.now(timezone.utc),
            request_payload={"prompt": "test"},
            token_count=100,
            tool_calls_count=3
        )
        
        # Flush to ensure write
        await clickhouse_writer.flush_all()
        
        # Verify write
        traces = await clickhouse_writer.get_execution_traces(user_id=user_id)
        assert len(traces) > 0
        assert traces[0]['trace_id'] == trace_id
        assert traces[0]['execution_id'] == execution_id
        assert traces[0]['agent_type'] == 'test_agent'
    
    @pytest.mark.asyncio
    async def test_write_events(self, clickhouse_schema, clickhouse_writer):
        """Test writing event records."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        trace_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        user_id = "test_user"
        
        # Write multiple events
        events = [
            (EventType.AGENT_STARTED, "agent_started"),
            (EventType.AGENT_THINKING, "agent_thinking"),
            (EventType.TOOL_EXECUTING, "tool_executing"),
            (EventType.TOOL_COMPLETED, "tool_completed"),
            (EventType.AGENT_COMPLETED, "agent_completed"),
        ]
        
        for idx, (event_type, event_name) in enumerate(events):
            await clickhouse_writer.write_event(
                trace_id=trace_id,
                execution_id=execution_id,
                user_id=user_id,
                event_type=event_type,
                event_name=event_name,
                timestamp=datetime.now(timezone.utc),
                sequence_number=idx,
                event_payload={"step": idx}
            )
        
        # Flush and verify
        await clickhouse_writer.flush_all()
        
        # Check stats
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] == 5
    
    @pytest.mark.asyncio
    async def test_write_metrics(self, clickhouse_schema, clickhouse_writer):
        """Test writing performance metrics."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        trace_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        user_id = "test_user"
        
        # Write various metrics
        await clickhouse_writer.write_metric(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            metric_type=MetricType.LATENCY,
            metric_name="api_latency",
            value=125.5,
            timestamp=datetime.now(timezone.utc),
            unit="ms",
            total_time_ms=125,
            llm_time_ms=100,
            processing_time_ms=25
        )
        
        await clickhouse_writer.write_metric(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            metric_type=MetricType.LLM,
            metric_name="token_usage",
            value=1500,
            timestamp=datetime.now(timezone.utc),
            unit="tokens",
            prompt_tokens=500,
            completion_tokens=1000,
            total_tokens=1500,
            model_name="gpt-4"
        )
        
        # Flush and verify
        await clickhouse_writer.flush_all()
        
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] == 2
    
    @pytest.mark.asyncio
    async def test_write_errors(self, clickhouse_schema, clickhouse_writer):
        """Test writing error logs."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        trace_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        user_id = "test_user"
        
        # Write error
        await clickhouse_writer.write_error(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            error_type=ErrorType.VALIDATION,
            error_message="Invalid input format",
            timestamp=datetime.now(timezone.utc),
            error_code="VAL001",
            severity="error",
            component_name="input_validator",
            is_recoverable=True,
            retry_count=1,
            affected_features=["chat", "agent_execution"]
        )
        
        # Flush and verify
        await clickhouse_writer.flush_all()
        
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] == 1
    
    @pytest.mark.asyncio
    async def test_write_correlations(self, clickhouse_schema, clickhouse_writer):
        """Test writing trace correlations."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        parent_trace = str(uuid.uuid4())
        child_trace = str(uuid.uuid4())
        
        # Write correlation
        await clickhouse_writer.write_correlation(
            parent_trace_id=parent_trace,
            child_trace_id=child_trace,
            relationship_type="parent_child",
            parent_agent_type="supervisor",
            child_agent_type="tool_executor",
            depth_level=1,
            context={"delegation": "tool_call"}
        )
        
        # Flush and verify
        await clickhouse_writer.flush_all()
        
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] == 1
    
    @pytest.mark.asyncio
    async def test_batch_writing(self, clickhouse_schema, clickhouse_writer):
        """Test batch writing functionality."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        # Write multiple records (more than batch size)
        user_id = "batch_test_user"
        
        for i in range(15):  # Batch size is 10
            await clickhouse_writer.write_execution(
                trace_id=str(uuid.uuid4()),
                execution_id=str(uuid.uuid4()),
                user_id=user_id,
                agent_type="batch_agent",
                agent_name=f"Agent {i}",
                status=ExecutionStatus.COMPLETED,
                start_time=datetime.now(timezone.utc),
                request_payload={"index": i}
            )
        
        # Wait for auto-flush
        await asyncio.sleep(2)
        
        # Check stats
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] >= 10  # At least one batch flushed
        assert stats['batch_flushes'] >= 1
    
    @pytest.mark.asyncio
    async def test_trace_context(self, clickhouse_schema, clickhouse_writer):
        """Test TraceContext context manager."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        user_id = "context_test_user"
        
        # Use trace context
        async with TraceContext(
            writer=clickhouse_writer,
            user_id=user_id,
            agent_type="context_agent",
            agent_name="Context Test Agent"
        ) as ctx:
            # Log tool execution
            await ctx.log_tool_execution(
                tool_name="test_tool",
                tool_input={"param": "value"},
                tool_output={"result": "success"},
                duration_ms=50
            )
            
            # Access trace info
            assert ctx.trace_id is not None
            assert ctx.execution_id is not None
            assert ctx.correlation_id is not None
        
        # Flush and verify
        await clickhouse_writer.flush_all()
        
        # Check multiple records were written
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] >= 4  # Start event, tool events, completion
    
    @pytest.mark.asyncio
    async def test_error_handling_in_context(self, clickhouse_schema, clickhouse_writer):
        """Test error handling in TraceContext."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        user_id = "error_context_user"
        
        # Use trace context with error
        try:
            async with TraceContext(
                writer=clickhouse_writer,
                user_id=user_id,
                agent_type="error_agent",
                agent_name="Error Test Agent"
            ) as ctx:
                # Simulate error
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        # Flush and verify
        await clickhouse_writer.flush_all()
        
        # Check error was logged
        stats = clickhouse_writer.get_stats()
        assert stats['total_writes'] >= 3  # Execution, event, error
    
    @pytest.mark.asyncio
    async def test_query_execution_traces(self, clickhouse_schema, clickhouse_writer):
        """Test querying execution traces with filters."""
        # Create schema
        await clickhouse_schema.create_tables()
        
        user_id = "query_test_user"
        start_time = datetime.now(timezone.utc)
        
        # Write multiple executions
        for i in range(5):
            await clickhouse_writer.write_execution(
                trace_id=str(uuid.uuid4()),
                execution_id=str(uuid.uuid4()),
                user_id=user_id,
                agent_type="query_agent",
                agent_name=f"Agent {i}",
                status=ExecutionStatus.COMPLETED,
                start_time=start_time + timedelta(minutes=i),
                end_time=start_time + timedelta(minutes=i, seconds=30),
                request_payload={"index": i}
            )
        
        # Flush
        await clickhouse_writer.flush_all()
        
        # Query with filters
        traces = await clickhouse_writer.get_execution_traces(
            user_id=user_id,
            start_time=start_time,
            limit=3
        )
        
        assert len(traces) <= 3
        assert all(t['user_id'] == user_id for t in traces)
        assert all(datetime.fromisoformat(str(t['start_time'])) >= start_time for t in traces)


# Integration test combining schema and writer
@pytest.mark.asyncio
async def test_full_trace_workflow():
    """Test complete trace workflow from schema creation to querying."""
    # Initialize components
    schema = ClickHouseTraceSchema(
        host='localhost',
        port=9000,
        database='netra_traces_integration',
        user='default',
        password=''
    )
    
    writer = ClickHouseTraceWriter(
        host='localhost',
        port=9000,
        database='netra_traces_integration',
        user='default',
        password='',
        batch_size=5,
        flush_interval=1.0
    )
    
    try:
        # Clean and create schema
        await schema.drop_all_tables()
        assert await schema.create_tables()
        
        # Start writer
        await writer.start()
        
        # Simulate agent execution workflow
        user_id = "integration_user"
        trace_id = str(uuid.uuid4())
        execution_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        # 1. Start execution
        await writer.write_execution(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            agent_type="integration_agent",
            agent_name="Integration Test",
            status=ExecutionStatus.RUNNING,
            start_time=start_time,
            request_payload={"task": "integration_test"}
        )
        
        # 2. Log events
        await writer.write_event(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            event_type=EventType.AGENT_STARTED,
            event_name="started",
            timestamp=start_time
        )
        
        # 3. Log metrics
        await writer.write_metric(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            metric_type=MetricType.LATENCY,
            metric_name="processing_time",
            value=150,
            timestamp=start_time,
            unit="ms"
        )
        
        # 4. Complete execution
        end_time = datetime.now(timezone.utc)
        await writer.write_execution(
            trace_id=trace_id,
            execution_id=execution_id,
            user_id=user_id,
            agent_type="integration_agent",
            agent_name="Integration Test",
            status=ExecutionStatus.COMPLETED,
            start_time=start_time,
            end_time=end_time,
            request_payload={"task": "integration_test"},
            response_payload={"result": "success"}
        )
        
        # 5. Flush and verify
        await writer.flush_all()
        
        # 6. Verify data
        stats = await schema.get_table_stats()
        assert stats['agent_executions'] > 0
        assert stats['agent_events'] > 0
        assert stats['performance_metrics'] > 0
        
        # 7. Query traces
        traces = await writer.get_execution_traces(user_id=user_id)
        assert len(traces) > 0
        assert traces[0]['trace_id'] == trace_id
        
    finally:
        # Cleanup
        await writer.stop()
        await schema.drop_all_tables()
        schema.close()