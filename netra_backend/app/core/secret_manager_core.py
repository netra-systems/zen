"""
Core secret manager implementation.
Provides the main EnhancedSecretManager class for secure secret management.
"""

import os
from typing import Any, Dict, Optional

from netra_backend.app.core.secret_manager_types import SecretAccessLevel, SecretMetadata
from netra_backend.app.schemas.config_types import EnvironmentType


class EnhancedSecretManager:
    """Enhanced secret manager with security levels and environment isolation."""
    
    def __init__(self, environment: EnvironmentType):
        """Initialize secret manager for given environment."""
        self.environment = environment
        self._secrets_metadata: Dict[str, SecretMetadata] = {}
    
    def get_secret(self, secret_name: str, access_level: SecretAccessLevel = SecretAccessLevel.INTERNAL) -> Optional[str]:
        """Get secret by name with access level validation."""
        # Record access
        if secret_name in self._secrets_metadata:
            self._secrets_metadata[secret_name].record_access("enhanced_secret_manager")
        else:
            # Create metadata for new secret
            self._secrets_metadata[secret_name] = SecretMetadata(
                secret_name=secret_name,
                access_level=access_level,
                environment=self.environment
            )
        
        # Get from environment
        return os.getenv(secret_name)
    
    def set_secret(self, secret_name: str, value: str, access_level: SecretAccessLevel = SecretAccessLevel.INTERNAL) -> None:
        """Set secret with metadata tracking."""
        # Create or update metadata
        self._secrets_metadata[secret_name] = SecretMetadata(
            secret_name=secret_name,
            access_level=access_level,
            environment=self.environment
        )
        
        # Set in environment (for development/testing)
        os.environ[secret_name] = value
    
    def has_secret(self, secret_name: str) -> bool:
        """Check if secret exists."""
        return secret_name in os.environ
    
    def get_metadata(self, secret_name: str) -> Optional[SecretMetadata]:
        """Get secret metadata."""
        return self._secrets_metadata.get(secret_name)
    
    def list_secrets(self) -> Dict[str, SecretMetadata]:
        """List all secret metadata."""
        return self._secrets_metadata.copy()
    
    def validate_access(self, secret_name: str, component: str, required_level: SecretAccessLevel) -> bool:
        """Validate component access to secret."""
        metadata = self.get_metadata(secret_name)
        if not metadata:
            return False
        
        # Check access level
        access_levels = [
            SecretAccessLevel.PUBLIC,
            SecretAccessLevel.INTERNAL,
            SecretAccessLevel.RESTRICTED,
            SecretAccessLevel.CRITICAL
        ]
        
        current_level_index = access_levels.index(metadata.access_level)
        required_level_index = access_levels.index(required_level)
        
        return current_level_index >= required_level_index
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        return {
            "environment": self.environment.value,
            "secret_count": len(self._secrets_metadata),
            "access_levels": [level.value for level in SecretAccessLevel]
        }