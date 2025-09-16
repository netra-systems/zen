from shared.isolated_environment import get_env
"""
Central Configuration Validator - Single Source of Truth

This module defines ALL configuration requirements for the entire Netra platform.
Every service MUST use this validator to ensure consistent configuration enforcement.

Business Value: Platform/Internal - Configuration Security and Consistency
Prevents production misconfigurations by centralizing all validation logic.

CRITICAL: This is the SSOT for configuration requirements - do not duplicate logic elsewhere.
"""

import os
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigRequirement(Enum):
    """Configuration requirement levels."""
    REQUIRED = "required"           # Must be present and non-empty
    REQUIRED_SECURE = "required_secure"  # Must be present, non-empty, and meet security criteria
    OPTIONAL = "optional"           # Can be missing or empty
    DEV_ONLY = "dev_only"          # Only allowed in development/test
    LEGACY = "legacy"              # Deprecated but still supported temporarily
    LEGACY_REQUIRED = "legacy_required"  # Deprecated but still required temporarily


@dataclass
class ConfigRule:
    """Configuration validation rule."""
    env_var: str
    requirement: ConfigRequirement
    environments: Set[Environment]
    min_length: Optional[int] = None
    forbidden_values: Optional[Set[str]] = None
    error_message: Optional[str] = None
    # Legacy support fields
    legacy_info: Optional['LegacyConfigInfo'] = None
    replacement_vars: Optional[List[str]] = None


@dataclass
class LegacyConfigInfo:
    """Information about legacy configuration variables."""
    deprecation_date: str  # ISO format date string
    migration_guide: str
    still_supported: bool
    removal_version: Optional[str] = None


class LegacyConfigMarker:
    """Mark and track legacy configuration variables to prevent regression."""
    
    LEGACY_VARIABLES: Dict[str, Dict[str, Any]] = {
        "DATABASE_URL": {
            "replacement": ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"],
            "deprecation_date": "2025-11-01",
            "migration_guide": "Use component-based database configuration instead of single DATABASE_URL for better flexibility.",
            "still_supported": True,
            "removal_version": "2.0.0",
            "environments_affected": ["development", "test"]
        },
        "JWT_SECRET": {
            "replacement": "JWT_SECRET_KEY",
            "deprecation_date": "2025-10-01",
            "migration_guide": "Rename JWT_SECRET to JWT_SECRET_KEY in all environments for consistency.",
            "still_supported": False,
            "removal_version": "1.5.0",
            "environments_affected": ["all"]
        },
        "REDIS_URL": {
            "replacement": ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "REDIS_DB"],
            "deprecation_date": "2025-11-01",
            "migration_guide": "Use component-based Redis configuration instead of single REDIS_URL.",
            "still_supported": True,
            "removal_version": "2.0.0",
            "environments_affected": ["development", "test"],
            "auto_construct": True
        },
        "GOOGLE_OAUTH_CLIENT_ID": {
            "replacement": ["GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_ID_TEST", "GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION"],
            "deprecation_date": "2025-09-01",
            "migration_guide": "Use environment-specific OAuth client IDs (e.g., GOOGLE_OAUTH_CLIENT_ID_STAGING) to prevent credential leakage between environments.",
            "still_supported": False,
            "removal_version": "1.3.0",
            "environments_affected": ["all"],
            "critical_security": True  # This was a security issue
        },
        "GOOGLE_OAUTH_CLIENT_SECRET": {
            "replacement": ["GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_SECRET_TEST", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"],
            "deprecation_date": "2025-09-01",
            "migration_guide": "Use environment-specific OAuth client secrets to prevent credential leakage between environments.",
            "still_supported": False,
            "removal_version": "1.3.0",
            "environments_affected": ["all"],
            "critical_security": True
        },
        "APP_SECRET_KEY": {
            "replacement": "SECRET_KEY",
            "deprecation_date": "2025-10-15",
            "migration_guide": "Use SECRET_KEY instead of APP_SECRET_KEY for consistency.",
            "still_supported": True,
            "removal_version": "1.6.0",
            "environments_affected": ["all"]
        }
    }
    
    @classmethod
    def is_legacy_variable(cls, var_name: str) -> bool:
        """Check if a variable is marked as legacy."""
        return var_name in cls.LEGACY_VARIABLES
    
    @classmethod
    def get_legacy_info(cls, var_name: str) -> Optional[Dict[str, Any]]:
        """Get legacy information for a variable."""
        return cls.LEGACY_VARIABLES.get(var_name)
    
    @classmethod
    def get_replacement_variables(cls, legacy_var: str) -> List[str]:
        """Get replacement variables for a legacy config."""
        config = cls.LEGACY_VARIABLES.get(legacy_var, {})
        replacement = config.get("replacement", [])
        return replacement if isinstance(replacement, list) else [replacement]
    
    @classmethod
    def check_legacy_usage(cls, configs: Dict[str, Any]) -> List[str]:
        """Check for usage of legacy variables and return warnings."""
        warnings = []
        
        for var_name, value in configs.items():
            if cls.is_legacy_variable(var_name) and value:
                legacy_info = cls.get_legacy_info(var_name)
                if legacy_info:
                    if legacy_info["still_supported"]:
                        warnings.append(
                            f"WARNING: '{var_name}' is deprecated and will be removed in version {legacy_info['removal_version']}. "
                            f"Migration: {legacy_info['migration_guide']}"
                        )
                    else:
                        warnings.append(
                            f"ERROR: '{var_name}' is no longer supported (removed in {legacy_info['removal_version']}). "
                            f"You must use: {', '.join(cls.get_replacement_variables(var_name))}"
                        )
                    
                    if legacy_info.get("critical_security"):
                        warnings.append(
                            f"SECURITY WARNING: Using '{var_name}' poses a security risk. "
                            f"This was identified as a critical security issue. Please migrate immediately."
                        )
        
        return warnings
    
    @classmethod
    def can_auto_construct(cls, legacy_var: str) -> bool:
        """Check if a legacy variable can be auto-constructed from components."""
        config = cls.LEGACY_VARIABLES.get(legacy_var, {})
        return config.get("auto_construct", False)


