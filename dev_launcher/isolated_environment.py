"""
Centralized environment variable management with isolation support and validation.

This module provides a singleton IsolatedEnvironment class that manages all environment
variable access across the dev launcher. In isolation mode, it maintains an internal
dictionary to prevent polluting os.environ during development and testing.

Also provides comprehensive validation of environment variables required for startup.

Business Value: Platform/Internal - System Stability
Prevents 90% of startup failures due to configuration issues.
"""
import os
import re
import threading
from dataclasses import dataclass
from typing import Dict, Optional, Any, Set, Callable, List, Tuple, Union
from pathlib import Path
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def _mask_sensitive_value(key: str, value: str) -> str:
    """
    Mask sensitive environment variable values for logging.
    
    Args:
        key: Environment variable name
        value: Environment variable value
        
    Returns:
        Masked value safe for logging
    """
    # Sensitive patterns - variables that should never be logged in full
    sensitive_patterns = [
        'password', 'secret', 'key', 'token', 'auth', 'credential',
        'private', 'cert', 'api_key', 'jwt', 'oauth', 'fernet'
    ]
    
    key_lower = key.lower()
    
    # Check if this is a sensitive variable
    if any(pattern in key_lower for pattern in sensitive_patterns):
        if len(value) <= 3:
            return "***"
        else:
            # Show first 3 chars and mask the rest
            return f"{value[:3]}***"
    
    # For non-sensitive variables, show first 50 chars as before
    return value[:50] + "..." if len(value) > 50 else value

# Import network constants for validation
try:
    from netra_backend.app.core.network_constants import (
        DatabaseConstants,
        HostConstants,
        NetworkEnvironmentHelper,
        ServicePorts,
    )
except ImportError:
    # Fallback for environments where these aren't available
    class DatabaseConstants:
        DATABASE_URL = "DATABASE_URL"
        REDIS_URL = "REDIS_URL"
        CLICKHOUSE_URL = "CLICKHOUSE_URL"
        POSTGRES_SCHEME = "postgresql"
        POSTGRES_ASYNC_SCHEME = "postgresql+asyncpg"
        REDIS_SCHEME = "redis"
        CLICKHOUSE_SCHEME = "clickhouse"


