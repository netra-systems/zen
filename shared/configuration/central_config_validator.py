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
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass

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


@dataclass
class ConfigRule:
    """Configuration validation rule."""
    env_var: str
    requirement: ConfigRequirement
    environments: Set[Environment]
    min_length: Optional[int] = None
    forbidden_values: Optional[Set[str]] = None
    error_message: Optional[str] = None


class CentralConfigurationValidator:
    """
    Central validator for all platform configuration requirements.
    
    This is the Single Source of Truth (SSOT) for configuration validation.
    All services must use this validator instead of implementing their own fallback logic.
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
        ConfigRule(
            env_var="DATABASE_PASSWORD",
            requirement=ConfigRequirement.REQUIRED_SECURE,
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=8,
            forbidden_values={"", "password", "postgres", "admin"},
            error_message="DATABASE_PASSWORD required in staging/production. Must be 8+ characters and not use common defaults."
        ),
        ConfigRule(
            env_var="DATABASE_HOST",
            requirement=ConfigRequirement.REQUIRED,
            environments={Environment.STAGING, Environment.PRODUCTION},
            forbidden_values={"localhost", "127.0.0.1", ""},
            error_message="DATABASE_HOST required in staging/production. Cannot be localhost or empty."
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
            environments={Environment.STAGING, Environment.PRODUCTION},
            min_length=32,
            error_message="FERNET_KEY required in staging/production for encryption."
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
        
        # OAuth Configuration (HIGH PRIORITY)
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
    ]
    
    def __init__(self, env_getter_func=None):
        """
        Initialize the central configuration validator.
        
        Args:
            env_getter_func: Function to get environment variables (defaults to os.environ.get)
        """
        self.env_getter = env_getter_func or (lambda key, default=None: os.environ.get(key, default))
        self._current_environment = None
        
    def get_environment(self) -> Environment:
        """Get the current deployment environment."""
        if self._current_environment is None:
            env_str = self.env_getter("ENVIRONMENT", "development").lower()
            try:
                self._current_environment = Environment(env_str)
            except ValueError:
                raise ValueError(f"Invalid ENVIRONMENT value: '{env_str}'. Must be one of: {[e.value for e in Environment]}")
        
        return self._current_environment
    
    def validate_all_requirements(self) -> None:
        """
        Validate ALL configuration requirements for the current environment.
        
        This is the main entry point that services should call at startup.
        FAILS HARD on any missing or invalid configuration.
        """
        environment = self.get_environment()
        validation_errors = []
        
        logger.info(f"Validating configuration requirements for {environment.value} environment")
        
        # Check each configuration rule
        for rule in self.CONFIGURATION_RULES:
            if environment in rule.environments:
                try:
                    self._validate_single_requirement(rule, environment)
                    logger.debug(f"✅ {rule.env_var} validation passed")
                except ValueError as e:
                    validation_errors.append(str(e))
                    logger.error(f"❌ {rule.env_var} validation failed: {e}")
        
        # HARD STOP: If any validation fails, prevent startup
        if validation_errors:
            error_msg = f"Configuration validation failed for {environment.value} environment:\n" + "\n".join(f"  - {err}" for err in validation_errors)
            logger.critical(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"✅ All configuration requirements validated for {environment.value}")
    
    def _validate_single_requirement(self, rule: ConfigRule, environment: Environment) -> None:
        """Validate a single configuration requirement."""
        value = self.env_getter(rule.env_var)
        
        # Check if value is present
        if rule.requirement in [ConfigRequirement.REQUIRED, ConfigRequirement.REQUIRED_SECURE]:
            if not value or not value.strip():
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
        """
        environment = self.get_environment()
        
        if environment in [Environment.STAGING, Environment.PRODUCTION]:
            # Hard requirements for staging/production
            return {
                "host": self.get_validated_config("DATABASE_HOST"),
                "port": self.env_getter("DATABASE_PORT") or "5432",
                "database": self.env_getter("DATABASE_NAME") or "netra_dev",
                "username": self.env_getter("DATABASE_USER") or "postgres",
                "password": self.get_validated_config("DATABASE_PASSWORD")
            }
        else:
            # Development/test can use defaults
            return {
                "host": self.env_getter("DATABASE_HOST", "localhost"),
                "port": self.env_getter("DATABASE_PORT", "5432"),
                "database": self.env_getter("DATABASE_NAME", "netra_dev"),
                "username": self.env_getter("DATABASE_USER", "postgres"),
                "password": self.env_getter("DATABASE_PASSWORD", "")
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
    
    def validate_startup_requirements(self) -> None:
        """
        Validate all startup requirements before service initialization.
        
        This should be called by every service at startup BEFORE any other initialization.
        FAILS HARD if any critical configuration is missing or invalid.
        """
        environment = self.get_environment()
        logger.info(f"🔍 Central Configuration Validation - {environment.value.upper()} Environment")
        
        try:
            # Validate all configuration requirements
            self.validate_all_requirements()
            
            # Additional startup validations
            self._validate_environment_consistency()
            
            logger.info(f"✅ Central configuration validation PASSED for {environment.value}")
            
        except ValueError as e:
            logger.critical(f"❌ Central configuration validation FAILED: {e}")
            raise
    
    def _validate_environment_consistency(self) -> None:
        """Validate environment-specific consistency requirements."""
        environment = self.get_environment()
        
        if environment == Environment.PRODUCTION:
            # Production-specific validations
            if self.env_getter("DEBUG", "").lower() == "true":
                raise ValueError("DEBUG must not be enabled in production environment")
            
            if self.env_getter("ALLOW_DEV_AUTH_BYPASS", "").lower() == "true":
                raise ValueError("ALLOW_DEV_AUTH_BYPASS must not be enabled in production environment")
        
        elif environment == Environment.STAGING:
            # Staging-specific validations
            if self.env_getter("ALLOW_DEV_AUTH_BYPASS", "").lower() == "true":
                logger.warning("ALLOW_DEV_AUTH_BYPASS enabled in staging - this should only be temporary")


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