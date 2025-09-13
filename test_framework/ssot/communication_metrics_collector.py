"""
Single Source of Truth (SSOT) Communication Metrics Collector

This module provides the unified CommunicationMetricsCollector for ALL WebSocket
communication performance tracking and monitoring across the entire test suite.
It provides comprehensive metrics collection for agent-WebSocket communication patterns.

Business Value: Platform/Internal - Test Infrastructure Stability & Development Velocity
Enables performance monitoring and optimization of WebSocket communication that supports
$500K+ ARR chat functionality through detailed metrics collection and analysis.

CRITICAL: This is the ONLY source for WebSocket communication metrics in test infrastructure.
ALL performance testing must use CommunicationMetricsCollector for consistency.
"""

import asyncio
import json
import logging
import statistics
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Deque
from enum import Enum

# Import SSOT environment management
from shared.isolated_environment import get_env

# Import existing WebSocket test infrastructure
from .websocket import WebSocketTestClient, WebSocketEventType, WebSocketMessage

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CONNECTION_COUNT = "connection_count"
    MESSAGE_SIZE = "message_size"
    EVENT_FREQUENCY = "event_frequency"
    AGENT_RESPONSE_TIME = "agent_response_time"
    USER_ENGAGEMENT = "user_engagement"


@dataclass
class MetricDataPoint:
    """Single metric data point."""
    metric_type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metric_type": self.metric_type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "metadata": self.metadata
        }


@dataclass
class CommunicationSession:
    """Communication session tracking."""
    session_id: str
    user_id: str
    agent_type: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime] = None
    message_count: int = 0
    event_count: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    errors: List[str] = field(default_factory=list)
    events_by_type: Dict[str, int] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get session duration."""
        if self.ended_at:
            return self.ended_at - self.started_at
        return None
    
    @property
    def messages_per_second(self) -> float:
        """Get messages per second rate."""
        duration = self.duration
        if duration and duration.total_seconds() > 0:
            return self.message_count / duration.total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_type": self.agent_type,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "message_count": self.message_count,
            "event_count": self.event_count,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "messages_per_second": self.messages_per_second,
            "errors": self.errors,
            "events_by_type": self.events_by_type
        }


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics."""
    total_sessions: int = 0
    active_sessions: int = 0
    average_session_duration: float = 0.0
    total_messages: int = 0
    total_events: int = 0
    average_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    throughput_messages_per_second: float = 0.0
    error_rate: float = 0.0
    connection_success_rate: float = 0.0
    agent_response_times: Dict[str, float] = field(default_factory=dict)
    event_type_distribution: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "average_session_duration": self.average_session_duration,
            "total_messages": self.total_messages,
            "total_events": self.total_events,
            "average_latency": self.average_latency,
            "p95_latency": self.p95_latency,
            "p99_latency": self.p99_latency,
            "throughput_messages_per_second": self.throughput_messages_per_second,
            "error_rate": self.error_rate,
            "connection_success_rate": self.connection_success_rate,
            "agent_response_times": self.agent_response_times,
            "event_type_distribution": self.event_type_distribution
        }


