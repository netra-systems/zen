"""
Service-isolated environment variable management for netra_backend.

This module provides environment variable management specifically for netra_backend,
ensuring service independence from dev_launcher while maintaining a compatible interface.

Business Value: Platform/Internal - Service Independence
Maintains microservice independence while providing unified environment management patterns.
"""
import os
import threading
from typing import Dict, Optional, Any, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IsolatedEnvironment:
    """
    Service-local environment variable manager for netra_backend.
    
    This class provides environment variable management without dependency on dev_launcher,
    ensuring microservice independence while maintaining a compatible interface.
    
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
            logger.debug("IsolatedEnvironment (netra_backend) initialized")
    
    def _auto_load_env_file(self) -> None:
        """Automatically load .env file if it exists."""
        try:
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
    
    def set(self, key: str, value: str, source: str = "unknown") -> None:
        """Set an environment variable value."""
        with self._lock:
            if self._isolation_enabled:
                self._isolated_vars[key] = value
            else:
                os.environ[key] = value
            logger.debug(f"Set {key} from {source}")
    
    def delete(self, key: str) -> None:
        """Delete an environment variable."""
        with self._lock:
            if self._isolation_enabled:
                self._isolated_vars.pop(key, None)
            else:
                os.environ.pop(key, None)
    
    def exists(self, key: str) -> bool:
        """Check if an environment variable exists."""
        with self._lock:
            if self._isolation_enabled:
                return key in self._isolated_vars
            return key in os.environ
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables."""
        with self._lock:
            if self._isolation_enabled:
                return dict(self._isolated_vars)
            return dict(os.environ)
    
    def update(self, updates: Dict[str, str], source: str = "unknown") -> None:
        """Update multiple environment variables."""
        with self._lock:
            for key, value in updates.items():
                self.set(key, value, source)
    
    def load_from_file(self, filepath: Path, override_existing: bool = True) -> int:
        """
        Load environment variables from a .env file.
        
        Args:
            filepath: Path to the .env file
            override_existing: Whether to override existing variables
            
        Returns:
            Number of variables loaded
        """
        loaded_count = 0
        
        if not filepath.exists():
            logger.warning(f"Environment file not found: {filepath}")
            return 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value and value[0] == value[-1] and value[0] in ('"', "'"):
                            value = value[1:-1]
                        
                        # Only set if override_existing or doesn't exist
                        if override_existing or not self.exists(key):
                            self.set(key, value, str(filepath))
                            loaded_count += 1
            
            logger.debug(f"Loaded {loaded_count} variables from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading environment file {filepath}: {e}")
        
        return loaded_count
    
    def protect(self, key: str) -> None:
        """Mark a variable as protected (cannot be modified)."""
        with self._lock:
            self._protected_vars.add(key)
    
    def is_protected(self, key: str) -> bool:
        """Check if a variable is protected."""
        with self._lock:
            return key in self._protected_vars
    
    def is_isolated(self) -> bool:
        """Check if isolation mode is enabled."""
        return self._isolation_enabled
    
    def get_subprocess_env(self) -> Dict[str, str]:
        """Get environment dict suitable for subprocess launches."""
        with self._lock:
            if self._isolation_enabled:
                # Merge isolated vars with minimal required system vars
                env = dict(self._isolated_vars)
                
                # Ensure critical system variables are present
                system_vars = ['PATH', 'SYSTEMROOT', 'TEMP', 'TMP', 'USERPROFILE', 'HOME']
                for var in system_vars:
                    if var in os.environ and var not in env:
                        env[var] = os.environ[var]
                
                return env
            else:
                return dict(os.environ)
    
    def clear(self) -> None:
        """Clear all environment variables (only in isolation mode)."""
        if not self._isolation_enabled:
            raise RuntimeError("Cannot clear environment variables outside isolation mode")
        
        with self._lock:
            self._isolated_vars.clear()
            self._protected_vars.clear()


# Singleton instance
_env_instance = IsolatedEnvironment()


def get_env() -> IsolatedEnvironment:
    """Get the singleton IsolatedEnvironment instance."""
    return _env_instance


# Backwards compatibility alias
IsolatedEnv = IsolatedEnvironment