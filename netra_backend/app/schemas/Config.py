import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from netra_backend.app.schemas.auth_types import AuthEndpoints, AuthConfigResponse, DevUser
from netra_backend.app.registry import User
from netra_backend.app.llm_types import LLMProvider

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
    project_id: str = Field(default_factory=lambda: os.environ.get("GCP_PROJECT_ID_NUMERICAL_STAGING", 
                                                                   os.environ.get("SECRET_MANAGER_PROJECT_ID", 
                                                                   "701982941522" if os.environ.get("ENVIRONMENT", "").lower() == "staging" else "304612253870")))
    version: str = "latest"


SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_models=["llm_configs.default", "llm_configs.triage", "llm_configs.data", "llm_configs.optimizations_core", "llm_configs.actions_to_meet_goals", "llm_configs.reporting", "llm_configs.google", "llm_configs.analysis"], target_field="api_key"),
    SecretReference(name="google-client-id", target_models=["google_cloud", "oauth_config"], target_field="client_id"),
    SecretReference(name="google-client-secret", target_models=["google_cloud", "oauth_config"], target_field="client_secret"),
    SecretReference(name="langfuse-secret-key", target_models=["langfuse"], target_field="secret_key"),
    SecretReference(name="langfuse-public-key", target_models=["langfuse"], target_field="public_key"),
    SecretReference(name="clickhouse-default-password", target_models=["clickhouse_native", "clickhouse_https"], target_field="password"),
    SecretReference(name="jwt-secret-key", target_field="jwt_secret_key"),
    SecretReference(name="fernet-key", target_field="fernet_key"),
    SecretReference(name="redis-default", target_models=["redis"], target_field="password"),
    SecretReference(name="github-token", target_field="github_token"),
]

class RedisConfig(BaseModel):
    host: str = 'redis-10504.fcrce190.us-east-1-1.ec2.redns.redis-cloud.com'
    port: int = 10504
    username: str = "default"
    password: Optional[str] = None

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
    host: str = "clickhouse_host_url_placeholder"
    port: int = 9440
    user: str = "default"
    password: str = ""
    database: str = "default"

class ClickHouseHTTPSConfig(BaseModel):
    host: str = "clickhouse_host_url_placeholder"
    port: int = 8443
    user: str = "default"
    password: str = ""
    database: str = "default"



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