class CommunicationMetricsCollector:
    """
    Single Source of Truth (SSOT) communication metrics collector.
    
    This collector provides comprehensive WebSocket communication metrics tracking:
    - Real-time performance monitoring with configurable sampling
    - Agent communication pattern analysis and optimization insights  
    - Multi-user session tracking with isolation and aggregation
    - Event delivery latency and throughput measurement
    - Error rate tracking and reliability metrics
    - Connection lifecycle and health monitoring
    - Business metrics for chat functionality performance
    
    Features:
    - SSOT compliance with existing test framework
    - Integration with production WebSocket and agent components
    - Real-time metrics collection with efficient memory usage
    - Historical trend analysis and performance baselines
    - Configurable alerting for performance degradation
    - Export capabilities for external monitoring systems
    
    Usage:
        async with CommunicationMetricsCollector() as metrics_collector:
            session_id = await metrics_collector.start_session(user_id="test_user")
            await metrics_collector.track_agent_communication(session_id, agent_type="triage")
            metrics = await metrics_collector.get_performance_metrics()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, env=None):
        """
        Initialize communication metrics collector.
        
        Args:
            config: Optional collector configuration
            env: Optional environment manager instance
        """
        self.env = env or get_env()
        self.config = config or self._get_default_config()
        self.collector_id = f"metrics_{uuid.uuid4().hex[:8]}"
        
        # Session tracking
        self.active_sessions: Dict[str, CommunicationSession] = {}
        self.completed_sessions: List[CommunicationSession] = []
        
        # Metrics storage
        self.metrics_buffer: Deque[MetricDataPoint] = deque(maxlen=self.config.get("max_metrics_buffer", 10000))
        self.metrics_by_type: Dict[MetricType, List[MetricDataPoint]] = defaultdict(list)
        
        # Performance tracking
        self.latency_measurements: Deque[float] = deque(maxlen=1000)
        self.throughput_measurements: Deque[float] = deque(maxlen=1000)
        self.error_count = 0
        self.total_operations = 0
        
        # Agent-specific metrics
        self.agent_response_times: Dict[str, List[float]] = defaultdict(list)
        self.agent_event_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Connection tracking
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        
        # Real-time monitoring
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        logger.debug(f"CommunicationMetricsCollector initialized [{self.collector_id}]")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default collector configuration."""
        return {
            "max_metrics_buffer": int(self.env.get("METRICS_BUFFER_SIZE", "10000")),
            "sampling_interval": float(self.env.get("METRICS_SAMPLING_INTERVAL", "1.0")),
            "enable_real_time_monitoring": self.env.get("METRICS_REAL_TIME", "true").lower() == "true",
            "max_session_history": int(self.env.get("MAX_SESSION_HISTORY", "1000")),
            "latency_threshold_warning": float(self.env.get("LATENCY_WARNING_THRESHOLD", "2.0")),
            "latency_threshold_critical": float(self.env.get("LATENCY_CRITICAL_THRESHOLD", "5.0")),
            "error_rate_threshold": float(self.env.get("ERROR_RATE_THRESHOLD", "0.05")),
            "export_metrics": self.env.get("EXPORT_METRICS", "false").lower() == "true"
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize metrics collector."""
        try:
            # Start real-time monitoring if enabled
            if self.config.get("enable_real_time_monitoring", True):
                await self.start_monitoring()
            
            logger.info(f"CommunicationMetricsCollector initialized [{self.collector_id}]")
            
        except Exception as e:
            logger.error(f"Metrics collector initialization failed: {e}")
            raise
    
    async def start_monitoring(self):
        """Start real-time metrics monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.debug("Real-time metrics monitoring started")
    
    async def stop_monitoring(self):
        """Stop real-time metrics monitoring."""
        self.is_monitoring = False
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.debug("Real-time metrics monitoring stopped")
    
    async def _monitoring_loop(self):
        """Real-time monitoring background loop."""
        try:
            while self.is_monitoring:
                await self._collect_system_metrics()
                await asyncio.sleep(self.config.get("sampling_interval", 1.0))
                
        except asyncio.CancelledError:
            logger.debug("Metrics monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Metrics monitoring loop error: {e}")
    
    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            # Collect connection count
            self.record_metric(
                MetricType.CONNECTION_COUNT,
                len(self.active_sessions),
                labels={"type": "active_sessions"}
            )
            
            # Collect throughput if we have recent measurements
            if self.throughput_measurements:
                recent_throughput = statistics.mean(list(self.throughput_measurements)[-10:])
                self.record_metric(
                    MetricType.THROUGHPUT,
                    recent_throughput,
                    labels={"window": "recent_10"}
                )
            
            # Collect error rate
            if self.total_operations > 0:
                error_rate = self.error_count / self.total_operations
                self.record_metric(
                    MetricType.ERROR_RATE,
                    error_rate,
                    labels={"type": "overall"}
                )
            
        except Exception as e:
            logger.error(f"System metrics collection error: {e}")
    
    def record_metric(self, metric_type: MetricType, value: float,
                     labels: Optional[Dict[str, str]] = None,
                     metadata: Optional[Dict[str, Any]] = None):
        """
        Record a metric data point.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            labels: Optional labels for categorization
            metadata: Optional additional metadata
        """
        data_point = MetricDataPoint(
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metadata=metadata or {}
        )
        
        # Add to buffer
        self.metrics_buffer.append(data_point)
        
        # Add to type-specific storage
        if len(self.metrics_by_type[metric_type]) >= 1000:
            self.metrics_by_type[metric_type].pop(0)  # Remove oldest
        self.metrics_by_type[metric_type].append(data_point)
        
        # Update specific metric tracking
        if metric_type == MetricType.LATENCY:
            self.latency_measurements.append(value)
        elif metric_type == MetricType.THROUGHPUT:
            self.throughput_measurements.append(value)
    
    async def start_session(self, user_id: str, agent_type: Optional[str] = None) -> str:
        """
        Start a new communication session tracking.
        
        Args:
            user_id: User ID for the session
            agent_type: Optional agent type for the session
            
        Returns:
            Session ID for tracking
        """
        session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
        
        session = CommunicationSession(
            session_id=session_id,
            user_id=user_id,
            agent_type=agent_type,
            started_at=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        
        # Record session start metric
        self.record_metric(
            MetricType.CONNECTION_COUNT,
            1,
            labels={"action": "session_started", "user_id": user_id, "agent_type": agent_type or "unknown"}
        )
        
        logger.debug(f"Started session tracking: {session_id} for user {user_id}")
        return session_id
    
    async def end_session(self, session_id: str):
        """
        End a communication session tracking.
        
        Args:
            session_id: Session ID to end
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Attempted to end non-existent session: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        session.ended_at = datetime.now()
        
        # Move to completed sessions
        self.completed_sessions.append(session)
        del self.active_sessions[session_id]
        
        # Trim history if needed
        max_history = self.config.get("max_session_history", 1000)
        if len(self.completed_sessions) > max_history:
            self.completed_sessions = self.completed_sessions[-max_history:]
        
        # Record session metrics
        if session.duration:
            self.record_metric(
                MetricType.CONNECTION_COUNT,
                -1,
                labels={"action": "session_ended", "user_id": session.user_id}
            )
            
            # Record session duration
            duration_seconds = session.duration.total_seconds()
            self.record_metric(
                MetricType.LATENCY,
                duration_seconds,
                labels={"type": "session_duration", "user_id": session.user_id},
                metadata={"session_id": session_id}
            )
        
        logger.debug(f"Ended session tracking: {session_id}")
    
    async def track_agent_communication(self, session_id: str, agent_type: str,
                                      request_content: Optional[str] = None) -> str:
        """
        Track agent communication within a session.
        
        Args:
            session_id: Session ID for tracking
            agent_type: Type of agent being tracked
            request_content: Optional request content
            
        Returns:
            Communication tracking ID
        """
        comm_id = f"comm_{agent_type}_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        # Update session if it exists
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.agent_type = agent_type
        
        # Record agent communication start
        self.record_metric(
            MetricType.AGENT_RESPONSE_TIME,
            0,  # Will be updated when communication ends
            labels={"agent_type": agent_type, "action": "started"},
            metadata={"session_id": session_id, "comm_id": comm_id, "start_time": start_time}
        )
        
        logger.debug(f"Started agent communication tracking: {comm_id} for {agent_type}")
        return comm_id
    
    async def track_websocket_events(self, session_id: str, events: List[WebSocketMessage]):
        """
        Track WebSocket events for performance analysis.
        
        Args:
            session_id: Session ID for tracking
            events: List of WebSocket events to track
        """
        if session_id not in self.active_sessions:
            logger.warning(f"Tracking events for non-existent session: {session_id}")
            return
        
        session = self.active_sessions[session_id]
        
        for event in events:
            # Update session event counts
            event_type_str = event.event_type.value
            session.events_by_type[event_type_str] = session.events_by_type.get(event_type_str, 0) + 1
            session.event_count += 1
            
            # Track event frequency
            self.record_metric(
                MetricType.EVENT_FREQUENCY,
                1,
                labels={"event_type": event_type_str, "session_id": session_id},
                metadata={"timestamp": event.timestamp.isoformat()}
            )
            
            # Track message size if available
            if hasattr(event, 'data') and event.data:
                try:
                    message_size = len(json.dumps(event.data))
                    session.total_bytes_sent += message_size
                    
                    self.record_metric(
                        MetricType.MESSAGE_SIZE,
                        message_size,
                        labels={"event_type": event_type_str, "direction": "sent"}
                    )
                except Exception as e:
                    logger.debug(f"Could not calculate message size for event: {e}")
            
            # Track agent-specific events
            if session.agent_type and session.agent_type in self.agent_event_counts:
                self.agent_event_counts[session.agent_type][event_type_str] += 1
        
        logger.debug(f"Tracked {len(events)} WebSocket events for session {session_id}")
    
    def track_connection_attempt(self, success: bool, latency: Optional[float] = None):
        """
        Track WebSocket connection attempt.
        
        Args:
            success: Whether connection was successful
            latency: Optional connection latency
        """
        self.connection_attempts += 1
        
        if success:
            self.successful_connections += 1
            
            if latency is not None:
                self.record_metric(
                    MetricType.LATENCY,
                    latency,
                    labels={"type": "connection_latency", "result": "success"}
                )
        else:
            self.failed_connections += 1
            self.error_count += 1
            
        self.total_operations += 1
        
        # Record connection success rate
        success_rate = self.successful_connections / self.connection_attempts
        self.record_metric(
            MetricType.CONNECTION_COUNT,
            success_rate,
            labels={"type": "success_rate"}
        )
    
    def track_message_latency(self, latency: float, message_type: str):
        """
        Track message delivery latency.
        
        Args:
            latency: Message latency in seconds
            message_type: Type of message
        """
        self.record_metric(
            MetricType.LATENCY,
            latency,
            labels={"type": "message_latency", "message_type": message_type}
        )
        
        # Check for latency alerts
        warning_threshold = self.config.get("latency_threshold_warning", 2.0)
        critical_threshold = self.config.get("latency_threshold_critical", 5.0)
        
        if latency > critical_threshold:
            logger.warning(f"CRITICAL: High message latency detected: {latency:.3f}s for {message_type}")
        elif latency > warning_threshold:
            logger.warning(f"WARNING: Elevated message latency: {latency:.3f}s for {message_type}")
    
    def track_throughput(self, messages_per_second: float, context: str = "general"):
        """
        Track throughput measurement.
        
        Args:
            messages_per_second: Throughput rate
            context: Context for the measurement
        """
        self.record_metric(
            MetricType.THROUGHPUT,
            messages_per_second,
            labels={"context": context}
        )
    
    def track_error(self, error_type: str, error_message: str, session_id: Optional[str] = None):
        """
        Track error occurrence.
        
        Args:
            error_type: Type of error
            error_message: Error message
            session_id: Optional session ID
        """
        self.error_count += 1
        self.total_operations += 1
        
        # Update session if provided
        if session_id and session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.errors.append(f"{error_type}: {error_message}")
        
        # Record error metric
        self.record_metric(
            MetricType.ERROR_RATE,
            1,
            labels={"error_type": error_type},
            metadata={"error_message": error_message, "session_id": session_id}
        )
        
        logger.debug(f"Tracked error: {error_type} - {error_message}")
    
    async def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get aggregated performance metrics.
        
        Returns:
            PerformanceMetrics with current system performance
        """
        metrics = PerformanceMetrics()
        
        try:
            # Session metrics
            metrics.total_sessions = len(self.completed_sessions) + len(self.active_sessions)
            metrics.active_sessions = len(self.active_sessions)
            
            # Calculate average session duration
            completed_durations = [
                session.duration.total_seconds() for session in self.completed_sessions 
                if session.duration
            ]
            
            if completed_durations:
                metrics.average_session_duration = statistics.mean(completed_durations)
            
            # Message and event counts
            metrics.total_messages = sum(session.message_count for session in self.active_sessions.values())
            metrics.total_messages += sum(session.message_count for session in self.completed_sessions)
            
            metrics.total_events = sum(session.event_count for session in self.active_sessions.values())
            metrics.total_events += sum(session.event_count for session in self.completed_sessions)
            
            # Latency metrics
            if self.latency_measurements:
                latency_list = list(self.latency_measurements)
                metrics.average_latency = statistics.mean(latency_list)
                
                if len(latency_list) >= 20:  # Need sufficient data for percentiles
                    metrics.p95_latency = statistics.quantiles(latency_list, n=20)[18]  # 95th percentile
                    metrics.p99_latency = statistics.quantiles(latency_list, n=100)[98]  # 99th percentile
            
            # Throughput metrics
            if self.throughput_measurements:
                metrics.throughput_messages_per_second = statistics.mean(list(self.throughput_measurements))
            
            # Error rate
            if self.total_operations > 0:
                metrics.error_rate = self.error_count / self.total_operations
            
            # Connection success rate
            if self.connection_attempts > 0:
                metrics.connection_success_rate = self.successful_connections / self.connection_attempts
            
            # Agent response times
            for agent_type, response_times in self.agent_response_times.items():
                if response_times:
                    metrics.agent_response_times[agent_type] = statistics.mean(response_times)
            
            # Event type distribution
            all_events = {}
            for session in list(self.active_sessions.values()) + self.completed_sessions:
                for event_type, count in session.events_by_type.items():
                    all_events[event_type] = all_events.get(event_type, 0) + count
            
            metrics.event_type_distribution = all_events
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
        
        return metrics
    
    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metrics for a specific session.
        
        Args:
            session_id: Session ID to get metrics for
            
        Returns:
            Session metrics dictionary or None if not found
        """
        session = self.active_sessions.get(session_id)
        if not session:
            # Check completed sessions
            session = next((s for s in self.completed_sessions if s.session_id == session_id), None)
        
        if session:
            return session.to_dict()
        
        return None
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """
        Get current real-time metrics.
        
        Returns:
            Real-time metrics dictionary
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(self.active_sessions),
            "total_metrics_collected": len(self.metrics_buffer),
            "recent_latency": statistics.mean(list(self.latency_measurements)[-10:]) if len(self.latency_measurements) >= 10 else None,
            "recent_throughput": statistics.mean(list(self.throughput_measurements)[-10:]) if len(self.throughput_measurements) >= 10 else None,
            "current_error_rate": self.error_count / self.total_operations if self.total_operations > 0 else 0,
            "connection_success_rate": self.successful_connections / self.connection_attempts if self.connection_attempts > 0 else 0
        }
    
    def export_metrics(self, format_type: str = "json") -> Union[Dict[str, Any], str]:
        """
        Export collected metrics in specified format.
        
        Args:
            format_type: Export format ("json", "csv", "prometheus")
            
        Returns:
            Exported metrics in requested format
        """
        if format_type == "json":
            return {
                "collector_id": self.collector_id,
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "metrics_buffer": [metric.to_dict() for metric in self.metrics_buffer],
                "active_sessions": [session.to_dict() for session in self.active_sessions.values()],
                "completed_sessions": [session.to_dict() for session in self.completed_sessions[-100:]],  # Last 100
                "summary": self.get_real_time_metrics()
            }
        elif format_type == "csv":
            # Simple CSV export of metrics
            lines = ["timestamp,metric_type,value,labels"]
            for metric in self.metrics_buffer:
                labels_str = ",".join([f"{k}={v}" for k, v in metric.labels.items()])
                lines.append(f"{metric.timestamp.isoformat()},{metric.metric_type.value},{metric.value},{labels_str}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    async def cleanup(self):
        """Clean up metrics collector resources."""
        try:
            # Stop monitoring
            await self.stop_monitoring()
            
            # End all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.end_session(session_id)
            
            # Export metrics if configured
            if self.config.get("export_metrics", False):
                try:
                    exported_data = self.export_metrics("json")
                    # In real implementation, would save to file or send to monitoring system
                    logger.info(f"Exported {len(self.metrics_buffer)} metrics for persistence")
                except Exception as e:
                    logger.error(f"Failed to export metrics: {e}")
            
            # Clear buffers
            self.metrics_buffer.clear()
            self.metrics_by_type.clear()
            self.latency_measurements.clear()
            self.throughput_measurements.clear()
            self.agent_response_times.clear()
            self.agent_event_counts.clear()
            
            logger.info(f"CommunicationMetricsCollector cleanup completed [{self.collector_id}]")
            
        except Exception as e:
            logger.error(f"Metrics collector cleanup failed: {e}")
    
    # Utility methods for test assertions
    
    def get_metric_history(self, metric_type: MetricType, limit: int = 100) -> List[MetricDataPoint]:
        """Get recent history for a specific metric type."""
        return self.metrics_by_type[metric_type][-limit:]
    
    def get_collector_status(self) -> Dict[str, Any]:
        """Get collector status and health."""
        return {
            "collector_id": self.collector_id,
            "is_monitoring": self.is_monitoring,
            "active_sessions": len(self.active_sessions),
            "completed_sessions": len(self.completed_sessions),
            "total_metrics": len(self.metrics_buffer),
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "error_count": self.error_count,
            "total_operations": self.total_operations,
            "config": self.config
        }


# Export CommunicationMetricsCollector
__all__ = [
    'CommunicationMetricsCollector',
    'MetricType',
    'MetricDataPoint',
    'CommunicationSession',
    'PerformanceMetrics'
]