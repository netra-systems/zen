"""Configuration schemas and data models.

**UPDATED**: This file has been migrated to use IsolatedEnvironment
for unified environment management. Follows SPEC/unified_environment_management.xml.

For new code, use:
from netra_backend.app.core.configuration import unified_config_manager
"""

from enum import Enum
from typing import Any, Dict, List, Optional

# Use backend-specific isolated environment
from shared.isolated_environment import get_env
# SSOT: Import SERVICE_ID constant
from shared.constants.service_identifiers import SERVICE_ID

from pydantic import BaseModel, Field, field_validator, ConfigDict

from netra_backend.app.schemas.auth_types import (
    AuthConfigResponse,
    AuthEndpoints,
    DevUser,
)
from netra_backend.app.schemas.llm_types import LLMProvider
from netra_backend.app.schemas.registry import User


class ClickHouseCredentials(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str

class SecretReference(BaseModel):
    name: str
    target_field: str
    target_models: Optional[List[str]] = None
    # Fixed: Use direct env fallback to prevent recursion during config initialization
    project_id: str = Field(default_factory=lambda: SecretReference._get_project_id_safe())
    version: str = "latest"
    
    @staticmethod
    def _get_project_id_safe() -> str:
        """Get project ID safely without causing recursion during config initialization.
        
        Uses IsolatedEnvironment for consistent environment access.
        """
        env = get_env()
        # Use IsolatedEnvironment for project ID loading
        return env.get("GCP_PROJECT_ID_NUMERICAL_STAGING", 
                       env.get("SECRET_MANAGER_PROJECT_ID", 
                       "701982941522" if env.get("ENVIRONMENT", "").lower() == "staging" else "304612253870"))


SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_models=["llm_configs.default", "llm_configs.triage", "llm_configs.data", "llm_configs.optimizations_core", "llm_configs.actions_to_meet_goals", "llm_configs.reporting", "llm_configs.analysis"], target_field="api_key"),
    SecretReference(name="google-client-id", target_models=["google_cloud", "oauth_config"], target_field="client_id"),
    SecretReference(name="google-client-secret", target_models=["google_cloud", "oauth_config"], target_field="client_secret"),
    SecretReference(name="langfuse-secret-key", target_models=["langfuse"], target_field="secret_key"),
    SecretReference(name="langfuse-public-key", target_models=["langfuse"], target_field="public_key"),
    SecretReference(name="clickhouse-default-password", target_models=["clickhouse_native", "clickhouse_https"], target_field="password"),
    SecretReference(name="jwt-secret-key", target_field="jwt_secret_key"),
    SecretReference(name="service-secret", target_field="service_secret"),
    SecretReference(name="fernet-key", target_field="fernet_key"),
    SecretReference(name="redis-default", target_models=["redis"], target_field="password"),
    SecretReference(name="github-token", target_field="github_token"),
]

class RedisConfig(BaseModel):
    host: str = 'localhost'
    port: int = 6379
    username: str = "default"
    password: Optional[str] = None
    db: int = 0
    ssl: bool = False

    def __init__(self, **data):
        # Load from environment if not provided in data
        env = get_env()

        # Map environment variables to field names if not already in data
        env_mappings = {
            'host': 'REDIS_HOST',
            'port': 'REDIS_PORT',
            'username': 'REDIS_USERNAME',
            'password': 'REDIS_PASSWORD',
            'db': 'REDIS_DB',
            'ssl': 'REDIS_SSL'
        }

        for field_name, env_var in env_mappings.items():
            if field_name not in data:
                env_value = env.get(env_var)
                if env_value is not None:
                    # Convert types as needed
                    if field_name == 'port':
                        try:
                            data[field_name] = int(env_value)
                        except (ValueError, TypeError):
                            pass
                    elif field_name == 'db':
                        try:
                            data[field_name] = int(env_value)
                        except (ValueError, TypeError):
                            pass
                    elif field_name == 'ssl':
                        data[field_name] = env_value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        data[field_name] = env_value

        super().__init__(**data)

class GoogleCloudConfig(BaseModel):
    project_id: str = "cryptic-net-466001-n0"
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""

class OAuthConfig(BaseModel):
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_uri: str = "https://accounts.google.com/o/oauth2/v2/auth"
    userinfo_endpoint: str = "https://www.googleapis.com/oauth2/userinfo"
    scopes: List[str] = ["openid", "email", "profile"]
    authorized_javascript_origins: List[str] = [
      "https://app.netrasystems.ai",
      "https://127.0.0.1",
      "http://localhost"
    ]
    authorized_redirect_uris: List[str] = [
      "https://app.netrasystems.ai/oauth2callback",
      "http://localhost:3000/auth/callback"
    ]

class ClickHouseNativeConfig(BaseModel):
    host: str = ""  # No default - must be explicitly configured for staging/production
    port: int = 9440
    user: str = "default"
    password: str = ""
    database: str = "default"
    # Timeout configurations for enterprise reliability
    connect_timeout: int = 10  # Connection timeout in seconds
    read_timeout: int = 30     # Read timeout in seconds  
    write_timeout: int = 30    # Write timeout in seconds
    query_timeout: int = 30    # Query execution timeout in seconds

class ClickHouseHTTPConfig(BaseModel):
    host: str = ""  # No default - must be explicitly configured for staging/production
    port: int = 8123  # Standard ClickHouse HTTP port
    user: str = "default"
    password: str = ""
    database: str = "default"
    # Timeout configurations for enterprise reliability
    connect_timeout: int = 10  # Connection timeout in seconds
    read_timeout: int = 30     # Read timeout in seconds
    write_timeout: int = 30    # Write timeout in seconds
    query_timeout: int = 30    # Query execution timeout in seconds

class ClickHouseHTTPSConfig(BaseModel):
    host: str = ""  # No default - must be explicitly configured for staging/production
    port: int = 8443  # Standard ClickHouse HTTPS port
    user: str = "default"
    password: str = ""
    database: str = "default"
    # Timeout configurations for enterprise reliability
    connect_timeout: int = 10  # Connection timeout in seconds
    read_timeout: int = 30     # Read timeout in seconds
    write_timeout: int = 30    # Write timeout in seconds  
    query_timeout: int = 30    # Query execution timeout in seconds



class ClickHouseLoggingConfig(BaseModel):
    enabled: bool = True
    default_table: str = "logs"
    default_time_period_days: int = 7
    available_tables: List[str] = Field(default_factory=lambda: ["logs"])
    default_tables: Dict[str, str] = Field(default_factory=lambda: {})
    available_time_periods: List[int] = Field(default_factory=lambda: [1, 7, 30, 90])


class LogTableSettings(BaseModel):
    log_table: str


class TimePeriodSettings(BaseModel):
    days: int


class DefaultLogTableSettings(BaseModel):
    context: str
    log_table: str


class LangfuseConfig(BaseModel):
    secret_key: str = ""
    public_key: str = ""
    host: str = "https://cloud.langfuse.com/"

class LLMConfig(BaseModel):
    provider: LLMProvider = Field(..., description="The LLM provider enum.")
    model_name: str = Field(..., description="The name of the model.")
    api_key: Optional[str] = Field(None, description="The API key for the LLM provider.")
    generation_config: Dict[str, Any] = Field({}, description="A dictionary of generation parameters, e.g., temperature, max_tokens.")

