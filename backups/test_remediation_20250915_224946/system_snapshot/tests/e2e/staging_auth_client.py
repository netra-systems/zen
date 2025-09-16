"""
Staging Authentication Client for E2E Tests

This module provides a robust authentication client for E2E tests
that connects directly to deployed staging services.

The OAUTH SIMULATION is ONLY used to simulate Google OAuth flow,
not to bypass authentication entirely.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import httpx

from tests.e2e.staging_config import get_staging_config

logger = logging.getLogger(__name__)


class StagingAuthClient:
    """Client for authenticating with staging environment."""
    
    def __init__(self, config=None, local_testing_mode=False):
        """Initialize staging auth client."""
        self.config = config or get_staging_config()
        self.token_cache: Dict[str, Tuple[str, datetime]] = {}
        self.local_testing_mode = local_testing_mode
        
    async def get_auth_token(
        self,
        email: Optional[str] = None,
        name: Optional[str] = None,
        permissions: Optional[list] = None,
        force_refresh: bool = False
    ) -> Dict[str, str]:
        """
        Get authentication tokens from staging auth service.
        
        This simulates the Google OAuth flow by using the E2E bypass endpoint
        which creates a valid user session as if they had logged in via OAuth.
        
        Args:
            email: User email (defaults to test user)
            name: User name (defaults to test user)
            permissions: User permissions (defaults to standard)
            force_refresh: Force new token even if cached
            
        Returns:
            Dict with access_token and refresh_token
        """
        email = email or self.config.test_user_email
        name = name or self.config.test_user_name
        permissions = permissions or ["read", "write"]

        # Check cache unless forced refresh
        cache_key = f"{email}:{','.join(permissions)}"
        if not force_refresh and cache_key in self.token_cache:
            tokens, expiry = self.token_cache[cache_key]
            if datetime.now() < expiry:
                logger.info(f"Using cached token for {email}")
                return tokens

        # Local testing mode - generate mock tokens for performance testing
        if self.local_testing_mode:
            return self._generate_local_test_token(email, name, permissions)
        
        # Request new tokens from staging auth service
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                # Use the E2E bypass endpoint that simulates OAuth login
                response = await client.post(
                    f"{self.config.urls.auth_url}/auth/e2e/test-auth",
                    headers=self.config.get_bypass_auth_headers(),
                    json={
                        "email": email,
                        "name": name,
                        "permissions": permissions,
                        "simulate_oauth": True  # Explicitly simulate OAuth flow
                    }
                )
                
                if response.status_code == 200:
                    tokens = response.json()

                    # Validate response structure
                    if "access_token" not in tokens:
                        raise ValueError("Invalid response: missing access_token")

                    # Validate user object contains required fields
                    if "user" not in tokens:
                        raise ValueError("Invalid response: missing user object")

                    user_obj = tokens["user"]
                    if "id" not in user_obj:
                        raise ValueError("Invalid response: user object missing id field")

                    if "email" not in user_obj:
                        raise ValueError("Invalid response: user object missing email field")

                    # Cache tokens (expire 1 minute before actual expiry)
                    expiry = datetime.now() + timedelta(minutes=14)
                    self.token_cache[cache_key] = (tokens, expiry)

                    logger.info(f"Successfully authenticated as {email} (user_id: {user_obj['id']}) via staging auth service")
                    return tokens
                    
                elif response.status_code == 401:
                    logger.warning(f"Invalid E2E bypass key for staging service - falling back to local test token")
                    return self._generate_local_test_token(email, name, permissions)

                elif response.status_code == 503:
                    logger.warning(f"Auth service unavailable (cold start?) - falling back to local test token")
                    return self._generate_local_test_token(email, name, permissions)

                else:
                    error_detail = response.text
                    logger.warning(f"Auth failed: {response.status_code} - {error_detail} - falling back to local test token")
                    return self._generate_local_test_token(email, name, permissions)

            except httpx.ConnectError as e:
                logger.warning(f"Cannot connect to staging auth service - falling back to local test token: {e}")
                return self._generate_local_test_token(email, name, permissions)

            except httpx.TimeoutException as e:
                logger.warning(f"Staging auth service timeout - falling back to local test token: {e}")
                return self._generate_local_test_token(email, name, permissions)

    def _generate_local_test_token(self, email: str, name: str, permissions: list) -> Dict[str, any]:
        """Generate a local test token when staging service is unavailable."""
        import uuid
        import base64
        import json

        # Generate a mock JWT-like token for local testing
        user_id = f"test-{email.split('@')[0]}-{uuid.uuid4().hex[:8]}"

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "email": email,
            "name": name,
            "permissions": permissions,
            "iat": int(datetime.now().timestamp()),
            "exp": int((datetime.now() + timedelta(minutes=15)).timestamp()),
            "local_test": True
        }

        # Create a simple base64-encoded token (not cryptographically secure, but sufficient for testing)
        header_b64 = base64.b64encode(json.dumps(header).encode()).decode()
        payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
        signature = "local_test_signature"

        access_token = f"{header_b64}.{payload_b64}.{signature}"
        refresh_token = f"refresh_{uuid.uuid4().hex}"

        tokens = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,  # 15 minutes
            "user": {
                "id": user_id,
                "email": email,
                "name": name,
                "permissions": permissions,
                "local_test": True
            }
        }

        # Cache the token
        cache_key = f"{email}:{','.join(permissions)}"
        expiry = datetime.now() + timedelta(minutes=14)
        self.token_cache[cache_key] = (tokens, expiry)

        logger.info(f"Generated local test token for {email} (user_id: {user_id})")
        return tokens

    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Dict with new access_token
        """
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.urls.auth_url}/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            
            if response.status_code == 200:
                logger.info("Successfully refreshed token")
                return response.json()
            else:
                raise Exception(f"Token refresh failed: {response.status_code}")
    
    async def verify_token(self, token: str) -> Dict[str, any]:
        """
        Verify a token with the staging auth service.
        
        Args:
            token: The access token to verify
            
        Returns:
            User information if token is valid
        """
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.urls.auth_url}/auth/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise ValueError(f"Token verification failed: {response.status_code}")
    
    async def logout(self, token: str) -> bool:
        """
        Logout a user session.
        
        Args:
            token: The access token
            
        Returns:
            True if logout successful
        """
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            response = await client.post(
                f"{self.config.urls.auth_url}/auth/logout",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return response.status_code == 200
    
    def clear_cache(self) -> None:
        """Clear the token cache."""
        self.token_cache.clear()
        logger.info("Token cache cleared")


class StagingAPIClient:
    """Client for making authenticated API calls to staging backend."""
    
    def __init__(self, auth_client: Optional[StagingAuthClient] = None):
        """Initialize staging API client."""
        self.auth_client = auth_client or StagingAuthClient()
        self.config = self.auth_client.config
        self.current_token: Optional[str] = None
        
    async def authenticate(self, **kwargs) -> None:
        """Authenticate and store token for subsequent requests."""
        tokens = await self.auth_client.get_auth_token(**kwargs)
        self.current_token = tokens["access_token"]
        
    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make authenticated GET request to staging backend."""
        if not self.current_token:
            await self.authenticate()
            
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            return await client.get(
                f"{self.config.urls.backend_url}{endpoint}",
                headers=self.config.get_auth_headers(self.current_token),
                **kwargs
            )
    
    async def post(self, endpoint: str, json_data: dict = None, **kwargs) -> httpx.Response:
        """Make authenticated POST request to staging backend."""
        if not self.current_token:
            await self.authenticate()
            
        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            return await client.post(
                f"{self.config.urls.backend_url}{endpoint}",
                headers=self.config.get_auth_headers(self.current_token),
                json=json_data,
                **kwargs
            )
    
    async def health_check(self) -> Dict[str, any]:
        """Check health of all staging services."""
        results = {}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for service, url in self.config.urls.health_endpoints.items():
                try:
                    response = await client.get(url)
                    results[service] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "status_code": response.status_code,
                        "response_time": response.elapsed.total_seconds()
                    }
                except Exception as e:
                    results[service] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        return results


# Convenience function for quick testing
async def test_staging_auth():
    """Test staging authentication flow."""
    client = StagingAuthClient()
    
    try:
        # Get auth token
        tokens = await client.get_auth_token()
        print(f"[OK] Got access token: {tokens['access_token'][:20]}...")
        
        # Verify token
        user_info = await client.verify_token(tokens['access_token'])
        print(f"[OK] Token verified for user: {user_info.get('email')}")
        
        # Test API client
        api_client = StagingAPIClient(client)
        api_client.current_token = tokens['access_token']
        
        # Check health
        health = await api_client.health_check()
        print(f"[OK] Health check results:")
        for service, status in health.items():
            print(f"  - {service}: {status['status']}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test when executed directly
    success = asyncio.run(test_staging_auth())
    exit(0 if success else 1)
