import os
from google.cloud import secretmanager
from typing import List, Dict
from app.schemas import AppConfig, ProductionConfig, TestingConfig, DevelopmentConfig, SecretReference, OAuthConfig

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

def load_secrets(config: AppConfig):
    """Fetches secrets from Secret Manager and populates the config object."""
    client = get_secret_client()
    if not client:
        print("Could not create Secret Manager client. Skipping secret loading.")
        return

    fetched_secrets = fetch_secrets(client, SECRET_CONFIG, config.log_secrets)

    for ref in SECRET_CONFIG:
        secret_value = fetched_secrets.get(ref.name)
        if secret_value is None:
            continue

        target_obj = config
        if ref.target_model:
            if '.' in ref.target_model:
                parts = ref.target_model.split('.', 1)
                dict_name = parts[0]
                key_name = parts[1]
                target_dict = getattr(config, dict_name)
                target_obj = target_dict.get(key_name)
            else:
                target_obj = getattr(config, ref.target_model)

        if target_obj:
            setattr(target_obj, ref.target_field, secret_value)

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
    
    load_secrets(config)
    return config

settings = get_settings()

if settings.log_secrets:
    print(settings.model_dump_json(indent=2))
