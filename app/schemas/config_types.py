"""Strong type definitions for Config Manager and configuration handling."""

from typing import Any, Dict, Optional, List, Union, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigurationStatus(str, Enum):
    """Configuration loading status."""
    LOADED = "loaded"
    FAILED = "failed"
    PARTIAL = "partial"
    VALIDATING = "validating"
    RELOADING = "reloading"


class SecretType(str, Enum):
    """Types of secrets managed by the system."""
    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    CONNECTION_STRING = "connection_string"
    ENCRYPTION_KEY = "encryption_key"


class SecretMapping(BaseModel):
    """Mapping configuration for secrets to config fields."""
    secret_name: str = Field(description="Name of the secret")
    secret_type: SecretType = Field(description="Type of secret")
    targets: List[str] = Field(description="List of configuration targets")
    field: str = Field(description="Field name to set")
    required: bool = Field(default=False, description="Whether this secret is required")
    environment_variable: Optional[str] = Field(default=None, description="Environment variable name as fallback")
    default_value: Optional[str] = Field(default=None, description="Default value if secret not found")
    validation_pattern: Optional[str] = Field(default=None, description="Regex pattern for validation")


class ConfigFieldInfo(BaseModel):
    """Information about a configuration field."""
    field_name: str = Field(description="Name of the configuration field")
    field_type: str = Field(description="Type of the field")
    is_required: bool = Field(description="Whether the field is required")
    default_value: Optional[Any] = Field(default=None, description="Default value")
    description: Optional[str] = Field(default=None, description="Field description")
    is_secret: bool = Field(default=False, description="Whether this field contains sensitive data")
    environment_variable: Optional[str] = Field(default=None, description="Associated environment variable")


class LLMConfigInfo(BaseModel):
    """Information about LLM configuration."""
    name: str = Field(description="Configuration name")
    provider: str = Field(description="LLM provider")
    model_name: str = Field(description="Model name")
    api_key_configured: bool = Field(description="Whether API key is configured")
    enabled: bool = Field(description="Whether configuration is enabled")
    generation_config: Dict[str, Any] = Field(description="Generation configuration")
    last_validated: Optional[datetime] = Field(default=None, description="Last validation timestamp")
    validation_status: Optional[str] = Field(default=None, description="Last validation status")


class DatabaseConfigInfo(BaseModel):
    """Information about database configuration."""
    connection_url_configured: bool = Field(description="Whether connection URL is configured")
    host: Optional[str] = Field(default=None, description="Database host")
    port: Optional[int] = Field(default=None, description="Database port")
    database: Optional[str] = Field(default=None, description="Database name")
    ssl_enabled: bool = Field(default=False, description="Whether SSL is enabled")
    connection_pool_size: Optional[int] = Field(default=None, description="Connection pool size")
    last_connection_test: Optional[datetime] = Field(default=None, description="Last connection test")
    connection_status: Optional[str] = Field(default=None, description="Last connection status")


class RedisConfigInfo(BaseModel):
    """Information about Redis configuration."""
    url_configured: bool = Field(description="Whether Redis URL is configured")
    host: Optional[str] = Field(default=None, description="Redis host")
    port: Optional[int] = Field(default=None, description="Redis port")
    database: Optional[int] = Field(default=None, description="Redis database number")
    ssl_enabled: bool = Field(default=False, description="Whether SSL is enabled")
    max_connections: Optional[int] = Field(default=None, description="Maximum connections")
    last_ping: Optional[datetime] = Field(default=None, description="Last ping test")
    ping_status: Optional[str] = Field(default=None, description="Last ping status")


class ClickHouseConfigInfo(BaseModel):
    """Information about ClickHouse configuration."""
    host: Optional[str] = Field(default=None, description="ClickHouse host")
    port: Optional[int] = Field(default=None, description="ClickHouse port")
    user: Optional[str] = Field(default=None, description="ClickHouse user")
    password_configured: bool = Field(description="Whether password is configured")
    database: Optional[str] = Field(default=None, description="ClickHouse database")
    secure: bool = Field(default=False, description="Whether connection is secure")
    last_health_check: Optional[datetime] = Field(default=None, description="Last health check")
    health_status: Optional[str] = Field(default=None, description="Last health status")


class WebSocketConfigInfo(BaseModel):
    """Information about WebSocket configuration."""
    url: str = Field(description="WebSocket URL")
    heartbeat_interval: int = Field(description="Heartbeat interval in seconds")
    max_connections_per_user: int = Field(description="Maximum connections per user")
    rate_limit_requests: int = Field(description="Rate limit requests per minute")
    rate_limit_window: int = Field(description="Rate limit window in seconds")


class ConfigurationSummary(BaseModel):
    """Summary of configuration status."""
    environment: Environment = Field(description="Current environment")
    status: ConfigurationStatus = Field(description="Configuration status")
    loaded_at: datetime = Field(description="Configuration load timestamp")
    secrets_loaded: int = Field(description="Number of secrets loaded")
    secrets_total: int = Field(description="Total number of secrets expected")
    critical_secrets_missing: List[str] = Field(description="Missing critical secrets")
    warnings: List[str] = Field(description="Configuration warnings")
    errors: List[str] = Field(description="Configuration errors")


