"""
JWT Test Manager - Authentication JWT token generation and validation for tests

Provides comprehensive JWT token generation, validation, and security testing
utilities for cross-service authentication testing.
"""

import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

import httpx
import jwt

from tests.e2e.jwt_token_helpers import JWTTestHelper

logger = logging.getLogger(__name__)

@dataclass
class TokenSet:
    """Container for JWT token set with user information."""
    access_token: str
    refresh_token: str
    user_id: str
    expires_at: Optional[datetime] = None

class JWTGenerationTestManager:
    """Base class for JWT token generation and validation testing."""
    
    def __init__(self, environment: Optional[str] = None):
        """Initialize JWT test manager with environment configuration."""
        self.jwt_helper = JWTTestHelper(environment)
        self.environment = environment or self.jwt_helper.environment
        self.generated_tokens: List[TokenSet] = []
        
        # Service endpoints based on environment
        if self.environment == "test":
            self.auth_service_url = "http://localhost:8083"
            self.backend_service_url = "http://localhost:8001"
        else:  # dev
            self.auth_service_url = "http://localhost:8081"
            self.backend_service_url = "http://localhost:8000"
    
    async def generate_token_via_auth_service(self, 
                                              user_id: Optional[str] = None,
                                              include_refresh: bool = True) -> TokenSet:
        """Generate JWT token set via Auth service authentication."""
        if user_id is None:
            user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        access_token = await self.jwt_helper.generate_valid_token(user_id=user_id)
        refresh_token = ""
        
        if include_refresh:
            refresh_token = await self.jwt_helper.generate_refresh_token(user_id=user_id)
        
        token_set = TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id
        )
        
        self.generated_tokens.append(token_set)
        return token_set
    
    async def validate_token_across_services(self, token: str) -> Dict[str, bool]:
        """Validate token across all services."""
        results = {}
        results["auth_service"] = await self._validate_token_auth_service(token)
        results["backend_service"] = await self._validate_token_backend_service(token)
        results["jwt_direct"] = await self._validate_token_direct(token)
        return results
    
    async def _validate_token_auth_service(self, token: str) -> bool:
        """Validate token against Auth service."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.auth_service_url}/auth/validate",
                    headers=headers,
                    timeout=5.0
                )
                return response.status_code == 200
        except:
            return False
    
    async def _validate_token_backend_service(self, token: str) -> bool:
        """Validate token against Backend service."""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {token}"}
                response = await client.get(
                    f"{self.backend_service_url}/api/validate_token",
                    headers=headers,
                    timeout=5.0
                )
                return response.status_code == 200
        except:
            return False
    
    async def _validate_token_direct(self, token: str) -> bool:
        """Direct JWT token validation."""
        try:
            return self.jwt_helper.validate_jwt_token(token)
        except:
            return False
    
    async def _validate_revoked_token_auth_service(self, token: str) -> bool:
        """Test if auth service accepts a revoked token (should return False)."""
        return await self._validate_token_auth_service(token)
    
    async def _validate_revoked_token_backend_service(self, token: str) -> bool:
        """Test if backend service accepts a revoked token (should return False)."""
        return await self._validate_token_backend_service(token)
    
    async def _validate_revoked_token_direct(self, token: str) -> bool:
        """Test if direct validation accepts a revoked token (should return False)."""
        return await self._validate_token_direct(token)
    
    async def test_expired_token_handling(self) -> Dict[str, Any]:
        """Test expired token handling across services."""
        expired_token = await self.jwt_helper.generate_expired_token()
        validation_results = await self.validate_token_across_services(expired_token)
        return {
            "expired_token": expired_token,
            "validation_results": validation_results,
            "all_rejected": not any(validation_results.values())
        }
    
    def _create_none_algorithm_token(self) -> str:
        """Create a JWT token with 'none' algorithm for security testing."""
        payload = {
            "sub": "test_user",
            "iat": datetime.now(timezone.utc).timestamp(),
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iss": "test_issuer"
        }
        
        header = {"typ": "JWT", "alg": "none"}
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"{header_b64}.{payload_b64}."
    
    def _create_wrong_issuer_token(self) -> str:
        """Create a JWT token with wrong issuer for security testing."""
        try:
            return self.jwt_helper.generate_token_with_wrong_issuer()
        except:
            payload = {
                "sub": "test_user",
                "iat": datetime.now(timezone.utc).timestamp(),
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
                "iss": "wrong_issuer"
            }
            return jwt.encode(payload, "wrong_secret", algorithm="HS256")
    
    def _create_service_token(self) -> str:
        """Create a service-to-service token for testing."""
        payload = {
            "sub": "service_account",
            "iat": datetime.now(timezone.utc).timestamp(),
            "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            "iss": "service_issuer",
            "type": "service"
        }
        return jwt.encode(payload, "service_secret", algorithm="HS256")
