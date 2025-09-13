"""
ClickHouse Trace Writer for High-Performance Trace Persistence
Provides batched, async writing of trace data to ClickHouse
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum
import logging
from collections import defaultdict
import time

from clickhouse_driver import Client
from clickhouse_driver.errors import ServerException
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

logger = logging.getLogger(__name__)


class EventType(Enum):
    """WebSocket and tool event types."""
    AGENT_STARTED = 1
    AGENT_THINKING = 2
    TOOL_EXECUTING = 3
    TOOL_COMPLETED = 4
    AGENT_COMPLETED = 5
    WEBSOCKET_SENT = 6
    WEBSOCKET_RECEIVED = 7
    ERROR_OCCURRED = 8
    CUSTOM = 9


class ExecutionStatus(Enum):
    """Agent execution status."""
    PENDING = 1
    RUNNING = 2
    COMPLETED = 3
    FAILED = 4
    CANCELLED = 5


class ErrorType(Enum):
    """Error categorization."""
    VALIDATION = 1
    AUTHENTICATION = 2
    AUTHORIZATION = 3
    NETWORK = 4
    DATABASE = 5
    LLM = 6
    TOOL = 7
    TIMEOUT = 8
    RATE_LIMIT = 9
    SYSTEM = 10
    UNKNOWN = 11


class MetricType(Enum):
    """Performance metric types."""
    LATENCY = 1
    THROUGHPUT = 2
    RESOURCE = 3
    LLM = 4
    DATABASE = 5
    NETWORK = 6
    CUSTOM = 7


class ClickHouseTraceWriter:
    """
    High-performance trace writer for ClickHouse.
    Supports batched writes, async operations, and automatic retries.
    """
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 9000,
        database: str = 'netra_traces',
        user: str = 'default',
        password: str = '',
        batch_size: int = 1000,
        flush_interval: float = 5.0,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize trace writer with batching configuration."""
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        self.client_kwargs = kwargs
        
        # Batch buffers for each table
        self._buffers: Dict[str, List[Dict]] = defaultdict(list)
        self._buffer_lock = asyncio.Lock()
        
        # Client connection
        self._client: Optional[Client] = None
        
        # Background flush task
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Statistics
        self._stats = {
            'total_writes': 0,
            'failed_writes': 0,
            'batch_flushes': 0,
            'retries': 0
        }
    
    async def start(self):
        """Start the background flush task."""
        if not self._running:
            self._running = True
            self._flush_task = asyncio.create_task(self._background_flush())
            logger.info("ClickHouse trace writer started")
    
    async def stop(self):
        """Stop the writer and flush remaining data."""
        self._running = False
        
        # Final flush
        await self.flush_all()
        
        # Cancel background task
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if self._client:
            self._client.disconnect()
            self._client = None
        
        logger.info(f"ClickHouse trace writer stopped. Stats: {self._stats}")
    
    def _get_client(self) -> Client:
        """Get or create ClickHouse client."""
        if self._client is None:
            self._client = Client(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                **self.client_kwargs
            )
        return self._client
    
    # Core write methods for each table
    
    async def write_execution(
        self,
        trace_id: str,
        execution_id: str,
        user_id: str,
        agent_type: str,
        agent_name: str,
        status: Union[ExecutionStatus, str],
        start_time: datetime,
        request_payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        agent_version: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        end_time: Optional[datetime] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_stack: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        **metrics
    ):
        """Write agent execution record."""
        if isinstance(status, ExecutionStatus):
            status = status.value
        elif isinstance(status, str):
            status = ExecutionStatus[status.upper()].value
        
        duration_ms = 0
        if end_time:
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        record = {
            'trace_id': trace_id,
            'execution_id': execution_id,
            'correlation_id': correlation_id or UnifiedIDManager().generate_id(IDType.TRACE, prefix="corr"),
            'user_id': user_id,
            'organization_id': organization_id or 'default',
            'agent_type': agent_type,
            'agent_name': agent_name,
            'agent_version': agent_version or '1.0.0',
            'parent_agent_id': parent_agent_id,
            'status': status,
            'start_time': start_time,
            'end_time': end_time,
            'duration_ms': duration_ms,
            'request_payload': json.dumps(request_payload),
            'response_payload': json.dumps(response_payload) if response_payload else '',
            'error_message': error_message,
            'error_stack': error_stack,
            'cpu_time_ms': metrics.get('cpu_time_ms', 0),
            'memory_mb': metrics.get('memory_mb', 0),
            'token_count': metrics.get('token_count', 0),
            'tool_calls_count': metrics.get('tool_calls_count', 0),
            'environment': metrics.get('environment', 'development'),
            'service_version': metrics.get('service_version', '1.0.0'),
            'metadata': json.dumps(metadata) if metadata else '{}',
            'tags': tags or [],
            'created_at': datetime.now(timezone.utc),
            'partition_date': start_time.date()
        }
        
        await self._add_to_buffer('agent_executions', record)
    
    async def write_event(
        self,
        trace_id: str,
        execution_id: str,
        user_id: str,
        event_type: Union[EventType, str],
        event_name: str,
        timestamp: datetime,
        correlation_id: Optional[str] = None,
        event_category: Optional[str] = None,
        event_payload: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
        tool_output: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        sequence_number: Optional[int] = None,
        session_id: Optional[str] = None,
        client_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Write agent event record."""
        if isinstance(event_type, EventType):
            event_type = event_type.value
        elif isinstance(event_type, str):
            event_type = EventType[event_type.upper()].value
        
        id_manager = UnifiedIDManager()
        record = {
            'event_id': id_manager.generate_id(IDType.TRACE, prefix="event"),
            'trace_id': trace_id,
            'execution_id': execution_id,
            'correlation_id': correlation_id or id_manager.generate_id(IDType.TRACE, prefix="corr_evt"),
            'user_id': user_id,
            'event_type': event_type,
            'event_name': event_name,
            'event_category': event_category or 'default',
            'event_payload': json.dumps(event_payload) if event_payload else '{}',
            'tool_name': tool_name,
            'tool_input': json.dumps(tool_input) if tool_input else None,
            'tool_output': json.dumps(tool_output) if tool_output else None,
            'timestamp': timestamp,
            'duration_ms': duration_ms,
            'sequence_number': sequence_number or 0,
            'session_id': session_id or '',
            'client_id': client_id or '',
            'metadata': json.dumps(metadata) if metadata else '{}',
            'created_at': datetime.now(timezone.utc),
            'partition_date': timestamp.date()
        }
        
        await self._add_to_buffer('agent_events', record)
    
    async def write_metric(
        self,
        trace_id: str,
        execution_id: str,
        user_id: str,
        metric_type: Union[MetricType, str],
        metric_name: str,
        value: float,
        timestamp: datetime,
        unit: str = 'ms',
        metric_category: Optional[str] = None,
        operation_name: Optional[str] = None,
        component_name: Optional[str] = None,
        model_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **timing_breakdown
    ):
        """Write performance metric record."""
        if isinstance(metric_type, MetricType):
            metric_type = metric_type.value
        elif isinstance(metric_type, str):
            metric_type = MetricType[metric_type.upper()].value
        
        record = {
            'metric_id': UnifiedIDManager().generate_id(IDType.METRIC, prefix="metric"),
            'trace_id': trace_id,
            'execution_id': execution_id,
            'user_id': user_id,
            'metric_type': metric_type,
            'metric_name': metric_name,
            'metric_category': metric_category or 'default',
            'value': value,
            'unit': unit,
            'total_time_ms': timing_breakdown.get('total_time_ms', 0),
            'llm_time_ms': timing_breakdown.get('llm_time_ms', 0),
            'tool_time_ms': timing_breakdown.get('tool_time_ms', 0),
            'database_time_ms': timing_breakdown.get('database_time_ms', 0),
            'network_time_ms': timing_breakdown.get('network_time_ms', 0),
            'processing_time_ms': timing_breakdown.get('processing_time_ms', 0),
            'cpu_percent': timing_breakdown.get('cpu_percent', 0.0),
            'memory_mb': timing_breakdown.get('memory_mb', 0.0),
            'disk_io_mb': timing_breakdown.get('disk_io_mb', 0.0),
            'network_io_mb': timing_breakdown.get('network_io_mb', 0.0),
            'prompt_tokens': timing_breakdown.get('prompt_tokens', 0),
            'completion_tokens': timing_breakdown.get('completion_tokens', 0),
            'total_tokens': timing_breakdown.get('total_tokens', 0),
            'model_name': model_name or '',
            'operation_name': operation_name or '',
            'component_name': component_name or '',
            'metadata': json.dumps(metadata) if metadata else '{}',
            'timestamp': timestamp,
            'created_at': datetime.now(timezone.utc),
            'partition_date': timestamp.date()
        }
        
        await self._add_to_buffer('performance_metrics', record)
    
    async def write_correlation(
        self,
        parent_trace_id: str,
        child_trace_id: str,
        relationship_type: str = 'parent_child',
        parent_agent_type: Optional[str] = None,
        child_agent_type: Optional[str] = None,
        parent_start_time: Optional[datetime] = None,
        child_start_time: Optional[datetime] = None,
        depth_level: int = 0,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """Write trace correlation record."""
        overlap_duration_ms = 0
        if parent_start_time and child_start_time:
            overlap_duration_ms = abs(int((child_start_time - parent_start_time).total_seconds() * 1000))
        
        record = {
            'correlation_id': UnifiedIDManager().generate_id(IDType.TRACE, prefix="corr_meta"),
            'parent_trace_id': parent_trace_id,
            'child_trace_id': child_trace_id,
            'relationship_type': relationship_type,
            'relationship_name': f"{parent_agent_type}->{child_agent_type}" if parent_agent_type and child_agent_type else '',
            'parent_agent_type': parent_agent_type or '',
            'child_agent_type': child_agent_type or '',
            'depth_level': depth_level,
            'parent_start_time': parent_start_time or datetime.now(timezone.utc),
            'child_start_time': child_start_time or datetime.now(timezone.utc),
            'overlap_duration_ms': overlap_duration_ms,
            'context': json.dumps(context) if context else '{}',
            'tags': tags or [],
            'created_at': datetime.now(timezone.utc),
            'partition_date': datetime.now(timezone.utc).date()
        }
        
        await self._add_to_buffer('trace_correlations', record)
    
    async def write_error(
        self,
        trace_id: str,
        execution_id: str,
        user_id: str,
        error_type: Union[ErrorType, str],
        error_message: str,
        timestamp: datetime,
        error_code: Optional[str] = None,
        error_category: Optional[str] = None,
        severity: str = 'error',
        error_stack: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None,
        service_name: Optional[str] = None,
        component_name: Optional[str] = None,
        function_name: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        is_recoverable: bool = False,
        retry_count: int = 0,
        max_retries: int = 3,
        recovery_action: Optional[str] = None,
        affected_users: Optional[List[str]] = None,
        affected_features: Optional[List[str]] = None,
        business_impact: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ):
        """Write error log record."""
        if isinstance(error_type, ErrorType):
            error_type = error_type.value
        elif isinstance(error_type, str):
            error_type = ErrorType[error_type.upper()].value
        
        # Map severity string to enum value
        severity_map = {
            'debug': 1,
            'info': 2,
            'warning': 3,
            'error': 4,
            'critical': 5
        }
        severity_value = severity_map.get(severity.lower(), 4)
        
        record = {
            'error_id': UnifiedIDManager().generate_id(IDType.TRACE, prefix="error"),
            'trace_id': trace_id,
            'execution_id': execution_id,
            'user_id': user_id,
            'error_type': error_type,
            'error_code': error_code or 'UNKNOWN',
            'error_category': error_category or 'default',
            'severity': severity_value,
            'error_message': error_message,
            'error_stack': error_stack or '',
            'error_context': json.dumps(error_context) if error_context else '{}',
            'service_name': service_name or '',
            'component_name': component_name or '',
            'function_name': function_name or '',
            'file_path': file_path or '',
            'line_number': line_number or 0,
            'is_recoverable': is_recoverable,
            'retry_count': retry_count,
            'max_retries': max_retries,
            'recovery_action': recovery_action or '',
            'affected_users': affected_users or [],
            'affected_features': affected_features or [],
            'business_impact': business_impact or '',
            'environment': 'development',
            'version': '1.0.0',
            'metadata': json.dumps(metadata) if metadata else '{}',
            'tags': tags or [],
            'timestamp': timestamp,
            'created_at': datetime.now(timezone.utc),
            'partition_date': timestamp.date()
        }
        
        await self._add_to_buffer('error_logs', record)
    
    # Batch management
    
    async def _add_to_buffer(self, table: str, record: Dict[str, Any]):
        """Add record to buffer for batched writing."""
        async with self._buffer_lock:
            self._buffers[table].append(record)
            
            # Auto-flush if batch size reached
            if len(self._buffers[table]) >= self.batch_size:
                await self._flush_table(table)
    
    async def _flush_table(self, table: str):
        """Flush buffered records for a specific table."""
        if not self._buffers[table]:
            return
        
        records = self._buffers[table]
        self._buffers[table] = []
        
        try:
            client = self._get_client()
            
            # Prepare column names and values
            if records:
                columns = list(records[0].keys())
                values = [tuple(r[col] for col in columns) for r in records]
                
                # Build insert query
                query = f"INSERT INTO {self.database}.{table} ({','.join(columns)}) VALUES"
                
                # Execute with retry logic
                for retry in range(self.max_retries):
                    try:
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            client.execute,
                            query,
                            values
                        )
                        
                        self._stats['total_writes'] += len(records)
                        self._stats['batch_flushes'] += 1
                        logger.debug(f"Flushed {len(records)} records to {table}")
                        break
                        
                    except ServerException as e:
                        self._stats['retries'] += 1
                        if retry == self.max_retries - 1:
                            raise
                        await asyncio.sleep(0.5 * (retry + 1))
                
        except Exception as e:
            self._stats['failed_writes'] += len(records)
            logger.error(f"Failed to flush {len(records)} records to {table}: {e}")
            
            # Return records to buffer for retry
            async with self._buffer_lock:
                self._buffers[table].extend(records)
    
    async def flush_all(self):
        """Flush all buffered data to ClickHouse."""
        tables = list(self._buffers.keys())
        for table in tables:
            await self._flush_table(table)
    
    async def _background_flush(self):
        """Background task to periodically flush buffers."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background flush: {e}")
    
    # Query methods for verification
    
    async def get_execution_traces(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query execution traces with filters."""
        client = self._get_client()
        
        conditions = []
        if user_id:
            conditions.append(f"user_id = '{user_id}'")
        if start_time:
            conditions.append(f"start_time >= '{start_time}'")
        if end_time:
            conditions.append(f"end_time <= '{end_time}'")
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
        SELECT * FROM {self.database}.agent_executions
        {where_clause}
        ORDER BY start_time DESC
        LIMIT {limit}
        """
        
        result = await asyncio.get_event_loop().run_in_executor(
            None, client.execute, query, with_column_types=True
        )
        
        if not result:
            return []
        
        columns = [col[0] for col in result[1]]
        rows = result[0]
        
        return [dict(zip(columns, row)) for row in rows]
    
    def get_stats(self) -> Dict[str, int]:
        """Get writer statistics."""
        return self._stats.copy()


# Convenience class for trace context management

class TraceContext:
    """Context manager for automatic trace writing."""
    
    def __init__(
        self,
        writer: ClickHouseTraceWriter,
        user_id: str,
        agent_type: str,
        agent_name: str
    ):
        self.writer = writer
        self.user_id = user_id
        self.agent_type = agent_type
        self.agent_name = agent_name
        
        id_manager = UnifiedIDManager()
        self.trace_id = id_manager.generate_id(IDType.TRACE, prefix="batch")
        self.execution_id = id_manager.generate_id(IDType.EXECUTION, prefix="batch")
        self.correlation_id = id_manager.generate_id(IDType.TRACE, prefix="batch_corr")
        
        self.start_time = None
        self.event_sequence = 0
        
    async def __aenter__(self):
        """Start trace context."""
        self.start_time = datetime.now(timezone.utc)
        
        # Write execution start
        await self.writer.write_execution(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            user_id=self.user_id,
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            status=ExecutionStatus.RUNNING,
            start_time=self.start_time,
            request_payload={},
            correlation_id=self.correlation_id
        )
        
        # Write start event
        await self.writer.write_event(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            user_id=self.user_id,
            event_type=EventType.AGENT_STARTED,
            event_name='agent_started',
            timestamp=self.start_time,
            correlation_id=self.correlation_id
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Complete trace context."""
        end_time = datetime.now(timezone.utc)
        
        if exc_type:
            # Write error
            await self.writer.write_error(
                trace_id=self.trace_id,
                execution_id=self.execution_id,
                user_id=self.user_id,
                error_type=ErrorType.SYSTEM,
                error_message=str(exc_val),
                timestamp=end_time,
                error_stack=str(exc_tb)
            )
            
            status = ExecutionStatus.FAILED
        else:
            status = ExecutionStatus.COMPLETED
        
        # Update execution status
        await self.writer.write_execution(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            user_id=self.user_id,
            agent_type=self.agent_type,
            agent_name=self.agent_name,
            status=status,
            start_time=self.start_time,
            end_time=end_time,
            request_payload={},
            correlation_id=self.correlation_id
        )
        
        # Write completion event
        await self.writer.write_event(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            user_id=self.user_id,
            event_type=EventType.AGENT_COMPLETED,
            event_name='agent_completed',
            timestamp=end_time,
            correlation_id=self.correlation_id,
            sequence_number=self._get_next_sequence()
        )
    
    def _get_next_sequence(self) -> int:
        """Get next event sequence number."""
        self.event_sequence += 1
        return self.event_sequence
    
    async def log_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ):
        """Log tool execution within trace context."""
        timestamp = datetime.now(timezone.utc)
        
        # Log tool start
        await self.writer.write_event(
            trace_id=self.trace_id,
            execution_id=self.execution_id,
            user_id=self.user_id,
            event_type=EventType.TOOL_EXECUTING,
            event_name='tool_executing',
            timestamp=timestamp,
            correlation_id=self.correlation_id,
            tool_name=tool_name,
            tool_input=tool_input,
            sequence_number=self._get_next_sequence()
        )
        
        # Log tool completion if output provided
        if tool_output is not None:
            await self.writer.write_event(
                trace_id=self.trace_id,
                execution_id=self.execution_id,
                user_id=self.user_id,
                event_type=EventType.TOOL_COMPLETED,
                event_name='tool_completed',
                timestamp=timestamp,
                correlation_id=self.correlation_id,
                tool_name=tool_name,
                tool_output=tool_output,
                duration_ms=duration_ms,
                sequence_number=self._get_next_sequence()
            )