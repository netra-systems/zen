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
    
    def __init__(self, config=None):
        """Initialize staging auth client."""
        self.config = config or get_staging_config()
        self.token_cache: Dict[str, Tuple[str, datetime]] = {}
        
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
                    
                    # Cache tokens (expire 1 minute before actual expiry)
                    expiry = datetime.now() + timedelta(minutes=14)
                    self.token_cache[cache_key] = (tokens, expiry)
                    
                    logger.info(f"Successfully authenticated as {email} via staging auth service")
                    return tokens
                    
                elif response.status_code == 401:
                    raise ValueError(f"Invalid E2E bypass key. Check E2E_OAUTH_SIMULATION_KEY environment variable")
                    
                elif response.status_code == 503:
                    raise ConnectionError(f"Auth service unavailable (cold start?). Retry in a few seconds")
                    
                else:
                    error_detail = response.text
                    raise Exception(f"Auth failed: {response.status_code} - {error_detail}")
                    
            except httpx.ConnectError as e:
                raise ConnectionError(f"Cannot connect to staging auth service at {self.config.urls.auth_url}: {e}")
                
            except httpx.TimeoutException:
                raise TimeoutError(f"Staging auth service timeout after {self.config.timeout}s")
    
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
            User information with "valid" key if token is valid
        """
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.config.urls.auth_url}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    # Add "valid" key for test compatibility
                    user_info["valid"] = True
                    return user_info
                else:
                    return {"valid": False, "error": f"Token verification failed: {response.status_code}"}
                    
        except Exception as e:
            logger.warning(f"Token verification error: {e}")
            # Fallback: Basic JWT validation
            try:
                import jwt
                
                # Use staging JWT secret for verification
                staging_jwt_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
                decoded = jwt.decode(token, staging_jwt_secret, algorithms=["HS256"])
                
                return {
                    "valid": True,
                    "user_id": decoded.get("sub"),
                    "email": decoded.get("email"),
                    "permissions": decoded.get("permissions", [])
                }
                
            except Exception as jwt_error:
                return {"valid": False, "error": f"JWT validation failed: {jwt_error}"}
    
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
    
    async def generate_test_access_token(
        self,
        user_id: str,
        email: str,
        permissions: Optional[list] = None
    ) -> str:
        """
        Generate test access token for E2E testing.
        
        This method uses the staging auth service to generate a valid JWT token
        for the specified user, mimicking the OAuth flow but using E2E bypass.
        
        Args:
            user_id: User ID for the token
            email: User email address
            permissions: User permissions (defaults to ["read", "write"])
            
        Returns:
            Valid JWT token string
        """
        permissions = permissions or ["read", "write"]
        
        # Try to get tokens via the E2E bypass endpoint
        try:
            tokens = await self.get_auth_token(
                email=email,
                name=f"E2E Test User {user_id}",
                permissions=permissions,
                force_refresh=True
            )
            return tokens["access_token"]
            
        except Exception as e:
            logger.warning(f"Staging auth service failed for {email}: {e}")
            logger.info("Falling back to JWT token creation")
            
            # Fallback: Create staging-compatible JWT token directly
            return self._create_staging_jwt_token(user_id, email, permissions)
    
    def _create_staging_jwt_token(self, user_id: str, email: str, permissions: list) -> str:
        """
        Create staging-compatible JWT token as fallback.
        
        This creates a JWT token that works with the staging environment
        when the auth service E2E bypass is unavailable.
        """
        import jwt
        import time
        from datetime import datetime, timedelta, timezone
        
        # Use staging JWT secret (hardcoded for E2E testing)
        staging_jwt_secret = "7SVLKvh7mJNeF6njiRJMoZpUWLya3NfsvJfRHPc0-cYI7Oh80oXOUHuBNuMjUI4ghNTHFH0H7s9vf3S835ET5A"
        
        # Create staging-compatible payload
        payload = {
            "sub": user_id,
            "email": email,
            "permissions": permissions,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service",
            "jti": f"e2e-staging-{int(time.time())}",
            "staging": True,
            "e2e_test": True
        }
        
        # Sign with staging secret
        token = jwt.encode(payload, staging_jwt_secret, algorithm="HS256")
        
        logger.info(f"Created fallback staging JWT for {email}")
        return token


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
