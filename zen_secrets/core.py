"""
Core Secret Management System

This module provides the main SecretManager class and core data structures
for the Zen Secret Management System. It serves as the primary interface
for all secret operations and coordinates between different backends.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from uuid import uuid4

from .exceptions import (
    SecretManagerError,
    SecretNotFoundError,
    SecretValidationError,
    SecretConfigurationError,
    SecretIntegrityError
)

logger = logging.getLogger(__name__)


class SecretType(Enum):
    """Types of secrets managed by the system."""
    OAUTH_TOKEN = "oauth_token"
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    SERVICE_ACCOUNT = "service_account"
    WEBHOOK_SECRET = "webhook_secret"
    ENCRYPTION_KEY = "encryption_key"
    TELEMETRY_TOKEN = "telemetry_token"
    CUSTOM = "custom"


class SecretClassification(Enum):
    """Security classification levels for secrets."""
    CRITICAL = "critical"      # System-critical secrets (database passwords, root keys)
    HIGH = "high"             # Sensitive secrets (OAuth tokens, API keys)
    MEDIUM = "medium"         # Moderately sensitive (webhook secrets, telemetry tokens)
    LOW = "low"              # Low sensitivity (public API endpoints, non-sensitive config)


class SecretEnvironment(Enum):
    """Environment types for secret management."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class SecretMetadata:
    """Metadata associated with a secret."""
    name: str
    secret_type: SecretType
    classification: SecretClassification
    environment: SecretEnvironment
    created_at: datetime
    last_rotated: Optional[datetime] = None
    rotation_interval: Optional[timedelta] = None
    tags: Dict[str, str] = field(default_factory=dict)
    description: Optional[str] = None
    owner: Optional[str] = None
    access_logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "secret_type": self.secret_type.value,
            "classification": self.classification.value,
            "environment": self.environment.value,
            "created_at": self.created_at.isoformat(),
            "last_rotated": self.last_rotated.isoformat() if self.last_rotated else None,
            "rotation_interval_days": self.rotation_interval.days if self.rotation_interval else None,
            "tags": self.tags,
            "description": self.description,
            "owner": self.owner,
            "access_count": len(self.access_logs)
        }


