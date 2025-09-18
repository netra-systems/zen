"""GCP Authentication Context Middleware for Error Reporting.

This middleware captures and preserves authentication context for GCP Error Reporting,
ensuring user context is properly tracked in error reports for enterprise customers.

Business Value Justification (BVJ):
1. Segment: Enterprise customers requiring compliance and user-specific error tracking
2. Business Goal: GDPR/SOX compliance and multi-user error isolation
3. Value Impact: Enables correlation of errors with specific authenticated users
4. Revenue Impact: Supports enterprise audit requirements and compliance features
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set
from contextvars import ContextVar
from datetime import datetime, timedelta
from enum import Enum

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from shared.types import StronglyTypedUserExecutionContext, UserID
from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
from netra_backend.app.auth_integration.auth import auth_client

# Context variables for async-safe context propagation
auth_user_context: ContextVar[Optional[StronglyTypedUserExecutionContext]] = ContextVar(
    'auth_user_context', default=None
)
auth_session_context: ContextVar[Dict[str, Any]] = ContextVar(
    'auth_session_context', default={}
)

logger = logging.getLogger(__name__)


class SessionAccessFailureReason(Enum):
    """Reasons for session access failures that need log rate limiting."""
    MIDDLEWARE_NOT_INSTALLED = "middleware_not_installed"
    RUNTIME_ERROR = "runtime_error"
    ATTRIBUTE_ERROR = "attribute_error"
    ASSERTION_ERROR = "assertion_error"


@dataclass
class SessionAccessLogMetrics:
    """Metrics for tracking session access log events."""
    total_attempts: int = 0
    total_failures: int = 0
    suppressed_logs: int = 0
    failures_by_reason: Dict[str, int] = field(default_factory=dict)
    last_log_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    window_start_time: Optional[datetime] = None


class SessionAccessRateLimiter:
    """Rate limiter for session access failure logs to prevent log spam.

    CRITICAL FIX for Issue #169: SessionMiddleware log spam

    This class implements time-windowed log suppression following SSOT patterns
    similar to WebSocketEmergencyThrottler to reduce log volume from 100+/hour
    to <12/hour (90% reduction target).

    Features:
    1. Time-windowed suppression (5-minute windows)
    2. Thread safety for concurrent requests
    3. Reason-based failure tracking
    4. Metrics for monitoring effectiveness
    5. Follows SSOT patterns from emergency throttling

    Business Value Justification (BVJ):
    - Segment: Platform/Infrastructure (ALL users benefit from reduced log noise)
    - Business Goal: Operational efficiency and log cost reduction
    - Value Impact: Eliminates log spam while preserving critical error visibility
    - Strategic Impact: Reduces operational noise and log storage costs
    """

    def __init__(self, log_window_minutes: int = 5, max_logs_per_window: int = 1):
        """Initialize session access rate limiter.

        Args:
            log_window_minutes: Time window for log suppression (default 5 minutes)
            max_logs_per_window: Maximum logs allowed per window (default 1)
        """
        self.log_window_seconds = log_window_minutes * 60
        self.max_logs_per_window = max_logs_per_window
        self.metrics = SessionAccessLogMetrics()
        self._lock = asyncio.Lock()

        # Track log events within current window
        self.current_window_logs = 0
        self.current_window_start: Optional[datetime] = None

        logger.debug(f"🛡️ SessionAccessRateLimiter initialized: {log_window_minutes}min windows, max {max_logs_per_window} logs/window")

    async def should_log_failure(self, failure_reason: SessionAccessFailureReason, error_message: str) -> bool:
        """Check if a session access failure should be logged.

        Args:
            failure_reason: Reason for the session access failure
            error_message: Error message that would be logged

        Returns:
            bool: True if the failure should be logged, False if suppressed
        """
        async with self._lock:
            now = datetime.now()

            # Update metrics
            self.metrics.total_attempts += 1
            self.metrics.total_failures += 1
            self.metrics.last_failure_time = now

            # Track failure by reason
            reason_key = failure_reason.value
            self.metrics.failures_by_reason[reason_key] = self.metrics.failures_by_reason.get(reason_key, 0) + 1

            # Initialize or reset window if needed
            if (self.current_window_start is None or
                (now - self.current_window_start).total_seconds() > self.log_window_seconds):

                self.current_window_start = now
                self.current_window_logs = 0
                self.metrics.window_start_time = now

            # Check if we can log in current window
            if self.current_window_logs < self.max_logs_per_window:
                self.current_window_logs += 1
                self.metrics.last_log_time = now

                logger.debug(f"📝 Session access failure logged ({self.current_window_logs}/{self.max_logs_per_window} in current window)")
                return True
            else:
                # Suppress this log
                self.metrics.suppressed_logs += 1

                # Log suppression notice at debug level (less frequent)
                if self.metrics.suppressed_logs % 10 == 1:  # Every 10th suppression
                    logger.debug(
                        f"🔇 Session access log suppressed (#{self.metrics.suppressed_logs}) - "
                        f"window limit reached ({self.max_logs_per_window} logs per {self.log_window_seconds/60:.0f}min)"
                    )

                return False

    async def record_success(self):
        """Record a successful session access."""
        async with self._lock:
            self.metrics.total_attempts += 1
            # Success doesn't count toward log limits

    def get_suppression_metrics(self) -> Dict[str, Any]:
        """Get current log suppression metrics."""
        return {
            "rate_limiting": {
                "window_seconds": self.log_window_seconds,
                "max_logs_per_window": self.max_logs_per_window,
                "current_window_logs": self.current_window_logs,
                "current_window_start": self.current_window_start.isoformat() if self.current_window_start else None
            },
            "metrics": {
                "total_attempts": self.metrics.total_attempts,
                "total_failures": self.metrics.total_failures,
                "suppressed_logs": self.metrics.suppressed_logs,
                "suppression_rate": (self.metrics.suppressed_logs / max(1, self.metrics.total_failures)) * 100,
                "failures_by_reason": dict(self.metrics.failures_by_reason),
                "last_log_time": self.metrics.last_log_time.isoformat() if self.metrics.last_log_time else None,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None
            }
        }

    def get_window_status(self) -> Dict[str, Any]:
        """Get current window status for monitoring."""
        now = datetime.now()
        window_remaining = 0

        if self.current_window_start:
            elapsed = (now - self.current_window_start).total_seconds()
            window_remaining = max(0, self.log_window_seconds - elapsed)

        return {
            "window_active": self.current_window_start is not None,
            "logs_used": self.current_window_logs,
            "logs_remaining": max(0, self.max_logs_per_window - self.current_window_logs),
            "window_remaining_seconds": window_remaining,
            "next_reset_time": (self.current_window_start + timedelta(seconds=self.log_window_seconds)).isoformat()
                              if self.current_window_start else None
        }


# Global rate limiter instance
_session_access_rate_limiter: Optional[SessionAccessRateLimiter] = None


def get_session_access_rate_limiter() -> SessionAccessRateLimiter:
    """Get the global session access rate limiter instance."""
    global _session_access_rate_limiter
    if _session_access_rate_limiter is None:
        _session_access_rate_limiter = SessionAccessRateLimiter()
    return _session_access_rate_limiter


class GCPAuthContextMiddleware(BaseHTTPMiddleware):
    """Middleware to capture and preserve authentication context for GCP error reporting.
    
    This middleware:
    1. Extracts JWT token and user authentication information
    2. Sets context variables for error reporting
    3. Preserves user isolation for multi-user error tracking
    4. Cleans up context after request completion
    """
    
    def __init__(self, app, enable_user_isolation: bool = True):
        super().__init__(app)
        self.enable_user_isolation = enable_user_isolation
    
    async def dispatch(self, request: Request, call_next):
        """Capture auth context and make available to error reporting."""
        
        # Extract authentication context
        auth_context = await self._extract_auth_context(request)
        user_context = await self._build_user_execution_context(auth_context)
        
        # Set context variables for error reporting
        self._set_auth_context_variables(user_context, auth_context)
        
        # Set GCP error reporter context
        self._set_gcp_error_context(user_context, auth_context, request)
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Ensure error has proper authentication context
            logger.error(
                f"Request failed with authentication context",
                extra={
                    'user_id': auth_context.get('user_id'),
                    'user_email': auth_context.get('user_email'),
                    'session_id': auth_context.get('session_id'),
                    'auth_method': auth_context.get('auth_method'),
                    'customer_tier': auth_context.get('customer_tier'),
                    'request_path': str(request.url.path),
                    'request_method': request.method
                },
                exc_info=e
            )
            raise
        finally:
            # Clean up context
            self._clear_auth_context()
    
    async def _extract_auth_context(self, request: Request) -> Dict[str, Any]:
        """Extract authentication context from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict containing authentication context
        """
        auth_context = {}
        
        try:
            # Extract JWT token from Authorization header
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                jwt_token = auth_header[7:]  # Remove 'Bearer ' prefix
                auth_context['jwt_token'] = jwt_token
                
                # Delegate JWT validation to auth service (SSOT compliance)
                # Issue #1195: Replace local JWT decoding with proper auth service delegation
                try:
                    jwt_validation_result = await auth_client.validate_token_jwt(jwt_token)
                    if jwt_validation_result and jwt_validation_result.get('valid'):
                        auth_context.update({
                            'auth_method': 'jwt',
                            'auth_timestamp': 'now',  # Would be actual timestamp from JWT
                            'permissions': jwt_validation_result.get('permissions', []),
                            'user_id': jwt_validation_result.get('user_id'),
                            'user_email': jwt_validation_result.get('email')
                        })
                        user_id = jwt_validation_result.get('user_id', 'unknown')
                        user_id_display = str(user_id)[:8] if user_id else 'unknown'
                        logger.debug(f"JWT validation successful via auth service for user {user_id_display}...")
                    else:
                        logger.warning("JWT validation failed via auth service - using fallback context")
                        auth_context.update({'auth_method': 'jwt_validation_failed'})
                except Exception as e:
                    logger.warning(f"Auth service JWT validation failed: {e} - using fallback context")
                    auth_context.update({'auth_method': 'jwt_validation_error'})
            
            # Extract from session if available - DEFENSIVE SESSION ACCESS WITH RATE LIMITING
            # CRITICAL FIX: Prevent SessionMiddleware crashes with try-catch and rate limited logging
            session_data = await self._safe_extract_session_data(request)
            auth_context.update(session_data)
            
            # Extract from request state (OAuth/auth service integration)
            if hasattr(request.state, 'user'):
                user = request.state.user
                auth_context.update({
                    'user_id': getattr(user, 'user_id', None),
                    'user_email': getattr(user, 'email', None),
                    'customer_tier': getattr(user, 'customer_tier', 'free')
                })
            
            # Default values if not found
            auth_context.setdefault('auth_method', 'unknown')
            auth_context.setdefault('customer_tier', 'free')
            auth_context.setdefault('user_id', 'anonymous')
            
        except Exception as e:
            logger.warning(f"Failed to extract auth context: {e}")
            # Return minimal context on failure
            auth_context = {
                'user_id': 'anonymous',
                'auth_method': 'extraction_failed',
                'customer_tier': 'free'
            }
        
        return auth_context
    
    async def _safe_extract_session_data(self, request: Request) -> Dict[str, Any]:
        """Safely extract session data with defensive programming and log rate limiting.

        CRITICAL FIX for Issue #169: SessionMiddleware authentication failures and log spam

        This method implements multiple fallback strategies to prevent crashes
        when SessionMiddleware is not installed or configured properly:
        1. Direct try-catch around session access (removes hasattr check)
        2. Improved RuntimeError handling for middleware order issues
        3. Fallback to request state and cookies if session unavailable
        4. RATE LIMITED LOGGING: Implements log suppression to reduce spam from 100+/hour to <12/hour

        Args:
            request: FastAPI request object

        Returns:
            Dict containing session data or empty dict if unavailable
        """
        session_data = {}
        rate_limiter = get_session_access_rate_limiter()

        try:
            # First line of defense: Try to access session directly
            # FIXED: Removed hasattr check that was causing RuntimeError issues
            session = request.session
            if session:
                session_data.update({
                    'session_id': session.get('session_id'),
                    'user_id': session.get('user_id'),
                    'user_email': session.get('user_email')
                })
                # Record successful session access
                await rate_limiter.record_success()
                logger.debug(f"Successfully extracted session data: {list(session_data.keys())}")
                return session_data
        except (AttributeError, RuntimeError, AssertionError) as e:
            # RATE LIMITED LOGGING: Use rate limiter to suppress log spam
            failure_reason = self._categorize_session_failure(e)
            error_message = f"Session access failed (middleware not installed?): {e}"

            # Only log if rate limiter allows it
            should_log = await rate_limiter.should_log_failure(failure_reason, error_message)
            if should_log:
                logger.warning(error_message)

        try:
            # Second line of defense: Fallback to cookie-based session extraction
            session_data.update(self._extract_session_from_cookies(request))

            # Third line of defense: Fallback to request state
            session_data.update(self._extract_session_from_request_state(request))

            if session_data:
                logger.info(f"Session data extracted via fallback methods: {list(session_data.keys())}")
            else:
                logger.debug("No session data available via any method")

        except Exception as e:
            logger.error(f"Unexpected error in session data extraction: {e}", exc_info=True)

        return session_data

    def _categorize_session_failure(self, exception: Exception) -> SessionAccessFailureReason:
        """Categorize session access failure for proper rate limiting.

        Args:
            exception: Exception that occurred during session access

        Returns:
            SessionAccessFailureReason: Categorized failure reason
        """
        if isinstance(exception, AttributeError):
            return SessionAccessFailureReason.ATTRIBUTE_ERROR
        elif isinstance(exception, RuntimeError):
            return SessionAccessFailureReason.RUNTIME_ERROR
        elif isinstance(exception, AssertionError):
            return SessionAccessFailureReason.ASSERTION_ERROR
        else:
            return SessionAccessFailureReason.MIDDLEWARE_NOT_INSTALLED
    
    def _extract_session_from_cookies(self, request: Request) -> Dict[str, Any]:
        """Extract session data from cookies as fallback.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict containing session data from cookies
        """
        cookie_data = {}
        try:
            # Look for session-related cookies
            session_cookie = request.cookies.get('session')
            user_id_cookie = request.cookies.get('user_id')
            email_cookie = request.cookies.get('user_email')
            
            if session_cookie:
                cookie_data['session_id'] = session_cookie
            if user_id_cookie:
                cookie_data['user_id'] = user_id_cookie
            if email_cookie:
                cookie_data['user_email'] = email_cookie
                
        except Exception as e:
            logger.debug(f"Cookie extraction failed: {e}")
        
        return cookie_data
    
    def _extract_session_from_request_state(self, request: Request) -> Dict[str, Any]:
        """Extract session data from request state as fallback.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict containing session data from request state
        """
        state_data = {}
        try:
            # Check for session data in request state
            if hasattr(request.state, 'session_id'):
                state_data['session_id'] = request.state.session_id
            if hasattr(request.state, 'user_id'):
                state_data['user_id'] = request.state.user_id
            if hasattr(request.state, 'user_email'):
                state_data['user_email'] = request.state.user_email
                
        except Exception as e:
            logger.debug(f"Request state extraction failed: {e}")
        
        return state_data
    
    
    async def _build_user_execution_context(
        self, 
        auth_context: Dict[str, Any]
    ) -> Optional[StronglyTypedUserExecutionContext]:
        """Build strongly typed user execution context.
        
        Args:
            auth_context: Authentication context dictionary
            
        Returns:
            StronglyTypedUserExecutionContext or None if user is anonymous
        """
        try:
            user_id_str = auth_context.get('user_id')
            if not user_id_str or user_id_str == 'anonymous':
                return None
            
            # Create strongly typed context (simplified implementation)
            # In real implementation, this would validate types properly
            return StronglyTypedUserExecutionContext(
                user_id=UserID(user_id_str),
                user_email=auth_context.get('user_email', ''),
                customer_tier=auth_context.get('customer_tier', 'free'),
                session_id=auth_context.get('session_id'),
                business_unit=auth_context.get('business_unit', 'platform'),
                compliance_requirements=auth_context.get('compliance_requirements', [])
            )
        except Exception as e:
            logger.warning(f"Failed to build user execution context: {e}")
            return None
    
    def _set_auth_context_variables(
        self, 
        user_context: Optional[StronglyTypedUserExecutionContext],
        auth_context: Dict[str, Any]
    ) -> None:
        """Set context variables for async-safe context propagation.
        
        Args:
            user_context: Strongly typed user context
            auth_context: Raw authentication context
        """
        auth_user_context.set(user_context)
        auth_session_context.set(auth_context)
    
    def _set_gcp_error_context(
        self,
        user_context: Optional[StronglyTypedUserExecutionContext],
        auth_context: Dict[str, Any],
        request: Request
    ) -> None:
        """Set GCP error reporter context.
        
        Args:
            user_context: Strongly typed user context
            auth_context: Authentication context
            request: FastAPI request
        """
        # Build HTTP context
        http_context = {
            'method': request.method,
            'url': str(request.url),
            'userAgent': request.headers.get('user-agent', ''),
            'referrer': request.headers.get('referer', ''),
            'remoteIp': request.client.host if request.client else None
        }
        
        # Build enhanced context for GCP error reporting
        gcp_context = {
            'user_id': auth_context.get('user_id'),
            'user_email': auth_context.get('user_email'),
            'customer_tier': auth_context.get('customer_tier'),
            'session_id': auth_context.get('session_id'),
            'auth_method': auth_context.get('auth_method'),
            'business_unit': auth_context.get('business_unit', 'platform'),
            'http_context': http_context
        }
        
        # Add enterprise context if available
        if user_context:
            gcp_context.update({
                'enterprise_customer': user_context.customer_tier in ['Enterprise', 'Enterprise_Plus'],
                'compliance_level': user_context.compliance_requirements,
                'user_isolation_id': f"user-{user_context.user_id.value}"
            })
        
        # Set context for GCP error reporter
        set_request_context(**gcp_context)
    
    def _clear_auth_context(self) -> None:
        """Clear authentication context after request completion."""
        auth_user_context.set(None)
        auth_session_context.set({})
        clear_request_context()


def get_current_user_context() -> Optional[StronglyTypedUserExecutionContext]:
    """Get current user context from context variables.
    
    Returns:
        Current user execution context or None if not available
    """
    return auth_user_context.get()


def get_current_auth_context() -> Dict[str, Any]:
    """Get current authentication context.
    
    Returns:
        Current authentication context dictionary
    """
    return auth_session_context.get({})


class MultiUserErrorContext:
    """Manages user-specific error context for enterprise isolation."""
    
    def create_user_error_context(
        self, 
        user_context: StronglyTypedUserExecutionContext
    ) -> Dict[str, Any]:
        """Create isolated error context for specific user.
        
        Args:
            user_context: User execution context
            
        Returns:
            User-specific error context for GCP reporting
        """
        return {
            "user_id": user_context.user_id.value,
            "user_email": user_context.user_email,
            "customer_tier": user_context.customer_tier,
            "business_unit": user_context.business_unit,
            "compliance_level": user_context.compliance_requirements,
            "session_id": user_context.session_id,
            "isolation_boundary": f"user-{user_context.user_id.value}",
            "gdpr_applicable": user_context.region in ["EU", "UK"] if hasattr(user_context, 'region') else False,
            "sox_required": "SOX" in user_context.compliance_requirements,
            "enterprise_context": True
        }


# Factory function for easy integration
def create_gcp_auth_context_middleware(enable_user_isolation: bool = True) -> GCPAuthContextMiddleware:
    """Create GCP authentication context middleware.

    Args:
        enable_user_isolation: Enable user isolation for enterprise customers

    Returns:
        Configured middleware instance
    """
    return GCPAuthContextMiddleware(None, enable_user_isolation)


# Public API for session access rate limiting monitoring
def get_session_access_suppression_metrics() -> Dict[str, Any]:
    """Get session access log suppression metrics for monitoring.

    Returns:
        Dict containing current rate limiting and suppression metrics
    """
    return get_session_access_rate_limiter().get_suppression_metrics()


def get_session_access_window_status() -> Dict[str, Any]:
    """Get current session access rate limiting window status.

    Returns:
        Dict containing current window status and remaining capacity
    """
    return get_session_access_rate_limiter().get_window_status()


# Export public interface
__all__ = [
    'GCPAuthContextMiddleware',
    'MultiUserErrorContext',
    'SessionAccessRateLimiter',
    'SessionAccessFailureReason',
    'get_current_user_context',
    'get_current_auth_context',
    'create_gcp_auth_context_middleware',
    'get_session_access_rate_limiter',
    'get_session_access_suppression_metrics',
    'get_session_access_window_status'
]