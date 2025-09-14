"""
JWT Test Generation Manager for Authentication Testing

SSOT compliant test utility for JWT generation and management in test environments.
Provides centralized JWT token generation following established patterns from jwt_test_utils.py

Business Value Justification (BVJ):
- Segment: Platform/Testing Infrastructure
- Business Goal: Enable reliable authentication testing across all services
- Value Impact: Prevents JWT-related test failures, enables Golden Path testing
- Strategic Impact: Supports $500K+ ARR by ensuring authentication system reliability
"""

from typing import Dict, List, Optional, Any
from test_framework.jwt_test_utils import JWTTestHelper


class JWTGenerationTestManager:
    """
    SSOT JWT Generation Test Manager
    
    Centralizes JWT token generation for all test scenarios while maintaining
    compatibility with existing test framework patterns.
    """
    
    def __init__(self, secret: Optional[str] = None):
        """
        Initialize JWT Generation Test Manager
        
        Args:
            secret: Optional JWT secret override for testing
        """
        self.jwt_helper = JWTTestHelper(secret=secret)
    
    def generate_test_token(
        self,
        user_id: str = "test-user",
        email: str = "test@example.com",
        permissions: Optional[List[str]] = None,
        expires_in_minutes: int = 60,
        **kwargs
    ) -> str:
        """
        Generate a standard test JWT token
        
        Args:
            user_id: User ID to include in token
            email: User email
            permissions: List of user permissions
            expires_in_minutes: Token expiration time
            **kwargs: Additional token claims
            
        Returns:
            JWT token string
        """
        return self.jwt_helper.create_user_token(
            user_id=user_id,
            email=email,
            permissions=permissions,
            expires_in_minutes=expires_in_minutes,
            **kwargs
        )
    
    def generate_service_token(
        self,
        service_name: str,
        expires_in_minutes: int = 60,
        **kwargs
    ) -> str:
        """
        Generate a service-to-service authentication token
        
        Args:
            service_name: Name of the service
            expires_in_minutes: Token expiration time
            **kwargs: Additional token claims
            
        Returns:
            Service JWT token string
        """
        return self.jwt_helper.create_service_token(
            service_name=service_name,
            expires_in_minutes=expires_in_minutes,
            **kwargs
        )
    
    def generate_expired_token(
        self,
        user_id: str = "test-user"
    ) -> str:
        """
        Generate an expired JWT token for testing expired token handling
        
        Args:
            user_id: User ID to include in token
            
        Returns:
            Expired JWT token string
        """
        return self.jwt_helper.create_expired_token(user_id=user_id)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode a JWT token for validation in tests
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded token payload
        """
        return self.jwt_helper.decode_token(token)
    
    def validate_token_format(self, token: str) -> bool:
        """
        Validate that a token has correct JWT structure
        
        Args:
            token: Token to validate
            
        Returns:
            True if token has valid JWT format
        """
        return self.jwt_helper.validate_token_structure(token)
    
    def create_auth_headers(self, token: str) -> Dict[str, str]:
        """
        Create authentication headers for HTTP requests
        
        Args:
            token: JWT token
            
        Returns:
            Dictionary with Authorization header
        """
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    # Compatibility methods for legacy test code
    
    def create_test_jwt(self, **kwargs) -> str:
        """Legacy compatibility method"""
        return self.generate_test_token(**kwargs)
    
    def create_valid_token(self, **kwargs) -> str:
        """Legacy compatibility method"""
        return self.generate_test_token(**kwargs)
    
    def create_invalid_token(self) -> str:
        """Legacy compatibility method - returns expired token"""
        return self.generate_expired_token()


# Convenience function for direct usage
def create_jwt_test_manager(secret: Optional[str] = None) -> JWTGenerationTestManager:
    """
    Create a JWT Generation Test Manager instance
    
    Args:
        secret: Optional JWT secret override
        
    Returns:
        JWTGenerationTestManager instance
    """
    return JWTGenerationTestManager(secret=secret)


# Legacy compatibility exports
JWTTestManager = JWTGenerationTestManager  # Alias for backward compatibility


__all__ = [
    "JWTGenerationTestManager",
    "JWTTestManager", 
    "create_jwt_test_manager"
]