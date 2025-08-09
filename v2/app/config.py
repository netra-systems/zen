import os
from google.cloud import secretmanager
from typing import List, Dict
from app import schemas
from tenacity import retry, stop_after_attempt, wait_fixed
from app.schemas import SECRET_CONFIG

class Settings:
    def __init__(self):
        self.loaded_settings = self._get_all_secrets_and_env_configs()
        if self.loaded_settings.log_secrets:
            print(self.loaded_settings.model_dump_json(indent=2))
        
    def get_settings(self) -> schemas.AppConfig:
        return self.loaded_settings
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_secret_client(self) -> secretmanager.SecretManagerServiceClient:
        """Initializes and returns a Secret Manager service client with retry logic."""
        try:
            return secretmanager.SecretManagerServiceClient()
        except Exception as e:
            print(f"Attempt to initialize Secret Manager client failed: {e}")
            raise ConnectionError(f"Failed to connect to Secret Manager: {e}")

    def _fetch_secrets(self, client: secretmanager.SecretManagerServiceClient, secret_references: List[schemas.SecretReference], log_secrets: bool = False) -> Dict[str, str]:
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

    def _load_secrets(self, config: schemas.AppConfig):
        """Fetches secrets from Secret Manager and populates the config object."""
        try:
            client = self._get_secret_client()
        except ConnectionError as e:
            print(f"Warning: Could not connect to Secret Manager. Using default settings. {e}")
            return

        if not client:
            print("Could not create Secret Manager client. Skipping secret loading.")
            return

        fetched_secrets = self._fetch_secrets(client, SECRET_CONFIG, config.log_secrets)

        for ref in SECRET_CONFIG:
            secret_value = fetched_secrets.get(ref.name)
            if secret_value is None:
                continue

            if ref.target_models:
                for target_model_str in ref.target_models:
                    target_obj = config
                    if '.' in target_model_str:
                        parts = target_model_str.split('.', 1)
                        dict_name = parts[0]
                        key_name = parts[1]
                        target_dict = getattr(config, dict_name)
                        target_obj = target_dict.get(key_name)
                    else:
                        target_obj = getattr(config, target_model_str)

                    if target_obj:
                        setattr(target_obj, ref.target_field, secret_value)
            else:
                setattr(config, ref.target_field, secret_value)

        # Check for missing LLM API keys
        for llm_name, llm_config in config.llm_configs.items():
            if not llm_config.api_key:
                print(f"Warning: API key for LLM '{llm_name}' is not set.")

    def _get_all_secrets_and_env_configs(self) -> schemas.AppConfig:
        """Returns the appropriate configuration class based on the environment."""
        environment = os.environ.get("environment", "development").lower()
        if os.environ.get("TESTING"):
            environment = "testing"
        print(f"|| Loading configuration for: {environment} ||")
        config_map = {
            "production": schemas.ProductionConfig,
            "testing": schemas.TestingConfig,
            "development": schemas.DevelopmentConfig
        }
        config = config_map.get(environment, schemas.DevelopmentConfig)()
        
        self._load_secrets(config)

        return config

settings = Settings().get_settings()
