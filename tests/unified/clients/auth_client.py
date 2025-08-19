"""Test client for auth service with typed methods."""

import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


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
                "password": password
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
            
    async def create_test_user(self, email: Optional[str] = None, 
                             password: str = "testpass123") -> Dict[str, Any]:
        """Create a test user with optional custom email.
        
        Args:
            email: Optional email, generates unique if not provided
            password: User password
            
        Returns:
            Dict with user info and token
        """
        if not email:
            import uuid
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
            
        user = await self.register(email, password)
        token = await self.login(email, password)
        
        return {
            "user": user,
            "email": email,
            "password": password,
            "token": token
        }
        
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()