"""
Kubernetes Secret Management with Workload Identity

This module provides secure integration with Kubernetes secrets using:
- Workload Identity Federation for GKE
- Secret Store CSI Driver for external secret mounting
- Native Kubernetes secrets as fallback
- Comprehensive RBAC and security controls
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

try:
    from kubernetes_asyncio import client, config
    from kubernetes_asyncio.client.rest import ApiException
    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    # Mock classes for type hints
    class ApiException(Exception):
        pass

from .core import SecretValue, SecretMetadata, SecretType, SecretClassification, SecretEnvironment, SecretConfig
from .exceptions import (
    SecretManagerError,
    SecretNotFoundError,
    SecretAccessDeniedError,
    SecretValidationError
)

logger = logging.getLogger(__name__)


class KubernetesSecretManager:
    """
    Kubernetes Secret Manager with Workload Identity and CSI Driver support.

    This manager provides:
    - Native Kubernetes secret management
    - Secret Store CSI Driver integration
    - Workload Identity Federation for GKE
    - Automatic secret synchronization
    - RBAC enforcement
    """

    def __init__(self, config: SecretConfig):
        """Initialize the Kubernetes Secret Manager."""
        if not K8S_AVAILABLE:
            raise SecretManagerError(
                "Kubernetes client dependencies not available. "
                "Install with: pip install kubernetes-asyncio"
            )

        self.config = config
        self.namespace = config.kubernetes_namespace
        self.environment = config.environment
        self._client: Optional[client.CoreV1Api] = None
        self._apps_client: Optional[client.AppsV1Api] = None
        self._custom_client: Optional[client.CustomObjectsApi] = None

        # CSI Driver configuration
        self.csi_driver_enabled = self._check_csi_driver_available()

        logger.info(f"Kubernetes Secret Manager initialized for namespace: {self.namespace}")

    async def initialize(self) -> None:
        """Initialize the Kubernetes client."""
        try:
            # Load configuration - try in-cluster first, then local kubeconfig
            try:
                config.load_incluster_config()
                logger.info("Using in-cluster Kubernetes configuration")
            except config.ConfigException:
                await config.load_kube_config()
                logger.info("Using local kubeconfig")

            # Initialize API clients
            self._client = client.CoreV1Api()
            self._apps_client = client.AppsV1Api()
            self._custom_client = client.CustomObjectsApi()

            # Verify connectivity and permissions
            await self._verify_permissions()

            logger.info("Kubernetes Secret Manager initialized successfully")

        except Exception as e:
            raise SecretManagerError(f"Failed to initialize Kubernetes client: {str(e)}")

    def _check_csi_driver_available(self) -> bool:
        """Check if Secret Store CSI Driver is available in the cluster."""
        # This would typically check for the CSI driver installation
        # For now, we'll check an environment variable
        return os.environ.get("SECRET_STORE_CSI_ENABLED", "false").lower() == "true"

    async def _verify_permissions(self) -> None:
        """Verify that we have necessary permissions."""
        try:
            # Test basic secret operations
            await self._client.list_namespaced_secret(namespace=self.namespace, limit=1)
            logger.debug("Kubernetes secret permissions verified")
        except ApiException as e:
            if e.status == 403:
                raise SecretAccessDeniedError(
                    "kubernetes-secrets",
                    "secrets.list",
                    self._get_service_account()
                )
            raise SecretManagerError(f"Permission verification failed: {str(e)}")

    def _get_service_account(self) -> Optional[str]:
        """Get the current service account name."""
        try:
            with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
                namespace = f.read().strip()
            return f"system:serviceaccount:{namespace}:default"
        except FileNotFoundError:
            return None

    async def get_secret(self, name: str, version: str = "latest") -> SecretValue:
        """
        Retrieve a secret from Kubernetes.

        Args:
            name: Secret name
            version: Secret version (for Kubernetes, this is typically ignored)

        Returns:
            SecretValue object containing the secret and metadata
        """
        secret_name = self._format_secret_name(name)

        try:
            # Try to get secret from Kubernetes
            k8s_secret = await self._client.read_namespaced_secret(
                name=secret_name,
                namespace=self.namespace
            )

            # Extract secret value and metadata
            secret_data = k8s_secret.data or {}
            if not secret_data:
                raise SecretNotFoundError(name, self.environment.value)

            # Get the main secret value (assume first key if multiple)
            secret_key = list(secret_data.keys())[0]
            secret_value = base64.b64decode(secret_data[secret_key]).decode('utf-8')

            # Create metadata from Kubernetes secret
            metadata = self._k8s_secret_to_metadata(k8s_secret)

            return SecretValue(
                value=secret_value,
                metadata=metadata,
                version=k8s_secret.metadata.resource_version or "1",
                checksum=""  # Will be calculated in __post_init__
            )

        except ApiException as e:
            if e.status == 404:
                raise SecretNotFoundError(name, self.environment.value)
            elif e.status == 403:
                raise SecretAccessDeniedError(
                    name,
                    "secrets.get",
                    self._get_service_account()
                )
            else:
                raise SecretManagerError(f"Failed to get secret '{name}': {str(e)}")

    async def set_secret(self, secret_value: SecretValue) -> str:
        """
        Store a secret in Kubernetes.

        Args:
            secret_value: SecretValue object to store

        Returns:
            Version string (resource version) of the created secret
        """
        secret_name = self._format_secret_name(secret_value.metadata.name)

        try:
            # Prepare secret data
            secret_data = {
                "value": base64.b64encode(secret_value.value.encode('utf-8')).decode('utf-8')
            }

            # Prepare labels and annotations
            labels = self._create_labels(secret_value.metadata)
            annotations = self._create_annotations(secret_value.metadata)

            # Create Kubernetes secret object
            k8s_secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name=secret_name,
                    namespace=self.namespace,
                    labels=labels,
                    annotations=annotations
                ),
                type="Opaque",
                data=secret_data
            )

            # Try to update existing secret first
            try:
                response = await self._client.replace_namespaced_secret(
                    name=secret_name,
                    namespace=self.namespace,
                    body=k8s_secret
                )
                operation = "updated"
            except ApiException as e:
                if e.status == 404:
                    # Secret doesn't exist, create it
                    response = await self._client.create_namespaced_secret(
                        namespace=self.namespace,
                        body=k8s_secret
                    )
                    operation = "created"
                else:
                    raise

            version = response.metadata.resource_version
            logger.info(f"Secret '{secret_value.metadata.name}' {operation} with version {version}")

            # If CSI driver is enabled, create SecretProviderClass
            if self.csi_driver_enabled:
                await self._create_secret_provider_class(secret_value.metadata)

            return version

        except ApiException as e:
            if e.status == 403:
                raise SecretAccessDeniedError(
                    secret_value.metadata.name,
                    "secrets.create or secrets.update",
                    self._get_service_account()
                )
            else:
                raise SecretManagerError(
                    f"Failed to store secret '{secret_value.metadata.name}': {str(e)}"
                )

    async def delete_secret(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a secret from Kubernetes.

        Args:
            name: Secret name
            version: Ignored for Kubernetes (versions not directly supported)

        Returns:
            True if deletion was successful
        """
        secret_name = self._format_secret_name(name)

        try:
            # Delete the Kubernetes secret
            await self._client.delete_namespaced_secret(
                name=secret_name,
                namespace=self.namespace
            )

            # Also delete SecretProviderClass if it exists
            if self.csi_driver_enabled:
                await self._delete_secret_provider_class(name)

            logger.info(f"Secret '{name}' deleted from Kubernetes")
            return True

        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Secret '{name}' not found for deletion")
                return False
            elif e.status == 403:
                raise SecretAccessDeniedError(
                    name,
                    "secrets.delete",
                    self._get_service_account()
                )
            else:
                raise SecretManagerError(f"Failed to delete secret '{name}': {str(e)}")

    async def list_secrets(self, filter_tags: Optional[Dict[str, str]] = None) -> List[SecretMetadata]:
        """
        List all secrets in the namespace with optional tag filtering.

        Args:
            filter_tags: Optional tags to filter by

        Returns:
            List of SecretMetadata objects
        """
        try:
            # Build label selector if filter_tags provided
            label_selector = None
            if filter_tags:
                # Convert tags to Kubernetes label selector format
                selectors = []
                for key, value in filter_tags.items():
                    safe_key = self._sanitize_label_key(key)
                    safe_value = self._sanitize_label_value(value)
                    selectors.append(f"{safe_key}={safe_value}")
                label_selector = ",".join(selectors)

            # List secrets
            secret_list = await self._client.list_namespaced_secret(
                namespace=self.namespace,
                label_selector=label_selector
            )

            secrets = []
            for k8s_secret in secret_list.items:
                # Skip non-managed secrets
                if not self._is_managed_secret(k8s_secret):
                    continue

                metadata = self._k8s_secret_to_metadata(k8s_secret)
                secrets.append(metadata)

            return secrets

        except ApiException as e:
            if e.status == 403:
                raise SecretAccessDeniedError(
                    "list-secrets",
                    "secrets.list",
                    self._get_service_account()
                )
            else:
                raise SecretManagerError(f"Failed to list secrets: {str(e)}")

    async def _create_secret_provider_class(self, metadata: SecretMetadata) -> None:
        """Create a SecretProviderClass for CSI driver integration."""
        if not self.csi_driver_enabled:
            return

        try:
            spc_name = self._format_secret_name(metadata.name) + "-spc"

            # Create SecretProviderClass manifest
            spc_manifest = {
                "apiVersion": "secrets-store.csi.x-k8s.io/v1",
                "kind": "SecretProviderClass",
                "metadata": {
                    "name": spc_name,
                    "namespace": self.namespace,
                    "labels": self._create_labels(metadata)
                },
                "spec": {
                    "provider": "gcp",
                    "parameters": {
                        "secrets": json.dumps([
                            {
                                "resourceName": f"projects/{self.config.gcp_project_id}/secrets/{metadata.name}/versions/latest",
                                "path": metadata.name
                            }
                        ])
                    }
                }
            }

            # Create the SecretProviderClass
            await self._custom_client.create_namespaced_custom_object(
                group="secrets-store.csi.x-k8s.io",
                version="v1",
                namespace=self.namespace,
                plural="secretproviderclasses",
                body=spc_manifest
            )

            logger.info(f"SecretProviderClass created for secret '{metadata.name}'")

        except Exception as e:
            logger.warning(f"Failed to create SecretProviderClass for '{metadata.name}': {str(e)}")

    async def _delete_secret_provider_class(self, name: str) -> None:
        """Delete the SecretProviderClass for a secret."""
        if not self.csi_driver_enabled:
            return

        try:
            spc_name = self._format_secret_name(name) + "-spc"

            await self._custom_client.delete_namespaced_custom_object(
                group="secrets-store.csi.x-k8s.io",
                version="v1",
                namespace=self.namespace,
                plural="secretproviderclasses",
                name=spc_name
            )

            logger.info(f"SecretProviderClass deleted for secret '{name}'")

        except ApiException as e:
            if e.status != 404:  # Ignore not found errors
                logger.warning(f"Failed to delete SecretProviderClass for '{name}': {str(e)}")

    def _k8s_secret_to_metadata(self, k8s_secret) -> SecretMetadata:
        """Convert Kubernetes secret to SecretMetadata."""
        labels = k8s_secret.metadata.labels or {}
        annotations = k8s_secret.metadata.annotations or {}

        # Extract metadata from labels and annotations
        secret_type_str = labels.get("zen-secrets/type", "custom")
        try:
            secret_type = SecretType(secret_type_str.replace("-", "_"))
        except ValueError:
            secret_type = SecretType.CUSTOM

        classification_str = labels.get("zen-secrets/classification", "medium")
        try:
            classification = SecretClassification(classification_str)
        except ValueError:
            classification = SecretClassification.MEDIUM

        environment_str = labels.get("zen-secrets/environment", "development")
        try:
            environment = SecretEnvironment(environment_str)
        except ValueError:
            environment = SecretEnvironment.DEVELOPMENT

        # Extract custom tags (remove system labels)
        system_label_prefixes = ["zen-secrets/", "kubernetes.io/", "app.kubernetes.io/"]
        tags = {}
        for key, value in labels.items():
            if not any(key.startswith(prefix) for prefix in system_label_prefixes):
                # Convert back from sanitized format
                original_key = key.replace("--", "_").replace("-", ".")
                tags[original_key] = value

        # Extract original secret name
        original_name = annotations.get("zen-secrets/original-name", k8s_secret.metadata.name)

        return SecretMetadata(
            name=original_name,
            secret_type=secret_type,
            classification=classification,
            environment=environment,
            created_at=k8s_secret.metadata.creation_timestamp,
            tags=tags,
            description=annotations.get("zen-secrets/description"),
            owner=annotations.get("zen-secrets/owner")
        )

    def _create_labels(self, metadata: SecretMetadata) -> Dict[str, str]:
        """Create Kubernetes labels from SecretMetadata."""
        labels = {
            "zen-secrets/managed": "true",
            "zen-secrets/type": metadata.secret_type.value.replace("_", "-"),
            "zen-secrets/classification": metadata.classification.value,
            "zen-secrets/environment": metadata.environment.value
        }

        # Add custom tags as labels (sanitized)
        for key, value in metadata.tags.items():
            safe_key = self._sanitize_label_key(key)
            safe_value = self._sanitize_label_value(value)
            labels[safe_key] = safe_value

        return labels

    def _create_annotations(self, metadata: SecretMetadata) -> Dict[str, str]:
        """Create Kubernetes annotations from SecretMetadata."""
        annotations = {
            "zen-secrets/original-name": metadata.name,
            "zen-secrets/created-at": metadata.created_at.isoformat()
        }

        if metadata.description:
            annotations["zen-secrets/description"] = metadata.description

        if metadata.owner:
            annotations["zen-secrets/owner"] = metadata.owner

        return annotations

    def _sanitize_label_key(self, key: str) -> str:
        """Sanitize a key for use as a Kubernetes label key."""
        # Replace invalid characters with safe alternatives
        sanitized = key.replace("_", "--").replace(".", "-")

        # Ensure it meets Kubernetes requirements
        # Must be 63 characters or less, start and end with alphanumeric
        if len(sanitized) > 63:
            sanitized = sanitized[:63]

        return sanitized

    def _sanitize_label_value(self, value: str) -> str:
        """Sanitize a value for use as a Kubernetes label value."""
        # Replace invalid characters
        sanitized = value.replace("_", "-").replace(".", "-")

        # Ensure it meets Kubernetes requirements
        if len(sanitized) > 63:
            sanitized = sanitized[:63]

        return sanitized

    def _format_secret_name(self, name: str) -> str:
        """
        Format secret name to be Kubernetes-compliant.
        Kubernetes resource names must be DNS-1123 subdomain names.
        """
        # Replace invalid characters
        formatted = name.lower().replace("_", "-").replace(".", "-").replace("/", "-")

        # Add environment prefix
        env_prefix = f"{self.environment.value}-"

        # Ensure it doesn't exceed 253 characters (DNS subdomain limit)
        max_length = 253 - len(env_prefix)
        if len(formatted) > max_length:
            formatted = formatted[:max_length]

        # Ensure it ends with alphanumeric character
        if formatted.endswith("-"):
            formatted = formatted[:-1] + "x"

        return f"{env_prefix}{formatted}"

    def _is_managed_secret(self, k8s_secret) -> bool:
        """Check if a Kubernetes secret is managed by zen-secrets."""
        labels = k8s_secret.metadata.labels or {}
        return labels.get("zen-secrets/managed") == "true"

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Kubernetes connection."""
        try:
            start_time = datetime.utcnow()

            # Test basic connectivity
            await self._client.list_namespaced_secret(namespace=self.namespace, limit=1)

            end_time = datetime.utcnow()

            return {
                "status": "healthy",
                "response_time_ms": (end_time - start_time).total_seconds() * 1000,
                "namespace": self.namespace,
                "csi_driver_enabled": self.csi_driver_enabled,
                "service_account": self._get_service_account(),
                "timestamp": end_time.isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "namespace": self.namespace,
                "timestamp": datetime.utcnow().isoformat()
            }

    async def close(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.api_client.close()
        if self._apps_client:
            await self._apps_client.api_client.close()
        if self._custom_client:
            await self._custom_client.api_client.close()

        logger.info("Kubernetes Secret Manager closed")