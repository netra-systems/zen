"""
Configuration Validation System for Netra Backend.

Provides comprehensive configuration validation with:
- Environment variable validation and type checking
- Required vs optional variable classification
- Format validation and pattern matching
- Case-insensitive lookups and normalization
- Default value fallbacks with inheritance
- Clear, actionable error messages with suggested fixes

Business Value Justification (BVJ):
- Segment: Platform/Internal (All deployment environments)
- Business Goal: Operational Excellence & Risk Reduction
- Value Impact: Prevents configuration-related service failures and security vulnerabilities
- Revenue Impact: Configuration errors cause deployment failures and security breaches that threaten entire platform
"""
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Union
from urllib.parse import urlparse
import json

from shared.isolated_environment import get_env
from netra_backend.app.core.exceptions_config import ConfigurationError, ValidationError
from netra_backend.app.core.unified_logging import get_logger


class ConfigType(Enum):
    """Configuration value types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    URL = "url"
    PATH = "path"
    EMAIL = "email"
    JSON = "json"
    LIST = "list"
    SECRET = "secret"
    PORT = "port"
    HOST = "host"


class ValidationSeverity(Enum):
    """Validation error severity levels."""
    ERROR = "error"      # Blocks startup
    WARNING = "warning"  # Allows startup with degradation
    INFO = "info"        # Informational only


@dataclass
class ValidationRule:
    """Configuration validation rule."""
    name: str
    config_type: ConfigType
    required: bool = True
    default: Any = None
    pattern: Optional[Pattern] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    choices: Optional[List[str]] = None
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""
    example: str = ""
    severity: ValidationSeverity = ValidationSeverity.ERROR
    depends_on: List[str] = field(default_factory=list)
    mutually_exclusive: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Compile regex patterns."""
        if isinstance(self.pattern, str):
            self.pattern = re.compile(self.pattern)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    variable: str
    value: Any
    success: bool
    severity: ValidationSeverity
    error_message: Optional[str] = None
    suggestion: Optional[str] = None
    used_default: bool = False
    
    @property
    def is_blocking(self) -> bool:
        """Check if this result blocks startup."""
        return not self.success and self.severity == ValidationSeverity.ERROR


@dataclass
class ConfigurationReport:
    """Comprehensive configuration validation report."""
    total_variables: int
    validated_count: int
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    info: List[ValidationResult]
    missing_required: List[str]
    using_defaults: List[str]
    security_issues: List[ValidationResult]
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is valid for startup."""
        return len(self.errors) == 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if configuration has warnings."""
        return len(self.warnings) > 0
    
    @property
    def summary(self) -> str:
        """Get validation summary."""
        return (
            f"Config validation: {self.validated_count}/{self.total_variables} variables - "
            f"{len(self.errors)} errors, {len(self.warnings)} warnings"
        )


