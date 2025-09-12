"""
Enhanced Logging System for WebSocket Notification Monitoring

This module provides enhanced logging capabilities with correlation IDs, 
structured logging, and comprehensive tracing for WebSocket notifications.

LOGGING OBJECTIVES:
1. Provide complete traceability of notification events
2. Enable correlation across distributed components
3. Support forensic analysis of silent failures
4. Facilitate debugging and troubleshooting
5. Ensure compliance and audit requirements

LOGGING FEATURES:
- Correlation ID tracking across all components
- Structured JSON logging for machine processing
- Performance metrics logging
- Error categorization and analysis
- User-specific event tracing
- Security and privacy protection
"""

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LogLevel(Enum):
    """Enhanced log levels for WebSocket monitoring."""
    TRACE = "TRACE"      # Detailed tracing information
    DEBUG = "DEBUG"      # Debug information  
    INFO = "INFO"        # General information
    WARN = "WARN"        # Warning conditions
    ERROR = "ERROR"      # Error conditions
    FATAL = "FATAL"      # Fatal errors requiring immediate attention


class EventCategory(Enum):
    """Categories of WebSocket events for classification."""
    BRIDGE_LIFECYCLE = "bridge_lifecycle"
    NOTIFICATION_DELIVERY = "notification_delivery"
    CONNECTION_MANAGEMENT = "connection_management"
    USER_ISOLATION = "user_isolation"
    PERFORMANCE_MONITORING = "performance_monitoring"
    ERROR_HANDLING = "error_handling"
    SECURITY_AUDIT = "security_audit"


