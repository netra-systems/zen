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

    def validate_staging_database_credentials(self) -> dict:
        """Validate database credentials specifically for staging environment.
        
        Returns:
            Dictionary with validation status and issues
        """
        validation_result = {
            "valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check environment is staging
        environment = self.get("ENVIRONMENT", "").lower()
        if environment != "staging":
            validation_result["warnings"].append(f"Not in staging environment (current: {environment})")
            return validation_result
        
        # Check required database variables
        required_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
        missing_vars = []
        
        for var in required_vars:
            value = self.get(var)
            if not value:
                missing_vars.append(var)
        
        if missing_vars:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Missing required staging database variables: {missing_vars}")
        
        # Validate specific credential values for staging
        postgres_host = self.get("POSTGRES_HOST", "")
        postgres_user = self.get("POSTGRES_USER", "")
        postgres_password = self.get("POSTGRES_PASSWORD", "")
        
        # Host validation for staging
        if postgres_host == "localhost":
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_HOST cannot be 'localhost' in staging - should be Cloud SQL connection")
        
        # User validation for staging - check for problematic patterns
        if postgres_user == "user_pr-4":
            validation_result["valid"] = False
            validation_result["issues"].append("Invalid POSTGRES_USER 'user_pr-4' - this will cause authentication failures")
        elif postgres_user.startswith("user_pr-"):
            validation_result["valid"] = False
            validation_result["issues"].append(f"Invalid POSTGRES_USER pattern '{postgres_user}' - appears to be misconfigured")
        elif not postgres_user:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_USER is not set")
        elif postgres_user != "postgres":
            validation_result["warnings"].append(f"POSTGRES_USER is '{postgres_user}' - verify this is correct for staging")
        
        # Password validation for staging
        if not postgres_password:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is not set")
        elif len(postgres_password) < 8:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is too short (< 8 characters) for staging")
        elif postgres_password in ["password", "123456", "admin", "test", "wrong_password"]:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is using insecure default - must be secure for staging")
        elif postgres_password.isdigit() and len(postgres_password) < 12:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is only numbers and too short - needs complexity")
        
        # Check for development credentials in staging
        if "dev" in postgres_password.lower():
            validation_result["warnings"].append("POSTGRES_PASSWORD contains 'dev' - verify this is not development password")
        
        return validation_result
    
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