class ConfigurationValidator:
    """
    Comprehensive configuration validation system.
    
    Features:
    - Type-safe validation with detailed error reporting
    - Environment-specific rule sets
    - Security validation for sensitive values
    - Default value management with inheritance
    - Case-insensitive environment variable lookup
    - Dependency validation between variables
    - Format validation with regex patterns
    - OAuth validation delegation to SSOT
    """
    
    def __init__(self, environment: str = "development"):
        self.logger = get_logger(__name__)
        self.environment = environment.lower()
        
        # Configuration rules registry
        self.rules: Dict[str, ValidationRule] = {}
        self.case_mapping: Dict[str, str] = {}  # lowercase -> actual name
        
        # Environment-specific configurations
        self.environment_defaults: Dict[str, Dict[str, Any]] = {}
        
        # Security patterns
        self.secret_patterns = [
            re.compile(r'.*(?:password|secret|key|token).*', re.IGNORECASE),
            re.compile(r'.*(?:api_key|apikey|auth).*', re.IGNORECASE),
            re.compile(r'.*(?:private|credential).*', re.IGNORECASE)
        ]
        
        # Common validation patterns
        self.patterns = {
            'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            'url': re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.IGNORECASE),
            'host': re.compile(r'^[a-zA-Z0-9.-]+$'),
            'port': re.compile(r'^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$')
        }
        
        self.logger.info("ConfigurationValidator initialized", extra={
            "environment": environment
        })
        
        # Register default rules
        self._register_default_rules()
    
    def _get_central_validator(self):
        """Get central SSOT validator instance."""
        if self._central_validator is None:
            try:
                from shared.configuration.central_config_validator import get_central_validator
                self._central_validator = get_central_validator()
            except ImportError as e:
                self.logger.warning(f"Central SSOT validator not available: {e}")
                self._central_validator = None
        return self._central_validator
    
    # =============================================================================
    # OAuth Validation Methods - FACADE PATTERN (Delegates to SSOT)
    # =============================================================================
    
    def validate_oauth_configuration(self) -> bool:
        """
        Validate OAuth configuration using SSOT delegation.
        
        This method delegates OAuth validation to the central SSOT validator.
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT OAuth provider validation
                return central_validator.validate_oauth_provider_configuration('google')
            else:
                # Fallback validation
                env = get_env()
                oauth_id = env.get(f"GOOGLE_OAUTH_CLIENT_ID_{self.environment.upper()}")
                oauth_secret = env.get(f"GOOGLE_OAUTH_CLIENT_SECRET_{self.environment.upper()}")
                return bool(oauth_id and oauth_secret)
        except Exception as e:
            self.logger.error(f"OAuth configuration validation failed: {e}")
            return False
    
    def validate_oauth(self) -> Dict[str, Any]:
        """
        Validate OAuth credentials using SSOT delegation.
        
        Returns:
            Dict with validation results
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Get OAuth credentials from SSOT
                oauth_creds = central_validator.get_oauth_credentials()
                
                # Use SSOT credential validation
                validation_result = central_validator.validate_oauth_credentials_endpoint(oauth_creds)
                
                return {
                    'oauth_valid': validation_result['valid'],
                    'errors': validation_result.get('errors', [])
                }
            else:
                # Fallback validation
                env = get_env()
                oauth_id = env.get(f"GOOGLE_OAUTH_CLIENT_ID_{self.environment.upper()}")
                oauth_secret = env.get(f"GOOGLE_OAUTH_CLIENT_SECRET_{self.environment.upper()}")
                
                if not oauth_id or not oauth_secret:
                    return {'oauth_valid': False, 'errors': ['OAuth credentials missing']}
                
                return {'oauth_valid': True, 'errors': []}
                
        except Exception as e:
            self.logger.error(f"OAuth validation failed: {e}")
            return {'oauth_valid': False, 'errors': [str(e)]}
    
    def validate_oauth_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate OAuth credentials using SSOT delegation.
        
        Args:
            credentials: OAuth credentials to validate
            
        Returns:
            Dict with validation results
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT OAuth credential validation
                return central_validator.validate_oauth_credentials_endpoint(credentials)
            else:
                # Fallback validation
                errors = []
                
                client_id = credentials.get('client_id')
                if not client_id:
                    errors.append("OAuth client_id is required")
                elif client_id in ["", "your-client-id", "REPLACE_WITH"]:
                    errors.append("OAuth client_id contains placeholder value")
                
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
                
        except Exception as e:
            self.logger.error(f"OAuth credential validation failed: {e}")
            return {"valid": False, "errors": [str(e)]}
    
    def get_oauth_credentials(self) -> Dict[str, str]:
        """
        Get validated OAuth credentials using SSOT delegation.
        
        Returns:
            Dict containing OAuth credentials
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT OAuth credential retrieval
                return central_validator.get_oauth_credentials()
            else:
                # Fallback credential retrieval
                env = get_env()
                client_id = env.get(f"GOOGLE_OAUTH_CLIENT_ID_{self.environment.upper()}")
                client_secret = env.get(f"GOOGLE_OAUTH_CLIENT_SECRET_{self.environment.upper()}")
                
                if not client_id or not client_secret:
                    raise ValueError(f"OAuth credentials not configured for {self.environment} environment")
                
                return {
                    "client_id": client_id,
                    "client_secret": client_secret
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get OAuth credentials: {e}")
            raise
    
    def validate_jwt(self) -> bool:
        """
        Validate JWT configuration using SSOT delegation.
        
        Returns:
            bool: True if JWT configuration is valid
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT JWT validation
                return central_validator.validate_jwt_configuration()
            else:
                # Fallback JWT validation
                env = get_env()
                jwt_secret = env.get("JWT_SECRET_KEY")
                return bool(jwt_secret and len(jwt_secret) >= 32)
        except Exception as e:
            self.logger.error(f"JWT validation failed: {e}")
            return False
    
    def validate_database(self) -> bool:
        """
        Validate database configuration using SSOT delegation.
        
        Returns:
            bool: True if database configuration is valid
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT database validation
                return central_validator.validate_database_configuration()
            else:
                # Fallback database validation
                env = get_env()
                db_url = env.get("DATABASE_URL")
                db_host = env.get("POSTGRES_HOST") or env.get("DATABASE_HOST")
                return bool(db_url or db_host)
        except Exception as e:
            self.logger.error(f"Database validation failed: {e}")
            return False
    
    def get_environment(self) -> str:
        """
        Get current environment using SSOT delegation.
        
        Returns:
            str: Current environment name
        """
        try:
            central_validator = self._get_central_validator()
            if central_validator:
                # Use SSOT environment detection
                return central_validator.get_current_environment()
            else:
                # Fallback environment detection
                return self.environment
        except Exception as e:
            self.logger.error(f"Environment detection failed: {e}")
            return self.environment
    
    def register_rule(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        self.rules[rule.name] = rule
        self.case_mapping[rule.name.lower()] = rule.name
        
        self.logger.debug("Validation rule registered", extra={
            "rule": rule.name,
            "type": rule.config_type.value,
            "required": rule.required,
            "severity": rule.severity.value
        })
    
    def register_rules(self, rules: List[ValidationRule]) -> None:
        """Register multiple validation rules."""
        for rule in rules:
            self.register_rule(rule)
    
    def set_environment_defaults(self, environment: str, defaults: Dict[str, Any]) -> None:
        """Set default values for a specific environment."""
        self.environment_defaults[environment.lower()] = defaults
        
        self.logger.debug("Environment defaults set", extra={
            "environment": environment,
            "defaults_count": len(defaults)
        })
    
    async def validate_configuration(self, 
                                   config_dict: Optional[Dict[str, Any]] = None) -> ConfigurationReport:
        """
        Validate all registered configuration rules.
        
        Args:
            config_dict: Optional configuration dictionary. If None, uses os.environ
            
        Returns:
            ConfigurationReport with detailed validation results
        """
        if config_dict is None:
            env = get_env()
            config_dict = env.get_all_variables()
        
        self.logger.info("Starting configuration validation", extra={
            "rules_count": len(self.rules),
            "environment": self.environment,
            "variables_available": len(config_dict)
        })
        
        results = []
        errors = []
        warnings = []
        info = []
        missing_required = []
        using_defaults = []
        security_issues = []
        
        # Validate each rule
        for rule_name, rule in self.rules.items():
            result = await self._validate_single_rule(rule, config_dict)
            results.append(result)
            
            # Categorize results
            if not result.success:
                if result.severity == ValidationSeverity.ERROR:
                    errors.append(result)
                    if result.error_message and "required" in result.error_message.lower():
                        missing_required.append(rule_name)
                elif result.severity == ValidationSeverity.WARNING:
                    warnings.append(result)
                elif result.severity == ValidationSeverity.INFO:
                    info.append(result)
            
            if result.used_default:
                using_defaults.append(rule_name)
            
            # Check for security issues
            if self._is_potentially_secret(rule_name, result.value):
                security_issues.append(result)
        
        # Additional validation
        await self._validate_dependencies(results, config_dict)
        await self._validate_mutual_exclusions(results, config_dict)
        
        report = ConfigurationReport(
            total_variables=len(self.rules),
            validated_count=len(results),
            errors=errors,
            warnings=warnings,
            info=info,
            missing_required=missing_required,
            using_defaults=using_defaults,
            security_issues=security_issues
        )
        
        self.logger.info("Configuration validation completed", extra={
            "summary": report.summary,
            "is_valid": report.is_valid,
            "has_warnings": report.has_warnings
        })
        
        return report
    
    async def _validate_single_rule(self, 
                                  rule: ValidationRule, 
                                  config_dict: Dict[str, Any]) -> ValidationResult:
        """Validate a single configuration rule."""
        # Get value with case-insensitive lookup
        value = self._get_config_value(rule.name, config_dict)
        used_default = False
        
        # Handle missing values
        if value is None:
            if rule.required:
                return ValidationResult(
                    variable=rule.name,
                    value=None,
                    success=False,
                    severity=rule.severity,
                    error_message=f"Required configuration variable '{rule.name}' is missing",
                    suggestion=f"Set {rule.name}={rule.example or 'VALUE'} in your environment"
                )
            elif rule.default is not None:
                value = self._get_default_value(rule)
                used_default = True
            else:
                # Optional variable with no default
                return ValidationResult(
                    variable=rule.name,
                    value=None,
                    success=True,
                    severity=ValidationSeverity.INFO,
                    used_default=False
                )
        
        # Type conversion and validation
        try:
            converted_value, error_msg, suggestion = self._validate_and_convert_value(rule, value)
            
            if error_msg:
                return ValidationResult(
                    variable=rule.name,
                    value=value,
                    success=False,
                    severity=rule.severity,
                    error_message=error_msg,
                    suggestion=suggestion,
                    used_default=used_default
                )
            
            return ValidationResult(
                variable=rule.name,
                value=converted_value,
                success=True,
                severity=ValidationSeverity.INFO,
                used_default=used_default
            )
            
        except Exception as e:
            return ValidationResult(
                variable=rule.name,
                value=value,
                success=False,
                severity=rule.severity,
                error_message=f"Validation error for {rule.name}: {str(e)}",
                suggestion=f"Check the value format for {rule.name}",
                used_default=used_default
            )
    
    def _get_config_value(self, name: str, config_dict: Dict[str, Any]) -> Any:
        """Get configuration value with case-insensitive lookup."""
        # Direct lookup
        if name in config_dict:
            return config_dict[name]
        
        # Case-insensitive lookup
        name_lower = name.lower()
        for key, value in config_dict.items():
            if key.lower() == name_lower:
                return value
        
        return None
    
    def _get_default_value(self, rule: ValidationRule) -> Any:
        """Get default value for a rule, considering environment-specific defaults."""
        # Check environment-specific defaults first
        env_defaults = self.environment_defaults.get(self.environment, {})
        if rule.name in env_defaults:
            return env_defaults[rule.name]
        
        return rule.default
    
    def _validate_and_convert_value(self, 
                                   rule: ValidationRule, 
                                   value: Any) -> tuple[Any, Optional[str], Optional[str]]:
        """Validate and convert value according to rule specifications."""
        # Convert string representation to actual type
        if isinstance(value, str) and rule.config_type != ConfigType.STRING:
            try:
                value = self._convert_string_to_type(value, rule.config_type)
            except ValueError as e:
                return None, f"Invalid {rule.config_type.value} format: {str(e)}", self._get_type_suggestion(rule)
        
        # Type-specific validation
        error_msg, suggestion = self._validate_type_specific(rule, value)
        if error_msg:
            return None, error_msg, suggestion
        
        # Pattern validation
        if rule.pattern and isinstance(value, str):
            if not rule.pattern.match(value):
                return None, f"Value does not match required pattern", f"Expected format: {rule.example or 'see documentation'}"
        
        # Range validation
        if rule.min_value is not None and isinstance(value, (int, float)):
            if value < rule.min_value:
                return None, f"Value {value} is below minimum {rule.min_value}", f"Set to at least {rule.min_value}"
        
        if rule.max_value is not None and isinstance(value, (int, float)):
            if value > rule.max_value:
                return None, f"Value {value} exceeds maximum {rule.max_value}", f"Set to at most {rule.max_value}"
        
        # Choices validation
        if rule.choices and value not in rule.choices:
            return None, f"Value must be one of: {', '.join(rule.choices)}", f"Use one of: {', '.join(rule.choices)}"
        
        # Custom validator
        if rule.validator:
            try:
                if not rule.validator(value):
                    return None, "Custom validation failed", "Check the value according to business rules"
            except Exception as e:
                return None, f"Custom validation error: {str(e)}", "Check the value format"
        
        return value, None, None
    
    def _convert_string_to_type(self, value: str, config_type: ConfigType) -> Any:
        """Convert string value to specified type."""
        if config_type == ConfigType.INTEGER:
            return int(value)
        elif config_type == ConfigType.FLOAT:
            return float(value)
        elif config_type == ConfigType.BOOLEAN:
            return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        elif config_type == ConfigType.JSON:
            return json.loads(value)
        elif config_type == ConfigType.LIST:
            return [item.strip() for item in value.split(',')]
        elif config_type == ConfigType.PORT:
            port = int(value)
            if not (1 <= port <= 65535):
                raise ValueError(f"Port must be between 1 and 65535")
            return port
        else:
            return value
    
    def _validate_type_specific(self, rule: ValidationRule, value: Any) -> tuple[Optional[str], Optional[str]]:
        """Perform type-specific validation."""
        if rule.config_type == ConfigType.URL:
            return self._validate_url(value)
        elif rule.config_type == ConfigType.EMAIL:
            return self._validate_email(value)
        elif rule.config_type == ConfigType.PATH:
            return self._validate_path(value)
        elif rule.config_type == ConfigType.HOST:
            return self._validate_host(value)
        elif rule.config_type == ConfigType.PORT:
            return self._validate_port(value)
        
        return None, None
    
    def _validate_url(self, value: str) -> tuple[Optional[str], Optional[str]]:
        """Validate URL format."""
        if not isinstance(value, str):
            return "URL must be a string", "Provide a valid URL like http://example.com"
        
        if not self.patterns['url'].match(value):
            return "Invalid URL format", "URL must start with http:// or https://"
        
        try:
            parsed = urlparse(value)
            if not parsed.netloc:
                return "URL missing hostname", "Include hostname in URL"
        except Exception:
            return "Invalid URL", "Provide a valid URL"
        
        return None, None
    
    def _validate_email(self, value: str) -> tuple[Optional[str], Optional[str]]:
        """Validate email format."""
        if not isinstance(value, str):
            return "Email must be a string", "Provide a valid email address"
        
        if not self.patterns['email'].match(value):
            return "Invalid email format", "Email must be in format user@domain.com"
        
        return None, None
    
    def _validate_path(self, value: str) -> tuple[Optional[str], Optional[str]]:
        """Validate file path."""
        if not isinstance(value, str):
            return "Path must be a string", "Provide a valid file path"
        
        try:
            path = Path(value)
            if path.exists() and not path.is_file() and not path.is_dir():
                return "Path exists but is not a file or directory", "Check the path"
        except Exception:
            return "Invalid path format", "Provide a valid file system path"
        
        return None, None
    
    def _validate_host(self, value: str) -> tuple[Optional[str], Optional[str]]:
        """Validate hostname."""
        if not isinstance(value, str):
            return "Host must be a string", "Provide a valid hostname"
        
        if not self.patterns['host'].match(value):
            return "Invalid hostname format", "Hostname can only contain letters, numbers, dots, and hyphens"
        
        return None, None
    
    def _validate_port(self, value: Union[int, str]) -> tuple[Optional[str], Optional[str]]:
        """Validate port number."""
        try:
            port = int(value)
            if not (1 <= port <= 65535):
                return "Port must be between 1 and 65535", "Use a valid port number"
        except (ValueError, TypeError):
            return "Port must be a number", "Provide a numeric port value"
        
        return None, None
    
    def _get_type_suggestion(self, rule: ValidationRule) -> str:
        """Get suggestion for type conversion errors."""
        type_examples = {
            ConfigType.INTEGER: "123",
            ConfigType.FLOAT: "123.45",
            ConfigType.BOOLEAN: "true or false",
            ConfigType.URL: "http://example.com",
            ConfigType.EMAIL: "user@example.com",
            ConfigType.PORT: "8080",
            ConfigType.JSON: '{"key": "value"}',
            ConfigType.LIST: "item1,item2,item3"
        }
        
        example = type_examples.get(rule.config_type, rule.example)
        return f"Expected {rule.config_type.value} format. Example: {example}"
    
    async def _validate_dependencies(self, 
                                   results: List[ValidationResult], 
                                   config_dict: Dict[str, Any]) -> None:
        """Validate configuration dependencies."""
        for rule in self.rules.values():
            if not rule.depends_on:
                continue
            
            # Check if this rule's value exists and dependencies are satisfied
            current_result = next((r for r in results if r.variable == rule.name), None)
            if not current_result or not current_result.success:
                continue
            
            # Validate dependencies
            for dep_name in rule.depends_on:
                dep_result = next((r for r in results if r.variable == dep_name), None)
                if not dep_result or not dep_result.success:
                    # Update current result to show dependency failure
                    current_result.success = False
                    current_result.error_message = f"Dependency {dep_name} is not properly configured"
                    current_result.suggestion = f"Configure {dep_name} before using {rule.name}"
    
    async def _validate_mutual_exclusions(self, 
                                        results: List[ValidationResult], 
                                        config_dict: Dict[str, Any]) -> None:
        """Validate mutually exclusive configurations."""
        for rule in self.rules.values():
            if not rule.mutually_exclusive:
                continue
            
            current_result = next((r for r in results if r.variable == rule.name), None)
            if not current_result or not current_result.success:
                continue
            
            # Check for conflicts
            for exclusive_name in rule.mutually_exclusive:
                exclusive_result = next((r for r in results if r.variable == exclusive_name), None)
                if exclusive_result and exclusive_result.success:
                    current_result.success = False
                    current_result.error_message = f"Cannot use {rule.name} together with {exclusive_name}"
                    current_result.suggestion = f"Choose either {rule.name} or {exclusive_name}, not both"
    
    def _is_potentially_secret(self, name: str, value: Any) -> bool:
        """Check if a configuration might contain secret information."""
        if not isinstance(value, str):
            return False
        
        # Check name patterns
        for pattern in self.secret_patterns:
            if pattern.match(name):
                return True
        
        # Check value patterns (basic heuristics)
        if len(value) > 20 and any(c.isalpha() and c.isupper() for c in value):
            # Might be a token or key
            return True
        
        return False
    
    def _register_default_rules(self) -> None:
        """Register default validation rules for common configurations."""
        default_rules = [
            # Database configurations
            ValidationRule(
                name="REDIS_URL", 
                config_type=ConfigType.URL,
                required=False,
                default="redis://localhost:6379/0",
                description="Redis connection URL for caching",
                example="redis://localhost:6379/0"
            ),
            
            ValidationRule(
                name="CLICKHOUSE_URL",
                config_type=ConfigType.URL,
                required=False,
                description="ClickHouse connection URL for analytics",
                example="http://localhost:8123"
            ),
            
            # Server configurations
            ValidationRule(
                name="PORT",
                config_type=ConfigType.PORT,
                required=False,
                default=8000,
                description="Server port number",
                example="8000"
            ),
            
            ValidationRule(
                name="HOST",
                config_type=ConfigType.HOST,
                required=False,
                default="localhost",
                description="Server host address",
                example="0.0.0.0"
            ),
            
            # Environment
            ValidationRule(
                name="ENVIRONMENT",
                config_type=ConfigType.STRING,
                required=False,
                default="development",
                choices=["development", "staging", "production"],
                description="Application environment",
                example="development"
            ),
            
            ValidationRule(
                name="DEBUG",
                config_type=ConfigType.BOOLEAN,
                required=False,
                default=False,
                description="Enable debug mode",
                example="false"
            ),
            
            # Security
            ValidationRule(
                name="SECRET_KEY",
                config_type=ConfigType.SECRET,
                required=True,
                description="Application secret key for encryption",
                example="your-secret-key-here"
            ),
            
            ValidationRule(
                name="JWT_SECRET",
                config_type=ConfigType.SECRET,
                required=False,
                description="JWT signing secret",
                example="jwt-secret-key"
            ),
            
            # External services
            ValidationRule(
                name="GOOGLE_API_KEY",
                config_type=ConfigType.SECRET,
                required=False,
                description="OpenAI API key for LLM services",
                example="sk-..."
            ),
            
            ValidationRule(
                name="GOOGLE_API_KEY",
                config_type=ConfigType.SECRET,
                required=False,
                description="Google API key for services",
                example="AIza..."
            ),
            
            # Monitoring
            ValidationRule(
                name="LOG_LEVEL",
                config_type=ConfigType.STRING,
                required=False,
                default="INFO",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                description="Logging level",
                example="INFO"
            ),
            
            ValidationRule(
                name="METRICS_ENABLED",
                config_type=ConfigType.BOOLEAN,
                required=False,
                default=True,
                description="Enable metrics collection",
                example="true"
            )
        ]
        
        self.register_rules(default_rules)


# Global configuration validator instance
config_validator = ConfigurationValidator()