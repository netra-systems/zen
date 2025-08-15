"""Error recovery middleware for automatic error handling and recovery.

Provides middleware-level error interception with automatic recovery attempts,
circuit breaking, and comprehensive error logging with context.
"""

import asyncio
import json
import time
import traceback
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.error_recovery import (
    ErrorRecoveryManager,
    RecoveryExecutor,
    RecoveryContext,
    OperationType,
    recovery_manager,
    recovery_executor
)
from app.core.error_codes import ErrorSeverity
from app.core.exceptions_base import NetraException
from app.services.transaction_manager import transaction_manager
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorRecoveryMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic error recovery and circuit breaking."""
    
    def __init__(self, app):
        """Initialize error recovery middleware."""
        super().__init__(app)
        self.recovery_manager = recovery_manager
        self.recovery_executor = recovery_executor
        self.transaction_manager = transaction_manager
        
        # Request type to operation type mapping
        self.operation_mapping = {
            'POST': OperationType.DATABASE_WRITE,
            'PUT': OperationType.DATABASE_WRITE,
            'PATCH': OperationType.DATABASE_WRITE,
            'DELETE': OperationType.DATABASE_WRITE,
            'GET': OperationType.DATABASE_READ,
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error recovery capabilities."""
        operation_id, operation_type = self._create_operation_context(request)
        
        circuit_check_response = self._check_circuit_breaker(request)
        if circuit_check_response:
            return circuit_check_response
        
        return await self._execute_request_with_retry(
            request, call_next, operation_id, operation_type
        )
    
    def _determine_operation_type(self, request: Request) -> OperationType:
        """Determine operation type from request."""
        path = request.url.path.lower()
        method = request.method
        
        # Special cases for specific endpoints
        if '/websocket' in path or '/ws' in path:
            return OperationType.WEBSOCKET_SEND
        elif '/llm' in path or '/ai' in path or '/agent' in path:
            return OperationType.LLM_REQUEST
        elif '/api/external' in path:
            return OperationType.EXTERNAL_API
        elif '/files' in path or '/upload' in path:
            return OperationType.FILE_OPERATION
        elif '/cache' in path:
            return OperationType.CACHE_OPERATION
        
        # Default mapping based on HTTP method
        return self.operation_mapping.get(method, OperationType.DATABASE_READ)
    
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity from exception type."""
        if isinstance(error, NetraException):
            return error.error_details.severity
        
        # Map common exception types to severity
        severity_mapping = {
            'ValidationError': ErrorSeverity.HIGH,
            'PermissionError': ErrorSeverity.HIGH,
            'ConnectionError': ErrorSeverity.MEDIUM,
            'TimeoutError': ErrorSeverity.MEDIUM,
            'HTTPException': ErrorSeverity.MEDIUM,
            'ValueError': ErrorSeverity.HIGH,
            'TypeError': ErrorSeverity.HIGH,
            'KeyError': ErrorSeverity.MEDIUM,
            'FileNotFoundError': ErrorSeverity.MEDIUM,
            'MemoryError': ErrorSeverity.CRITICAL,
        }
        
        error_type = type(error).__name__
        return severity_mapping.get(error_type, ErrorSeverity.MEDIUM)
    
    def _extract_request_metadata(self, request: Request) -> Dict[str, Any]:
        """Extract metadata from request for recovery context."""
        metadata = {
            'method': request.method,
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'headers': dict(request.headers),
            'client_host': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'content_type': request.headers.get('content-type'),
        }
        
        # Add user context if available
        if hasattr(request.state, 'user') and request.state.user:
            metadata['user_id'] = str(request.state.user.id)
            metadata['user_email'] = getattr(request.state.user, 'email', None)
        
        # Add request ID if available
        if hasattr(request.state, 'request_id'):
            metadata['request_id'] = request.state.request_id
        
        return metadata
    
    def _create_operation_context(self, request: Request) -> tuple[str, OperationType]:
        """Create operation context for request processing."""
        operation_id = f"{request.method}:{request.url.path}:{int(time.time())}"
        operation_type = self._determine_operation_type(request)
        return operation_id, operation_type
    
    def _check_circuit_breaker(self, request: Request) -> Optional[JSONResponse]:
        """Check circuit breaker and return early response if needed."""
        circuit_breaker = self.recovery_manager.get_circuit_breaker(
            f"{request.method}:{request.url.path}"
        )
        
        if not circuit_breaker.should_allow_request():
            logger.warning(f"Circuit breaker open for {request.url.path}")
            return self._create_circuit_breaker_response()
        return None
    
    def _create_circuit_breaker_response(self) -> JSONResponse:
        """Create service unavailable response for circuit breaker."""
        return JSONResponse(
            status_code=503,
            content={
                "error": "SERVICE_UNAVAILABLE",
                "message": "Service temporarily unavailable",
                "retry_after": 60
            }
        )
    
    async def _execute_request_with_retry(
        self,
        request: Request,
        call_next: Callable,
        operation_id: str,
        operation_type: OperationType
    ) -> Response:
        """Execute request with retry logic and recovery."""
        circuit_breaker = self.recovery_manager.get_circuit_breaker(
            f"{request.method}:{request.url.path}"
        )
        max_attempts = 3
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                response = await self._handle_request_attempt(
                    request, call_next, operation_id, attempt, circuit_breaker
                )
                return response
            except Exception as error:
                last_error = error
                recovery_response = await self._handle_request_error(
                    request, error, operation_id, operation_type, 
                    attempt, max_attempts, circuit_breaker
                )
                if recovery_response:
                    return recovery_response
                if attempt >= max_attempts - 1:
                    break
        
        return await self._handle_final_failure(
            request, last_error, operation_id, circuit_breaker
        )
    
    async def _handle_request_attempt(
        self,
        request: Request,
        call_next: Callable,
        operation_id: str,
        attempt: int,
        circuit_breaker
    ) -> Response:
        """Handle a single request attempt."""
        request.state.operation_id = operation_id
        request.state.attempt = attempt
        
        response = await call_next(request)
        circuit_breaker.record_success()
        
        return self._add_success_headers(response, operation_id, attempt)
    
    def _add_success_headers(self, response: Response, operation_id: str, attempt: int) -> Response:
        """Add success headers to response."""
        response.headers["X-Operation-ID"] = operation_id
        response.headers["X-Attempt"] = str(attempt + 1)
        return response
    
    async def _handle_request_error(
        self,
        request: Request,
        error: Exception,
        operation_id: str,
        operation_type: OperationType,
        attempt: int,
        max_attempts: int,
        circuit_breaker
    ) -> Optional[JSONResponse]:
        """Handle request error and return recovery response if needed."""
        context = self._create_recovery_context(
            operation_id, operation_type, error, attempt, max_attempts, request
        )
        
        await self._log_error_with_context(error, context, request)
        
        return await self._attempt_error_recovery(
            request, context, attempt, max_attempts, circuit_breaker
        )
    
    def _create_recovery_context(
        self,
        operation_id: str,
        operation_type: OperationType,
        error: Exception,
        attempt: int,
        max_attempts: int,
        request: Request
    ) -> RecoveryContext:
        """Create recovery context for error handling."""
        return RecoveryContext(
            operation_id=operation_id,
            operation_type=operation_type,
            error=error,
            severity=self._determine_severity(error),
            retry_count=attempt,
            max_retries=max_attempts - 1,
            metadata=self._extract_request_metadata(request)
        )
    
    async def _attempt_error_recovery(
        self,
        request: Request,
        context: RecoveryContext,
        attempt: int,
        max_attempts: int,
        circuit_breaker
    ) -> Optional[JSONResponse]:
        """Attempt error recovery and return response if needed."""
        if attempt >= max_attempts - 1:
            return None
        
        recovery_result = await self.recovery_executor.attempt_recovery(context)
        
        if recovery_result.success:
            if recovery_result.action_taken.value == "compensate":
                return self._create_recovery_response(
                    request, context, recovery_result
                )
        else:
            circuit_breaker.record_failure()
        
        return None
    
    async def _handle_final_failure(
        self,
        request: Request,
        error: Exception,
        operation_id: str,
        circuit_breaker
    ) -> JSONResponse:
        """Handle final failure after all attempts exhausted."""
        circuit_breaker.record_failure()
        return await self._create_error_response(request, error, operation_id)
    
    async def _log_error_with_context(
        self,
        error: Exception,
        context: RecoveryContext,
        request: Request
    ) -> None:
        """Log error with comprehensive context."""
        error_data = {
            'operation_id': context.operation_id,
            'operation_type': context.operation_type.value,
            'severity': context.severity.value,
            'retry_count': context.retry_count,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'request_method': request.method,
            'request_path': request.url.path,
            'client_ip': request.client.host if request.client else None,
            'user_agent': request.headers.get('user-agent'),
            'elapsed_time_ms': context.elapsed_time.total_seconds() * 1000,
        }
        
        # Add user context
        if hasattr(request.state, 'user') and request.state.user:
            error_data['user_id'] = str(request.state.user.id)
        
        # Add stack trace for critical errors
        if context.severity == ErrorSeverity.CRITICAL:
            error_data['stack_trace'] = traceback.format_exc()
        
        # Log based on severity
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error in request processing", **error_data)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error("High severity error in request processing", **error_data)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error in request processing", **error_data)
        else:
            logger.info("Low severity error in request processing", **error_data)
    
    def _create_recovery_response(
        self,
        request: Request,
        context: RecoveryContext,
        recovery_result
    ) -> JSONResponse:
        """Create response after successful recovery."""
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Request completed with recovery",
                "recovery_info": {
                    "action_taken": recovery_result.action_taken.value,
                    "operation_id": context.operation_id,
                    "compensation_required": recovery_result.compensation_required,
                    "retry_count": context.retry_count
                }
            },
            headers={
                "X-Operation-ID": context.operation_id,
                "X-Recovery-Action": recovery_result.action_taken.value,
                "X-Retry-Count": str(context.retry_count)
            }
        )
    
    async def _create_error_response(
        self,
        request: Request,
        error: Exception,
        operation_id: str
    ) -> JSONResponse:
        """Create final error response after all recovery attempts failed."""
        # Determine appropriate HTTP status code
        status_code = 500
        if isinstance(error, HTTPException):
            status_code = error.status_code
        elif isinstance(error, (ValueError, TypeError)):
            status_code = 400
        elif isinstance(error, PermissionError):
            status_code = 403
        elif isinstance(error, FileNotFoundError):
            status_code = 404
        
        # Create error response
        error_response = {
            "error": True,
            "error_type": type(error).__name__,
            "message": str(error),
            "operation_id": operation_id,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
            "method": request.method
        }
        
        # Add request ID if available
        if hasattr(request.state, 'request_id'):
            error_response["request_id"] = request.state.request_id
        
        # Add trace ID if available
        if hasattr(request.state, 'trace_id'):
            error_response["trace_id"] = request.state.trace_id
        
        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={
                "X-Operation-ID": operation_id,
                "X-Error-Type": type(error).__name__,
                "X-Error-Recovery": "failed"
            }
        )


class TransactionMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic transaction management."""
    
    def __init__(self, app):
        """Initialize transaction middleware."""
        super().__init__(app)
        self.transaction_manager = transaction_manager
        
        # Paths that require transaction management
        self.transactional_paths = {
            '/api/corpus',
            '/api/synthetic-data',
            '/api/admin',
            '/api/generation'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with transaction management."""
        # Check if path requires transaction
        path = request.url.path
        needs_transaction = any(
            path.startswith(tx_path) for tx_path in self.transactional_paths
        )
        
        if not needs_transaction or request.method == 'GET':
            # Process without transaction
            return await call_next(request)
        
        # Process with transaction
        try:
            async with self.transaction_manager.transaction() as transaction_id:
                # Store transaction ID in request state
                request.state.transaction_id = transaction_id
                
                # Process request
                response = await call_next(request)
                
                # Add transaction header
                response.headers["X-Transaction-ID"] = transaction_id
                
                return response
                
        except Exception as error:
            logger.error(f"Transaction failed: {error}")
            raise error


class ErrorMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting error metrics."""
    
    def __init__(self, app):
        """Initialize error metrics middleware."""
        super().__init__(app)
        self.error_counts: Dict[str, int] = {}
        self.last_reset = time.time()
        self.reset_interval = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect error metrics from requests."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record response metrics
            duration = time.time() - start_time
            self._record_request_metric(request, response.status_code, duration)
            
            return response
            
        except Exception as error:
            # Record error metrics
            duration = time.time() - start_time
            self._record_error_metric(request, error, duration)
            raise error
    
    def _record_request_metric(
        self,
        request: Request,
        status_code: int,
        duration: float
    ) -> None:
        """Record request completion metrics."""
        path = request.url.path
        method = request.method
        
        # Reset counters if needed
        self._reset_counters_if_needed()
        
        # Record metrics
        metric_key = f"{method}:{path}:success"
        self.error_counts[metric_key] = self.error_counts.get(metric_key, 0) + 1
        
        # Log slow requests
        if duration > 5.0:
            logger.warning(
                f"Slow request: {method} {path}",
                duration_seconds=duration,
                status_code=status_code
            )
    
    def _record_error_metric(
        self,
        request: Request,
        error: Exception,
        duration: float
    ) -> None:
        """Record error metrics."""
        path = request.url.path
        method = request.method
        error_type = type(error).__name__
        
        # Reset counters if needed
        self._reset_counters_if_needed()
        
        # Record error metrics
        metric_key = f"{method}:{path}:error:{error_type}"
        self.error_counts[metric_key] = self.error_counts.get(metric_key, 0) + 1
        
        # Log error metric
        logger.info(
            f"Error metric recorded: {metric_key}",
            duration_seconds=duration,
            error_message=str(error)
        )
    
    def _reset_counters_if_needed(self) -> None:
        """Reset error counters periodically."""
        current_time = time.time()
        if current_time - self.last_reset > self.reset_interval:
            self.error_counts.clear()
            self.last_reset = current_time
            logger.debug("Error metrics counters reset")
    
    def get_error_metrics(self) -> Dict[str, Any]:
        """Get current error metrics."""
        return {
            'error_counts': self.error_counts.copy(),
            'last_reset': self.last_reset,
            'reset_interval': self.reset_interval
        }