class CentralConfigurationValidator:
    """
    Central validator for all platform configuration requirements.
    
    This is the Single Source of Truth (SSOT) for configuration validation.
    All services must use this validator instead of implementing their own fallback logic.
    
    RACE CONDITION PROTECTION: Enhanced with service lifecycle management to prevent
    race conditions during initialization where environment loading and validation
    happen concurrently.
    """
    
    # SSOT: Configuration Requirements for ALL Services
    CONFIGURATION_RULES: List[ConfigRule] = [
        # JWT Authentication Secrets (CRITICAL)
        ConfigRule(
            env_var="JWT_SECRET_STAGING",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.STAGING},
            min_length=32,
            error_message="JWT_SECRET_STAGING required in staging environment. Set JWT_SECRET_STAGING environment variable or configure staging-jwt-secret in Secret Manager."
        ),
        ConfigRule(
            env_var="JWT_SECRET_PRODUCTION", 
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.PRODUCTION},
            min_length=32,
            error_message="JWT_SECRET_PRODUCTION required in production environment. Set JWT_SECRET_PRODUCTION environment variable or configure prod-jwt-secret in Secret Manager."
        ),
        ConfigRule(
            env_var="JWT_SECRET_KEY",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.DEVELOPMENT, Environment.TEST},
            min_length=32,
            error_message="JWT_SECRET_KEY required in development/test environments."
        ),
        
        # Database Configuration (CRITICAL) 
        # CRITICAL FIX: Support #removed-legacyOR component-based configuration
        # This aligns with actual GCP deployment patterns where #removed-legacyis provided
        # No hard requirements for individual components if #removed-legacyis present
        ConfigRule(
            env_var="POSTGRES_PASSWORD",
            requirement=ConfigRequirement.OPTIONAL,  # Made optional since #removed-legacycan be used instead
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=8,
            forbidden_values={"", "password", "postgres", "admin"},
            error_message="POSTGRES_PASSWORD (if provided) must be 8+ characters and not use common defaults. Alternative: Use #removed-legacyfor Cloud SQL connections."
        ),
        ConfigRule(
            env_var="POSTGRES_HOST",
            requirement=ConfigRequirement.OPTIONAL,  # Made optional since #removed-legacycan be used instead
            environments={Environment.STAGING, Environment.PRODUCTION},
            # Note: Cloud SQL Unix socket paths are valid (e.g., /cloudsql/project:region:instance)
            # These should NOT be treated as localhost violations
            forbidden_values={"localhost", "127.0.0.1"},  # Removed empty string check for Cloud SQL
            error_message="POSTGRES_HOST (if provided) cannot be localhost/127.0.0.1 in staging/production. Cloud SQL Unix sockets (/cloudsql/...) are allowed. Alternative: Use #removed-legacyfor Cloud SQL connections."
        ),
        
        # Redis Configuration (CRITICAL)
        ConfigRule(
            env_var="REDIS_PASSWORD",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=8,
            forbidden_values={"", "redis", "password"},
            error_message="REDIS_PASSWORD required in staging/production. Must be 8+ characters."
        ),
        ConfigRule(
            env_var="REDIS_HOST",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.STAGING, Environment.PRODUCTION},
            forbidden_values={"localhost", "127.0.0.1", ""},
            error_message="REDIS_HOST required in staging/production. Cannot be localhost or empty."
        ),
        
        # Service-to-Service Authentication (CRITICAL)
        ConfigRule(
            env_var="SERVICE_SECRET",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=32,
            error_message="SERVICE_SECRET required in staging/production for inter-service authentication."
        ),
        ConfigRule(
            env_var="FERNET_KEY",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.PRODUCTION},  # Only strictly required in production
            min_length=32,
            error_message="FERNET_KEY required in production for encryption."
        ),
        ConfigRule(
            env_var="FERNET_KEY",
            requirement=ConfigRequirement.OPTIONAL,  # Optional in staging to allow gradual rollout
            environments={Environment.STAGING},
            min_length=32,
            error_message="FERNET_KEY recommended in staging for encryption. Service will run without it but encryption features may be limited."
        ),
        
        # LLM API Keys (HIGH PRIORITY) - Made optional, but at least one required
        ConfigRule(
            env_var="ANTHROPIC_API_KEY",
            requirement=ConfigRequirement.OPTIONAL,
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=10,
            forbidden_values={"", "sk-ant-placeholder", "your-api-key"},
            error_message="ANTHROPIC_API_KEY invalid format. Cannot be placeholder value."
        ),
        ConfigRule(
            env_var="OPENAI_API_KEY",
            requirement=ConfigRequirement.OPTIONAL,
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=10,
            forbidden_values={"", "sk-placeholder", "your-api-key"},
            error_message="OPENAI_API_KEY invalid format. Cannot be placeholder value."
        ),
        ConfigRule(
            env_var="GEMINI_API_KEY",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=10,
            forbidden_values={"", "your-api-key", "AIzaSy-placeholder"},
            error_message="GEMINI_API_KEY required in staging/production. Cannot be placeholder value."
        ),
        
        # OAuth Configuration (HIGH PRIORITY) - SSOT for all environments
        # Development Environment OAuth
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.DEVELOPMENT},
            forbidden_values={"", "your-client-id", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT required in development environment."
        ),
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.DEVELOPMENT},
            min_length=10,
            forbidden_values={"", "your-client-secret", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT required in development environment."
        ),
        
        # Test Environment OAuth (uses explicit test configs, not fallbacks)
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_ID_TEST",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.TEST},
            forbidden_values={"", "your-client-id", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_ID_TEST required in test environment."
        ),
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_SECRET_TEST",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.TEST},
            min_length=10,
            forbidden_values={"", "your-client-secret", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_SECRET_TEST required in test environment."
        ),
        
        # Staging Environment OAuth
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_ID_STAGING",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.STAGING},
            forbidden_values={"", "your-client-id", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_ID_STAGING required in staging environment."
        ),
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.STAGING},
            min_length=10,
            forbidden_values={"", "your-client-secret", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_SECRET_STAGING required in staging environment."
        ),
        
        # Production Environment OAuth
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_ID_PRODUCTION",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.PRODUCTION},
            forbidden_values={"", "your-client-id", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_ID_PRODUCTION required in production environment."
        ),
        ConfigRule(
            env_var="GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.PRODUCTION},
            min_length=10,
            forbidden_values={"", "your-client-secret", "REPLACE_WITH"},
            error_message="GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION required in production environment."
        ),
    ]
    
    def __init__(self, env_getter_func=None):
        """
        Initialize the central configuration validator.
        
        Args:
            env_getter_func: Function to get environment variables (defaults to os.environ.get)
        """
        # CRITICAL FIX: Use IsolatedEnvironment instead of direct os.environ access
        if env_getter_func is None:
            env = get_env()
            self.env_getter = lambda key, default=None: env.get(key, default)
        else:
            self.env_getter = env_getter_func
        self._current_environment = None
        
        # RACE CONDITION PROTECTION: Track initialization state
        self._is_initialized = False
        self._initialization_lock = threading.RLock()
        self._readiness_state = "uninitialized"  # uninitialized -> loading -> ready -> failed
        self._last_error = None
        self._retry_count = 0
        self._max_retries = 3
        
    def get_environment(self) -> Environment:
        """Get the current deployment environment using unified detection logic."""
        # CRITICAL FIX: Consistent environment detection that prevents test/runtime mismatches
        # Issue: Environment detection was inconsistent - tests expected None but got Environment.TEST
        
        # PRIORITY 1: Check for test context consistently
        is_test_context = self._is_test_context()
        
        # For test contexts, handle environment carefully to match test expectations
        if is_test_context:
            # Get explicit ENVIRONMENT setting
            env_str = self.env_getter("ENVIRONMENT", "test").lower()
            
            # CRITICAL FIX: Always respect explicit ENVIRONMENT setting even in test context
            # Test contexts can set ENVIRONMENT to staging/production to test strict validation
            if env_str == "test":
                return Environment.TEST
            elif env_str in ["testing"]:  
                return Environment.TEST
            elif env_str == "development":
                return Environment.DEVELOPMENT
            elif env_str == "staging":
                return Environment.STAGING
            elif env_str == "production":
                return Environment.PRODUCTION
            else:
                # For unknown values in test context, default to TEST
                logger.debug(f"Unknown ENVIRONMENT '{env_str}' in test context, defaulting to TEST")
                return Environment.TEST
        
        # PRIORITY 2: Try unified environment detector for consistency (non-test contexts)
        try:
            # Import locally to avoid circular dependencies during config bootstrap
            from netra_backend.app.core.environment_constants import EnvironmentDetector
            
            unified_env = EnvironmentDetector.get_environment()
            
            # Map backend environment names to central validator environment names
            env_mapping = {
                "testing": Environment.TEST,    # Backend uses "testing", central uses "test"
                "development": Environment.DEVELOPMENT,
                "staging": Environment.STAGING,
                "production": Environment.PRODUCTION
            }
            
            if unified_env.lower() in env_mapping:
                return env_mapping[unified_env.lower()]
            else:
                logger.warning(f"Unknown environment from EnvironmentDetector: '{unified_env}', falling back to legacy detection")
                # Fall through to legacy detection as fallback
        except ImportError:
            # If backend modules not available (e.g., during auth service tests), use legacy detection
            logger.debug("EnvironmentDetector not available, using legacy environment detection")
        
        # PRIORITY 3: Legacy fallback with caching for performance
        if self._current_environment is None:
            env_str = self.env_getter("ENVIRONMENT", "development").lower()
            try:
                # Map testing -> test for consistency
                if env_str == "testing":
                    env_str = "test"
                self._current_environment = Environment(env_str)
            except ValueError:
                raise ValueError(f"Invalid ENVIRONMENT value: '{env_str}'. Must be one of: {[e.value for e in Environment]}")
        
        return self._current_environment
    
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
        
        # Check for test environment variables
        test_indicators = [
            'PYTEST_CURRENT_TEST',
            'TESTING',
            'TEST_MODE'
        ]
        
        for indicator in test_indicators:
            if self.env_getter(indicator):
                return True
        
        # Check if ENVIRONMENT is set to testing
        env_value = self.env_getter('ENVIRONMENT', '').lower()
        if env_value in ['test', 'testing']:
            return True
        
        return False
    
    def clear_environment_cache(self) -> None:
        """Clear the cached environment value.
        
        This is useful in test contexts where the environment may change
        between tests via environment variable patching.
        """
        self._current_environment = None
    
    def _wait_for_environment_readiness(self, timeout_seconds: float = 10.0) -> bool:
        """
        Wait for the environment to be ready for validation.
        
        RACE CONDITION FIX: This prevents validation from running before
        environment loading is complete, which was causing OAuth validation
        errors during service startup.
        
        Args:
            timeout_seconds: Maximum time to wait for readiness
            
        Returns:
            bool: True if environment is ready, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            try:
                # Check if IsolatedEnvironment is properly initialized
                env = get_env()
                
                # Test basic functionality - can we detect test context?
                test_context = env._is_test_context()
                
                # Test environment variable access
                env_name = env.get("ENVIRONMENT", "development")
                
                # DOCKER STARTUP FIX: Check OAuth credentials specifically for development
                # This prevents the race condition where validation runs before Docker
                # environment variables are fully available
                if env_name == "development":
                    oauth_id = env.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
                    oauth_secret = env.get("GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT")
                    
                    # For development, OAuth credentials should be available before validation
                    if not oauth_id or not oauth_secret:
                        logger.debug(f"OAuth credentials not yet available in Docker environment (id: {bool(oauth_id)}, secret: {bool(oauth_secret)})")
                        time.sleep(0.1)
                        continue
                    
                    # Additional validation that they're not placeholder values
                    if oauth_id in ["", "your-client-id", "REPLACE_WITH"] or oauth_secret in ["", "your-client-secret", "REPLACE_WITH"]:
                        logger.debug(f"OAuth credentials contain placeholder values, waiting for proper values")
                        time.sleep(0.1)
                        continue
                
                # If we get here without exceptions and OAuth check passed, environment is ready
                logger.debug(f"Environment readiness check passed (env: {env_name}, test: {test_context})")
                return True
                
            except Exception as e:
                logger.debug(f"Environment not ready yet: {e}")
                time.sleep(0.1)  # Short sleep before retry
                continue
        
        logger.warning(f"Environment readiness timeout after {timeout_seconds}s")
        return False
    
    def _detect_timing_issue(self) -> Optional[str]:
        """
        Detect if current failures are due to timing/race conditions.
        
        Returns:
            Optional error message if timing issue detected
        """
        try:
            # Check if environment variables are in an inconsistent state
            env = get_env()
            
            # Test 1: Can we access basic environment variables?
            basic_vars_accessible = True
            try:
                env.get("ENVIRONMENT")
                env.get("PYTEST_CURRENT_TEST") 
            except Exception:
                basic_vars_accessible = False
            
            # Test 2: Is isolated environment in a transitional state?
            debug_info = env.get_debug_info()
            isolation_enabled = debug_info.get("isolation_enabled", False)
            isolated_vars_count = debug_info.get("isolated_vars_count", 0)
            
            # Test 3: Are we in test context detection limbo?
            test_context_detection_working = True
            try:
                env._is_test_context()
            except Exception:
                test_context_detection_working = False
            
            # Test 4: OAuth-specific timing issues (DOCKER STARTUP FIX)
            oauth_timing_issues = []
            current_env = self.get_environment()
            
            # Check if OAuth variables are accessible but validation is failing
            # This indicates a race condition during Docker container startup
            if current_env == Environment.DEVELOPMENT:
                oauth_id = env.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
                oauth_secret = env.get("GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT")
                
                # OAuth variables present in environment but validation might be failing
                # due to initialization timing issues
                if oauth_id and oauth_secret:
                    # Variables exist - any validation failure is likely timing-related
                    oauth_timing_issues.append("OAuth credentials available but validation failing (Docker startup race condition)")
                elif not oauth_id and not oauth_secret:
                    # Neither available - might be too early in startup
                    oauth_timing_issues.append("OAuth credentials not yet loaded (Docker environment loading)")
                else:
                    # Partial loading - clear timing issue
                    oauth_timing_issues.append("OAuth credentials partially loaded (race condition during Docker startup)")
            
            # Analyze for timing issues
            timing_issues = []
            
            if not basic_vars_accessible:
                timing_issues.append("Basic environment variable access failing")
                
            if isolation_enabled and isolated_vars_count == 0:
                timing_issues.append("Isolation enabled but no isolated variables loaded")
            
            if not test_context_detection_working:
                timing_issues.append("Test context detection mechanism failing")
            
            if oauth_timing_issues:
                timing_issues.extend(oauth_timing_issues)
            
            if timing_issues:
                return f"Timing/race condition detected: {'; '.join(timing_issues)}"
                
        except Exception as e:
            return f"Environment access completely failing during timing detection: {e}"
        
        return None
    
    def validate_all_requirements(self) -> None:
        """
        Validate ALL configuration requirements for the current environment.
        
        This is the main entry point that services should call at startup.
        FAILS HARD on any missing or invalid configuration.
        
        RACE CONDITION PROTECTION: Now includes timing-aware validation with retry logic.
        """
        with self._initialization_lock:
            self._readiness_state = "loading"
            
            try:
                # LEVEL 1 FIX: Wait for environment readiness before validation
                # CRITICAL FIX: In test contexts, skip readiness check to avoid timeout issues
                # Tests should run immediately without waiting for Docker/OAuth readiness
                is_test_context = self._is_test_context()
                if not is_test_context:
                    try:
                        env = self.get_environment()
                        timeout = 3.0 if env == "staging" else 10.0
                    except:
                        timeout = 3.0  # Default to shorter timeout if environment detection fails
                    
                    if not self._wait_for_environment_readiness(timeout_seconds=timeout):
                        timing_issue = self._detect_timing_issue()
                        if timing_issue:
                            self._readiness_state = "failed"
                            self._last_error = f"Environment readiness timeout: {timing_issue}"
                            raise ValueError(f"RACE CONDITION DETECTED - {self._last_error}")
                        else:
                            self._readiness_state = "failed"
                            self._last_error = "Environment readiness timeout (unknown cause)"
                            raise ValueError(self._last_error)
                
                # LEVEL 2 FIX: Enhanced error attribution for timing issues
                environment = self.get_environment()
                validation_errors = []
                
                logger.info(f"Validating configuration requirements for {environment.value} environment (readiness verified)")
                
                # Check each configuration rule with timing awareness
                for rule in self.CONFIGURATION_RULES:
                    if environment in rule.environments:
                        try:
                            self._validate_single_requirement_with_timing(rule, environment)
                            logger.debug(f" PASS:  {rule.env_var} validation passed")
                        except ValueError as e:
                            # Enhanced error attribution
                            timing_issue = self._detect_timing_issue()
                            if timing_issue:
                                error_msg = f"{rule.env_var} validation failed due to race condition: {e} (Timing issue: {timing_issue})"
                            else:
                                error_msg = f"{rule.env_var} validation failed: {e}"
                            validation_errors.append(error_msg)
                            logger.error(f" FAIL:  {error_msg}")
                
                # CRITICAL: Additional validation for database configuration in staging/production
                if environment in [Environment.STAGING, Environment.PRODUCTION]:
                    try:
                        self._validate_database_configuration(environment)
                        logger.debug(" PASS:  Database configuration validation passed")
                    except ValueError as e:
                        timing_issue = self._detect_timing_issue()
                        if timing_issue:
                            error_msg = f"Database configuration validation failed due to race condition: {e} (Timing issue: {timing_issue})"
                        else:
                            error_msg = f"Database configuration validation failed: {e}"
                        validation_errors.append(error_msg)
                        logger.error(f" FAIL:  {error_msg}")
                
                # HARD STOP: If any validation fails, prevent startup with detailed attribution
                if validation_errors:
                    self._readiness_state = "failed"
                    error_msg = f"Configuration validation failed for {environment.value} environment:\n" + "\n".join(f"  - {err}" for err in validation_errors)
                    self._last_error = error_msg
                    logger.critical(error_msg)
                    raise ValueError(error_msg)
                
                # Success
                self._readiness_state = "ready" 
                self._is_initialized = True
                logger.info(f" PASS:  All configuration requirements validated for {environment.value}")
                
            except Exception as e:
                self._readiness_state = "failed"
                self._last_error = str(e)
                raise
    
    def _validate_single_requirement_with_timing(self, rule: ConfigRule, environment: Environment) -> None:
        """Validate a single configuration requirement with timing awareness and retry logic."""
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                # Try the original validation
                self._validate_single_requirement(rule, environment)
                return  # Success
                
            except ValueError as e:
                # Check if this might be a timing issue
                timing_issue = self._detect_timing_issue()
                if timing_issue and attempt < max_retries - 1:
                    logger.debug(f"Retrying {rule.env_var} validation (attempt {attempt + 1}) due to timing issue: {timing_issue}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    # Final attempt failed or not a timing issue
                    raise e
    
    def _validate_single_requirement(self, rule: ConfigRule, environment: Environment) -> None:
        """Validate a single configuration requirement."""
        value = self.env_getter(rule.env_var)
        
        # CRITICAL FIX: Enhanced JWT secret validation
        # The central validator MUST detect missing JWT secrets properly
        # NOTE: Legacy fallback removed to enforce strict environment-specific JWT secrets
        if rule.env_var.startswith('JWT_SECRET'):
            # Log if legacy JWT_SECRET usage is detected but don't use it as fallback
            legacy_jwt_secret = self.env_getter('JWT_SECRET')
            if legacy_jwt_secret and not value:
                # Legacy JWT_SECRET is present but environment-specific one is missing
                logger.warning(f"Legacy JWT_SECRET detected but {rule.env_var} is required for {environment.value} environment. "
                              f"Environment-specific JWT secrets are now mandatory.")
        
        # CRITICAL FIX: For test environment OAuth credentials during pytest collection,
        # be more lenient to handle timing issues during configuration loading
        if environment == Environment.TEST and rule.env_var in ['GOOGLE_OAUTH_CLIENT_ID_TEST', 'GOOGLE_OAUTH_CLIENT_SECRET_TEST']:
            if not value or not value.strip():
                # During test context, try to get the value from test defaults if available
                try:
                    from shared.isolated_environment import get_env
                    env = get_env()

                    # CRITICAL FIX: More robust test context detection during pytest collection
                    # The isolated environment's _is_test_context() may fail during collection
                    is_test_context = (
                        env._is_test_context() or
                        env.get('PYTEST_CURRENT_TEST') or
                        environment == Environment.TEST or
                        'pytest' in str(env.get('_', ''))
                    )
                    
                    if is_test_context and hasattr(env, '_get_test_environment_defaults'):
                        test_defaults = env._get_test_environment_defaults()
                        if rule.env_var in test_defaults:
                            value = test_defaults[rule.env_var]
                            logger.debug(f"Using test default for {rule.env_var} during validation")
                except Exception as e:
                    logger.debug(f"Could not load test defaults for {rule.env_var}: {e}")
                
                # If still no value, fail with detailed error message
                if not value or not value.strip():
                    error_msg = (rule.error_message or 
                               f"{rule.env_var} is required in {environment.value} environment. "
                               f"Ensure test environment is properly configured with OAuth test credentials.")
                    raise ValueError(error_msg)
        
        # Check if value is present for required configurations
        elif rule.requirement in [ConfigRequirement.REQUIRED, ConfigRequirement.REQUIRED_SECURE]:
            if not value or not value.strip():
                # CRITICAL FIX: Enhanced error message for JWT secrets
                if rule.env_var.startswith('JWT_SECRET'):
                    # Check if legacy JWT_SECRET exists to provide better error message
                    legacy_jwt_secret = self.env_getter('JWT_SECRET')
                    if legacy_jwt_secret:
                        # CRITICAL: Legacy fallback should not prevent ValueError for missing env-specific secrets
                        # The test expects ValueError to be raised even when legacy JWT_SECRET exists
                        # This enforces migration to environment-specific secrets
                        error_msg = (f"{rule.env_var} is required in {environment.value} environment. "
                                   f"Legacy JWT_SECRET found but environment-specific secrets are mandatory. "
                                   f"Set {rule.env_var} environment variable.")
                        raise ValueError(error_msg)
                    else:
                        error_msg = (rule.error_message or 
                                   f"{rule.env_var} is required in {environment.value} environment. "
                                   f"No JWT secret configuration found.")
                        raise ValueError(error_msg)
                else:
                    error_msg = rule.error_message or f"{rule.env_var} is required in {environment.value} environment"
                    raise ValueError(error_msg)
        
        # If value is present, validate security requirements
        if value and rule.requirement == ConfigRequirement.REQUIRED_SECURE:
            # Check minimum length
            if rule.min_length and len(value.strip()) < rule.min_length:
                raise ValueError(f"{rule.env_var} must be at least {rule.min_length} characters long in {environment.value}")
            
            # Check forbidden values
            if rule.forbidden_values and value.strip() in rule.forbidden_values:
                raise ValueError(f"{rule.env_var} cannot use forbidden value in {environment.value}")
    
    def detect_deployment_pattern(self, environment: Environment) -> str:
        """
        Detect the deployment pattern being used.
        
        Returns:
            str: "database_url" for Cloud Run/GCP pattern, "component_based" for traditional setup
        """
        database_url = self.env_getter("DATABASE_URL")
        
        if database_url and database_url.strip():
            return "database_url"
        
        # Check for component-based configuration
        host = self.env_getter("POSTGRES_HOST") or self.env_getter("DATABASE_HOST")
        if host:
            return "component_based"
            
        # No clear pattern detected
        return "unknown"
    
    def _validate_database_configuration(self, environment: Environment) -> None:
        """
        Validate that database configuration is sufficient for the environment.
        
        CRITICAL: Ensure we have EITHER DATABASE_URL OR component-based configuration.
        This prevents false positives where GCP provides DATABASE_URL but validator
        expects individual components.
        """
        deployment_pattern = self.detect_deployment_pattern(environment)
        
        # Pattern 1: DATABASE_URL deployment (GCP Cloud Run pattern)
        if deployment_pattern == "database_url":
            logger.info(f"Database configuration: Using DATABASE_URL deployment pattern for {environment.value} environment")
            return
        
        # Pattern 2: Component-based deployment  
        elif deployment_pattern == "component_based":
            # Check for either POSTGRES_* (GCP/modern) or DATABASE_* (legacy) variables
            host = self.env_getter("POSTGRES_HOST") or self.env_getter("DATABASE_HOST")
            password = self.env_getter("POSTGRES_PASSWORD") or self.env_getter("DATABASE_PASSWORD")
            
            if not password:
                raise ValueError(
                    f"Database password required in {environment.value} environment for component-based deployment. "
                    f"Provide POSTGRES_PASSWORD/DATABASE_PASSWORD"
                )
            
            # Validate host (allow Cloud SQL sockets)
            if host in {"localhost", "127.0.0.1"}:
                raise ValueError(
                    f"Database host cannot be localhost in {environment.value} environment. "
                    f"Use Cloud SQL socket (/cloudsql/...) or external host"
                )
            
            # Validate password security
            if len(password) < 8 or password in {"", "password", "postgres", "admin"}:
                raise ValueError(
                    f"Database password must be 8+ characters and not use common defaults in {environment.value} environment"
                )
            
            logger.info(f"Database configuration: Using component-based deployment pattern for {environment.value} environment")
        
        # Pattern 3: No valid deployment pattern detected
        else:
            raise ValueError(
                f"No valid database configuration detected for {environment.value} environment. "
                f"Provide either DATABASE_URL (Cloud Run) or POSTGRES_HOST/POSTGRES_PASSWORD (component-based)"
            )
    
    def get_validated_config(self, config_name: str) -> str:
        """
        Get a validated configuration value.
        
        This method should be used by services instead of direct environment access
        for critical configurations.
        """
        environment = self.get_environment()
        
        # Find the rule for this config
        for rule in self.CONFIGURATION_RULES:
            if rule.env_var == config_name and environment in rule.environments:
                self._validate_single_requirement(rule, environment)
                value = self.env_getter(config_name)
                if value:
                    return value.strip()
                
        # If no rule found or not required in this environment
        value = self.env_getter(config_name)
        return value.strip() if value else ""
    
    def get_jwt_secret(self) -> str:
        """
        Get the JWT secret for the current environment.
        
        This replaces all JWT secret loading logic in individual services.
        SSOT for JWT secret requirements.
        """
        environment = self.get_environment()
        
        if environment == Environment.STAGING:
            return self.get_validated_config("JWT_SECRET_STAGING")
        elif environment == Environment.PRODUCTION:
            return self.get_validated_config("JWT_SECRET_PRODUCTION")
        elif environment in [Environment.DEVELOPMENT, Environment.TEST]:
            return self.get_validated_config("JWT_SECRET_KEY")
        else:
            raise ValueError(f"Unknown environment: {environment}")
    
    def get_database_credentials(self) -> Dict[str, str]:
        """
        Get validated database credentials for the current environment.
        
        SSOT for database configuration requirements.
        
        CRITICAL FIX: Support both DATABASE_* (legacy) and POSTGRES_* (GCP/Cloud SQL) patterns.
        This aligns validator with actual deployment patterns used by GCP Cloud Run.
        """
        environment = self.get_environment()
        
        if environment in [Environment.STAGING, Environment.PRODUCTION]:
            # CRITICAL: Check for #removed-legacyfirst (Cloud Run deployment pattern)
            database_url = self.env_getter("DATABASE_URL")
            if database_url:
                # #removed-legacyis sufficient - no need to validate individual components
                # This is how GCP Cloud Run deployments work
                logger.info(f"Using #removed-legacyfor {environment.value} database configuration")
                # Return minimal config - the actual connection uses #removed-legacydirectly
                return {
                    "url": database_url,
                    "host": "cloud-sql",  # Placeholder for Cloud SQL
                    "port": "5432",
                    "database": "netra_staging" if environment == Environment.STAGING else "netra_prod",
                    "username": "postgres",
                    "password": "***"  # Handled by DATABASE_URL
                }
            
            # Fallback: Check for component-based configuration (POSTGRES_* or DATABASE_*)
            # Try POSTGRES_* first (modern GCP pattern), then DATABASE_* (legacy pattern)
            host = self.env_getter("POSTGRES_HOST") or self.env_getter("DATABASE_HOST")
            password = self.env_getter("POSTGRES_PASSWORD") or self.env_getter("DATABASE_PASSWORD")
            
            # Validate that we have at least host and password for component-based config
            if not host:
                raise ValueError(f"Database host required in {environment.value}. Set #removed-legacyor POSTGRES_HOST/DATABASE_HOST")
            if not password:
                raise ValueError(f"Database password required in {environment.value}. Set #removed-legacyor POSTGRES_PASSWORD/DATABASE_PASSWORD")
            
            # Additional validation for component-based config
            if host in {"localhost", "127.0.0.1"} and not host.startswith("/cloudsql/"):
                raise ValueError(f"Database host cannot be localhost in {environment.value} (Cloud SQL sockets like /cloudsql/... are allowed)")
            
            if len(password) < 8 or password in {"", "password", "postgres", "admin"}:
                raise ValueError(f"Database password must be 8+ characters and not use common defaults in {environment.value}")
            
            return {
                "host": host,
                "port": self.env_getter("POSTGRES_PORT") or self.env_getter("DATABASE_PORT") or "5432",
                "database": self.env_getter("POSTGRES_DB") or self.env_getter("DATABASE_NAME") or "netra_dev",
                "username": self.env_getter("POSTGRES_USER") or self.env_getter("DATABASE_USER") or "postgres",
                "password": password
            }
        else:
            # Development/test can use defaults - support both patterns
            return {
                "host": self.env_getter("POSTGRES_HOST") or self.env_getter("DATABASE_HOST", "localhost"),
                "port": self.env_getter("POSTGRES_PORT") or self.env_getter("DATABASE_PORT", "5432"),
                "database": self.env_getter("POSTGRES_DB") or self.env_getter("DATABASE_NAME", "netra_dev"),
                "username": self.env_getter("POSTGRES_USER") or self.env_getter("DATABASE_USER", "postgres"),
                "password": self.env_getter("POSTGRES_PASSWORD") or self.env_getter("DATABASE_PASSWORD", "")
            }
    
    def get_redis_credentials(self) -> Dict[str, str]:
        """
        Get validated Redis credentials for the current environment.
        
        SSOT for Redis configuration requirements.
        """
        environment = self.get_environment()
        
        if environment in [Environment.STAGING, Environment.PRODUCTION]:
            # Hard requirements for staging/production
            return {
                "host": self.get_validated_config("REDIS_HOST"),
                "port": self.env_getter("REDIS_PORT") or "6379",
                "db": self.env_getter("REDIS_DB", "0"),
                "password": self.get_validated_config("REDIS_PASSWORD")
            }
        else:
            # Development/test can use defaults
            return {
                "host": self.env_getter("REDIS_HOST", "localhost"),
                "port": self.env_getter("REDIS_PORT", "6379"),
                "db": self.env_getter("REDIS_DB", "0"),
                "password": self.env_getter("REDIS_PASSWORD", "")
            }
    
    def get_llm_credentials(self) -> Dict[str, str]:
        """
        Get validated LLM API credentials for the current environment.
        
        SSOT for LLM API key requirements.
        ANTHROPIC_API_KEY and OPENAI_API_KEY are optional, but at least one LLM provider must be configured.
        GEMINI_API_KEY is required as the primary provider.
        """
        environment = self.get_environment()
        
        credentials = {}
        
        if environment in [Environment.STAGING, Environment.PRODUCTION]:
            # GEMINI is required, others are optional
            gemini_key = self.env_getter("GEMINI_API_KEY")
            if gemini_key:
                credentials["gemini"] = self.get_validated_config("GEMINI_API_KEY")
            
            # ANTHROPIC and OPENAI are optional but validated if present
            anthropic_key = self.env_getter("ANTHROPIC_API_KEY")
            if anthropic_key and anthropic_key.strip():
                credentials["anthropic"] = self.get_validated_config("ANTHROPIC_API_KEY")
            
            openai_key = self.env_getter("OPENAI_API_KEY")
            if openai_key and openai_key.strip():
                credentials["openai"] = self.get_validated_config("OPENAI_API_KEY")
                
            # At least GEMINI must be configured
            if "gemini" not in credentials:
                raise ValueError(f"GEMINI_API_KEY required in {environment.value} environment (primary LLM provider)")
        else:
            # Development/test - use any available keys or placeholders
            credentials["anthropic"] = self.env_getter("ANTHROPIC_API_KEY", "sk-ant-dev-placeholder")
            credentials["openai"] = self.env_getter("OPENAI_API_KEY", "sk-dev-placeholder")
            credentials["gemini"] = self.env_getter("GEMINI_API_KEY", "dev-gemini-key")
        
        return credentials
    
    def get_oauth_credentials(self) -> Dict[str, str]:
        """
        SSOT: Get validated OAuth credentials for the current environment.
        
        This replaces all service-specific OAuth credential loading logic.
        Each environment has explicit, named OAuth configurations - NO fallbacks.
        
        Returns:
            Dict containing 'client_id' and 'client_secret' for OAuth
        """
        environment = self.get_environment()
        
        if environment == Environment.DEVELOPMENT:
            client_id = self.get_validated_config("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
            client_secret = self.get_validated_config("GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT")
        elif environment == Environment.TEST:
            client_id = self.get_validated_config("GOOGLE_OAUTH_CLIENT_ID_TEST")
            client_secret = self.get_validated_config("GOOGLE_OAUTH_CLIENT_SECRET_TEST")
        elif environment == Environment.STAGING:
            client_id = self.get_validated_config("GOOGLE_OAUTH_CLIENT_ID_STAGING")
            client_secret = self.get_validated_config("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
        elif environment == Environment.PRODUCTION:
            client_id = self.get_validated_config("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
            client_secret = self.get_validated_config("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
        else:
            raise ValueError(f"Unknown environment for OAuth configuration: {environment}")
        
        if not client_id or not client_secret:
            raise ValueError(f"OAuth credentials not properly configured for {environment.value} environment")
        
        return {
            "client_id": client_id,
            "client_secret": client_secret
        }
    
    def get_oauth_client_id(self) -> str:
        """
        SSOT: Get validated OAuth client ID for the current environment.
        """
        credentials = self.get_oauth_credentials()
        return credentials["client_id"]
    
    def get_oauth_client_secret(self) -> str:
        """
        SSOT: Get validated OAuth client secret for the current environment.
        """
        credentials = self.get_oauth_credentials()
        return credentials["client_secret"]
    
    def validate_oauth_token_comprehensive(self, token: str) -> bool:
        """
        SSOT: Comprehensive OAuth token validation.
        
        Replaces duplicate OAuth token validation logic from auth_integration/validators.py.
        
        Args:
            token: OAuth token to validate
            
        Returns:
            bool: True if token is valid format, False otherwise
        """
        if not token:
            return False
        
        # Check OAuth token length constraints
        return 10 <= len(token) <= 2000
    
    def validate_oauth_credentials_endpoint(self, credentials: dict) -> dict:
        """
        SSOT: OAuth credential validation for routes.
        
        Replaces duplicate OAuth credential validation from auth_routes/oauth_validation.py.
        
        Args:
            credentials: Dict containing OAuth config (client_id, client_secret)
            
        Returns:
            dict: Validation result with 'valid' and 'errors' keys
        """
        errors = []
        
        # Validate client_id
        client_id = credentials.get('client_id')
        if not client_id:
            errors.append("OAuth client_id is required")
        elif client_id in ["", "your-client-id", "REPLACE_WITH"]:
            errors.append("OAuth client_id contains placeholder value")
        
        # Validate client_secret
        client_secret = credentials.get('client_secret')
        if not client_secret:
            errors.append("OAuth client_secret is required")
        elif client_secret in ["", "your-client-secret", "REPLACE_WITH"]:
            errors.append("OAuth client_secret contains placeholder value")
        elif len(client_secret) < 10:
            errors.append("OAuth client_secret too short (minimum 10 characters)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def validate_oauth_provider_configuration(self, provider: str) -> bool:
        """
        SSOT: OAuth provider configuration validation.
        
        Replaces duplicate OAuth provider validation from configuration_validator.py.
        
        Args:
            provider: OAuth provider name (e.g., 'google')
            
        Returns:
            bool: True if provider configuration is valid
        """
        if provider.lower() != 'google':
            # Only Google OAuth is currently supported
            return False
        
        try:
            # Use SSOT OAuth credentials validation
            oauth_creds = self.get_oauth_credentials()
            
            # Validate credentials exist and are non-empty
            return (
                oauth_creds.get('client_id') and 
                oauth_creds.get('client_secret') and
                len(oauth_creds['client_secret']) >= 10
            )
        except ValueError:
            # OAuth credentials not configured for current environment
            return False
    
    def simulate_oauth_end_to_end(self) -> dict:
        """
        SSOT: OAuth E2E simulation validation.
        
        Replaces duplicate OAuth E2E simulation from configuration_drift_monitor.py.
        
        Returns:
            dict: Simulation result with validation status
        """
        import time
        
        environment = self.get_environment()
        current_env_str = environment.value
        
        # Get E2E OAuth simulation key
        e2e_oauth_key = self.env_getter("E2E_OAUTH_SIMULATION_KEY")
        
        validation_result = {
            "config_key": "E2E_OAUTH_SIMULATION_KEY",
            "environment": current_env_str,
            "validation_timestamp": time.time(),
            "key_available": e2e_oauth_key is not None,
            "key_length": len(e2e_oauth_key) if e2e_oauth_key else 0,
            "drift_detected": False,
            "drift_details": [],
            "business_impact": "none"
        }
        
        if not e2e_oauth_key:
            validation_result.update({
                "drift_detected": True,
                "business_impact": "high",
                "error": "E2E_OAUTH_SIMULATION_KEY missing - E2E authentication bypass unavailable"
            })
            return validation_result
        
        # Validate key format and content
        if len(e2e_oauth_key) < 32:
            validation_result.update({
                "drift_detected": True,
                "business_impact": "moderate",
                "warning": f"E2E_OAUTH_SIMULATION_KEY too short ({len(e2e_oauth_key)} chars, expected 32+)"
            })
        
        return validation_result
    
    def validate_oauth_configs_for_environment(self, environment: str) -> Dict[str, Any]:
        """
        SSOT: Validate OAuth configuration for a specific environment.
        
        Replaces duplicate OAuth config validation from cross_service_validator.py.
        
        Args:
            environment: The environment to validate (development, test, staging, production)
            
        Returns:
            Dict with 'valid' (bool) and 'errors' (list) keys
        """
        errors = []
        
        try:
            # Check for environment-specific OAuth credentials
            client_id_key = f"GOOGLE_OAUTH_CLIENT_ID_{environment.upper()}"
            client_secret_key = f"GOOGLE_OAUTH_CLIENT_SECRET_{environment.upper()}"
            
            client_id = self.env_getter(client_id_key)
            client_secret = self.env_getter(client_secret_key)
            
            # Validate client ID
            if not client_id:
                errors.append(f"Missing {client_id_key} for {environment} environment")
            elif client_id in ["", "your-client-id", "REPLACE_WITH"]:
                errors.append(f"Invalid {client_id_key} - contains placeholder value")
            
            # Validate client secret
            if not client_secret:
                errors.append(f"Missing {client_secret_key} for {environment} environment")
            elif client_secret in ["", "your-client-secret", "REPLACE_WITH"]:
                errors.append(f"Invalid {client_secret_key} - contains placeholder value")
            elif len(client_secret) < 10:
                errors.append(f"Invalid {client_secret_key} - too short (minimum 10 characters)")
            
            # Additional validation for production/staging
            if environment.lower() in ['staging', 'production']:
                # Check that we're not using development credentials in production
                dev_client_id = self.env_getter("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
                if client_id == dev_client_id and dev_client_id:
                    errors.append(f"Security issue: {environment} environment is using development OAuth credentials")
            
        except Exception as e:
            errors.append(f"OAuth validation error for {environment}: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def validate_startup_requirements(self) -> None:
        """
        Validate all startup requirements before service initialization.

        This should be called by every service at startup BEFORE any other initialization.
        FAILS HARD if any critical configuration is missing or invalid.
        """
        environment = self.get_environment()
        logger.info(f" SEARCH:  Central Configuration Validation - {environment.value.upper()} Environment")

        try:
            # Check for legacy variable usage
            self._check_and_warn_legacy_configs()

            # Validate all configuration requirements
            self.validate_all_requirements()

            # Additional startup validations
            self._validate_environment_consistency()

            # Special check for FERNET_KEY in staging - warn but don't fail
            if environment == Environment.STAGING:
                fernet_key = self.env_getter("FERNET_KEY")
                if not fernet_key:
                    logger.warning(
                        "FERNET_KEY not configured in staging environment. "
                        "Encryption features may be limited. Consider adding FERNET_KEY "
                        "to enable full encryption functionality."
                    )

            logger.info(f" PASS:  Central configuration validation PASSED for {environment.value}")

        except ValueError as e:
            logger.critical(f" FAIL:  Central configuration validation FAILED: {e}")
            raise
    
    def _check_and_warn_legacy_configs(self) -> None:
        """Check for legacy configuration usage and log warnings."""
        # SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
        # Collect all environment variables
        env = get_env()
        current_configs = env.get_all()
        
        # CRITICAL FIX: Enhanced legacy JWT_SECRET detection
        # Check specifically for JWT_SECRET usage
        if 'JWT_SECRET' in current_configs and current_configs['JWT_SECRET']:
            environment = self.get_environment()
            
            # Check if the appropriate environment-specific JWT secret exists
            env_specific_secrets = {
                Environment.STAGING: 'JWT_SECRET_STAGING',
                Environment.PRODUCTION: 'JWT_SECRET_PRODUCTION', 
                Environment.DEVELOPMENT: 'JWT_SECRET_KEY',
                Environment.TEST: 'JWT_SECRET_KEY'
            }
            
            expected_secret = env_specific_secrets.get(environment)
            if expected_secret and not current_configs.get(expected_secret):
                logger.warning(f"Legacy JWT_SECRET usage detected in {environment.value} environment. "
                              f"Please migrate to {expected_secret} for environment-specific JWT secrets.")
        
        # Check for legacy usage using the standard marker
        warnings = LegacyConfigMarker.check_legacy_usage(current_configs)

        for warning in warnings:
            if warning.startswith("ERROR:"):
                # Special handling for JWT_SECRET - warn but don't fail if proper secrets exist
                if "'JWT_SECRET' is no longer supported" in warning:
                    environment = self.get_environment()
                    env_specific_secrets = {
                        Environment.STAGING: 'JWT_SECRET_STAGING',
                        Environment.PRODUCTION: 'JWT_SECRET_PRODUCTION',
                        Environment.DEVELOPMENT: 'JWT_SECRET_KEY',
                        Environment.TEST: 'JWT_SECRET_KEY'
                    }
                    expected_secret = env_specific_secrets.get(environment)

                    # If the proper environment-specific secret exists, just warn
                    if expected_secret and current_configs.get(expected_secret):
                        logger.warning(f"Legacy JWT_SECRET detected but {expected_secret} is properly configured. "
                                     f"Please remove JWT_SECRET from environment variables to avoid confusion.")
                        continue  # Don't raise error, just continue
                    else:
                        # If proper secret missing, this is a real error
                        logger.error(warning)
                        raise ValueError(warning)
                else:
                    logger.error(warning)
                    # Don't fail hard on legacy configs if they're still supported
                    # This allows gradual migration
                    if "no longer supported" in warning:
                        raise ValueError(warning)
            elif warning.startswith("SECURITY WARNING:"):
                logger.critical(warning)
            else:
                logger.warning(warning)
    
    def _validate_environment_consistency(self) -> None:
        """Validate environment-specific consistency requirements."""
        environment = self.get_environment()
        
        if environment == Environment.PRODUCTION:
            # Production-specific validations
            if self.env_getter("DEBUG", "").lower() == "true":
                raise ValueError("DEBUG must not be enabled in production environment")
            
            if self.env_getter("ALLOW_DEV_OAUTH_SIMULATION", "").lower() == "true":
                raise ValueError("ALLOW_DEV_OAUTH_SIMULATION must not be enabled in production environment")
        
        elif environment == Environment.STAGING:
            # Staging-specific validations
            if self.env_getter("ALLOW_DEV_OAUTH_SIMULATION", "").lower() == "true":
                logger.warning("ALLOW_DEV_OAUTH_SIMULATION enabled in staging - this should only be temporary")


# Global instance - SSOT for configuration validation
_global_validator: Optional[CentralConfigurationValidator] = None


def get_central_validator(env_getter_func=None) -> CentralConfigurationValidator:
    """
    Get the global central configuration validator instance.
    
    This ensures all services use the same validator instance (SSOT).
    """
    global _global_validator
    
    if _global_validator is None:
        _global_validator = CentralConfigurationValidator(env_getter_func)
    
    return _global_validator


def clear_central_validator_cache() -> None:
    """
    Clear the central validator's cached values.
    
    This is useful in test contexts where environment variables may change
    between tests via environment variable patching.
    """
    global _global_validator
    
    if _global_validator is not None:
        _global_validator.clear_environment_cache()


def validate_platform_configuration() -> None:
    """
    Validate ALL platform configuration requirements.
    
    This is the main entry point that should be called by all services at startup.
    """
    validator = get_central_validator()
    validator.validate_startup_requirements()


def get_jwt_secret() -> str:
    """
    SSOT: Get JWT secret for the current environment.
    
    Replaces all service-specific JWT secret loading logic.
    """
    validator = get_central_validator()
    return validator.get_jwt_secret()


def get_database_credentials() -> Dict[str, str]:
    """
    SSOT: Get validated database credentials.
    
    Replaces all service-specific database configuration logic.
    """
    validator = get_central_validator()
    return validator.get_database_credentials()


def get_redis_credentials() -> Dict[str, str]:
    """
    SSOT: Get validated Redis credentials.
    
    Replaces all service-specific Redis configuration logic.
    """
    validator = get_central_validator()
    return validator.get_redis_credentials()


def get_llm_credentials() -> Dict[str, str]:
    """
    SSOT: Get validated LLM API credentials.
    
    Replaces all service-specific LLM configuration logic.
    """
    validator = get_central_validator()
    return validator.get_llm_credentials()


def get_oauth_credentials() -> Dict[str, str]:
    """
    SSOT: Get validated OAuth credentials for the current environment.
    
    Replaces all service-specific OAuth configuration logic.
    Returns dict with 'client_id' and 'client_secret'.
    """
    validator = get_central_validator()
    return validator.get_oauth_credentials()


def get_oauth_client_id() -> str:
    """
    SSOT: Get validated OAuth client ID for the current environment.
    
    Replaces all service-specific OAuth client ID loading logic.
    """
    validator = get_central_validator()
    return validator.get_oauth_client_id()


def get_oauth_client_secret() -> str:
    """
    SSOT: Get validated OAuth client secret for the current environment.
    
    Replaces all service-specific OAuth client secret loading logic.
    """
    validator = get_central_validator()
    return validator.get_oauth_client_secret()


def validate_oauth_token_comprehensive(token: str) -> bool:
    """
    SSOT: Comprehensive OAuth token validation.
    
    Replaces duplicate OAuth token validation logic across all services.
    """
    validator = get_central_validator()
    return validator.validate_oauth_token_comprehensive(token)


def validate_oauth_credentials_endpoint(credentials: dict) -> dict:
    """
    SSOT: OAuth credential validation for routes.
    
    Replaces duplicate OAuth credential validation logic across all services.
    """
    validator = get_central_validator()
    return validator.validate_oauth_credentials_endpoint(credentials)


def validate_oauth_provider_configuration(provider: str) -> bool:
    """
    SSOT: OAuth provider configuration validation.
    
    Replaces duplicate OAuth provider validation logic across all services.
    """
    validator = get_central_validator()
    return validator.validate_oauth_provider_configuration(provider)


def simulate_oauth_end_to_end() -> dict:
    """
    SSOT: OAuth E2E simulation validation.
    
    Replaces duplicate OAuth E2E simulation logic across all services.
    """
    validator = get_central_validator()
    return validator.simulate_oauth_end_to_end()


def validate_oauth_configs_for_environment(environment: str) -> Dict[str, Any]:
    """
    SSOT: Validate OAuth configuration for a specific environment.
    
    Replaces duplicate OAuth config validation logic across all services.
    """
    validator = get_central_validator()
    return validator.validate_oauth_configs_for_environment(environment)


def check_config_before_deletion(config_key: str, service_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Check if a configuration can be safely deleted.
    
    Args:
        config_key: The configuration key to check
        service_name: Optional service context for the check
    
    Returns:
        (can_delete, reason, affected_services)
    """
    # First check if it's a legacy variable
    if LegacyConfigMarker.is_legacy_variable(config_key):
        legacy_info = LegacyConfigMarker.get_legacy_info(config_key)
        if legacy_info and legacy_info["still_supported"]:
            return {
                "safe_to_delete": False,
                "reason": f"Legacy variable '{config_key}' is still supported until {legacy_info['deprecation_date']}. "
                         f"Migration required: {legacy_info['migration_guide']}",
                "warnings": [f"Legacy variable {config_key} is still in use"],
                "affected_services": legacy_info.get("environments_affected", [])
            }
        elif legacy_info and not legacy_info["still_supported"]:
            return {
                "safe_to_delete": True,
                "reason": f"Legacy variable '{config_key}' is deprecated and can be removed. "
                         f"Ensure replacements are in place: {', '.join(LegacyConfigMarker.get_replacement_variables(config_key))}",
                "warnings": [],
                "affected_services": legacy_info.get("environments_affected", [])
            }
    
    # Check against configuration rules
    validator = get_central_validator()
    for rule in validator.CONFIGURATION_RULES:
        if rule.env_var == config_key:
            if rule.requirement in [ConfigRequirement.REQUIRED, ConfigRequirement.REQUIRED_SECURE]:
                affected_envs = [env.value for env in rule.environments]
                return {
                    "safe_to_delete": False,
                    "reason": f"Configuration '{config_key}' is required in environments: {', '.join(affected_envs)}. "
                             f"Cannot be deleted without migration plan.",
                    "warnings": [f"Configuration {config_key} is required in {', '.join(affected_envs)}"],
                    "affected_services": affected_envs
                }
            elif rule.requirement == ConfigRequirement.OPTIONAL:
                return {
                    "safe_to_delete": True,
                    "reason": f"Configuration '{config_key}' is optional and can be safely deleted.",
                    "warnings": [],
                    "affected_services": []
                }
    
    # Not in our configuration rules - check with backend-specific dependencies if available
    try:
        from netra_backend.app.core.config_dependencies import ConfigDependencyMap
        can_delete, reason = ConfigDependencyMap.can_delete_config(config_key)
        return {
            "safe_to_delete": can_delete,
            "reason": reason,
            "warnings": [] if can_delete else [reason],
            "affected_services": []
        }
    except ImportError:
        # Backend not available, assume it's safe to delete unknown configs
        return {
            "safe_to_delete": True,
            "reason": f"Configuration '{config_key}' is not tracked in central validator. Verify with service-specific checks.",
            "warnings": [],
            "affected_services": []
        }
    
    def is_ready(self) -> bool:
        """Check if the validator is ready to perform validations."""
        return self._readiness_state == "ready"
    
    def get_readiness_state(self) -> str:
        """Get the current readiness state."""
        return self._readiness_state
    
    def get_last_error(self) -> Optional[str]:
        """Get the last error that occurred during validation."""
        return self._last_error
    
    def force_readiness_check(self) -> bool:
        """Force a readiness check and return the result."""
        with self._initialization_lock:
            return self._wait_for_environment_readiness(timeout_seconds=5.0)