class WebSocketConfig(BaseModel):
    ws_url: str = Field(default="ws://localhost:8000/ws", description="The WebSocket URL for the frontend to connect to.")
    
    # CRITICAL: Cloud-native timeout configuration for $200K+ MRR reliability
    # These timeouts are managed by timeout_configuration.py for environment awareness
    connection_timeout: int = Field(default=60, description="WebSocket connection timeout (seconds)")
    recv_timeout: int = Field(default=35, description="WebSocket receive timeout (seconds) - MUST be > agent execution timeout")
    send_timeout: int = Field(default=30, description="WebSocket send timeout (seconds)")
    heartbeat_timeout: int = Field(default=90, description="WebSocket heartbeat timeout (seconds)")
    heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval (seconds)")
    
    # PHASE 1 FEATURE FLAG: SSOT consolidation control
    ssot_consolidation_enabled: bool = Field(
        default=False, 
        description="Enable WebSocket SSOT consolidation to eliminate race conditions (Phase 1: backward compatibility)"
    )
    
    def __init__(self, **kwargs):
        # Override with environment variable if not explicitly set
        if 'ssot_consolidation_enabled' not in kwargs:
            env_value = get_env().get("WEBSOCKET_SSOT_CONSOLIDATION", "false").lower()
            kwargs['ssot_consolidation_enabled'] = env_value in ("true", "1", "yes", "on")
        super().__init__(**kwargs)

