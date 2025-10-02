"""
Configuration Management for Zen Secret Management System

This module provides advanced configuration management with:
- Environment-based configuration loading
- Schema validation and type checking
- Configuration templating and inheritance
- Dynamic configuration updates
- Secure configuration storage
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from dataclasses import dataclass, field
from datetime import timedelta

from .core import SecretEnvironment, SecretClassification
from .exceptions import SecretConfigurationError


@dataclass
class ZenApexConfig:
    """Configuration for Zen-Apex OAuth integration."""
    client_id: str
    client_secret_name: str  # Name of secret containing client secret
    auth_url: str
    token_url: str
    redirect_uri: str = "http://localhost:8080/callback"
    scope: str = "read write"
    use_pkce: bool = True
    timeout_seconds: int = 300


@dataclass
class TelemetryConfig:
    """Configuration for OpenTelemetry integration."""
    enabled: bool = True
    anonymous_mode: bool = True
    service_account_secret_name: str = "telemetry-service-account"
    project_id: str = "netra-telemetry-public"
    endpoint: str = "https://cloudtrace.googleapis.com"
    sample_rate: float = 0.1


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enforce_tls: bool = True
    min_tls_version: str = "1.3"
    certificate_validation: bool = True
    access_logging: bool = True
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 1000
    ip_whitelist: List[str] = field(default_factory=list)
    require_mfa: bool = False


@dataclass
class BackupConfig:
    """Backup configuration settings."""
    enabled: bool = True
    provider: str = "gcs"  # gcs, s3, azure
    bucket_name: str = ""
    retention_days: int = 30
    encryption_enabled: bool = True
    compression_enabled: bool = True
    schedule_cron: str = "0 2 * * *"  # Daily at 2 AM


@dataclass
class AlertingConfig:
    """Alerting configuration settings."""
    enabled: bool = True
    email_notifications: bool = True
    slack_notifications: bool = False
    webhook_notifications: bool = False
    email_recipients: List[str] = field(default_factory=list)
    slack_webhook_secret_name: str = "slack-webhook-url"
    webhook_url_secret_name: str = "alerting-webhook-url"
    alert_cooldown_minutes: int = 30


class ConfigurationManager:
    """
    Advanced configuration manager for the Zen Secret Management System.

    Features:
    - Multi-format configuration loading (JSON, YAML, ENV)
    - Schema validation and type checking
    - Environment-based configuration inheritance
    - Secure configuration with secret references
    - Dynamic configuration updates
    """

    def __init__(self, config_path: Optional[Path] = None,
                 environment: Optional[str] = None):
        """Initialize the configuration manager."""
        self.config_path = config_path
        self.environment = environment or os.environ.get("ZEN_SECRETS_ENV", "development")
        self._config_cache: Dict[str, Any] = {}
        self._watchers: List[Any] = []

    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from multiple sources with precedence."""
        config = {}

        # 1. Load default configuration
        config.update(self._get_default_config())

        # 2. Load from configuration files
        if self.config_path and self.config_path.exists():
            file_config = self._load_config_file(self.config_path)
            config = self._deep_merge(config, file_config)

        # 3. Load environment-specific configuration
        env_config_path = self._get_env_config_path()
        if env_config_path and env_config_path.exists():
            env_config = self._load_config_file(env_config_path)
            config = self._deep_merge(config, env_config)

        # 4. Override with environment variables
        env_overrides = self._load_env_variables()
        config = self._deep_merge(config, env_overrides)

        # 5. Validate configuration
        self._validate_configuration(config)

        # 6. Process secret references
        config = self._process_secret_references(config)

        self._config_cache = config
        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "zen_secrets": {
                "gcp_project_id": "",
                "gsm_enabled": True,
                "kubernetes_enabled": True,
                "kubernetes_namespace": "default",
                "workload_identity_enabled": True,
                "environment": self.environment,
                "encryption_key_id": None,
                "enforce_rotation": True,
                "default_rotation_interval_days": 90,
                "monitoring_enabled": True,
                "audit_logging_enabled": True,
                "alert_on_access_denied": True,
                "alert_on_rotation_failure": True,
                "backup_enabled": True,
                "backup_retention_days": 30,
                "cache_enabled": True,
                "cache_ttl_seconds": 300,
                "max_concurrent_operations": 10,
                "strict_validation": True,
                "require_classification": True
            },
            "zen_apex": {
                "client_id": "",
                "client_secret_name": "apex-client-secret",
                "auth_url": "https://apex.example.com/oauth/authorize",
                "token_url": "https://apex.example.com/oauth/token",
                "redirect_uri": "http://localhost:8080/callback",
                "scope": "read write",
                "use_pkce": True,
                "timeout_seconds": 300
            },
            "telemetry": {
                "enabled": True,
                "anonymous_mode": True,
                "service_account_secret_name": "telemetry-service-account",
                "project_id": "netra-telemetry-public",
                "endpoint": "https://cloudtrace.googleapis.com",
                "sample_rate": 0.1
            },
            "security": {
                "enforce_tls": True,
                "min_tls_version": "1.3",
                "certificate_validation": True,
                "access_logging": True,
                "rate_limiting_enabled": True,
                "max_requests_per_minute": 1000,
                "ip_whitelist": [],
                "require_mfa": False
            },
            "backup": {
                "enabled": True,
                "provider": "gcs",
                "bucket_name": "",
                "retention_days": 30,
                "encryption_enabled": True,
                "compression_enabled": True,
                "schedule_cron": "0 2 * * *"
            },
            "alerting": {
                "enabled": True,
                "email_notifications": True,
                "slack_notifications": False,
                "webhook_notifications": False,
                "email_recipients": [],
                "slack_webhook_secret_name": "slack-webhook-url",
                "webhook_url_secret_name": "alerting-webhook-url",
                "alert_cooldown_minutes": 30
            }
        }

    def _load_config_file(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from a file."""
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                else:
                    return json.load(f)
        except Exception as e:
            raise SecretConfigurationError(
                f"Failed to load configuration from {config_path}: {str(e)}",
                str(config_path)
            )

    def _get_env_config_path(self) -> Optional[Path]:
        """Get environment-specific configuration file path."""
        if not self.config_path:
            return None

        # Look for environment-specific config file
        base_path = self.config_path.parent
        base_name = self.config_path.stem
        suffix = self.config_path.suffix

        env_config_path = base_path / f"{base_name}.{self.environment}{suffix}"
        return env_config_path if env_config_path.exists() else None

    def _load_env_variables(self) -> Dict[str, Any]:
        """Load configuration overrides from environment variables."""
        config = {}
        prefix = "ZEN_SECRETS_"

        # Define environment variable mappings
        env_mappings = {
            f"{prefix}GCP_PROJECT_ID": "zen_secrets.gcp_project_id",
            f"{prefix}GSM_ENABLED": "zen_secrets.gsm_enabled",
            f"{prefix}KUBERNETES_ENABLED": "zen_secrets.kubernetes_enabled",
            f"{prefix}KUBERNETES_NAMESPACE": "zen_secrets.kubernetes_namespace",
            f"{prefix}WORKLOAD_IDENTITY_ENABLED": "zen_secrets.workload_identity_enabled",
            f"{prefix}ENVIRONMENT": "zen_secrets.environment",
            f"{prefix}ENFORCE_ROTATION": "zen_secrets.enforce_rotation",
            f"{prefix}MONITORING_ENABLED": "zen_secrets.monitoring_enabled",
            f"{prefix}BACKUP_ENABLED": "zen_secrets.backup_enabled",

            "APEX_CLIENT_ID": "zen_apex.client_id",
            "APEX_CLIENT_SECRET_NAME": "zen_apex.client_secret_name",
            "APEX_AUTH_URL": "zen_apex.auth_url",
            "APEX_TOKEN_URL": "zen_apex.token_url",

            "TELEMETRY_ENABLED": "telemetry.enabled",
            "TELEMETRY_ANONYMOUS_MODE": "telemetry.anonymous_mode",
            "TELEMETRY_PROJECT_ID": "telemetry.project_id",
            "TELEMETRY_SAMPLE_RATE": "telemetry.sample_rate",
        }

        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif self._is_float(value):
                    value = float(value)

                # Set nested configuration value
                self._set_nested_config(config, config_path, value)

        return config

    def _is_float(self, value: str) -> bool:
        """Check if a string can be converted to float."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _set_nested_config(self, config: Dict[str, Any], path: str, value: Any) -> None:
        """Set a nested configuration value using dot notation."""
        keys = path.split('.')
        current = config

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate configuration schema and values."""
        errors = []

        # Validate required fields
        zen_secrets = config.get("zen_secrets", {})
        if not zen_secrets.get("gcp_project_id"):
            errors.append("zen_secrets.gcp_project_id is required")

        # Validate environment
        environment = zen_secrets.get("environment", "development")
        try:
            SecretEnvironment(environment)
        except ValueError:
            errors.append(f"Invalid environment: {environment}")

        # Validate Zen-Apex configuration
        zen_apex = config.get("zen_apex", {})
        if zen_apex.get("client_id") and not zen_apex.get("client_secret_name"):
            errors.append("zen_apex.client_secret_name is required when client_id is set")

        # Validate telemetry configuration
        telemetry = config.get("telemetry", {})
        sample_rate = telemetry.get("sample_rate", 0.1)
        if not (0.0 <= sample_rate <= 1.0):
            errors.append("telemetry.sample_rate must be between 0.0 and 1.0")

        # Validate security configuration
        security = config.get("security", {})
        max_requests = security.get("max_requests_per_minute", 1000)
        if max_requests <= 0:
            errors.append("security.max_requests_per_minute must be positive")

        if errors:
            raise SecretConfigurationError(
                f"Configuration validation failed: {'; '.join(errors)}"
            )

    def _process_secret_references(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process secret references in configuration values."""
        # This would resolve secret references like ${secret:secret-name}
        # For now, we'll just return the config as-is
        # In a full implementation, this would resolve secret references
        return config

    def get_zen_secrets_config(self) -> Dict[str, Any]:
        """Get Zen Secrets configuration."""
        if not self._config_cache:
            self.load_configuration()
        return self._config_cache.get("zen_secrets", {})

    def get_zen_apex_config(self) -> ZenApexConfig:
        """Get Zen-Apex OAuth configuration."""
        if not self._config_cache:
            self.load_configuration()

        apex_config = self._config_cache.get("zen_apex", {})
        return ZenApexConfig(**apex_config)

    def get_telemetry_config(self) -> TelemetryConfig:
        """Get OpenTelemetry configuration."""
        if not self._config_cache:
            self.load_configuration()

        telemetry_config = self._config_cache.get("telemetry", {})
        return TelemetryConfig(**telemetry_config)

    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        if not self._config_cache:
            self.load_configuration()

        security_config = self._config_cache.get("security", {})
        return SecurityConfig(**security_config)

    def get_backup_config(self) -> BackupConfig:
        """Get backup configuration."""
        if not self._config_cache:
            self.load_configuration()

        backup_config = self._config_cache.get("backup", {})
        return BackupConfig(**backup_config)

    def get_alerting_config(self) -> AlertingConfig:
        """Get alerting configuration."""
        if not self._config_cache:
            self.load_configuration()

        alerting_config = self._config_cache.get("alerting", {})
        return AlertingConfig(**alerting_config)

    def update_configuration(self, updates: Dict[str, Any]) -> None:
        """Update configuration dynamically."""
        if not self._config_cache:
            self.load_configuration()

        self._config_cache = self._deep_merge(self._config_cache, updates)
        self._validate_configuration(self._config_cache)

    def export_configuration(self, format: str = "yaml") -> str:
        """Export current configuration in specified format."""
        if not self._config_cache:
            self.load_configuration()

        if format.lower() == "yaml":
            return yaml.dump(self._config_cache, default_flow_style=False)
        else:
            return json.dumps(self._config_cache, indent=2)

    def get_configuration_template(self) -> str:
        """Get a configuration template with documentation."""
        template = """
# Zen Secret Management System Configuration

zen_secrets:
  # Google Cloud Project ID for Secret Manager
  gcp_project_id: "your-gcp-project-id"

  # Enable Google Secret Manager backend
  gsm_enabled: true

  # Enable Kubernetes secret management
  kubernetes_enabled: true
  kubernetes_namespace: "default"

  # Enable Workload Identity Federation for GKE
  workload_identity_enabled: true

  # Deployment environment (development, staging, production)
  environment: "development"

  # Encryption key ID for additional encryption (optional)
  encryption_key_id: null

  # Secret rotation settings
  enforce_rotation: true
  default_rotation_interval_days: 90

  # Monitoring and alerting
  monitoring_enabled: true
  audit_logging_enabled: true
  alert_on_access_denied: true
  alert_on_rotation_failure: true

  # Backup settings
  backup_enabled: true
  backup_retention_days: 30

  # Performance settings
  cache_enabled: true
  cache_ttl_seconds: 300
  max_concurrent_operations: 10

  # Validation settings
  strict_validation: true
  require_classification: true

# Zen-Apex OAuth Integration
zen_apex:
  client_id: "your-apex-client-id"
  client_secret_name: "apex-client-secret"
  auth_url: "https://apex.example.com/oauth/authorize"
  token_url: "https://apex.example.com/oauth/token"
  redirect_uri: "http://localhost:8080/callback"
  scope: "read write"
  use_pkce: true
  timeout_seconds: 300

# OpenTelemetry Configuration
telemetry:
  enabled: true
  anonymous_mode: true
  service_account_secret_name: "telemetry-service-account"
  project_id: "netra-telemetry-public"
  endpoint: "https://cloudtrace.googleapis.com"
  sample_rate: 0.1

# Security Settings
security:
  enforce_tls: true
  min_tls_version: "1.3"
  certificate_validation: true
  access_logging: true
  rate_limiting_enabled: true
  max_requests_per_minute: 1000
  ip_whitelist: []
  require_mfa: false

# Backup Configuration
backup:
  enabled: true
  provider: "gcs"  # gcs, s3, azure
  bucket_name: "your-backup-bucket"
  retention_days: 30
  encryption_enabled: true
  compression_enabled: true
  schedule_cron: "0 2 * * *"  # Daily at 2 AM

# Alerting Configuration
alerting:
  enabled: true
  email_notifications: true
  slack_notifications: false
  webhook_notifications: false
  email_recipients:
    - "admin@example.com"
  slack_webhook_secret_name: "slack-webhook-url"
  webhook_url_secret_name: "alerting-webhook-url"
  alert_cooldown_minutes: 30
        """
        return template.strip()