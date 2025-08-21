"""Error context management and utilities for error logging.

Provides context managers and utilities for maintaining error context across operations.
"""

import traceback
from contextlib import contextmanager
from typing import Optional, List

from netra_backend.app.core.error_logging_types import (
    DetailedErrorContext, 
    ErrorCategory, 
    ErrorSeverity,
    LogLevel
)
from netra_backend.app.core.error_codes import ErrorCode
from netra_backend.app.core.error_recovery import OperationType, RecoveryContext
from netra_backend.app.schemas.shared_types import ErrorContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorContextManager:
    """Manages error context stack and inheritance."""
    
    def __init__(self):
        """Initialize context manager."""
        self.context_stack: List[DetailedErrorContext] = []
    
    def create_context(
        self,
        error: Exception,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        **kwargs
    ) -> DetailedErrorContext:
        """Create rich error context from exception and additional data."""
        context = self._build_base_context(error, severity, category, **kwargs)
        return self._inherit_parent_context(context)
    
    def _build_base_context(
        self,
        error: Exception,
        severity: Optional[ErrorSeverity],
        category: Optional[ErrorCategory],
        **kwargs
    ) -> DetailedErrorContext:
        """Build base context from error and parameters."""
        context_data = self._prepare_context_data(error, severity, category)
        return DetailedErrorContext(**context_data, **kwargs)
    
    def _prepare_context_data(
        self, 
        error: Exception, 
        severity: Optional[ErrorSeverity], 
        category: Optional[ErrorCategory]
    ) -> dict:
        """Prepare context data dictionary."""
        return {
            'severity': severity or self._determine_severity(error),
            'category': category or self._determine_category(error),
            'error_code': self._determine_error_code(error),
            'stack_trace': traceback.format_exc(),
        }
    
    def _inherit_parent_context(self, context: DetailedErrorContext) -> DetailedErrorContext:
        """Inherit context from parent if available."""
        if not self.context_stack:
            return context
        parent = self.context_stack[-1]
        return self._copy_parent_fields(context, parent)
    
    def _copy_parent_fields(
        self, 
        context: DetailedErrorContext, 
        parent: DetailedErrorContext
    ) -> DetailedErrorContext:
        """Copy relevant fields from parent context."""
        self._copy_identification_fields(context, parent)
        self._copy_session_fields(context, parent)
        return context
    
    def _copy_identification_fields(
        self, context: DetailedErrorContext, parent: DetailedErrorContext
    ) -> None:
        """Copy identification fields from parent."""
        context.correlation_id = parent.correlation_id
        context.trace_id = parent.trace_id
    
    def _copy_session_fields(
        self, context: DetailedErrorContext, parent: DetailedErrorContext
    ) -> None:
        """Copy session-related fields from parent."""
        context.session_id = parent.session_id
        context.user_id = parent.user_id
    
    @contextmanager
    def error_context(self, **context_kwargs):
        """Context manager for maintaining error context across operations."""
        context = DetailedErrorContext(**context_kwargs)
        self.context_stack.append(context)
        try:
            yield context
        finally:
            self.context_stack.pop()
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity from exception type."""
        severity_mapping = self._get_severity_mapping()
        error_type = type(error).__name__
        return severity_mapping.get(error_type, ErrorSeverity.MEDIUM)
    
    def _determine_category(self, error: Exception) -> ErrorCategory:
        """Determine error category from exception type."""
        category_mapping = self._get_category_mapping()
        error_type = type(error).__name__
        return category_mapping.get(error_type, ErrorCategory.APPLICATION)
    
    def _determine_error_code(self, error: Exception) -> Optional[ErrorCode]:
        """Determine error code from exception type."""
        code_mapping = self._get_code_mapping()
        error_type = type(error).__name__
        return code_mapping.get(error_type)
    
    def _get_severity_mapping(self) -> dict:
        """Get error type to severity mapping."""
        critical_errors = self._get_critical_severity_errors()
        high_errors = self._get_high_severity_errors()
        medium_errors = self._get_medium_severity_errors()
        return {**critical_errors, **high_errors, **medium_errors}
    
    def _get_critical_severity_errors(self) -> dict:
        """Get critical severity error mappings."""
        return {
            'MemoryError': ErrorSeverity.CRITICAL,
            'SystemExit': ErrorSeverity.CRITICAL,
        }
    
    def _get_high_severity_errors(self) -> dict:
        """Get high severity error mappings."""
        return {
            'KeyboardInterrupt': ErrorSeverity.HIGH,
            'ConnectionError': ErrorSeverity.HIGH,
            'ValueError': ErrorSeverity.HIGH,
            'TypeError': ErrorSeverity.HIGH,
            'PermissionError': ErrorSeverity.HIGH,
        }
    
    def _get_medium_severity_errors(self) -> dict:
        """Get medium severity error mappings."""
        return {
            'TimeoutError': ErrorSeverity.MEDIUM,
            'AttributeError': ErrorSeverity.MEDIUM,
            'KeyError': ErrorSeverity.MEDIUM,
            'FileNotFoundError': ErrorSeverity.MEDIUM,
        }
    
    def _get_category_mapping(self) -> dict:
        """Get error type to category mapping."""
        security_errors = self._get_security_category_errors()
        infra_errors = self._get_infrastructure_category_errors()
        app_errors = self._get_application_category_errors()
        system_errors = self._get_system_category_errors()
        return {**security_errors, **infra_errors, **app_errors, **system_errors}
    
    def _get_security_category_errors(self) -> dict:
        """Get security category error mappings."""
        return {'PermissionError': ErrorCategory.SECURITY}
    
    def _get_infrastructure_category_errors(self) -> dict:
        """Get infrastructure category error mappings."""
        return {
            'ConnectionError': ErrorCategory.INFRASTRUCTURE,
            'TimeoutError': ErrorCategory.INFRASTRUCTURE,
        }
    
    def _get_application_category_errors(self) -> dict:
        """Get application category error mappings."""
        return {
            'ValueError': ErrorCategory.APPLICATION,
            'TypeError': ErrorCategory.APPLICATION,
            'KeyError': ErrorCategory.APPLICATION,
        }
    
    def _get_system_category_errors(self) -> dict:
        """Get system category error mappings."""
        return {
            'FileNotFoundError': ErrorCategory.SYSTEM,
            'MemoryError': ErrorCategory.SYSTEM,
        }
    
    def _get_code_mapping(self) -> dict:
        """Get error type to error code mapping."""
        return {
            'ConnectionError': ErrorCode.DATABASE_CONNECTION_FAILED,
            'TimeoutError': ErrorCode.SERVICE_TIMEOUT,
            'ValueError': ErrorCode.VALIDATION_ERROR,
            'PermissionError': ErrorCode.AUTHORIZATION_FAILED,
            'FileNotFoundError': ErrorCode.FILE_NOT_FOUND,
        }


class RecoveryLogger:
    """Handles logging of recovery attempts and business impact."""
    
    def __init__(self, context_manager: ErrorContextManager):
        """Initialize with context manager."""
        self.context_manager = context_manager
    
    def log_recovery_attempt(
        self,
        recovery_context: RecoveryContext,
        recovery_action: str,
        success: bool,
        details: Optional[dict] = None
    ) -> DetailedErrorContext:
        """Create context for recovery attempt logging."""
        context = self._build_recovery_context(
            recovery_context, recovery_action, success, details
        )
        return context
    
    def log_business_impact_context(
        self,
        error: Exception,
        impact_description: str,
        affected_users: int = 0,
        financial_impact: float = 0.0,
        context: Optional[ErrorContext] = None
    ) -> DetailedErrorContext:
        """Create context for business impact logging."""
        context = self._get_or_create_context(error, context)
        enhanced_context = self._enhance_business_context(context, impact_description, affected_users, financial_impact)
        return enhanced_context
    
    def _get_or_create_context(self, error: Exception, context: Optional[ErrorContext]) -> DetailedErrorContext:
        """Get existing context or create new one."""
        if context is None:
            return self.context_manager.create_context(error)
        return context
    
    def log_security_incident_context(
        self,
        error: Exception,
        incident_type: str,
        risk_level: str = "medium",
        context: Optional[ErrorContext] = None
    ) -> DetailedErrorContext:
        """Create context for security incident logging."""
        if context is None:
            context = self.context_manager.create_context(error)
        
        context = self._enhance_security_context(context, incident_type, risk_level)
        return context
    
    def _build_recovery_context(
        self,
        recovery_context: RecoveryContext,
        recovery_action: str,
        success: bool,
        details: Optional[dict]
    ) -> DetailedErrorContext:
        """Build context for recovery logging."""
        context_data = self._prepare_recovery_context_data(recovery_context, recovery_action, success, details)
        return DetailedErrorContext(**context_data)
    
    def _prepare_recovery_context_data(
        self, recovery_context: RecoveryContext, recovery_action: str, success: bool, details: Optional[dict]
    ) -> dict:
        """Prepare recovery context data dictionary."""
        basic_data = self._get_recovery_basic_data(recovery_context, success)
        metadata = self._build_recovery_metadata(recovery_action, success, recovery_context, details)
        return {**basic_data, 'metadata': metadata, 'tags': ['recovery', 'automation']}
    
    def _get_recovery_basic_data(self, recovery_context: RecoveryContext, success: bool) -> dict:
        """Get basic recovery context data."""
        return {
            'correlation_id': recovery_context.operation_id,
            'operation_type': recovery_context.operation_type,
            'operation_id': recovery_context.operation_id,
            'severity': ErrorSeverity.INFO if success else ErrorSeverity.WARNING,
            'category': ErrorCategory.SYSTEM
        }
    
    def _enhance_business_context(
        self,
        context: DetailedErrorContext,
        impact_description: str,
        affected_users: int,
        financial_impact: float
    ) -> DetailedErrorContext:
        """Enhance context with business impact information."""
        context.business_impact = impact_description
        context.affected_users = affected_users
        context.financial_impact = financial_impact
        context.category = ErrorCategory.BUSINESS
        context.tags.extend(['business_impact', 'customer_facing'])
        return context
    
    def _enhance_security_context(
        self,
        context: DetailedErrorContext,
        incident_type: str,
        risk_level: str
    ) -> DetailedErrorContext:
        """Enhance context with security incident information."""
        self._apply_security_settings(context)
        self._add_security_metadata(context, incident_type, risk_level)
        self._add_security_tags(context, risk_level)
        return context
    
    def _apply_security_settings(self, context: DetailedErrorContext) -> None:
        """Apply security-specific severity and category."""
        context.severity = ErrorSeverity.HIGH
        context.category = ErrorCategory.SECURITY
    
    def _add_security_metadata(self, context: DetailedErrorContext, incident_type: str, risk_level: str) -> None:
        """Add security incident metadata to context."""
        context.metadata.update({
            'incident_type': incident_type,
            'risk_level': risk_level,
            'requires_investigation': True
        })
    
    def _add_security_tags(self, context: DetailedErrorContext, risk_level: str) -> None:
        """Add security-related tags to context."""
        context.tags.extend(['security', 'incident', risk_level])
    
    def _build_recovery_metadata(
        self,
        recovery_action: str,
        success: bool,
        recovery_context: RecoveryContext,
        details: Optional[dict]
    ) -> dict:
        """Build metadata for recovery context."""
        return {
            'recovery_action': recovery_action,
            'success': success,
            'retry_count': recovery_context.retry_count,
            'elapsed_time_ms': recovery_context.elapsed_time.total_seconds() * 1000,
            'details': details or {}
        }


# Global context manager instance
error_context_manager = ErrorContextManager()
recovery_logger = RecoveryLogger(error_context_manager)