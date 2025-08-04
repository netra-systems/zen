import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
from google.cloud import secretmanager
from typing import List, Dict, Optional

class SecretReference(BaseModel):
    name: str
    target_field: str
    target_model: Optional[str] = None
    project_id: str = "304612253870"
    version: str = "latest"

SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_model="google_model", target_field="gemini_api_key"),
    SecretReference(name="google-client-id", target_model="google_cloud", target_field="google_client_id"),
    SecretReference(name="google-client-secret", target_model="google_cloud", target_field="google_client_secret"),
    SecretReference(name="langfuse-secret-key", target_model="langfuse", target_field="secret_key"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_native", target_field="password"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_https", target_field="password"),
    #SecretReference(name="database-url", target_field="database_url"),
    SecretReference(name="jwt-secret-key", target_field="jwt_secret_key"),
    SecretReference(name="fernet-key", target_field="fernet_key")
]

def get_secret_client() -> secretmanager.SecretManagerServiceClient:
    """Initializes and returns a Secret Manager service client."""
    try:
        return secretmanager.SecretManagerServiceClient()
    except Exception as e:
        print(f"Error initializing Secret Manager client: {e}")
        return None

def fetch_secrets(client: secretmanager.SecretManagerServiceClient, secret_references: List[SecretReference]) -> Dict[str, str]:
    """Fetches multiple secrets from Google Cloud Secret Manager."""
    secrets = {}
    if not client:
        return secrets

    for ref in secret_references:
        try:
            name = f"projects/{ref.project_id}/secrets/{ref.name}/versions/{ref.version}"
            response = client.access_secret_version(name=name)
            secrets[ref.name] = response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Error fetching secret {ref.name}: {e}")
            secrets[ref.name] = None
    return secrets

class GoogleCloudConfig(BaseModel):
    project_id: str = os.environ.get("GOOGLE_PROJECT_ID")
    google_client_id: str = None
    google_client_secret: str = None

class GoogleModelConfig(GoogleCloudConfig):
    gemini_api_key: str = None
    corpus_generation_model: str = "gemini-2.5-flash-lite"

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

class LangfuseConfig(BaseModel):
    secret_key: str = ""
    public_key: str = ""
    host: str = "https://cloud.langfuse.com/"

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
    fernet_key: str = None
    jwt_secret_key: str = None
    api_base_url: str = "http://localhost:8000"
    database_url: str = None
    log_level: str = "DEBUG"

    def load_secrets(self):
        if self.google_cloud.project_id and self.app_env != "testing":
            print("Loading secrets from Google Cloud Secret Manager...")
            client = get_secret_client()
            if not client:
                return

            fetched_secrets = fetch_secrets(client, SECRET_CONFIG)

            for secret_ref in SECRET_CONFIG:
                fetched_value = fetched_secrets.get(secret_ref.name)
                if fetched_value:
                    target = self
                    if secret_ref.target_model:
                        target = getattr(self, secret_ref.target_model, None)
                    
                    if target:
                        setattr(target, secret_ref.target_field, fetched_value)
                else:
                    print(f"Secret '{secret_ref.name}' not found or failed to fetch.")
            
            print("Secrets loaded.")

class DevelopmentConfig(AppConfig):
    """Development-specific settings can override defaults."""
    database_url: str = "postgresql+asyncpg://postgres:123@localhost/netra"

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