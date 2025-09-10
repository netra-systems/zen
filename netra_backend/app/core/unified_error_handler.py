"""
Unified Error Handler Framework - Single Source of Truth for ALL Error Handling

This module provides the complete, unified error handling framework for the entire
netra_backend service. All error handling must go through this framework.

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is the ONLY error handling implementation in the service
- All other error handlers are deprecated and must be removed
- Uses canonical types from schemas.core_enums and schemas.shared_types
- Supports all domain-specific requirements (API, Agent, WebSocket, Database, etc.)

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & Operational Excellence
- Value Impact: Consistent error experience, reduced downtime, improved debugging
- Strategic Impact: Single maintenance point, reduced complexity, faster development
"""

import asyncio
import time
import traceback
import linecache
import inspect
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.error_response import ErrorResponse
from netra_backend.app.core.exceptions_agent import AgentError
from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.core_enums import ErrorCategory
from netra_backend.app.schemas.shared_types import ErrorContext
from shared.isolated_environment import get_environment_manager

logger = central_logger.get_logger(__name__)


class ErrorHandlingResult:
    """
    Result object for error handling operations.
    
    Provides a standardized interface for reporting error handling outcomes,
    including recovery attempts, success status, and any resulting data.
    """
    
    def __init__(
        self,
        attempted: bool = False,
        success: bool = False,
        retry_after: Optional[float] = None,
        result: Optional[Any] = None,
        error: Optional[Exception] = None,
        recovery_method: Optional[str] = None
    ):
        """Initialize error handling result."""
        self.attempted = attempted
        self.success = success
        self.retry_after = retry_after
        self.result = result
        self.error = error
        self.recovery_method = recovery_method


