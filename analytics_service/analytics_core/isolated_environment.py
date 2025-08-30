"""
Service-isolated environment variable management for analytics_service.

This module provides environment variable management specifically for analytics_service,
ensuring service independence from other microservices while maintaining 
a compatible interface.

Business Value: Platform/Internal - Service Independence
Maintains microservice independence while providing unified environment management patterns.

CRITICAL: This is analytics_service's own environment management - NEVER import from other services
"""
import os
import threading
from typing import Dict, Optional, Any, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IsolatedEnvironment:
    """
    Service-local environment variable manager for analytics_service.
    
    This class provides environment variable management without dependency on other services,
    ensuring complete microservice independence while maintaining 
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
            self._original_state: Optional[Dict[str, str]] = None
            
            # Automatically load .env file if it exists
            self._auto_load_env_file()
            
            self._initialized = True
            logger.debug("IsolatedEnvironment (analytics_service) initialized")
    
    def _expand_shell_commands(self, value: str) -> str:
        """
        Expand shell commands in environment variable values.
        
        This handles cases where SERVICE_ID contains shell commands like:
        - $(whoami)
        - $(hostname)
        - $(date +%Y%m%d-%H%M%S)
        - ${VARIABLE}
        
        Args:
            value: The environment variable value to expand
            
        Returns:
            Expanded value with shell commands executed
        """
        if not value or not isinstance(value, str):
            return value
        
        # Skip expansion during pytest to avoid side effects in tests
        import sys
        if 'pytest' in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("Skipping shell expansion during pytest")
            return value
        
        # Skip if explicitly disabled
        if os.environ.get("DISABLE_SHELL_EXPANSION", "false").lower() == "true":
            return value
        
        import re
        import subprocess
        
        # Pattern to match shell command substitutions: $(command) or `command`
        shell_patterns = [
            (r'\$\(([^)]+)\)', 'dollar_paren'),      # $(command)
            (r'`([^`]+)`', 'backtick'),              # `command`
        ]
        
        expanded_value = value
        
        for pattern, pattern_type in shell_patterns:
            matches = re.finditer(pattern, expanded_value)
            
            for match in matches:
                full_match = match.group(0)  # Full matched text like $(whoami)
                command = match.group(1)     # Just the command like whoami
                
                try:
                    # Execute the command safely
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=5,  # 5 second timeout
                        check=False  # Don't raise on non-zero exit
                    )
                    
                    if result.returncode == 0:
                        # Success - use the output (strip whitespace)
                        command_output = result.stdout.strip()
                        expanded_value = expanded_value.replace(full_match, command_output)
                        logger.debug(f"Expanded shell command '{command}' to '{command_output}'")
                    else:
                        # Command failed - log error but keep original
                        logger.warning(f"Shell command '{command}' failed with code {result.returncode}: {result.stderr}")
                        # Keep the original unexpanded form to indicate the issue
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Shell command '{command}' timed out after 5 seconds")
                    # Keep original unexpanded form
                except Exception as e:
                    logger.warning(f"Error executing shell command '{command}': {e}")
                    # Keep original unexpanded form
        
        # Also expand environment variable references like ${VARIABLE}
        # This is safer than full shell expansion
        env_var_pattern = r'\$\{([^}]+)\}'
        
        def replace_env_var(match):
            var_name = match.group(1)
            # Get the variable value, but don't recursively expand to avoid loops
            var_value = os.environ.get(var_name, '')
            if var_value:
                logger.debug(f"Expanded environment variable ${{{var_name}}} to '{var_value}'")
            return var_value
        
        expanded_value = re.sub(env_var_pattern, replace_env_var, expanded_value)
        
        # If the value changed, log the expansion
        if expanded_value != value:
            logger.info(f"Expanded environment value for shell commands")
        
        return expanded_value
    
    def _auto_load_env_file(self) -> None:
        """Automatically load .env or .secrets file if it exists."""
        import sys
        
        # Skip auto-loading during pytest to allow test configuration to take precedence
        if 'pytest' in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("Skipping env file auto-load during pytest execution")
            return
            
        # Skip auto-loading if explicitly disabled
        if os.environ.get("DISABLE_SECRETS_LOADING", "").lower() == "true":
            logger.debug("Skipping env file auto-load due to DISABLE_SECRETS_LOADING")
            return
            
        try:
            # Look for .env file first
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                loaded_count = self.load_from_file(env_file)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .env")
                return
            
            # If no .env file, look for .secrets file
            secrets_file = Path.cwd() / ".secrets"
            if secrets_file.exists():
                loaded_count = self.load_from_file(secrets_file)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .secrets")
                    
        except Exception as e:
            logger.warning(f"Failed to auto-load env file: {e}")
    
    @classmethod
    def get_instance(cls) -> 'IsolatedEnvironment':
        """Get the singleton instance."""
        return cls()
    
    def enable_isolation(self, backup_original: bool = True) -> None:
        """Enable isolation mode to prevent os.environ pollution."""
        with self._lock:
            self._isolation_enabled = True
            if backup_original:
                # Save original state for reset_to_original()
                self._original_state = dict(os.environ)
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
        """Get an environment variable value with shell command expansion."""
        with self._lock:
            if self._isolation_enabled:
                value = self._isolated_vars.get(key, default)
            else:
                value = os.environ.get(key, default)
            
            # Expand shell commands in the value if present
            return self._expand_shell_commands(value) if value else value
    
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

    def validate_analytics_configuration(self) -> dict:
        """Validate analytics service configuration.
        
        Returns:
            Dictionary with validation status and issues
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        environment = self.get("ENVIRONMENT", "").lower()
        
        # Only require explicit URLs in staging/production
        if environment in ["staging", "production"]:
            required_vars = ["CLICKHOUSE_ANALYTICS_URL", "REDIS_ANALYTICS_URL"]
            missing_vars = []
            
            for var in required_vars:
                value = self.get(var)
                if not value:
                    missing_vars.append(var)
            
            if missing_vars:
                validation_result["valid"] = False
                validation_result["issues"].append(f"Missing required analytics variables for {environment}: {missing_vars}")
        
        # Validate specific configuration values if they exist
        clickhouse_url = self.get("CLICKHOUSE_ANALYTICS_URL", "")
        redis_url = self.get("REDIS_ANALYTICS_URL", "")
        
        # ClickHouse URL validation
        if clickhouse_url and not clickhouse_url.startswith(("clickhouse://", "http://", "https://")):
            validation_result["valid"] = False
            validation_result["issues"].append("CLICKHOUSE_ANALYTICS_URL must start with clickhouse://, http://, or https://")
        
        # Redis URL validation
        if redis_url and not redis_url.startswith("redis://"):
            validation_result["valid"] = False
            validation_result["issues"].append("REDIS_ANALYTICS_URL must start with redis://")
        
        # Environment specific validations
        if environment in ["staging", "production"]:
            # Ensure URLs are not localhost in production if they are set
            if clickhouse_url and "localhost" in clickhouse_url:
                validation_result["valid"] = False
                validation_result["issues"].append("CLICKHOUSE_ANALYTICS_URL cannot be localhost in staging/production")
            
            if redis_url and "localhost" in redis_url:
                validation_result["valid"] = False
                validation_result["issues"].append("REDIS_ANALYTICS_URL cannot be localhost in staging/production")
        elif environment in ["development", "test"]:
            # In development/test, warn if explicit URLs are missing but don't fail
            if not clickhouse_url:
                validation_result["warnings"].append("CLICKHOUSE_ANALYTICS_URL not set - using development defaults")
            if not redis_url:
                validation_result["warnings"].append("REDIS_ANALYTICS_URL not set - using development defaults")
        
        return validation_result
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables."""
        with self._lock:
            if self._isolation_enabled:
                return self._isolated_vars.copy()
            return dict(os.environ)
    
    def get_all_variables(self) -> Dict[str, str]:
        """Get all environment variables - alias for get_all() for test compatibility."""
        return self.get_all()
    
    def reset(self) -> None:
        """Reset the environment to initial state."""
        with self._lock:
            self._isolated_vars.clear()
            self._protected_vars.clear()
            self._isolation_enabled = False
            logger.debug("Environment reset to initial state")
    
    def reset_to_original(self) -> None:
        """Reset the environment to the original state captured during enable_isolation."""
        with self._lock:
            if self._original_state is not None:
                if self._isolation_enabled:
                    # In isolation mode, restore to isolated vars
                    self._isolated_vars = self._original_state.copy()
                else:
                    # Not in isolation mode, restore to os.environ
                    # Clear all current environment variables that weren't in original
                    for key in list(os.environ.keys()):
                        if key not in self._original_state:
                            del os.environ[key]
                    # Restore original variables
                    for key, value in self._original_state.items():
                        os.environ[key] = value
                logger.debug("Environment reset to original state")
            else:
                logger.warning("No original state saved - cannot reset to original")


# Singleton instance getter for convenience
def get_env() -> IsolatedEnvironment:
    """Get the singleton IsolatedEnvironment instance."""
    return IsolatedEnvironment.get_instance()


# Export for compatibility
__all__ = ['IsolatedEnvironment', 'get_env']