class AppConfig(BaseModel):
    """Base configuration class."""

    environment: str = "development"
    app_name: str = "netra"  # Application name for identification
    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    oauth_config: OAuthConfig = Field(default_factory=OAuthConfig)
    clickhouse_native: ClickHouseNativeConfig = ClickHouseNativeConfig()
    clickhouse_https: ClickHouseHTTPSConfig = ClickHouseHTTPSConfig()
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
    
    # Service modes configuration (local/shared/mock/disabled)
    redis_mode: str = Field(
        default="shared",
        description="Redis service mode: local, shared, mock, or disabled"
    )
    clickhouse_mode: str = Field(
        default="shared", 
        description="ClickHouse service mode: local, shared, mock, or disabled"
    )
    llm_mode: str = Field(
        default="shared",
        description="LLM service mode: local, shared, mock, or disabled"
    )
    
    # Service configuration is now managed through dev_launcher service config
    # Services use the mode specified in the launcher (local/shared/mock)
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
    
    # CORS configuration
    cors_origins: Optional[List[str]] = Field(
        default=None,
        description="Allowed CORS origins - can be list or comma-separated string"
    )
    
    # Additional middleware configuration
    disable_https_only: bool = Field(
        default=False,
        description="Disable HTTPS-only mode for sessions (dev/testing)"
    )
    
    # Agent Configuration
    agent_cache_ttl: int = Field(default=300, description="Agent cache TTL in seconds")
    agent_max_cache_size: int = Field(default=1000, description="Agent maximum cache entries")
    agent_redis_ttl: int = Field(default=3600, description="Agent Redis cache TTL in seconds")
    agent_default_timeout: float = Field(default=30.0, description="Agent default timeout in seconds")
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
    service_id: str = Field(default="backend", description="Service ID for authentication")
    service_secret: Optional[str] = Field(default=None, description="Service secret for authentication")
    
    # Cloud Run environment variables
    k_service: Optional[str] = Field(default=None, description="Cloud Run service name")
    k_revision: Optional[str] = Field(default=None, description="Cloud Run service revision")
    
    # PR environment variables
    pr_number: Optional[str] = Field(default=None, description="Pull request number for PR environments")
    
    # OAuth client ID fallback variables
    google_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID fallback")
    google_oauth_client_id: Optional[str] = Field(default=None, description="Google OAuth client ID alternative")
    
    # Google App Engine environment variables
    gae_application: Optional[str] = Field(default=None, description="Google App Engine application ID")
    gae_version: Optional[str] = Field(default=None, description="Google App Engine version")
    
    # Google Kubernetes Engine environment variables  
    kubernetes_service_host: Optional[str] = Field(default=None, description="Kubernetes service host for GKE detection")
    
    # Startup control environment variables
    fast_startup_mode: str = Field(default="false", description="Fast startup mode flag")
    skip_migrations: str = Field(default="false", description="Skip migrations flag")
    disable_startup_checks: str = Field(default="false", description="Disable startup checks flag")

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
    
    # OAuth configuration for development - populated by SecretReference system
    oauth_config: OAuthConfig = OAuthConfig(
        client_id="",  # Populated by SecretReference: google-client-id
        client_secret="",  # Populated by SecretReference: google-client-secret
        authorized_redirect_uris=[
            "http://localhost:8000/api/auth/callback",
            "http://localhost:8001/api/auth/callback",
            "http://localhost:8002/api/auth/callback",
            "http://localhost:8003/api/auth/callback",
            "http://localhost:8080/api/auth/callback",
            "http://127.0.0.1:8000/api/auth/callback",
            "http://127.0.0.1:8001/api/auth/callback",
            "http://127.0.0.1:8002/api/auth/callback",
            "http://127.0.0.1:8003/api/auth/callback",
            "http://127.0.0.1:8080/api/auth/callback",
            "http://localhost:3000/auth/callback",
            "http://localhost:3001/auth/callback",
            "http://localhost:3002/auth/callback"
        ]
    )
    
    def __init__(self, **data):
        import os
        self._load_database_url(data, os)
        service_modes = self._get_service_modes(os)
        self._configure_service_flags(data, service_modes)
        self._log_service_configuration(service_modes)
        super().__init__(**data)
    
    def _load_database_url(self, data: dict, os_module) -> None:
        """Load database URL from environment - always prefer environment over defaults."""
        env_db_url = os_module.environ.get('DATABASE_URL')
        if env_db_url:
            data['database_url'] = env_db_url
        elif 'database_url' not in data or data.get('database_url') is None:
            # Fallback only if no env var and no value provided
            data['database_url'] = "postgresql+asyncpg://postgres:postgres@localhost:5432/netra"
    
    def _get_service_modes(self, os_module) -> dict:
        """Get service modes from environment variables."""
        return {
            'redis': os_module.environ.get("REDIS_MODE", "shared").lower(),
            'clickhouse': os_module.environ.get("CLICKHOUSE_MODE", "shared").lower(),
            'llm': os_module.environ.get("LLM_MODE", "shared").lower()
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
        """Log which services are running in mock mode."""
        mock_messages = self._get_mock_messages()
        self._log_services_in_mock_mode(logger, service_modes, mock_messages)
    
    def _get_mock_messages(self) -> dict:
        """Get dictionary of mock service messages."""
        return {
            'redis': "Redis running in MOCK mode",
            'clickhouse': "ClickHouse running in MOCK mode",
            'llm': "LLM running in MOCK mode"
        }
    
    def _log_services_in_mock_mode(self, logger, service_modes: dict, mock_messages: dict) -> None:
        """Log each service that is in mock mode."""
        for service, mode in service_modes.items():
            if mode == "mock":
                logger.info(mock_messages[service])

class ProductionConfig(AppConfig):
    """Production-specific settings."""
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

class StagingConfig(AppConfig):
    """Staging-specific settings."""
    environment: str = "staging"
    debug: bool = False
    log_level: str = "INFO"
    # Staging uses production-like settings but with relaxed validation
    
    def __init__(self, **data):
        """Initialize staging config with environment variables."""
        import os
        # Load database URL from environment if not provided
        if 'database_url' not in data and os.environ.get('DATABASE_URL'):
            data['database_url'] = os.environ.get('DATABASE_URL')
        super().__init__(**data)
    
class NetraTestingConfig(AppConfig):
    """Testing-specific settings."""
    environment: str = "testing"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra_test"
    auth_service_url: str = "http://localhost:8001"
    fast_startup_mode: str = "true"  # Enable fast startup for tests