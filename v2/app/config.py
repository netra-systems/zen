import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from google.cloud import secretmanager
from typing import List, Dict

def get_secrets(secret_ids: List[str], project_id: str, version_id: str = "latest") -> Dict[str, str]:
    """Fetches multiple secrets from Google Cloud Secret Manager."""
    secrets = {}
    try:
        client = secretmanager.SecretManagerServiceClient()
        for secret_id in secret_ids:
            name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
            try:
                response = client.access_secret_version(name=name)
                secrets[secret_id] = response.payload.data.decode("UTF-8")
            except Exception as e:
                print(f"Error fetching secret {secret_id}: {e}")
                secrets[secret_id] = None
    except Exception as e:
        print(f"Error initializing Secret Manager client: {e}")
    return secrets

class GoogleCloudConfig(BaseModel):
    project_id: str = os.environ.get("GOOGLE_PROJECT_ID")

class GoogleModelConfig(BaseModel):
    gemini_api_key: str = None
    google_client_id: str = None
    google_client_secret: str = None
    corpus_generation_model: str = "gemini-2.5-flash-lite"

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

class LangfuseConfig(BaseModel):
    secret_key: str = ""
    public_key: str = ""
    host: str = ""

class AppConfig(BaseSettings):
    """Base configuration class."""
    model_config = SettingsConfigDict(
        env_file="app/.env",
        case_sensitive=False,
        env_nested_delimiter='__'    
    )
    app_env: str = "development"

    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    google_model: GoogleModelConfig = GoogleModelConfig()
    clickhouse_native: ClickHouseNativeConfig = ClickHouseNativeConfig()
    clickhouse_https: ClickHouseHTTPSConfig = ClickHouseHTTPSConfig()
    langfuse: LangfuseConfig = LangfuseConfig()

    secret_key: str = "default_secret_key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    fernet_key: str = "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw="
    jwt_secret_key: str = "dev_jwt_secretkeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeey"
    api_base_url: str = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"
    log_level: str = "DEBUG"

    def load_secrets(self):
        if self.google_cloud.project_id and self.app_env != "testing":
            print("Loading secrets from Google Cloud Secret Manager...")
            secrets_to_fetch = ["gemini_api_key", "google_client_id", "google_client_secret"]
            fetched_secrets = get_secrets(secrets_to_fetch, self.google_cloud.project_id)
            
            self.google_model.gemini_api_key = fetched_secrets.get("gemini_api_key")
            self.google_model.google_client_id = fetched_secrets.get("google_client_id")
            self.google_model.google_client_secret = fetched_secrets.get("google_client_secret")
            
            print("Secrets loaded.")

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
    config_map = {
        "production": ProductionConfig,
        "testing": TestingConfig,
        "development": DevelopmentConfig
    }
    config = config_map.get(app_env, DevelopmentConfig)()
    config.load_secrets()
    return config

settings = get_settings()
# The following line is for debugging and will print the loaded settings.
# In a real application, you would just export 'settings'.
print(settings.model_dump_json(indent=2))