class AppConfig(BaseModel):
    """Base configuration class."""

    environment: str = "development"
    app_name: str = "netra"  # Application name for identification
    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    oauth_config: OAuthConfig = Field(default_factory=OAuthConfig)
    clickhouse_native: ClickHouseNativeConfig = Field(default_factory=ClickHouseNativeConfig)
    clickhouse_http: ClickHouseHTTPConfig = Field(default_factory=ClickHouseHTTPConfig)
    clickhouse_https: ClickHouseHTTPSConfig = Field(default_factory=ClickHouseHTTPSConfig)
    clickhouse_logging: ClickHouseLoggingConfig = ClickHouseLoggingConfig()
    langfuse: LangfuseConfig = LangfuseConfig()
    ws_config: WebSocketConfig = Field(default_factory=WebSocketConfig)

    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = None
    jwt_secret_key: str = None
    api_base_url: str = "http://localhost:8000"
    database_url: str = None  # Will be loaded from environment
    redis_url: str = None  # Added for staging/production Redis URL
    clickhouse_url: str = None  # Added for staging/production ClickHouse URL
    log_level: str = "DEBUG"
    log_secrets: bool = False
    log_async_checkout: bool = False  # Control async connection checkout debug logging
    frontend_url: str = "http://localhost:3010"
    redis: "RedisConfig" = Field(default_factory=lambda: RedisConfig())
    
    # LLM Cache Settings
    llm_cache_enabled: bool = True
    llm_cache_ttl: int = 3600  # 1 hour default
    
    # LLM Heartbeat Settings
    llm_heartbeat_enabled: bool = True
    llm_heartbeat_interval_seconds: float = 2.5  # Heartbeat every 2.5 seconds
    
    # LLM Data Logging Settings (DEBUG level)
    llm_data_logging_enabled: bool = True
    llm_data_truncate_length: int = 1000  # Characters to truncate prompts/responses
    llm_data_log_format: str = "json"  # "json" or "text" format
    llm_data_json_depth: int = 3  # Maximum depth for JSON logging
    llm_heartbeat_log_json: bool = True  # Log heartbeat as JSON
    
    # SubAgent Communication Logging Settings (INFO level)
    subagent_logging_enabled: bool = True  # Enable/disable subagent communication logging
    
    # Service modes configuration (local/shared/disabled)
    redis_mode: str = Field(
        default="shared",
        description="Redis service mode: local, shared, or disabled"
    )
    clickhouse_mode: str = Field(
        default="shared", 
        description="ClickHouse service mode: local, shared, or disabled"
    )
    llm_mode: str = Field(
        default="shared",
        description="LLM service mode: local, shared, or disabled"
    )
    
    # Service configuration is now managed through dev_launcher service config
    # Services use the mode specified in the launcher (local/shared)
    dev_mode_redis_enabled: bool = Field(
        default=True, 
        description="Redis service status (managed by dev launcher)"
    )
    dev_mode_clickhouse_enabled: bool = Field(
        default=True, 
        description="ClickHouse service status (managed by dev launcher)"
    )
    dev_mode_llm_enabled: bool = Field(
        default=True, 
        description="LLM service status (managed by dev launcher)"
    )
    
    # GitHub integration
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub token for repository access"
    )
    
    # LLM API Keys
    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Gemini API key for Google AI models"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        description="Anthropic API key for Claude models"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for GPT models"
    )
    
    # CORS configuration
    cors_origins: Optional[str] = Field(
        default=None,
        description="Allowed CORS origins - comma-separated string or '*' for all"
    )
    
    # AUTH PERMISSIVENESS CONFIGURATION (WebSocket 1011 Remediation)
    auth_permissiveness_enabled: bool = Field(
        default=True,
        description="Enable auth permissiveness system to prevent WebSocket 1011 errors"
    )
    auth_circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable auth circuit breaker for graceful degradation"
    )
    auth_strict_mode: bool = Field(
        default=None,  # Auto-detect based on environment
        description="Force strict authentication mode (None=auto-detect)"
    )
    auth_demo_mode: bool = Field(
        default=None,  # Auto-detect from DEMO_MODE env var
        description="Enable demo mode authentication bypass (None=auto-detect)"
    )
    auth_emergency_mode: bool = Field(
        default=False,
        description="Enable emergency authentication bypass when auth services are down"
    )
    auth_failure_threshold: int = Field(
        default=5,
        description="Number of consecutive failures before tripping circuit breaker"
    )
    auth_failure_rate_threshold: float = Field(
        default=0.5,
        description="Failure rate (0.0-1.0) that trips circuit breaker"
    )
    auth_circuit_open_timeout: int = Field(
        default=30,
        description="Seconds to keep circuit breaker open before testing recovery"
    )
    auth_relaxed_fallback_enabled: bool = Field(
        default=True,
        description="Enable relaxed auth fallback when circuit breaker is open"
    )
    auth_demo_fallback_enabled: bool = Field(
        default=True,
        description="Enable demo auth fallback when circuit breaker is open"
    )
    auth_emergency_fallback_enabled: bool = Field(
        default=True,
        description="Enable emergency auth fallback when all else fails"
    )
    
    # Additional middleware configuration
    disable_https_only: bool = Field(
        default=False,
        description="Disable HTTPS-only mode for sessions (dev/testing)"
    )
    
    # Agent Configuration - CRITICAL: Timeout hierarchy coordination for $200K+ MRR reliability
    agent_cache_ttl: int = Field(default=300, description="Agent cache TTL in seconds")
    agent_max_cache_size: int = Field(default=1000, description="Agent maximum cache entries")
    agent_redis_ttl: int = Field(default=3600, description="Agent Redis cache TTL in seconds")
    
    # PRIORITY 3 FIX: Cloud-native timeout configuration with WebSocket coordination
    # These values are environment-aware and managed by timeout_configuration.py
    agent_default_timeout: float = Field(default=30.0, description="Agent default execution timeout (seconds) - MUST be < WebSocket recv timeout")
    agent_thinking_timeout: float = Field(default=25.0, description="Agent thinking phase timeout (seconds)")
    agent_tool_timeout: float = Field(default=20.0, description="Agent tool execution timeout (seconds)")
    agent_completion_timeout: float = Field(default=15.0, description="Agent completion timeout (seconds)")
    agent_long_timeout: float = Field(default=300.0, description="Agent long operation timeout in seconds")
    agent_recovery_timeout: float = Field(default=45.0, description="Agent recovery timeout in seconds")
    
    agent_default_user_id: str = Field(default="default_user", description="Agent default user ID")
    agent_admin_user_id: str = Field(default="admin", description="Agent admin user ID")
    agent_max_retries: int = Field(default=3, description="Agent maximum retry attempts")
    agent_base_delay: float = Field(default=1.0, description="Agent base retry delay in seconds")
    agent_max_delay: float = Field(default=60.0, description="Agent maximum retry delay in seconds")
    agent_backoff_factor: float = Field(default=2.0, description="Agent retry backoff factor")
    agent_failure_threshold: int = Field(default=3, description="Agent failure threshold")
    agent_reset_timeout: float = Field(default=30.0, description="Agent reset timeout in seconds")
    agent_max_concurrent: int = Field(default=10, description="Agent maximum concurrent operations")
    agent_batch_size: int = Field(default=100, description="Agent batch size")
    
    # Environment detection for tests and development
    pytest_current_test: Optional[str] = Field(default=None, description="Current pytest test indicator")
    testing: Optional[str] = Field(default=None, description="Testing flag for environment detection")
    
    # Auth service configuration
    auth_service_url: str = Field(default="http://127.0.0.1:8081", description="Auth service URL")
    auth_service_enabled: str = Field(default="true", description="Auth service enabled flag")
    auth_fast_test_mode: str = Field(default="false", description="Auth fast test mode flag")
    auth_cache_ttl_seconds: str = Field(default="300", description="Auth cache TTL in seconds")
    service_id: str = Field(default=SERVICE_ID, description="Service ID for cross-service authentication (SSOT)")
    service_secret: Optional[str] = Field(
        default=None, 
        description="Shared secret for secure cross-service authentication. Must be at least 32 characters and different from JWT secret."
    )
    
    # Cloud Run environment variables
    k_service: Optional[str] = Field(default=None, description="Cloud Run service name")
    k_revision: Optional[str] = Field(default=None, description="Cloud Run service revision")
    
    # PR environment variables
    pr_number: Optional[str] = Field(default=None, description="Pull request number for PR environments")
    
    # OAuth client ID fallback variables
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID")
    google_client_secret: Optional[str] = Field(default=None, description="Google OAuth client secret")
    google_oauth_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID alternative")
    
    # Google App Engine environment variables
    gae_application: Optional[str] = Field(default=None, description="Google App Engine application ID")
    gae_version: Optional[str] = Field(default=None, description="Google App Engine version")
    
    # Google Kubernetes Engine environment variables  
    kubernetes_service_host: Optional[str] = Field(default=None, description="Kubernetes service host for GKE detection")
    
    # PostgreSQL Database Configuration (consolidated from postgres_config.py)
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=30, description="Maximum overflow connections")
    db_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    db_pool_recycle: int = Field(default=1800, description="Recycle connections every N seconds")
    db_pool_pre_ping: bool = Field(default=True, description="Test connections before using")
    db_echo: bool = Field(default=False, description="Echo SQL statements")
    db_echo_pool: bool = Field(default=False, description="Echo connection pool events")
    db_max_connections: int = Field(default=100, description="Hard limit on total connections")
    db_connection_timeout: int = Field(default=10, description="Connection establishment timeout")
    db_statement_timeout: int = Field(default=30000, description="Max statement execution time in ms")
    db_enable_read_write_split: bool = Field(default=False, description="Enable read/write splitting")
    db_read_url: Optional[str] = Field(default=None, description="Read database URL")
    db_write_url: Optional[str] = Field(default=None, description="Write database URL")
    db_enable_query_cache: bool = Field(default=True, description="Enable query caching")
    db_query_cache_ttl: int = Field(default=300, description="Query cache TTL in seconds")
    db_query_cache_size: int = Field(default=1000, description="Max cached queries")
    db_transaction_retry_attempts: int = Field(default=3, description="Transaction retry attempts")
    db_transaction_retry_delay: float = Field(default=0.1, description="Base retry delay in seconds")
    db_transaction_retry_backoff: float = Field(default=2.0, description="Exponential backoff multiplier")
    
    # Query Cache Configuration (consolidated from cache_config.py)
    cache_enabled: bool = Field(default=True, description="Enable caching system")
    cache_default_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Maximum cache entries")
    cache_strategy: str = Field(default="adaptive", description="Cache strategy: lru, ttl, or adaptive")
    cache_prefix: str = Field(default="db_query_cache:", description="Cache key prefix")
    cache_metrics_enabled: bool = Field(default=True, description="Enable cache metrics")
    cache_frequent_query_threshold: int = Field(default=5, description="Queries executed N+ times")
    cache_frequent_query_ttl_multiplier: float = Field(default=2.0, description="TTL multiplier for frequent queries")
    cache_slow_query_threshold: float = Field(default=1.0, description="Queries taking N+ seconds")
    cache_slow_query_ttl_multiplier: float = Field(default=3.0, description="TTL multiplier for slow queries")
    
    # Startup control environment variables
    fast_startup_mode: str = Field(default="false", description="Fast startup mode flag")
    skip_migrations: str = Field(default="false", description="Skip migrations flag")
    disable_startup_checks: str = Field(default="false", description="Disable startup checks flag")
    
    # OpenTelemetry configuration
    otel_enabled: str = Field(default="auto", description="OpenTelemetry telemetry enabled (auto/true/false)")
    otel_service_name: Optional[str] = Field(default=None, description="Service name for telemetry")
    otel_exporter_otlp_endpoint: Optional[str] = Field(default=None, description="OTLP endpoint for trace export")
    otel_exporter_otlp_headers: Optional[str] = Field(default=None, description="OTLP headers in key=value,key=value format")
    otel_console_exporter: str = Field(default="false", description="Enable console exporter for debugging")
    otel_instrument_fastapi: str = Field(default="true", description="Enable FastAPI automatic instrumentation")
    otel_instrument_requests: str = Field(default="true", description="Enable requests automatic instrumentation")
    otel_instrument_redis: str = Field(default="true", description="Enable Redis automatic instrumentation")
    otel_instrument_sqlalchemy: str = Field(default="true", description="Enable SQLAlchemy automatic instrumentation")
    otel_excluded_urls: str = Field(default="/health,/metrics,/docs,/openapi.json", description="URLs to exclude from telemetry")
    otel_resource_attributes: Optional[str] = Field(default=None, description="Additional resource attributes")
    
    # Service availability flags for staging infrastructure (pragmatic degradation)
    redis_optional_in_staging: bool = Field(default=False, description="Allow staging to run without Redis (graceful degradation)")
    clickhouse_optional_in_staging: bool = Field(default=False, description="Allow staging to run without ClickHouse (graceful degradation)")
    skip_redis_init: bool = Field(default=False, description="Skip Redis initialization for optional operation")
    skip_clickhouse_init: bool = Field(default=False, description="Skip ClickHouse initialization for optional operation")
    
    # Robust startup configuration
    use_robust_startup: str = Field(default="true", description="Use robust startup manager with dependency resolution")
    graceful_startup_mode: str = Field(default="true", description="Allow graceful degradation during startup")
    allow_degraded_mode: str = Field(default="true", description="Allow system to run in degraded mode if non-critical services fail")
    startup_max_retries: int = Field(default=3, description="Maximum retries for startup components")
    startup_circuit_breaker_threshold: int = Field(default=3, description="Circuit breaker failure threshold")
    startup_recovery_timeout: int = Field(default=300, description="Circuit breaker recovery timeout in seconds")
    
    # Compatibility properties for uppercase attribute access (SSOT pattern)
    @property
    def API_BASE_URL(self) -> str:
        """Compatibility alias for api_base_url."""
        return self.api_base_url
    
    @property
    def SECRET_KEY(self) -> str:
        """Compatibility alias for secret_key."""
        return self.secret_key
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        """CRITICAL: Validate SECRET_KEY security requirements for FastAPI sessions."""
        if v is None or v == "":
            raise ValueError("SECRET_KEY is required and cannot be empty")
        
        # Validate minimum length for security
        if len(v) < 32:
            raise ValueError(f"SECRET_KEY must be at least 32 characters for security, got {len(v)} characters")
        
        # Check environment - stricter validation for production environments
        env = get_env()
        current_env = env.get("ENVIRONMENT", "development").lower()
        
        # CRITICAL: Skip strict validation if we're in a test context
        # This allows test configs to use test secrets even when ENVIRONMENT=staging/production
        is_test_context = (
            env.get("PYTEST_CURRENT_TEST") or 
            env.get("TESTING") or 
            env.get("TEST_MODE") or
            'pytest' in str(env.get("_", ""))  # Check if running under pytest
        )
        
        if current_env in ["staging", "production"] and not is_test_context:
            # Additional security checks for production environments
            insecure_patterns = ['default', 'secret', 'password', 'dev', 'test', 'demo', 'example', 'change', 'admin']
            if any(pattern in v.lower() for pattern in insecure_patterns):
                raise ValueError(f"SECRET_KEY contains insecure pattern for {current_env} environment - not allowed")
            
            # Check for low entropy (basic check)
            if len(set(v)) < 8:
                raise ValueError("SECRET_KEY has insufficient entropy - too few unique characters for production")
        
        return v

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret_key(cls, v):
        """CRITICAL: Validate JWT_SECRET_KEY security requirements."""
        if v is None or v == "":
            # JWT secret key is optional in some contexts, but warn if missing
            return v
        
        # CRITICAL: Clean whitespace from secrets (common staging deployment issue)
        v = v.strip() if v else v
        
        if not v:
            # After trimming, if empty, return None
            return None
        
        # Validate minimum length for security
        if len(v) < 32:
            raise ValueError(f"JWT_SECRET_KEY must be at least 32 characters for security, got {len(v)} characters")
        
        # Check environment - stricter validation for production environments
        env = get_env()
        current_env = env.get("ENVIRONMENT", "development").lower()
        
        # CRITICAL: Skip strict validation if we're in a test context
        # This allows test configs to use test secrets even when ENVIRONMENT=staging/production
        is_test_context = (
            env.get("PYTEST_CURRENT_TEST") or 
            env.get("TESTING") or 
            env.get("TEST_MODE") or
            'pytest' in str(env.get("_", ""))  # Check if running under pytest
        )
        
        if current_env in ["staging", "production"] and not is_test_context:
            # Additional security checks for production environments
            insecure_patterns = ['default', 'secret', 'password', 'dev', 'test', 'demo', 'example', 'change', 'jwt']
            if any(pattern in v.lower() for pattern in insecure_patterns):
                raise ValueError(f"JWT_SECRET_KEY contains insecure pattern for {current_env} environment - not allowed")
        
        return v

    @field_validator('service_secret')
    @classmethod
    def validate_service_secret(cls, v):
        """CRITICAL: Validate service secret security requirements
        
        Environment-aware validation:
        - Production: Strict validation against weak patterns
        - Test/Development: Allow test values and hex strings
        """
        if v is None:
            # Allow None for backward compatibility, but log warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("service_secret not configured - this reduces security")
            return v
        
        # Validate minimum length for security
        if len(v) < 32:
            raise ValueError(f"service_secret must be at least 32 characters for security, got {len(v)}")
        
        # Note: Cross-field validation for JWT secret would require model_validator in Pydantic v2
        # This security check is handled at runtime during configuration loading
        
        # Environment-aware validation - check if we're in test environment
        from netra_backend.app.core.project_utils import is_test_environment
        is_testing = is_test_environment()
        
        # Check for hex string pattern (from openssl rand -hex 32)
        # Hex strings are valid secrets as per CLAUDE.md
        import re
        is_hex_string = re.match(r'^[a-f0-9]{32,}$', v.lower())
        
        # Additional security checks for weak patterns
        # In production: reject weak patterns
        # In test/development: allow test values and hex strings
        if not is_testing and not is_hex_string:
            weak_patterns = ['default', 'secret', 'password', 'dev-secret', 'test', 'admin', 'user']
            if any(pattern in v.lower() for pattern in weak_patterns):
                raise ValueError(f"service_secret cannot contain weak patterns like: {', '.join(weak_patterns)} (production environment)")
        
        return v

    llm_configs: Dict[str, LLMConfig] = {
        "default": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
        ),
        "analysis": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
            generation_config={"temperature": 0.5},
        ),
        "triage": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
        ),
        "data": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
        ),
        "optimizations_core": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
        ),
        "actions_to_meet_goals": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
        ),
        "reporting": LLMConfig(
            provider=LLMProvider.GOOGLE,
            model_name="gemini-2.5-pro",
        ),
    }

