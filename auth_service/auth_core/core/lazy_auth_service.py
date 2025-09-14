"""
Lazy Auth Service Initialization - Issue #926 Remediation
Thread-safe lazy initialization to prevent race conditions during service startup
"""
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Global instance and lock for thread-safe lazy initialization
_auth_service_instance: Optional['AuthService'] = None
_auth_service_lock = threading.RLock()  # RLock allows recursive locking by same thread

def get_auth_service() -> 'AuthService':
    """
    Thread-safe lazy initialization of AuthService instance.
    
    Uses double-checked locking pattern to ensure only one instance is created
    even in multi-threaded environments while maintaining performance.
    
    Returns:
        AuthService: Singleton instance of AuthService
        
    Raises:
        RuntimeError: If AuthService initialization fails
        ImportError: If AuthService class cannot be imported
    """
    global _auth_service_instance
    
    # First check without lock for performance (most common case)
    if _auth_service_instance is not None:
        return _auth_service_instance
    
    # Acquire lock for initialization
    with _auth_service_lock:
        # Double-check pattern: verify instance wasn't created while waiting for lock
        if _auth_service_instance is not None:
            return _auth_service_instance
        
        try:
            # Import AuthService only when needed to avoid circular imports
            from auth_service.auth_core.services.auth_service import AuthService
            
            logger.info("Initializing AuthService instance (lazy initialization)")
            _auth_service_instance = AuthService()
            logger.info("AuthService instance initialized successfully")
            
            return _auth_service_instance
            
        except ImportError as e:
            logger.error(f"Failed to import AuthService: {e}")
            raise ImportError(f"AuthService class not available: {e}") from e
        except Exception as e:
            logger.error(f"Failed to initialize AuthService: {e}")
            raise RuntimeError(f"AuthService initialization failed: {e}") from e

def reset_auth_service() -> None:
    """
    Reset the AuthService instance for testing purposes.
    
    WARNING: This should only be used in test environments.
    """
    global _auth_service_instance
    
    with _auth_service_lock:
        if _auth_service_instance is not None:
            logger.warning("Resetting AuthService instance (should only happen in tests)")
            _auth_service_instance = None

def is_auth_service_initialized() -> bool:
    """
    Check if AuthService has been initialized without triggering initialization.
    
    Returns:
        bool: True if instance exists, False otherwise
    """
    return _auth_service_instance is not None

def get_auth_service_safe() -> Optional['AuthService']:
    """
    Get AuthService instance if already initialized, return None otherwise.
    
    This method does not trigger initialization and is safe to call
    during shutdown or in error scenarios.
    
    Returns:
        Optional[AuthService]: Instance if initialized, None otherwise
    """
    return _auth_service_instance