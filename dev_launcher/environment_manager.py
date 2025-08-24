"""
Environment Manager compatibility wrapper.

This module provides a EnvironmentManager class that wraps IsolatedEnvironment
to maintain backwards compatibility with existing tests and code.

Business Value: Platform/Internal - System Stability
Maintains compatibility while migrating to centralized environment management.
"""

import os
from contextlib import contextmanager
from typing import Dict, Optional, Set, Any, List, Tuple
import logging

from dev_launcher.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Compatibility wrapper for IsolatedEnvironment.
    
    Provides the EnvironmentManager interface that existing tests expect,
    while delegating to the centralized IsolatedEnvironment implementation.
    """
    
    def __init__(self, isolation_mode: bool = False):
        """Initialize EnvironmentManager with specified isolation mode."""
        self.env = get_env()
        self.isolation_mode = isolation_mode
        self._conflicts_prevented: Dict[str, List[str]] = {}
        self._total_conflicts = 0
        self._variable_sources: Dict[str, str] = {}
        
        # Configure isolation based on mode
        if isolation_mode and not self.env.is_isolation_enabled():
            self.env.enable_isolation()
        elif not isolation_mode and self.env.is_isolation_enabled():
            self.env.disable_isolation()
    
    # Delegate core methods directly to IsolatedEnvironment
    def set(self, key: str, value: str, source: str = "unknown", force: bool = False) -> bool:
        """Set an environment variable - direct delegation to IsolatedEnvironment."""
        # Track the original source if it's a new variable
        if key not in self._variable_sources:
            self._variable_sources[key] = source
        elif force:
            # Only update source if forcing override
            self._variable_sources[key] = source
            
        result = self.env.set(key, value, source, force)
        return result
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable - direct delegation to IsolatedEnvironment."""
        return self.env.get(key, default)
    
    def delete(self, key: str, source: str = "unknown") -> bool:
        """Delete an environment variable - direct delegation to IsolatedEnvironment."""
        result = self.env.delete(key, source)
        if result:
            self._variable_sources.pop(key, None)
        return result
    
    def protect_variable(self, key: str) -> None:
        """Protect a variable from modification."""
        self.env.protect_variable(key)
    
    def enable_isolation(self) -> None:
        """Enable isolation mode."""
        self.env.enable_isolation()
        self.isolation_mode = True
    
    def disable_isolation(self) -> None:
        """Disable isolation mode."""
        self.env.disable_isolation()
        self.isolation_mode = False
    
    def is_isolation_enabled(self) -> bool:
        """Check if isolation is enabled."""
        return self.env.is_isolation_enabled()
    
    def set_environment(self, key: str, value: str, source: str = "unknown", 
                        allow_override: bool = False) -> bool:
        """
        Set an environment variable with conflict prevention.
        
        Args:
            key: Environment variable name
            value: Environment variable value
            source: Source of the variable
            allow_override: Whether to allow overriding existing values
            
        Returns:
            True if set successfully, False if blocked
        """
        # Check for conflicts
        existing_value = self.env.get(key)
        if existing_value is not None and existing_value != value:
            existing_source = self._variable_sources.get(key, "unknown")
            
            # If not allowing override and value differs, track conflict
            if not allow_override:
                self._track_conflict(key, source, existing_source)
                return False
        
        # Set the variable
        result = self.env.set(key, value, source, force=allow_override)
        
        if result:
            self._variable_sources[key] = source
        
        return result
    
    def get_environment(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable value."""
        return self.env.get(key, default)
    
    def has_variable(self, key: str) -> bool:
        """Check if a variable exists."""
        return self.env.get(key) is not None
    
    def bulk_set_environment(self, variables: Dict[str, str], source: str = "unknown",
                            allow_override: bool = False) -> Dict[str, bool]:
        """
        Set multiple environment variables.
        
        Args:
            variables: Dictionary of variable name -> value
            source: Source of the variables
            allow_override: Whether to allow overriding existing values
            
        Returns:
            Dictionary of variable name -> whether it was set
        """
        results = {}
        for key, value in variables.items():
            results[key] = self.set_environment(key, value, source, allow_override)
        return results
    
    @contextmanager
    def set_temporary_flag(self, key: str, value: str, source: str = "unknown"):
        """
        Context manager for setting a temporary environment variable.
        
        The variable will be removed when exiting the context.
        """
        # Store original value if it exists
        original_value = self.env.get(key)
        
        # Set the temporary flag
        self.env.set(key, value, source)
        self._variable_sources[key] = source
        
        try:
            yield
        finally:
            # Restore original state
            if original_value is not None:
                self.env.set(key, original_value, source)
            else:
                self.env.delete(key, source)
                self._variable_sources.pop(key, None)
    
    def get_conflicts_report(self) -> Dict[str, Any]:
        """Get a report of prevented conflicts."""
        return {
            "total_conflicts": self._total_conflicts,
            "conflicts_prevented": dict(self._conflicts_prevented)
        }
    
    def get_variable_source(self, key: str) -> Optional[str]:
        """Get the source of a variable."""
        return self._variable_sources.get(key) or self.env.get_variable_source(key)
    
    def _track_conflict(self, key: str, attempted_source: str, existing_source: str):
        """Track a prevented conflict."""
        self._total_conflicts += 1
        
        if key not in self._conflicts_prevented:
            self._conflicts_prevented[key] = []
        
        conflict_info = f"{attempted_source} (blocked by {existing_source})"
        if conflict_info not in self._conflicts_prevented[key]:
            self._conflicts_prevented[key].append(conflict_info)
        
        logger.debug(f"Prevented conflict: {key} from {attempted_source} (existing: {existing_source})")
    
    def reset(self):
        """Reset the environment manager state."""
        self.env.reset_to_original()
        self._conflicts_prevented.clear()
        self._total_conflicts = 0
        self._variable_sources.clear()
    
    def get_subprocess_env(self, additional_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get environment variables for subprocess calls."""
        return self.env.get_subprocess_env(additional_vars)


# Global instance management
_global_manager: Optional[EnvironmentManager] = None


def get_environment_manager(isolation_mode: Optional[bool] = None) -> EnvironmentManager:
    """
    Get or create the global EnvironmentManager instance.
    
    Args:
        isolation_mode: If provided on first call, sets isolation mode
        
    Returns:
        The global EnvironmentManager instance
    """
    global _global_manager
    
    if _global_manager is None:
        # Auto-detect isolation mode based on environment
        if isolation_mode is None:
            env = get_env()
            environment = env.get("ENVIRONMENT", "development")
            isolation_mode = environment == "development"
        
        _global_manager = EnvironmentManager(isolation_mode=isolation_mode)
    
    return _global_manager


def reset_global_manager():
    """Reset the global manager instance (mainly for testing)."""
    global _global_manager
    if _global_manager:
        _global_manager.reset()
    _global_manager = None