class DevelopmentConfig(AppConfig):
    """Development-specific settings can override defaults."""
    debug: bool = True
    database_url: str = None  # Will be loaded from environment
    dev_user_email: str = "dev@example.com"
    log_level: str = "DEBUG"
    jwt_secret_key: str = "development_secret_key_for_jwt_do_not_use_in_production"
    fernet_key: str = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="  # Generated with Fernet.generate_key()
    
    # Development telemetry settings
    otel_enabled: str = "true"
    otel_console_exporter: str = "true"  # Enable console output for development
    otel_service_name: Optional[str] = "netra-backend-dev"
    
    # OAuth configuration for development - populated by SecretReference system
    oauth_config: OAuthConfig = OAuthConfig(
        client_id="",  # Populated by SecretReference: google-client-id
        client_secret="",  # Populated by SecretReference: google-client-secret
        authorized_redirect_uris=[
            "http://localhost:8000/auth/callback",
            "http://localhost:8081/auth/callback",
            "http://localhost:8002/auth/callback",
            "http://localhost:8003/auth/callback",
            "http://localhost:8080/auth/callback",
            "http://127.0.0.1:8000/auth/callback",
            "http://127.0.0.1:8001/auth/callback",
            "http://127.0.0.1:8002/auth/callback",
            "http://127.0.0.1:8003/auth/callback",
            "http://127.0.0.1:8080/auth/callback",
            "http://localhost:3000/auth/callback",
            "http://localhost:3001/auth/callback",
            "http://localhost:3002/auth/callback"
        ]
    )
    
    def __init__(self, **data):
        """Initialize development configuration.
        
        LEGACY: This method uses direct os.environ access. Consider
        migration to unified configuration system.
        """
        # Get environment instance for loading values
        env = get_env()
        
        # LEGACY: Direct env access - should migrate to unified config
        self._load_database_url_from_unified_config(data)
        service_modes = self._get_service_modes_from_unified_config()
        self._configure_service_flags(data, service_modes)
        self._log_service_configuration(service_modes)
        
        # Load API keys from environment for development
        self._load_api_keys_from_environment(env, data)
        
        super().__init__(**data)
    
    def _load_database_url_from_unified_config(self, data: dict) -> None:
        """Load database URL from environment using DatabaseURLBuilder SSOT.
        
        Uses DatabaseURLBuilder to ensure SSOT compliance and proper URL construction.
        """
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Use IsolatedEnvironment for database URL loading
        env = get_env()
        
        # Use DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL for current environment (development config = development environment)
        database_url = builder.development.auto_url
        
        # Set the database URL from builder - NO MANUAL FALLBACKS
        if database_url:
            data['database_url'] = database_url
        else:
            # Log critical error - let the system handle missing configuration properly
            import logging
            logger = logging.getLogger(__name__)
            logger.error("DatabaseURLBuilder failed to construct URL - check environment configuration")
            # Don't set any fallback - let upstream handle the missing URL
    
    def _get_service_modes_from_unified_config(self) -> dict:
        """Get service modes from environment with fallback.
        
        Uses IsolatedEnvironment for consistent environment access.
        """
        # Use IsolatedEnvironment for service mode configuration
        env = get_env()
        return {
            'redis': env.get("REDIS_MODE", "shared").lower(),
            'clickhouse': env.get("CLICKHOUSE_MODE", "shared").lower(),
            'llm': env.get("LLM_MODE", "shared").lower()
        }
    
    def _configure_service_flags(self, data: dict, service_modes: dict) -> None:
        """Configure service enabled flags based on modes."""
        data["dev_mode_redis_enabled"] = service_modes['redis'] != "disabled"
        data["dev_mode_clickhouse_enabled"] = service_modes['clickhouse'] != "disabled"
        data["dev_mode_llm_enabled"] = service_modes['llm'] != "disabled"
    
    def _log_service_configuration(self, service_modes: dict) -> None:
        """Log service configuration for transparency."""
        import logging
        logger = logging.getLogger(__name__)
        self._log_mock_services(logger, service_modes)
    
    def _log_mock_services(self, logger, service_modes: dict) -> None:
        """Deprecated: Mock mode is not supported in development."""
        # Mock mode is only for specific testing cases, not for development
        pass
    
    def _load_api_keys_from_environment(self, env, data: dict) -> None:
        """Load API keys and service URLs from environment variables for development."""
        # Load API keys and service URLs from environment variables
        api_key_mappings = {
            'GEMINI_API_KEY': 'gemini_api_key',
            'ANTHROPIC_API_KEY': 'anthropic_api_key', 
            'OPENAI_API_KEY': 'openai_api_key',
            'AUTH_SERVICE_URL': 'auth_service_url',  # CRITICAL FIX: Load AUTH_SERVICE_URL for Issue #631
        }
        
        for env_var, field_name in api_key_mappings.items():
            api_key = env.get(env_var)
            if api_key:
                data[field_name] = api_key
        
        # Special handling for llm_configs - populate API keys from environment
        gemini_api_key = env.get('GEMINI_API_KEY')
        if gemini_api_key:
            # Create or update llm_configs with the API key populated
            data['llm_configs'] = {
                "default": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "analysis": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                    generation_config={"temperature": 0.5},
                ),
                "triage": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "data": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "optimizations_core": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "actions_to_meet_goals": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "reporting": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
            }
        
        # Load OAuth credentials from environment
        oauth_client_id = env.get('OAUTH_GOOGLE_CLIENT_ID_ENV')
        oauth_client_secret = env.get('OAUTH_GOOGLE_CLIENT_SECRET_ENV')
        
        if oauth_client_id or oauth_client_secret:
            if 'google_cloud' not in data:
                data['google_cloud'] = {}
            if 'oauth_config' not in data:
                data['oauth_config'] = {}
            
            if oauth_client_id:
                data['google_cloud']['client_id'] = oauth_client_id
                data['oauth_config']['client_id'] = oauth_client_id
            if oauth_client_secret:
                data['google_cloud']['client_secret'] = oauth_client_secret
                data['oauth_config']['client_secret'] = oauth_client_secret
        
        # Load other configuration from environment
        cors_origins = env.get('CORS_ORIGINS')
        if cors_origins:
            data['cors_origins'] = cors_origins
        
        # Load service modes from environment
        llm_mode = env.get('LLM_MODE')
        if llm_mode:
            data['llm_mode'] = llm_mode
            
        redis_mode = env.get('REDIS_MODE')
        if redis_mode:
            data['redis_mode'] = redis_mode
            
        clickhouse_mode = env.get('CLICKHOUSE_MODE')
        if clickhouse_mode:
            data['clickhouse_mode'] = clickhouse_mode

