"""
Enhanced secret management system with multiple security layers.
Implements secure secret storage, rotation, and access control following PRODUCTION_SECRETS_ISOLATION.xml.

This module now uses a modular architecture with components split across multiple files:
- secret_manager_types.py: Basic types and enums
- secret_manager_encryption.py: Encryption functionality
- secret_manager_auth.py: Authentication methods
- secret_manager_loading.py: Secret loading functionality  
- secret_manager_core.py: Core secret manager
- secret_manager_factory.py: Factory functions

This file maintains backward compatibility by re-exporting the main classes and functions.
"""

# Re-export main classes and functions for backward compatibility
from netra_backend.app.core.secret_manager_types import SecretAccessLevel, SecretMetadata
from netra_backend.app.core.secret_manager_encryption import SecretEncryption
from netra_backend.app.core.secret_manager_core import EnhancedSecretManager
from netra_backend.app.core.secret_manager_factory import create_secret_manager, enhanced_secret_manager
from netra_backend.app.schemas.config_types import EnvironmentType

# Expose the main API
__all__ = [
    'SecretAccessLevel',
    'SecretMetadata', 
    'SecretEncryption',
    'EnhancedSecretManager',
    'create_secret_manager',
    'enhanced_secret_manager',
    'EnvironmentType'
]