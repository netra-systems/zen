"""
Trace Persistence Manager for ExecutionTracker
==============================================
CRITICAL: This module persists agent execution traces to ClickHouse for observability.

Problem Solved:
- Agent executions lack persistent tracing
- No batch writing for performance
- No retry logic for failed writes
- No structured persistence layer

Solution:
- Buffered batch writer with configurable batch size
- Automatic flush on interval or buffer size
- Retry logic with exponential backoff
- Structured persistence interface
"""

import asyncio
import json
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from netra_backend.app.core.execution_tracker import ExecutionRecord, ExecutionState
from netra_backend.app.db.clickhouse import get_clickhouse_client
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ClickHouseTraceWriter:
    """Handles direct writes to ClickHouse trace tables."""
    
    async def create_tables_if_needed(self):
        """Create trace tables if they don't exist."""
        async with get_clickhouse_client() as client:
            # Create execution traces table
            await client.execute("""
                CREATE TABLE IF NOT EXISTS execution_traces (
                    execution_id UUID,
                    agent_name String,
                    correlation_id Nullable(String),
                    thread_id Nullable(String),
                    user_id Nullable(String),
                    state String,
                    start_time DateTime64(3),
                    end_time Nullable(DateTime64(3)),
                    duration_seconds Nullable(Float64),
                    error Nullable(String),
                    heartbeat_count UInt32,
                    websocket_updates_sent UInt32,
                    timeout_seconds Float64,
                    created_at DateTime64(3) DEFAULT now64(3),
                    date Date MATERIALIZED toDate(start_time)
                )
                ENGINE = MergeTree()
                PARTITION BY date
                ORDER BY (start_time, execution_id)
                TTL start_time + INTERVAL 30 DAY
                SETTINGS index_granularity = 8192
            """)
            
            # Create agent events table
            await client.execute("""
                CREATE TABLE IF NOT EXISTS agent_events (
                    execution_id UUID,
                    event_type String,
                    event_data String,
                    timestamp DateTime64(3),
                    agent_name String,
                    user_id Nullable(String),
                    thread_id Nullable(String),
                    created_at DateTime64(3) DEFAULT now64(3),
                    date Date MATERIALIZED toDate(timestamp)
                )
                ENGINE = MergeTree()
                PARTITION BY date
                ORDER BY (timestamp, execution_id)
                TTL timestamp + INTERVAL 7 DAY
                SETTINGS index_granularity = 8192
            """)
            
            # Create performance metrics table
            await client.execute("""
                CREATE TABLE IF NOT EXISTS execution_metrics (
                    execution_id UUID,
                    metric_type String,
                    metric_value Float64,
                    timestamp DateTime64(3),
                    agent_name String,
                    user_id Nullable(String),
                    metadata Nullable(String),
                    created_at DateTime64(3) DEFAULT now64(3),
                    date Date MATERIALIZED toDate(timestamp)
                )
                ENGINE = MergeTree()
                PARTITION BY date
                ORDER BY (timestamp, execution_id)
                TTL timestamp + INTERVAL 14 DAY
                SETTINGS index_granularity = 8192
            """)
            
            logger.info("Trace tables created/verified successfully")
    
    async def write_execution_trace(self, records: List[Dict[str, Any]]) -> bool:
        """Write execution trace records to ClickHouse."""
        if not records:
            return True
            
        try:
            async with get_clickhouse_client() as client:
                # Prepare batch insert data
                values = []
                for record in records:
                    values.append({
                        'execution_id': str(record['execution_id']),
                        'agent_name': record['agent_name'],
                        'correlation_id': record.get('correlation_id'),
                        'thread_id': record.get('thread_id'),
                        'user_id': record.get('user_id'),
                        'state': record['state'],
                        'start_time': datetime.fromtimestamp(record['start_time']),
                        'end_time': datetime.fromtimestamp(record['end_time']) if record.get('end_time') else None,
                        'duration_seconds': record.get('duration'),
                        'error': record.get('error'),
                        'heartbeat_count': record.get('heartbeat_count', 0),
                        'websocket_updates_sent': record.get('websocket_updates_sent', 0),
                        'timeout_seconds': record.get('timeout_seconds', 30.0)
                    })
                
                # Batch insert
                if values:
                    columns = list(values[0].keys())
                    for value in values:
                        await client.execute(
                            f"INSERT INTO execution_traces ({', '.join(columns)}) VALUES",
                            [value]
                        )
                    
                logger.debug(f"Written {len(records)} execution traces to ClickHouse")
                return True
                
        except Exception as e:
            logger.error(f"Failed to write execution traces: {e}")
            return False
    
    async def write_agent_event(self, events: List[Dict[str, Any]]) -> bool:
        """Write agent events to ClickHouse."""
        if not events:
            return True
            
        try:
            async with get_clickhouse_client() as client:
                for event in events:
                    await client.execute(
                        """INSERT INTO agent_events 
                        (execution_id, event_type, event_data, timestamp, agent_name, user_id, thread_id) 
                        VALUES""",
                        [{
                            'execution_id': str(event['execution_id']),
                            'event_type': event['event_type'],
                            'event_data': json.dumps(event.get('event_data', {})),
                            'timestamp': event.get('timestamp', datetime.now()),
                            'agent_name': event.get('agent_name', 'unknown'),
                            'user_id': event.get('user_id'),
                            'thread_id': event.get('thread_id')
                        }]
                    )
                
                logger.debug(f"Written {len(events)} agent events to ClickHouse")
                return True
                
        except Exception as e:
            logger.error(f"Failed to write agent events: {e}")
            return False
    
    async def write_performance_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """Write performance metrics to ClickHouse."""
        if not metrics:
            return True
            
        try:
            async with get_clickhouse_client() as client:
                for metric in metrics:
                    await client.execute(
                        """INSERT INTO execution_metrics 
                        (execution_id, metric_type, metric_value, timestamp, agent_name, user_id, metadata) 
                        VALUES""",
                        [{
                            'execution_id': str(metric['execution_id']),
                            'metric_type': metric['metric_type'],
                            'metric_value': metric['metric_value'],
                            'timestamp': metric.get('timestamp', datetime.now()),
                            'agent_name': metric.get('agent_name', 'unknown'),
                            'user_id': metric.get('user_id'),
                            'metadata': json.dumps(metric.get('metadata', {})) if metric.get('metadata') else None
                        }]
                    )
                
                logger.debug(f"Written {len(metrics)} performance metrics to ClickHouse")
                return True
                
        except Exception as e:
            logger.error(f"Failed to write performance metrics: {e}")
            return False


