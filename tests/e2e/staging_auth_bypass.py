"""
E2E Test Authentication Helper for Staging Environment

This module provides authentication bypass functionality for E2E tests
running against the staging environment. It uses a secure bypass key
stored in Google Secrets Manager to authenticate without OAuth.

Usage:
    auth_helper = StagingAuthHelper()
    token = await auth_helper.get_test_token()
    
    # Use token in API requests
    headers = {"Authorization": f"Bearer {token}"}
"""

import os
import json
import asyncio
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class StagingAuthHelper:
    """Helper class for E2E test authentication on staging."""
    
    def __init__(self, bypass_key: Optional[str] = None):
        """
        Initialize the staging auth helper.
        
        Args:
            bypass_key: E2E bypass key. If not provided, will try to load from environment.
        """
        env = get_env()
        self.bypass_key = bypass_key or env.get("E2E_OAUTH_SIMULATION_KEY")
        # Use SSOT for staging auth URL
        from netra_backend.app.core.network_constants import URLConstants
        self.staging_auth_url = env.get("STAGING_AUTH_URL", URLConstants.STAGING_AUTH_URL)
        self.token_cache: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        
        if not self.bypass_key:
            raise ValueError(
                "E2E_OAUTH_SIMULATION_KEY not provided. Set it via environment variable or pass directly."
            )
    
    async def get_test_token(
        self,
        email: str = "e2e-test@staging.netrasystems.ai",
        name: str = "E2E Test User",
        permissions: list = None
    ) -> str:
        """
        Get a valid test token for E2E testing.
        
        Args:
            email: Test user email
            name: Test user name
            permissions: List of permissions for the test user
            
        Returns:
            JWT access token for testing
        """
        # Check if we have a cached token that's still valid
        if self.token_cache and self.token_expiry and datetime.now() < self.token_expiry:
            logger.info("Using cached test token")
            return self.token_cache
        
        # Request new token
        permissions = permissions or ["read", "write"]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.staging_auth_url}/auth/e2e/test-auth",
                    headers={
                        "X-E2E-Bypass-Key": self.bypass_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "email": email,
                        "name": name,
                        "permissions": permissions
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token_cache = data["access_token"]
                    # Cache for 14 minutes (assuming 15 minute expiry)
                    self.token_expiry = datetime.now() + timedelta(minutes=14)
                    logger.info(f"Successfully obtained test token for {email}")
                    return self.token_cache
                else:
                    error_msg = f"Failed to get test token: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                    
            except httpx.RequestError as e:
                logger.error(f"Network error during test authentication: {e}")
                raise
    
    async def get_authenticated_client(
        self,
        base_url: Optional[str] = None,
        **user_kwargs
    ) -> httpx.AsyncClient:
        """
        Get an authenticated HTTP client for E2E testing.
        
        Args:
            base_url: Base URL for the client
            **user_kwargs: Additional arguments for get_test_token
            
        Returns:
            Configured httpx.AsyncClient with auth headers
        """
        token = await self.get_test_token(**user_kwargs)
        
        return httpx.AsyncClient(
            base_url=base_url or self.staging_auth_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    def get_sync_token(self, **kwargs) -> str:
        """
        Synchronous wrapper for getting test token.
        
        Returns:
            JWT access token for testing
        """
        return asyncio.run(self.get_test_token(**kwargs))


# Singleton instance for easy import
_staging_auth = None

def get_staging_auth() -> StagingAuthHelper:
    """Get or create the singleton staging auth helper."""
    global _staging_auth
    if _staging_auth is None:
        _staging_auth = StagingAuthHelper()
    return _staging_auth


# Example usage and test
async def test_staging_auth():
    """Test the staging OAUTH SIMULATION functionality."""
    try:
        auth = StagingAuthHelper()
        
        # Get a test token
        token = await auth.get_test_token()
        print(f"Successfully obtained test token: {token[:20]}...")
        
        # Get an authenticated client
        async with await auth.get_authenticated_client() as client:
            # Test with a simple health check
            response = await client.get("/auth/health")
            print(f"Health check response: {response.status_code}")
            
            # Test token validation
            response = await client.post("/auth/verify")
            if response.status_code == 200:
                user_info = response.json()
                print(f"Token validated successfully: {user_info}")
            else:
                print(f"Token validation failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test if executed directly
    success = asyncio.run(test_staging_auth())
    exit(0 if success else 1)
