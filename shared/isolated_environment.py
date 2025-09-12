"""
Unified Environment Variable Management - SINGLE SOURCE OF TRUTH

This module provides centralized environment variable management across the entire platform.
ALL environment variable access MUST go through this unified implementation.

CRITICAL: This consolidates the following previous implementations:
- dev_launcher.isolated_environment.IsolatedEnvironment (1286 lines)
- netra_backend.app.core.isolated_environment.IsolatedEnvironment (491 lines)
- auth_service.auth_core.isolated_environment.IsolatedEnvironment (409 lines)
- analytics_service.analytics_core.isolated_environment.IsolatedEnvironment (244 lines)

Business Value: Platform/Internal - System Stability & Service Independence
Prevents configuration drift and ensures consistent environment management across all services.

REQUIREMENTS per SPEC/unified_environment_management.xml:
- Single Source of Truth (SSOT) for all environment access
- Thread-safe singleton pattern
- Isolation mode for development/testing
- Source tracking for debugging
- Service independence maintained
"""
import os
import re
import secrets
import threading
import subprocess
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


@dataclass
class ValidationResult:
    """Environment variable validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_optional: List[str]
    fallback_applied: List[str] = None
    suggestions: List[str] = None
    missing_optional_by_category: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.fallback_applied is None:
            self.fallback_applied = []
        if self.suggestions is None:
            self.suggestions = []
        if self.missing_optional_by_category is None:
            self.missing_optional_by_category = {}


class IsolatedEnvironment:
    """
    Unified environment variable manager with isolation support - SINGLE SOURCE OF TRUTH.
    
    This singleton class manages ALL environment variable access across the entire platform.
    Features from all previous implementations:
    - Isolation mode prevents os.environ pollution
    - Thread-safe operations with RLock
    - Source tracking for debugging
    - Value sanitization and validation
    - Shell command expansion
    - Comprehensive validation with fallbacks
    - Test integration compatibility
    - Service independence support
    
    CRITICAL: This replaces ALL previous IsolatedEnvironment implementations.
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
        """Ensure singleton behavior with thread safety.
        
        Enhanced double-checked locking with additional safety measures.
        This method guarantees that only one instance is ever created across
        all threads and all access patterns.
        """
        # First check (fast path) - no lock needed if instance already exists
        if cls._instance is not None:
            return cls._instance
        
        # Second check with lock (slow path) - ensure atomic instance creation
        with cls._lock:
            if cls._instance is None:
                logger.debug("Creating new IsolatedEnvironment singleton instance")
                cls._instance = super().__new__(cls)
                
                # CRITICAL: Verify module-level singleton consistency
                # This ensures _env_instance and cls._instance are always the same
                import sys
                current_module = sys.modules.get(__name__)
                if current_module and hasattr(current_module, '_env_instance'):
                    if current_module._env_instance is not None and current_module._env_instance is not cls._instance:
                        logger.warning(
                            f"Singleton consistency issue detected: "
                            f"cls._instance={id(cls._instance)} != "
                            f"_env_instance={id(current_module._env_instance)}"
                        )
                        # Force consistency by updating module instance
                        current_module._env_instance = cls._instance
                        logger.info("Forced singleton consistency - updated _env_instance")
                
                logger.debug(f"Singleton instance created: ID {id(cls._instance)}")
            else:
                logger.debug("Singleton instance already exists, returning existing")
                
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
            self._env_cache: Dict[str, Any] = {}
            self._original_state: Optional[Dict[str, str]] = None
            self._bypass_test_defaults: bool = False  # Flag to bypass test defaults after force reset
            self._explicitly_cleared_keys: Set[str] = set()  # Keys that were explicitly cleared
            
            # Track initial os.environ state
            self._original_environ_backup = dict(os.environ)
            
            # Automatically load .env file if it exists
            self._auto_load_env_file()
            
            # Set default optimized persistence configuration
            self._set_optimized_persistence_defaults()
            
            # CRITICAL FIX: Auto-enable isolation during test contexts to ensure test defaults are available
            # This ensures OAuth test credentials are accessible during CentralConfigurationValidator execution
            if self._is_test_context():
                self._isolation_enabled = True
                logger.debug("Auto-enabled isolation for test context - OAuth test credentials now available")
            
            self._initialized = True
            logger.debug("Unified IsolatedEnvironment initialized")
    
    def _auto_load_env_file(self) -> None:
        """Automatically load .env file if it exists.
        
        IMPORTANT: Does NOT override existing environment variables.
        This ensures that environment variables set by Docker, Cloud Run,
        or the deployment system take precedence over .env file values.
        
        CRITICAL: .env files are NEVER loaded in staging or production environments
        to ensure secrets come only from the deployment system.
        EXCEPTION: For local testing, environment-specific files (staging.env, production.env)
        can be loaded when ENABLE_LOCAL_CONFIG_FILES=true is set.
        """
        # Skip auto-loading during pytest to allow test configuration to take precedence
        import sys
        if 'pytest' in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            logger.debug("Skipping env file auto-load during pytest execution")
            return
        
        # Skip auto-loading if explicitly disabled
        if os.environ.get("DISABLE_SECRETS_LOADING", "").lower() == "true":
            logger.debug("Skipping env file auto-load due to DISABLE_SECRETS_LOADING")
            return
            
        # Check current environment
        environment = os.environ.get('ENVIRONMENT', '').lower()
        
        # For staging/production: only load environment-specific config if explicitly enabled for local testing
        if environment in ['staging', 'production']:
            enable_local_config = os.environ.get("ENABLE_LOCAL_CONFIG_FILES", "").lower() == "true"
            if enable_local_config:
                self._load_environment_specific_file(environment)
            else:
                logger.debug(f"Skipping .env file loading in {environment} environment (set ENABLE_LOCAL_CONFIG_FILES=true for local testing)")
            return
        
        try:
            # Look for .env file first
            env_file = Path.cwd() / ".env"
            if env_file.exists():
                # Load .env file but DO NOT override existing variables
                loaded_count, errors = self.load_from_file(env_file, override_existing=False)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .env (without overriding existing)")
                if errors:
                    for error in errors:
                        logger.warning(f"Auto-load error: {error}")
                return
            
            # If no .env file, look for .secrets file (auth_service compatibility)
            secrets_file = Path.cwd() / ".secrets"
            if secrets_file.exists():
                loaded_count, errors = self.load_from_file(secrets_file, override_existing=False)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from .secrets (without overriding existing)")
                if errors:
                    for error in errors:
                        logger.warning(f"Auto-load error: {error}")
                        
        except Exception as e:
            logger.warning(f"Failed to auto-load env file: {e}")
    
    def _load_environment_specific_file(self, environment: str) -> None:
        """Load environment-specific configuration file for local testing.
        
        This method loads config/{environment}.env files when ENABLE_LOCAL_CONFIG_FILES=true.
        Used for local testing of staging/production configurations.
        
        Args:
            environment: The environment name (e.g., 'staging', 'production')
        """
        try:
            config_dir = Path.cwd() / "config"
            env_file = config_dir / f"{environment}.env"
            
            if env_file.exists():
                # Load environment-specific file but DO NOT override existing variables
                # This ensures deployment system values take precedence
                loaded_count, errors = self.load_from_file(env_file, override_existing=False)
                if loaded_count > 0:
                    logger.debug(f"Auto-loaded {loaded_count} variables from {environment}.env (without overriding existing)")
                if errors:
                    for error in errors:
                        logger.warning(f"Auto-load error from {environment}.env: {error}")
            else:
                logger.debug(f"Environment-specific file {env_file} not found")
                
        except Exception as e:
            logger.warning(f"Failed to load environment-specific file for {environment}: {e}")
    
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
        
        CRITICAL: This method MUST NOT use self.get() to avoid recursion with logging.
        
        Returns:
            bool: True if in test context, False otherwise
        """
        import sys
        
        # CRITICAL FIX: Only check for pytest if we're actually running pytest
        # Don't trigger test mode just because pytest is imported as a dependency
        if 'pytest' in sys.modules and hasattr(sys.modules['pytest'], 'main'):
            # Only consider it a test if pytest is actively running a test
            if os.environ.get('PYTEST_CURRENT_TEST'):
                return True
            # Additional check: if pytest is actively executing (not just imported)
            if hasattr(sys, '_pytest_running') and sys._pytest_running:
                return True
        
        # Check for test environment variables using internal access to avoid recursion
        test_indicators = [
            'PYTEST_CURRENT_TEST',
            'TESTING',
            'TEST_MODE'
        ]
        
        # CRITICAL: When isolation is enabled, we need to check isolated vars first
        # This ensures test context detection respects isolation boundaries for testing scenarios
        for indicator in test_indicators:
            # In isolation mode, check isolated vars first, then fall back to os.environ
            if self._isolation_enabled and indicator in self._isolated_vars:
                value = self._isolated_vars[indicator]
                if value == "__UNSET__":
                    continue  # Variable was explicitly unset in isolation
            else:
                # Use os.environ for non-isolated vars or when isolation is disabled
                value = os.environ.get(indicator, '')
            
            # PYTEST_CURRENT_TEST contains test identifier, not boolean value
            if indicator == 'PYTEST_CURRENT_TEST':
                # If PYTEST_CURRENT_TEST exists and is not empty, we're in a test
                if value:
                    return True
            else:
                # For other indicators, check for boolean values
                if value.lower() in ['true', '1', 'yes', 'on']:
                    return True
        
        # Check if ENVIRONMENT is set to testing
        # In isolation mode, check isolated vars first
        if self._isolation_enabled and 'ENVIRONMENT' in self._isolated_vars:
            env_value = self._isolated_vars['ENVIRONMENT']
            if env_value != "__UNSET__":
                env_value = env_value.lower()
            else:
                env_value = ''
        else:
            env_value = os.environ.get('ENVIRONMENT', '').lower()
            
        if env_value in ['test', 'testing']:
            return True
        
        return False
    
    def _get_test_environment_defaults(self) -> Dict[str, str]:
        """
        Get built-in default values for test environment.
        
        CRITICAL: These defaults ensure OAuth test credentials are ALWAYS available
        during test execution, preventing CentralConfigurationValidator failures.
        
        Returns:
            Dict of test environment default values
        """
        return {
            # OAuth Test Environment Credentials - CRITICAL for CentralConfigurationValidator
            'GOOGLE_OAUTH_CLIENT_ID_TEST': 'test-oauth-client-id-for-automated-testing',
            'GOOGLE_OAUTH_CLIENT_SECRET_TEST': 'test-oauth-client-secret-for-automated-testing',
            
            # E2E Test OAuth Simulation - CRITICAL for agent integration tests
            'E2E_OAUTH_SIMULATION_KEY': 'test-e2e-oauth-bypass-key-for-testing-only-unified-2025',
            
            # Basic test environment settings
            'ENVIRONMENT': 'test',
            'TESTING': '1',
            'TEST_MODE': 'true',
            'TEST_ENV': 'test',
            
            # Security defaults for testing
            'JWT_SECRET_KEY': 'test-jwt-secret-key-32-characters-long-for-testing-only',
            'SERVICE_SECRET': 'test-service-secret-32-characters-long-for-cross-service-auth',
            'FERNET_KEY': 'test-fernet-key-for-encryption-32-characters-long-base64-encoded=',
            'SECRET_KEY': 'test-secret-key-for-test-environment-only-32-chars-min',
            
            # API Keys for testing (placeholder values for unit tests, staging uses Secret Manager)
            'ANTHROPIC_API_KEY': 'test-anthropic-api-key-placeholder-for-unit-tests',
            'OPENAI_API_KEY': 'test-openai-api-key-placeholder-for-unit-tests', 
            'GEMINI_API_KEY': 'test-gemini-api-key-placeholder-for-unit-tests',
            
            # Database defaults for testing
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5434',
            'POSTGRES_USER': 'netra_test',
            'POSTGRES_PASSWORD': 'netra_test_password',
            'POSTGRES_DB': 'netra_test',
            'DATABASE_URL': 'postgresql://netra_test:netra_test_password@localhost:5434/netra_test',
            
            # Redis defaults for testing
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6381',
            'REDIS_URL': 'redis://localhost:6381/0',
            
            # Service configuration for testing
            'SERVER_PORT': '8000',
            'AUTH_PORT': '8081',
            'FRONTEND_PORT': '3000',
            'LOG_LEVEL': 'DEBUG',
            
            # Staging environment test defaults - FIXES GitHub Issue #259
            'JWT_SECRET_STAGING': 'test_jwt_secret_staging_' + secrets.token_urlsafe(32),
            'REDIS_PASSWORD': 'test_redis_password_' + secrets.token_urlsafe(16),
            'GOOGLE_OAUTH_CLIENT_ID_STAGING': 'test_oauth_client_id_staging.apps.googleusercontent.com',
            'GOOGLE_OAUTH_CLIENT_SECRET_STAGING': 'test_oauth_client_secret_staging_' + secrets.token_urlsafe(24),

            # Production environment test defaults (comprehensive coverage)
            'JWT_SECRET_PRODUCTION': 'test_jwt_secret_production_' + secrets.token_urlsafe(32),
            'GOOGLE_OAUTH_CLIENT_ID_PRODUCTION': 'test_oauth_client_id_production.apps.googleusercontent.com',
            'GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION': 'test_oauth_client_secret_production_' + secrets.token_urlsafe(24)
        }
    
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
        # CRITICAL: Don't use logger.debug here as it can cause recursion with logging filters
        import sys
        if 'pytest' in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
            return value
        
        # Skip if explicitly disabled
        if os.environ.get("DISABLE_SHELL_EXPANSION", "false").lower() == "true":
            return value
        
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
                        # Skip logging during shell expansion to avoid recursion
                    else:
                        # Command failed - log error but keep original
                        logger.warning(f"Shell command '{command}' failed with code {result.returncode}: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    logger.warning(f"Shell command '{command}' timed out after 5 seconds")
                except Exception as e:
                    logger.warning(f"Error executing shell command '{command}': {e}")
        
        # Also expand environment variable references like ${VARIABLE}
        env_var_pattern = r'\$\{([^}]+)\}'
        
        def replace_env_var(match):
            var_name = match.group(1)
            # Get the variable value, but don't recursively expand to avoid loops
            var_value = os.environ.get(var_name, '')
            # Skip logging during variable expansion to avoid recursion
            return var_value
        
        expanded_value = re.sub(env_var_pattern, replace_env_var, expanded_value)
        
        # Skip logging expansion to avoid recursion with logging filters
        
        return expanded_value
    
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
                # Save original state for reset_to_original()
                self._original_state = dict(os.environ)
                
            # Always refresh isolated vars when explicitly requested or first time enabling
            if refresh_vars or not was_already_enabled:
                # Copy current environment to isolated storage
                self._isolated_vars = dict(os.environ)
                logger.debug(f"Refreshed isolated vars from os.environ: {len(self._isolated_vars)} variables captured")
            
            # CRITICAL TEST INTEGRATION: In test context, sync isolated vars with os.environ
            # This ensures test patches (patch.dict(os.environ, ...)) are immediately available
            if self._is_test_context():
                self._sync_with_os_environ()
            
            # Ensure preserved variables remain in os.environ
            for key in self.PRESERVE_IN_OS_ENVIRON:
                if key in self._isolated_vars and key not in os.environ:
                    os.environ[key] = self._isolated_vars[key]
                    logger.debug(f"Preserved {key} in os.environ during isolation")
                elif key in os.environ and key not in self._isolated_vars:
                    self._isolated_vars[key] = os.environ[key]
                    logger.debug(f"Captured {key} from os.environ during isolation")
            
            if was_already_enabled:
                logger.debug(f"Environment isolation refreshed with {len(self._isolated_vars)} variables")
            else:
                logger.info("Environment isolation enabled")
    
    def enable_isolation_mode(self, backup_original: bool = True, refresh_vars: bool = True) -> None:
        """
        BACKWARDS COMPATIBILITY: Alias for enable_isolation method.
        
        This method maintains compatibility with existing test framework code
        that calls enable_isolation_mode() instead of enable_isolation().
        
        Args:
            backup_original: Whether to backup current os.environ state
            refresh_vars: Whether to refresh isolated vars from current os.environ state
        """
        return self.enable_isolation(backup_original, refresh_vars)
    
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
                if self._original_environ_backup:
                    os.environ.clear()
                    os.environ.update(self._original_environ_backup)
                    logger.info("Original environment restored")
            else:
                # Sync isolated vars to os.environ
                for key, value in self._isolated_vars.items():
                    os.environ[key] = value
                logger.info("Isolated environment synced to os.environ")
            
            # Clear isolated vars and cache
            self._isolated_vars.clear()
            self._env_cache.clear()
            logger.debug("Isolation mode disabled")
    
    def is_isolated(self) -> bool:
        """Check if isolation mode is enabled."""
        return self._isolation_enabled
    
    def is_isolation_enabled(self) -> bool:
        """Check if isolation mode is enabled (alias for compatibility)."""
        return self._isolation_enabled
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable value."""
        with self._lock:
            # CRITICAL FIX: When isolation is enabled, isolated variables ALWAYS take precedence
            # This ensures that our configuration values are properly retrieved during testing
            if self._isolation_enabled:
                # Check isolated variables first (including explicitly unset ones)
                if key in self._isolated_vars:
                    override_value = self._isolated_vars[key]
                    if override_value == "__UNSET__":
                        return default  # Variable was explicitly unset
                    # If value exists and is non-empty, return it
                    if override_value:
                        return self._expand_shell_commands(override_value)
                    # If value is empty string, fall through to check test defaults
                    # This allows test defaults to provide values for empty variables
                
                # If not in isolated vars but we're in test context, sync with os.environ
                # This allows pytest patches to be picked up, but only if not already in isolated vars
                if self._is_test_context() and key in os.environ:
                    value = os.environ[key]
                    # Only return non-empty values, let empty values fall through to test defaults
                    if value:
                        return self._expand_shell_commands(value)
                
                # CRITICAL FIX: Provide OAuth test credentials as built-in defaults during test context
                # This ensures CentralConfigurationValidator can always find required test OAuth credentials
                # CRITICAL: Honor bypass flag to prevent configuration pollution between test scenarios
                # CRITICAL: Don't return defaults for keys that were explicitly cleared
                if self._is_test_context() and not self._bypass_test_defaults:
                    test_defaults = self._get_test_environment_defaults()
                    if key in test_defaults:
                        # Don't return defaults for keys that were explicitly cleared
                        if key not in self._explicitly_cleared_keys:
                            return test_defaults[key]
                
                # Not found in isolated vars or os.environ
                return default
            
            # Not in isolation mode - use normal environment access with caching
            else:
                # Check cache first (analytics compatibility)
                if key in self._env_cache:
                    cached_value = self._env_cache[key]
                    if cached_value is None:
                        return default
                    return self._expand_shell_commands(cached_value) if cached_value else cached_value
                
                # Get from os.environ
                if key in os.environ:
                    value = os.environ[key]
                    # Cache the actual value
                    self._env_cache[key] = value
                    # Expand shell commands in the value if present
                    return self._expand_shell_commands(value) if value else value
                else:
                    # Cache that it doesn't exist (using None as marker)
                    self._env_cache[key] = None
                    return default
    
    def set(self, key: str, value: str, source: str = "unknown", force: bool = False) -> bool:
        """
        Set an environment variable with source tracking.
        
        Args:
            key: Environment variable name
            value: Environment variable value
            source: Source of the variable (for debugging)
            force: Whether to overwrite protected variables
            
        Returns:
            True if variable was set, False if blocked by protection
        """
        with self._lock:
            # Check protection
            if not force and key in self._protected_vars:
                logger.debug(f"Blocked setting protected variable: {key}")
                return False
            
            old_value = self.get(key)
            
            # Apply sanitization to avoid corruption of sensitive values
            sanitized_value = self._sanitize_value(value)
            
            # Set in appropriate location
            if self._isolation_enabled:
                # Always set in isolated vars
                self._isolated_vars[key] = sanitized_value
                
                # Also preserve in os.environ if it's a tool-specific variable
                if key in self.PRESERVE_IN_OS_ENVIRON:
                    os.environ[key] = sanitized_value
                    masked_value = _mask_sensitive_value(key, sanitized_value)
                    logger.debug(f"Set isolated var + preserved in os.environ: {key}={masked_value} (source: {source})")
                else:
                    masked_value = _mask_sensitive_value(key, sanitized_value)
                    logger.debug(f"Set isolated var: {key}={masked_value} (source: {source})")
            else:
                os.environ[key] = sanitized_value
                masked_value = _mask_sensitive_value(key, sanitized_value)
                if source != "silent":
                    logger.debug(f"Set os.environ: {key}={masked_value} (source: {source})")
            
            # Update cache
            self._env_cache[key] = sanitized_value
            
            # Track source
            self._variable_sources[key] = source
            
            # Notify callbacks
            for callback in self._change_callbacks:
                try:
                    callback(key, old_value, sanitized_value)
                except Exception as e:
                    logger.warning(f"Environment change callback failed: {e}")
            
            return True
    
    def delete(self, key: str, source: str = "unknown") -> bool:
        """Delete an environment variable."""
        with self._lock:
            old_value = self.get(key)
            if old_value is None:
                return False
            
            # Delete from appropriate location
            if self._isolation_enabled:
                if key in self._isolated_vars:
                    # In isolation mode, we need to track that this variable was unset
                    self._isolated_vars[key] = "__UNSET__"
                    
                # Also delete from os.environ if it was preserved there
                if key in self.PRESERVE_IN_OS_ENVIRON and key in os.environ:
                    del os.environ[key]
            else:
                if key in os.environ:
                    del os.environ[key]
            
            # Remove from cache
            self._env_cache.pop(key, None)
            
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
    
    def clear_env_var(self, key: str) -> bool:
        """Clear/delete an environment variable (alias for delete method)."""
        return self.delete(key, source='test_clear')
    
    def exists(self, key: str) -> bool:
        """Check if an environment variable exists."""
        with self._lock:
            if self._isolation_enabled:
                # Check if explicitly unset
                if key in self._isolated_vars and self._isolated_vars[key] == "__UNSET__":
                    return False
                return key in self._isolated_vars
            return key in os.environ
    
    def is_set(self, key: str) -> bool:
        """Check if an environment variable is set (alias for exists)."""
        return self.exists(key)
    
    def unset(self, key: str) -> None:
        """Unset an environment variable (alias for delete)."""
        self.delete(key)
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables."""
        with self._lock:
            if self._isolation_enabled:
                # Filter out explicitly unset variables
                result = {}
                for k, v in self._isolated_vars.items():
                    if v != "__UNSET__":
                        result[k] = v
                return result
            else:
                return dict(os.environ)
    
    def get_all_variables(self) -> Dict[str, str]:
        """Get all environment variables (alias for compatibility)."""
        return self.get_all()
    
    def as_dict(self) -> Dict[str, str]:
        """Get all environment variables as a dictionary (compatibility method)."""
        return self.get_all()
    
    def update(self, variables: Dict[str, str], source: str = "unknown", force: bool = False) -> Dict[str, bool]:
        """Update multiple environment variables."""
        results = {}
        for key, value in variables.items():
            results[key] = self.set(key, value, source, force)
        
        if source != "silent" and variables:
            logger.debug(f"Updated {len(variables)} variables from {source}")
        
        return results
    
    def get_subprocess_env(self, additional_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get environment variables for subprocess calls.
        
        Args:
            additional_vars: Additional variables to include
            
        Returns:
            Complete environment dictionary for subprocess
        """
        if self._isolation_enabled:
            # Merge isolated vars with minimal required system vars
            env = dict(self._isolated_vars)
            
            # Ensure critical system variables are present
            system_vars = ['PATH', 'SYSTEMROOT', 'TEMP', 'TMP', 'USERPROFILE', 'HOME']
            for var in system_vars:
                if var in os.environ and var not in env:
                    env[var] = os.environ[var]
        else:
            env = dict(os.environ)
        
        if additional_vars:
            env.update(additional_vars)
        
        return env
    
    def clear(self, force_reset: bool = False) -> None:
        """
        Clear all environment variables (only in isolation mode).
        
        Args:
            force_reset: If True, completely reset singleton state including variable sources tracking.
                        This prevents configuration pollution between test scenarios.
                        If False, will auto-detect environment switching and enable bypass if needed.
        """
        if not self._isolation_enabled:
            raise RuntimeError("Cannot clear environment variables outside isolation mode")
        
        with self._lock:
            # CRITICAL FIX: In test contexts, clearing should disable built-in defaults to prevent pollution
            # This ensures complete isolation between different test configurations
            should_bypass_defaults = force_reset or self._is_test_context()
            if should_bypass_defaults and not force_reset:
                logger.debug("Test context detected during clear() - enabling test defaults bypass to ensure clean configuration isolation")
            
            # CRITICAL FIX: Track keys that existed before clearing for bypass logic
            if should_bypass_defaults:
                # Remember which keys were explicitly set so we don't return defaults for them
                self._explicitly_cleared_keys.update(self._isolated_vars.keys())
                logger.debug(f"Tracked {len(self._isolated_vars)} explicitly cleared keys: {list(self._isolated_vars.keys())}")
            
            self._isolated_vars.clear()
            self._protected_vars.clear()
            self._env_cache.clear()
            
            # CRITICAL FIX: Clear variable sources to prevent configuration pollution
            if should_bypass_defaults:
                self._variable_sources.clear()
                self._bypass_test_defaults = True  # Bypass test defaults until next reset
                logger.debug("Cleared all singleton state including variable sources and enabled test defaults bypass")
    
    def protect(self, key: str) -> None:
        """Mark a variable as protected (cannot be modified)."""
        self.protect_variable(key)
    
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
        """Add a callback to be notified of environment changes."""
        with self._lock:
            self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[str, Optional[str], str], None]) -> None:
        """Remove a change callback."""
        with self._lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)

    def get_change_history(self, key: str) -> List[Dict[str, Any]]:
        """
        Get change history for a specific environment variable.
        
        Args:
            key: Environment variable name
            
        Returns:
            List of change records with timestamps and sources
        """
        # For now, return a simplified history based on current state
        history = []
        current_value = self.get(key)
        current_source = self.get_variable_source(key)
        
        if current_value is not None:
            history.append({
                "value": current_value,
                "source": current_source or "unknown",
                "timestamp": "current"
            })
        
        return history

    def get_sources(self) -> Dict[str, List[str]]:
        """
        Get all environment variables organized by source.
        
        Returns:
            Dictionary mapping source names to lists of variable names
        """
        sources = {}
        
        with self._lock:
            for var_name, source in self._variable_sources.items():
                if source not in sources:
                    sources[source] = []
                sources[source].append(var_name)
        
        return sources
    
    def load_from_file(self, filepath: Union[str, Path], source: Optional[str] = None, override_existing: bool = True) -> Tuple[int, List[str]]:
        """
        Load environment variables from a .env file.
        
        Args:
            filepath: Path to .env file (str or Path)
            source: Source name for tracking (defaults to filename)
            override_existing: Whether to override existing variables
            
        Returns:
            Tuple of (loaded_count, error_messages)
        """
        # Convert string to Path if needed
        if isinstance(filepath, str):
            filepath = Path(filepath)
            
        if source is None:
            source = f"file:{filepath.name}"
        
        if not filepath.exists():
            logger.warning(f"Environment file not found: {filepath}")
            return 0, [f"File not found: {filepath}"]
        
        loaded_count = 0
        errors = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' not in line:
                        errors.append(f"Line {line_num}: Invalid format (missing =)")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Validate key is not empty
                    if not key:
                        errors.append(f"Line {line_num}: Invalid format (empty key name)")
                        continue
                    
                    # Remove quotes if present
                    if value and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    
                    # OS environment variables (current, not just original) always have priority 
                    # over file-based configs regardless of override_existing setting
                    # But only skip if the variable was set externally (not by a previous load_from_file)
                    if self._isolation_enabled and key in self._isolated_vars:
                        # In isolation mode, check if this was set by us vs externally
                        var_source = self._variable_sources.get(key, "")
                        if not var_source.startswith("file:"):
                            # This was set externally (via set() method, not from a file), skip it
                            continue
                    elif not self._isolation_enabled and key in os.environ:
                        # Check if this was set by us (via load_from_file) or externally
                        var_source = self._variable_sources.get(key, "")
                        if not var_source.startswith("file:"):
                            # This was set externally (OS env, not from a file), skip it
                            continue
                    
                    # Skip if exists and not overriding (for non-OS env vars)
                    if not override_existing and self.get(key) is not None:
                        continue
                    
                    # Don't overwrite protected variables
                    if not self.is_protected(key):
                        if self.set(key, value, source):
                            loaded_count += 1
                    
        except Exception as e:
            errors.append(f"Error reading file: {e}")
        
        if loaded_count > 0:
            logger.debug(f"Loaded {loaded_count} variables from {filepath}")
        
        return loaded_count, errors
    
    def get_changes_since_init(self) -> Dict[str, Tuple[Optional[str], str]]:
        """Get all variables that have changed since initialization."""
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
    
    def reset(self) -> None:
        """Reset the environment to initial state."""
        with self._lock:
            self._isolated_vars.clear()
            self._protected_vars.clear()
            self._env_cache.clear()
            self._isolation_enabled = False
            self._bypass_test_defaults = False  # Reset bypass flag
            self._explicitly_cleared_keys.clear()  # Clear explicitly cleared keys
            logger.debug("Environment reset to initial state")
    
    def reset_to_original(self) -> None:
        """Reset environment to original state."""
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
            elif self._original_environ_backup:
                # Fallback to backup
                if self._isolation_enabled:
                    self._isolated_vars = dict(self._original_environ_backup)
                else:
                    os.environ.clear()
                    os.environ.update(self._original_environ_backup)
                logger.info("Environment reset to original state using backup")
            else:
                logger.warning("No original state saved - cannot reset to original")
            
            # Clear tracking
            self._variable_sources.clear()
            self._env_cache.clear()
            self._bypass_test_defaults = False  # Reset bypass flag
            self._explicitly_cleared_keys.clear()  # Clear explicitly cleared keys
    
    def clear_cache(self) -> None:
        """Clear the environment cache."""
        with self._lock:
            self._env_cache.clear()
    
    def enable_test_defaults_bypass(self) -> None:
        """
        Enable bypass of test defaults to prevent configuration pollution.
        
        This method allows tests to explicitly disable built-in test defaults
        to ensure proper isolation between different test scenarios.
        """
        with self._lock:
            self._bypass_test_defaults = True
            logger.debug("Test defaults bypass enabled - built-in test defaults will not be returned")
    
    def disable_test_defaults_bypass(self) -> None:
        """
        Disable bypass of test defaults to restore normal test behavior.
        
        This method restores normal test context behavior where built-in
        test defaults are returned when variables are not explicitly set.
        """
        with self._lock:
            self._bypass_test_defaults = False
            logger.debug("Test defaults bypass disabled - built-in test defaults will be returned in test context")
    
    def complete_reset_for_testing(self) -> None:
        """
        Completely reset the singleton for clean test isolation.
        
        This method resets ALL internal state to ensure no pollution
        between test runs. Only use this in test contexts.
        
        DANGER: This will reset all configuration and should only be used
        in test scenarios where complete clean state is needed.
        """
        with self._lock:
            if not self._is_test_context():
                logger.warning("complete_reset_for_testing called outside test context - this is dangerous!")
            
            # Reset ALL internal state
            self._isolated_vars.clear()
            self._protected_vars.clear()
            self._env_cache.clear()
            self._variable_sources.clear()
            self._change_callbacks.clear()
            self._explicitly_cleared_keys.clear()
            
            # Reset flags
            self._isolation_enabled = False
            self._bypass_test_defaults = False
            
            # Clear original state tracking
            self._original_environ_backup.clear()
            self._original_state = None
            
            logger.debug("Complete singleton reset performed - all state cleared")
    
    def get_all_with_prefix(self, prefix: str) -> Dict[str, str]:
        """Get all environment variables with a specific prefix."""
        result = {}
        
        # Check isolated vars if isolation is enabled
        if self._isolation_enabled:
            for key, value in self._isolated_vars.items():
                if key.startswith(prefix) and value != "__UNSET__":
                    result[key] = value
        
        # Check actual environment
        for key, value in os.environ.items():
            if key.startswith(prefix) and key not in result:
                # Only include if not explicitly unset in isolation mode
                if not (self._isolation_enabled and key in self._isolated_vars and self._isolated_vars[key] == "__UNSET__"):
                    result[key] = value
        
        return result
    
    def get_environment_name(self) -> str:
        """
        Get the current environment name with enhanced GCP project ID detection.
        
        PRIORITY ORDER (Issue #586 Fix):
        1. GCP Cloud Run markers (K_SERVICE, GCP_PROJECT_ID, GOOGLE_CLOUD_PROJECT)
        2. Explicit ENVIRONMENT variable
        3. Test context detection
        4. Safe fallback to staging (not development)
        
        Returns:
            Environment name: 'development', 'test', 'staging', or 'production'
        """
        # PRIORITY 1: Enhanced GCP Project ID Detection (Issue #586 Fix)
        # Check GCP Cloud Run environment markers first for accurate detection
        gcp_project_id = self.get("GCP_PROJECT_ID")
        google_cloud_project = self.get("GOOGLE_CLOUD_PROJECT") 
        k_service = self.get("K_SERVICE")
        
        # GCP Project ID-based detection (most reliable for Cloud Run)
        if gcp_project_id:
            if "production" in gcp_project_id.lower() or "prod" in gcp_project_id.lower():
                return "production"
            elif "staging" in gcp_project_id.lower() or "stage" in gcp_project_id.lower():
                return "staging"
            elif "dev" in gcp_project_id.lower() or "development" in gcp_project_id.lower():
                return "development"
        
        # GOOGLE_CLOUD_PROJECT fallback detection
        if google_cloud_project:
            if "production" in google_cloud_project.lower() or "prod" in google_cloud_project.lower():
                return "production"
            elif "staging" in google_cloud_project.lower() or "stage" in google_cloud_project.lower():
                return "staging"
            elif "dev" in google_cloud_project.lower() or "development" in google_cloud_project.lower():
                return "development"
        
        # K_SERVICE-based detection (Cloud Run service name)
        if k_service:
            if "production" in k_service.lower() or "prod" in k_service.lower():
                return "production"
            elif "staging" in k_service.lower() or "stage" in k_service.lower():
                return "staging"
            elif "dev" in k_service.lower() or "development" in k_service.lower():
                return "development"
        
        # PRIORITY 2: Explicit ENVIRONMENT variable
        explicit_env = self.get("ENVIRONMENT")
        if explicit_env:
            env = explicit_env.lower()
            if env in ["development", "dev", "local"]:
                return "development"
            elif env in ["test", "testing"]:
                return "test"
            elif env == "staging":
                return "staging"
            elif env in ["production", "prod"]:
                return "production"
        
        # PRIORITY 3: Test context detection
        if self._is_test_context():
            return "test"
        
        # PRIORITY 4: Safe fallback (Issue #586 Fix)
        # Default to staging instead of development for safer timeout configurations
        # in Cloud Run environments where detection might fail during cold start
        return "staging"
    
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
    
    def validate_staging_database_credentials(self) -> dict:
        """Validate database credentials specifically for staging environment."""
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
            for var in missing_vars:
                validation_result["issues"].append(f"Missing required staging database variable: {var}")
        
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
        elif postgres_password in ["password", "123456", "admin", "test", "wrong_password"]:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is using insecure default - must be secure for staging")
        elif len(postgres_password) < 8:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is too short (< 8 characters) for staging")
        elif postgres_password.isdigit() and len(postgres_password) < 12:
            validation_result["valid"] = False
            validation_result["issues"].append("POSTGRES_PASSWORD is only numbers and too short - needs complexity")
        
        # Check for development credentials in staging
        if "dev" in postgres_password.lower():
            validation_result["warnings"].append("POSTGRES_PASSWORD contains 'dev' - verify this is not development password")
        
        return validation_result
    
    def _sanitize_value(self, value: str) -> str:
        """Sanitize environment variable value while preserving database credentials."""
        if not isinstance(value, str):
            return str(value)
        
        # Check if this looks like a database URL
        is_database_url = any(proto in value.lower() for proto in ["postgresql://", "mysql://", "sqlite://", "clickhouse://"])
        
        if is_database_url:
            return self._sanitize_database_url(value)
        else:
            return self._sanitize_generic_value(value)
    
    def _sanitize_database_url(self, url: str) -> str:
        """Sanitize database URL while preserving password integrity."""
        try:
            # Parse the URL to handle components separately
            parsed = urlparse(url)
            
            # Sanitize individual components while preserving password integrity
            scheme = self._remove_control_characters(parsed.scheme) if parsed.scheme else ""
            hostname = self._remove_control_characters(parsed.hostname) if parsed.hostname else ""
            username = self._remove_control_characters(parsed.username) if parsed.username else ""
            password = self._sanitize_password_preserving_special_chars(parsed.password) if parsed.password else ""
            port = parsed.port
            path = self._remove_control_characters(parsed.path) if parsed.path else ""
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
            from urllib.parse import urlunparse
            sanitized_url = urlunparse((
                scheme, netloc, path, "", query, ""
            ))
            
            return sanitized_url
            
        except Exception as e:
            logger.warning(f"Database URL sanitization failed, using generic sanitization: {e}")
            return self._sanitize_generic_value(url)
    
    def _sanitize_password_preserving_special_chars(self, password: str) -> str:
        """Sanitize password by removing only control characters, preserving special chars."""
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
        """Remove control characters from string value."""
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
        """Sanitize generic environment variable value."""
        return self._remove_control_characters(value)
    
    def validate_all(self) -> ValidationResult:
        """Validate all environment variables."""
        errors = []
        warnings = []
        missing_optional = []
        
        # Check for required variables
        required_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]
        for var in required_vars:
            if not self.get(var):
                errors.append(f"Missing required variable: {var}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)
    
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


# Singleton instance
_env_instance = IsolatedEnvironment()


def get_env() -> IsolatedEnvironment:
    """Get the singleton IsolatedEnvironment instance.
    
    Enhanced with singleton consistency verification to ensure
    module-level and class-level singletons are always identical.
    """
    global _env_instance
    
    # CRITICAL: Verify singleton consistency
    if IsolatedEnvironment._instance is not None and _env_instance is not IsolatedEnvironment._instance:
        logger.warning(
            f"Singleton inconsistency detected in get_env(): "
            f"_env_instance={id(_env_instance)} != "
            f"IsolatedEnvironment._instance={id(IsolatedEnvironment._instance)}"
        )
        # Force consistency by returning the class instance (which is more authoritative)
        _env_instance = IsolatedEnvironment._instance
        logger.info("Forced singleton consistency in get_env() - updated _env_instance")
    
    return _env_instance


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


# Legacy compatibility functions and classes
def load_secrets() -> bool:
    """Legacy compatibility function for loading secrets."""
    logger.info("load_secrets called - compatibility mode")
    return True


class SecretLoader:
    """Legacy compatibility class for secret loading functionality."""
    
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

    def get_masked_value(self, key: str) -> str:
        """
        Get a masked version of a value for logging purposes.
        
        Args:
            key: Environment variable name
            
        Returns:
            Masked value safe for logging
        """
        value = self.env_manager.get(key, "")
        return _mask_sensitive_value(key, value)


# Legacy compatibility function  
def get_environment_manager(isolation_mode: Optional[bool] = None):
    """Legacy compatibility function for get_environment_manager.
    
    IMPORTANT: This function returns the unified IsolatedEnvironment as the single source of truth.
    The dev_launcher.environment_manager module has been consolidated into shared.isolated_environment.
    """
    # Always use the unified IsolatedEnvironment as single source of truth
    env = get_env()
    if isolation_mode is not None:
        if isolation_mode:
            env.enable_isolation()
        else:
            env.disable_isolation()
    return env


# Backwards Compatibility: EnvironmentValidator class
class EnvironmentValidator:
    """Backwards compatibility wrapper for environment validation functionality."""
    
    
    def validate_all(self) -> ValidationResult:
        """Validate all environment variables."""
        # Basic validation - can be extended
        errors = []
        warnings = []
        missing_optional = []
        
        # Check for required variables
        required_vars = ["DATABASE_URL", "JWT_SECRET_KEY", "SECRET_KEY"]
        for var in required_vars:
            if not self.env.get(var):
                errors.append(f"Missing required variable: {var}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)
    
    def validate_with_fallbacks(self) -> ValidationResult:
        """Enhanced validation with fallback application."""
        return self.validate_all()
    
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
    
    def get_fix_suggestions(self, result: ValidationResult) -> List[str]:
        """Get suggestions for fixing validation issues."""
        suggestions = []
        
        if result.errors:
            suggestions.append("Fix the errors above before starting services")
            suggestions.append("Check your .env file for missing or incorrect values")
        
        return suggestions

    def __init__(self, env: Optional['IsolatedEnvironment'] = None):
        """
        Initialize environment validator with specific environment instance.
        
        Args:
            env: IsolatedEnvironment instance to validate (uses global if None)
        """
        self.env = env or get_env()

    def validate_critical_service_variables(self, service_name: str) -> ValidationResult:
        """
        Validate critical service variables that prevent cascade failures.
        
        Args:
            service_name: Name of service to validate (backend, auth, frontend)
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        missing_optional = []
        
        if service_name == "backend":
            # Critical backend variables from MISSION_CRITICAL_NAMED_VALUES_INDEX.xml
            required_vars = ["SERVICE_SECRET", "SERVICE_ID", "DATABASE_URL", "JWT_SECRET_KEY"]
            for var in required_vars:
                value = self.env.get(var)
                if not value:
                    errors.append(f"CRITICAL: Missing {var} - this will cause {self._get_cascade_impact(var)}")
                elif var == "SERVICE_SECRET" and len(value) < 8:
                    errors.append(f"SERVICE_SECRET too short - must be at least 8 characters to prevent auth failures")
        
        elif service_name == "auth":
            required_vars = ["JWT_SECRET_KEY", "SERVICE_SECRET", "DATABASE_URL"]
            for var in required_vars:
                if not self.env.get(var):
                    errors.append(f"CRITICAL: Missing {var} for auth service")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)

    def validate_service_id_stability(self) -> ValidationResult:
        """
        Validate SERVICE_ID stability requirement to prevent auth failures.
        
        Returns:
            ValidationResult indicating if SERVICE_ID is stable
        """
        errors = []
        warnings = []
        missing_optional = []
        
        service_id = self.env.get("SERVICE_ID", "")
        
        if not service_id:
            errors.append("SERVICE_ID is missing")
        elif "-" in service_id and service_id.count("-") > 1:
            # Check for timestamp patterns (common issue)
            parts = service_id.split("-")
            if len(parts) >= 3 and parts[-1].isdigit() and len(parts[-1]) >= 8:
                errors.append(f"SERVICE_ID '{service_id}' appears to have timestamp suffix - must be stable value 'netra-backend'")
        elif service_id != "netra-backend":
            warnings.append(f"SERVICE_ID is '{service_id}' - verify this matches expected stable value")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)

    def validate_frontend_critical_variables(self) -> ValidationResult:
        """
        Validate critical frontend environment variables.
        
        Returns:
            ValidationResult for frontend configuration
        """
        errors = []
        warnings = []
        missing_optional = []
        
        critical_vars = [
            "NEXT_PUBLIC_API_URL",
            "NEXT_PUBLIC_WS_URL",
            "NEXT_PUBLIC_AUTH_URL", 
            "NEXT_PUBLIC_ENVIRONMENT"
        ]
        
        for var in critical_vars:
            value = self.env.get(var)
            if not value:
                errors.append(f"CRITICAL: Missing {var} - {self._get_frontend_cascade_impact(var)}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)

    def validate_staging_domain_configuration(self) -> ValidationResult:
        """
        Validate staging domain configuration to prevent API connection failures.
        
        Returns:
            ValidationResult for staging domain validation
        """
        errors = []
        warnings = []
        missing_optional = []
        
        environment = self.env.get("ENVIRONMENT", "").lower()
        if environment != "staging":
            return ValidationResult(True, [], [], [])  # Skip if not staging
        
        api_url = self.env.get("NEXT_PUBLIC_API_URL", "")
        ws_url = self.env.get("NEXT_PUBLIC_WS_URL", "")
        auth_url = self.env.get("NEXT_PUBLIC_AUTH_URL", "")
        
        # Check for incorrect staging patterns
        incorrect_patterns = [
            ("localhost", "Localhost URLs not allowed in staging"),
            ("staging.netrasystems.ai", "Should use api.staging.netrasystems.ai subdomain"),
            ("http://", "Should use HTTPS in staging")
        ]
        
        for url, url_name in [(api_url, "API"), (ws_url, "WebSocket"), (auth_url, "Auth")]:
            if url:
                for pattern, message in incorrect_patterns:
                    if pattern in url:
                        errors.append(f"{url_name} URL contains '{pattern}': {message}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)

    def validate_discovery_endpoint_configuration(self, discovery_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate discovery endpoint configuration.
        
        Args:
            discovery_data: Dictionary containing discovery endpoint data
            
        Returns:
            ValidationResult for discovery configuration
        """
        errors = []
        warnings = []
        missing_optional = []
        
        environment = self.env.get("ENVIRONMENT", "").lower()
        
        if environment in ["staging", "production"]:
            # Check for localhost URLs in non-local environments
            for key, url in discovery_data.items():
                if isinstance(url, str) and "localhost" in url:
                    errors.append(f"Discovery endpoint '{key}' contains localhost URL in {environment}: {url}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)

    def validate_environment_specific_behavior(self, env_name: str) -> ValidationResult:
        """
        Validate environment-specific behavior requirements.
        
        Args:
            env_name: Environment name (development, staging, production)
            
        Returns:
            ValidationResult for environment-specific validation
        """
        errors = []
        warnings = []
        missing_optional = []
        
        debug_value = self.env.get("DEBUG", "").lower()
        api_url = self.env.get("NEXT_PUBLIC_API_URL", "")
        
        if env_name == "development":
            if debug_value != "true":
                warnings.append("DEBUG should be 'true' in development")
            if api_url and "localhost" not in api_url:
                warnings.append("Development should typically use localhost URLs")
                
        elif env_name in ["staging", "production"]:
            if debug_value == "true":
                errors.append(f"DEBUG should be 'false' in {env_name}, not 'true'")
            if api_url and "localhost" in api_url:
                errors.append(f"Should not use localhost URLs in {env_name}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, missing_optional)

    def _get_cascade_impact(self, var_name: str) -> str:
        """Get cascade impact description for a variable."""
        impacts = {
            "SERVICE_SECRET": "complete authentication failure and circuit breaker permanent open",
            "SERVICE_ID": "authentication mismatches and service communication failures", 
            "DATABASE_URL": "complete backend failure with no data access",
            "JWT_SECRET_KEY": "token validation failures and authentication breakdown"
        }
        return impacts.get(var_name, "service functionality degradation")

    def _get_frontend_cascade_impact(self, var_name: str) -> str:
        """Get cascade impact description for frontend variables."""
        impacts = {
            "NEXT_PUBLIC_API_URL": "No API calls work, no agents run, no data fetched",
            "NEXT_PUBLIC_WS_URL": "No real-time updates, no agent thinking messages, chat appears frozen",
            "NEXT_PUBLIC_AUTH_URL": "No login, no authentication, users cannot access system",
            "NEXT_PUBLIC_ENVIRONMENT": "Wrong URLs used, staging/production confusion, data corruption"
        }
        return impacts.get(var_name, "frontend functionality failure")


# Backwards compatibility aliases
IsolatedEnv = IsolatedEnvironment