@dataclass
class SecretValue:
    """Container for secret value with metadata."""
    value: str
    metadata: SecretMetadata
    version: str
    checksum: str

    def __post_init__(self):
        """Calculate checksum if not provided."""
        if not self.checksum:
            self.checksum = hashlib.sha256(self.value.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify the integrity of the secret value."""
        expected_checksum = hashlib.sha256(self.value.encode()).hexdigest()
        return self.checksum == expected_checksum

    def to_dict(self, include_value: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally including the secret value."""
        result = {
            "metadata": self.metadata.to_dict(),
            "version": self.version,
            "checksum": self.checksum,
            "integrity_verified": self.verify_integrity()
        }
        if include_value:
            result["value"] = self.value
        return result


@dataclass
class SecretConfig:
    """Configuration for the Secret Management System."""

    # Google Secret Manager settings
    gcp_project_id: str
    gsm_enabled: bool = True

    # Kubernetes settings
    kubernetes_enabled: bool = True
    kubernetes_namespace: str = "default"
    workload_identity_enabled: bool = True

    # Environment settings
    environment: SecretEnvironment = SecretEnvironment.DEVELOPMENT

    # Security settings
    encryption_key_id: Optional[str] = None
    enforce_rotation: bool = True
    default_rotation_interval: timedelta = field(default_factory=lambda: timedelta(days=90))

    # Monitoring settings
    monitoring_enabled: bool = True
    audit_logging_enabled: bool = True
    alert_on_access_denied: bool = True
    alert_on_rotation_failure: bool = True

    # Backup settings
    backup_enabled: bool = True
    backup_retention_days: int = 30

    # Performance settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    max_concurrent_operations: int = 10

    # Validation settings
    strict_validation: bool = True
    require_classification: bool = True

    @classmethod
    def from_environment(cls, env_prefix: str = "ZEN_SECRETS") -> "SecretConfig":
        """Create configuration from environment variables."""
        def get_env(key: str, default: Any = None, type_func: Callable = str) -> Any:
            env_key = f"{env_prefix}_{key}"
            value = os.environ.get(env_key, default)
            if value is None:
                return None
            if type_func == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            return type_func(value)

        # Required settings
        gcp_project_id = get_env("GCP_PROJECT_ID")
        if not gcp_project_id:
            raise SecretConfigurationError("GCP_PROJECT_ID is required")

        environment_str = get_env("ENVIRONMENT", "development")
        try:
            environment = SecretEnvironment(environment_str.lower())
        except ValueError:
            raise SecretConfigurationError(f"Invalid environment: {environment_str}")

        return cls(
            gcp_project_id=gcp_project_id,
            gsm_enabled=get_env("GSM_ENABLED", True, bool),
            kubernetes_enabled=get_env("KUBERNETES_ENABLED", True, bool),
            kubernetes_namespace=get_env("KUBERNETES_NAMESPACE", "default"),
            workload_identity_enabled=get_env("WORKLOAD_IDENTITY_ENABLED", True, bool),
            environment=environment,
            encryption_key_id=get_env("ENCRYPTION_KEY_ID"),
            enforce_rotation=get_env("ENFORCE_ROTATION", True, bool),
            default_rotation_interval=timedelta(days=get_env("DEFAULT_ROTATION_DAYS", 90, int)),
            monitoring_enabled=get_env("MONITORING_ENABLED", True, bool),
            audit_logging_enabled=get_env("AUDIT_LOGGING_ENABLED", True, bool),
            alert_on_access_denied=get_env("ALERT_ON_ACCESS_DENIED", True, bool),
            alert_on_rotation_failure=get_env("ALERT_ON_ROTATION_FAILURE", True, bool),
            backup_enabled=get_env("BACKUP_ENABLED", True, bool),
            backup_retention_days=get_env("BACKUP_RETENTION_DAYS", 30, int),
            cache_enabled=get_env("CACHE_ENABLED", True, bool),
            cache_ttl_seconds=get_env("CACHE_TTL_SECONDS", 300, int),
            max_concurrent_operations=get_env("MAX_CONCURRENT_OPERATIONS", 10, int),
            strict_validation=get_env("STRICT_VALIDATION", True, bool),
            require_classification=get_env("REQUIRE_CLASSIFICATION", True, bool)
        )

    @classmethod
    def from_file(cls, config_path: Path) -> "SecretConfig":
        """Load configuration from JSON or YAML file."""
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    import yaml
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            # Convert string enums to enum objects
            if 'environment' in data:
                data['environment'] = SecretEnvironment(data['environment'])

            # Convert rotation interval
            if 'default_rotation_interval' in data:
                days = data.pop('default_rotation_interval')
                data['default_rotation_interval'] = timedelta(days=days)

            return cls(**data)

        except Exception as e:
            raise SecretConfigurationError(
                f"Failed to load configuration from {config_path}: {str(e)}",
                str(config_path)
            )


class SecretManager:
    """
    Main Secret Manager class.

    This is the primary interface for all secret management operations.
    It coordinates between different backends (GSM, Kubernetes) and provides
    a unified API for secret operations.
    """

    def __init__(self, config: SecretConfig):
        """Initialize the Secret Manager."""
        self.config = config
        self.session_id = str(uuid4())
        self._cache: Dict[str, SecretValue] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._operation_semaphore = asyncio.Semaphore(config.max_concurrent_operations)

        # Initialize backends
        self._gsm_client = None
        self._k8s_client = None
        self._rotation_engine = None
        self._monitor = None

        logger.info(f"SecretManager initialized with session_id={self.session_id}")

    async def initialize(self) -> None:
        """Initialize all backends asynchronously."""
        if self.config.gsm_enabled:
            from .gsm import GoogleSecretManagerClient
            self._gsm_client = GoogleSecretManagerClient(self.config)
            await self._gsm_client.initialize()

        if self.config.kubernetes_enabled:
            from .kubernetes import KubernetesSecretManager
            self._k8s_client = KubernetesSecretManager(self.config)
            await self._k8s_client.initialize()

        if self.config.enforce_rotation:
            from .rotation import SecretRotationEngine
            self._rotation_engine = SecretRotationEngine(self.config, self)
            await self._rotation_engine.initialize()

        if self.config.monitoring_enabled:
            from .monitoring import SecretMonitor
            self._monitor = SecretMonitor(self.config)
            await self._monitor.initialize()

        logger.info("All Secret Manager backends initialized successfully")

    async def get_secret(self, name: str, version: str = "latest") -> SecretValue:
        """
        Get a secret by name and version.

        Args:
            name: Secret name
            version: Secret version (default: "latest")

        Returns:
            SecretValue object containing the secret and metadata

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretAccessDeniedError: If access is denied
        """
        async with self._operation_semaphore:
            cache_key = f"{name}:{version}"

            # Check cache first
            if self.config.cache_enabled and self._is_cached(cache_key):
                secret_value = self._cache[cache_key]
                if secret_value.verify_integrity():
                    await self._log_access(name, "cache_hit")
                    return secret_value
                else:
                    # Cache corruption detected, remove from cache
                    self._invalidate_cache(cache_key)
                    logger.warning(f"Cache corruption detected for {name}, fetching fresh copy")

            # Fetch from primary backend
            secret_value = await self._fetch_secret(name, version)

            # Validate secret
            if self.config.strict_validation:
                await self._validate_secret(secret_value)

            # Update cache
            if self.config.cache_enabled:
                self._cache[cache_key] = secret_value
                self._cache_timestamps[cache_key] = time.time()

            # Log access
            await self._log_access(name, "fetched")

            return secret_value

    async def set_secret(self, name: str, value: str, metadata: SecretMetadata) -> str:
        """
        Create or update a secret.

        Args:
            name: Secret name
            value: Secret value
            metadata: Secret metadata

        Returns:
            Version string of the created secret
        """
        async with self._operation_semaphore:
            # Validate metadata
            if self.config.require_classification and not metadata.classification:
                raise SecretValidationError(name, ["classification is required"])

            # Create secret value object
            version = str(uuid4())
            secret_value = SecretValue(
                value=value,
                metadata=metadata,
                version=version,
                checksum=""  # Will be calculated in __post_init__
            )

            # Validate secret
            if self.config.strict_validation:
                await self._validate_secret(secret_value)

            # Store in primary backend
            version = await self._store_secret(secret_value)

            # Invalidate cache
            cache_key = f"{name}:latest"
            self._invalidate_cache(cache_key)

            # Log operation
            await self._log_access(name, "created")

            return version

    async def rotate_secret(self, name: str) -> str:
        """
        Rotate a secret using the rotation engine.

        Args:
            name: Secret name to rotate

        Returns:
            New version string
        """
        if not self._rotation_engine:
            raise SecretManagerError("Secret rotation is not enabled")

        return await self._rotation_engine.rotate_secret(name)

    async def delete_secret(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a secret or specific version.

        Args:
            name: Secret name
            version: Specific version to delete (None for all versions)

        Returns:
            True if deletion was successful
        """
        async with self._operation_semaphore:
            success = await self._delete_secret(name, version)

            # Invalidate cache
            if version:
                cache_key = f"{name}:{version}"
                self._invalidate_cache(cache_key)
            else:
                # Clear all cached versions
                keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{name}:")]
                for key in keys_to_remove:
                    self._invalidate_cache(key)

            # Log operation
            await self._log_access(name, "deleted")

            return success

    async def list_secrets(self, filter_tags: Optional[Dict[str, str]] = None) -> List[SecretMetadata]:
        """
        List all secrets with optional tag filtering.

        Args:
            filter_tags: Optional tags to filter by

        Returns:
            List of SecretMetadata objects
        """
        return await self._list_secrets(filter_tags)

    async def backup_secrets(self, backup_location: str) -> Dict[str, Any]:
        """
        Backup all secrets to specified location.

        Args:
            backup_location: Where to store the backup

        Returns:
            Backup metadata
        """
        if not self.config.backup_enabled:
            raise SecretManagerError("Backup is not enabled")

        # Implementation would go here
        # This is a placeholder for the backup functionality
        logger.info(f"Backing up secrets to {backup_location}")
        return {"backup_id": str(uuid4()), "timestamp": datetime.utcnow().isoformat()}

    def _is_cached(self, cache_key: str) -> bool:
        """Check if a secret is cached and not expired."""
        if cache_key not in self._cache:
            return False

        timestamp = self._cache_timestamps.get(cache_key, 0)
        return (time.time() - timestamp) < self.config.cache_ttl_seconds

    def _invalidate_cache(self, cache_key: str) -> None:
        """Remove a secret from cache."""
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)

    async def _fetch_secret(self, name: str, version: str) -> SecretValue:
        """Fetch secret from primary backend."""
        if self._gsm_client:
            return await self._gsm_client.get_secret(name, version)
        elif self._k8s_client:
            return await self._k8s_client.get_secret(name, version)
        else:
            raise SecretManagerError("No secret backend available")

    async def _store_secret(self, secret_value: SecretValue) -> str:
        """Store secret in primary backend."""
        if self._gsm_client:
            return await self._gsm_client.set_secret(secret_value)
        elif self._k8s_client:
            return await self._k8s_client.set_secret(secret_value)
        else:
            raise SecretManagerError("No secret backend available")

    async def _delete_secret(self, name: str, version: Optional[str]) -> bool:
        """Delete secret from primary backend."""
        if self._gsm_client:
            return await self._gsm_client.delete_secret(name, version)
        elif self._k8s_client:
            return await self._k8s_client.delete_secret(name, version)
        else:
            raise SecretManagerError("No secret backend available")

    async def _list_secrets(self, filter_tags: Optional[Dict[str, str]]) -> List[SecretMetadata]:
        """List secrets from primary backend."""
        if self._gsm_client:
            return await self._gsm_client.list_secrets(filter_tags)
        elif self._k8s_client:
            return await self._k8s_client.list_secrets(filter_tags)
        else:
            raise SecretManagerError("No secret backend available")

    async def _validate_secret(self, secret_value: SecretValue) -> None:
        """Validate secret value and metadata."""
        errors = []

        # Check integrity
        if not secret_value.verify_integrity():
            errors.append("integrity check failed")

        # Check required fields
        if not secret_value.value:
            errors.append("secret value is empty")

        if not secret_value.metadata.name:
            errors.append("secret name is required")

        # Environment-specific validations
        if self.config.environment == SecretEnvironment.PRODUCTION:
            if secret_value.metadata.classification == SecretClassification.LOW:
                errors.append("low classification secrets not allowed in production")

        if errors:
            raise SecretValidationError(secret_value.metadata.name, errors)

    async def _log_access(self, name: str, operation: str) -> None:
        """Log secret access for audit purposes."""
        if self.config.audit_logging_enabled:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": self.session_id,
                "secret_name": name,
                "operation": operation,
                "environment": self.config.environment.value
            }
            logger.info(f"Secret access: {json.dumps(log_entry)}")

            # Send to monitoring system if available
            if self._monitor:
                await self._monitor.log_access(log_entry)

    async def close(self) -> None:
        """Clean up resources."""
        if self._gsm_client:
            await self._gsm_client.close()
        if self._k8s_client:
            await self._k8s_client.close()
        if self._rotation_engine:
            await self._rotation_engine.close()
        if self._monitor:
            await self._monitor.close()

        # Clear cache
        self._cache.clear()
        self._cache_timestamps.clear()

        logger.info(f"SecretManager session {self.session_id} closed")