class RecoveryStrategy(ABC):
    """Base class for error recovery strategies."""
    
    @abstractmethod
    async def attempt_recovery(
        self, 
        error: Exception, 
        context: ErrorContext,
        operation: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Attempt error recovery."""
        pass


class RetryRecoveryStrategy(RecoveryStrategy):
    """Retry-based recovery strategy using UnifiedRetryHandler."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        # Import here to avoid circular imports
        from netra_backend.app.core.resilience.unified_retry_handler import (
            UnifiedRetryHandler, RetryConfig, RetryStrategy
        )
        
        self.max_retries = max_retries
        self.base_delay = base_delay
        
        # Create unified retry handler with appropriate config
        retry_config = RetryConfig(
            max_attempts=max_retries,
            base_delay=base_delay,
            strategy=RetryStrategy.EXPONENTIAL,
            backoff_multiplier=2.0,
            jitter_range=0.1,
            circuit_breaker_enabled=False,
            metrics_enabled=True
        )
        self._retry_handler = UnifiedRetryHandler("error_recovery", retry_config)
    
    async def attempt_recovery(
        self, 
        error: Exception, 
        context: ErrorContext,
        operation: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Attempt recovery via retries using UnifiedRetryHandler."""
        if not operation:
            return None
        
        # Update context with current retry count
        context.retry_count = getattr(context, 'retry_count', 0)
        
        # If we've exceeded retries, don't attempt
        if context.retry_count >= self.max_retries:
            logger.warning(f"Max retries ({self.max_retries}) exceeded, stopping recovery attempts")
            return None
        
        try:
            # Create wrapper function that includes kwargs
            async def operation_wrapper():
                return await operation(**kwargs)
            
            # Execute with unified retry handler
            result = await self._retry_handler.execute_with_retry_async(operation_wrapper)
            
            # Update context with total attempts
            context.retry_count = result.total_attempts
            
            if result.success:
                logger.info(f"Retry recovery succeeded after {result.total_attempts} attempts")
                return result.result
            else:
                logger.warning(f"Retry recovery failed after {result.total_attempts} attempts: {result.final_exception}")
                return None
                
        except Exception as retry_error:
            logger.warning(f"Retry recovery failed: {retry_error}")
            context.retry_count += 1
            return None


class FallbackRecoveryStrategy(RecoveryStrategy):
    """Fallback-based recovery strategy."""
    
    def __init__(self, fallback_operation: Callable):
        self.fallback_operation = fallback_operation
    
    async def attempt_recovery(
        self, 
        error: Exception, 
        context: ErrorContext,
        operation: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Attempt recovery via fallback operation."""
        try:
            logger.info(f"Attempting fallback recovery for {context.operation}")
            return await self.fallback_operation(**kwargs)
        except Exception as fallback_error:
            logger.error(f"Fallback recovery failed: {fallback_error}")
            return None


class UnifiedErrorHandler:
    """
    Unified Error Handler - Single Source of Truth for ALL Error Handling
    
    Consolidates all error handling patterns from across the service:
    - API error handling (FastAPI exceptions)
    - Agent error handling (LLM, execution, coordination)
    - Database error handling (SQLAlchemy, constraints)
    - WebSocket error handling (connections, messages)
    - Domain-specific error handling (corpus, synthetic data, etc.)
    """
    
    def __init__(self, max_history: int = 1000):
        """Initialize unified error handler."""
        self.error_history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self._error_metrics = self._init_error_metrics()
        self._recovery_strategies = self._init_recovery_strategies()
        self._status_mappings = self._init_status_mappings()
    
    def _init_error_metrics(self) -> Dict[str, Union[int, float]]:
        """Initialize error metrics tracking."""
        return {
            'total_errors': 0,
            'recovery_attempts': 0,
            'recovery_successes': 0,
            'fallback_uses': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'last_updated': time.time()
        }
    
    def _init_recovery_strategies(self) -> Dict[str, RecoveryStrategy]:
        """Initialize recovery strategies for different error types."""
        return {
            'retry': RetryRecoveryStrategy(),
            'database_retry': RetryRecoveryStrategy(max_retries=5, base_delay=0.5),
            'llm_retry': RetryRecoveryStrategy(max_retries=3, base_delay=2.0),
            'network_retry': RetryRecoveryStrategy(max_retries=4, base_delay=1.5),
        }
    
    def _init_status_mappings(self) -> Dict[Union[ErrorCode, str], int]:
        """Initialize HTTP status code mappings."""
        return {
            ErrorCode.VALIDATION_ERROR: 422,
            ErrorCode.AUTHENTICATION_FAILED: 401,
            ErrorCode.AUTHORIZATION_FAILED: 403,
            ErrorCode.RECORD_NOT_FOUND: 404,
            ErrorCode.RECORD_ALREADY_EXISTS: 409,
            ErrorCode.DATABASE_ERROR: 500,
            ErrorCode.SERVICE_UNAVAILABLE: 503,
            ErrorCode.AGENT_TIMEOUT: 408,
            ErrorCode.LLM_RATE_LIMIT_EXCEEDED: 429,
            # String mappings for backward compatibility
            'VALIDATION_ERROR': 422,
            'AUTH_FAILED': 401,
            'AUTH_UNAUTHORIZED': 403,
            'DB_RECORD_NOT_FOUND': 404,
            'DB_CONSTRAINT_VIOLATION': 409,
            'INTERNAL_ERROR': 500,
            'SERVICE_UNAVAILABLE': 503,
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        recovery_operation: Optional[Callable] = None,
        **kwargs
    ) -> Union[ErrorResponse, Any]:
        """
        Unified error handling entry point.
        
        Handles ANY type of error from ANY domain in the system.
        Returns appropriate response based on context (API response, agent result, etc.)
        """
        # Create context if not provided
        if context is None:
            context = self._create_default_context()
        
        # Classify and process the error
        error_info = self._classify_error(error, context)
        
        # Store error for metrics and history
        self._store_error(error_info)
        
        # Log error appropriately
        self._log_error(error_info)
        
        # Attempt recovery if operation provided
        recovery_result = await self._attempt_recovery(
            error, context, recovery_operation, **kwargs
        )
        
        # If recovery succeeded, return the result
        if recovery_result is not None:
            self._record_recovery_success()
            return recovery_result
        
        # Return standardized error response
        return self._create_error_response(error_info)
    
    def _create_default_context(self) -> ErrorContext:
        """Create default error context."""
        return ErrorContext(
            trace_id=str(uuid4()),
            operation="unknown",
            timestamp=datetime.now(timezone.utc)
        )
    
    def _classify_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """Classify error and determine handling strategy."""
        error_type = type(error).__name__
        
        # Determine category
        category = self._categorize_error(error)
        
        # Determine severity
        severity = self._determine_severity(error, category)
        
        # Determine if recoverable
        is_recoverable = self._is_recoverable_error(error)
        
        # Extract debug information for non-production environments
        debug_info = self._extract_debug_info(error)
        
        return {
            'error_id': str(uuid4()),
            'error': error,
            'error_type': error_type,
            'category': category,
            'severity': severity,
            'context': context,
            'is_recoverable': is_recoverable,
            'message': str(error),
            'technical_details': traceback.format_exc(),
            'debug_info': debug_info,
            'timestamp': datetime.now(timezone.utc)
        }
    
    def _extract_debug_info(self, error: Exception) -> Dict[str, Any]:
        """
        Extract debug information from exception for non-production environments.
        
        SECURITY: Only extracts debug info in development/test environments.
        Production environments get minimal information to prevent information disclosure.
        """
        env_manager = get_environment_manager()
        
        # Security check: Only extract debug info in non-production environments
        if env_manager.is_production():
            return {}
        
        debug_info = {}
        
        try:
            # Get current traceback
            tb = error.__traceback__
            if tb is None:
                # If no traceback attached, get current one
                tb = traceback.extract_tb(error.__traceback__)
                if not tb:
                    tb = traceback.extract_stack()
            
            # Extract stack frames
            stack_frames = []
            line_number = None
            source_file = None
            
            if tb:
                # Get traceback information
                if hasattr(tb, '__iter__'):
                    # tb is already a StackSummary or list
                    for frame in tb:
                        if hasattr(frame, 'filename'):
                            stack_frames.append({
                                'file': self._sanitize_file_path(frame.filename),
                                'line': frame.lineno,
                                'function': frame.name,
                                'code': frame.line
                            })
                        else:
                            # Handle tuple format
                            stack_frames.append({
                                'file': self._sanitize_file_path(frame[0]),
                                'line': frame[1],
                                'function': frame[2],
                                'code': frame[3]
                            })
                    
                    # Get the last frame for primary error location
                    if stack_frames:
                        last_frame = stack_frames[-1]
                        source_file = last_frame['file']
                        line_number = last_frame['line']
                else:
                    # tb is a traceback object - extract manually
                    current_tb = tb
                    while current_tb:
                        frame = current_tb.tb_frame
                        filename = frame.f_code.co_filename
                        line_no = current_tb.tb_lineno
                        func_name = frame.f_code.co_name
                        
                        # Get the source line
                        line_code = linecache.getline(filename, line_no).strip()
                        
                        stack_frames.append({
                            'file': self._sanitize_file_path(filename),
                            'line': line_no,
                            'function': func_name,
                            'code': line_code
                        })
                        
                        # Store the deepest frame info as primary location
                        source_file = self._sanitize_file_path(filename)
                        line_number = line_no
                        
                        current_tb = current_tb.tb_next
            
            # Build debug info
            debug_info.update({
                'line_number': line_number,
                'source_file': source_file,
                'stack_trace': [f"{frame['file']}:{frame['line']} in {frame['function']}" for frame in stack_frames],
                'stack_frames': stack_frames if not env_manager.is_staging() else stack_frames[-3:],  # Limit frames in staging
                'error_type': type(error).__name__,
                'error_module': type(error).__module__,
            })
            
            # Add additional context if available
            if hasattr(error, '__cause__') and error.__cause__:
                debug_info['caused_by'] = {
                    'type': type(error.__cause__).__name__,
                    'message': str(error.__cause__)
                }
            
            if hasattr(error, '__context__') and error.__context__:
                debug_info['context_error'] = {
                    'type': type(error.__context__).__name__,
                    'message': str(error.__context__)
                }
            
            # Add locals from the error frame (development only)
            if env_manager.is_development() and stack_frames:
                try:
                    # Get the frame where error occurred
                    current_tb = error.__traceback__
                    if current_tb:
                        while current_tb.tb_next:
                            current_tb = current_tb.tb_next
                        
                        frame_locals = current_tb.tb_frame.f_locals
                        # Filter out sensitive information and large objects
                        safe_locals = {}
                        for key, value in frame_locals.items():
                            if not key.startswith('_') and len(str(value)) < 200:
                                try:
                                    # Try to convert to string safely
                                    safe_locals[key] = str(value)
                                except:
                                    safe_locals[key] = f"<{type(value).__name__}>"
                        debug_info['local_variables'] = safe_locals
                except Exception:
                    # Don't fail debug extraction due to local variable inspection
                    pass
        
        except Exception as debug_error:
            # Don't let debug extraction fail the error handling
            logger.warning(f"Failed to extract debug info: {debug_error}")
            debug_info = {
                'debug_extraction_error': str(debug_error),
                'error_type': type(error).__name__
            }
        
        return debug_info
    
    def _sanitize_file_path(self, file_path: str) -> str:
        """
        Sanitize file paths for security.
        
        Removes absolute paths and sensitive directory information.
        """
        try:
            # Convert to relative path from project root
            if os.path.isabs(file_path):
                # Try to make relative to current working directory
                try:
                    cwd = os.getcwd()
                    if file_path.startswith(cwd):
                        return os.path.relpath(file_path, cwd)
                except:
                    pass
                
                # Fallback: just show filename and parent directory
                path_parts = file_path.split(os.sep)
                if len(path_parts) > 1:
                    return f"{path_parts[-2]}/{path_parts[-1]}"
                else:
                    return path_parts[-1]
            
            return file_path
        except Exception:
            # Fallback to just the filename
            return os.path.basename(file_path) if file_path else "unknown"
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize error based on type and characteristics."""
        error_type = type(error).__name__
        
        # Database errors
        if isinstance(error, SQLAlchemyError) or 'Database' in error_type:
            return ErrorCategory.DATABASE
        
        # Validation errors
        if isinstance(error, (ValidationError, ValueError)) or 'Validation' in error_type:
            return ErrorCategory.VALIDATION
        
        # Network/HTTP errors
        if isinstance(error, HTTPException) or 'HTTP' in error_type or 'Network' in error_type:
            return ErrorCategory.NETWORK
        
        # Agent/LLM errors
        if isinstance(error, AgentError) or 'Agent' in error_type or 'LLM' in error_type:
            return ErrorCategory.PROCESSING
        
        # WebSocket errors
        if 'WebSocket' in error_type or 'WS' in error_type:
            return ErrorCategory.WEBSOCKET
        
        # Timeout errors
        if 'Timeout' in error_type or isinstance(error, asyncio.TimeoutError):
            return ErrorCategory.TIMEOUT
        
        # Authentication/Security errors
        if 'Auth' in error_type or 'Token' in error_type or 'Security' in error_type:
            return ErrorCategory.USER  # Auth errors are user-facing
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on type and impact."""
        error_type = type(error).__name__
        
        # Critical errors that affect system stability
        if 'Critical' in error_type or 'OutOfMemory' in error_type:
            return ErrorSeverity.CRITICAL
        
        # High severity for data integrity and security
        if category in [ErrorCategory.SECURITY, ErrorCategory.DATABASE] and 'Constraint' in error_type:
            return ErrorSeverity.HIGH
        
        # Medium severity for business logic failures
        if category in [ErrorCategory.PROCESSING, ErrorCategory.VALIDATION]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for recoverable issues
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.NETWORK]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM  # Default
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if error is recoverable via retry or fallback."""
        error_type = type(error).__name__
        
        # Recoverable errors
        recoverable_patterns = [
            'Timeout', 'RateLimit', 'Connection', 'Network', 
            'ServiceUnavailable', 'TemporaryFailure'
        ]
        
        # Non-recoverable errors
        non_recoverable_patterns = [
            'Permission', 'Auth', 'Validation', 'NotFound',
            'Constraint', 'OutOfMemory', 'Critical'
        ]
        
        for pattern in non_recoverable_patterns:
            if pattern in error_type:
                return False
        
        for pattern in recoverable_patterns:
            if pattern in error_type:
                return True
        
        # Default to recoverable for unknown errors
        return True
    
    async def _attempt_recovery(
        self,
        error: Exception,
        context: ErrorContext,
        operation: Optional[Callable] = None,
        **kwargs
    ) -> Optional[Any]:
        """Attempt error recovery using appropriate strategy."""
        if not operation or not self._is_recoverable_error(error):
            return None
        
        # Select recovery strategy based on error type
        strategy = self._select_recovery_strategy(error)
        
        self._error_metrics['recovery_attempts'] += 1
        
        try:
            result = await strategy.attempt_recovery(error, context, operation, **kwargs)
            if result is not None:
                self._error_metrics['recovery_successes'] += 1
            return result
        except Exception as recovery_error:
            logger.error(f"Recovery failed: {recovery_error}")
            return None
    
    def _select_recovery_strategy(self, error: Exception) -> RecoveryStrategy:
        """Select appropriate recovery strategy for error type."""
        error_type = type(error).__name__
        
        if isinstance(error, SQLAlchemyError):
            return self._recovery_strategies['database_retry']
        elif 'LLM' in error_type or 'Agent' in error_type:
            return self._recovery_strategies['llm_retry']
        elif 'Network' in error_type or 'HTTP' in error_type:
            return self._recovery_strategies['network_retry']
        else:
            return self._recovery_strategies['retry']
    
    def _create_error_response(self, error_info: Dict[str, Any]) -> ErrorResponse:
        """Create standardized error response."""
        error = error_info['error']
        context = error_info['context']
        
        # Handle specific exception types
        if isinstance(error, NetraException):
            return self._handle_netra_exception(error, context)
        elif isinstance(error, ValidationError):
            return self._handle_validation_error(error, context)
        elif isinstance(error, SQLAlchemyError):
            return self._handle_database_error(error, context)
        elif isinstance(error, HTTPException):
            return self._handle_http_exception(error, context)
        else:
            return self._handle_generic_error(error, context)
    
    def _handle_netra_exception(self, error: NetraException, context: ErrorContext) -> ErrorResponse:
        """Handle custom Netra exceptions."""
        debug_info = self._extract_debug_info(error)
        
        return ErrorResponse(
            error_code=error.error_details.code.value if hasattr(error.error_details.code, 'value') else str(error.error_details.code),
            message=error.error_details.message,
            user_message=error.error_details.user_message,
            details=error.error_details.details,
            trace_id=context.trace_id,
            request_id=context.request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            line_number=debug_info.get('line_number'),
            source_file=debug_info.get('source_file'),
            stack_trace=debug_info.get('stack_trace'),
            debug_info=debug_info
        )
    
    def _handle_validation_error(self, error: ValidationError, context: ErrorContext) -> ErrorResponse:
        """Handle validation errors."""
        validation_errors = []
        if hasattr(error, 'errors') and callable(error.errors):
            for err in error.errors():
                field = " -> ".join(str(loc) for loc in err.get("loc", []))
                validation_errors.append({
                    "field": field,
                    "message": err.get("msg", "Validation error"),
                    "type": err.get("type", "value_error")
                })
        
        debug_info = self._extract_debug_info(error)
        
        return ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR.value,
            message="Validation failed",
            user_message="Please check your input and try again",
            details={"validation_errors": validation_errors},
            trace_id=context.trace_id,
            request_id=context.request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            line_number=debug_info.get('line_number'),
            source_file=debug_info.get('source_file'),
            stack_trace=debug_info.get('stack_trace'),
            debug_info=debug_info
        )
    
    def _handle_database_error(self, error: SQLAlchemyError, context: ErrorContext) -> ErrorResponse:
        """Handle database errors."""
        if isinstance(error, IntegrityError):
            error_code = ErrorCode.DATABASE_CONSTRAINT_VIOLATION
            message = "Database constraint violation"
            user_message = "The operation could not be completed due to data constraints"
        else:
            error_code = ErrorCode.DATABASE_ERROR
            message = "Database operation failed"
            user_message = "A database error occurred. Please try again"
        
        debug_info = self._extract_debug_info(error)
        
        return ErrorResponse(
            error_code=error_code.value,
            message=message,
            user_message=user_message,
            details={"error_type": type(error).__name__, "error": str(error)},
            trace_id=context.trace_id,
            request_id=context.request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            line_number=debug_info.get('line_number'),
            source_file=debug_info.get('source_file'),
            stack_trace=debug_info.get('stack_trace'),
            debug_info=debug_info
        )
    
    def _handle_http_exception(self, error: HTTPException, context: ErrorContext) -> ErrorResponse:
        """Handle HTTP exceptions."""
        error_code = self._map_http_status_to_error_code(error.status_code)
        debug_info = self._extract_debug_info(error)
        
        return ErrorResponse(
            error_code=error_code.value,
            message=error.detail or "HTTP error occurred",
            user_message=error.detail or "A server error occurred",
            details={"status_code": error.status_code},
            trace_id=context.trace_id,
            request_id=context.request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            line_number=debug_info.get('line_number'),
            source_file=debug_info.get('source_file'),
            stack_trace=debug_info.get('stack_trace'),
            debug_info=debug_info
        )
    
    def _handle_generic_error(self, error: Exception, context: ErrorContext) -> ErrorResponse:
        """Handle generic/unknown errors."""
        debug_info = self._extract_debug_info(error)
        
        return ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR.value,
            message="An internal server error occurred",
            user_message="Something went wrong. Please try again later",
            details={
                "error_type": type(error).__name__,
                "error": str(error),
                "operation": context.operation
            },
            trace_id=context.trace_id,
            request_id=context.request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            line_number=debug_info.get('line_number'),
            source_file=debug_info.get('source_file'),
            stack_trace=debug_info.get('stack_trace'),
            debug_info=debug_info
        )
    
    def _map_http_status_to_error_code(self, status_code: int) -> ErrorCode:
        """Map HTTP status codes to internal error codes."""
        mapping = {
            HTTP_401_UNAUTHORIZED: ErrorCode.AUTHENTICATION_FAILED,
            HTTP_403_FORBIDDEN: ErrorCode.AUTHORIZATION_FAILED,
            HTTP_404_NOT_FOUND: ErrorCode.RECORD_NOT_FOUND,
            HTTP_409_CONFLICT: ErrorCode.RECORD_ALREADY_EXISTS,
            HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
        }
        return mapping.get(status_code, ErrorCode.INTERNAL_ERROR)
    
    def get_http_status_code(self, error_code: Union[ErrorCode, str]) -> int:
        """Get HTTP status code for error code."""
        if isinstance(error_code, str):
            return self._status_mappings.get(error_code, 500)
        return self._status_mappings.get(error_code, 500)
    
    def _store_error(self, error_info: Dict[str, Any]) -> None:
        """Store error in history with metrics tracking."""
        self.error_history.append(error_info)
        self._update_metrics(error_info)
        self._manage_history_size()
    
    def _update_metrics(self, error_info: Dict[str, Any]) -> None:
        """Update error metrics."""
        self._error_metrics['total_errors'] += 1
        
        category = error_info['category'].value
        severity = error_info['severity'].value
        
        if category not in self._error_metrics['errors_by_category']:
            self._error_metrics['errors_by_category'][category] = 0
        self._error_metrics['errors_by_category'][category] += 1
        
        if severity not in self._error_metrics['errors_by_severity']:
            self._error_metrics['errors_by_severity'][severity] = 0
        self._error_metrics['errors_by_severity'][severity] += 1
        
        self._error_metrics['last_updated'] = time.time()
    
    def _manage_history_size(self) -> None:
        """Keep error history within size limits."""
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def _log_error(self, error_info: Dict[str, Any]) -> None:
        """Log error with appropriate severity level."""
        severity = error_info['severity']
        context = error_info['context']
        message = f"{context.operation}: {error_info['message']}"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(message, exc_info=error_info['error'])
        elif severity == ErrorSeverity.HIGH:
            logger.error(message, exc_info=error_info['error'])
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(message)
        else:
            logger.info(message)
    
    def _record_recovery_success(self) -> None:
        """Record successful recovery in metrics."""
        self._error_metrics['recovery_successes'] += 1
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        total_attempts = self._error_metrics['recovery_attempts']
        success_rate = (
            (self._error_metrics['recovery_successes'] / total_attempts * 100)
            if total_attempts > 0 else 0.0
        )
        
        return {
            **self._error_metrics,
            'success_rate': success_rate,
            'recent_errors': len(self._get_recent_errors()),
        }
    
    def _get_recent_errors(self) -> List[Dict[str, Any]]:
        """Get errors from the last hour."""
        cutoff_time = time.time() - 3600
        return [
            e for e in self.error_history 
            if e['timestamp'].timestamp() > cutoff_time
        ]


# =============================================================================
# DOMAIN-SPECIFIC CONVENIENCE INTERFACES
# =============================================================================

class APIErrorHandler:
    """Convenience interface for API error handling."""
    
    def __init__(self, unified_handler: UnifiedErrorHandler):
        self._handler = unified_handler
    
    async def handle_exception(
        self,
        exc: Exception,
        request: Optional[Request] = None,
        trace_id: Optional[str] = None
    ) -> JSONResponse:
        """Handle API exception and return JSONResponse."""
        context = ErrorContext(
            trace_id=trace_id or str(uuid4()),
            operation="api_request",
            request_id=self._extract_request_id(request),
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await self._handler.handle_error(exc, context)
        if isinstance(result, ErrorResponse):
            # Convert ErrorResponse to JSONResponse with proper HTTP status code
            status_code = self._handler.get_http_status_code(result.error_code)
            return JSONResponse(
                status_code=status_code,
                content=result.model_dump(),
                headers={"Content-Type": "application/json"}
            )
        return result
    
    def _extract_request_id(self, request: Optional[Request]) -> Optional[str]:
        """Extract request ID from request if available."""
        if request and hasattr(request.state, 'request_id'):
            return request.state.request_id
        return None
    
    def get_http_status_code(self, error_code: Union[ErrorCode, str]) -> int:
        """Get HTTP status code for error code."""
        return self._handler.get_http_status_code(error_code)


class AgentErrorHandler:
    """Convenience interface for agent error handling."""
    
    def __init__(self, unified_handler: UnifiedErrorHandler):
        self._handler = unified_handler
        # Create recovery manager for backward compatibility
        from netra_backend.app.core.error_recovery import ErrorRecoveryManager
        self.recovery_coordinator = ErrorRecoveryManager()
    
    @property
    def max_history(self) -> int:
        """Get max history from unified handler."""
        return self._handler.max_history
    
    @property  
    def error_history(self) -> List[Dict[str, Any]]:
        """Get error history from unified handler."""
        return self._handler.error_history
    
    @property
    def _error_metrics(self) -> Dict[str, Union[int, float]]:
        """Get error metrics from unified handler."""
        return self._handler._error_metrics
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for backward compatibility."""
        stats = self._handler.get_error_statistics()
        # Convert to expected format for backward compatibility
        return {
            'total_errors': stats.get('total_errors', 0),
            'error_categories': stats.get('errors_by_category', {}),
            'error_severities': stats.get('errors_by_severity', {}),
            **stats  # Include all other stats
        }
    
    def _convert_to_agent_error(self, error: Exception, context: ErrorContext) -> AgentError:
        """Convert exception to AgentError for backward compatibility."""
        return AgentError(
            message=str(error),
            severity=self._handler._determine_severity(error, self._handler._categorize_error(error)),
            context=context,
            original_error=error,
            recoverable=self._handler._is_recoverable_error(error)
        )
    
    def _log_error(self, error: Union[Exception, AgentError]) -> None:
        """Log error via unified handler."""
        if isinstance(error, AgentError):
            error_info = {
                'error': error,
                'severity': error.severity,
                'context': error.context,
                'message': error.message
            }
        else:
            error_info = self._handler._classify_error(error, self._handler._create_default_context())
        self._handler._log_error(error_info)
    
    def _store_error(self, error: Union[Exception, AgentError]) -> None:
        """Store error via unified handler."""
        if isinstance(error, AgentError):
            error_info = {
                'error': error,
                'severity': error.severity,
                'context': error.context,
                'category': ErrorCategory.PROCESSING,  # Default for agent errors
                'message': error.message,
                'timestamp': error.context.timestamp if error.context else datetime.now(timezone.utc),
                'is_recoverable': error.recoverable,
                'error_type': type(error).__name__
            }
        else:
            error_info = self._handler._classify_error(error, self._handler._create_default_context())
        self._handler._store_error(error_info)
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        fallback_operation: Optional[Callable] = None,
        **kwargs
    ) -> Union[AgentError, Any]:
        """Handle agent error with automatic recovery attempts."""
        if context is None:
            context = ErrorContext(
                trace_id=str(uuid4()),
                operation="agent_execution",
                agent_name=kwargs.get('agent_name', 'unknown'),
                operation_name=kwargs.get('operation_name', 'unknown'),
                run_id=kwargs.get('run_id'),
                timestamp=datetime.now(timezone.utc)
            )
        
        # For AgentError types, store them and return as-is for backward compatibility
        if isinstance(error, AgentError):
            # Set context if not already set
            if not error.context:
                error.context = context
            # Store the error
            self._store_error(error)
            return error
        
        # For other exception types, convert to AgentError for backward compatibility
        agent_error = self._convert_to_agent_error(error, context)
        self._store_error(agent_error)
        return agent_error
    
    async def handle_execution_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        fallback_operation: Optional[Callable] = None,
        **kwargs
    ) -> Union[AgentError, Any]:
        """Handle execution error - alias for handle_error for backward compatibility."""
        return await self.handle_error(error, context, fallback_operation, **kwargs)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the error handler."""
        return {
            'status': 'healthy',
            'total_errors': self._handler._error_metrics.get('total_errors', 0),
            'recovery_attempts': self._handler._error_metrics.get('recovery_attempts', 0),
            'recovery_successes': self._handler._error_metrics.get('recovery_successes', 0),
            'error_categories': self._handler._error_metrics.get('errors_by_category', {}),
            'error_severities': self._handler._error_metrics.get('errors_by_severity', {})
        }


class WebSocketErrorHandler:
    """Convenience interface for WebSocket error handling."""
    
    def __init__(self, unified_handler: UnifiedErrorHandler):
        self._handler = unified_handler
    
    async def handle_websocket_error(
        self,
        error: Exception,
        connection_id: Optional[str] = None,
        message_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Handle WebSocket error and return appropriate response."""
        context = ErrorContext(
            trace_id=str(uuid4()),
            operation="websocket_operation",
            session_id=connection_id,
            details={"message_type": message_type} if message_type else {},
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await self._handler.handle_error(error, context, **kwargs)
        
        # Convert to WebSocket-compatible format
        if isinstance(result, ErrorResponse):
            return {
                "type": "error",
                "error_code": result.error_code,
                "message": result.user_message,
                "trace_id": result.trace_id,
                "recoverable": self._handler._is_recoverable_error(error)
            }
        
        return result


# =============================================================================
# GLOBAL INSTANCES - SINGLE SOURCE OF TRUTH
# =============================================================================

# Single global unified error handler instance
_unified_error_handler = UnifiedErrorHandler()

# Domain-specific convenience handlers
api_error_handler = APIErrorHandler(_unified_error_handler)
agent_error_handler = AgentErrorHandler(_unified_error_handler)
websocket_error_handler = WebSocketErrorHandler(_unified_error_handler)

# Global aliases for backward compatibility
global_agent_error_handler = agent_error_handler
global_api_error_handler = api_error_handler


# =============================================================================
# CONVENIENCE FUNCTIONS - UNIFIED INTERFACE
# =============================================================================

async def handle_error(
    error: Exception,
    context: Optional[ErrorContext] = None,
    recovery_operation: Optional[Callable] = None,
    **kwargs
) -> Union[ErrorResponse, Any]:
    """Global convenience function for error handling."""
    return await _unified_error_handler.handle_error(error, context, recovery_operation, **kwargs)


def handle_exception(
    exc: Exception,
    request: Optional[Request] = None,
    trace_id: Optional[str] = None
) -> JSONResponse:
    """Synchronous convenience function for API exception handling."""
    import asyncio
    return asyncio.run(api_error_handler.handle_exception(exc, request, trace_id))


def get_http_status_code(error_code: Union[ErrorCode, str]) -> int:
    """Get HTTP status code for error code."""
    return _unified_error_handler.get_http_status_code(error_code)


def get_error_statistics() -> Dict[str, Any]:
    """Get unified error statistics."""
    return _unified_error_handler.get_error_statistics()


# =============================================================================
# DECORATOR FOR AGENT ERROR HANDLING
# =============================================================================

def handle_agent_error(
    agent_name: str, 
    operation_name: str, 
    max_retries: int = 3,
    retry_delay: float = 1.0,
    error_handler: Optional['AgentErrorHandler'] = None
):
    """
    Decorator for automatic agent error handling and recovery.
    
    Args:
        agent_name: Name of the agent for context
        operation_name: Name of the operation for context
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (with exponential backoff)
        error_handler: Custom error handler instance (defaults to global)
    
    Usage:
        @handle_agent_error(agent_name="DataAgent", operation_name="process_data")
        async def process_data():
            # Function that might fail
            pass
    """
    import functools
    import inspect
    
    def decorator(func: Callable) -> Callable:
        handler = error_handler or agent_error_handler
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = ErrorContext(
                    trace_id=str(uuid4()),
                    operation=operation_name,
                    agent_name=agent_name,
                    operation_name=operation_name,
                    timestamp=datetime.now(timezone.utc)
                )
                
                for attempt in range(max_retries + 1):
                    try:
                        context.retry_count = attempt
                        return await func(*args, **kwargs)
                    except Exception as e:
                        # Store error in handler
                        if isinstance(e, AgentError):
                            if not e.context:
                                e.context = context
                            handler._store_error(e)
                        else:
                            agent_error = handler._convert_to_agent_error(e, context)
                            handler._store_error(agent_error)
                        
                        # Check if should retry
                        if attempt < max_retries and handler._handler._is_recoverable_error(e):
                            delay = retry_delay * (2 ** attempt)  # Exponential backoff
                            await asyncio.sleep(delay)
                            continue
                        else:
                            # Re-raise the original exception after max retries or non-recoverable
                            raise e
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                context = ErrorContext(
                    trace_id=str(uuid4()),
                    operation=operation_name,
                    agent_name=agent_name,
                    operation_name=operation_name,
                    timestamp=datetime.now(timezone.utc)
                )
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Store error in handler
                    if isinstance(e, AgentError):
                        if not e.context:
                            e.context = context
                        handler._store_error(e)
                    else:
                        agent_error = handler._convert_to_agent_error(e, context)
                        handler._store_error(agent_error)
                    
                    # For sync functions, don't retry, just store and re-raise
                    raise e
            
            return sync_wrapper
    
    return decorator


# Backward compatibility alias - factory function to create AgentErrorHandler
def ErrorHandler():
    """Factory function to create AgentErrorHandler with default unified handler."""
    return AgentErrorHandler(_unified_error_handler)


# =============================================================================
# FASTAPI EXCEPTION HANDLERS
# =============================================================================

async def unified_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Unified exception handler for FastAPI."""
    return await api_error_handler.handle_exception(exc, request)


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Validation exception handler for FastAPI."""
    return await api_error_handler.handle_exception(exc, request)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP exception handler for FastAPI.
    
    SECURITY ENHANCEMENT: Converts 404/405 responses to 401 for API endpoints
    to prevent information disclosure through API surface enumeration.
    """
    # SECURITY FIX: Convert 404/405 to 401 for API endpoints when user is not authenticated
    if exc.status_code in [404, 405] and _is_api_endpoint(request.url.path):
        # Check if path is excluded from authentication requirements
        if not _is_excluded_from_auth(request.url.path):
            # Check if request has valid authentication
            if not _has_valid_auth(request):
                logger.warning(f"Converting HTTP {exc.status_code} to 401 for protected endpoint: {request.url.path}")
                return JSONResponse(
                    status_code=401,
                    content={"error": "authentication_failed", "message": "Authentication required"},
                    headers={"WWW-Authenticate": "Bearer"}
                )
    
    return await api_error_handler.handle_exception(exc, request)


def _is_api_endpoint(path: str) -> bool:
    """Check if path is an API endpoint that should be protected."""
    return path.startswith("/api/")


def _has_valid_auth(request: Request) -> bool:
    """Check if request has valid authentication."""
    # Check if request state indicates successful authentication
    # This will be set by the auth middleware if authentication was successful
    return getattr(request.state, 'authenticated', False)


def _is_excluded_from_auth(path: str) -> bool:
    """Check if path is excluded from authentication requirements.
    
    This should match the same exclusion logic used in FastAPIAuthMiddleware
    to ensure consistency between auth middleware and error handling.
    """
    # Default excluded paths that match FastAPIAuthMiddleware configuration
    excluded_paths = [
        "/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc",
        "/ws", "/websocket", "/ws/test", "/ws/config", "/ws/health", "/ws/stats",
        "/api/v1/auth"
    ]
    return any(excluded in path for excluded in excluded_paths)


async def netra_exception_handler(request: Request, exc: NetraException) -> JSONResponse:
    """Netra exception handler for FastAPI."""
    return await api_error_handler.handle_exception(exc, request)


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """General exception handler for FastAPI."""
    return await api_error_handler.handle_exception(exc, request)