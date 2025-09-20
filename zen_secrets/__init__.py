"""
Zen Secrets Management System

A bulletproof secret management system designed for production-ready OSS applications.
Provides secure integration with Google Secret Manager, Kubernetes Workload Identity,
and comprehensive secret lifecycle management.

Core Features:
- Google Secret Manager integration with Workload Identity
- Kubernetes-native secret management
- Automated secret rotation and lifecycle management
- Comprehensive monitoring and alerting
- Multi-environment support (dev/staging/prod)
- Zero-downtime secret updates
- Audit logging and compliance

Usage:
    from zen_secrets import SecretManager, SecretConfig

    # Initialize secret manager
    config = SecretConfig.from_environment()
    secret_manager = SecretManager(config)

    # Get secrets
    oauth_secret = await secret_manager.get_secret("apex-oauth-token")
    telemetry_token = await secret_manager.get_secret("telemetry-service-account")
"""

__version__ = "1.0.0"
__author__ = "Netra Systems"

from .core import SecretManager, SecretConfig, SecretType, SecretClassification
from .gsm import GoogleSecretManagerClient
from .kubernetes import KubernetesSecretManager
from .rotation import SecretRotationEngine
from .monitoring import SecretMonitor
from .exceptions import (
    SecretManagerError,
    SecretNotFoundError,
    SecretAccessDeniedError,
    SecretRotationError,
    SecretValidationError
)

__all__ = [
    "SecretManager",
    "SecretConfig",
    "SecretType",
    "SecretClassification",
    "GoogleSecretManagerClient",
    "KubernetesSecretManager",
    "SecretRotationEngine",
    "SecretMonitor",
    "SecretManagerError",
    "SecretNotFoundError",
    "SecretAccessDeniedError",
    "SecretRotationError",
    "SecretValidationError"
]