from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SecretReference(BaseModel):
    name: str
    target_model: Optional[str] = None
    target_field: str
    project_id: str = "netra-414903"
    version: str = "latest"

class LLMConfig(BaseModel):
    api_key: Optional[str] = None
    model_name: str = "gemini-1.5-flash"
    max_tokens: int = 2048
    temperature: float = 0.7

class GoogleCloudConfig(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

class LangfuseConfig(BaseModel):
    secret_key: Optional[str] = None
    public_key: Optional[str] = None

class ClickHouseConfig(BaseModel):
    host: str
    port: int
    user: str
    password: Optional[str] = None
    database: str

class PostgresConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    database: str

class OAuthConfig(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

class AppConfig(BaseModel):
    log_secrets: bool = False
    llm_configs: Dict[str, LLMConfig]
    google_cloud: GoogleCloudConfig
    langfuse: LangfuseConfig
    clickhouse_native: ClickHouseConfig
    clickhouse_https: ClickHouseConfig
    clickhouse_https_dev: ClickHouseConfig
    postgres: PostgresConfig
    jwt_secret_key: Optional[str] = None
    fernet_key: Optional[str] = None
    oauth_config: OAuthConfig

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres.user}:{self.postgres.password}@{self.postgres.host}:{self.postgres.port}/{self.postgres.database}"

class ProductionConfig(AppConfig):
    pass

class DevelopmentConfig(AppConfig):
    llm_configs: Dict[str, LLMConfig] = Field(default_factory=lambda: {"default": LLMConfig()})
    google_cloud: GoogleCloudConfig = Field(default_factory=GoogleCloudConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    clickhouse_native: ClickHouseConfig = Field(default_factory=lambda: ClickHouseConfig(host="localhost", port=9000, user="default", password="", database="netra"))
    clickhouse_https: ClickHouseConfig = Field(default_factory=lambda: ClickHouseConfig(host="localhost", port=8443, user="default", password="", database="netra"))
    clickhouse_https_dev: ClickHouseConfig = Field(default_factory=lambda: ClickHouseConfig(host="localhost", port=8443, user="default", password="", database="netra_dev"))
    postgres: PostgresConfig = Field(default_factory=lambda: PostgresConfig(host="localhost", port=5432, user="postgres", password="123", database="netra"))
    oauth_config: OAuthConfig = Field(default_factory=OAuthConfig)


class TestingConfig(AppConfig):
    llm_configs: Dict[str, LLMConfig] = Field(default_factory=lambda: {"default": LLMConfig()})
    google_cloud: GoogleCloudConfig = Field(default_factory=GoogleCloudConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    clickhouse_native: ClickHouseConfig = Field(default_factory=lambda: ClickHouseConfig(host="localhost", port=9000, user="default", password="", database="netra_test"))
    clickhouse_https: ClickHouseConfig = Field(default_factory=lambda: ClickHouseConfig(host="localhost", port=8443, user="default", password="", database="netra_test"))
    clickhouse_https_dev: ClickHouseConfig = Field(default_factory=lambda: ClickHouseConfig(host="localhost", port=8443, user="default", password="", database="netra_dev_test"))
    postgres: PostgresConfig = Field(default_factory=lambda: PostgresConfig(host="localhost", port=5432, user="postgres", password="123", database="netra_test"))
    oauth_config: OAuthConfig = Field(default_factory=OAuthConfig)
