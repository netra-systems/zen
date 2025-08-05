import os
from pydantic import BaseModel
from google.cloud import secretmanager
from typing import List, Dict, Optional
from app.llm.schemas import LLMConfig

class SecretReference(BaseModel):
    name: str
    target_field: str
    target_model: Optional[str] = None
    project_id: str = "304612253870"
    version: str = "latest"

# https://console.cloud.google.com/security/secret-manager?inv=1&invt=Ab4muw&project=cryptic-net-466001-n0
SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_model="google_model", target_field="gemini_api_key"),
    SecretReference(name="google-client-id", target_model="google_cloud", target_field="client_id"),
    SecretReference(name="google-client-secret", target_model="google_cloud", target_field="client_secret"),
    SecretReference(name="langfuse-secret-key", target_model="langfuse", target_field="secret_key"),
    SecretReference(name="langfuse-public-key", target_model="langfuse", target_field="public_key"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_native", target_field="password"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_https", target_field="password"),
    SecretReference(name="clickhouse-development-password", target_model="clickhouse_https_dev", target_field="password"),
    #SecretReference(name="database-url", target_field="database_url"),
    SecretReference(name="clickhouse-development-password", target_model="clickhouse_https_dev", target_field="password"),
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

def fetch_secrets(client: secretmanager.SecretManagerServiceClient, secret_references: List[SecretReference], log_secrets: bool = False) -> Dict[str, str]:
    """Fetches multiple secrets from Google Cloud Secret Manager."""
    secrets = {}
    if not client:
        return secrets

    for ref in secret_references:
        try:
            name = f"projects/{ref.project_id}/secrets/{ref.name}/versions/{ref.version}"
            response = client.access_secret_version(name=name)
            secrets[ref.name] = response.payload.data.decode("UTF-8")
            if log_secrets:
                print(f"Fetched secret: {ref.name}")
        except Exception as e:
            if log_secrets:
                print(f"Error fetching secret {ref.name}: {e}")
            secrets[ref.name] = None
    return secrets

class GoogleCloudConfig(BaseModel):
    project_id: str = "cryptic-net-466001-n0"
    client_id: str = None
    client_secret: str = None

class GoogleModelConfig(GoogleCloudConfig):
    gemini_api_key: str = None
    corpus_generation_model: str = "gemini-2.5-flash-lite"
    analysis_model: str = "gemini-2.5-flash-lite"
    analysis_model_fallback: str = "gemini-2.5-flash-lite"

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


class LangfuseConfig(BaseModel):
    secret_key: str = ""
    public_key: str = ""
    host: str = "https://cloud.langfuse.com/"

class AppConfig(BaseModel):
    """Base configuration class."""

    app_env: str = "development"
    google_cloud: GoogleCloudConfig = GoogleCloudConfig()
    google_model: GoogleModelConfig = GoogleModelConfig()
    clickhouse_native: ClickHouseNativeConfig = ClickHouseNativeConfig()
    clickhouse_https: ClickHouseHTTPSConfig = ClickHouseHTTPSConfig()
    clickhouse_https_dev: ClickHouseHTTPSDevConfig = ClickHouseHTTPSDevConfig()
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
    run_startup_simulation: bool = False

    llm_configs: Dict[str, LLMConfig] = {
        "default": LLMConfig(
            provider="google",
            model_name="gemini-1.5-flash-latest",
        ),
        "analysis": LLMConfig(
            provider="google",
            model_name="gemini-2.5-flash-lite",
            temperature=0.5,
        ),
        "gpt-4": LLMConfig(
            provider="openai",
            model_name="gpt-4",
            temperature=0.8,
        ),
    }

    def load_secrets(self):
        if self.google_cloud.project_id and self.app_env != "testing":
            if self.log_secrets:
                print("Loading secrets from Google Cloud Secret Manager...")
            client = get_secret_client()
            if not client:
                return

            fetched_secrets = fetch_secrets(client, SECRET_CONFIG, self.log_secrets)

            for secret_ref in SECRET_CONFIG:
                fetched_value = fetched_secrets.get(secret_ref.name)
                if fetched_value:
                    target = self
                    if secret_ref.target_model:
                        target = getattr(self, secret_ref.target_model, None)
                    
                    if target:
                        setattr(target, secret_ref.target_field, fetched_value)
                elif self.log_secrets:
                    print(f"Secret '{secret_ref.name}' not found or failed to fetch.")
            
            if self.log_secrets:
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
    if os.environ.get("TESTING"):
        app_env = "testing"
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
if settings.log_secrets:
    print(settings.model_dump_json(indent=2))