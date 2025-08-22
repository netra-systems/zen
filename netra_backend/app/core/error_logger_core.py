"""Core error logger implementation with aggregation and metrics.

Provides the main ErrorLogger class with comprehensive error logging capabilities.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_logging_context import (
    error_context_manager,
    recovery_logger,
)
from netra_backend.app.core.error_logging_types import (
    DetailedErrorContext,
    ErrorAggregation,
    ErrorCategory,
    ErrorSeverity,
    LogLevel,
)
from netra_backend.app.core.error_recovery import RecoveryContext
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.shared_types import ErrorContext

logger = central_logger.get_logger(__name__)


class ErrorLogger:
    """Enhanced error logger with context and correlation."""
    
    def __init__(self, max_aggregations: int = 10000):
        """Initialize error logger."""
        self.max_aggregations = max_aggregations
        self.error_aggregations: Dict[str, ErrorAggregation] = {}
        self.correlation_tracking: Dict[str, List[str]] = defaultdict(list)
        
        # Performance tracking
        self.logging_metrics = self._init_logging_metrics()
    
    def _init_logging_metrics(self) -> Dict[str, Any]:
        """Initialize logging metrics dictionary."""
        return {
            'total_errors_logged': 0,
            'errors_by_severity': defaultdict(int),
            'errors_by_category': defaultdict(int),
            'unique_error_signatures': 0,
        }
    
    def log_error(
        self,
        error: Exception,
        context: Optional[DetailedErrorContext] = None,
        **kwargs
    ) -> str:
        """Log error with comprehensive context."""
        context = self._ensure_context(error, context, **kwargs)
        self._execute_error_logging_pipeline(error, context)
        return context.error_id
    
    def _execute_error_logging_pipeline(self, error: Exception, context: DetailedErrorContext) -> None:
        """Execute the complete error logging pipeline."""
        self._process_error(error, context)
        self._perform_logging(error, context)
        self._track_correlation(context)
    
    def _ensure_context(
        self,
        error: Exception,
        context: Optional[DetailedErrorContext],
        **kwargs
    ) -> DetailedErrorContext:
        """Ensure context exists or create it."""
        if context is None:
            return self._create_new_context(error, **kwargs)
        return context
    
    def _create_new_context(self, error: Exception, **kwargs) -> DetailedErrorContext:
        """Create new error context."""
        return error_context_manager.create_context(error, **kwargs)
    
    def _process_error(self, error: Exception, context: DetailedErrorContext) -> None:
        """Process error for metrics and aggregation."""
        self._update_metrics(context)
        self._aggregate_error(error, context)
    
    def _perform_logging(self, error: Exception, context: DetailedErrorContext) -> None:
        """Perform actual logging with appropriate level."""
        log_data = self._prepare_log_data(error, context)
        self._write_log(context.severity, str(error), log_data)
    
    def _track_correlation(self, context: DetailedErrorContext) -> None:
        """Track correlation chains."""
        if context.correlation_id:
            self.correlation_tracking[context.correlation_id].append(context.error_id)
    
    def log_recovery_attempt(
        self,
        recovery_context: RecoveryContext,
        recovery_action: str,
        success: bool,
        details: Optional[Dict] = None
    ) -> None:
        """Log error recovery attempts."""
        context = self._create_recovery_context(recovery_context, recovery_action, success, details)
        self._log_recovery_result(recovery_action, success, context)
    
    def _create_recovery_context(
        self,
        recovery_context: RecoveryContext,
        recovery_action: str,
        success: bool,
        details: Optional[Dict]
    ) -> Any:
        """Create recovery context."""
        return recovery_logger.log_recovery_attempt(recovery_context, recovery_action, success, details)
    
    def _log_recovery_result(
        self,
        recovery_action: str,
        success: bool,
        context: Any
    ) -> None:
        """Log the recovery result."""
        log_message = self._format_recovery_message(recovery_action, success)
        self._write_recovery_log(success, log_message, context)
    
    def _write_recovery_log(
        self, success: bool, log_message: str, context: Any
    ) -> None:
        """Write recovery log with appropriate level."""
        log_data = self._prepare_log_data(None, context)
        level = LogLevel.INFO if success else LogLevel.WARNING
        self._write_log_level(level, log_message, log_data)
    
    def _format_recovery_message(self, recovery_action: str, success: bool) -> str:
        """Format recovery attempt log message."""
        status = 'SUCCESS' if success else 'FAILED'
        return f"Recovery attempt {recovery_action}: {status}"
    
    def log_business_impact(
        self,
        error: Exception,
        impact_description: str,
        affected_users: int = 0,
        financial_impact: float = 0.0,
        context: Optional[ErrorContext] = None
    ) -> str:
        """Log error with business impact assessment."""
        enhanced_context = self._create_business_impact_context(error, impact_description, affected_users, financial_impact, context)
        return self.log_error(error, enhanced_context)
    
    def _create_business_impact_context(
        self,
        error: Exception,
        impact_description: str,
        affected_users: int,
        financial_impact: float,
        context: Optional[ErrorContext]
    ) -> Any:
        """Create business impact context."""
        return recovery_logger.log_business_impact_context(error, impact_description, affected_users, financial_impact, context)
    
    def log_security_incident(
        self,
        error: Exception,
        incident_type: str,
        risk_level: str = "medium",
        context: Optional[ErrorContext] = None
    ) -> str:
        """Log security-related errors."""
        enhanced_context = self._create_security_incident_context(error, incident_type, risk_level, context)
        return self.log_error(error, enhanced_context)
    
    def _create_security_incident_context(
        self,
        error: Exception,
        incident_type: str,
        risk_level: str,
        context: Optional[ErrorContext]
    ) -> Any:
        """Create security incident context."""
        return recovery_logger.log_security_incident_context(error, incident_type, risk_level, context)
    
    def get_error_patterns(
        self,
        time_window: Optional[timedelta] = None
    ) -> List[Dict[str, Any]]:
        """Get error patterns for analysis."""
        time_window = self._get_default_time_window(time_window)
        cutoff_time = datetime.now() - time_window
        patterns = self._collect_patterns(cutoff_time)
        return self._sort_patterns_by_count(patterns)
    
    def _get_default_time_window(self, time_window: Optional[timedelta]) -> timedelta:
        """Get default time window if none provided."""
        if time_window is None:
            return timedelta(hours=24)
        return time_window
    
    def _sort_patterns_by_count(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort patterns by count in descending order."""
        patterns.sort(key=lambda x: x['count'], reverse=True)
        return patterns
    
    def _collect_patterns(self, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """Collect error patterns within time window."""
        patterns = []
        for signature, aggregation in self.error_aggregations.items():
            if aggregation.last_seen >= cutoff_time:
                pattern_dict = self._format_pattern(signature, aggregation)
                patterns.append(pattern_dict)
        return patterns
    
    def _format_pattern(self, signature: str, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Format error pattern for output."""
        base_data = self._get_pattern_base_data(signature, aggregation)
        metadata = self._get_pattern_metadata(aggregation)
        return {**base_data, **metadata}
    
    def _get_pattern_base_data(self, signature: str, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Get base pattern data."""
        return {
            'signature': signature,
            'count': aggregation.count,
            'first_seen': aggregation.first_seen.isoformat(),
            'last_seen': aggregation.last_seen.isoformat()
        }
    
    def _get_pattern_metadata(self, aggregation: ErrorAggregation) -> Dict[str, Any]:
        """Get pattern metadata."""
        return {
            'affected_components': list(aggregation.affected_components),
            'affected_users_count': len(aggregation.affected_users),
            'severity_distribution': dict(aggregation.severity_distribution)
        }
    
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
    
    async def get_recent_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent errors within specified hours for compatibility."""
        time_window = timedelta(hours=hours)
        return self.get_error_patterns(time_window)
    
    def _update_metrics(self, context: DetailedErrorContext) -> None:
        """Update logging metrics."""
        self.logging_metrics['total_errors_logged'] += 1
        self.logging_metrics['errors_by_severity'][context.severity.value] += 1
        self.logging_metrics['errors_by_category'][context.category.value] += 1
    
    def _aggregate_error(self, error: Exception, context: DetailedErrorContext) -> None:
        """Aggregate error for pattern analysis."""
        signature = self._create_error_signature(error, context)
        aggregation = self._get_or_create_aggregation(signature)
        self._update_aggregation(aggregation, context)
        self._cleanup_if_needed()
    
    def _cleanup_if_needed(self) -> None:
        """Cleanup old aggregations if limit exceeded."""
        if len(self.error_aggregations) > self.max_aggregations:
            self._cleanup_old_aggregations()
    
    def _get_or_create_aggregation(self, signature: str) -> ErrorAggregation:
        """Get existing aggregation or create new one."""
        if signature not in self.error_aggregations:
            self.error_aggregations[signature] = ErrorAggregation(
                error_signature=signature
            )
            self.logging_metrics['unique_error_signatures'] += 1
        return self.error_aggregations[signature]
    
    def _update_aggregation(
        self, 
        aggregation: ErrorAggregation, 
        context: DetailedErrorContext
    ) -> None:
        """Update aggregation with new occurrence."""
        self._update_aggregation_counts(aggregation, context)
        self._update_all_aggregation_data(aggregation, context)
    
    def _update_aggregation_counts(self, aggregation: ErrorAggregation, context: DetailedErrorContext) -> None:
        """Update aggregation count and timestamp."""
        aggregation.count += 1
        aggregation.last_seen = context.timestamp
    
    def _update_all_aggregation_data(self, aggregation: ErrorAggregation, context: DetailedErrorContext) -> None:
        """Update all aggregation data."""
        self._update_aggregation_components(aggregation, context)
        self._update_aggregation_severity(aggregation, context)
        self._update_aggregation_occurrences(aggregation, context)
    
    def _update_aggregation_components(
        self, 
        aggregation: ErrorAggregation, 
        context: DetailedErrorContext
    ) -> None:
        """Update aggregation component tracking."""
        self._add_component_if_present(aggregation, context)
        self._add_user_if_present(aggregation, context)
    
    def _add_component_if_present(self, aggregation: ErrorAggregation, context: DetailedErrorContext) -> None:
        """Add component to aggregation if present."""
        if context.component:
            aggregation.affected_components.add(context.component)
    
    def _add_user_if_present(self, aggregation: ErrorAggregation, context: DetailedErrorContext) -> None:
        """Add user to aggregation if present."""
        if context.user_id:
            aggregation.affected_users.add(context.user_id)
    
    def _update_aggregation_severity(
        self, 
        aggregation: ErrorAggregation, 
        context: DetailedErrorContext
    ) -> None:
        """Update aggregation severity distribution."""
        severity_key = context.severity.value
        current_count = aggregation.severity_distribution.get(severity_key, 0)
        aggregation.severity_distribution[severity_key] = current_count + 1
    
    def _update_aggregation_occurrences(
        self, 
        aggregation: ErrorAggregation, 
        context: DetailedErrorContext
    ) -> None:
        """Update aggregation recent occurrences."""
        occurrence_data = self._create_occurrence_data(context)
        aggregation.recent_occurrences.append(occurrence_data)
    
    def _create_occurrence_data(self, context: DetailedErrorContext) -> Dict[str, Any]:
        """Create occurrence data from context."""
        return {
            'error_id': context.error_id,
            'timestamp': context.timestamp.isoformat(),
            'component': context.component,
            'user_id': context.user_id
        }
    
    def _create_error_signature(self, error: Exception, context: DetailedErrorContext) -> str:
        """Create a signature for error aggregation."""
        components = self._build_signature_components(error, context)
        components = self._add_stack_trace_fingerprint(components, context)
        return '|'.join(components)
    
    def _build_signature_components(
        self, 
        error: Exception, 
        context: DetailedErrorContext
    ) -> List[str]:
        """Build base signature components."""
        error_info = self._get_error_signature_info(error)
        context_info = self._get_context_signature_info(context)
        return [*error_info, *context_info]
    
    def _get_error_signature_info(self, error: Exception) -> List[str]:
        """Get error information for signature."""
        return [
            type(error).__name__,
            str(error)[:100]  # First 100 chars of error message
        ]
    
    def _get_context_signature_info(self, context: DetailedErrorContext) -> List[str]:
        """Get context information for signature."""
        return [
            context.component or 'unknown',
            context.operation_type.value if context.operation_type else 'unknown'
        ]
    
    def _add_stack_trace_fingerprint(
        self, 
        components: List[str], 
        context: DetailedErrorContext
    ) -> List[str]:
        """Add stack trace fingerprint to signature."""
        if not context.stack_trace:
            return components
        return self._append_stack_trace_components(components, context.stack_trace)
    
    def _append_stack_trace_components(self, components: List[str], stack_trace: str) -> List[str]:
        """Append stack trace components to signature."""
        stack_lines = stack_trace.split('\n')
        relevant_lines = self._extract_relevant_stack_lines(stack_lines)
        components.extend(relevant_lines)
        return components
    
    def _extract_relevant_stack_lines(self, stack_lines: List[str]) -> List[str]:
        """Extract relevant lines from stack trace."""
        relevant_lines = [
            line.strip() for line in stack_lines
            if 'File "' in line and 'app/' in line
        ][:3]  # First 3 relevant stack frames
        return relevant_lines
    
    def _cleanup_old_aggregations(self) -> None:
        """Remove old error aggregations to maintain memory limits."""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        old_signatures = self._find_old_signatures(cutoff_time)
        self._remove_old_signatures(old_signatures)
        
        logger.debug(f"Cleaned up {len(old_signatures)} old error aggregations")
    
    def _find_old_signatures(self, cutoff_time: datetime) -> List[str]:
        """Find signatures older than cutoff time."""
        return [
            signature for signature, aggregation in self.error_aggregations.items()
            if aggregation.last_seen < cutoff_time
        ]
    
    def _remove_old_signatures(self, old_signatures: List[str]) -> None:
        """Remove old signatures from aggregations."""
        for signature in old_signatures:
            del self.error_aggregations[signature]
    
    def _prepare_log_data(
        self,
        error: Optional[Exception],
        context: DetailedErrorContext
    ) -> Dict[str, Any]:
        """Prepare structured log data."""
        log_data = context.to_dict()
        return self._finalize_log_data(log_data, error)
    
    def _finalize_log_data(self, log_data: Dict[str, Any], error: Optional[Exception]) -> Dict[str, Any]:
        """Finalize log data with error information."""
        if error:
            self._add_error_data_to_log(log_data, error)
        return log_data
    
    def _add_error_data_to_log(self, log_data: Dict[str, Any], error: Exception) -> None:
        """Add error data to log data."""
        error_data = self._extract_error_data(error)
        log_data.update(error_data)
    
    def _extract_error_data(self, error: Exception) -> Dict[str, Any]:
        """Extract data from exception."""
        return {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'error_args': error.args if hasattr(error, 'args') else []
        }
    
    def _write_log(
        self,
        severity: ErrorSeverity,
        message: str,
        data: Dict[str, Any]
    ) -> None:
        """Write log with appropriate level."""
        log_func = self._get_log_function_for_severity(severity)
        log_func(message, **data)
    
    def _get_log_function_for_severity(self, severity: ErrorSeverity):
        """Get log function for given severity."""
        severity_map = self._get_severity_log_map()
        return severity_map.get(severity, logger.info)
    
    def _get_severity_log_map(self) -> Dict[ErrorSeverity, Any]:
        """Get severity to log function mapping."""
        return {
            ErrorSeverity.CRITICAL: logger.critical,
            ErrorSeverity.HIGH: logger.error,
            ErrorSeverity.MEDIUM: logger.warning,
        }
    
    def _write_log_level(
        self,
        level: LogLevel,
        message: str,
        data: Dict[str, Any]
    ) -> None:
        """Write log with specific level."""
        log_func = self._get_log_function_for_level(level)
        log_func(message, **data)
    
    def _get_log_function_for_level(self, level: LogLevel):
        """Get log function for given level."""
        level_map = self._get_level_log_map()
        return level_map.get(level, logger.debug)
    
    def _get_level_log_map(self) -> Dict[LogLevel, Any]:
        """Get level to log function mapping."""
        return {
            LogLevel.CRITICAL: logger.critical,
            LogLevel.ERROR: logger.error,
            LogLevel.WARNING: logger.warning,
            LogLevel.INFO: logger.info,
        }


# Global error logger instance
error_logger = ErrorLogger()