class ProductionConfig(AppConfig):
    """Production-specific settings with MANDATORY services."""
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    # Production telemetry settings
    otel_enabled: str = "true"
    otel_console_exporter: str = "false"  # Disable console output for production
    otel_service_name: Optional[str] = "netra-backend"
    
    def _load_database_url_from_unified_config_production(self, data: dict) -> None:
        """Load database URL from environment using DatabaseURLBuilder SSOT.
        
        Uses DatabaseURLBuilder to ensure SSOT compliance for production environment.
        """
        from shared.database_url_builder import DatabaseURLBuilder
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Use IsolatedEnvironment for production database URL
        env = get_env()
        
        # Check if we're in a test environment (pytest is running)
        is_testing = any('pytest' in arg or 'test' in arg.lower() for arg in __import__('sys').argv)
        
        # Use DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL for production environment
        database_url = builder.production.auto_url
        
        # Set the database URL from builder - NO MANUAL FALLBACKS
        if database_url:
            data['database_url'] = database_url
            logger.info(builder.get_safe_log_message())
        else:
            # In test environments, provide a safe fallback
            if is_testing:
                data['database_url'] = "postgresql://test:test@localhost:5432/test_netra"
                logger.warning("Using test database URL fallback during unit test execution")
            else:
                # Production MUST have a database URL - this is critical
                raise ValueError(
                    "DatabaseURLBuilder failed to construct URL for production environment. "
                    "Ensure POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are set, "
                    "or #removed-legacyis provided."
                )
    
    def __init__(self, **data):
        """Initialize production config."""
        # Get environment instance for loading values
        env = get_env()
        
        # CRITICAL: Load secrets FIRST as they may be needed by database URL
        self._load_secrets_from_environment(data)
        # Load API keys from environment for production
        self._load_api_keys_from_environment(env, data)
        # Load database URL after secrets are available
        self._load_database_url_from_unified_config_production(data)
        super().__init__(**data)
        # Validation moved to validate_mandatory_services() to be called after population
    
    def _load_secrets_from_environment(self, data: dict) -> None:
        """Load critical secrets from environment variables.
        
        This ensures SERVICE_SECRET, JWT_SECRET_KEY, and other critical
        secrets are loaded from Google Secret Manager or environment.
        """
        from shared.isolated_environment import get_env
        import logging
        
        logger = logging.getLogger(__name__)
        env = get_env()
        
        # Load critical secrets that may come from Google Secret Manager
        critical_secrets = [
            ('SERVICE_SECRET', 'service_secret'),
            ('SERVICE_ID', 'service_id'),
            ('JWT_SECRET_KEY', 'jwt_secret_key'),
            ('SECRET_KEY', 'secret_key'),
            ('FERNET_KEY', 'fernet_key'),
        ]
        
        for env_name, config_name in critical_secrets:
            # Use get() method which IsolatedEnvironment supports
            env_value = env.get(env_name)
            # CRITICAL FIX: Always override with env value if present, even if data has None
            if env_value:
                data[config_name] = env_value
                logger.info(f"Loaded {env_name} from environment")
        
        # Log what's loaded for debugging
        logger.info(f"SERVICE_ID configured: {bool(data.get('service_id'))}")
        logger.info(f"SERVICE_SECRET configured: {bool(data.get('service_secret'))}")
    
    def _load_api_keys_from_environment(self, env, data: dict) -> None:
        """Load API keys and service URLs from environment variables for production."""
        # Load API keys and service URLs from environment variables
        api_key_mappings = {
            'GEMINI_API_KEY': 'gemini_api_key',
            'ANTHROPIC_API_KEY': 'anthropic_api_key', 
            'OPENAI_API_KEY': 'openai_api_key',
            'AUTH_SERVICE_URL': 'auth_service_url',  # CRITICAL FIX: Load AUTH_SERVICE_URL for Issue #631
        }
        
        for env_var, field_name in api_key_mappings.items():
            api_key = env.get(env_var)
            if api_key:
                data[field_name] = api_key
        
        # Special handling for llm_configs - populate API keys from environment
        gemini_api_key = env.get('GEMINI_API_KEY')
        if gemini_api_key:
            # Create or update llm_configs with the API key populated
            data['llm_configs'] = {
                "default": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "analysis": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                    generation_config={"temperature": 0.5},
                ),
                "triage": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "data": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "optimizations_core": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "actions_to_meet_goals": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "reporting": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
            }
        
        # Load OAuth credentials from environment
        oauth_client_id = env.get('OAUTH_GOOGLE_CLIENT_ID_ENV') or env.get('GOOGLE_CLIENT_ID')
        oauth_client_secret = env.get('OAUTH_GOOGLE_CLIENT_SECRET_ENV') or env.get('GOOGLE_CLIENT_SECRET')
        
        if oauth_client_id or oauth_client_secret:
            if 'google_cloud' not in data:
                data['google_cloud'] = {}
            if 'oauth_config' not in data:
                data['oauth_config'] = {}
            
            if oauth_client_id:
                data['google_cloud']['client_id'] = oauth_client_id
                data['oauth_config']['client_id'] = oauth_client_id
            if oauth_client_secret:
                data['google_cloud']['client_secret'] = oauth_client_secret
                data['oauth_config']['client_secret'] = oauth_client_secret
        
        # Load other configuration from environment
        cors_origins = env.get('CORS_ORIGINS')
        if cors_origins:
            data['cors_origins'] = cors_origins
        
        # Load service modes from environment
        llm_mode = env.get('LLM_MODE')
        if llm_mode:
            data['llm_mode'] = llm_mode
            
        redis_mode = env.get('REDIS_MODE')
        if redis_mode:
            data['redis_mode'] = redis_mode
            
        clickhouse_mode = env.get('CLICKHOUSE_MODE')
        if clickhouse_mode:
            data['clickhouse_mode'] = clickhouse_mode
        
        # Load GitHub token
        github_token = env.get('GITHUB_TOKEN')
        if github_token:
            data['github_token'] = github_token
    
    def validate_mandatory_services(self):
        """Validate that all mandatory services are configured for production."""
        # CRITICAL: ClickHouse is MANDATORY in production
        if not self.clickhouse_native.host and not self.clickhouse_https.host:
            raise ValueError(
                "ClickHouse configuration is MANDATORY in production. "
                "Set either clickhouse_native.host or clickhouse_https.host"
            )
        
        # CRITICAL: Redis is MANDATORY in production
        if not self.redis.host:
            raise ValueError(
                "Redis configuration is MANDATORY in production. "
                "Set redis.host with valid Redis server address"
            )
        
        # CRITICAL: JWT secret is MANDATORY in production
        if not self.jwt_secret_key:
            raise ValueError(
                "JWT_SECRET_KEY is MANDATORY in production. "
                "Set a secure JWT secret of at least 32 characters"
            )

