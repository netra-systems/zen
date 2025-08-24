"""
Service-isolated environment variable management for auth_service.

This module provides environment variable management specifically for auth_service,
ensuring service independence from dev_launcher and netra_backend while maintaining 
a compatible interface.

Business Value: Platform/Internal - Service Independence
Maintains microservice independence while providing unified environment management patterns.

CRITICAL: This is auth_service's own environment management - NEVER import from dev_launcher or netra_backend
"""
import os
import threading
from typing import Dict, Optional, Any, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IsolatedEnvironment:
    """
    Service-local environment variable manager for auth_service.
    
    This class provides environment variable management without dependency on dev_launcher
    or netra_backend, ensuring complete microservice independence while maintaining 
    a compatible interface.
    
    In production, it directly accesses os.environ.
    In development/testing, it can optionally use isolation mode to prevent environment pollution.
    """
    
    _instance: Optional['IsolatedEnvironment'] = None
    _lock = threading.RLock()
    
    def __new__(cls) -> 'IsolatedEnvironment':
        """Ensure singleton behavior with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the isolated environment manager."""
        # Prevent re-initialization of singleton
        if hasattr(self, '_initialized'):
            return
            
        with self._lock:
            if hasattr(self, '_initialized'):
                return
                
            # Internal state
            self._isolated_vars: Dict[str, str] = {}
            self._isolation_enabled = False
            self._protected_vars: Set[str] = set()
            
            # Automatically load .env file if it exists
            self._auto_load_env_file()
            
            self._initialized = True
            logger.debug("IsolatedEnvironment (auth_service) initialized")
    
    def _auto_load_env_file(self) -> None:
        """Automatically load .env file if it exists."""
        import sys
        
        # Skip auto-loading .env during pytest to allow test configuration to take precedence
        if 'pytest' in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("Skipping .env auto-load during pytest execution")
            return
            
        try:
            # Look for .env file in project root
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                loaded_count = self.load_from_file(env_file)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .env")
        except Exception as e:
            logger.warning(f"Failed to auto-load .env file: {e}")
    
    @classmethod
    def get_instance(cls) -> 'IsolatedEnvironment':
        """Get the singleton instance."""
        return cls()
    
    def enable_isolation(self, backup_original: bool = True) -> None:
        """Enable isolation mode to prevent os.environ pollution."""
        with self._lock:
            self._isolation_enabled = True
            if backup_original:
                # Copy current environment to isolated storage
                self._isolated_vars = dict(os.environ)
            logger.debug("Isolation mode enabled")
    
    def disable_isolation(self) -> None:
        """Disable isolation mode."""
        with self._lock:
            self._isolation_enabled = False
            self._isolated_vars.clear()
            logger.debug("Isolation mode disabled")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable value."""
        with self._lock:
            if self._isolation_enabled:
                return self._isolated_vars.get(key, default)
            return os.environ.get(key, default)
    
    def set(self, key: str, value: str, source: str = "runtime") -> None:
        """Set an environment variable value."""
        with self._lock:
            if self._isolation_enabled:
                self._isolated_vars[key] = value
            else:
                os.environ[key] = value
            
            if source != "silent":
                logger.debug(f"Set {key} from {source}")
    
    def update(self, vars: Dict[str, str], source: str = "batch") -> None:
        """Update multiple environment variables."""
        with self._lock:
            for key, value in vars.items():
                self.set(key, value, source="silent")
            
            if source != "silent" and vars:
                logger.debug(f"Updated {len(vars)} variables from {source}")
    
    def protect(self, key: str) -> None:
        """Mark a variable as protected (cannot be overwritten)."""
        with self._lock:
            self._protected_vars.add(key)
    
    def is_protected(self, key: str) -> bool:
        """Check if a variable is protected."""
        with self._lock:
            return key in self._protected_vars
    
    def load_from_file(self, filepath: Path) -> int:
        """Load environment variables from a file."""
        loaded = 0
        try:
            if not filepath.exists():
                logger.warning(f"Environment file not found: {filepath}")
                return 0
            
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        # Don't overwrite protected variables
                        if not self.is_protected(key):
                            self.set(key, value, source="silent")
                            loaded += 1
            
            if loaded > 0:
                logger.debug(f"Loaded {loaded} variables from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load environment from {filepath}: {e}")
        
        return loaded
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables."""
        with self._lock:
            if self._isolation_enabled:
                return self._isolated_vars.copy()
            return dict(os.environ)
    
    def reset(self) -> None:
        """Reset the environment to initial state."""
        with self._lock:
            self._isolated_vars.clear()
            self._protected_vars.clear()
            self._isolation_enabled = False
            logger.debug("Environment reset to initial state")


# Singleton instance getter for convenience
def get_env() -> IsolatedEnvironment:
    """Get the singleton IsolatedEnvironment instance."""
    return IsolatedEnvironment.get_instance()


# Export for compatibility
__all__ = ['IsolatedEnvironment', 'get_env']