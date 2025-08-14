"""Comprehensive error logging system with rich context and correlation.

Provides structured error logging with detailed context, correlation IDs,
error aggregation, and integration with monitoring systems.
"""

import json
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable
from collections import defaultdict, deque

from app.core.error_codes import ErrorCode, ErrorSeverity
from app.core.error_recovery import RecoveryContext, OperationType
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class LogLevel(Enum):
    """Enhanced log levels for error logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SECURITY = "security"
    BUSINESS = "business"


class ErrorCategory(Enum):
    """Categories for error classification."""
    SYSTEM = "system"
    APPLICATION = "application"
    SECURITY = "security"
    BUSINESS = "business"
    INFRASTRUCTURE = "infrastructure"
    INTEGRATION = "integration"
    USER = "user"


@dataclass
class DetailedErrorContext:
    """Rich context information for error logging with extensive metadata."""
    # Core identifiers
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Temporal information
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Error classification
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.APPLICATION
    error_code: Optional[ErrorCode] = None
    
    # Operational context
    operation_type: Optional[OperationType] = None
    operation_id: Optional[str] = None
    agent_type: Optional[str] = None
    component: Optional[str] = None
    
    # User and request context
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Technical context
    stack_trace: Optional[str] = None
    environment: str = "development"
    version: Optional[str] = None
    
    # Business context
    business_impact: Optional[str] = None
    affected_users: int = 0
    financial_impact: float = 0.0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        
        # Convert enums to values
        if isinstance(data.get('severity'), ErrorSeverity):
            data['severity'] = data['severity'].value
        if isinstance(data.get('category'), ErrorCategory):
            data['category'] = data['category'].value
        if isinstance(data.get('error_code'), ErrorCode):
            data['error_code'] = data['error_code'].value
        if isinstance(data.get('operation_type'), OperationType):
            data['operation_type'] = data['operation_type'].value
        
        # Convert datetime to ISO string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        
        return data


@dataclass
class ErrorAggregation:
    """Aggregated error information for pattern analysis."""
    error_signature: str
    count: int = 0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    affected_components: Set[str] = field(default_factory=set)
    affected_users: Set[str] = field(default_factory=set)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    recent_occurrences: deque = field(default_factory=lambda: deque(maxlen=100))


class ErrorLogger:
    """Enhanced error logger with context and correlation."""
    
    def __init__(self, max_aggregations: int = 10000):
        """Initialize error logger."""
        self.max_aggregations = max_aggregations
        self.error_aggregations: Dict[str, ErrorAggregation] = {}
        self.correlation_tracking: Dict[str, List[str]] = defaultdict(list)
        self.context_stack: List[DetailedErrorContext] = []
        
        # Performance tracking
        self.logging_metrics = {
            'total_errors_logged': 0,
            'errors_by_severity': defaultdict(int),
            'errors_by_category': defaultdict(int),
            'unique_error_signatures': 0,
        }
    
    def create_context(
        self,
        error: Exception,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        **kwargs
    ) -> DetailedErrorContext:
        """Create rich error context from exception and additional data."""
        context = DetailedErrorContext(
            severity=severity or self._determine_severity(error),
            category=category or self._determine_category(error),
            error_code=self._determine_error_code(error),
            stack_trace=traceback.format_exc(),
            **kwargs
        )
        
        # Inherit context from stack if available
        if self.context_stack:
            parent_context = self.context_stack[-1]
            context.correlation_id = parent_context.correlation_id
            context.trace_id = parent_context.trace_id
            context.session_id = parent_context.session_id
            context.user_id = parent_context.user_id
        
        return context
    
    def log_error(
        self,
        error: Exception,
        context: Optional[DetailedErrorContext] = None,
        **kwargs
    ) -> str:
        """Log error with comprehensive context."""
        if context is None:
            context = self.create_context(error, **kwargs)
        
        # Update metrics
        self._update_metrics(context)
        
        # Aggregate error for pattern analysis
        self._aggregate_error(error, context)
        
        # Log with appropriate level
        log_data = self._prepare_log_data(error, context)
        self._write_log(context.severity, str(error), log_data)
        
        # Track correlation
        if context.correlation_id:
            self.correlation_tracking[context.correlation_id].append(context.error_id)
        
        return context.error_id
    
    def log_recovery_attempt(
        self,
        recovery_context: RecoveryContext,
        recovery_action: str,
        success: bool,
        details: Optional[Dict] = None
    ) -> None:
        """Log error recovery attempts."""
        context = DetailedErrorContext(
            correlation_id=recovery_context.operation_id,
            operation_type=recovery_context.operation_type,
            operation_id=recovery_context.operation_id,
            severity=ErrorSeverity.INFO if success else ErrorSeverity.WARNING,
            category=ErrorCategory.SYSTEM,
            metadata={
                'recovery_action': recovery_action,
                'success': success,
                'retry_count': recovery_context.retry_count,
                'elapsed_time_ms': recovery_context.elapsed_time.total_seconds() * 1000,
                'details': details or {}
            },
            tags=['recovery', 'automation']
        )
        
        log_message = f"Recovery attempt {recovery_action}: {'SUCCESS' if success else 'FAILED'}"
        log_data = self._prepare_log_data(None, context)
        
        level = LogLevel.INFO if success else LogLevel.WARNING
        self._write_log_level(level, log_message, log_data)
    
    def log_business_impact(
        self,
        error: Exception,
        impact_description: str,
        affected_users: int = 0,
        financial_impact: float = 0.0,
        context: Optional[ErrorContext] = None
    ) -> str:
        """Log error with business impact assessment."""
        if context is None:
            context = self.create_context(error)
        
        context.business_impact = impact_description
        context.affected_users = affected_users
        context.financial_impact = financial_impact
        context.category = ErrorCategory.BUSINESS
        context.tags.extend(['business_impact', 'customer_facing'])
        
        return self.log_error(error, context)
    
    def log_security_incident(
        self,
        error: Exception,
        incident_type: str,
        risk_level: str = "medium",
        context: Optional[ErrorContext] = None
    ) -> str:
        """Log security-related errors."""
        if context is None:
            context = self.create_context(error)
        
        context.severity = ErrorSeverity.HIGH
        context.category = ErrorCategory.SECURITY
        context.metadata.update({
            'incident_type': incident_type,
            'risk_level': risk_level,
            'requires_investigation': True
        })
        context.tags.extend(['security', 'incident', risk_level])
        
        return self.log_error(error, context)
    
    @contextmanager
    def error_context(self, **context_kwargs):
        """Context manager for maintaining error context across operations."""
        context = DetailedErrorContext(**context_kwargs)
        self.context_stack.append(context)
        try:
            yield context
        finally:
            self.context_stack.pop()
    
    def get_error_patterns(
        self,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Get error patterns for analysis."""
        if time_window is None:
            time_window = timedelta(hours=24)
        
        cutoff_time = datetime.now() - time_window
        patterns = []
        
        for signature, aggregation in self.error_aggregations.items():
            if aggregation.last_seen >= cutoff_time:
                patterns.append({
                    'signature': signature,
                    'count': aggregation.count,
                    'first_seen': aggregation.first_seen.isoformat(),
                    'last_seen': aggregation.last_seen.isoformat(),
                    'affected_components': list(aggregation.affected_components),
                    'affected_users_count': len(aggregation.affected_users),
                    'severity_distribution': dict(aggregation.severity_distribution)
                })
        
        # Sort by count descending
        patterns.sort(key=lambda x: x['count'], reverse=True)
        return patterns
    
    def get_correlation_chain(self, correlation_id: str) -> List[str]:
        """Get all error IDs in a correlation chain."""
        return self.correlation_tracking.get(correlation_id, [])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging metrics."""
        return {
            **self.logging_metrics,
            'errors_by_severity': dict(self.logging_metrics['errors_by_severity']),
            'errors_by_category': dict(self.logging_metrics['errors_by_category']),
            'active_aggregations': len(self.error_aggregations),
            'correlation_chains': len(self.correlation_tracking)
        }
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity from exception type."""
        severity_mapping = {
            'MemoryError': ErrorSeverity.CRITICAL,
            'SystemExit': ErrorSeverity.CRITICAL,
            'KeyboardInterrupt': ErrorSeverity.HIGH,
            'ConnectionError': ErrorSeverity.HIGH,
            'TimeoutError': ErrorSeverity.MEDIUM,
            'ValueError': ErrorSeverity.HIGH,
            'TypeError': ErrorSeverity.HIGH,
            'AttributeError': ErrorSeverity.MEDIUM,
            'KeyError': ErrorSeverity.MEDIUM,
            'FileNotFoundError': ErrorSeverity.MEDIUM,
            'PermissionError': ErrorSeverity.HIGH,
        }
        
        error_type = type(error).__name__
        return severity_mapping.get(error_type, ErrorSeverity.MEDIUM)
    
    def _determine_category(self, error: Exception) -> ErrorCategory:
        """Determine error category from exception type."""
        category_mapping = {
            'PermissionError': ErrorCategory.SECURITY,
            'ConnectionError': ErrorCategory.INFRASTRUCTURE,
            'TimeoutError': ErrorCategory.INFRASTRUCTURE,
            'ValueError': ErrorCategory.APPLICATION,
            'TypeError': ErrorCategory.APPLICATION,
            'KeyError': ErrorCategory.APPLICATION,
            'FileNotFoundError': ErrorCategory.SYSTEM,
            'MemoryError': ErrorCategory.SYSTEM,
        }
        
        error_type = type(error).__name__
        return category_mapping.get(error_type, ErrorCategory.APPLICATION)
    
    def _determine_error_code(self, error: Exception) -> Optional[ErrorCode]:
        """Determine error code from exception type."""
        code_mapping = {
            'ConnectionError': ErrorCode.DATABASE_CONNECTION_FAILED,
            'TimeoutError': ErrorCode.SERVICE_TIMEOUT,
            'ValueError': ErrorCode.VALIDATION_ERROR,
            'PermissionError': ErrorCode.AUTHORIZATION_FAILED,
            'FileNotFoundError': ErrorCode.FILE_NOT_FOUND,
        }
        
        error_type = type(error).__name__
        return code_mapping.get(error_type)
    
    def _update_metrics(self, context: DetailedErrorContext) -> None:
        """Update logging metrics."""
        self.logging_metrics['total_errors_logged'] += 1
        self.logging_metrics['errors_by_severity'][context.severity.value] += 1
        self.logging_metrics['errors_by_category'][context.category.value] += 1
    
    def _aggregate_error(self, error: Exception, context: DetailedErrorContext) -> None:
        """Aggregate error for pattern analysis."""
        signature = self._create_error_signature(error, context)
        
        if signature not in self.error_aggregations:
            self.error_aggregations[signature] = ErrorAggregation(
                error_signature=signature
            )
            self.logging_metrics['unique_error_signatures'] += 1
        
        aggregation = self.error_aggregations[signature]
        aggregation.count += 1
        aggregation.last_seen = context.timestamp
        
        if context.component:
            aggregation.affected_components.add(context.component)
        if context.user_id:
            aggregation.affected_users.add(context.user_id)
        
        severity_key = context.severity.value
        aggregation.severity_distribution[severity_key] = (
            aggregation.severity_distribution.get(severity_key, 0) + 1
        )
        
        aggregation.recent_occurrences.append({
            'error_id': context.error_id,
            'timestamp': context.timestamp.isoformat(),
            'component': context.component,
            'user_id': context.user_id
        })
        
        # Cleanup old aggregations if limit exceeded
        if len(self.error_aggregations) > self.max_aggregations:
            self._cleanup_old_aggregations()
    
    def _create_error_signature(self, error: Exception, context: DetailedErrorContext) -> str:
        """Create a signature for error aggregation."""
        components = [
            type(error).__name__,
            str(error)[:100],  # First 100 chars of error message
            context.component or 'unknown',
            context.operation_type.value if context.operation_type else 'unknown'
        ]
        
        # Add stack trace fingerprint (first few frames)
        if context.stack_trace:
            stack_lines = context.stack_trace.split('\n')
            relevant_lines = [
                line.strip() for line in stack_lines
                if 'File "' in line and 'app/' in line
            ][:3]  # First 3 relevant stack frames
            components.extend(relevant_lines)
        
        return '|'.join(components)
    
    def _cleanup_old_aggregations(self) -> None:
        """Remove old error aggregations to maintain memory limits."""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        old_signatures = [
            signature for signature, aggregation in self.error_aggregations.items()
            if aggregation.last_seen < cutoff_time
        ]
        
        for signature in old_signatures:
            del self.error_aggregations[signature]
        
        logger.debug(f"Cleaned up {len(old_signatures)} old error aggregations")
    
    def _prepare_log_data(
        self,
        error: Optional[Exception],
        context: DetailedErrorContext
    ) -> Dict[str, Any]:
        """Prepare structured log data."""
        log_data = context.to_dict()
        
        if error:
            log_data.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'error_args': error.args if hasattr(error, 'args') else []
            })
        
        return log_data
    
    def _write_log(
        self,
        severity: ErrorSeverity,
        message: str,
        data: Dict[str, Any]
    ) -> None:
        """Write log with appropriate level."""
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(message, **data)
        elif severity == ErrorSeverity.HIGH:
            logger.error(message, **data)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(message, **data)
        else:
            logger.info(message, **data)
    
    def _write_log_level(
        self,
        level: LogLevel,
        message: str,
        data: Dict[str, Any]
    ) -> None:
        """Write log with specific level."""
        if level == LogLevel.CRITICAL:
            logger.critical(message, **data)
        elif level == LogLevel.ERROR:
            logger.error(message, **data)
        elif level == LogLevel.WARNING:
            logger.warning(message, **data)
        elif level == LogLevel.INFO:
            logger.info(message, **data)
        else:
            logger.debug(message, **data)