class StagingConfig(AppConfig):
    """Staging-specific settings with MANDATORY services."""
    environment: str = "staging"
    debug: bool = False
    log_level: str = "INFO"
    
    # CRITICAL FIX: Override localhost defaults with proper staging URLs  
    # This fixes validation failures where StagingConfig inherits localhost URLs from AppConfig
    # Issue resolved: Configuration validation failed for environment 'staging'
    frontend_url: str = "https://app.staging.netrasystems.ai"
    api_base_url: str = "https://api.staging.netrasystems.ai" 
    auth_service_url: str = "https://auth.staging.netrasystems.ai"
    
    # Staging telemetry settings
    otel_enabled: str = "true"
    otel_console_exporter: str = "false"  # Disable console output for staging
    otel_service_name: Optional[str] = "netra-backend-staging"
    
    # CRITICAL: Remove optional flags - services are MANDATORY
    redis_optional_in_staging: bool = False  # Redis is MANDATORY
    clickhouse_optional_in_staging: bool = False  # ClickHouse is MANDATORY
    skip_redis_init: bool = False
    
    def __init__(self, **data):
        """Initialize staging config."""
        # Get environment instance for loading values
        env = get_env()
        
        # CRITICAL: Load secrets FIRST as they may be needed by database URL
        self._load_secrets_from_environment(data)
        # Load API keys from environment for staging
        self._load_api_keys_from_environment(env, data)
        # Load database URL after secrets are available
        self._load_database_url_from_unified_config_staging(data)
        super().__init__(**data)
        # Validation moved to validate_mandatory_services() to be called after population
    
    def _load_secrets_from_environment(self, data: dict) -> None:
        """Load critical secrets from environment variables.
        
        This ensures SERVICE_SECRET, JWT_SECRET_KEY, and other critical
        secrets are loaded from Google Secret Manager or environment.
        """
        from shared.isolated_environment import get_env
        import logging
        
        logger = logging.getLogger(__name__)
        env = get_env()
        
        # Load critical secrets that may come from Google Secret Manager
        critical_secrets = [
            ('SERVICE_SECRET', 'service_secret'),
            ('SERVICE_ID', 'service_id'),
            ('JWT_SECRET_KEY', 'jwt_secret_key'),
            ('SECRET_KEY', 'secret_key'),
            ('FERNET_KEY', 'fernet_key'),
        ]
        
        for env_name, config_name in critical_secrets:
            # Use get() method which IsolatedEnvironment supports
            env_value = env.get(env_name)
            # CRITICAL FIX: Always override with env value if present, even if data has None
            if env_value:
                data[config_name] = env_value
                logger.info(f"Loaded {env_name} from environment")
        
        # Log what's loaded for debugging
        logger.info(f"SERVICE_ID configured: {bool(data.get('service_id'))}")
        logger.info(f"SERVICE_SECRET configured: {bool(data.get('service_secret'))}")
    
    def _load_api_keys_from_environment(self, env, data: dict) -> None:
        """Load API keys and service URLs from environment variables for staging."""
        # Load API keys and service URLs from environment variables
        api_key_mappings = {
            'GEMINI_API_KEY': 'gemini_api_key',
            'ANTHROPIC_API_KEY': 'anthropic_api_key', 
            'OPENAI_API_KEY': 'openai_api_key',
            'AUTH_SERVICE_URL': 'auth_service_url',  # CRITICAL FIX: Load AUTH_SERVICE_URL for Issue #631
        }
        
        for env_var, field_name in api_key_mappings.items():
            api_key = env.get(env_var)
            if api_key:
                data[field_name] = api_key
        
        # Special handling for llm_configs - populate API keys from environment
        gemini_api_key = env.get('GEMINI_API_KEY')
        if gemini_api_key:
            # Create or update llm_configs with the API key populated
            data['llm_configs'] = {
                "default": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "analysis": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                    generation_config={"temperature": 0.5},
                ),
                "triage": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "data": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "optimizations_core": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "actions_to_meet_goals": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "reporting": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
            }
        
        # Load OAuth credentials from environment (with additional staging fallbacks)
        oauth_client_id = (env.get('OAUTH_GOOGLE_CLIENT_ID_ENV') or 
                          env.get('GOOGLE_CLIENT_ID') or 
                          env.get('GOOGLE_OAUTH_CLIENT_ID'))
        oauth_client_secret = (env.get('OAUTH_GOOGLE_CLIENT_SECRET_ENV') or 
                              env.get('GOOGLE_CLIENT_SECRET') or 
                              env.get('GOOGLE_OAUTH_CLIENT_SECRET'))
        
        if oauth_client_id or oauth_client_secret:
            if 'google_cloud' not in data:
                data['google_cloud'] = {}
            if 'oauth_config' not in data:
                data['oauth_config'] = {}
            
            if oauth_client_id:
                data['google_cloud']['client_id'] = oauth_client_id
                data['oauth_config']['client_id'] = oauth_client_id
            if oauth_client_secret:
                data['google_cloud']['client_secret'] = oauth_client_secret
                data['oauth_config']['client_secret'] = oauth_client_secret
        
        # Load other configuration from environment
        cors_origins = env.get('CORS_ORIGINS')
        if cors_origins:
            data['cors_origins'] = cors_origins
        
        # Load service modes from environment
        llm_mode = env.get('LLM_MODE')
        if llm_mode:
            data['llm_mode'] = llm_mode
            
        redis_mode = env.get('REDIS_MODE')
        if redis_mode:
            data['redis_mode'] = redis_mode
            
        clickhouse_mode = env.get('CLICKHOUSE_MODE')
        if clickhouse_mode:
            data['clickhouse_mode'] = clickhouse_mode
        
        # Load GitHub token
        github_token = env.get('GITHUB_TOKEN')
        if github_token:
            data['github_token'] = github_token
        
        # Load Redis URL for staging
        redis_url = env.get('REDIS_URL')
        if redis_url:
            data['redis_url'] = redis_url

        # Load Redis configuration for staging
        redis_host = env.get('REDIS_HOST')
        redis_port = env.get('REDIS_PORT')
        redis_password = env.get('REDIS_PASSWORD')
        redis_db = env.get('REDIS_DB')
        redis_ssl = env.get('REDIS_SSL')

        # Ensure we have redis configuration dictionary
        if 'redis' not in data:
            data['redis'] = {}

        # Load Redis configuration values if available
        if redis_host:
            data['redis']['host'] = redis_host
        if redis_port:
            try:
                data['redis']['port'] = int(redis_port)
            except (ValueError, TypeError):
                pass
        if redis_password:
            data['redis']['password'] = redis_password
        if redis_db:
            try:
                data['redis']['db'] = int(redis_db)
            except (ValueError, TypeError):
                pass
        if redis_ssl:
            data['redis']['ssl'] = redis_ssl.lower() in ('true', '1', 'yes', 'on')

        # If we have any Redis configuration, create RedisConfig with our data
        if redis_host or redis_port or redis_password or redis_db or redis_ssl:
            data['redis'] = RedisConfig(**data['redis'])

        # Load ClickHouse configuration for staging
        clickhouse_host = env.get('CLICKHOUSE_HOST')
        clickhouse_port = env.get('CLICKHOUSE_PORT')
        clickhouse_password = env.get('CLICKHOUSE_PASSWORD')
        
        if clickhouse_host:
            if 'clickhouse_native' not in data:
                data['clickhouse_native'] = {}
            if 'clickhouse_https' not in data:
                data['clickhouse_https'] = {}
            data['clickhouse_native']['host'] = clickhouse_host
            data['clickhouse_https']['host'] = clickhouse_host
            
        if clickhouse_port:
            try:
                port_value = int(clickhouse_port)
                if 'clickhouse_native' not in data:
                    data['clickhouse_native'] = {}
                data['clickhouse_native']['port'] = port_value
            except (ValueError, TypeError):
                pass
                
        if clickhouse_password:
            if 'clickhouse_native' not in data:
                data['clickhouse_native'] = {}
            if 'clickhouse_https' not in data:
                data['clickhouse_https'] = {}
            data['clickhouse_native']['password'] = clickhouse_password
            data['clickhouse_https']['password'] = clickhouse_password
    
    def validate_mandatory_services(self):
        """Validate that all mandatory services are configured for staging."""
        # CRITICAL: ClickHouse is MANDATORY in staging
        if not self.clickhouse_native.host and not self.clickhouse_https.host:
            raise ValueError(
                "ClickHouse configuration is MANDATORY in staging. "
                "Set either clickhouse_native.host or clickhouse_https.host"
            )
        
        # CRITICAL: Redis is MANDATORY in staging
        if not self.redis.host:
            raise ValueError(
                "Redis configuration is MANDATORY in staging. "
                "Set redis.host with valid Redis server address"
            )
        
        # CRITICAL: JWT secret is MANDATORY in staging
        if not self.jwt_secret_key:
            raise ValueError(
                "JWT_SECRET_KEY is MANDATORY in staging. "
                "Set a secure JWT secret of at least 32 characters"
            )
    
    def _load_database_url_from_unified_config_staging(self, data: dict) -> None:
        """Load database URL from environment using DatabaseURLBuilder SSOT.
        
        Uses DatabaseURLBuilder to ensure SSOT compliance for staging environment.
        """
        from shared.database_url_builder import DatabaseURLBuilder
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Use IsolatedEnvironment for staging database URL
        env = get_env()
        
        # Check if we're in a test environment (pytest is running)
        is_testing = any('pytest' in arg or 'test' in arg.lower() for arg in __import__('sys').argv)
        
        # Use DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH
        builder = DatabaseURLBuilder(env.as_dict())
        
        # Get URL for staging environment
        database_url = builder.staging.auto_url
        
        # Set the database URL from builder - NO MANUAL FALLBACKS
        if database_url:
            data['database_url'] = database_url
            logger.info(builder.get_safe_log_message())
        else:
            # In test environments, provide a safe fallback
            if is_testing:
                data['database_url'] = "postgresql://test:test@localhost:5432/test_netra_staging"
                logger.warning("Using test staging database URL fallback during unit test execution")
            else:
                # Staging MUST have a database URL - this is critical
                raise ValueError(
                    "DatabaseURLBuilder failed to construct URL for staging environment. "
                    "Ensure POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are set, "
                    "or #removed-legacyis provided."
                )
    

