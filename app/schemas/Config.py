from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from .Auth import AuthEndpoints, AuthConfigResponse, DevUser
from .User import User

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
    project_id: str = "304612253870"
    version: str = "latest"


SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_models=["llm_configs.default", "llm_configs.triage", "llm_configs.data", "llm_configs.optimizations_core", "llm_configs.actions_to_meet_goals", "llm_configs.reporting", "llm_configs.google", "llm_configs.analysis"], target_field="api_key"),
    SecretReference(name="google-client-id", target_models=["google_cloud", "oauth_config"], target_field="client_id"),
    SecretReference(name="google-client-secret", target_models=["google_cloud", "oauth_config"], target_field="client_secret"),
    SecretReference(name="langfuse-secret-key", target_models=["langfuse"], target_field="secret_key"),
    SecretReference(name="langfuse-public-key", target_models=["langfuse"], target_field="public_key"),
    SecretReference(name="clickhouse-default-password", target_models=["clickhouse_native", "clickhouse_https"], target_field="password"),
    SecretReference(name="clickhouse-development-password", target_models=["clickhouse_https_dev"], target_field="password"),
    SecretReference(name="jwt-secret-key", target_field="jwt_secret_key"),
    SecretReference(name="fernet-key", target_field="fernet_key"),
    SecretReference(name="redis-default", target_models=["redis"], target_field="password"),
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
    host: str = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    port: int = 9440
    user: str = "default"
    password: str = ""
    database: str = "default"

class ClickHouseHTTPSConfig(BaseModel):
    host: str = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    port: int = 8443
    user: str = "default"
    password: str = ""
    database: str = "default"


class ClickHouseHTTPSDevConfig(BaseModel):
    host: str = "xedvrr4c3r.us-central1.gcp.clickhouse.cloud"
    port: int = 8443
    user: str = "development_user"
    password: str = ""
    database: str = "development"
    superuser: bool = True


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
    provider: str = Field(..., description="The LLM provider (e.g., 'google', 'openai').")
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
    clickhouse_https_dev: ClickHouseHTTPSDevConfig = ClickHouseHTTPSDevConfig()
    clickhouse_logging: ClickHouseLoggingConfig = ClickHouseLoggingConfig()
    langfuse: LangfuseConfig = LangfuseConfig()
    ws_config: WebSocketConfig = Field(default_factory=WebSocketConfig)

    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = None
    jwt_secret_key: str = None
    api_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/netra"
    redis_url: str = None  # Added for staging/production Redis URL
    clickhouse_url: str = None  # Added for staging/production ClickHouse URL
    log_level: str = "DEBUG"
    log_secrets: bool = False
    frontend_url: str = "http://localhost:3010"
    redis: "RedisConfig" = Field(default_factory=lambda: RedisConfig())
    
    # LLM Cache Settings
    llm_cache_enabled: bool = True
    llm_cache_ttl: int = 3600  # 1 hour default
    
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

    llm_configs: Dict[str, LLMConfig] = {
        "default": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "analysis": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
            generation_config={"temperature": 0.5},
        ),
        "triage": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "data": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "optimizations_core": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "actions_to_meet_goals": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
        "reporting": LLMConfig(
            provider="google",
            model_name="gemini-2.5-pro",
        ),
    }

class DevelopmentConfig(AppConfig):
    """Development-specific settings can override defaults."""
    debug: bool = True
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/netra"
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
        # Check service modes from environment (set by dev launcher)
        redis_mode = os.environ.get("REDIS_MODE", "shared").lower()
        clickhouse_mode = os.environ.get("CLICKHOUSE_MODE", "shared").lower()
        llm_mode = os.environ.get("LLM_MODE", "shared").lower()
        
        # Services are only disabled if explicitly set to 'disabled' mode
        data["dev_mode_redis_enabled"] = redis_mode != "disabled"
        data["dev_mode_clickhouse_enabled"] = clickhouse_mode != "disabled"
        data["dev_mode_llm_enabled"] = llm_mode != "disabled"
        
        # Log service configuration for transparency
        import logging
        logger = logging.getLogger(__name__)
        if redis_mode == "mock":
            logger.info("Redis running in MOCK mode")
        if clickhouse_mode == "mock":
            logger.info("ClickHouse running in MOCK mode")
        if llm_mode == "mock":
            logger.info("LLM running in MOCK mode")
        
        super().__init__(**data)

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