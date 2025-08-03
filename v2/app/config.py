import os
from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    """Base configuration class."""
    app_env: str = "development"
    gemini_api_key: str
    clickhouse_host: str
    clickhouse_port: int
    clickhouse_user: str
    clickhouse_password: str
    clickhouse_db: str
    secret_key: str
    google_client_id: str
    google_client_secret: str   
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str
    jwt_secret_key: str
    api_base_url: str = "http://localhost:8000"
    
    model_config = SettingsConfigDict(env_file='app/.env')

class DevelopmentConfig(AppConfig):
    """Development configuration.
    Extends AppConfig, so just add other ones:
    """
    log_level: str = "DEBUG"
    secret_key: str = "secret_key"
    fernet_key: str = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="
    jwt_secret_key: str = "jwt_secret_key"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"

class ProductionConfig(AppConfig):
    """Production configuration."""
    log_level: str = "INFO"

class TestingConfig(AppConfig):
    """Testing configuration."""
    log_level: str = "DEBUG"
    app_env: str = "testing"

def get_settings() -> AppConfig:
    """Returns the appropriate configuration class based on the APP_ENV environment variable."""
    app_env = os.environ.get("APP_ENV", "development")
    print(f"|| {app_env} || Env loading configuration.")
    if app_env == "production":
        return ProductionConfig()
    elif app_env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()

settings = get_settings()
print(settings.model_dump())