class NetraTestingConfig(AppConfig):
    """Testing-specific settings."""
    environment: str = "testing"
    # database_url will be set dynamically via DatabaseURLBuilder in __init__
    auth_service_url: str = "http://localhost:8081"
    fast_startup_mode: str = "true"  # Enable fast startup for tests
    service_secret: str = "mock-service-auth-key-for-cross-service-auth-32-chars-minimum-length"  # Test-safe default
    jwt_secret_key: str = "mock_jwt_auth_key_for_checking_32_chars_minimum_required_length"  # Test-safe JWT secret
    fernet_key: str = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="  # Test-safe Fernet key (same as dev)
    secret_key: str = "mock-fastapi-session-secret-key-for-testing-32-chars-minimum-required"  # Test-safe SECRET_KEY (32+ chars)
    
    # Testing telemetry settings
    otel_enabled: str = "false"  # Disabled by default for tests to avoid overhead
    otel_console_exporter: str = "true"  # Enable console output when telemetry is enabled for debugging
    otel_service_name: Optional[str] = "netra-backend-test"
    
    def __init__(self, **data):
        """Initialize test configuration using DatabaseURLBuilder."""
        from shared.database_url_builder import DatabaseURLBuilder
        from shared.isolated_environment import get_env
        import os
        
        env = get_env()
        
        # CRITICAL FIX: For test scenarios using patch.dict(os.environ), we need to 
        # merge isolated variables with os.environ, giving priority to os.environ
        env_dict = env.as_dict()
        for key, value in os.environ.items():
            if key not in env_dict or env_dict[key] != value:
                env_dict[key] = value
        
        # Use DatabaseURLBuilder as the SINGLE SOURCE OF TRUTH
        builder = DatabaseURLBuilder(env_dict)
        
        # Get URL for test environment - uses DatabaseURLBuilder SSOT test.auto_url which handles environment variables or test defaults
        database_url = builder.test.auto_url
        
        if database_url:
            data['database_url'] = database_url
        else:
            # For tests, if no URL available, let it fail properly
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("No database URL available from DatabaseURLBuilder for test environment")
        
        # Load API keys from environment for testing (use corrected environment)
        self._load_api_keys_from_environment_corrected(env_dict, data)
        
        super().__init__(**data)
    
    def _load_api_keys_from_environment_corrected(self, env_dict: dict, data: dict) -> None:
        """Load API keys and service URLs from corrected environment dictionary for testing."""
        # Helper function to get values from environment dictionary
        def get_env_value(key):
            return env_dict.get(key)
        
        # Load API keys and service URLs from environment variables
        api_key_mappings = {
            'GEMINI_API_KEY': 'gemini_api_key',
            'ANTHROPIC_API_KEY': 'anthropic_api_key', 
            'OPENAI_API_KEY': 'openai_api_key',
            'AUTH_SERVICE_URL': 'auth_service_url',  # CRITICAL FIX: Load AUTH_SERVICE_URL for Issue #631
        }
        
        for env_var, field_name in api_key_mappings.items():
            api_key = get_env_value(env_var)
            if api_key:
                data[field_name] = api_key
        
        # Load security keys from environment (override defaults if they meet validation criteria)
        security_key_mappings = {
            'SECRET_KEY': 'secret_key',  # CRITICAL FIX: Load SECRET_KEY for FastAPI sessions
            'JWT_SECRET_KEY': 'jwt_secret_key',
            'FERNET_KEY': 'fernet_key',
            'SERVICE_SECRET': 'service_secret',
        }
        
        for env_var, field_name in security_key_mappings.items():
            key_value = get_env_value(env_var)
            if key_value:
                # CRITICAL FIX: For SECRET_KEY, only override if it meets length requirements
                # This prevents validation failures that cause fallback to basic AppConfig
                if field_name == 'secret_key' and len(key_value) < 32:
                    # Keep the class default (32+ chars) instead of environment value
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Ignoring environment {env_var} (length: {len(key_value)}) - using test-safe default instead")
                    continue
                data[field_name] = key_value
        
        # Load OAuth credentials from environment (test environment uses TEST suffix)
        oauth_client_id = get_env_value('GOOGLE_OAUTH_CLIENT_ID_TEST')
        oauth_client_secret = get_env_value('GOOGLE_OAUTH_CLIENT_SECRET_TEST')
        
        if oauth_client_id or oauth_client_secret:
            if 'google_cloud' not in data:
                data['google_cloud'] = {}
            if 'oauth_config' not in data:
                data['oauth_config'] = {}
            
            if oauth_client_id:
                data['google_cloud']['client_id'] = oauth_client_id
                data['oauth_config']['client_id'] = oauth_client_id
            if oauth_client_secret:
                data['google_cloud']['client_secret'] = oauth_client_secret
                data['oauth_config']['client_secret'] = oauth_client_secret
        
        # Load REDIS_URL from corrected environment
        redis_url = get_env_value('REDIS_URL')
        if redis_url:
            data['redis_url'] = redis_url
        
        # Load ClickHouse configuration from corrected environment
        clickhouse_host = get_env_value('CLICKHOUSE_HOST')
        clickhouse_port = get_env_value('CLICKHOUSE_PORT')
        clickhouse_user = get_env_value('CLICKHOUSE_USER')
        clickhouse_password = get_env_value('CLICKHOUSE_PASSWORD')
        clickhouse_database = get_env_value('CLICKHOUSE_DATABASE') or get_env_value('CLICKHOUSE_DB')
        
        # CRITICAL FIX: Provide test-safe ClickHouse defaults for validation compliance
        # This ensures tests work with --no-docker flag without breaking SSOT validation
        if 'clickhouse_native' not in data:
            data['clickhouse_native'] = {}
        if 'clickhouse_https' not in data:
            data['clickhouse_https'] = {}
            
        # Set defaults first (test-safe values that pass validation)
        test_clickhouse_defaults = {
            'host': 'localhost',  # Valid non-empty host for validation
            'port': 8126,         # Docker test port or safe default
            'user': 'test',       # Test user
            'password': 'test',   # Test password
            'database': 'test_analytics'  # Test database
        }
        
        # Apply defaults to both native and https configs
        for config_key in ['clickhouse_native', 'clickhouse_https']:
            for field, default_value in test_clickhouse_defaults.items():
                data[config_key][field] = default_value
        
        # Override with environment variables if present (SSOT principle)
        if clickhouse_host or clickhouse_port or clickhouse_user or clickhouse_password or clickhouse_database:
            if clickhouse_host:
                data['clickhouse_native']['host'] = clickhouse_host
                data['clickhouse_https']['host'] = clickhouse_host
            if clickhouse_port:
                try:
                    port_value = int(clickhouse_port)
                    data['clickhouse_native']['port'] = port_value
                    # Also set HTTPS port for test compatibility
                    data['clickhouse_https']['port'] = port_value
                except (ValueError, TypeError):
                    pass
            if clickhouse_user:
                data['clickhouse_native']['user'] = clickhouse_user
                data['clickhouse_https']['user'] = clickhouse_user
            if clickhouse_password:
                data['clickhouse_native']['password'] = clickhouse_password
                data['clickhouse_https']['password'] = clickhouse_password
            if clickhouse_database:
                data['clickhouse_native']['database'] = clickhouse_database
                data['clickhouse_https']['database'] = clickhouse_database
    
    def _load_api_keys_from_environment(self, env, data: dict) -> None:
        """Load API keys from environment variables for testing."""
        # Load API keys from environment variables
        api_key_mappings = {
            'GEMINI_API_KEY': 'gemini_api_key',
            'ANTHROPIC_API_KEY': 'anthropic_api_key', 
            'OPENAI_API_KEY': 'openai_api_key',
        }
        
        for env_var, field_name in api_key_mappings.items():
            api_key = env.get(env_var)
            if api_key:
                data[field_name] = api_key
        
        # Load security keys from environment (override defaults)
        security_key_mappings = {
            'SECRET_KEY': 'secret_key',  # CRITICAL FIX: Load SECRET_KEY for FastAPI sessions
            'JWT_SECRET_KEY': 'jwt_secret_key',
            'FERNET_KEY': 'fernet_key',
            'SERVICE_SECRET': 'service_secret',
        }
        
        for env_var, field_name in security_key_mappings.items():
            key_value = env.get(env_var)
            if key_value:
                data[field_name] = key_value
        
        # Special handling for llm_configs - populate API keys from environment
        gemini_api_key = env.get('GEMINI_API_KEY')
        if gemini_api_key:
            # Create or update llm_configs with the API key populated
            data['llm_configs'] = {
                "default": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "analysis": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                    generation_config={"temperature": 0.5},
                ),
                "triage": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "data": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "optimizations_core": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "actions_to_meet_goals": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
                "reporting": LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model_name="gemini-2.5-pro",
                    api_key=gemini_api_key,
                ),
            }
        
        # Load OAuth credentials from environment (test environment uses TEST suffix)
        oauth_client_id = env.get('GOOGLE_OAUTH_CLIENT_ID_TEST')
        oauth_client_secret = env.get('GOOGLE_OAUTH_CLIENT_SECRET_TEST')
        
        if oauth_client_id or oauth_client_secret:
            if 'google_cloud' not in data:
                data['google_cloud'] = {}
            if 'oauth_config' not in data:
                data['oauth_config'] = {}
            
            if oauth_client_id:
                data['google_cloud']['client_id'] = oauth_client_id
                data['oauth_config']['client_id'] = oauth_client_id
            if oauth_client_secret:
                data['google_cloud']['client_secret'] = oauth_client_secret
                data['oauth_config']['client_secret'] = oauth_client_secret
        
        # Load other configuration from environment
        cors_origins = env.get('CORS_ORIGINS')
        if cors_origins:
            data['cors_origins'] = cors_origins
        
        # Load service modes from environment
        llm_mode = env.get('LLM_MODE')
        if llm_mode:
            data['llm_mode'] = llm_mode
            
        redis_mode = env.get('REDIS_MODE')
        if redis_mode:
            data['redis_mode'] = redis_mode
            
        clickhouse_mode = env.get('CLICKHOUSE_MODE')
        if clickhouse_mode:
            data['clickhouse_mode'] = clickhouse_mode
        
        # Load database configuration
        # NOTE: Database configuration is handled by DatabaseURLBuilder in __init__ via SSOT patterns - don't override it here
        
        redis_url = env.get('REDIS_URL')
        if redis_url:
            data['redis_url'] = redis_url
        
        # Load ClickHouse configuration
        clickhouse_host = env.get('CLICKHOUSE_HOST')
        clickhouse_port = env.get('CLICKHOUSE_PORT')
        clickhouse_password = env.get('CLICKHOUSE_PASSWORD')
        
        if clickhouse_host or clickhouse_port or clickhouse_password:
            if 'clickhouse_native' not in data:
                data['clickhouse_native'] = {}
            if clickhouse_host:
                data['clickhouse_native']['host'] = clickhouse_host
            if clickhouse_port:
                try:
                    data['clickhouse_native']['port'] = int(clickhouse_port)
                except (ValueError, TypeError):
                    pass
            if clickhouse_password:
                data['clickhouse_native']['password'] = clickhouse_password

class LLMProvider(str, Enum):
    """LLM provider enum for configuration schemas (local to avoid circular imports)."""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    MOCK = "mock"

