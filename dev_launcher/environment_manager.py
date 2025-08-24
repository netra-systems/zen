"""
Environment variable management with conflict prevention and isolation support.

Centralized environment variable manager that prevents conflicts, tracks sources,
and supports isolation mode to avoid polluting os.environ in development/testing.
"""

import logging
import os
import threading
from typing import Dict, Optional, Set, Any

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Environment manager that prevents conflicts and provides isolation.
    
    Features:
    - Prevents duplicate setting of same variable by different components
    - Tracks what variables have been set and by whom
    - Supports isolation mode where nothing goes to os.environ
    - Thread-safe operations for concurrent access
    - Proper precedence handling (first setter wins unless explicit override)
    """
    
    def __init__(self, isolation_mode: bool = False):
        """Initialize the environment manager."""
        self.isolation_mode = isolation_mode
        self._variables: Dict[str, str] = {}
        self._sources: Dict[str, str] = {}  # Track who set each variable
        self._conflicts_prevented: Dict[str, Set[str]] = {}  # Track prevented conflicts
        self._operation_lock = threading.Lock()
        
        logger.debug(f"EnvironmentManager initialized with isolation_mode={isolation_mode}")
    
    def set_environment(self, key: str, value: str, source: str = "unknown", 
                       allow_override: bool = False) -> bool:
        """
        Set an environment variable with conflict prevention.
        
        Args:
            key: Environment variable name
            value: Environment variable value
            source: Source component setting the variable (for tracking)
            allow_override: Allow overriding existing value
            
        Returns:
            True if variable was set, False if conflict prevented
        """
        with self._operation_lock:
            # Check for conflicts
            if key in self._variables and not allow_override:
                existing_source = self._sources.get(key, "unknown")
                existing_value = self._variables[key]
                
                # Only prevent if values are different
                if existing_value != value:
                    # Track prevented conflict
                    if key not in self._conflicts_prevented:
                        self._conflicts_prevented[key] = set()
                    self._conflicts_prevented[key].add(source)
                    
                    logger.warning(f"Conflict prevented: {key} already set by {existing_source} "
                                 f"(value: {existing_value[:50]}...), {source} attempted to set "
                                 f"different value (value: {value[:50]}...)")
                    return False
                else:
                    # Same value, just update source tracking
                    logger.debug(f"Duplicate set ignored: {key}={value} by {source} "
                               f"(already set by {existing_source} with same value)")
                    return True
            
            # Set the variable
            self._variables[key] = value
            self._sources[key] = source
            
            # Set in os.environ if not in isolation mode
            if not self.isolation_mode:
                os.environ[key] = value
            
            logger.debug(f"Environment variable set: {key}={value[:50]}... by {source}")
            return True
    
    def get_environment(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Variable value or default
        """
        with self._operation_lock:
            if key in self._variables:
                return self._variables[key]
            
            # Fallback to os.environ if not in isolation mode
            if not self.isolation_mode:
                return os.environ.get(key, default)
            
            return default
    
    def has_variable(self, key: str) -> bool:
        """Check if a variable is managed by this manager."""
        with self._operation_lock:
            return key in self._variables or (not self.isolation_mode and key in os.environ)
    
    def get_variable_source(self, key: str) -> Optional[str]:
        """Get the source that set a variable."""
        with self._operation_lock:
            return self._sources.get(key)
    
    def get_conflicts_report(self) -> Dict[str, Any]:
        """Get a report of prevented conflicts."""
        with self._operation_lock:
            return {
                "conflicts_prevented": dict(self._conflicts_prevented),
                "total_conflicts": sum(len(sources) for sources in self._conflicts_prevented.values()),
                "variables_managed": len(self._variables),
                "isolation_mode": self.isolation_mode
            }
    
    def set_temporary_flag(self, key: str, value: str, source: str = "temporary") -> "TemporaryFlag":
        """
        Set a temporary flag that will be automatically cleaned up.
        
        Args:
            key: Environment variable name
            value: Environment variable value
            source: Source component setting the flag
            
        Returns:
            TemporaryFlag context manager for cleanup
        """
        return TemporaryFlag(self, key, value, source)
    
    def bulk_set_environment(self, variables: Dict[str, str], source: str = "bulk", 
                           allow_override: bool = False) -> Dict[str, bool]:
        """
        Set multiple environment variables at once.
        
        Args:
            variables: Dictionary of key-value pairs
            source: Source component setting the variables
            allow_override: Allow overriding existing values
            
        Returns:
            Dictionary mapping keys to success status
        """
        results = {}
        for key, value in variables.items():
            results[key] = self.set_environment(key, value, source, allow_override)
        return results
    
    def clear_variables_by_source(self, source: str):
        """Clear all variables set by a specific source."""
        with self._operation_lock:
            keys_to_remove = [key for key, var_source in self._sources.items() if var_source == source]
            
            for key in keys_to_remove:
                del self._variables[key]
                del self._sources[key]
                
                # Remove from os.environ if not in isolation mode
                if not self.isolation_mode and key in os.environ:
                    del os.environ[key]
            
            logger.debug(f"Cleared {len(keys_to_remove)} variables set by {source}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status information about managed variables."""
        with self._operation_lock:
            sources_count = {}
            for source in self._sources.values():
                sources_count[source] = sources_count.get(source, 0) + 1
            
            return {
                "isolation_mode": self.isolation_mode,
                "total_variables": len(self._variables),
                "sources": sources_count,
                "conflicts_prevented": len(self._conflicts_prevented),
                "variables_by_source": {
                    source: [key for key, var_source in self._sources.items() if var_source == source]
                    for source in set(self._sources.values())
                }
            }


class TemporaryFlag:
    """Context manager for temporary environment flags."""
    
    def __init__(self, manager: EnvironmentManager, key: str, value: str, source: str):
        self.manager = manager
        self.key = key
        self.value = value
        self.source = source
        self._was_set = False
    
    def __enter__(self):
        """Set the temporary flag."""
        self._was_set = self.manager.set_environment(self.key, self.value, self.source, allow_override=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up the temporary flag."""
        if self._was_set:
            with self.manager._operation_lock:
                if self.key in self.manager._variables:
                    del self.manager._variables[self.key]
                    del self.manager._sources[self.key]
                    
                    # Remove from os.environ if not in isolation mode
                    if not self.manager.isolation_mode and self.key in os.environ:
                        del os.environ[self.key]
                    
                    logger.debug(f"Cleaned up temporary flag: {self.key} set by {self.source}")


# Global instance accessor with singleton pattern
class _GlobalManagerSingleton:
    """Singleton wrapper for global environment manager."""
    
    _instance: Optional[EnvironmentManager] = None
    _lock = threading.Lock()
    
    @classmethod
    def get_manager(cls, isolation_mode: Optional[bool] = None) -> EnvironmentManager:
        """Get or create the global environment manager instance."""
        with cls._lock:
            if cls._instance is None:
                # Auto-detect isolation mode if not specified
                if isolation_mode is None:
                    environment = os.environ.get('ENVIRONMENT', 'development').lower()
                    isolation_mode = environment == 'development'
                
                cls._instance = EnvironmentManager(isolation_mode=isolation_mode)
                logger.debug(f"Created global EnvironmentManager with isolation_mode={isolation_mode}")
            
            return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset the global manager (for testing purposes)."""
        with cls._lock:
            cls._instance = None


def get_environment_manager(isolation_mode: Optional[bool] = None) -> EnvironmentManager:
    """
    Get the global environment manager instance.
    
    Args:
        isolation_mode: Enable isolation mode (auto-detected if None)
        
    Returns:
        EnvironmentManager instance
    """
    return _GlobalManagerSingleton.get_manager(isolation_mode)


def reset_global_manager():
    """Reset the global manager (for testing purposes)."""
    _GlobalManagerSingleton.reset()