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
    target_model: Optional[str] = None
    project_id: str = "304612253870"
    version: str = "latest"


SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_model="llm_configs.default", target_field="api_key"),
    SecretReference(name="gemini-api-key", target_model="llm_configs.triage", target_field="api_key"),
    SecretReference(name="gemini-api-key", target_model="llm_configs.data", target_field="api_key"),
    SecretReference(name="gemini-api-key", target_model="llm_configs.optimizations_core", target_field="api_key"),
    SecretReference(name="gemini-api-key", target_model="llm_configs.actions_to_meet_goals", target_field="api_key"),
    SecretReference(name="gemini-api-key", target_model="llm_configs.reporting", target_field="api_key"),
    SecretReference(name="google-client-id", target_model="google_cloud", target_field="client_id"),
    SecretReference(name="google-client-secret", target_model="google_cloud", target_field="client_secret"),
    SecretReference(name="langfuse-secret-key", target_model="langfuse", target_field="secret_key"),
    SecretReference(name="langfuse-public-key", target_model="langfuse", target_field="public_key"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_native", target_field="password"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_https", target_field="password"),
    SecretReference(name="clickhouse-development-password", target_model="clickhouse_https_dev", target_field="password"),
    SecretReference(name="jwt-secret-key", target_field="jwt_secret_key"),
    SecretReference(name="fernet-key", target_field="fernet_key"),
    SecretReference(name="google-client-id", target_model="oauth_config", target_field="client_id"),
    SecretReference(name="google-client-secret", target_model="oauth_config", target_field="client_secret"),
]

class GoogleCloudConfig(BaseModel):
    project_id: str = "cryptic-net-466001-n0"
    client_id: str = None
    client_secret: str = None

class OAuthConfig(BaseModel):
    client_id: str = None
    client_secret: str = None
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

class AppConfig(BaseModel):
    """Base configuration class."""

    environment: str = "development"
    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    oauth_config: OAuthConfig = Field(default_factory=OAuthConfig)
    clickhouse_native: ClickHouseNativeConfig = ClickHouseNativeConfig()
    clickhouse_https: ClickHouseHTTPSConfig = ClickHouseHTTPSConfig()
    clickhouse_https_dev: ClickHouseHTTPSDevConfig = ClickHouseHTTPSDevConfig()
    clickhouse_logging: ClickHouseLoggingConfig = ClickHouseLoggingConfig()
    langfuse: LangfuseConfig = LangfuseConfig()

    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = None
    jwt_secret_key: str = None
    api_base_url: str = "http://localhost:8000"
    database_url: str = None
    log_level: str = "DEBUG"
    log_secrets: bool = False
    frontend_url: str = "http://localhost:3000"
    redis_url: Optional[str] = None

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
        "gpt-4": LLMConfig(
            provider="openai",
            model_name="gpt-4",
            generation_config={"temperature": 0.8},
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
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"
    redis_url: str = "redis://127.0.0.1:6379"
    dev_user_email: str = "dev@example.com"
    log_level: str = "DEBUG"

class ProductionConfig(AppConfig):
    """Production-specific settings."""
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"

class TestingConfig(AppConfig):
    """Testing-specific settings."""
    environment: str = "testing"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra_test"
    redis_url: str = "redis://127.0.0.1:6379"