@dataclass
class LogContext:
    """Enhanced logging context with correlation tracking."""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # User context
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    connection_id: Optional[str] = None
    
    # Execution context
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    operation: Optional[str] = None
    
    # Performance context
    start_time: Optional[float] = None
    duration_ms: Optional[float] = None
    
    # Event classification
    category: Optional[EventCategory] = None
    event_type: Optional[str] = None
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def start_timing(self) -> None:
        """Start timing operation."""
        self.start_time = time.time()
    
    def end_timing(self) -> None:
        """End timing operation and calculate duration."""
        if self.start_time:
            self.duration_ms = (time.time() - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging."""
        result = {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add non-None fields
        if self.user_id:
            result["user_id"] = self.user_id
        if self.thread_id:
            result["thread_id"] = self.thread_id
        if self.run_id:
            result["run_id"] = self.run_id
        if self.connection_id:
            result["connection_id"] = self.connection_id
        if self.agent_name:
            result["agent_name"] = self.agent_name
        if self.tool_name:
            result["tool_name"] = self.tool_name
        if self.operation:
            result["operation"] = self.operation
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.category:
            result["category"] = self.category.value
        if self.event_type:
            result["event_type"] = self.event_type
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result


class WebSocketEnhancedLogger:
    """Enhanced logger for WebSocket notification monitoring."""
    
    def __init__(self, logger_name: str = "websocket_monitor"):
        """Initialize enhanced logger."""
        self.logger_name = logger_name
        self.base_logger = central_logger.get_logger(logger_name)
        
        # Context stack for nested operations
        self.context_stack: List[LogContext] = []
        
        # Performance tracking
        self.performance_logs: List[Dict[str, Any]] = []
        self.max_performance_logs = 1000
        
        logger.info(f" SEARCH:  Enhanced WebSocket logger initialized: {logger_name}")
    
    @contextmanager
    def log_context(self, context: LogContext):
        """Context manager for enhanced logging with automatic cleanup."""
        self.context_stack.append(context)
        context.start_timing()
        
        try:
            yield context
        finally:
            context.end_timing()
            
            # Log operation completion
            self.log_structured(
                LogLevel.TRACE,
                f"Operation completed: {context.operation or 'unknown'}",
                context=context,
                metadata={
                    "operation_completed": True,
                    "duration_ms": context.duration_ms
                }
            )
            
            # Remove from stack
            if self.context_stack and self.context_stack[-1] == context:
                self.context_stack.pop()
    
    def log_structured(self,
                      level: LogLevel,
                      message: str,
                      context: Optional[LogContext] = None,
                      category: Optional[EventCategory] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log structured message with full context."""
        
        # Use provided context or get from stack
        log_context = context or (self.context_stack[-1] if self.context_stack else LogContext())
        
        if category:
            log_context.category = category
        
        if metadata:
            log_context.metadata.update(metadata)
        
        # Create structured log entry
        log_entry = {
            "message": message,
            "level": level.value,
            **log_context.to_dict()
        }
        
        # Add performance metrics if available
        if log_context.duration_ms is not None:
            log_entry["performance"] = {
                "duration_ms": log_context.duration_ms,
                "slow_operation": log_context.duration_ms > 1000
            }
            
            # Store performance data
            self._store_performance_log(log_entry)
        
        # Log with appropriate level
        structured_message = f"[{log_context.correlation_id}] {message}"
        
        if level == LogLevel.TRACE:
            self.base_logger.debug(f"TRACE: {structured_message}")
        elif level == LogLevel.DEBUG:
            self.base_logger.debug(structured_message)
        elif level == LogLevel.INFO:
            self.base_logger.info(structured_message)
        elif level == LogLevel.WARN:
            self.base_logger.warning(structured_message)
        elif level == LogLevel.ERROR:
            self.base_logger.error(structured_message)
        elif level == LogLevel.FATAL:
            self.base_logger.critical(structured_message)
        
        # Also log structured data for analysis
        self.base_logger.debug(f"STRUCTURED_LOG: {json.dumps(log_entry)}")
    
    def _store_performance_log(self, log_entry: Dict[str, Any]) -> None:
        """Store performance log for analysis."""
        perf_entry = {
            "timestamp": log_entry["timestamp"],
            "operation": log_entry.get("operation", "unknown"),
            "duration_ms": log_entry["performance"]["duration_ms"],
            "user_id": log_entry.get("user_id"),
            "category": log_entry.get("category"),
            "correlation_id": log_entry["correlation_id"]
        }
        
        self.performance_logs.append(perf_entry)
        
        # Trim to max size
        if len(self.performance_logs) > self.max_performance_logs:
            self.performance_logs = self.performance_logs[-self.max_performance_logs//2:]
    
    # Convenience methods for common WebSocket events
    
    def log_bridge_initialization_started(self, user_id: str, thread_id: str, connection_id: str) -> LogContext:
        """Log bridge initialization start."""
        context = LogContext(
            user_id=user_id,
            thread_id=thread_id,
            connection_id=connection_id,
            operation="bridge_initialization",
            category=EventCategory.BRIDGE_LIFECYCLE,
            event_type="initialization_started"
        )
        
        self.log_structured(
            LogLevel.INFO,
            f"WebSocket bridge initialization started for user {user_id}",
            context=context,
            metadata={"initialization_phase": "started"}
        )
        
        return context
    
    def log_bridge_initialization_success(self, context: LogContext, duration_ms: float) -> None:
        """Log successful bridge initialization."""
        context.duration_ms = duration_ms
        context.event_type = "initialization_success"
        
        self.log_structured(
            LogLevel.INFO,
            f"WebSocket bridge initialization successful ({duration_ms:.1f}ms)",
            context=context,
            metadata={
                "initialization_phase": "completed",
                "success": True,
                "performance_ms": duration_ms
            }
        )
    
    def log_bridge_initialization_failed(self, context: LogContext, error: str, duration_ms: float) -> None:
        """Log failed bridge initialization."""
        context.duration_ms = duration_ms
        context.event_type = "initialization_failed"
        
        self.log_structured(
            LogLevel.FATAL,
            f"WebSocket bridge initialization FAILED: {error} ({duration_ms:.1f}ms)",
            context=context,
            metadata={
                "initialization_phase": "failed",
                "success": False,
                "error": error,
                "performance_ms": duration_ms,
                "requires_immediate_attention": True
            }
        )
    
    def log_notification_attempted(self, user_id: str, thread_id: str, run_id: str,
                                 agent_name: str, tool_name: Optional[str] = None) -> LogContext:
        """Log notification attempt."""
        context = LogContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            operation="notification_delivery",
            category=EventCategory.NOTIFICATION_DELIVERY,
            event_type="notification_attempted"
        )
        
        self.log_structured(
            LogLevel.TRACE,
            f"Notification attempt: {tool_name or agent_name} -> user {user_id}",
            context=context,
            metadata={"delivery_phase": "attempted"}
        )
        
        return context
    
    def log_notification_delivered(self, context: LogContext, delivery_time_ms: float) -> None:
        """Log successful notification delivery."""
        context.duration_ms = delivery_time_ms  
        context.event_type = "notification_delivered"
        
        self.log_structured(
            LogLevel.INFO,
            f"Notification delivered successfully ({delivery_time_ms:.1f}ms)",
            context=context,
            metadata={
                "delivery_phase": "completed",
                "success": True,
                "performance_ms": delivery_time_ms
            }
        )
    
    def log_notification_failed(self, context: LogContext, error: str, error_type: str) -> None:
        """Log failed notification delivery."""
        context.event_type = "notification_failed"
        
        self.log_structured(
            LogLevel.ERROR,
            f"Notification delivery FAILED: {error}",
            context=context,
            metadata={
                "delivery_phase": "failed",
                "success": False,
                "error": error,
                "error_type": error_type,
                "requires_investigation": True
            }
        )
    
    def log_silent_failure_detected(self, user_id: str, thread_id: str, failure_context: str) -> None:
        """Log silent failure detection."""
        context = LogContext(
            user_id=user_id,
            thread_id=thread_id,
            operation="silent_failure_detection",
            category=EventCategory.ERROR_HANDLING,
            event_type="silent_failure_detected"
        )
        
        self.log_structured(
            LogLevel.FATAL,
            f"SILENT FAILURE DETECTED: {failure_context}",
            context=context,
            metadata={
                "failure_type": "silent",
                "user_impact": "high",
                "requires_immediate_attention": True,
                "business_impact": "user_experience_degradation",
                "failure_context": failure_context
            }
        )
    
    def log_isolation_violation(self, source_user: str, target_user: str, 
                              violation_type: str, violation_context: str) -> None:
        """Log user isolation violation."""
        context = LogContext(
            user_id=source_user,
            operation="isolation_violation_detection",
            category=EventCategory.SECURITY_AUDIT,
            event_type="isolation_violation",
            metadata={
                "target_user": target_user,
                "violation_type": violation_type,
                "violation_context": violation_context
            }
        )
        
        self.log_structured(
            LogLevel.FATAL,
            f"USER ISOLATION VIOLATION: {source_user} -> {target_user} ({violation_type})",
            context=context,
            metadata={
                "security_incident": True,
                "requires_immediate_attention": True,
                "privacy_impact": "potential_data_exposure",
                "business_risk": "high"
            }
        )
    
    def log_connection_event(self, user_id: str, connection_id: str, 
                           event_type: str, details: str) -> None:
        """Log connection lifecycle events."""
        context = LogContext(
            user_id=user_id,
            connection_id=connection_id,
            operation="connection_management",
            category=EventCategory.CONNECTION_MANAGEMENT,
            event_type=event_type
        )
        
        log_level = LogLevel.INFO
        if event_type in ["connection_lost", "connection_failed"]:
            log_level = LogLevel.WARN
        elif event_type in ["connection_restored", "connection_established"]:
            log_level = LogLevel.INFO
        
        self.log_structured(
            log_level,
            f"Connection event: {event_type} - {details}",
            context=context,
            metadata={"connection_details": details}
        )
    
    def log_performance_metric(self, operation: str, duration_ms: float, 
                             user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log performance metrics."""
        context = LogContext(
            user_id=user_id,
            operation=operation,
            category=EventCategory.PERFORMANCE_MONITORING,
            event_type="performance_metric",
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Determine performance level
        log_level = LogLevel.INFO
        if duration_ms > 5000:
            log_level = LogLevel.ERROR
        elif duration_ms > 2000:
            log_level = LogLevel.WARN
        
        self.log_structured(
            log_level,
            f"Performance: {operation} took {duration_ms:.1f}ms",
            context=context,
            metadata={
                "performance_category": self._categorize_performance(duration_ms),
                "performance_acceptable": duration_ms <= 1000
            }
        )
    
    def _categorize_performance(self, duration_ms: float) -> str:
        """Categorize performance based on duration."""
        if duration_ms <= 100:
            return "excellent"
        elif duration_ms <= 500:
            return "good"
        elif duration_ms <= 1000:
            return "acceptable"
        elif duration_ms <= 2000:
            return "slow" 
        elif duration_ms <= 5000:
            return "very_slow"
        else:
            return "unacceptable"
    
    def log_error_with_context(self, error: Exception, context: LogContext, 
                             operation: str, impact: str = "unknown") -> None:
        """Log error with full context."""
        context.operation = operation
        context.category = EventCategory.ERROR_HANDLING
        context.event_type = "error_occurred"
        
        error_metadata = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "operation": operation,
            "impact": impact,
            "stack_trace": self._get_sanitized_stack_trace(error)
        }
        
        self.log_structured(
            LogLevel.ERROR,
            f"Operation failed: {operation} - {error}",
            context=context,
            metadata=error_metadata
        )
    
    def _get_sanitized_stack_trace(self, error: Exception) -> str:
        """Get sanitized stack trace without sensitive information."""
        import traceback
        
        try:
            stack_trace = traceback.format_exc()
            
            # Sanitize sensitive paths
            sanitized = stack_trace.replace("/Users/", "[USER]/")
            sanitized = sanitized.replace("\\Users\\", "[USER]\\")
            
            # Limit length
            if len(sanitized) > 2000:
                sanitized = sanitized[:2000] + "...[truncated]"
            
            return sanitized
        except Exception:
            return "Unable to capture stack trace"
    
    # Audit logging for compliance
    
    def log_security_event(self, event_type: str, user_id: str, details: str, 
                          risk_level: str = "medium") -> None:
        """Log security-related events for audit."""
        context = LogContext(
            user_id=user_id,
            operation="security_audit",
            category=EventCategory.SECURITY_AUDIT,
            event_type=event_type
        )
        
        self.log_structured(
            LogLevel.WARN if risk_level == "high" else LogLevel.INFO,
            f"Security event: {event_type} - {details}",
            context=context,
            metadata={
                "security_event": True,
                "risk_level": risk_level,
                "audit_required": risk_level == "high",
                "details": details
            }
        )
    
    def log_privacy_event(self, event_type: str, user_id: str, data_type: str, 
                         action: str) -> None:
        """Log privacy-related events for compliance."""
        context = LogContext(
            user_id=user_id,
            operation="privacy_audit",
            category=EventCategory.SECURITY_AUDIT,
            event_type=event_type
        )
        
        self.log_structured(
            LogLevel.INFO,
            f"Privacy event: {event_type} - {action} on {data_type}",
            context=context,
            metadata={
                "privacy_event": True,
                "data_type": data_type,
                "action": action,
                "compliance_required": True
            }
        )
    
    # Diagnostic logging
    
    def log_diagnostic_checkpoint(self, checkpoint_name: str, user_id: str, 
                                 state: Dict[str, Any]) -> None:
        """Log diagnostic checkpoint for troubleshooting."""
        context = LogContext(
            user_id=user_id,
            operation="diagnostic_checkpoint",
            category=EventCategory.PERFORMANCE_MONITORING,
            event_type="checkpoint"
        )
        
        self.log_structured(
            LogLevel.TRACE,
            f"Diagnostic checkpoint: {checkpoint_name}",
            context=context,
            metadata={
                "checkpoint_name": checkpoint_name,
                "system_state": state,
                "diagnostic": True
            }
        )
    
    def log_system_state_snapshot(self, snapshot_reason: str, state_data: Dict[str, Any]) -> None:
        """Log system state snapshot for analysis."""
        context = LogContext(
            operation="system_state_snapshot", 
            category=EventCategory.PERFORMANCE_MONITORING,
            event_type="state_snapshot"
        )
        
        self.log_structured(
            LogLevel.DEBUG,
            f"System state snapshot: {snapshot_reason}",
            context=context,
            metadata={
                "snapshot_reason": snapshot_reason,
                "state_data": state_data,
                "diagnostic": True
            }
        )
    
    # Analysis and reporting
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary from logs."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.isoformat()
        
        recent_logs = [
            log for log in self.performance_logs 
            if log["timestamp"] > cutoff_timestamp
        ]
        
        if not recent_logs:
            return {"period_hours": hours, "performance_logs": 0}
        
        # Calculate statistics
        durations = [log["duration_ms"] for log in recent_logs]
        operations = {}
        
        for log in recent_logs:
            op = log["operation"]
            if op not in operations:
                operations[op] = {"count": 0, "total_duration": 0, "durations": []}
            
            operations[op]["count"] += 1
            operations[op]["total_duration"] += log["duration_ms"]
            operations[op]["durations"].append(log["duration_ms"])
        
        # Calculate per-operation statistics
        operation_stats = {}
        for op, data in operations.items():
            durations = data["durations"]
            operation_stats[op] = {
                "count": data["count"],
                "avg_duration_ms": data["total_duration"] / data["count"],
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p95_duration_ms": self._calculate_percentile(durations, 95),
                "slow_operations": sum(1 for d in durations if d > 1000)
            }
        
        return {
            "period_hours": hours,
            "performance_logs": len(recent_logs),
            "overall_stats": {
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p50_duration_ms": self._calculate_percentile(durations, 50),
                "p95_duration_ms": self._calculate_percentile(durations, 95),
                "p99_duration_ms": self._calculate_percentile(durations, 99)
            },
            "operation_stats": operation_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def search_logs_by_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Search logs by correlation ID for tracing."""
        # This would typically search log storage system
        # For now, return placeholder indicating search capability
        return [{
            "message": f"Log search for correlation_id {correlation_id}",
            "implementation": "Connect to log storage system (ELK, Splunk, etc.)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    
    def get_user_event_trace(self, user_id: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get complete event trace for a user."""
        # This would typically query log storage for user events
        # For now, return placeholder indicating trace capability
        return [{
            "message": f"Event trace for user {user_id} (last {hours}h)",
            "implementation": "Query log storage for user-specific events", 
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]


class CorrelationTracker:
    """Tracks correlation IDs across WebSocket operations."""
    
    def __init__(self):
        """Initialize correlation tracker.""" 
        self.active_correlations: Dict[str, Dict[str, Any]] = {}
        self.correlation_timeout = 300  # 5 minutes
        
    def start_correlation(self, correlation_id: str, operation: str, 
                         user_id: str, metadata: Dict[str, Any]) -> None:
        """Start tracking a correlation."""
        self.active_correlations[correlation_id] = {
            "correlation_id": correlation_id,
            "operation": operation,
            "user_id": user_id,
            "started_at": datetime.now(timezone.utc),
            "metadata": metadata,
            "events": []
        }
    
    def add_correlation_event(self, correlation_id: str, event: str, details: Any) -> None:
        """Add event to correlation trace."""
        if correlation_id in self.active_correlations:
            self.active_correlations[correlation_id]["events"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "details": details
            })
    
    def end_correlation(self, correlation_id: str, result: str) -> Optional[Dict[str, Any]]:
        """End correlation tracking and return trace."""
        correlation = self.active_correlations.pop(correlation_id, None)
        if correlation:
            correlation["ended_at"] = datetime.now(timezone.utc)
            correlation["result"] = result
            correlation["duration_ms"] = (
                correlation["ended_at"] - correlation["started_at"]
            ).total_seconds() * 1000
        
        return correlation
    
    def cleanup_expired_correlations(self) -> int:
        """Clean up expired correlations."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.correlation_timeout)
        
        expired = [
            cid for cid, corr in self.active_correlations.items()
            if corr["started_at"] < cutoff
        ]
        
        for cid in expired:
            del self.active_correlations[cid]
        
        return len(expired)


# Global enhanced logger instances
_websocket_enhanced_logger: Optional[WebSocketEnhancedLogger] = None
_correlation_tracker: Optional[CorrelationTracker] = None


def get_websocket_enhanced_logger() -> WebSocketEnhancedLogger:
    """Get or create the global enhanced logger."""
    global _websocket_enhanced_logger
    if _websocket_enhanced_logger is None:
        _websocket_enhanced_logger = WebSocketEnhancedLogger("websocket_monitoring")
    return _websocket_enhanced_logger


def get_correlation_tracker() -> CorrelationTracker:
    """Get or create the global correlation tracker."""
    global _correlation_tracker
    if _correlation_tracker is None:
        _correlation_tracker = CorrelationTracker()
    return _correlation_tracker


# Convenience functions for common logging patterns

def log_websocket_operation(operation: str, user_id: str, thread_id: str = "unknown"):
    """Context manager for logging WebSocket operations.""" 
    enhanced_logger = get_websocket_enhanced_logger()
    
    context = LogContext(
        user_id=user_id,
        thread_id=thread_id,
        operation=operation,
        category=EventCategory.BRIDGE_LIFECYCLE
    )
    
    return enhanced_logger.log_context(context)


def log_notification_lifecycle(user_id: str, thread_id: str, run_id: str, 
                             agent_name: str, tool_name: Optional[str] = None):
    """Context manager for logging notification lifecycle."""
    enhanced_logger = get_websocket_enhanced_logger()
    
    context = LogContext(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        agent_name=agent_name,
        tool_name=tool_name,
        operation="notification_lifecycle",
        category=EventCategory.NOTIFICATION_DELIVERY
    )
    
    return enhanced_logger.log_context(context)


async def log_system_startup() -> None:
    """Log WebSocket monitoring system startup."""
    enhanced_logger = get_websocket_enhanced_logger()
    
    startup_context = LogContext(
        operation="monitoring_system_startup",
        category=EventCategory.BRIDGE_LIFECYCLE,
        event_type="system_startup"
    )
    
    enhanced_logger.log_structured(
        LogLevel.INFO,
        "WebSocket monitoring system starting up",
        context=startup_context,
        metadata={
            "startup_phase": "initialization",
            "monitoring_components": [
                "notification_monitor",
                "health_checker", 
                "alert_system",
                "enhanced_logging"
            ]
        }
    )


async def log_system_shutdown() -> None:
    """Log WebSocket monitoring system shutdown."""
    enhanced_logger = get_websocket_enhanced_logger()
    
    shutdown_context = LogContext(
        operation="monitoring_system_shutdown",
        category=EventCategory.BRIDGE_LIFECYCLE,
        event_type="system_shutdown"
    )
    
    enhanced_logger.log_structured(
        LogLevel.INFO,
        "WebSocket monitoring system shutting down",
        context=shutdown_context,
        metadata={"shutdown_phase": "cleanup"}
    )