class ErrorReportGenerator:
    """Generates comprehensive error reports."""
    
    def __init__(self, error_logger: ErrorLogger):
        """Initialize with error logger."""
        self.error_logger = error_logger
    
    def generate_summary_report(
        self,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Generate error summary report."""
        if time_window is None:
            time_window = timedelta(hours=24)
        
        patterns = self.error_logger.get_error_patterns(time_window)
        metrics = self.error_logger.get_metrics()
        
        # Calculate derived metrics
        total_errors = sum(pattern['count'] for pattern in patterns)
        critical_errors = sum(
            pattern['severity_distribution'].get('critical', 0)
            for pattern in patterns
        )
        
        return {
            'report_period': {
                'duration_hours': time_window.total_seconds() / 3600,
                'end_time': datetime.now().isoformat()
            },
            'summary': {
                'total_errors': total_errors,
                'unique_error_patterns': len(patterns),
                'critical_errors': critical_errors,
                'error_rate_per_hour': total_errors / (time_window.total_seconds() / 3600)
            },
            'top_error_patterns': patterns[:10],
            'metrics': metrics
        }
    
    def generate_detailed_report(
        self,
        error_signature: str
    ) -> Optional[Dict[str, Any]]:
        """Generate detailed report for specific error pattern."""
        aggregation = self.error_logger.error_aggregations.get(error_signature)
        if not aggregation:
            return None
        
        return {
            'error_signature': error_signature,
            'statistics': {
                'total_occurrences': aggregation.count,
                'first_seen': aggregation.first_seen.isoformat(),
                'last_seen': aggregation.last_seen.isoformat(),
                'affected_components': list(aggregation.affected_components),
                'affected_users_count': len(aggregation.affected_users),
                'severity_distribution': dict(aggregation.severity_distribution)
            },
            'recent_occurrences': list(aggregation.recent_occurrences),
            'recommendations': self._generate_recommendations(aggregation)
        }
    
    def _generate_recommendations(
        self,
        aggregation: ErrorAggregation
    ) -> List[str]:
        """Generate recommendations based on error pattern."""
        recommendations = []
        
        if aggregation.count > 100:
            recommendations.append(
                "High frequency error - consider implementing circuit breaker"
            )
        
        if len(aggregation.affected_components) > 5:
            recommendations.append(
                "Error affects multiple components - investigate common dependencies"
            )
        
        critical_count = aggregation.severity_distribution.get('critical', 0)
        if critical_count > 0:
            recommendations.append(
                f"Contains {critical_count} critical errors - prioritize investigation"
            )
        
        if len(aggregation.affected_users) > 50:
            recommendations.append(
                "High user impact - consider emergency response procedures"
            )
        
        return recommendations


# Global error logger instance
error_logger = ErrorLogger()
error_report_generator = ErrorReportGenerator(error_logger)


# Convenience functions for common use cases
def log_agent_error(
    agent_type: str,
    operation: str,
    error: Exception,
    user_id: Optional[str] = None,
    **kwargs
) -> str:
    """Log agent-specific error."""
    context = error_logger.create_context(
        error,
        agent_type=agent_type,
        component=f"{agent_type}_agent",
        operation_id=operation,
        user_id=user_id,
        tags=['agent', agent_type],
        **kwargs
    )
    return error_logger.log_error(error, context)


def log_database_error(
    table_name: str,
    operation: str,
    error: Exception,
    **kwargs
) -> str:
    """Log database-specific error."""
    context = error_logger.create_context(
        error,
        component='database',
        operation_type=OperationType.DATABASE_WRITE if operation in ['INSERT', 'UPDATE', 'DELETE'] else OperationType.DATABASE_READ,
        metadata={'table_name': table_name, 'sql_operation': operation},
        tags=['database', operation.lower()],
        **kwargs
    )
    return error_logger.log_error(error, context)


def log_api_error(
    endpoint: str,
    method: str,
    error: Exception,
    status_code: Optional[int] = None,
    **kwargs
) -> str:
    """Log API-specific error."""
    context = error_logger.create_context(
        error,
        component='api',
        metadata={
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code
        },
        tags=['api', method.lower()],
        **kwargs
    )
    return error_logger.log_error(error, context)