class TracePersistenceManager:
    """
    Manages buffered persistence of execution traces to ClickHouse.
    
    Features:
    - Buffered batch writing for performance
    - Automatic flush on interval or buffer size
    - Retry logic for failed writes
    - Separate buffers for different data types
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        max_retries: int = 3
    ):
        """
        Initialize the persistence manager.
        
        Args:
            batch_size: Maximum number of records before automatic flush
            flush_interval: Time in seconds between automatic flushes
            max_retries: Maximum number of retry attempts for failed writes
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries
        
        # Separate buffers for different data types
        self.execution_buffer: List[Dict[str, Any]] = []
        self.event_buffer: List[Dict[str, Any]] = []
        self.metrics_buffer: List[Dict[str, Any]] = []
        
        # ClickHouse writer
        self.clickhouse_writer = ClickHouseTraceWriter()
        
        # Flush task
        self.flush_task: Optional[asyncio.Task] = None
        
        # Lock for thread-safe buffer access
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'executions_persisted': 0,
            'events_persisted': 0,
            'metrics_persisted': 0,
            'flush_count': 0,
            'retry_count': 0,
            'failure_count': 0
        }
    
    async def start(self):
        """Start the persistence manager and create tables."""
        # Create tables if needed
        await self.clickhouse_writer.create_tables_if_needed()
        
        # Start flush task
        if not self.flush_task or self.flush_task.done():
            self.flush_task = asyncio.create_task(self._periodic_flush())
            logger.info("TracePersistenceManager started")
    
    async def stop(self):
        """Stop the persistence manager and flush remaining data."""
        # Cancel flush task
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
            self.flush_task = None
        
        # Final flush
        await self.flush_all()
        logger.info(f"TracePersistenceManager stopped. Stats: {self.stats}")
    
    async def _periodic_flush(self):
        """Periodically flush buffers."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
    
    async def persist_execution(self, record: ExecutionRecord):
        """
        Persist an execution record.
        
        Args:
            record: ExecutionRecord to persist
        """
        async with self._lock:
            # Convert to dict and add to buffer
            record_dict = record.to_dict()
            record_dict['duration'] = record.duration()
            self.execution_buffer.append(record_dict)
            
            # Check if buffer needs flushing
            if len(self.execution_buffer) >= self.batch_size:
                await self._flush_executions()
    
    async def persist_event(self, event: Dict[str, Any]):
        """
        Persist an agent event.
        
        Args:
            event: Event dictionary with execution_id, event_type, etc.
        """
        async with self._lock:
            self.event_buffer.append(event)
            
            if len(self.event_buffer) >= self.batch_size:
                await self._flush_events()
    
    async def persist_metrics(self, metrics: Dict[str, Any]):
        """
        Persist performance metrics.
        
        Args:
            metrics: Metrics dictionary with execution_id, metric_type, value, etc.
        """
        async with self._lock:
            self.metrics_buffer.append(metrics)
            
            if len(self.metrics_buffer) >= self.batch_size:
                await self._flush_metrics()
    
    async def flush_all(self):
        """Flush all buffers."""
        async with self._lock:
            await self._flush_executions()
            await self._flush_events()
            await self._flush_metrics()
            self.stats['flush_count'] += 1
    
    async def _flush_executions(self):
        """Flush execution buffer with retry logic."""
        if not self.execution_buffer:
            return
            
        buffer_copy = self.execution_buffer.copy()
        self.execution_buffer.clear()
        
        for attempt in range(self.max_retries):
            try:
                success = await self.clickhouse_writer.write_execution_trace(buffer_copy)
                if success:
                    self.stats['executions_persisted'] += len(buffer_copy)
                    return
                else:
                    self.stats['retry_count'] += 1
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                logger.error(f"Flush execution attempt {attempt + 1} failed: {e}")
                self.stats['retry_count'] += 1
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        self.stats['failure_count'] += 1
        logger.error(f"Failed to persist {len(buffer_copy)} execution records after {self.max_retries} attempts")
    
    async def _flush_events(self):
        """Flush event buffer with retry logic."""
        if not self.event_buffer:
            return
            
        buffer_copy = self.event_buffer.copy()
        self.event_buffer.clear()
        
        for attempt in range(self.max_retries):
            try:
                success = await self.clickhouse_writer.write_agent_event(buffer_copy)
                if success:
                    self.stats['events_persisted'] += len(buffer_copy)
                    return
                else:
                    self.stats['retry_count'] += 1
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Flush events attempt {attempt + 1} failed: {e}")
                self.stats['retry_count'] += 1
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        self.stats['failure_count'] += 1
        logger.error(f"Failed to persist {len(buffer_copy)} event records after {self.max_retries} attempts")
    
    async def _flush_metrics(self):
        """Flush metrics buffer with retry logic."""
        if not self.metrics_buffer:
            return
            
        buffer_copy = self.metrics_buffer.copy()
        self.metrics_buffer.clear()
        
        for attempt in range(self.max_retries):
            try:
                success = await self.clickhouse_writer.write_performance_metrics(buffer_copy)
                if success:
                    self.stats['metrics_persisted'] += len(buffer_copy)
                    return
                else:
                    self.stats['retry_count'] += 1
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Flush metrics attempt {attempt + 1} failed: {e}")
                self.stats['retry_count'] += 1
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        self.stats['failure_count'] += 1
        logger.error(f"Failed to persist {len(buffer_copy)} metric records after {self.max_retries} attempts")
    
    def get_stats(self) -> Dict[str, int]:
        """Get persistence statistics."""
        return self.stats.copy()


class ExecutionPersistence:
    """
    High-level interface for execution persistence.
    Provides simplified methods for common persistence operations.
    """
    
    def __init__(self, persistence_manager: Optional[TracePersistenceManager] = None):
        """
        Initialize with optional custom persistence manager.
        
        Args:
            persistence_manager: Custom persistence manager or None for default
        """
        self.manager = persistence_manager or TracePersistenceManager()
        self._started = False
    
    async def ensure_started(self):
        """Ensure the persistence manager is started."""
        if not self._started:
            await self.manager.start()
            self._started = True
    
    async def write_execution_start(self, execution_id: UUID, context: Dict[str, Any]) -> bool:
        """
        Write execution start event.
        
        Args:
            execution_id: Execution UUID
            context: Execution context (agent_name, user_id, etc.)
            
        Returns:
            True if successfully queued for persistence
        """
        await self.ensure_started()
        
        event = {
            'execution_id': execution_id,
            'event_type': 'execution_start',
            'event_data': context,
            'timestamp': datetime.now(),
            'agent_name': context.get('agent_name', 'unknown'),
            'user_id': context.get('user_id'),
            'thread_id': context.get('thread_id')
        }
        
        await self.manager.persist_event(event)
        return True
    
    async def write_execution_update(self, execution_id: UUID, state: str, metadata: Optional[Dict] = None) -> bool:
        """
        Write execution state update.
        
        Args:
            execution_id: Execution UUID
            state: New state
            metadata: Optional metadata
            
        Returns:
            True if successfully queued for persistence
        """
        await self.ensure_started()
        
        event = {
            'execution_id': execution_id,
            'event_type': 'state_change',
            'event_data': {
                'new_state': state,
                'metadata': metadata or {}
            },
            'timestamp': datetime.now(),
            'agent_name': metadata.get('agent_name', 'unknown') if metadata else 'unknown',
            'user_id': metadata.get('user_id') if metadata else None,
            'thread_id': metadata.get('thread_id') if metadata else None
        }
        
        await self.manager.persist_event(event)
        return True
    
    async def write_execution_complete(self, execution_id: UUID, result: Dict[str, Any]) -> bool:
        """
        Write execution completion.
        
        Args:
            execution_id: Execution UUID
            result: Execution result including state, error, duration, etc.
            
        Returns:
            True if successfully queued for persistence
        """
        await self.ensure_started()
        
        # Persist completion event
        event = {
            'execution_id': execution_id,
            'event_type': 'execution_complete',
            'event_data': result,
            'timestamp': datetime.now(),
            'agent_name': result.get('agent_name', 'unknown'),
            'user_id': result.get('user_id'),
            'thread_id': result.get('thread_id')
        }
        
        await self.manager.persist_event(event)
        return True
    
    async def write_performance_metrics(self, execution_id: UUID, metrics: Dict[str, Any]) -> bool:
        """
        Write performance metrics.
        
        Args:
            execution_id: Execution UUID
            metrics: Performance metrics dictionary
            
        Returns:
            True if successfully queued for persistence
        """
        await self.ensure_started()
        
        # Write individual metrics
        for metric_type, metric_value in metrics.items():
            if isinstance(metric_value, (int, float)):
                metric_record = {
                    'execution_id': execution_id,
                    'metric_type': metric_type,
                    'metric_value': float(metric_value),
                    'timestamp': datetime.now(),
                    'agent_name': metrics.get('agent_name', 'unknown'),
                    'user_id': metrics.get('user_id')
                }
                await self.manager.persist_metrics(metric_record)
        
        return True
    
    async def persist_execution_record(self, record: ExecutionRecord):
        """
        Persist a complete execution record.
        
        Args:
            record: ExecutionRecord to persist
        """
        await self.ensure_started()
        await self.manager.persist_execution(record)
    
    async def flush(self):
        """Force flush all pending writes."""
        await self.manager.flush_all()
    
    async def shutdown(self):
        """Shutdown persistence and flush remaining data."""
        if self._started:
            await self.manager.stop()
            self._started = False
    
    def get_stats(self) -> Dict[str, int]:
        """Get persistence statistics."""
        return self.manager.get_stats()


# Global instance for easy access
_global_persistence: Optional[ExecutionPersistence] = None


def get_execution_persistence() -> ExecutionPersistence:
    """Get or create global execution persistence instance."""
    global _global_persistence
    if _global_persistence is None:
        _global_persistence = ExecutionPersistence()
    return _global_persistence


async def init_execution_persistence():
    """Initialize global execution persistence."""
    persistence = get_execution_persistence()
    await persistence.ensure_started()
    logger.info("Execution persistence initialized")
    return persistence