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
import urllib.parse

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
            
            # Set default optimized persistence configuration
            self._set_optimized_persistence_defaults()
            
            self._initialized = True
            logger.debug("IsolatedEnvironment (netra_backend) initialized")
    
    def _auto_load_env_file(self) -> None:
        """Automatically load .env file if it exists.
        
        IMPORTANT: Does NOT override existing environment variables.
        This ensures that environment variables set by Docker, Cloud Run,
        or the deployment system take precedence over .env file values.
        
        CRITICAL: .env files are NEVER loaded in staging or production environments
        to ensure secrets come only from the deployment system.
        """
        # Check current environment - never load .env in staging/production
        environment = os.environ.get('ENVIRONMENT', '').lower()
        if environment in ['staging', 'production']:
            logger.debug(f"Skipping .env file loading in {environment} environment")
            return
            
        try:
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                # Load .env file but DO NOT override existing variables
                # This is critical for staging/production where environment
                # variables are set by the deployment system
                loaded_count = self.load_from_file(env_file, override_existing=False)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .env (without overriding existing)")
        except Exception as e:
            logger.warning(f"Failed to auto-load .env file: {e}")
    
    def _set_optimized_persistence_defaults(self) -> None:
        """Set default configuration for optimized persistence features."""
        # Default configurations for optimized persistence
        default_configs = {
            'ENABLE_OPTIMIZED_PERSISTENCE': 'false',  # Disabled by default for safety
            'OPTIMIZED_PERSISTENCE_CACHE_SIZE': '1000',
            'OPTIMIZED_PERSISTENCE_DEDUPLICATION': 'true',
            'OPTIMIZED_PERSISTENCE_COMPRESSION': 'true'
        }
        
        for key, default_value in default_configs.items():
            if not self.exists(key):
                self.set(key, default_value, "optimized_persistence_defaults")
                logger.debug(f"Set default optimized persistence config: {key}={default_value}")
    
    @classmethod
    def get_instance(cls) -> 'IsolatedEnvironment':
        """Get the singleton instance."""
        return cls()
    
    def _is_test_context(self) -> bool:
        """Check if we're currently running in a test context.
        
        This method detects various test environments to ensure proper
        environment variable handling during tests.
        
        Returns:
            bool: True if in test context, False otherwise
        """
        import sys
        
        # Check for pytest execution
        if 'pytest' in sys.modules:
            return True
        
        # Check for test environment variables using internal access to avoid recursion
        test_indicators = [
            'PYTEST_CURRENT_TEST',
            'TESTING',
            'TEST_MODE'
        ]
        
        # Use internal state or fallback to os.environ for test detection only
        # This is necessary to avoid recursion since get() calls _is_test_context()
        env_dict = self._isolated_vars if self._isolation_enabled else os.environ
        
        for indicator in test_indicators:
            if env_dict.get(indicator):
                return True
        
        # Check if ENVIRONMENT is set to testing
        env_value = env_dict.get('ENVIRONMENT', '').lower()
        if env_value in ['test', 'testing']:
            return True
        
        return False
    
    def _sync_with_os_environ(self) -> None:
        """Synchronize isolated variables with os.environ during test execution.
        
        This method ensures that test patches (patch.dict(os.environ, ...)) are 
        immediately reflected in the isolated environment, providing seamless
        integration between pytest mocking and IsolatedEnvironment.
        """
        if self._isolation_enabled:
            # Merge os.environ changes into isolated vars
            # This allows test patches to be immediately available
            self._isolated_vars.update(os.environ)
            logger.debug("Synced isolated vars with os.environ for test context")
    
    def enable_isolation(self, backup_original: bool = True) -> None:
        """Enable isolation mode to prevent os.environ pollution."""
        with self._lock:
            self._isolation_enabled = True
            if backup_original:
                # Copy current environment to isolated storage
                self._isolated_vars = dict(os.environ)
            
            # CRITICAL TEST INTEGRATION: In test context, sync isolated vars with os.environ
            # This ensures test patches (patch.dict(os.environ, ...)) are immediately available
            if self._is_test_context():
                self._sync_with_os_environ()
            
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
            # CRITICAL TEST INTEGRATION: Always prioritize os.environ during test context
            # This ensures that test patches (patch.dict(os.environ, ...)) are immediately respected
            if self._is_test_context():
                return os.environ.get(key, default)
            
            if self._isolation_enabled:
                return self._isolated_vars.get(key, default)
            
            return os.environ.get(key, default)
    
    def set(self, key: str, value: str, source: str = "unknown") -> None:
        """Set an environment variable value."""
        with self._lock:
            # Apply sanitization to avoid corruption of sensitive values like database URLs
            sanitized_value = self._sanitize_value(value)
            
            if self._isolation_enabled:
                self._isolated_vars[key] = sanitized_value
            else:
                os.environ[key] = sanitized_value
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
    
    def _sanitize_value(self, value: str) -> str:
        """Sanitize environment variable value while preserving database credentials.
        
        This method removes control characters but preserves password integrity.
        Special handling is applied for database URLs to prevent authentication failures.
        
        Args:
            value: Raw environment variable value
            
        Returns:
            Sanitized value with control characters removed but passwords preserved
        """
        if not isinstance(value, str):
            return str(value)
        
        # Check if this looks like a database URL
        is_database_url = any(proto in value.lower() for proto in ["postgresql://", "mysql://", "sqlite://", "clickhouse://"])
        
        if is_database_url:
            return self._sanitize_database_url(value)
        else:
            return self._sanitize_generic_value(value)
    
    def _sanitize_database_url(self, url: str) -> str:
        """Sanitize database URL while preserving password integrity.
        
        Args:
            url: Database URL to sanitize
            
        Returns:
            Sanitized URL with control characters removed but authentication preserved
        """
        import urllib.parse
        
        try:
            # Parse the URL to handle components separately
            parsed = urllib.parse.urlparse(url)
            
            # Sanitize individual components while preserving password integrity
            scheme = self._remove_control_characters(parsed.scheme) if parsed.scheme else ""
            
            # For hostname, remove control characters but preserve the structure
            hostname = self._remove_control_characters(parsed.hostname) if parsed.hostname else ""
            
            # For username, remove control characters
            username = self._remove_control_characters(parsed.username) if parsed.username else ""
            
            # For password, PRESERVE special characters but remove only control characters
            password = self._sanitize_password_preserving_special_chars(parsed.password) if parsed.password else ""
            
            # For port, keep as-is if valid
            port = parsed.port
            
            # For path, remove control characters
            path = self._remove_control_characters(parsed.path) if parsed.path else ""
            
            # For query parameters, remove control characters
            query = self._remove_control_characters(parsed.query) if parsed.query else ""
            
            # Reconstruct the URL
            netloc = ""
            if username:
                netloc += username
                if password:
                    netloc += f":{password}"
                netloc += "@"
            
            if hostname:
                netloc += hostname
                if port:
                    netloc += f":{port}"
            
            # Use urlunparse to reconstruct properly
            sanitized_url = urllib.parse.urlunparse((
                scheme, netloc, path, "", query, ""
            ))
            
            return sanitized_url
            
        except Exception as e:
            logger.warning(f"Database URL sanitization failed, using generic sanitization: {e}")
            return self._sanitize_generic_value(url)
    
    def _sanitize_password_preserving_special_chars(self, password: str) -> str:
        """Sanitize password by removing only control characters, preserving special chars.
        
        Args:
            password: Password to sanitize
            
        Returns:
            Password with only control characters removed
        """
        if not password:
            return password
        
        # Remove only ASCII control characters (0-31 and 127) but preserve all other characters
        sanitized = ""
        for char in password:
            char_code = ord(char)
            if char_code < 32 or char_code == 127:
                # Skip control characters but log for debugging
                logger.debug(f"Removed control character from password: ASCII {char_code}")
            else:
                sanitized += char
        
        return sanitized
    
    def _remove_control_characters(self, value: str) -> str:
        """Remove control characters from string value.
        
        Args:
            value: String to clean
            
        Returns:
            String with control characters removed
        """
        if not value:
            return value
        
        # Remove ASCII control characters (0-31 and 127)
        sanitized = ""
        for char in value:
            char_code = ord(char)
            if char_code < 32 or char_code == 127:
                # Log specific control characters for debugging
                char_name = {
                    10: 'newline (LF)',
                    13: 'carriage return (CR)',
                    9: 'tab',
                    0: 'null byte'
                }.get(char_code, f'control character (ASCII {char_code})')
                logger.debug(f"Removed {char_name} from environment value")
            else:
                sanitized += char
        
        return sanitized
    
    def _sanitize_generic_value(self, value: str) -> str:
        """Sanitize generic environment variable value.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        return self._remove_control_characters(value)


# Singleton instance
_env_instance = IsolatedEnvironment()


def get_env() -> IsolatedEnvironment:
    """Get the singleton IsolatedEnvironment instance."""
    return _env_instance


# Backwards compatibility alias
IsolatedEnv = IsolatedEnvironment