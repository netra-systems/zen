"""
SSOT Secrets Configuration Module
Compatibility layer for secret management across the Netra platform.

This module provides backward compatibility for the expected SecretManager import
while delegating to the unified secrets management system.
"""

# Re-export from unified_secrets for backward compatibility
from netra_backend.app.core.configuration.unified_secrets import (
    UnifiedSecretsManager,
    UnifiedSecretManager,  # Alias for compatibility
    get_secrets_manager,
    get_secret,
    set_secret,
    get_jwt_secret,
    SecretConfig
)

# Provide the expected SecretManager class name
SecretManager = UnifiedSecretsManager

# Standard exports
__all__ = [
    'SecretManager',
    'UnifiedSecretsManager', 
    'UnifiedSecretManager',
    'get_secrets_manager',
    'get_secret',
    'set_secret',
    'get_jwt_secret',
    'SecretConfig'
]