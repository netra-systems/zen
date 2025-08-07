import os
from google.cloud import secretmanager
from typing import List, Dict
from app.schemas import AppConfig, ProductionConfig, TestingConfig, DevelopmentConfig, SecretReference

SECRET_CONFIG: List[SecretReference] = [
    SecretReference(name="gemini-api-key", target_model="llm_configs.default", target_field="api_key"),
    SecretReference(name="google-client-id", target_model="google_cloud", target_field="client_id"),
    SecretReference(name="google-client-secret", target_model="google_cloud", target_field="client_secret"),
    SecretReference(name="langfuse-secret-key", target_model="langfuse", target_field="secret_key"),
    SecretReference(name="langfuse-public-key", target_model="langfuse", target_field="public_key"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_native", target_field="password"),
    SecretReference(name="clickhouse-default-password", target_model="clickhouse_https", target_field="password"),
    SecretReference(name="clickhouse-development-password", target_model="clickhouse_https_dev", target_field="password"),
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

def get_settings() -> AppConfig:
    """Returns the appropriate configuration class based on the environment."""
    environment = os.environ.get("environment", "development").lower()
    if os.environ.get("TESTING"):
        environment = "testing"
    print(f"|| Loading configuration for: {environment} ||")
    config_map = {
        "production": ProductionConfig,
        "testing": TestingConfig,
        "development": DevelopmentConfig
    }
    config = config_map.get(environment, DevelopmentConfig)()
    config.load_secrets()
    return config

settings = get_settings()

if settings.log_secrets:
    print(settings.model_dump_json(indent=2))
