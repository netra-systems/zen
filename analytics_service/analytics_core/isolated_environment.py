"""
Analytics Service Isolated Environment Management

Service-specific environment management following the unified environment pattern.
Maintains complete microservice independence as per SPEC/independent_services.xml.

CRITICAL: This service MUST NOT import from other services (dev_launcher, netra_backend, auth_service)
"""
import os
import threading
from typing import Dict, Optional, Any

class IsolatedEnvironment:
    """
    Thread-safe singleton for analytics service environment management.
    
    Provides isolation and consistent environment variable access
    specifically for the analytics service.
    """
    
    _instance: Optional['IsolatedEnvironment'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'IsolatedEnvironment':
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the environment manager."""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
                
            self._env_cache: Dict[str, Any] = {}
            self._isolation_enabled = False
            self._overrides: Dict[str, str] = {}
            self._initialized = True
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value with caching.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        # Check overrides first
        if self._isolation_enabled and key in self._overrides:
            return self._overrides[key]
        
        # Check cache
        if key in self._env_cache:
            return self._env_cache[key]
        
        # Get from environment
        value = os.environ.get(key, default)
        
        # Cache the value
        self._env_cache[key] = value
        
        return value
    
    def set(self, key: str, value: str, category: Optional[str] = None) -> None:
        """
        Set environment variable value.
        
        Args:
            key: Environment variable name
            value: Value to set
            category: Optional category for organization (ignored but kept for compatibility)
        """
        if self._isolation_enabled:
            self._overrides[key] = value
        else:
            os.environ[key] = value
        
        # Update cache
        self._env_cache[key] = value
    
    def enable_isolation(self) -> None:
        """
        Enable isolation mode for testing.
        
        In isolation mode, set() operations don't affect the actual environment
        but are stored in overrides that take precedence in get() operations.
        """
        self._isolation_enabled = True
    
    def disable_isolation(self) -> None:
        """
        Disable isolation mode.
        
        Returns to normal operation where set() affects the actual environment.
        """
        self._isolation_enabled = False
        self._overrides.clear()
    
    def clear_cache(self) -> None:
        """Clear the environment cache."""
        with self._lock:
            self._env_cache.clear()
    
    def get_all_with_prefix(self, prefix: str) -> Dict[str, str]:
        """
        Get all environment variables with a specific prefix.
        
        Args:
            prefix: Prefix to filter by
            
        Returns:
            Dictionary of matching environment variables
        """
        result = {}
        
        # Check overrides if isolation is enabled
        if self._isolation_enabled:
            for key, value in self._overrides.items():
                if key.startswith(prefix):
                    result[key] = value
        
        # Check actual environment
        for key, value in os.environ.items():
            if key.startswith(prefix) and key not in result:
                result[key] = value
        
        return result
    
    def is_set(self, key: str) -> bool:
        """
        Check if an environment variable is set.
        
        Args:
            key: Environment variable name
            
        Returns:
            True if the variable is set, False otherwise
        """
        if self._isolation_enabled and key in self._overrides:
            return True
        return key in os.environ
    
    def unset(self, key: str) -> None:
        """
        Unset an environment variable.
        
        Args:
            key: Environment variable name to unset
        """
        if self._isolation_enabled:
            self._overrides.pop(key, None)
        else:
            os.environ.pop(key, None)
        
        # Remove from cache
        self._env_cache.pop(key, None)
    
    def get_environment_name(self) -> str:
        """
        Get the current environment name.
        
        Returns:
            Environment name (development, test, staging, production)
        """
        env = self.get("ENVIRONMENT", "development").lower()
        if env in ["development", "dev", "local"]:
            return "development"
        elif env in ["test", "testing"]:
            return "test"
        elif env == "staging":
            return "staging"
        elif env in ["production", "prod"]:
            return "production"
        return "development"
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.get_environment_name() == "production"
    
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.get_environment_name() == "staging"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.get_environment_name() == "development"
    
    def is_test(self) -> bool:
        """Check if running in test environment."""
        return self.get_environment_name() == "test"


# Global singleton instance
_env_manager: Optional[IsolatedEnvironment] = None


def get_env() -> IsolatedEnvironment:
    """
    Get the global IsolatedEnvironment instance for analytics service.
    
    Returns:
        IsolatedEnvironment singleton instance
    """
    global _env_manager
    if _env_manager is None:
        _env_manager = IsolatedEnvironment()
    return _env_manager