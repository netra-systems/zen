"""
Secret Manager Builder - Unified secret management following SSOT principles

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all services)
- Business Goal: System Reliability, Development Velocity
- Value Impact: Provides unified secret management interface for JWTConfigBuilder
- Strategic Impact: Eliminates JWT configuration failures, maintains SSOT compliance

CRITICAL BUSINESS PROBLEM SOLVED:
JWTConfigBuilder requires a SecretManagerBuilder interface but the implementation
was missing, causing JWT configuration to fail across all services. This creates
a unified secret management interface that leverages existing SSOT patterns.

SSOT COMPLIANCE:
This implementation builds upon existing SharedJWTSecretManager rather than
duplicating secret management logic. It provides the interface needed by
JWTConfigBuilder while maintaining single source of truth for secret handling.
"""

import logging
from typing import Dict, Any, Optional
from shared.jwt_secret_manager import SharedJWTSecretManager
from shared.config_builder_base import ConfigBuilderBase

logger = logging.getLogger(__name__)


class SecretManagerBuilder(ConfigBuilderBase):
    """
    Secret Manager Builder - Unified secret management interface.
    
    Provides organized access to secrets following existing SSOT patterns:
    - auth.get_jwt_secret()
    - environment property  
    - env property for environment variable access
    
    This class serves as an adapter to provide the interface expected by
    JWTConfigBuilder while leveraging existing secret management infrastructure.
    """
    
    def __init__(self, service: str = "shared", env_vars: Optional[Dict[str, Any]] = None):
        """Initialize secret manager builder."""
        # Call parent constructor which handles environment detection and env vars
        super().__init__(env_vars)
        
        self.service = service
        
        # Initialize sub-builders
        self.auth = self.AuthBuilder(self)
    
    class AuthBuilder:
        """Authentication secret builder."""
        
        def __init__(self, parent):
            self.parent = parent
        
        def get_jwt_secret(self) -> str:
            """Get JWT secret key using shared secret manager."""
            return SharedJWTSecretManager.get_jwt_secret()
        
        def get_service_secret(self) -> str:
            """Get service secret using shared secret manager."""
            return SharedJWTSecretManager.get_service_secret()
        
        def validate_jwt_secret(self, secret: str = None) -> bool:
            """Validate JWT secret meets requirements."""
            if secret is None:
                secret = self.get_jwt_secret()
            return SharedJWTSecretManager.validate_jwt_secret(secret)
    
    # Note: environment property is inherited from ConfigBuilderBase
    # env property is also inherited and provides access to environment variables
    
    # Abstract method implementations required by ConfigBuilderBase
    def validate(self) -> tuple[bool, str]:
        """
        Validate secret manager configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Test that we can get JWT secret
            jwt_secret = self.auth.get_jwt_secret()
            if not jwt_secret:
                return False, "JWT secret is not available"
            
            # Validate JWT secret strength
            if not self.auth.validate_jwt_secret(jwt_secret):
                return False, "JWT secret does not meet minimum requirements (32+ characters)"
            
            return True, ""
            
        except Exception as e:
            return False, f"Secret manager validation failed: {str(e)}"
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about secret manager configuration."""
        try:
            # Get common debug info from base class
            debug_info = self.get_common_debug_info()
            
            # Test secret availability
            jwt_secret = self.auth.get_jwt_secret()
            service_secret = self.auth.get_service_secret()
            
            # Add secret manager specific debug information
            debug_info.update({
                "service": self.service,
                "secret_availability": {
                    "jwt_secret_available": bool(jwt_secret),
                    "jwt_secret_length": len(jwt_secret) if jwt_secret else 0,
                    "jwt_secret_valid": self.auth.validate_jwt_secret(jwt_secret),
                    "service_secret_available": bool(service_secret),
                    "service_secret_length": len(service_secret) if service_secret else 0
                },
                "configuration": {
                    "uses_shared_jwt_secret_manager": True,
                    "follows_ssot_principles": True
                }
            })
            
            # Validation info
            is_valid, error = self.validate()
            debug_info["validation"] = {
                "is_valid": is_valid,
                "error": error if error else None
            }
            
            return debug_info
            
        except Exception as e:
            # Get common debug info even on error
            debug_info = self.get_common_debug_info()
            debug_info.update({
                "service": self.service,
                "error": str(e),
                "validation": {
                    "is_valid": False,
                    "error": str(e)
                }
            })
            return debug_info


# Convenience functions for backward compatibility
def get_secret_manager_builder(service: str = "shared") -> SecretManagerBuilder:
    """Get Secret Manager Builder instance for service."""
    return SecretManagerBuilder(service=service)


def validate_secret_manager(service: str = "shared") -> tuple[bool, str]:
    """Validate secret manager for service."""
    builder = SecretManagerBuilder(service=service)
    return builder.validate()


def get_jwt_secret_unified(service: str = "shared") -> str:
    """Get JWT secret using unified secret manager."""
    builder = SecretManagerBuilder(service=service)
    return builder.auth.get_jwt_secret()