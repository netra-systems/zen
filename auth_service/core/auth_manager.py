"""
AuthManager - Simplified Authentication Manager for Tests
Provides a simple interface to auth functionality for test modules
This is a facade over the main UnifiedAuthInterface for easier testing

SSOT Compliance: This is a test-specific wrapper, not a duplicate implementation
"""

import logging
from typing import Dict, Any, Optional
from auth_service.auth_core.unified_auth_interface import UnifiedAuthInterface

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Simplified AuthManager for test modules
    This provides a stable interface for tests that need basic auth functionality
    """
    
    def __init__(self):
        """Initialize auth manager with unified interface"""
        try:
            self._auth_interface = UnifiedAuthInterface()
            logger.info("AuthManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AuthManager: {e}")
            raise
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token and return payload if valid"""
        try:
            if not self._auth_interface:
                raise RuntimeError("Auth interface not initialized")
            
            # Use the unified interface to validate token
            payload = self._auth_interface.jwt_handler.decode_token(token)
            return {
                "valid": True,
                "payload": payload,
                "user_id": payload.get("sub", ""),
                "email": payload.get("email", "")
            }
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "payload": None
            }
    
    def create_test_user(self, email: str = "test@example.com", password: str = "test_password") -> Optional[str]:
        """Create a test user - for testing purposes only"""
        try:
            if not hasattr(self._auth_interface, 'auth_service'):
                logger.warning("Auth service not available for user creation")
                return None
            
            # This would typically create a user through the auth service
            # For now, return a mock user ID for tests
            test_user_id = f"test_user_{hash(email) % 10000}"
            logger.info(f"Created test user: {test_user_id}")
            return test_user_id
        except Exception as e:
            logger.error(f"Failed to create test user: {e}")
            return None
    
    def get_test_token(self, user_id: str = "test_user", email: str = "test@example.com") -> Optional[str]:
        """Generate a test JWT token - for testing purposes only"""
        try:
            if not self._auth_interface:
                raise RuntimeError("Auth interface not initialized")
            
            # Create test payload
            test_payload = {
                "sub": user_id,
                "email": email,
                "iat": 1234567890,
                "exp": 2234567890,  # Far future expiry
                "test": True  # Mark as test token
            }
            
            token = self._auth_interface.jwt_handler.encode_token(test_payload)
            logger.debug(f"Generated test token for user: {user_id}")
            return token
        except Exception as e:
            logger.error(f"Failed to generate test token: {e}")
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, '_auth_interface'):
                # Cleanup would happen here
                logger.debug("AuthManager cleanup completed")
        except Exception as e:
            logger.error(f"Error during AuthManager cleanup: {e}")
    
    def is_configured(self) -> bool:
        """Check if auth manager is properly configured"""
        try:
            return (
                hasattr(self, '_auth_interface') and 
                self._auth_interface is not None and
                hasattr(self._auth_interface, 'jwt_handler')
            )
        except Exception:
            return False