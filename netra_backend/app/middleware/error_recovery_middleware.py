"""Error recovery middleware for automatic error handling and recovery.

Provides middleware-level error interception with automatic recovery attempts,
circuit breaking, and comprehensive error logging with context.
"""

import time
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.error_recovery import (
    RecoveryContext,
    OperationType,
    recovery_manager,
    recovery_executor
)
from app.services.transaction_manager import transaction_manager
from app.logging_config import central_logger
from netra_backend.app.error_recovery_helpers import (
    determine_operation_type,
    determine_severity,
    extract_request_metadata,
    build_error_data,
    enhance_error_data,
    log_by_severity,
    build_recovery_context
)
from netra_backend.app.error_response_builder import (
    create_circuit_breaker_response,
    create_recovery_response,
    create_error_response,
    add_success_headers
)

logger = central_logger.get_logger(__name__)


class ErrorRecoveryMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic error recovery and circuit breaking."""
    
    def __init__(self, app):
        """Initialize error recovery middleware."""
        super().__init__(app)
        self.recovery_manager = recovery_manager
        self.recovery_executor = recovery_executor
        self.transaction_manager = transaction_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error recovery capabilities."""
        operation_id, operation_type = self._create_operation_context(request)
        circuit_check_response = self._check_circuit_breaker(request)
        if circuit_check_response:
            return circuit_check_response
        return await self._execute_with_context(
            request, call_next, operation_id, operation_type
        )
    
    async def _execute_with_context(
        self,
        request: Request,
        call_next: Callable,
        operation_id: str,
        operation_type: OperationType
    ) -> Response:
        """Execute request with operation context."""
        return await self._execute_request_with_retry(
            request, call_next, operation_id, operation_type
        )
    
    def _create_operation_context(self, request: Request) -> tuple[str, OperationType]:
        """Create operation context for request processing."""
        operation_id = f"{request.method}:{request.url.path}:{int(time.time())}"
        operation_type = determine_operation_type(request)
        return operation_id, operation_type
    
    def _check_circuit_breaker(self, request: Request) -> Optional[JSONResponse]:
        """Check circuit breaker and return early response if needed."""
        circuit_breaker = self._get_circuit_breaker_for_path(request)
        if not circuit_breaker.should_allow_request():
            logger.warning(f"Circuit breaker open for {request.url.path}")
            return create_circuit_breaker_response()
        return None

    def _get_circuit_breaker_for_path(self, request: Request):
        """Get circuit breaker for request path."""
        path_key = f"{request.method}:{request.url.path}"
        return self.recovery_manager.get_circuit_breaker(path_key)
    
    async def _execute_request_with_retry(
        self,
        request: Request,
        call_next: Callable,
        operation_id: str,
        operation_type: OperationType
    ) -> Response:
        """Execute request with retry logic and recovery."""
        circuit_breaker = self._get_request_circuit_breaker(request)
        return await self._retry_request_loop(
            request, call_next, operation_id, operation_type, circuit_breaker
        )
    
    def _get_request_circuit_breaker(self, request: Request):
        """Get circuit breaker for request."""
        return self.recovery_manager.get_circuit_breaker(
            f"{request.method}:{request.url.path}"
        )
    
    async def _retry_request_loop(
        self, request: Request, call_next: Callable, operation_id: str, 
        operation_type: OperationType, circuit_breaker
    ) -> Response:
        """Execute retry loop for request."""
        max_attempts = 3
        last_error = await self._execute_all_retry_attempts(
            request, call_next, operation_id, operation_type, max_attempts, circuit_breaker
        )
        return await self._handle_final_failure(request, last_error, operation_id, circuit_breaker)
    
    async def _execute_all_retry_attempts(
        self, request: Request, call_next: Callable, operation_id: str,
        operation_type: OperationType, max_attempts: int, circuit_breaker
    ):
        """Execute all retry attempts and return last error or successful response."""
        for attempt in range(max_attempts):
            result = await self._try_single_attempt(
                request, call_next, operation_id, operation_type, 
                attempt, max_attempts, circuit_breaker
            )
            if isinstance(result, Response):
                return result
        return result
    
    async def _try_single_attempt(
        self, request: Request, call_next: Callable, operation_id: str, 
        operation_type: OperationType, attempt: int, max_attempts: int, circuit_breaker
    ):
        """Try a single request attempt."""
        try:
            return await self._handle_request_attempt(
                request, call_next, operation_id, attempt, circuit_breaker
            )
        except Exception as error:
            return await self._handle_attempt_error(
                request, error, operation_id, operation_type, 
                attempt, max_attempts, circuit_breaker
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
        return add_success_headers(response, operation_id, attempt)
    
    async def _handle_attempt_error(
        self, request: Request, error: Exception, operation_id: str, 
        operation_type: OperationType, attempt: int, max_attempts: int, circuit_breaker
    ):
        """Handle error during single attempt."""
        recovery_response = await self._handle_request_error(
            request, error, operation_id, operation_type, 
            attempt, max_attempts, circuit_breaker
        )
        return recovery_response if recovery_response else error
    
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
        return self._build_context_from_request(
            operation_id, operation_type, error, attempt, max_attempts, request
        )

    def _build_context_from_request(
        self, operation_id: str, operation_type: OperationType, error: Exception,
        attempt: int, max_attempts: int, request: Request
    ) -> RecoveryContext:
        """Build recovery context from request parameters."""
        metadata = extract_request_metadata(request)
        severity = determine_severity(error)
        return build_recovery_context(
            operation_id, operation_type, error, severity, attempt, max_attempts, metadata
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
        return self._process_recovery_result(
            request, context, recovery_result, circuit_breaker
        )
    
    def _process_recovery_result(
        self, request: Request, context: RecoveryContext, recovery_result, circuit_breaker
    ) -> Optional[JSONResponse]:
        """Process recovery result and return appropriate response."""
        if recovery_result.success:
            return self._handle_successful_recovery(request, context, recovery_result)
        circuit_breaker.record_failure("recovery_failure")
        return None
    
    def _handle_successful_recovery(
        self, request: Request, context: RecoveryContext, recovery_result
    ) -> Optional[JSONResponse]:
        """Handle successful recovery attempt."""
        if recovery_result.action_taken.value == "compensate":
            return create_recovery_response(request, context, recovery_result)
        return None
    
    async def _handle_final_failure(
        self,
        request: Request,
        error: Exception,
        operation_id: str,
        circuit_breaker
    ) -> JSONResponse:
        """Handle final failure after all attempts exhausted."""
        circuit_breaker.record_failure(type(error).__name__)
        return create_error_response(request, error, operation_id)
    
    async def _log_error_with_context(
        self,
        error: Exception,
        context: RecoveryContext,
        request: Request
    ) -> None:
        """Log error with comprehensive context."""
        error_data = build_error_data(error, context, request)
        enhance_error_data(error_data, request, context)
        log_by_severity(context.severity, error_data)