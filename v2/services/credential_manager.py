# /services/credential_manager.py
import os
import json
import logging
from typing import Dict, Optional

# This is a mock secret store for demonstration purposes.
# In a real environment, you would replace this with calls to a proper secret management service
# like AWS Secrets Manager, Google Secret Manager, or HashiCorp Vault.
MOCK_SECRET_STORE = {
    "customer_abc_ch_creds": {
        "host": "customer.clickhouse.cloud",
        "port": 9440,
        "user": "netra_integration_sync_user",
        "database": "customer_db"
    },
    "netra_ch_creds": {
        "host": "localhost", # or your internal Netra ClickHouse instance
        "port": 9000,
        "user": "default",
        "database": "netra_analysis"
    }
}

def get_credentials(secret_name: str, password_override: Optional[str] = None) -> Dict:
    """
    Fetches database credentials from a secret store.
    
    This function simulates fetching credentials. In a production environment,
    this would involve using a library like boto3 (for AWS) or google-cloud-secret-manager.
    
    Args:
        secret_name: The identifier for the secret to retrieve.
        password_override: A password to use instead of one from the secret store.

    Returns:
        A dictionary containing connection details.
    """
    logging.info(f"Attempting to retrieve secret: {secret_name}")

    # Prioritize environment variables for credentials
    env_secret = os.getenv(secret_name)
    if env_secret:
        try:
            creds = json.loads(env_secret)
            logging.info(f"Loaded credentials for '{secret_name}' from environment variable.")
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON from environment variable: {secret_name}")
            raise ValueError(f"Invalid JSON in environment variable {secret_name}")
    elif secret_name in MOCK_SECRET_STORE:
        creds = MOCK_SECRET_STORE[secret_name]
        logging.info(f"Loaded credentials for '{secret_name}' from mock store.")
    else:
        logging.error(f"Secret '{secret_name}' not found.")
        raise ValueError(f"Secret '{secret_name}' not found in environment or mock store.")

    # Override the password if one is provided
    if password_override:
        creds['password'] = password_override
    elif 'password' not in creds and os.getenv('CLICKHOUSE_PASSWORD'):
        creds['password'] = os.getenv('CLICKHOUSE_PASSWORD')

    if 'password' not in creds:
        logging.warning(f"No password found for secret '{secret_name}'. Connection may fail.")

    return creds