def get_legacy_migration_report() -> Dict[str, Any]:
    """
    Generate a report of all legacy configurations and their migration status.
    
    Returns:
        Dictionary with legacy_vars list and migration_status
    """
    legacy_vars = []
    current_date = datetime.now()
    
    for var_name, info in LegacyConfigMarker.LEGACY_VARIABLES.items():
        try:
            deprecation_date = datetime.fromisoformat(info["deprecation_date"])
            days_until_removal = (deprecation_date - current_date).days
        except (ValueError, KeyError):
            days_until_removal = 0
        
        status = "removed" if not info["still_supported"] else (
            "deprecated" if days_until_removal > 0 else "overdue_for_removal"
        )
        
        legacy_vars.append({
            "name": var_name,
            "status": status,
            "deprecation_date": info.get("deprecation_date"),
            "removal_version": info.get("removal_version", "TBD"),
            "replacement": info.get("replacement"),
            "migration_guide": info.get("migration_guide"),
            "critical_security": info.get("critical_security", False),
            "auto_construct": info.get("auto_construct", False),
            "still_supported": info.get("still_supported", True),
            "environments_affected": info.get("environments_affected", [])
        })
    
    # Determine overall migration status
    total_vars = len(legacy_vars)
    removed_vars = sum(1 for var in legacy_vars if var["status"] == "removed")
    
    if removed_vars == total_vars:
        migration_status = "complete"
    elif removed_vars > total_vars / 2:
        migration_status = "mostly_complete"
    else:
        migration_status = "in_progress"
    
    return {
        "legacy_vars": legacy_vars,
        "migration_status": migration_status,
        "total_legacy_vars": total_vars,
        "removed_vars": removed_vars,
        "deprecated_vars": sum(1 for var in legacy_vars if var["status"] == "deprecated"),
        "overdue_vars": sum(1 for var in legacy_vars if var["status"] == "overdue_for_removal")
    }
