"""Observability Pipeline - SSOT for Monitoring, Metrics, Logs, and Traces

This module provides the unified observability pipeline for comprehensive system monitoring.
It integrates metrics collection, log aggregation, and distributed tracing following SSOT principles.

Business Value Justification (BVJ):
- Segment: Platform/Internal + Enterprise customers
- Business Goal: Enable proactive monitoring and issue resolution
- Value Impact: Observability prevents outages and enables SLA compliance
- Strategic Impact: Transparency builds customer trust and enables premium pricing

SSOT Compliance:
- Integrates with existing monitoring services as SSOT
- Uses existing metrics and alerting services
- Provides unified interface for all observability data
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.monitoring.metrics_service import MetricsService
from netra_backend.app.services.monitoring.alerting_service import AlertingService
from netra_backend.app.redis_manager import redis_manager

logger = central_logger.get_logger(__name__)


class PipelineComponent(Enum):
    """Observability pipeline components."""
    METRICS = "metrics"
    LOGS = "logs"
    TRACES = "traces"
    ALERTS = "alerts"


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PipelineStats:
    """Statistics for observability pipeline."""
    pipeline_id: str
    components_active: List[str]
    metrics_processed: int = 0
    logs_processed: int = 0
    traces_processed: int = 0
    alerts_triggered: int = 0
    processing_errors: int = 0
    start_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None


@dataclass
class MetricData:
    """Metric data structure."""
    name: str
    value: Union[int, float]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class LogData:
    """Log data structure."""
    level: str
    message: str
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


@dataclass
class TraceData:
    """Trace data structure."""
    trace_id: str
    span_id: str
    operation_name: str
    start_time: datetime
    duration_ms: float
    tags: Dict[str, str] = field(default_factory=dict)
    status: str = "ok"


class ObservabilityPipeline:
    """SSOT Observability Pipeline - unified monitoring, metrics, logs, and traces.
    
    This class provides comprehensive observability capabilities while using
    existing monitoring services as SSOT implementations.
    """
    
    def __init__(self):
        """Initialize ObservabilityPipeline using SSOT pattern."""
        # Initialize services with fallback for testing
        try:
            self._metrics_service = MetricsService()
        except Exception as e:
            logger.warning(f"Failed to initialize MetricsService: {e}")
            self._metrics_service = None
            
        try:
            self._alerting_service = AlertingService()
        except Exception as e:
            logger.warning(f"Failed to initialize AlertingService: {e}")
            self._alerting_service = None
            
        self._redis_client = None
        self._active_pipelines: Dict[str, PipelineStats] = {}
        self._processing_tasks: Dict[str, asyncio.Task] = {}
        logger.debug("ObservabilityPipeline initialized using SSOT monitoring services")
    
    async def _get_redis(self):
        """Get Redis client lazily."""
        if not self._redis_client:
            self._redis_client = await redis_manager.get_client()
        return self._redis_client
    
    async def start_pipeline(
        self,
        components: List[str],
        test_prefix: Optional[str] = None,
        pipeline_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start observability pipeline with specified components.
        
        Args:
            components: List of components to enable (metrics, logs, traces, alerts)
            test_prefix: Optional test prefix for isolation
            pipeline_config: Optional configuration for pipeline components
            
        Returns:
            Pipeline ID for tracking
        """
        try:
            pipeline_id = str(uuid.uuid4())
            
            # Validate components
            valid_components = [comp for comp in components if comp in [c.value for c in PipelineComponent]]
            if not valid_components:
                raise ValueError("No valid components specified")
            
            # Create pipeline stats
            pipeline_stats = PipelineStats(
                pipeline_id=pipeline_id,
                components_active=valid_components,
                start_time=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc)
            )
            
            # Store pipeline stats
            self._active_pipelines[pipeline_id] = pipeline_stats
            
            # Store in Redis for persistence
            await self._store_pipeline_stats(pipeline_stats)
            
            # Start processing task
            processing_task = asyncio.create_task(
                self._run_pipeline_processing(pipeline_id, valid_components, test_prefix)
            )
            self._processing_tasks[pipeline_id] = processing_task
            
            logger.info(f"Started observability pipeline {pipeline_id} with components: {valid_components}")
            return pipeline_id
            
        except Exception as e:
            logger.error(f"Failed to start observability pipeline: {e}")
            raise
    
    async def stop_pipeline(self, pipeline_id: str) -> bool:
        """Stop observability pipeline.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            True if stopped successfully
        """
        try:
            if pipeline_id in self._processing_tasks:
                task = self._processing_tasks.pop(pipeline_id)
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            if pipeline_id in self._active_pipelines:
                del self._active_pipelines[pipeline_id]
            
            # Clean up from Redis
            await self._cleanup_pipeline_data(pipeline_id)
            
            logger.info(f"Stopped observability pipeline {pipeline_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop pipeline {pipeline_id}: {e}")
            return False
    
    async def get_pipeline_stats(self, pipeline_id: str) -> Optional[PipelineStats]:
        """Get pipeline statistics.
        
        Args:
            pipeline_id: Pipeline identifier
            
        Returns:
            PipelineStats object or None if not found
        """
        try:
            # Check active pipelines first
            if pipeline_id in self._active_pipelines:
                return self._active_pipelines[pipeline_id]
            
            # Check Redis
            redis_client = await self._get_redis()
            stats_data = await redis_client.get(f"pipeline:stats:{pipeline_id}")
            
            if stats_data:
                stats_dict = json.loads(stats_data)
                return self._dict_to_pipeline_stats(stats_dict)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get pipeline stats for {pipeline_id}: {e}")
            return None
    
    async def emit_metric(
        self,
        name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]] = None,
        metric_type: MetricType = MetricType.GAUGE
    ) -> bool:
        """Emit a metric to the observability pipeline.
        
        Args:
            name: Metric name
            value: Metric value
            tags: Optional tags for the metric
            metric_type: Type of metric (counter, gauge, histogram, timer)
            
        Returns:
            True if emitted successfully
        """
        try:
            metric_data = MetricData(
                name=name,
                value=value,
                timestamp=datetime.now(timezone.utc),
                tags=tags or {},
                metric_type=metric_type
            )
            
            # Store metric data
            await self._store_metric_data(metric_data)
            
            # Update pipeline stats for active pipelines with metrics component
            for pipeline_id, stats in self._active_pipelines.items():
                if PipelineComponent.METRICS.value in stats.components_active:
                    stats.metrics_processed += 1
                    stats.last_activity = datetime.now(timezone.utc)
            
            # Send to metrics service (SSOT) if available
            if self._metrics_service:
                await self._metrics_service.record_metric(
                    metric_name=name,
                    value=value,
                    tags=tags,
                    timestamp=metric_data.timestamp
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit metric {name}: {e}")
            return False
    
    async def cleanup_test_data(self, test_prefix: str) -> int:
        """Clean up test data from the pipeline.
        
        Args:
            test_prefix: Test prefix to clean up
            
        Returns:
            Number of items cleaned up
        """
        try:
            redis_client = await self._get_redis()
            
            # Clean up metrics
            metric_keys = await redis_client.keys(f"metric:{test_prefix}:*")
            
            # Clean up logs  
            log_keys = await redis_client.keys(f"log:{test_prefix}:*")
            
            # Clean up traces
            trace_keys = await redis_client.keys(f"trace:{test_prefix}:*")
            
            # Clean up pipeline data
            pipeline_keys = await redis_client.keys(f"pipeline:*:{test_prefix}:*")
            
            all_keys = metric_keys + log_keys + trace_keys + pipeline_keys
            
            if all_keys:
                await redis_client.delete(*all_keys)
            
            cleaned_count = len(all_keys)
            logger.info(f"Cleaned up {cleaned_count} test data items for prefix {test_prefix}")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup test data for {test_prefix}: {e}")
            return 0
    
    # Private helper methods
    
    async def _run_pipeline_processing(
        self,
        pipeline_id: str,
        components: List[str],
        test_prefix: Optional[str]
    ) -> None:
        """Run pipeline processing loop."""
        try:
            while pipeline_id in self._active_pipelines:
                # Process each component
                for component in components:
                    await self._process_component_data(pipeline_id, component, test_prefix)
                
                # Brief pause between processing cycles
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logger.debug(f"Pipeline processing cancelled for {pipeline_id}")
        except Exception as e:
            logger.error(f"Pipeline processing error for {pipeline_id}: {e}")
    
    async def _process_component_data(
        self,
        pipeline_id: str,
        component: str,
        test_prefix: Optional[str]
    ) -> None:
        """Process data for specific component."""
        try:
            if component == PipelineComponent.METRICS.value:
                await self._process_metrics_data(pipeline_id, test_prefix)
            elif component == PipelineComponent.LOGS.value:
                await self._process_logs_data(pipeline_id, test_prefix)
            elif component == PipelineComponent.TRACES.value:
                await self._process_traces_data(pipeline_id, test_prefix)
            elif component == PipelineComponent.ALERTS.value:
                await self._process_alerts_data(pipeline_id, test_prefix)
                
        except Exception as e:
            logger.error(f"Error processing {component} data for pipeline {pipeline_id}: {e}")
            if pipeline_id in self._active_pipelines:
                self._active_pipelines[pipeline_id].processing_errors += 1
    
    async def _process_metrics_data(self, pipeline_id: str, test_prefix: Optional[str]) -> None:
        """Process metrics data."""
        try:
            redis_client = await self._get_redis()
            pattern = f"metric:{test_prefix or '*'}:*"
            metric_keys = await redis_client.keys(pattern)
            
            processed_count = 0
            for key in metric_keys[:100]:  # Process in batches
                metric_data = await redis_client.get(key)
                if metric_data:
                    # Process metric data (validation, aggregation, etc.)
                    processed_count += 1
            
            if processed_count > 0 and pipeline_id in self._active_pipelines:
                self._active_pipelines[pipeline_id].metrics_processed += processed_count
                
        except Exception as e:
            logger.error(f"Error processing metrics data: {e}")
    
    async def _process_logs_data(self, pipeline_id: str, test_prefix: Optional[str]) -> None:
        """Process logs data."""
        try:
            redis_client = await self._get_redis()
            pattern = f"log:{test_prefix or '*'}:*"
            log_keys = await redis_client.keys(pattern)
            
            processed_count = 0
            for key in log_keys[:100]:  # Process in batches
                log_data = await redis_client.get(key)
                if log_data:
                    # Process log data (parsing, filtering, etc.)
                    processed_count += 1
            
            if processed_count > 0 and pipeline_id in self._active_pipelines:
                self._active_pipelines[pipeline_id].logs_processed += processed_count
                
        except Exception as e:
            logger.error(f"Error processing logs data: {e}")
    
    async def _process_traces_data(self, pipeline_id: str, test_prefix: Optional[str]) -> None:
        """Process traces data."""
        try:
            redis_client = await self._get_redis()
            pattern = f"trace:{test_prefix or '*'}:*"
            trace_keys = await redis_client.keys(pattern)
            
            processed_count = 0
            for key in trace_keys[:100]:  # Process in batches
                trace_data = await redis_client.get(key)
                if trace_data:
                    # Process trace data (correlation, analysis, etc.)
                    processed_count += 1
            
            if processed_count > 0 and pipeline_id in self._active_pipelines:
                self._active_pipelines[pipeline_id].traces_processed += processed_count
                
        except Exception as e:
            logger.error(f"Error processing traces data: {e}")
    
    async def _process_alerts_data(self, pipeline_id: str, test_prefix: Optional[str]) -> None:
        """Process alerts data."""
        try:
            # Check for alert conditions
            redis_client = await self._get_redis()
            
            # Example: Check for high error rates
            error_pattern = f"error:{test_prefix or '*'}:*"
            error_keys = await redis_client.keys(error_pattern)
            
            if len(error_keys) > 10:  # Threshold for alert
                # Trigger alert via SSOT alerting service if available
                if self._alerting_service:
                    await self._alerting_service.trigger_alert(
                        alert_name=f"High Error Rate - {test_prefix or 'system'}",
                        severity="high",
                        description=f"Detected {len(error_keys)} errors in observability pipeline",
                        context={"pipeline_id": pipeline_id, "error_count": len(error_keys)}
                    )
                
                if pipeline_id in self._active_pipelines:
                    self._active_pipelines[pipeline_id].alerts_triggered += 1
                
        except Exception as e:
            logger.error(f"Error processing alerts data: {e}")
    
    async def _store_metric_data(self, metric_data: MetricData) -> None:
        """Store metric data in Redis."""
        try:
            redis_client = await self._get_redis()
            
            metric_dict = {
                "name": metric_data.name,
                "value": metric_data.value,
                "timestamp": metric_data.timestamp.isoformat(),
                "tags": metric_data.tags,
                "metric_type": metric_data.metric_type.value
            }
            
            # Store with time-based key for ordering
            timestamp_key = int(metric_data.timestamp.timestamp())
            key = f"metric:{metric_data.name}:{timestamp_key}"
            
            await redis_client.set(key, json.dumps(metric_dict), ex=3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store metric data: {e}")
    
    async def _store_pipeline_stats(self, stats: PipelineStats) -> None:
        """Store pipeline stats in Redis."""
        try:
            redis_client = await self._get_redis()
            
            stats_dict = self._pipeline_stats_to_dict(stats)
            key = f"pipeline:stats:{stats.pipeline_id}"
            
            await redis_client.set(key, json.dumps(stats_dict), ex=86400)  # 24 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store pipeline stats: {e}")
    
    async def _cleanup_pipeline_data(self, pipeline_id: str) -> None:
        """Clean up pipeline data from Redis."""
        try:
            redis_client = await self._get_redis()
            
            # Clean up pipeline stats
            await redis_client.delete(f"pipeline:stats:{pipeline_id}")
            
            # Clean up related data
            pattern = f"pipeline:*:{pipeline_id}:*"
            keys = await redis_client.keys(pattern)
            
            if keys:
                await redis_client.delete(*keys)
                
        except Exception as e:
            logger.error(f"Failed to cleanup pipeline data for {pipeline_id}: {e}")
    
    def _pipeline_stats_to_dict(self, stats: PipelineStats) -> Dict[str, Any]:
        """Convert PipelineStats to dictionary."""
        return {
            "pipeline_id": stats.pipeline_id,
            "components_active": stats.components_active,
            "metrics_processed": stats.metrics_processed,
            "logs_processed": stats.logs_processed,
            "traces_processed": stats.traces_processed,
            "alerts_triggered": stats.alerts_triggered,
            "processing_errors": stats.processing_errors,
            "start_time": stats.start_time.isoformat() if stats.start_time else None,
            "last_activity": stats.last_activity.isoformat() if stats.last_activity else None
        }
    
    def _dict_to_pipeline_stats(self, stats_dict: Dict[str, Any]) -> PipelineStats:
        """Convert dictionary to PipelineStats."""
        return PipelineStats(
            pipeline_id=stats_dict["pipeline_id"],
            components_active=stats_dict["components_active"],
            metrics_processed=stats_dict.get("metrics_processed", 0),
            logs_processed=stats_dict.get("logs_processed", 0),
            traces_processed=stats_dict.get("traces_processed", 0),
            alerts_triggered=stats_dict.get("alerts_triggered", 0),
            processing_errors=stats_dict.get("processing_errors", 0),
            start_time=datetime.fromisoformat(stats_dict["start_time"].replace("Z", "+00:00")) if stats_dict.get("start_time") else None,
            last_activity=datetime.fromisoformat(stats_dict["last_activity"].replace("Z", "+00:00")) if stats_dict.get("last_activity") else None
        )


# Supporting classes for trace and log collection

class TraceCollector:
    """Trace collector for distributed tracing."""
    
    def __init__(self):
        self._active_traces: Dict[str, TraceData] = {}
    
    async def start_trace(self, operation_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Start a new trace.
        
        Args:
            operation_name: Name of the operation being traced
            tags: Optional tags for the trace
            
        Returns:
            Trace ID
        """
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        trace_data = TraceData(
            trace_id=trace_id,
            span_id=span_id,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc),
            duration_ms=0.0,
            tags=tags or {}
        )
        
        self._active_traces[trace_id] = trace_data
        return trace_id
    
    async def end_trace(self, trace_id: str, status: str = "ok") -> bool:
        """End a trace and calculate duration.
        
        Args:
            trace_id: Trace ID to end
            status: Final status of the trace
            
        Returns:
            True if ended successfully
        """
        try:
            if trace_id in self._active_traces:
                trace_data = self._active_traces[trace_id]
                end_time = datetime.now(timezone.utc)
                trace_data.duration_ms = (end_time - trace_data.start_time).total_seconds() * 1000
                trace_data.status = status
                
                # Store trace data
                await self._store_trace_data(trace_data)
                
                # Remove from active traces
                del self._active_traces[trace_id]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to end trace {trace_id}: {e}")
            return False
    
    async def _store_trace_data(self, trace_data: TraceData) -> None:
        """Store trace data in Redis."""
        try:
            redis_client = await redis_manager.get_client()
            
            trace_dict = {
                "trace_id": trace_data.trace_id,
                "span_id": trace_data.span_id,
                "operation_name": trace_data.operation_name,
                "start_time": trace_data.start_time.isoformat(),
                "duration_ms": trace_data.duration_ms,
                "tags": trace_data.tags,
                "status": trace_data.status
            }
            
            key = f"trace:{trace_data.trace_id}:{trace_data.span_id}"
            await redis_client.set(key, json.dumps(trace_dict), ex=3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store trace data: {e}")


class LogAggregator:
    """Log aggregator for centralized logging."""
    
    async def emit_log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> bool:
        """Emit a log message.
        
        Args:
            level: Log level (INFO, WARNING, ERROR, etc.)
            message: Log message
            context: Optional context information
            source: Optional source identifier
            
        Returns:
            True if emitted successfully
        """
        try:
            log_data = LogData(
                level=level,
                message=message,
                timestamp=datetime.now(timezone.utc),
                context=context or {},
                source=source
            )
            
            # Store log data
            await self._store_log_data(log_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")
            return False
    
    async def _store_log_data(self, log_data: LogData) -> None:
        """Store log data in Redis."""
        try:
            redis_client = await redis_manager.get_client()
            
            log_dict = {
                "level": log_data.level,
                "message": log_data.message,
                "timestamp": log_data.timestamp.isoformat(),
                "context": log_data.context,
                "source": log_data.source
            }
            
            # Store with time-based key for ordering
            timestamp_key = int(log_data.timestamp.timestamp())
            key = f"log:{log_data.level}:{timestamp_key}"
            
            await redis_client.set(key, json.dumps(log_dict), ex=3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store log data: {e}")


__all__ = [
    'ObservabilityPipeline',
    'TraceCollector',
    'LogAggregator',
    'PipelineComponent',
    'MetricType',
    'PipelineStats',
    'MetricData',
    'LogData',
    'TraceData'
]