class ConfigurationResponse(BaseModel):
    """Response model for configuration endpoint."""
    summary: ConfigurationSummary = Field(description="Configuration summary")
    llm_configs: Dict[str, LLMConfigInfo] = Field(description="LLM configurations")
    database_config: DatabaseConfigInfo = Field(description="Database configuration")
    redis_config: RedisConfigInfo = Field(description="Redis configuration")
    clickhouse_config: ClickHouseConfigInfo = Field(description="ClickHouse configuration")
    websocket_config: WebSocketConfigInfo = Field(description="WebSocket configuration")
    field_info: List[ConfigFieldInfo] = Field(description="Configuration field information")
    secret_mappings: List[SecretMapping] = Field(description="Secret mapping configurations")


class ConfigValidationRule(BaseModel):
    """Validation rule for configuration."""
    field_path: str = Field(description="Path to the field to validate")
    rule_type: Literal["required", "type", "pattern", "range", "custom"] = Field(description="Type of validation rule")
    parameters: Dict[str, Any] = Field(description="Rule parameters")
    error_message: str = Field(description="Error message for validation failure")
    severity: Literal["error", "warning", "info"] = Field(description="Validation severity")


class ConfigValidationResult(BaseModel):
    """Result of configuration validation."""
    is_valid: bool = Field(description="Whether configuration is valid")
    errors: List[str] = Field(description="Validation errors")
    warnings: List[str] = Field(description="Validation warnings")
    field_results: Dict[str, bool] = Field(description="Validation result per field")
    validation_timestamp: datetime = Field(description="Validation timestamp")
    validation_duration_ms: float = Field(description="Validation duration")


class SecretLoadResult(BaseModel):
    """Result of secret loading operation."""
    total_secrets: int = Field(description="Total number of secrets processed")
    loaded_secrets: int = Field(description="Number of secrets successfully loaded")
    failed_secrets: List[str] = Field(description="Names of secrets that failed to load")
    skipped_secrets: List[str] = Field(description="Names of secrets that were skipped")
    critical_missing: List[str] = Field(description="Critical secrets that are missing")
    load_duration_ms: float = Field(description="Time taken to load secrets")
    source: Literal["secret_manager", "environment", "fallback"] = Field(description="Source of secrets")


class ConfigReloadResult(BaseModel):
    """Result of configuration reload operation."""
    success: bool = Field(description="Whether reload was successful")
    previous_status: ConfigurationStatus = Field(description="Previous configuration status")
    new_status: ConfigurationStatus = Field(description="New configuration status")
    changes_detected: List[str] = Field(description="List of changes detected")
    reload_timestamp: datetime = Field(description="Reload timestamp")
    reload_duration_ms: float = Field(description="Reload duration")
    errors: List[str] = Field(description="Errors encountered during reload")
    warnings: List[str] = Field(description="Warnings generated during reload")


class EnvironmentDetectionResult(BaseModel):
    """Result of environment detection."""
    detected_environment: Environment = Field(description="Detected environment")
    detection_method: str = Field(description="Method used for detection")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in detection")
    indicators: Dict[str, Any] = Field(description="Environment indicators found")
    fallback_used: bool = Field(description="Whether fallback detection was used")


class ConfigHealthCheck(BaseModel):
    """Health check for configuration components."""
    component: str = Field(description="Component name")
    healthy: bool = Field(description="Whether component is healthy")
    status: str = Field(description="Component status")
    response_time_ms: Optional[float] = Field(default=None, description="Response time for health check")
    error: Optional[str] = Field(default=None, description="Error message if unhealthy")
    last_checked: datetime = Field(description="Last health check timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional health check metadata")


class ConfigurationDiagnostics(BaseModel):
    """Comprehensive configuration diagnostics."""
    overall_health: bool = Field(description="Overall configuration health")
    environment: Environment = Field(description="Current environment")
    config_status: ConfigurationStatus = Field(description="Configuration status")
    component_health: List[ConfigHealthCheck] = Field(description="Health of individual components")
    secret_diagnostics: SecretLoadResult = Field(description="Secret loading diagnostics")
    validation_result: ConfigValidationResult = Field(description="Configuration validation result")
    performance_metrics: Dict[str, float] = Field(description="Performance metrics")
    recommendations: List[str] = Field(description="Recommendations for improvement")
    generated_at: datetime = Field(description="Diagnostics generation timestamp")


class ConfigBackup(BaseModel):
    """Configuration backup information."""
    backup_id: str = Field(description="Unique backup identifier")
    environment: Environment = Field(description="Environment at backup time")
    created_at: datetime = Field(description="Backup creation timestamp")
    config_hash: str = Field(description="Hash of the configuration")
    includes_secrets: bool = Field(description="Whether backup includes secrets")
    backup_size_bytes: int = Field(description="Backup size in bytes")
    description: Optional[str] = Field(default=None, description="Backup description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional backup metadata")


class ConfigurationHistory(BaseModel):
    """History of configuration changes."""
    change_id: str = Field(description="Unique change identifier")
    timestamp: datetime = Field(description="Change timestamp")
    change_type: Literal["reload", "secret_update", "validation", "backup", "restore"] = Field(description="Type of change")
    environment: Environment = Field(description="Environment where change occurred")
    changed_fields: List[str] = Field(description="Fields that were changed")
    change_summary: str = Field(description="Summary of the change")
    initiated_by: Optional[str] = Field(default=None, description="Who initiated the change")
    success: bool = Field(description="Whether change was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if change failed")