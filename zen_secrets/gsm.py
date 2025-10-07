"""
Google Secret Manager Integration

This module provides secure integration with Google Secret Manager (GSM) using
Workload Identity Federation for authentication. It implements the complete
GSM client with proper error handling, retry logic, and security features.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

try:
    from google.cloud import secretmanager
    from google.cloud.secretmanager import SecretManagerServiceAsyncClient
    from google.auth import default
    from google.auth.exceptions import DefaultCredentialsError
    from google.api_core import retry, exceptions as gcp_exceptions
    GSM_AVAILABLE = True
except ImportError:
    GSM_AVAILABLE = False
    # Create mock classes for type hints
    class SecretManagerServiceAsyncClient:
        pass

from .core import SecretValue, SecretMetadata, SecretType, SecretClassification, SecretEnvironment, SecretConfig
from .exceptions import (
    SecretManagerError,
    SecretNotFoundError,
    SecretAccessDeniedError,
    SecretValidationError
)

logger = logging.getLogger(__name__)


class GoogleSecretManagerClient:
    """
    Google Secret Manager client with Workload Identity Federation support.

    This client provides secure access to Google Secret Manager with:
    - Workload Identity Federation authentication
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Audit logging and monitoring
    - Secret versioning and metadata management
    """

    def __init__(self, config: SecretConfig):
        """Initialize the GSM client."""
        if not GSM_AVAILABLE:
            raise SecretManagerError(
                "Google Cloud Secret Manager dependencies not available. "
                "Install with: pip install google-cloud-secret-manager"
            )

        self.config = config
        self.project_id = config.gcp_project_id
        self.environment = config.environment
        self._client: Optional[SecretManagerServiceAsyncClient] = None
        self._credentials = None

        # Retry configuration
        self._retry_config = retry.Retry(
            initial=1.0,
            maximum=60.0,
            multiplier=2.0,
            deadline=300.0,  # 5 minutes total
            predicate=retry.if_exception_type(
                gcp_exceptions.InternalServerError,
                gcp_exceptions.ServiceUnavailable,
                gcp_exceptions.DeadlineExceeded,
                gcp_exceptions.TooManyRequests
            )
        )

        logger.info(f"GSM Client initialized for project: {self.project_id}")

    async def initialize(self) -> None:
        """Initialize the GSM client with authentication."""
        try:
            # Initialize credentials with Workload Identity
            if self.config.workload_identity_enabled:
                # In Kubernetes with Workload Identity, credentials are automatically available
                self._credentials, _ = default()
                logger.info("Using Workload Identity Federation for GSM authentication")
            else:
                # Fall back to default credentials (service account key, gcloud auth, etc.)
                self._credentials, _ = default()
                logger.info("Using default credentials for GSM authentication")

            # Initialize the async client
            self._client = SecretManagerServiceAsyncClient(credentials=self._credentials)

            # Test connectivity
            await self._test_connectivity()

            logger.info("GSM client initialized successfully")

        except DefaultCredentialsError as e:
            raise SecretManagerError(
                f"Failed to initialize GSM client - credentials not available: {str(e)}"
            )
        except Exception as e:
            raise SecretManagerError(f"Failed to initialize GSM client: {str(e)}")

    async def _test_connectivity(self) -> None:
        """Test connectivity to Google Secret Manager."""
        try:
            # Try to list secrets (with limit to minimize impact)
            parent = f"projects/{self.project_id}"
            request = secretmanager.ListSecretsRequest(
                parent=parent,
                page_size=1
            )
            await self._client.list_secrets(request=request, retry=self._retry_config)
            logger.debug("GSM connectivity test successful")
        except gcp_exceptions.PermissionDenied:
            raise SecretAccessDeniedError(
                "test-connectivity",
                "secretmanager.secrets.list",
                self._get_service_account_email()
            )
        except Exception as e:
            raise SecretManagerError(f"GSM connectivity test failed: {str(e)}")

    def _get_service_account_email(self) -> Optional[str]:
        """Get the service account email from credentials."""
        if hasattr(self._credentials, 'service_account_email'):
            return self._credentials.service_account_email
        return None

    async def get_secret(self, name: str, version: str = "latest") -> SecretValue:
        """
        Retrieve a secret from Google Secret Manager.

        Args:
            name: Secret name
            version: Secret version (default: "latest")

        Returns:
            SecretValue object containing the secret and metadata
        """
        secret_name = self._format_secret_name(name)
        version_name = f"{secret_name}/versions/{version}"

        try:
            # Get secret value
            request = secretmanager.AccessSecretVersionRequest(name=version_name)
            response = await self._client.access_secret_version(
                request=request,
                retry=self._retry_config
            )

            secret_value = response.payload.data.decode('utf-8')

            # Get secret metadata
            metadata = await self._get_secret_metadata(secret_name)

            return SecretValue(
                value=secret_value,
                metadata=metadata,
                version=response.name.split("/")[-1],
                checksum=""  # Will be calculated in __post_init__
            )

        except gcp_exceptions.NotFound:
            raise SecretNotFoundError(name, self.environment.value)
        except gcp_exceptions.PermissionDenied:
            raise SecretAccessDeniedError(
                name,
                "secretmanager.versions.access",
                self._get_service_account_email()
            )
        except Exception as e:
            raise SecretManagerError(f"Failed to get secret '{name}': {str(e)}")

    async def set_secret(self, secret_value: SecretValue) -> str:
        """
        Store a secret in Google Secret Manager.

        Args:
            secret_value: SecretValue object to store

        Returns:
            Version string of the created secret
        """
        secret_name = self._format_secret_name(secret_value.metadata.name)

        try:
            # Check if secret exists, create if not
            try:
                await self._client.get_secret(
                    request=secretmanager.GetSecretRequest(name=secret_name),
                    retry=self._retry_config
                )
            except gcp_exceptions.NotFound:
                # Create the secret
                await self._create_secret(secret_value.metadata)

            # Add secret version
            request = secretmanager.AddSecretVersionRequest(
                parent=secret_name,
                payload=secretmanager.SecretPayload(
                    data=secret_value.value.encode('utf-8')
                )
            )

            response = await self._client.add_secret_version(
                request=request,
                retry=self._retry_config
            )

            version = response.name.split("/")[-1]
            logger.info(f"Secret '{secret_value.metadata.name}' stored with version {version}")

            return version

        except gcp_exceptions.PermissionDenied:
            raise SecretAccessDeniedError(
                secret_value.metadata.name,
                "secretmanager.secrets.create or secretmanager.versions.add",
                self._get_service_account_email()
            )
        except Exception as e:
            raise SecretManagerError(
                f"Failed to store secret '{secret_value.metadata.name}': {str(e)}"
            )

    async def _create_secret(self, metadata: SecretMetadata) -> None:
        """Create a new secret in GSM."""
        parent = f"projects/{self.project_id}"
        secret_id = self._format_secret_id(metadata.name)

        # Prepare labels (GSM labels must be lowercase)
        labels = {
            "environment": metadata.environment.value,
            "secret_type": metadata.secret_type.value.replace("_", "-"),
            "classification": metadata.classification.value,
            "managed_by": "zen-secrets"
        }

        # Add custom tags as labels
        for key, value in metadata.tags.items():
            # GSM label keys must be lowercase and contain only letters, numbers, and hyphens
            label_key = key.lower().replace("_", "-").replace(".", "-")
            labels[label_key] = value.lower().replace("_", "-").replace(".", "-")

        secret = secretmanager.Secret(
            labels=labels,
            replication=secretmanager.Replication(
                automatic=secretmanager.Replication.Automatic()
            )
        )

        request = secretmanager.CreateSecretRequest(
            parent=parent,
            secret_id=secret_id,
            secret=secret
        )

        await self._client.create_secret(request=request, retry=self._retry_config)
        logger.info(f"Secret '{metadata.name}' created in GSM")

    async def delete_secret(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a secret or specific version.

        Args:
            name: Secret name
            version: Specific version to delete (None for entire secret)

        Returns:
            True if deletion was successful
        """
        secret_name = self._format_secret_name(name)

        try:
            if version:
                # Delete specific version
                version_name = f"{secret_name}/versions/{version}"
                request = secretmanager.DestroySecretVersionRequest(name=version_name)
                await self._client.destroy_secret_version(
                    request=request,
                    retry=self._retry_config
                )
                logger.info(f"Secret version '{name}:{version}' deleted")
            else:
                # Delete entire secret
                request = secretmanager.DeleteSecretRequest(name=secret_name)
                await self._client.delete_secret(request=request, retry=self._retry_config)
                logger.info(f"Secret '{name}' deleted completely")

            return True

        except gcp_exceptions.NotFound:
            logger.warning(f"Secret '{name}' not found for deletion")
            return False
        except gcp_exceptions.PermissionDenied:
            raise SecretAccessDeniedError(
                name,
                "secretmanager.secrets.delete or secretmanager.versions.destroy",
                self._get_service_account_email()
            )
        except Exception as e:
            raise SecretManagerError(f"Failed to delete secret '{name}': {str(e)}")

    async def list_secrets(self, filter_tags: Optional[Dict[str, str]] = None) -> List[SecretMetadata]:
        """
        List all secrets with optional tag filtering.

        Args:
            filter_tags: Optional tags to filter by

        Returns:
            List of SecretMetadata objects
        """
        try:
            parent = f"projects/{self.project_id}"
            request = secretmanager.ListSecretsRequest(parent=parent)

            secrets = []
            async for secret in await self._client.list_secrets(
                request=request,
                retry=self._retry_config
            ):
                # Convert GSM secret to metadata
                metadata = await self._gsm_secret_to_metadata(secret)

                # Apply tag filtering
                if filter_tags:
                    if not all(
                        metadata.tags.get(key) == value
                        for key, value in filter_tags.items()
                    ):
                        continue

                secrets.append(metadata)

            return secrets

        except gcp_exceptions.PermissionDenied:
            raise SecretAccessDeniedError(
                "list-secrets",
                "secretmanager.secrets.list",
                self._get_service_account_email()
            )
        except Exception as e:
            raise SecretManagerError(f"Failed to list secrets: {str(e)}")

    async def _get_secret_metadata(self, secret_name: str) -> SecretMetadata:
        """Get metadata for a secret."""
        try:
            request = secretmanager.GetSecretRequest(name=secret_name)
            secret = await self._client.get_secret(request=request, retry=self._retry_config)
            return await self._gsm_secret_to_metadata(secret)
        except Exception as e:
            raise SecretManagerError(f"Failed to get metadata for {secret_name}: {str(e)}")

    async def _gsm_secret_to_metadata(self, gsm_secret) -> SecretMetadata:
        """Convert GSM secret object to SecretMetadata."""
        labels = gsm_secret.labels or {}

        # Extract metadata from labels
        secret_type = SecretType(labels.get("secret_type", "custom").replace("-", "_"))
        classification = SecretClassification(labels.get("classification", "medium"))
        environment = SecretEnvironment(labels.get("environment", "development"))

        # Extract custom tags (remove system labels)
        system_labels = {"environment", "secret_type", "classification", "managed_by"}
        tags = {
            key: value for key, value in labels.items()
            if key not in system_labels
        }

        # Extract secret name from full resource name
        secret_id = gsm_secret.name.split("/")[-1]
        secret_name = self._parse_secret_name(secret_id)

        return SecretMetadata(
            name=secret_name,
            secret_type=secret_type,
            classification=classification,
            environment=environment,
            created_at=gsm_secret.create_time,
            tags=tags,
            description=f"GSM secret: {secret_id}"
        )

    def _format_secret_name(self, name: str) -> str:
        """Format secret name for GSM."""
        secret_id = self._format_secret_id(name)
        return f"projects/{self.project_id}/secrets/{secret_id}"

    def _format_secret_id(self, name: str) -> str:
        """
        Format secret name to be GSM-compliant.
        GSM secret names must be 1-255 characters and match [a-zA-Z0-9-_]+
        """
        # Replace invalid characters with hyphens
        formatted = name.replace(".", "-").replace("/", "-").replace(":", "-")

        # Add environment prefix for better organization
        env_prefix = f"{self.environment.value}-"

        # Ensure it doesn't exceed 255 characters
        max_length = 255 - len(env_prefix)
        if len(formatted) > max_length:
            formatted = formatted[:max_length]

        return f"{env_prefix}{formatted}"

    def _parse_secret_name(self, secret_id: str) -> str:
        """Parse the original secret name from GSM secret ID."""
        # Remove environment prefix
        env_prefix = f"{self.environment.value}-"
        if secret_id.startswith(env_prefix):
            return secret_id[len(env_prefix):]
        return secret_id

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on GSM connection."""
        try:
            start_time = datetime.utcnow()
            await self._test_connectivity()
            end_time = datetime.utcnow()

            return {
                "status": "healthy",
                "response_time_ms": (end_time - start_time).total_seconds() * 1000,
                "project_id": self.project_id,
                "service_account": self._get_service_account_email(),
                "timestamp": end_time.isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "project_id": self.project_id,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            # AsyncClient doesn't have an explicit close method
            # The gRPC channel will be cleaned up automatically
            self._client = None
        logger.info("GSM client closed")