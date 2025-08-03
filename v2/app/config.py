import os
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

# Correct Pattern: Nested configuration models are plain BaseModels.
# They define the data shape but do not load settings themselves.
class ClickHouseNativeConfig(BaseModel):
    host: str
    port: int = 9440
    user: str = "default"
    password: str = ""
    database: str = "default"

class ClickHouseHTTPSConfig(BaseModel):
    host: str
    port: int = 8443
    user: str = "default"
    password: str = ""
    database: str = "default"

# Correct Pattern: Only the top-level class inherits from BaseSettings.
# It is the single source of truth for loading from the .env file.
class AppConfig(BaseSettings):
    """Base configuration class."""
    # Top-level settings
    app_env: str = "development"
    gemini_api_key: str
    google_client_id: str
    google_client_secret: str

    # Nested models. Pydantic automatically maps env vars with prefixes
    # like `clickhouse_native_host` to `clickhouse_native.host`.
    clickhouse_native: ClickHouseNativeConfig
    clickhouse_https: ClickHouseHTTPSConfig

    # Settings for different environments can have defaults here
    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = "default_fernet_key"
    jwt_secret_key: str = "default_jwt_secret_key"
    api_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"

    # This single config dictionary controls loading for the entire AppConfig.
    model_config = SettingsConfigDict(
        env_file="app/.env",
        case_sensitive=False,
        env_prefix=""
    )

class DevelopmentConfig(AppConfig):
    """Development-specific settings can override defaults."""
    secret_key: str = "dev_secret_key"
    fernet_key: str = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="
    jwt_secret_key: str = "dev_jwt_secret_key"

class ProductionConfig(AppConfig):
    """Production-specific settings."""
    log_level: str = "INFO"
    # In production, you would likely override keys to be loaded from a secure source

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
