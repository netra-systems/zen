# /v2/services/security_service.py
import os
import json
import logging
from typing import Dict, Optional
from google.cloud import secretmanager
from ..config import settings

# --- Logger Setup ---
logger = logging.getLogger(__name__)

class SecurityService:
    """
    Handles all security-related operations, primarily secrets management.
    """

    def __init__(self, gcp_project_id: str):
        self.gcp_project_id = gcp_project_id
        if self.gcp_project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
                logger.info("Google Secret Manager client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Google Secret Manager client: {e}", exc_info=True)
                self.client = None
        else:
            logger.warning("GCP_PROJECT_ID not set. Secrets will NOT be managed by Google Secret Manager.")
            self.client = None

    def get_secret(self, secret_id: str, version_id: str = "latest") -> Optional[Dict]:
        """
        Retrieves a secret from Google Secret Manager.
        The secret payload is expected to be a JSON string.
        """
        if not self.client:
            logger.error("Cannot get secret, Secret Manager client is not available.")
            return None

        name = f"projects/{self.gcp_project_id}/secrets/{secret_id}/versions/{version_id}"
        logger.info(f"Attempting to retrieve secret: {name}")

        try:
            response = self.client.access_secret_version(request={"name": name})
            payload = response.payload.data.decode("UTF-8")
            return json.loads(payload)
        except Exception as e:
            logger.error(f"Failed to access secret '{secret_id}': {e}", exc_info=True)
            return None

    def create_or_update_secret(self, secret_id: str, payload: Dict) -> bool:
        """
        Creates a new secret or adds a new version to an existing secret in Google Secret Manager.
        """
        if not self.client:
            logger.error("Cannot create/update secret, Secret Manager client is not available.")
            return False

        parent = f"projects/{self.gcp_project_id}"
        secret_name = f"{parent}/secrets/{secret_id}"
        
        try:
            # Check if secret exists, if not, create it
            try:
                self.client.get_secret(request={"name": secret_name})
            except Exception: # google.api_core.exceptions.NotFound
                logger.info(f"Secret '{secret_id}' not found. Creating it now.")
                self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )

            # Add the new secret version
            payload_bytes = json.dumps(payload).encode("UTF-8")
            self.client.add_secret_version(
                request={"parent": secret_name, "payload": {"data": payload_bytes}}
            )
            logger.info(f"Successfully added a new version to secret '{secret_id}'.")
            return True

        except Exception as e:
            logger.error(f"Failed to create or update secret '{secret_id}': {e}", exc_info=True)
            return False

# --- Service Instance ---
# A single instance of the service can be created and used throughout the application
security_service = SecurityService(gcp_project_id=settings.GCP_PROJECT_ID)
