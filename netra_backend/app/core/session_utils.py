"""
Session utility functions for safe session access across environments.

CRITICAL FIX for Issue #169: SessionMiddleware authentication infrastructure

This module provides centralized session availability detection and safe access
patterns to prevent crashes when SessionMiddleware is not installed or configured properly.

Business Value Justification (BVJ):
1. Segment: All customer tiers - prevents authentication flow failures
2. Business Goal: System stability and $500K+ ARR protection  
3. Value Impact: Eliminates SessionMiddleware crashes across deployment environments
4. Revenue Impact: Maintains authentication continuity for all customers
"""

import logging
from typing import Any, Dict, Optional
from fastapi import Request
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class SessionAvailabilityDetector:
    """Detects session middleware availability across different environments."""
    
    def __init__(self):
        self.env_manager = get_env()
        self._cached_availability = None
    
    def is_session_middleware_available(self, request: Request = None) -> bool:
        """Check if SessionMiddleware is properly installed and available.
        
        Args:
            request: Optional FastAPI request to test session access
            
        Returns:
            True if SessionMiddleware is available and functional
        """
        # Use cached result if available
        if self._cached_availability is not None:
            return self._cached_availability
        
        # Test session availability
        if request:
            availability = self._test_session_access(request)
        else:
            availability = self._detect_session_environment()
        
        # Cache the result for future calls
        self._cached_availability = availability
        return availability
    
    def _test_session_access(self, request: Request) -> bool:
        """Test actual session access on a request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if session can be accessed without errors
        """
        try:
            if not hasattr(request, 'session'):
                logger.debug("Request has no session attribute")
                return False
            
            # Try to access the session
            session = request.session
            # Test basic session operation
            test_key = '__session_test__'
            session[test_key] = 'test'
            result = session.get(test_key) == 'test'
            
            # Clean up test
            if test_key in session:
                del session[test_key]
            
            logger.debug(f"Session access test successful: {result}")
            return result
            
        except (AttributeError, RuntimeError, Exception) as e:
            logger.warning(f"Session access test failed: {e}")
            return False
    
    def _detect_session_environment(self) -> bool:
        """Detect session availability based on environment configuration.
        
        Returns:
            True if environment suggests session middleware should be available
        """
        environment = self.env_manager.get('ENVIRONMENT', '').lower()
        
        # Environments where session middleware is typically configured
        session_environments = ['staging', 'production', 'development']
        
        if environment in session_environments:
            secret_key = self.env_manager.get('SECRET_KEY')
            if secret_key and len(secret_key.strip()) >= 32:
                logger.debug(f"Environment {environment} has valid SECRET_KEY for sessions")
                return True
            else:
                logger.warning(f"Environment {environment} missing valid SECRET_KEY for sessions")
                return False
        
        logger.debug(f"Environment {environment} typically does not use session middleware")
        return False