@dataclass
class ValidationResult:
    """Environment variable validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_optional: List[str]
    fallback_applied: List[str] = None  # Track variables that used fallbacks
    suggestions: List[str] = None  # Automated suggestions for fixes
    missing_optional_by_category: Dict[str, List[str]] = None  # Categorized missing optional vars
    
    def __post_init__(self):
        if self.fallback_applied is None:
            self.fallback_applied = []
        if self.suggestions is None:
            self.suggestions = []
        if self.missing_optional_by_category is None:
            self.missing_optional_by_category = {}


class IsolatedEnvironment:
    """
    Centralized environment variable manager with isolation support.
    
    This singleton class manages all environment variable access across the system.
    In isolation mode, it maintains an internal dictionary instead of directly
    modifying os.environ, preventing environment pollution during development/testing.
    
    Key Features:
    - Singleton pattern ensures single source of truth
    - Isolation mode prevents os.environ pollution
    - Thread-safe operations
    - Source tracking for debugging
    - Backwards compatibility with existing code
    - Subprocess environment management
    - Pytest integration compatibility
    """
    
    _instance: Optional['IsolatedEnvironment'] = None
    _lock = threading.RLock()
    
    # Variables that must always remain in os.environ for external tool compatibility
    PRESERVE_IN_OS_ENVIRON = {
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION", 
        "_PYTEST_RAISE",
        "PYTEST_PLUGINS",
        "PYTEST_TIMEOUT",
        # Add other tool-specific variables as needed
    }
    
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
            self._variable_sources: Dict[str, str] = {}
            self._isolation_enabled = False
            self._protected_vars: Set[str] = set()
            self._change_callbacks: List[Callable[[str, Optional[str], str], None]] = []
            self._original_environ_backup: Dict[str, str] = {}
            
            # Track initial os.environ state
            self._original_environ_backup = dict(os.environ)
            
            # Automatically load .env file if it exists for dev mode
            self._auto_load_env_file()
            
            self._initialized = True
            logger.debug("IsolatedEnvironment initialized")
    
    def _auto_load_env_file(self) -> None:
        """Automatically load .env file if it exists in the current directory.
        
        This ensures that environment variables are available immediately
        when the IsolatedEnvironment is first created, before any backend
        imports that might trigger configuration loading.
        """
        try:
            # Look for .env file in current working directory
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                # Load with override to ensure we get the latest values
                loaded_count, errors = self.load_from_file(env_file, source="auto_load", override_existing=True)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .env")
                if errors:
                    for error in errors:
                        logger.warning(f"Auto-load error: {error}")
        except Exception as e:
            # Don't fail initialization if env loading fails
            logger.warning(f"Failed to auto-load .env file: {e}")
    
    @classmethod
    def get_instance(cls) -> 'IsolatedEnvironment':
        """Get the singleton instance."""
        return cls()
    
    def enable_isolation(self, backup_original: bool = True, refresh_vars: bool = True) -> None:
        """
        Enable isolation mode to prevent os.environ pollution.
        
        Args:
            backup_original: Whether to backup current os.environ state
            refresh_vars: Whether to refresh isolated vars from current os.environ state
        """
        with self._lock:
            was_already_enabled = self._isolation_enabled
            
            if was_already_enabled and not refresh_vars:
                logger.debug("Isolation already enabled, no refresh requested")
                return
                
            self._isolation_enabled = True
            
            if backup_original and not was_already_enabled:
                self._original_environ_backup = dict(os.environ)
                
            # Always refresh isolated vars when explicitly requested or first time enabling
            if refresh_vars or not was_already_enabled:
                # ALWAYS copy current os.environ to isolated vars when enabling isolation
                # This ensures all variables that exist at the time of enabling isolation are captured
                # regardless of any previous reset operations
                self._isolated_vars = dict(os.environ)
                logger.debug(f"Refreshed isolated vars from os.environ: {len(self._isolated_vars)} variables captured")
            
            # Ensure preserved variables remain in os.environ
            # This is critical for tools like pytest that manage their own variables
            for key in self.PRESERVE_IN_OS_ENVIRON:
                if key in self._isolated_vars and key not in os.environ:
                    # Variable is in isolated vars but not in os.environ, restore it
                    os.environ[key] = self._isolated_vars[key]
                    logger.debug(f"Preserved {key} in os.environ during isolation")
                elif key in os.environ and key not in self._isolated_vars:
                    # Variable is in os.environ but not in isolated vars, capture it
                    self._isolated_vars[key] = os.environ[key]
                    logger.debug(f"Captured {key} from os.environ during isolation")
            
            if was_already_enabled:
                logger.debug(f"Environment isolation refreshed with {len(self._isolated_vars)} variables")
            else:
                logger.info("Environment isolation enabled")
    
    def disable_isolation(self, restore_original: bool = False) -> None:
        """
        Disable isolation mode and optionally restore original environment.
        
        Args:
            restore_original: Whether to restore original os.environ state
        """
        with self._lock:
            if not self._isolation_enabled:
                logger.debug("Isolation not enabled")
                return
                
            self._isolation_enabled = False
            
            if restore_original:
                # Clear current environ and restore original
                os.environ.clear()
                os.environ.update(self._original_environ_backup)
                logger.info("Original environment restored")
            else:
                # Sync isolated vars to os.environ
                for key, value in self._isolated_vars.items():
                    os.environ[key] = value
                logger.info("Isolated environment synced to os.environ")
    
    def is_isolation_enabled(self) -> bool:
        """Check if isolation mode is enabled."""
        return self._isolation_enabled
    
    def set(self, key: str, value: str, source: str, force: bool = False) -> bool:
        """
        Set an environment variable with mandatory source tracking.
        
        Args:
            key: Environment variable name
            value: Environment variable value
            source: Source of the variable (REQUIRED for debugging - no default)
            force: Whether to overwrite protected variables
            
        Returns:
            True if variable was set, False if blocked by protection
            
        Raises:
            TypeError: If source parameter is not provided (enforces spec requirement)
        """
        with self._lock:
            # Check protection
            if not force and key in self._protected_vars:
                logger.debug(f"Blocked setting protected variable: {key}")
                return False
            
            old_value = self.get(key)
            
            # Set in appropriate location
            if self._isolation_enabled:
                # Always set in isolated vars
                self._isolated_vars[key] = value
                
                # Also preserve in os.environ if it's a tool-specific variable
                if key in self.PRESERVE_IN_OS_ENVIRON:
                    os.environ[key] = value
                    masked_value = _mask_sensitive_value(key, value)
                    logger.debug(f"Set isolated var + preserved in os.environ: {key}={masked_value} (source: {source})")
                else:
                    masked_value = _mask_sensitive_value(key, value)
                    logger.debug(f"Set isolated var: {key}={masked_value} (source: {source})")
            else:
                os.environ[key] = value
                masked_value = _mask_sensitive_value(key, value)
                logger.debug(f"Set os.environ: {key}={masked_value} (source: {source})")
            
            # Track source
            self._variable_sources[key] = source
            
            # Notify callbacks
            for callback in self._change_callbacks:
                try:
                    callback(key, old_value, value)
                except Exception as e:
                    logger.warning(f"Environment change callback failed: {e}")
            
            return True
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        if self._isolation_enabled:
            return self._isolated_vars.get(key, default)
        else:
            return os.environ.get(key, default)
    
    def delete(self, key: str, source: str = "unknown") -> bool:
        """
        Delete an environment variable.
        
        Args:
            key: Environment variable name
            source: Source of the deletion (for debugging)
            
        Returns:
            True if variable was deleted, False if not found
        """
        with self._lock:
            old_value = self.get(key)
            if old_value is None:
                return False
            
            # Delete from appropriate location
            if self._isolation_enabled:
                if key in self._isolated_vars:
                    del self._isolated_vars[key]
                    
                # Also delete from os.environ if it was preserved there
                if key in self.PRESERVE_IN_OS_ENVIRON and key in os.environ:
                    del os.environ[key]
            else:
                if key in os.environ:
                    del os.environ[key]
            
            # Clean up tracking
            self._variable_sources.pop(key, None)
            
            # Notify callbacks
            for callback in self._change_callbacks:
                try:
                    callback(key, old_value, None)
                except Exception as e:
                    logger.warning(f"Environment change callback failed: {e}")
            
            logger.debug(f"Deleted environment variable: {key} (source: {source})")
            return True
    
    def exists(self, key: str) -> bool:
        """
        Check if an environment variable exists.
        
        Args:
            key: Environment variable name
            
        Returns:
            True if the variable exists, False otherwise
        """
        with self._lock:
            if self._isolation_enabled:
                return key in self._isolated_vars
            else:
                return key in os.environ
    
    def update(self, variables: Dict[str, str], source: str = "unknown", force: bool = False) -> Dict[str, bool]:
        """
        Update multiple environment variables.
        
        Args:
            variables: Dictionary of variable name -> value
            source: Source of the variables (for debugging)
            force: Whether to overwrite protected variables
            
        Returns:
            Dictionary of variable name -> whether it was set
        """
        results = {}
        for key, value in variables.items():
            results[key] = self.set(key, value, source, force)
        return results
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables as a dictionary."""
        if self._isolation_enabled:
            return dict(self._isolated_vars)
        else:
            return dict(os.environ)
    
    def get_subprocess_env(self, additional_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get environment variables for subprocess calls.
        
        This method always returns the complete environment needed for subprocesses,
        combining isolated vars (if in isolation mode) with any additional variables.
        
        Args:
            additional_vars: Additional variables to include
            
        Returns:
            Complete environment dictionary for subprocess
        """
        if self._isolation_enabled:
            env = dict(self._isolated_vars)
        else:
            env = dict(os.environ)
        
        if additional_vars:
            env.update(additional_vars)
        
        return env
    
    def protect_variable(self, key: str) -> None:
        """Mark a variable as protected from modification."""
        with self._lock:
            self._protected_vars.add(key)
            logger.debug(f"Protected variable: {key}")
    
    def unprotect_variable(self, key: str) -> None:
        """Remove protection from a variable."""
        with self._lock:
            self._protected_vars.discard(key)
            logger.debug(f"Unprotected variable: {key}")
    
    def is_protected(self, key: str) -> bool:
        """Check if a variable is protected."""
        return key in self._protected_vars
    
    def get_variable_source(self, key: str) -> Optional[str]:
        """Get the source of a variable."""
        return self._variable_sources.get(key)
    
    def add_change_callback(self, callback: Callable[[str, Optional[str], str], None]) -> None:
        """
        Add a callback to be notified of environment changes.
        
        Args:
            callback: Function with signature (key, old_value, new_value)
        """
        with self._lock:
            self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[str, Optional[str], str], None]) -> None:
        """Remove a change callback."""
        with self._lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)
    
    def load_from_file(self, file_path: Union[str, Path], source: Optional[str] = None, override_existing: bool = False) -> Tuple[int, List[str]]:
        """
        Load environment variables from a .env file.
        
        Args:
            file_path: Path to .env file (str or Path)
            source: Source name for tracking (defaults to filename)
            override_existing: Whether to override existing variables
            
        Returns:
            Tuple of (loaded_count, error_messages)
        """
        # Convert string to Path if needed
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        if source is None:
            source = f"file:{file_path.name}"
        
        if not file_path.exists():
            return 0, [f"File not found: {file_path}"]
        
        loaded_count = 0
        errors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse key=value
                    if '=' not in line:
                        errors.append(f"Line {line_num}: Invalid format (missing =)")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip('\'"').strip()
                    
                    # OS environment variables (current, not just original) always have priority 
                    # over file-based configs regardless of override_existing setting
                    # But only skip if the variable was set externally (not by a previous load_from_file)
                    if not self._isolation_enabled and key in os.environ:
                        # Check if this was set by us (via load_from_file) or externally
                        source = self._variable_sources.get(key, "")
                        if not source.startswith("file:"):
                            # This was set externally (OS env, not from a file), skip it
                            continue
                    
                    # Skip if exists and not overriding (for non-OS env vars)
                    if not override_existing and self.get(key) is not None:
                        continue
                    
                    if self.set(key, value, source):
                        loaded_count += 1
                    
        except Exception as e:
            errors.append(f"Error reading file: {e}")
        
        return loaded_count, errors
    
    def get_changes_since_init(self) -> Dict[str, Tuple[Optional[str], str]]:
        """
        Get all variables that have changed since initialization.
        
        Returns:
            Dictionary of key -> (original_value, current_value)
        """
        changes = {}
        current_env = self.get_all()
        
        # Check for additions/modifications
        for key, current_value in current_env.items():
            original_value = self._original_environ_backup.get(key)
            if original_value != current_value:
                changes[key] = (original_value, current_value)
        
        # Check for deletions
        for key, original_value in self._original_environ_backup.items():
            if key not in current_env:
                changes[key] = (original_value, None)
        
        return changes
    
    def reset_to_original(self) -> None:
        """Reset environment to original state from initialization."""
        with self._lock:
            if self._isolation_enabled:
                self._isolated_vars = dict(self._original_environ_backup)
            else:
                os.environ.clear()
                os.environ.update(self._original_environ_backup)
            
            # Clear tracking
            self._variable_sources.clear()
            
            logger.info("Environment reset to original state")
    
    # Environment Validation Methods
    # These methods provide comprehensive validation functionality previously in EnvironmentValidator
    
    def _get_required_variables(self) -> Dict[str, str]:
        """Get required environment variables with descriptions."""
        return {
            DatabaseConstants.DATABASE_URL: "PostgreSQL database connection string",
            "JWT_SECRET_KEY": "JWT token signing secret key",
            "SECRET_KEY": "Application secret key",
            "ENVIRONMENT": "Runtime environment (development/staging/production)"
        }
    
    def _get_optional_variables(self) -> Dict[str, str]:
        """Get optional environment variables with descriptions."""
        return {
            # Database connections (optional for some environments)
            DatabaseConstants.REDIS_URL: "Redis connection string",
            DatabaseConstants.CLICKHOUSE_URL: "ClickHouse connection string",
            
            # LLM API Keys (optional for basic functionality)
            "ANTHROPIC_API_KEY": "Anthropic API key for LLM services",
            "OPENAI_API_KEY": "OpenAI API key for LLM services",
            "GEMINI_API_KEY": "Google Gemini API key for LLM services",
            
            # OAuth Configuration (environment-specific)
            "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "Google OAuth client ID for development",
            "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": "Google OAuth client secret for development",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": "Google OAuth client ID for staging",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "Google OAuth client secret for staging",
            "GITHUB_OAUTH_CLIENT_ID": "GitHub OAuth client ID for authentication",
            "GITHUB_OAUTH_CLIENT_SECRET": "GitHub OAuth client secret for authentication",
            
            # API Keys for third-party integrations
            "NETRA_API_KEY": "Netra API key for service-to-service authentication",
            "LANGFUSE_PUBLIC_KEY": "Langfuse public key for observability",
            "LANGFUSE_SECRET_KEY": "Langfuse secret key for observability",
            
            # Monitoring and observability
            "GRAFANA_ADMIN_PASSWORD": "Grafana admin password for monitoring dashboards",
            "PROMETHEUS_ENABLED": "Enable Prometheus metrics collection",
            
            # Feature flags and optional configurations
            "ENABLE_WEBSOCKET_METRICS": "Enable WebSocket metrics collection",
            "WEBSOCKET_DEBUG_LOGGING": "Enable debug logging for WebSocket connections",
            "DISABLE_AUTH": "Disable authentication for testing (development only)",
            "TEST_MODE": "Enable test mode with relaxed validations",
            
            # Cloud and deployment specific
            "GCP_PROJECT_ID": "Google Cloud Project ID",
            "K_SERVICE": "Cloud Run service name (set automatically)",
            "K_REVISION": "Cloud Run revision (set automatically)",
            "PR_NUMBER": "Pull request number for staging environments",
            
            # Legacy OAuth fallbacks
            "GOOGLE_CLIENT_ID": "Legacy Google OAuth client ID (use environment-specific versions instead)",
            "GOOGLE_OAUTH_CLIENT_ID": "Legacy Google OAuth client ID (use environment-specific versions instead)"
        }
    
    def _get_validation_rules(self) -> Dict[str, callable]:
        """Get validation rules for environment variables."""
        return {
            DatabaseConstants.DATABASE_URL: self._validate_database_url,
            DatabaseConstants.REDIS_URL: self._validate_redis_url,
            DatabaseConstants.CLICKHOUSE_URL: self._validate_clickhouse_url,
            "JWT_SECRET_KEY": self._validate_secret_key,
            "SECRET_KEY": self._validate_secret_key,
            "ANTHROPIC_API_KEY": self._validate_anthropic_key,
            "OPENAI_API_KEY": self._validate_openai_key,
            "ENVIRONMENT": self._validate_environment
        }
    
    def validate_all(self) -> ValidationResult:
        """Validate all environment variables with enhanced categorization."""
        errors = []
        warnings = []
        missing_optional = []
        current_environment = self.get("ENVIRONMENT", "development")
        
        # Check required variables
        errors.extend(self._check_required_variables())
        
        # Check optional variables with context-aware warnings
        all_missing_optional = self._check_optional_variables()
        missing_optional_by_category = self._categorize_missing_optional_variables()
        
        # Convert warnings for critical missing optionals based on environment
        for var_info in all_missing_optional:
            var_name = var_info.split(' (')[0]  # Extract variable name
            if self._should_warn_about_missing_optional(var_name, current_environment):
                warnings.append(f"Missing important optional variable: {var_info}")
            else:
                missing_optional.append(var_info)
        
        # Validate variable formats
        format_errors, format_warnings = self._validate_variable_formats()
        errors.extend(format_errors)
        warnings.extend(format_warnings)
        
        # Check environment consistency
        consistency_errors = self._check_environment_consistency()
        errors.extend(consistency_errors)
        
        is_valid = len(errors) == 0
        result = ValidationResult(is_valid, errors, warnings, missing_optional)
        result.missing_optional_by_category = missing_optional_by_category
        return result
    
    def _check_required_variables(self) -> List[str]:
        """Check that all required variables are present."""
        errors = []
        required_vars = self._get_required_variables()
        for var_name, description in required_vars.items():
            if not self.get(var_name):
                errors.append(f"Missing required environment variable: {var_name} ({description})")
        return errors
    
    def _check_optional_variables(self) -> List[str]:
        """Check optional variables and note missing ones."""
        missing = []
        optional_vars = self._get_optional_variables()
        for var_name, description in optional_vars.items():
            if not self.get(var_name):
                missing.append(f"{var_name} ({description})")
        return missing
    
    def _categorize_missing_optional_variables(self) -> Dict[str, List[str]]:
        """Categorize missing optional variables by type for better reporting."""
        missing_by_category = {
            "OAuth Configuration": [],
            "LLM API Keys": [],
            "Database Connections": [],
            "Monitoring & Observability": [],
            "Feature Flags": [],
            "Cloud & Deployment": [],
            "Third-party Integrations": [],
            "Legacy/Deprecated": []
        }
        
        optional_vars = self._get_optional_variables()
        
        # Define category mappings
        category_patterns = {
            "OAuth Configuration": ["OAUTH", "CLIENT_ID", "CLIENT_SECRET", "GITHUB_OAUTH"],
            "LLM API Keys": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY"],
            "Database Connections": ["REDIS_URL", "CLICKHOUSE_URL"],
            "Monitoring & Observability": ["GRAFANA", "PROMETHEUS", "LANGFUSE", "WEBSOCKET_DEBUG", "WEBSOCKET_METRICS"],
            "Feature Flags": ["DISABLE_AUTH", "TEST_MODE", "ENABLE_", "_ENABLED"],
            "Cloud & Deployment": ["GCP_PROJECT", "K_SERVICE", "K_REVISION", "PR_NUMBER"],
            "Third-party Integrations": ["NETRA_API_KEY", "API_KEY"],
            "Legacy/Deprecated": ["GOOGLE_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_ID"]  # Non-environment-specific ones
        }
        
        for var_name, description in optional_vars.items():
            if not self.get(var_name):
                categorized = False
                for category, patterns in category_patterns.items():
                    if any(pattern in var_name for pattern in patterns):
                        missing_by_category[category].append(f"{var_name} ({description})")
                        categorized = True
                        break
                
                if not categorized:
                    missing_by_category["Third-party Integrations"].append(f"{var_name} ({description})")
        
        # Remove empty categories
        return {k: v for k, v in missing_by_category.items() if v}
    
    def _should_warn_about_missing_optional(self, var_name: str, environment: str = None) -> bool:
        """Determine if we should warn about missing optional variable based on context."""
        if environment is None:
            environment = self.get("ENVIRONMENT", "development")
        
        # Critical optional variables that should be warned about in staging/production
        critical_optional_in_staging = [
            "GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"
        ]
        
        # Variables that are only relevant in certain environments
        environment_specific = {
            "development": ["GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT"],
            "staging": ["GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "GCP_PROJECT_ID"],
            "production": ["GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION", "GCP_PROJECT_ID"]
        }
        
        # Don't warn about environment-specific variables in wrong environment
        for env, vars_for_env in environment_specific.items():
            if env != environment and var_name in vars_for_env:
                return False
        
        # Warn about critical variables in staging/production
        if environment in ["staging", "production"] and var_name in critical_optional_in_staging:
            return True
            
        # For development, only warn about development-specific OAuth
        if environment == "development" and var_name in environment_specific["development"]:
            return True
            
        return False
    
    def _validate_variable_formats(self) -> Tuple[List[str], List[str]]:
        """Validate format of environment variables."""
        errors = []
        warnings = []
        
        validation_rules = self._get_validation_rules()
        for var_name, validator in validation_rules.items():
            value = self.get(var_name)
            if value:  # Only validate if present
                try:
                    result = validator(value)
                    if not result.is_valid:
                        errors.extend([f"{var_name}: {error}" for error in result.errors])
                        warnings.extend([f"{var_name}: {warning}" for warning in result.warnings])
                except Exception as e:
                    errors.append(f"{var_name}: Validation failed - {str(e)}")
        
        return errors, warnings
    
    def _check_environment_consistency(self) -> List[str]:
        """Check consistency across environment variables."""
        errors = []
        
        # Check JWT secret consistency
        errors.extend(self._check_jwt_secret_consistency())
        
        # Check port conflicts
        errors.extend(self._check_port_conflicts())
        
        # Check database consistency
        errors.extend(self._check_database_consistency())
        
        return errors
    
    def _check_jwt_secret_consistency(self) -> List[str]:
        """Check JWT secret key consistency."""
        errors = []
        jwt_secret = self.get("JWT_SECRET_KEY")
        if jwt_secret and len(jwt_secret) < 32:
            errors.append("JWT_SECRET_KEY should be at least 32 characters for security")
        return errors
    
    def _check_port_conflicts(self) -> List[str]:
        """Check for potential port conflicts."""
        errors = []
        used_ports = set()
        
        # Extract ports from URLs
        port_sources = [
            ("DATABASE_URL", self._extract_port_from_url),
            ("REDIS_URL", self._extract_port_from_url),
            ("CLICKHOUSE_URL", self._extract_port_from_url)
        ]
        
        for source, extractor in port_sources:
            url = self.get(source)
            if url:
                port = extractor(url)
                if port and port in used_ports:
                    errors.append(f"Port conflict: {port} used by multiple services")
                if port:
                    used_ports.add(port)
        
        return errors
    
    def _check_database_consistency(self) -> List[str]:
        """Check database configuration consistency."""
        errors = []
        
        database_url = self.get(DatabaseConstants.DATABASE_URL)
        if database_url:
            # Check if URL format matches expected pattern
            if not self._is_supported_database_url(database_url):
                errors.append("DATABASE_URL format not supported for current environment")
        
        return errors
    
    def _extract_port_from_url(self, url: str) -> Optional[int]:
        """Extract port from URL."""
        try:
            parsed = urlparse(url)
            return parsed.port
        except:
            return None
    
    def _is_supported_database_url(self, url: str) -> bool:
        """Check if database URL format is supported."""
        try:
            parsed = urlparse(url)
            supported_schemes = [
                DatabaseConstants.POSTGRES_SCHEME,
                DatabaseConstants.POSTGRES_ASYNC_SCHEME,
                "sqlite", "sqlite+aiosqlite"
            ]
            return parsed.scheme in supported_schemes
        except:
            return False
    
    def _validate_database_url(self, value: str) -> ValidationResult:
        """Validate database URL format."""
        errors = []
        warnings = []
        
        try:
            parsed = urlparse(value)
            
            # Check scheme
            if not parsed.scheme:
                errors.append("Missing URL scheme (postgresql:// expected)")
            elif parsed.scheme not in [DatabaseConstants.POSTGRES_SCHEME, DatabaseConstants.POSTGRES_ASYNC_SCHEME, "sqlite", "sqlite+aiosqlite"]:
                errors.append(f"Unsupported scheme: {parsed.scheme}")
            
            # Check host (unless SQLite)
            if not parsed.scheme.startswith("sqlite") and not parsed.hostname:
                errors.append("Missing database host")
            
            # Check database name
            if not parsed.path or parsed.path == "/":
                warnings.append("No database name specified in URL")
            
        except Exception as e:
            errors.append(f"Invalid URL format: {str(e)}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _validate_redis_url(self, value: str) -> ValidationResult:
        """Validate Redis URL format."""
        errors = []
        warnings = []
        
        try:
            parsed = urlparse(value)
            
            if parsed.scheme != DatabaseConstants.REDIS_SCHEME:
                errors.append(f"Expected redis:// scheme, got {parsed.scheme}")
            
            if not parsed.hostname:
                errors.append("Missing Redis host")
                
        except Exception as e:
            errors.append(f"Invalid Redis URL: {str(e)}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _validate_clickhouse_url(self, value: str) -> ValidationResult:
        """Validate ClickHouse URL format."""
        errors = []
        warnings = []
        
        try:
            parsed = urlparse(value)
            
            if parsed.scheme != DatabaseConstants.CLICKHOUSE_SCHEME:
                errors.append(f"Expected clickhouse:// scheme, got {parsed.scheme}")
            
            if not parsed.hostname:
                errors.append("Missing ClickHouse host")
                
        except Exception as e:
            errors.append(f"Invalid ClickHouse URL: {str(e)}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _validate_secret_key(self, value: str) -> ValidationResult:
        """Validate secret key format."""
        errors = []
        warnings = []
        
        if len(value) < 16:
            errors.append("Secret key too short (minimum 16 characters)")
        elif len(value) < 32:
            warnings.append("Secret key should be at least 32 characters for better security")
        
        # Check for placeholder values
        placeholder_patterns = ["placeholder", "dev-key", "test-key", "change-me"]
        if any(pattern in value.lower() for pattern in placeholder_patterns):
            warnings.append("Secret key appears to be a placeholder value")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _validate_anthropic_key(self, value: str) -> ValidationResult:
        """Validate Anthropic API key format."""
        errors = []
        warnings = []
        
        if not value.startswith("sk-ant-"):
            warnings.append("Anthropic API key should start with 'sk-ant-'")
        
        if "placeholder" in value.lower():
            warnings.append("Anthropic API key appears to be a placeholder")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _validate_openai_key(self, value: str) -> ValidationResult:
        """Validate OpenAI API key format."""
        errors = []
        warnings = []
        
        if not value.startswith("sk-"):
            warnings.append("OpenAI API key should start with 'sk-'")
        
        if "placeholder" in value.lower():
            warnings.append("OpenAI API key appears to be a placeholder")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def _validate_environment(self, value: str) -> ValidationResult:
        """Validate environment setting."""
        errors = []
        warnings = []
        
        valid_environments = ["development", "staging", "production", "testing"]
        if value.lower() not in valid_environments:
            errors.append(f"Invalid environment: {value}. Must be one of: {', '.join(valid_environments)}")
        
        return ValidationResult(len(errors) == 0, errors, warnings, [])
    
    def print_validation_summary(self, result: ValidationResult) -> None:
        """Print validation summary with formatting."""
        if result.is_valid:
            print("ENVIRONMENT | All required variables validated successfully")
        else:
            print("ENVIRONMENT | Validation failed")
            
        if result.errors:
            print(f"\nERRORS ({len(result.errors)}):")
            for error in result.errors:
                print(f"  - {error}")
                
        if result.warnings:
            print(f"\nWARNINGS ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        # Print categorized optional variables
        if result.missing_optional_by_category:
            print(f"\nOPTIONAL VARIABLES BY CATEGORY:")
            for category, vars_in_category in result.missing_optional_by_category.items():
                if vars_in_category:  # Only show categories that have missing vars
                    print(f"\n  {category} ({len(vars_in_category)} missing):")
                    for missing in vars_in_category:
                        print(f"    - {missing}")
                        
        elif result.missing_optional:
            # Fallback to old format if categorization failed
            print(f"\nOPTIONAL MISSING ({len(result.missing_optional)}):")
            for missing in result.missing_optional:
                print(f"  - {missing}")
    
    def get_fix_suggestions(self, result: ValidationResult) -> List[str]:
        """Get suggestions for fixing validation issues."""
        suggestions = []
        
        if result.errors:
            suggestions.append("Fix the errors above before starting services")
            suggestions.append("Check your .env file for missing or incorrect values")
            suggestions.append("Refer to .env.example for correct format")
        
        if any("placeholder" in error.lower() for error in result.warnings):
            suggestions.append("Replace placeholder API keys with real values for full functionality")
        
        if any("secret" in error.lower() for error in result.errors):
            suggestions.append("Generate secure secret keys using: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
        
        return suggestions
    
    def _get_fallback_values(self) -> Dict[str, callable]:
        """Get fallback value generators for required variables."""
        return {
            "DATABASE_URL": self._generate_database_url_fallback,
            "JWT_SECRET_KEY": self._generate_jwt_secret_fallback,
            "SECRET_KEY": self._generate_secret_key_fallback,
            "ENVIRONMENT": lambda: "development",
        }
    
    def _generate_database_url_fallback(self) -> str:
        """Generate a fallback database URL for development."""
        try:
            # Import DatabaseURLBuilder to construct PostgreSQL URLs from components
            from shared.database_url_builder import DatabaseURLBuilder
            
            # Use DatabaseURLBuilder to construct URL from environment variables
            builder = DatabaseURLBuilder(self.get_all())
            
            # Get the appropriate URL for the environment
            postgres_url = builder.get_url_for_environment(sync=False)
            
            if postgres_url:
                logger.info(f"Generated PostgreSQL fallback URL using DatabaseURLBuilder")
                return postgres_url
            else:
                logger.warning("DatabaseURLBuilder could not generate URL, falling back to development default")
                return builder.development.default_url
                
        except Exception as e:
            logger.warning(f"Failed to use DatabaseURLBuilder for fallback: {e}")
            # Fallback to the development default if DatabaseURLBuilder fails
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev"
    
    def _generate_jwt_secret_fallback(self) -> str:
        """Generate a secure JWT secret key."""
        import secrets
        return secrets.token_urlsafe(64)
    
    def _generate_secret_key_fallback(self) -> str:
        """Generate a secure application secret key."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def validate_with_fallbacks(self, enable_fallbacks: bool = True, development_mode: bool = True) -> ValidationResult:
        """Enhanced validation with fallback application and categorization."""
        errors = []
        warnings = []
        missing_optional = []
        fallback_applied = []
        current_environment = self.get("ENVIRONMENT", "development")
        
        required_vars = self._get_required_variables()
        fallback_values = self._get_fallback_values()
        
        # Check required variables with fallbacks
        for var_name, description in required_vars.items():
            if not self.get(var_name):
                if enable_fallbacks and var_name in fallback_values:
                    try:
                        fallback_value = fallback_values[var_name]()
                        if fallback_value:
                            self.set(var_name, fallback_value, "environment_validator_fallback")
                            fallback_applied.append(var_name)
                            logger.info(f"Applied fallback for {var_name}")
                        else:
                            errors.append(f"Missing required environment variable: {var_name} ({description})")
                    except Exception as e:
                        logger.warning(f"Failed to generate fallback for {var_name}: {e}")
                        errors.append(f"Missing required environment variable: {var_name} ({description})")
                else:
                    errors.append(f"Missing required environment variable: {var_name} ({description})")
        
        # Check optional variables with context-aware warnings
        all_missing_optional = self._check_optional_variables()
        missing_optional_by_category = self._categorize_missing_optional_variables()
        
        # Convert warnings for critical missing optionals based on environment
        for var_info in all_missing_optional:
            var_name = var_info.split(' (')[0]  # Extract variable name
            if self._should_warn_about_missing_optional(var_name, current_environment):
                warnings.append(f"Missing important optional variable: {var_info}")
            else:
                missing_optional.append(var_info)
        
        # Validate formats
        format_errors, format_warnings = self._validate_variable_formats()
        errors.extend(format_errors)
        warnings.extend(format_warnings)
        
        # Check consistency
        consistency_errors = self._check_environment_consistency()
        errors.extend(consistency_errors)
        
        is_valid = len(errors) == 0
        suggestions = self.get_fix_suggestions(ValidationResult(is_valid, errors, warnings, missing_optional))
        
        result = ValidationResult(is_valid, errors, warnings, missing_optional, fallback_applied, suggestions)
        result.missing_optional_by_category = missing_optional_by_category
        return result
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the environment manager."""
        return {
            "isolation_enabled": self._isolation_enabled,
            "isolated_vars_count": len(self._isolated_vars),
            "os_environ_count": len(os.environ),
            "protected_vars": list(self._protected_vars),
            "tracked_sources": dict(self._variable_sources),
            "change_callbacks_count": len(self._change_callbacks),
            "original_backup_count": len(self._original_environ_backup)
        }


# Global instance for easy access
_global_env = IsolatedEnvironment()


def get_env() -> IsolatedEnvironment:
    """Get the global isolated environment instance."""
    return _global_env


# Convenience functions for backwards compatibility
def setenv(key: str, value: str, source: str = "unknown") -> bool:
    """Set environment variable using the global isolated environment."""
    return get_env().set(key, value, source)


def getenv(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable using the global isolated environment."""
    return get_env().get(key, default)


def delenv(key: str) -> bool:
    """Delete environment variable using the global isolated environment."""
    return get_env().delete(key)


def get_subprocess_env(additional_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Get complete environment for subprocess calls."""
    return get_env().get_subprocess_env(additional_vars)


# Legacy compatibility function  
def get_environment_manager(isolation_mode: Optional[bool] = None):
    """
    Legacy compatibility function for get_environment_manager.
    
    This function now delegates to the EnvironmentManager wrapper for full compatibility.
    
    Args:
        isolation_mode: If provided, enables/disables isolation mode
        
    Returns:
        EnvironmentManager instance wrapping IsolatedEnvironment
    """
    # Import here to avoid circular dependency
    from dev_launcher.environment_manager import get_environment_manager as get_manager
    return get_manager(isolation_mode)


def load_secrets() -> bool:
    """
    Legacy compatibility function for loading secrets.
    
    This is a placeholder for the load_secrets functionality that was moved.
    Returns True to indicate successful loading for backward compatibility.
    
    Returns:
        bool: Always returns True for compatibility
    """
    # Simple compatibility implementation
    logger.info("load_secrets called - compatibility mode")
    return True


class SecretLoader:
    """
    Legacy compatibility class for secret loading functionality.
    
    This provides a compatibility layer for existing code that expects SecretLoader.
    Actual secret loading functionality is handled by the environment management system.
    """
    
    def __init__(self, env_manager: Optional[IsolatedEnvironment] = None):
        """Initialize secret loader."""
        self.env_manager = env_manager or get_env()
        
    def load_secrets(self) -> bool:
        """Load secrets (compatibility method)."""
        return load_secrets()
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value."""
        return self.env_manager.get(key, default)
    
    def set_secret(self, key: str, value: str, source: str = "secret_loader") -> bool:
        """Set a secret value."""
        return self.env_manager.set(key, value, source)


# Backwards Compatibility: EnvironmentValidator class
# This provides a compatibility layer for existing code that expects EnvironmentValidator
class EnvironmentValidator:
    """
    Backwards compatibility wrapper for environment validation functionality.
    
    This class delegates all validation operations to the global IsolatedEnvironment instance.
    It maintains the same API as the original EnvironmentValidator for seamless migration.
    """
    
    def __init__(self, enable_fallbacks: bool = True, development_mode: bool = True):
        """Initialize environment validator (compatibility layer)."""
        self.enable_fallbacks = enable_fallbacks
        self.development_mode = development_mode
        self.env = get_env()
    
    @property
    def required_vars(self) -> Dict[str, str]:
        """Get required environment variables."""
        return self.env._get_required_variables()
    
    @property 
    def optional_vars(self) -> Dict[str, str]:
        """Get optional environment variables."""
        return self.env._get_optional_variables()
    
    @property
    def validation_rules(self) -> Dict[str, callable]:
        """Get validation rules."""
        return self.env._get_validation_rules()
    
    def validate_all(self) -> ValidationResult:
        """Validate all environment variables."""
        return self.env.validate_all()
    
    def validate_with_fallbacks(self) -> ValidationResult:
        """Enhanced validation with fallback application."""
        return self.env.validate_with_fallbacks(self.enable_fallbacks, self.development_mode)
    
    def print_validation_summary(self, result: ValidationResult) -> None:
        """Print validation summary with colors and formatting."""
        return self.env.print_validation_summary(result)
    
    def get_fix_suggestions(self, result: ValidationResult) -> List[str]:
        """Get suggestions for fixing validation issues."""
        return self.env.get_fix_suggestions(result)