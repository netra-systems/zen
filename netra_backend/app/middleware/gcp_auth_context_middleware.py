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
from typing import Any, Dict, Optional
from contextvars import ContextVar

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from shared.types import StronglyTypedUserExecutionContext, UserID
from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context

# Context variables for async-safe context propagation
auth_user_context: ContextVar[Optional[StronglyTypedUserExecutionContext]] = ContextVar(
    'auth_user_context', default=None
)
auth_session_context: ContextVar[Dict[str, Any]] = ContextVar(
    'auth_session_context', default={}
)

logger = logging.getLogger(__name__)


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
                
                # Extract user information from JWT (simplified - in real implementation
                # this would decode and validate the JWT)
                auth_context.update(await self._decode_jwt_context(jwt_token))
            
            # Extract from session if available - DEFENSIVE SESSION ACCESS
            # CRITICAL FIX: Prevent SessionMiddleware crashes with try-catch and hasattr checks
            session_data = self._safe_extract_session_data(request)
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
    
    def _safe_extract_session_data(self, request: Request) -> Dict[str, Any]:
        """Safely extract session data with defensive programming.
        
        CRITICAL FIX for Issue #169: SessionMiddleware authentication failures
        
        This method implements multiple fallback strategies to prevent crashes
        when SessionMiddleware is not installed or configured properly:
        1. Direct try-catch around session access (removes hasattr check)
        2. Improved RuntimeError handling for middleware order issues  
        3. Fallback to request state and cookies if session unavailable
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict containing session data or empty dict if unavailable
        """
        session_data = {}
        
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
                logger.debug(f"Successfully extracted session data: {list(session_data.keys())}")
                return session_data
        except (AttributeError, RuntimeError, AssertionError) as e:
            # Session middleware not installed or session access failed
            logger.warning(f"Session access failed (middleware not installed?): {e}")
        
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
            logger.error(f"Unexpected error in session data extraction: {e}", exc_info=e)
        
        return session_data
    
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
    
    async def _decode_jwt_context(self, jwt_token: str) -> Dict[str, Any]:
        """Decode JWT token to extract user context.
        
        Args:
            jwt_token: JWT token string
            
        Returns:
            Dict containing user context from JWT
        """
        try:
            # In a real implementation, this would decode and validate the JWT
            # For now, return placeholder context
            return {
                'auth_method': 'jwt',
                'auth_timestamp': 'now',  # Would be actual timestamp
                'permissions': []  # Would be extracted from JWT
            }
        except Exception as e:
            logger.warning(f"Failed to decode JWT context: {e}")
            return {'auth_method': 'jwt_decode_failed'}
    
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