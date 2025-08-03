import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

class ClickHouseNativeConfig(BaseModel):
    host: str = "localhost"
    port: int = 9440
    user: str = "default"
    password: str = ""
    database: str = "default"

class ClickHouseHTTPSConfig(BaseModel):
    host: str = "localhost"
    port: int = 8443
    user: str = "default"
    password: str = ""
    database: str = "default"

class AppConfig(BaseSettings):
    """Base configuration class."""
    # Top-level settings
    
    # This single config dictionary controls loading for the entire AppConfig.
    model_config = SettingsConfigDict(
        env_file="app/.env",
        case_sensitive=False,
        env_nested_delimiter='__'    
    )
    app_env: str = "development"
    gemini_api_key: str
    google_client_id: str
    google_client_secret: str

    clickhouse_native: ClickHouseNativeConfig = ClickHouseNativeConfig()
    clickhouse_https: ClickHouseHTTPSConfig = ClickHouseHTTPSConfig()

    # Settings for different environments can have defaults here
    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="
    jwt_secret_key: str = "dev_jwt_secretkeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeey"
    api_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"
    log_level: str = "DEBUG"

class DevelopmentConfig(AppConfig):
    """Development-specific settings can override defaults."""
    pass

class ProductionConfig(AppConfig):
    """Production-specific settings."""
    log_level: str = "INFO"


class TestingConfig(AppConfig):
    """Testing-specific settings."""
    app_env: str = "testing"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra_test"

def get_settings() -> AppConfig:
    """Returns the appropriate configuration class based on the APP_ENV."""
    app_env = os.environ.get("APP_ENV", "development").lower()
    print(f"|| Loading configuration for: {app_env} ||")
    if app_env == "production":
        return ProductionConfig()
    elif app_env == "testing":
        return TestingConfig()
    return DevelopmentConfig()

settings = get_settings()
# The following line is for debugging and will print the loaded settings.
# In a real application, you would just export 'settings'.
print(settings.model_dump_json(indent=2))
