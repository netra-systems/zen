"""
Shared JWT Secret Manager
Simple implementation to support basic JWT functionality
"""

from shared.isolated_environment import get_env


class SharedJWTSecretManager:
    """Shared JWT secret manager for consistent secret handling across services"""
    
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT secret from environment"""
        env = get_env()
        return env.get(
            'JWT_SECRET_KEY',
            'dev-jwt-secret-key-must-be-at-least-32-characters'
        )
    
    @staticmethod
    def get_service_secret() -> str:
        """Get service secret from environment"""
        env = get_env()
        return env.get(
            'SERVICE_SECRET', 
            'test-secret-for-local-development-only-32chars'
        )
    
    @staticmethod
    def validate_jwt_secret(secret: str) -> bool:
        """Validate JWT secret meets minimum requirements"""
        return bool(secret and len(secret) >= 32)