class SafeSessionAccessor:
    """Provides safe session access patterns with automatic fallbacks."""
    
    def __init__(self):
        self.detector = SessionAvailabilityDetector()
    
    def get_session_data(self, request: Request, keys: list = None) -> Dict[str, Any]:
        """Safely extract session data with comprehensive fallback strategies.
        
        Args:
            request: FastAPI request object
            keys: Optional list of specific keys to extract
            
        Returns:
            Dictionary of session data or empty dict if unavailable
        """
        if keys is None:
            keys = ['session_id', 'user_id', 'user_email', 'user_role']
        
        session_data = {}
        
        # Strategy 1: Try session middleware
        if self.detector.is_session_middleware_available(request):
            session_data.update(self._extract_from_session(request, keys))
        
        # Strategy 2: Fallback to cookies
        if not session_data:
            session_data.update(self._extract_from_cookies(request, keys))
        
        # Strategy 3: Fallback to request state
        if not session_data:
            session_data.update(self._extract_from_request_state(request, keys))
        
        # Strategy 4: Fallback to headers (JWT, etc.)
        if not session_data:
            session_data.update(self._extract_from_headers(request, keys))
        
        return session_data
    
    def _extract_from_session(self, request: Request, keys: list) -> Dict[str, Any]:
        """Extract data from session middleware.
        
        Args:
            request: FastAPI request object
            keys: List of keys to extract
            
        Returns:
            Dictionary of extracted session data
        """
        data = {}
        try:
            if hasattr(request, 'session') and request.session:
                for key in keys:
                    value = request.session.get(key)
                    if value:
                        data[key] = value
                        
                logger.debug(f"Extracted from session: {list(data.keys())}")
        except Exception as e:
            logger.debug(f"Session extraction failed: {e}")
        
        return data
    
    def _extract_from_cookies(self, request: Request, keys: list) -> Dict[str, Any]:
        """Extract data from cookies.
        
        Args:
            request: FastAPI request object  
            keys: List of keys to extract
            
        Returns:
            Dictionary of extracted cookie data
        """
        data = {}
        try:
            for key in keys:
                cookie_value = request.cookies.get(key)
                if cookie_value:
                    data[key] = cookie_value
                    
            if data:
                logger.debug(f"Extracted from cookies: {list(data.keys())}")
        except Exception as e:
            logger.debug(f"Cookie extraction failed: {e}")
        
        return data
    
    def _extract_from_request_state(self, request: Request, keys: list) -> Dict[str, Any]:
        """Extract data from request state.
        
        Args:
            request: FastAPI request object
            keys: List of keys to extract
            
        Returns:
            Dictionary of extracted request state data
        """
        data = {}
        try:
            for key in keys:
                if hasattr(request.state, key):
                    value = getattr(request.state, key)
                    if value:
                        data[key] = value
                        
            if data:
                logger.debug(f"Extracted from request state: {list(data.keys())}")
        except Exception as e:
            logger.debug(f"Request state extraction failed: {e}")
        
        return data
    
    def _extract_from_headers(self, request: Request, keys: list) -> Dict[str, Any]:
        """Extract data from request headers (JWT, custom headers).
        
        Args:
            request: FastAPI request object
            keys: List of keys to extract
            
        Returns:
            Dictionary of extracted header data
        """
        data = {}
        try:
            # Check for common header-based session data
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                # Basic JWT extraction (in real app, would decode properly)
                data['auth_method'] = 'jwt'
                data['jwt_token'] = auth_header[7:]
            
            # Check for custom session headers
            session_header = request.headers.get('X-Session-ID')
            if session_header:
                data['session_id'] = session_header
                
            user_header = request.headers.get('X-User-ID')
            if user_header:
                data['user_id'] = user_header
                
            if data:
                logger.debug(f"Extracted from headers: {list(data.keys())}")
        except Exception as e:
            logger.debug(f"Header extraction failed: {e}")
        
        return data
    
    def safe_set_session_data(self, request: Request, key: str, value: Any) -> bool:
        """Safely set session data if session middleware is available.
        
        Args:
            request: FastAPI request object
            key: Session key to set
            value: Value to store
            
        Returns:
            True if data was successfully set, False otherwise
        """
        try:
            if self.detector.is_session_middleware_available(request):
                if hasattr(request, 'session') and request.session is not None:
                    request.session[key] = value
                    logger.debug(f"Successfully set session data: {key}")
                    return True
            
            logger.debug(f"Session middleware not available, cannot set: {key}")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to set session data {key}: {e}")
            return False


# Global instances for easy access
session_detector = SessionAvailabilityDetector()
safe_session = SafeSessionAccessor()


def is_session_available(request: Request = None) -> bool:
    """Check if session middleware is available.
    
    Args:
        request: Optional FastAPI request for testing
        
    Returns:
        True if session middleware is available
    """
    return session_detector.is_session_middleware_available(request)


def get_safe_session_data(request: Request, keys: list = None) -> Dict[str, Any]:
    """Get session data safely with fallbacks.
    
    Args:
        request: FastAPI request object
        keys: Optional list of keys to extract
        
    Returns:
        Dictionary of session data
    """
    return safe_session.get_session_data(request, keys)


def set_safe_session_data(request: Request, key: str, value: Any) -> bool:
    """Set session data safely if middleware available.
    
    Args:
        request: FastAPI request object
        key: Session key to set
        value: Value to store
        
    Returns:
        True if successfully set
    """
    return safe_session.safe_set_session_data(request, key, value)