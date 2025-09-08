"""Test client for auth service with typed methods."""

import logging
from typing import Any, Dict, List, Optional

import httpx
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


env = get_env()
class AuthTestClient:
    """Typed client for testing auth service endpoints."""
    
    def __init__(self, base_url: str):
        """Initialize auth test client.
        
        Args:
            base_url: Base URL of the auth service (e.g., http://localhost:8081)
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=10.0)
        
    async def register(self, email: str, password: str, 
                      first_name: str = "Test", last_name: str = "User") -> Dict[str, Any]:
        """Register a new user.
        
        Args:
            email: User email
            password: User password
            first_name: User's first name
            last_name: User's last name
            
        Returns:
            User registration response
        """
        response = await self.client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "confirm_password": password,
                "first_name": first_name,
                "last_name": last_name
            }
        )
        response.raise_for_status()
        return response.json()
        
    async def login(self, email: str, password: str) -> str:
        """Login and get JWT token.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            JWT access token
        """
        response = await self.client.post(
            "/auth/login",
            json={
                "email": email,
                "password": password,
                "provider": "local"
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"]
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Token verification response with user info
        """
        response = await self.client.get(
            "/auth/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
        
    async def refresh_token(self, refresh_token: str) -> str:
        """Refresh an access token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New access token
        """
        response = await self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"]
        
    async def logout(self, token: str) -> None:
        """Logout a user.
        
        Args:
            token: JWT token to invalidate
        """
        response = await self.client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        
    async def get_user_profile(self, token: str) -> Dict[str, Any]:
        """Get user profile information.
        
        Args:
            token: JWT token for authentication
            
        Returns:
            User profile data
        """
        response = await self.client.get(
            "/auth/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
        
    async def health_check(self) -> bool:
        """Check auth service health.
        
        Returns:
            True if service is healthy
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def detailed_health_check(self) -> Dict[str, Any]:
        """Perform detailed health check with diagnostic information.
        
        Returns:
            Dictionary with health status and diagnostic information
        """
        import time
        start_time = time.time()
        
        try:
            response = await self.client.get("/health")
            response_time_ms = (time.time() - start_time) * 1000
            
            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "url": f"{self.base_url}/health",
                "service_type": "auth",
                "response_data": response.json() if response.status_code == 200 else None,
                "error": None
            }
            
        except httpx.ConnectError as e:
            return {
                "available": False,
                "status_code": None,
                "response_time_ms": (time.time() - start_time) * 1000,
                "url": f"{self.base_url}/health",
                "service_type": "auth",
                "response_data": None,
                "error": f"Connection failed: {str(e)}"
            }
        except httpx.TimeoutException as e:
            return {
                "available": False,
                "status_code": None,
                "response_time_ms": (time.time() - start_time) * 1000,
                "url": f"{self.base_url}/health",
                "service_type": "auth",
                "response_data": None,
                "error": f"Timeout: {str(e)}"
            }
        except Exception as e:
            return {
                "available": False,
                "status_code": None,
                "response_time_ms": (time.time() - start_time) * 1000,
                "url": f"{self.base_url}/health",
                "service_type": "auth",
                "response_data": None,
                "error": f"Unexpected error: {str(e)}"
            }
            
    async def create_test_user(self, email: Optional[str] = None, 
                             password: str = "TestPass123#") -> Dict[str, Any]:
        """Create a test user with optional custom email.
        Uses mock token for testing to avoid auth service dependency issues.
        
        Args:
            email: Optional email (auto-generated if None)
            password: User password (for mock purposes)
            
        Returns:
            Dict with user info and token
        """
        # Generate test user data
        import uuid
        if not email:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        # Use mock token that's signed with the test JWT secret
        # This allows the backend to validate it properly
        import time

        import jwt
        
        # Get JWT secret from environment (set by test config)
        import os
        jwt_secret = env.get("JWT_SECRET_KEY", "test-jwt-secret-key-unified-testing-32chars")
        
        # Create a valid JWT token for testing
        payload = {
            "sub": f"test-user-{int(time.time())}",
            "email": email,
            "permissions": ["read", "write"],
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,  # 15 minutes
            "token_type": "access",
            "iss": "netra-auth-service",  # Required issuer claim
            "jti": str(uuid.uuid4())      # Required JWT ID for replay protection
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        return {
            "user": {
                "id": payload["sub"],
                "email": email,
                "name": "Test User"
            },
            "email": email,
            "password": password,
            "token": token
        }
        
    async def update_user_permissions(self, user_id: str, permissions: List[str]) -> Dict[str, Any]:
        """Update user permissions.
        
        Args:
            user_id: User ID
            permissions: List of permissions to set
            
        Returns:
            Updated user data
        """
        response = await self.client.put(
            f"/auth/users/{user_id}/permissions",
            json={"permissions": permissions}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions.
        
        Args:
            user_id: User ID
            
        Returns:
            List of user permissions
        """
        response = await self.client.get(f"/auth/users/{user_id}/permissions")
        response.raise_for_status()
        data = response.json()
        return data.get("permissions", [])
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()